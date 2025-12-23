"""
Event Notifier
==============

Utility to send event notifications with annotated frames to web backend.
"""
import os
import base64
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import numpy as np

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None


def serialize_for_json(obj: Any) -> Any:
    """
    Recursively serialize objects for JSON encoding.
    Converts datetime objects to ISO format strings.
    
    Args:
        obj: Object to serialize
    
    Returns:
        JSON-serializable object
    """
    if isinstance(obj, datetime):
        return obj.isoformat() + "Z" if obj.tzinfo else obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


def encode_frame_to_base64(frame: np.ndarray) -> Optional[str]:
    """
    Encode a frame (numpy array) to base64 JPEG string.
    
    Args:
        frame: OpenCV frame (numpy array in BGR format)
    
    Returns:
        Base64-encoded JPEG string, or None if encoding fails
    """
    if cv2 is None:
        return None
    
    try:
        # Encode frame as JPEG
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            return None
        
        # Convert to base64
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        return frame_base64
    except Exception as exc:
        print(f"[event_notifier] ⚠️  Error encoding frame: {exc}")
        return None


async def send_event_to_backend(
    event: Dict[str, Any],
    annotated_frame: np.ndarray,
    agent_id: str,
    agent_name: str,
    camera_id: Optional[str] = None,
    video_timestamp: Optional[str] = None,
    detections: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send event notification with annotated frame to web backend.
    
    Args:
        event: Event dict with 'label' and optionally 'rule_index'
        annotated_frame: Frame with bounding boxes drawn (numpy array)
        agent_id: Agent identifier
        agent_name: Agent name
        camera_id: Camera identifier (optional)
        video_timestamp: Video timestamp string (optional)
        detections: Detection details (optional)
    
    Returns:
        True if sent successfully, False otherwise
    """
    # Get web backend URL from device (per-device URL)
    web_backend_url = None
    
    if camera_id:
        try:
            # Import repositories (lazy import to avoid circular dependencies)
            from agent.infrastructure.database.camera_repository_impl import MongoCameraRepository
            from agent.infrastructure.database.device_repository_impl import MongoDeviceRepository
            
            camera_repo = MongoCameraRepository()
            device_repo = MongoDeviceRepository()
            
            # Get camera to find device_id
            camera = camera_repo.find_by_id(camera_id)
            if camera and camera.device_id:
                # Get device to find web_backend_url
                device = device_repo.find_by_id(camera.device_id)
                if device and device.web_backend_url:
                    web_backend_url = device.web_backend_url
                    print(f"[event_notifier] Using device-specific web backend URL: {web_backend_url}")
        except Exception as e:
            print(f"[event_notifier] ⚠️  Error getting device URL: {e}")
    
    # Fallback to environment variable if device URL not found
    if not web_backend_url:
        web_backend_url = os.getenv("WEB_BACKEND_URL")
        if web_backend_url:
            print(f"[event_notifier] Using environment variable WEB_BACKEND_URL: {web_backend_url}")
    
    if not web_backend_url:
        print("[event_notifier] ⚠️  WEB_BACKEND_URL not found in device or environment, skipping event notification")
        return False
    
    # Encode frame to base64
    frame_base64 = encode_frame_to_base64(annotated_frame)
    if not frame_base64:
        print("[event_notifier] ⚠️  Failed to encode frame, skipping event notification")
        return False
    
    # Build payload
    payload = {
        "event": {
            "label": event.get("label", "Unknown"),
            "rule_index": event.get("rule_index"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        "agent": {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "camera_id": camera_id,
        },
        "frame": {
            "image_base64": frame_base64,
            "format": "jpeg",
        },
        "metadata": {
            "video_timestamp": video_timestamp,
            "detections": serialize_for_json(detections) if detections else None,
        }
    }
    
    # Send HTTP POST request
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try common endpoint paths
            endpoints = [
                f"{web_backend_url}/api/events",
                f"{web_backend_url}/events",
                f"{web_backend_url}/api/agents/{agent_id}/events",
            ]
            
            last_error = None
            for endpoint in endpoints:
                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code in [200, 201, 202]:
                        print(f"[event_notifier] ✅ Event sent to backend: {event.get('label')} (endpoint: {endpoint})")
                        return True
                    else:
                        print(f"[event_notifier] ⚠️  Backend returned status {response.status_code} for {endpoint}")
                except httpx.RequestError as e:
                    last_error = e
                    continue
                except Exception as e:
                    last_error = e
                    print(f"[event_notifier] ⚠️  Error with endpoint {endpoint}: {e}")
                    continue
            
            error_msg = str(last_error) if last_error else "unknown error"
            print(f"[event_notifier] ⚠️  Failed to send event: all endpoints failed. Last error: {error_msg}")
            return False
    except Exception as exc:
        import traceback
        print(f"[event_notifier] ⚠️  Error sending event to backend: {exc}")
        print(f"[event_notifier] ⚠️  Traceback: {traceback.format_exc()}")
        return False


def send_event_to_backend_sync(
    event: Dict[str, Any],
    annotated_frame: np.ndarray,
    agent_id: str,
    agent_name: str,
    camera_id: Optional[str] = None,
    video_timestamp: Optional[str] = None,
    detections: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Synchronous wrapper for send_event_to_backend.
    Uses asyncio.run() to execute the async function.
    """
    import asyncio
    try:
        # Try to get existing event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to use a different approach
                # Create a new thread with a new event loop
                import concurrent.futures
                import threading
                
                result = [None]
                exception = [None]
                
                def run_in_thread():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result[0] = new_loop.run_until_complete(
                            send_event_to_backend(
                                event, annotated_frame, agent_id, agent_name,
                                camera_id, video_timestamp, detections
                            )
                        )
                        new_loop.close()
                    except Exception as e:
                        exception[0] = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join(timeout=5)
                
                if thread.is_alive():
                    print("[event_notifier] ⚠️  Timeout sending event")
                    return False
                
                if exception[0]:
                    raise exception[0]
                return result[0] if result[0] is not None else False
            else:
                return loop.run_until_complete(
                    send_event_to_backend(
                        event, annotated_frame, agent_id, agent_name,
                        camera_id, video_timestamp, detections
                    )
                )
        except RuntimeError:
            # No event loop exists, create a new one
            return asyncio.run(
                send_event_to_backend(
                    event, annotated_frame, agent_id, agent_name,
                    camera_id, video_timestamp, detections
                )
            )
    except Exception as exc:
        print(f"[event_notifier] ⚠️  Error in sync wrapper: {exc}")
        # Fallback: create new event loop
        try:
            return asyncio.run(
                send_event_to_backend(
                    event, annotated_frame, agent_id, agent_name,
                    camera_id, video_timestamp, detections
                )
            )
        except Exception as exc2:
            print(f"[event_notifier] ⚠️  Error in fallback: {exc2}")
            return False

