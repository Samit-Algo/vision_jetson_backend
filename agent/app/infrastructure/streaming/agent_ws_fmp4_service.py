"""
Agent WebSocket fMP4 Service
============================

Streams agent-processed frames (with bounding boxes) via WebSocket as fMP4.
Reads frames from shared_store instead of RTSP.
"""
import asyncio
import subprocess
import traceback
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Any
from fastapi import WebSocket


@dataclass
class _AgentStreamState:
    process: subprocess.Popen
    viewers: Set[WebSocket] = field(default_factory=set)
    frame_reader_task: Optional[asyncio.Task] = None
    broadcast_task: Optional[asyncio.Task] = None
    last_error: Optional[str] = None
    init_segment: Optional[bytes] = None
    _mp4_parse_buf: bytearray = field(default_factory=bytearray)
    _init_accum: bytearray = field(default_factory=bytearray)
    _init_ready: bool = False
    _last_frame_index: int = -1


class AgentWsFmp4Service:
    """
    Agent streaming service: shared_store frames -> FFmpeg -> fMP4 -> WebSocket.
    
    Design:
    - 1 FFmpeg process per agent
    - N websocket viewers per agent (broadcast)
    - Reads processed frames from shared_store[agent_id]
    - Encodes to H.264 fMP4 via FFmpeg pipe
    """
    
    def __init__(self, shared_store: Dict[str, Any]) -> None:
        self.shared_store = shared_store
        self._streams: Dict[str, _AgentStreamState] = {}
        self._lock = asyncio.Lock()
        
        # Frame encoding settings
        self._fps = 25  # Default FPS (will use actual_fps from frames if available)
        
    def _build_ffmpeg_cmd(self, width: int, height: int, fps: int = 25) -> list[str]:
        """
        Build FFmpeg command that reads raw frames from stdin and outputs fMP4.
        
        Input: raw BGR frames via pipe (stdin) - matches OpenCV format
        Output: H.264 encoded fMP4 fragments
        """
        return [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            # Input: raw BGR frames from stdin (OpenCV format)
            "-f", "rawvideo",
            "-pixel_format", "bgr24",  # BGR matches OpenCV format
            "-video_size", f"{width}x{height}",
            "-framerate", str(fps),
            "-i", "pipe:0",
            # Video encoding: H.264
            "-c:v", "libx264",
            "-preset", "ultrafast",  # Low latency
            "-tune", "zerolatency",
            "-profile:v", "baseline",
            "-level", "3.0",
            "-pix_fmt", "yuv420p",
            "-g", str(fps * 2),  # GOP size (keyframe every 2 seconds)
            "-keyint_min", str(fps),  # Minimum keyframe interval
            "-bf", "0",  # No B-frames for lower latency
            # Fragmented MP4 for MSE
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            # Output to stdout
            "pipe:1",
        ]
    
    def _start_process(self, agent_id: str, width: int, height: int, fps: int = 25) -> subprocess.Popen:
        """Start FFmpeg process for agent stream."""
        print(f"[agent_ws_fmp4] Starting WS fMP4 stream for agent {agent_id} ({width}x{height} @ {fps}fps)")
        
        ffmpeg_cmd = self._build_ffmpeg_cmd(width, height, fps)
        
        # Start FFmpeg process with unbuffered I/O
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        
        # Start background task to monitor FFmpeg stderr for errors
        asyncio.create_task(self._monitor_ffmpeg_stderr(agent_id, process))
        
        print(f"[agent_ws_fmp4] FFmpeg process started for agent {agent_id} (PID: {process.pid})")
        return process
    
    async def _monitor_ffmpeg_stderr(self, agent_id: str, process: subprocess.Popen):
        """Monitor FFmpeg stderr for errors and log them."""
        print(f"[agent_ws_fmp4] FFmpeg stderr monitor started for agent {agent_id}")
        try:
            loop = asyncio.get_event_loop()
            while process.poll() is None:
                try:
                    # Use executor to avoid blocking the event loop
                    line = await loop.run_in_executor(None, process.stderr.readline)
                    if line:
                        line_str = line.decode('utf-8', errors='ignore').strip()
                        if line_str:
                            if 'error' in line_str.lower() or 'failed' in line_str.lower():
                                print(f"[agent_ws_fmp4] ERROR: FFmpeg error for agent {agent_id}: {line_str}")
                            else:
                                print(f"[agent_ws_fmp4] DEBUG: FFmpeg stderr for agent {agent_id}: {line_str}")
                except Exception as e:
                    print(f"[agent_ws_fmp4] WARNING: Error reading FFmpeg stderr: {e}")
                    break
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[agent_ws_fmp4] ERROR: Error in FFmpeg stderr monitor: {e}")
        finally:
            print(f"[agent_ws_fmp4] FFmpeg stderr monitor stopped for agent {agent_id}")
    
    async def _read_frames_and_feed_ffmpeg(self, agent_id: str, state: _AgentStreamState):
        """
        Read frames from shared_store and feed to FFmpeg stdin.
        Runs in background task.
        Uses executor to avoid blocking the event loop.
        """
        frame_interval = 1.0 / self._fps
        no_frame_count = 0
        max_no_frame_wait = 100
        frames_written = 0
        
        print(f"[agent_ws_fmp4] Frame reader started for agent {agent_id}")
        
        try:
            while state.process.poll() is None:
                # Read latest frame from shared_store
                agent_data = self.shared_store.get(agent_id)
                
                if not agent_data:
                    no_frame_count += 1
                    if no_frame_count == 1:
                        print(f"[agent_ws_fmp4] DEBUG: No data in shared_store for agent {agent_id}, available keys: {list(self.shared_store.keys())}")
                    if no_frame_count > max_no_frame_wait:
                        if no_frame_count % 100 == 0:
                            print(f"[agent_ws_fmp4] WARNING: No frames in shared_store for agent {agent_id} (waiting... {no_frame_count} attempts)")
                        await asyncio.sleep(0.1)
                    else:
                        await asyncio.sleep(0.05)
                    continue
                
                if "bytes" not in agent_data:
                    no_frame_count += 1
                    if no_frame_count == 1:
                        print(f"[agent_ws_fmp4] DEBUG: No 'bytes' key in shared_store for agent {agent_id}, keys: {list(agent_data.keys())}")
                    await asyncio.sleep(0.05)
                    continue
                
                # Check if this is a new frame
                frame_index = agent_data.get("frame_index", -1)
                if frame_index == state._last_frame_index:
                    await asyncio.sleep(0.01)
                    continue
                
                state._last_frame_index = frame_index
                no_frame_count = 0
                
                # Get frame data
                frame_bytes = agent_data.get("bytes")
                shape = agent_data.get("shape")  # (height, width, 3)
                
                if not frame_bytes:
                    print(f"[agent_ws_fmp4] WARNING: Frame bytes is empty for agent {agent_id}")
                    await asyncio.sleep(0.01)
                    continue
                    
                if not shape or len(shape) < 2:
                    print(f"[agent_ws_fmp4] WARNING: Invalid shape for agent {agent_id}: {shape}")
                    await asyncio.sleep(0.01)
                    continue
                
                height, width = shape[0], shape[1]
                
                # Validate frame size matches shape
                expected_size = height * width * 3
                if len(frame_bytes) != expected_size:
                    print(f"[agent_ws_fmp4] WARNING: Frame size mismatch for agent {agent_id}: expected {expected_size}, got {len(frame_bytes)}")
                    await asyncio.sleep(0.01)
                    continue
                
                # Get FPS from frame data (use actual_fps if available, fallback to camera_fps)
                actual_fps = agent_data.get("actual_fps") or agent_data.get("camera_fps") or self._fps
                frame_interval = 1.0 / max(1, actual_fps)  # Prevent division by zero
                
                # Write frame bytes directly to FFmpeg stdin (already in BGR format)
                # Use executor to avoid blocking event loop
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, state.process.stdin.write, frame_bytes)
                    await loop.run_in_executor(None, state.process.stdin.flush)
                    frames_written += 1
                    if frames_written == 1:
                        print(f"[agent_ws_fmp4] First frame written to FFmpeg for agent {agent_id} (size: {len(frame_bytes)} bytes, shape: {width}x{height})")
                    if frames_written % 30 == 0:
                        print(f"[agent_ws_fmp4] DEBUG: Written {frames_written} frames to FFmpeg for agent {agent_id}")
                except BrokenPipeError:
                    print(f"[agent_ws_fmp4] WARNING: FFmpeg pipe broken for agent {agent_id} - FFmpeg may have crashed")
                    # Check FFmpeg stderr for errors
                    if state.process.stderr:
                        try:
                            stderr_data = state.process.stderr.read(4096)
                            if stderr_data:
                                print(f"[agent_ws_fmp4] ERROR: FFmpeg stderr for agent {agent_id}: {stderr_data.decode('utf-8', errors='ignore')}")
                        except:
                            pass
                    break
                except Exception as e:
                    print(f"[agent_ws_fmp4] ERROR: Error writing frame to FFmpeg for agent {agent_id}: {e}")
                    print(traceback.format_exc())
                    break
                
                # Maintain FPS
                await asyncio.sleep(frame_interval)
                
        except Exception as e:
            print(f"[agent_ws_fmp4] ERROR: Error in frame reader for agent {agent_id}: {e}")
            print(traceback.format_exc())
        finally:
            print(f"[agent_ws_fmp4] Frame reader stopped for agent {agent_id}, wrote {frames_written} frames total")
            # Close FFmpeg stdin when done
            if state.process.stdin:
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, state.process.stdin.close)
                except:
                    pass
    
    async def _broadcast_loop(self, agent_id: str):
        """
        Read fMP4 chunks from FFmpeg stdout and broadcast to all WebSocket viewers.
        Also handles MP4 init segment extraction.
        Uses executor to avoid blocking the event loop.
        """
        state = self._streams.get(agent_id)
        if not state:
            print(f"[agent_ws_fmp4] ERROR: No state found for agent {agent_id} in broadcast loop")
            return
        
        print(f"[agent_ws_fmp4] Broadcast loop started for agent {agent_id}")
        loop = asyncio.get_event_loop()
        chunks_sent = 0
        empty_chunks = 0
        
        try:
            while state.process.poll() is None:
                # Read chunk from FFmpeg stdout (non-blocking)
                try:
                    chunk = await loop.run_in_executor(None, state.process.stdout.read, 4096)
                except Exception as e:
                    print(f"[agent_ws_fmp4] ERROR: Error reading from FFmpeg stdout for agent {agent_id}: {e}")
                    await asyncio.sleep(0.1)
                    continue
                
                if not chunk:
                    empty_chunks += 1
                    if empty_chunks == 1:
                        print(f"[agent_ws_fmp4] DEBUG: Received empty chunk from FFmpeg for agent {agent_id} (FFmpeg may not be producing output yet)")
                    if empty_chunks % 100 == 0:
                        print(f"[agent_ws_fmp4] WARNING: Still receiving empty chunks from FFmpeg for agent {agent_id} ({empty_chunks} empty chunks)")
                    await asyncio.sleep(0.01)
                    continue
                
                empty_chunks = 0
                chunks_sent += 1
                if chunks_sent == 1:
                    print(f"[agent_ws_fmp4] First chunk received from FFmpeg for agent {agent_id} (size: {len(chunk)} bytes)")
                if chunks_sent % 100 == 0:
                    print(f"[agent_ws_fmp4] DEBUG: Sent {chunks_sent} chunks for agent {agent_id}")
                
                # Parse MP4 to extract init segment (ftyp + moov)
                if not state._init_ready:
                    state._mp4_parse_buf.extend(chunk)
                    self._try_extract_init_segment(state, agent_id)
                    
                    # If init segment is now ready, send it to existing viewers
                    if state._init_ready and state.init_segment:
                        disconnected = set()
                        for ws in state.viewers:
                            try:
                                await ws.send_bytes(state.init_segment)
                                print(f"[agent_ws_fmp4] Sent init segment to viewer for agent {agent_id} ({len(state.init_segment)} bytes)")
                            except Exception as e:
                                print(f"[agent_ws_fmp4] WARNING: Error sending init segment: {e}")
                                disconnected.add(ws)
                        
                        for ws in disconnected:
                            state.viewers.discard(ws)
                        
                        # Clear parse buffer and continue with remaining data
                        if state._mp4_parse_buf:
                            chunk = bytes(state._mp4_parse_buf)
                            state._mp4_parse_buf.clear()
                        else:
                            continue
                
                # Broadcast media chunks to all viewers
                disconnected = set()
                for ws in state.viewers:
                    try:
                        await ws.send_bytes(chunk)
                    except Exception as e:
                        print(f"[agent_ws_fmp4] WARNING: Error sending chunk to viewer: {e}")
                        disconnected.add(ws)
                
                # Remove disconnected viewers
                for ws in disconnected:
                    state.viewers.discard(ws)
                    
        except Exception as e:
            print(f"[agent_ws_fmp4] ERROR: Error in broadcast loop for agent {agent_id}: {e}")
            print(traceback.format_exc())
        finally:
            print(f"[agent_ws_fmp4] Broadcast loop stopped for agent {agent_id}, sent {chunks_sent} chunks total")
    
    def _try_extract_init_segment(self, state: _AgentStreamState, agent_id: str) -> None:
        """
        Parse MP4 boxes from the stream until we capture the init segment:
        ftyp + moov (and ignore everything else). Store it in state.init_segment.
        Based on vision-backend implementation.
        """
        buf = state._mp4_parse_buf

        def read_u32(b: bytes) -> int:
            return int.from_bytes(b, "big", signed=False)

        while True:
            if len(buf) < 8:
                return

            size = read_u32(buf[0:4])
            box_type = bytes(buf[4:8])

            header_len = 8
            if size == 1:
                # 64-bit extended size
                if len(buf) < 16:
                    return
                size = int.from_bytes(buf[8:16], "big", signed=False)
                header_len = 16
            elif size == 0:
                # box extends to end of file/stream (not expected for live)
                return

            if size < header_len or size > 50_000_000:
                # Guard against corruption; stop trying
                print(f"[agent_ws_fmp4] WARNING: Invalid box size {size} for agent {agent_id}, stopping init segment extraction")
                return

            if len(buf) < size:
                return

            box = bytes(buf[:size])
            del buf[:size]

            # Keep only ftyp + moov as init segment
            if box_type in (b"ftyp", b"moov"):
                state._init_accum.extend(box)
                if box_type == b"moov":
                    state.init_segment = bytes(state._init_accum)
                    state._init_ready = True
                    print(f"[agent_ws_fmp4] Captured init segment for agent {agent_id} ({len(state.init_segment)} bytes)")
                    # Free memory we no longer need
                    state._mp4_parse_buf.clear()
                    return
    
    async def add_viewer(self, agent_id: str, websocket: WebSocket, camera_id: str) -> None:
        """
        Register a websocket viewer for an agent stream.
        Starts FFmpeg + frame reader + broadcaster on first viewer.
        """
        print(f"[agent_ws_fmp4] Adding viewer for agent {agent_id}")
        
        # Get frame dimensions from first frame in shared_store
        # Wait a bit for frames to be available (agent might be processing)
        agent_data = None
        for attempt in range(20):  # Wait up to 2 seconds
            agent_data = self.shared_store.get(agent_id)
            if agent_data and "shape" in agent_data and "bytes" in agent_data:
                break
            await asyncio.sleep(0.1)
        
        if not agent_data:
            print(f"[agent_ws_fmp4] WARNING: No data in shared_store for agent {agent_id} after waiting")
            print(f"[agent_ws_fmp4] WARNING: Available keys in shared_store: {list(self.shared_store.keys())}")
            await websocket.close(code=1008, reason="Agent stream not available - no frames")
            return
        
        if "shape" not in agent_data:
            print(f"[agent_ws_fmp4] WARNING: No shape in shared_store for agent {agent_id}, data keys: {list(agent_data.keys())}")
            await websocket.close(code=1008, reason="Agent stream not available - invalid frame data")
            return
        
        shape = agent_data.get("shape")
        if not shape or len(shape) < 2:
            print(f"[agent_ws_fmp4] WARNING: Invalid shape for agent {agent_id}: {shape}")
            await websocket.close(code=1008, reason="Agent stream not available - invalid dimensions")
            return
        
        height, width = shape[0], shape[1]
        print(f"[agent_ws_fmp4] Agent {agent_id} frame dimensions: {width}x{height}")
        
        # Get FPS from frame data
        fps = agent_data.get("actual_fps") or agent_data.get("camera_fps") or self._fps
        print(f"[agent_ws_fmp4] Agent {agent_id} FPS: {fps}")
        
        init_to_send: Optional[bytes] = None
        
        async with self._lock:
            state = self._streams.get(agent_id)
            if state is None or state.process.poll() is not None:
                # (Re)start process
                print(f"[agent_ws_fmp4] Starting new FFmpeg process for agent {agent_id}")
                process = self._start_process(agent_id, width, height, int(fps))
                state = _AgentStreamState(process=process)
                self._streams[agent_id] = state
                
                # Verify FFmpeg process is running
                if process.poll() is not None:
                    print(f"[agent_ws_fmp4] ERROR: FFmpeg process died immediately after start for agent {agent_id}")
                    # Try to read stderr for error message
                    try:
                        stderr_data = process.stderr.read(4096)
                        if stderr_data:
                            print(f"[agent_ws_fmp4] ERROR: FFmpeg stderr: {stderr_data.decode('utf-8', errors='ignore')}")
                    except:
                        pass
                    await websocket.close(code=1011, reason="FFmpeg process failed to start")
                    return
                
                # Start frame reader task
                state.frame_reader_task = asyncio.create_task(
                    self._read_frames_and_feed_ffmpeg(agent_id, state)
                )
                print(f"[agent_ws_fmp4] Started frame reader task for agent {agent_id} (task: {state.frame_reader_task})")
                
                # Start broadcaster task
                state.broadcast_task = asyncio.create_task(
                    self._broadcast_loop(agent_id)
                )
                print(f"[agent_ws_fmp4] Started broadcaster task for agent {agent_id} (task: {state.broadcast_task})")
                
                # Give tasks a moment to start executing
                await asyncio.sleep(0.1)
                
                # Verify tasks are running
                if state.frame_reader_task.done():
                    try:
                        await state.frame_reader_task
                    except Exception as e:
                        print(f"[agent_ws_fmp4] ERROR: Frame reader task failed immediately: {e}")
                        print(traceback.format_exc())
                
                if state.broadcast_task.done():
                    try:
                        await state.broadcast_task
                    except Exception as e:
                        print(f"[agent_ws_fmp4] ERROR: Broadcast task failed immediately: {e}")
                        print(traceback.format_exc())
                
                # Wait a bit for init segment to be generated
                await asyncio.sleep(0.4)
            
            # Send init segment if available
            if state.init_segment:
                init_to_send = state.init_segment
                print(f"[agent_ws_fmp4] Init segment available for agent {agent_id} ({len(init_to_send)} bytes)")
            else:
                print(f"[agent_ws_fmp4] WARNING: Init segment not ready yet for agent {agent_id}, will wait...")
            
            state.viewers.add(websocket)
            print(f"[agent_ws_fmp4] Added viewer for agent {agent_id} (total viewers: {len(state.viewers)})")
        
        # Send init segment if available
        if init_to_send:
            try:
                await websocket.send_bytes(init_to_send)
                print(f"[agent_ws_fmp4] Sent init segment to viewer for agent {agent_id}")
            except Exception as e:
                print(f"[agent_ws_fmp4] ERROR: Error sending init segment: {e}")
        else:
            # Wait for init segment (with timeout)
            print(f"[agent_ws_fmp4] Waiting for init segment for agent {agent_id}...")
            for _ in range(50):  # Wait up to 5 seconds
                await asyncio.sleep(0.1)
                async with self._lock:
                    state = self._streams.get(agent_id)
                    if state and state.init_segment:
                        try:
                            await websocket.send_bytes(state.init_segment)
                            print(f"[agent_ws_fmp4] Sent init segment to viewer for agent {agent_id} (after wait)")
                            break
                        except Exception as e:
                            print(f"[agent_ws_fmp4] ERROR: Error sending init segment after wait: {e}")
                            break
    
    async def remove_viewer(self, agent_id: str, websocket: WebSocket) -> None:
        """Remove a websocket viewer."""
        print(f"[agent_ws_fmp4] Removing viewer for agent {agent_id}")
        async with self._lock:
            state = self._streams.get(agent_id)
            if state:
                # Close the WebSocket connection explicitly
                try:
                    if websocket.client_state.name != "DISCONNECTED":
                        await websocket.close(code=1000, reason="Viewer removed")
                except Exception as e:
                    print(f"[agent_ws_fmp4] WARNING: Error closing WebSocket: {e}")
                
                state.viewers.discard(websocket)
                print(f"[agent_ws_fmp4] Viewer removed for agent {agent_id}, remaining viewers: {len(state.viewers)}")
                
                # If no viewers, stop the stream
                if not state.viewers:
                    print(f"[agent_ws_fmp4] No viewers left for agent {agent_id}, stopping stream")
                    if state.process:
                        try:
                            state.process.terminate()
                            state.process.wait(timeout=2)
                        except:
                            try:
                                state.process.kill()
                            except:
                                pass
                    if state.frame_reader_task:
                        state.frame_reader_task.cancel()
                        try:
                            await state.frame_reader_task
                        except asyncio.CancelledError:
                            pass
                    if state.broadcast_task:
                        state.broadcast_task.cancel()
                        try:
                            await state.broadcast_task
                        except asyncio.CancelledError:
                            pass
                    del self._streams[agent_id]
                    print(f"[agent_ws_fmp4] Stopped stream for agent {agent_id} (no viewers)")
