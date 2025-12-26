"""
Event Notifier
==============

Utility to send event notifications with annotated frames to Kafka.
Events are published to Kafka topic for consumption by web backend.
"""
import base64
import json
from typing import Dict, Any, Optional
from datetime import datetime
import numpy as np

from app.utils.datetime_utils import now_iso
from app.core.config import get_settings

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer = None  # type: ignore
    KafkaError = Exception  # type: ignore


# Singleton Kafka producer instance
_kafka_producer: Optional[Any] = None


def test_kafka_connection(producer: Any) -> bool:
    """
    Test Kafka connection by attempting to get metadata.
    
    Args:
        producer: KafkaProducer instance
    
    Returns:
        True if connection is working, False otherwise
    """
    try:
        # Try to get cluster metadata (this tests the connection)
        metadata = producer.list_topics(timeout=5)
        return True
    except Exception as e:
        print(f"[event_notifier] ⚠️  Kafka connection test failed: {e}")
        return False


def get_kafka_producer() -> Optional[Any]:
    """
    Get or create Kafka producer (singleton pattern).
    Tests connection to verify Kafka is running.
    
    Returns:
        KafkaProducer instance if available, None otherwise
    """
    global _kafka_producer
    
    if not KAFKA_AVAILABLE:
        print("[event_notifier] ❌ WARNING: kafka-python not available. Install with: pip install kafka-python")
        return None
    
    if _kafka_producer is None:
        try:
            settings = get_settings()
            print(f"[event_notifier] 🔌 Attempting to connect to Kafka: {settings.kafka_bootstrap_servers}")
            
            _kafka_producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                # Reliability settings
                retries=3,
                acks='all',  # Wait for all replicas to acknowledge
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                # Compression to reduce message size (important for base64 images)
                compression_type='gzip',
                # Message size settings (for large video chunks)
                max_request_size=10485760,  # 10MB (default is 1MB)
                # Timeout settings
                request_timeout_ms=30000,
                delivery_timeout_ms=120000,
            )
            
            # Test connection
            print("[event_notifier] 🔍 Testing Kafka connection...")
            if test_kafka_connection(_kafka_producer):
                print(f"[event_notifier] ✅ [SUCCESS] Kafka producer initialized and connected: {settings.kafka_bootstrap_servers}")
                print(f"[event_notifier] 📡 Topic: {settings.kafka_events_topic}")
            else:
                print(f"[event_notifier] ⚠️  [WARNING] Kafka producer created but connection test failed")
                print(f"[event_notifier] ⚠️  Kafka may not be running or unreachable")
        except Exception as e:
            print(f"[event_notifier] ❌ [ERROR] Failed to initialize Kafka producer: {e}")
            import traceback
            print(f"[event_notifier] Traceback: {traceback.format_exc()}")
            return None
    
    return _kafka_producer


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


def send_event_to_kafka(
    event: Dict[str, Any],
    annotated_frame: np.ndarray,
    agent_id: str,
    agent_name: str,
    camera_id: Optional[str] = None,
    video_timestamp: Optional[str] = None,
    detections: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> bool:
    """
    Send event notification with annotated frame to Kafka topic.
    
    Args:
        event: Event dict with 'label' and optionally 'rule_index'
        annotated_frame: Frame with bounding boxes drawn (numpy array)
        agent_id: Agent identifier
        agent_name: Agent name
        camera_id: Camera identifier (optional)
        video_timestamp: Video timestamp string (optional)
        detections: Detection details (optional)
        session_id: Session identifier for linking to video chunks (optional)
    
    Returns:
        True if sent successfully, False otherwise
    """
    producer = get_kafka_producer()
    if not producer:
        print("[event_notifier] [WARNING] Kafka producer not available, skipping event notification")
        return False
    
    # Encode frame to base64
    frame_base64 = encode_frame_to_base64(annotated_frame)
    if not frame_base64:
        print("[event_notifier] [WARNING] Failed to encode frame, skipping event notification")
        return False
    
    # Fetch owner_user_id and device_id from camera if camera_id is provided
    owner_user_id = None
    device_id = None
    
    if camera_id:
        try:
            # Import repositories (lazy import to avoid circular dependencies)
            from app.infrastructure.db.mongo_camera_repository import MongoCameraRepository
            
            camera_repo = MongoCameraRepository()
            camera = camera_repo.find_by_id(camera_id)
            
            if camera:
                owner_user_id = camera.owner_user_id
                device_id = camera.device_id
        except Exception as e:
            print(f"[event_notifier] [WARNING] Error fetching camera details: {e}")
            # Continue without owner_user_id and device_id
    
    # Build payload (same structure as before for backward compatibility)
    payload = {
        "event": {
            "label": event.get("label", "Unknown"),
            "rule_index": event.get("rule_index"),
            "timestamp": now_iso(),
        },
        "agent": {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "camera_id": camera_id,
        },
        "camera": {
            "owner_user_id": owner_user_id,
            "device_id": device_id,
        },
        "frame": {
            "image_base64": frame_base64,
            "format": "jpeg",
        },
        "metadata": {
            "video_timestamp": video_timestamp,
            "detections": serialize_for_json(detections) if detections else None,
            "session_id": session_id,  # Link to video chunks
        }
    }
    
    # Send to Kafka
    try:
        settings = get_settings()
        event_label = event.get("label", "Unknown")
        print(f"[event_notifier] 📤 Sending event to Kafka: label='{event_label}' | agent={agent_id} | session_id={session_id}")
        
        # Use agent_id as key for partitioning (ensures events from same agent go to same partition)
        future = producer.send(
            settings.kafka_events_topic,
            value=payload,
            key=agent_id.encode('utf-8') if agent_id else None
        )
        
        # Wait for send confirmation (with timeout)
        record_metadata = future.get(timeout=10)
        print(
            f"[event_notifier] ✅ [SUCCESS] Event added successfully to Kafka!\n"
            f"   ├─ Event: '{event_label}'\n"
            f"   ├─ Agent: {agent_id}\n"
            f"   ├─ Session ID: {session_id}\n"
            f"   ├─ Topic: {record_metadata.topic}\n"
            f"   ├─ Partition: {record_metadata.partition}\n"
            f"   └─ Offset: {record_metadata.offset}"
        )
        return True
    except KafkaError as e:
        print(f"[event_notifier] ❌ [ERROR] Kafka error sending event: {e}")
        print(f"[event_notifier] ⚠️  Event NOT sent - check Kafka connection")
        return False
    except Exception as e:
        print(f"[event_notifier] ❌ [ERROR] Error sending event to Kafka: {e}")
        print(f"[event_notifier] ⚠️  Event NOT sent - check Kafka connection")
        import traceback
        print(f"[event_notifier] Traceback: {traceback.format_exc()}")
        return False


def send_event_video_to_kafka(
    session_id: str,
    chunk_number: int,
    is_final_chunk: bool,
    chunk_start_time: datetime,
    chunk_end_time: datetime,
    chunk_duration_seconds: float,
    event_label: str,
    rule_index: int,
    agent_id: str,
    agent_name: str,
    camera_id: Optional[str] = None,
    video_base64: Optional[str] = None,
    fps: int = 5,
    resolution: tuple = (1280, 720)
) -> bool:
    """
    Send event video chunk to Kafka topic.
    
    This function sends video chunks created from event sessions.
    Each chunk represents a time-sliced portion of an event session.
    
    Args:
        session_id: Unique session identifier
        chunk_number: Sequential chunk number (0, 1, 2, ...)
        is_final_chunk: True if this is the final chunk of the session
        chunk_start_time: Start time of this chunk
        chunk_end_time: End time of this chunk
        chunk_duration_seconds: Duration of chunk in seconds
        event_label: Event label (e.g., "person without helmet")
        rule_index: Rule index that triggered the event
        agent_id: Agent identifier
        agent_name: Agent name
        camera_id: Camera identifier (optional)
        video_base64: Base64-encoded video data
        fps: Video frames per second
        resolution: Video resolution (width, height)
    
    Returns:
        True if sent successfully, False otherwise
    """
    producer = get_kafka_producer()
    if not producer:
        print("[event_notifier] [WARNING] Kafka producer not available, skipping video chunk")
        return False
    
    if not video_base64:
        print("[event_notifier] [WARNING] No video data provided, skipping video chunk")
        return False
    
    # Fetch owner_user_id and device_id from camera if camera_id is provided
    owner_user_id = None
    device_id = None
    
    if camera_id:
        try:
            from app.infrastructure.db.mongo_camera_repository import MongoCameraRepository
            
            camera_repo = MongoCameraRepository()
            camera = camera_repo.find_by_id(camera_id)
            
            if camera:
                owner_user_id = camera.owner_user_id
                device_id = camera.device_id
        except Exception as e:
            print(f"[event_notifier] [WARNING] Error fetching camera details: {e}")
    
    # Build payload for video chunk
    payload = {
        "type": "event_video",
        "session_id": session_id,
        "sequence_number": chunk_number,
        "is_final_chunk": is_final_chunk,
        "chunk": {
            "chunk_number": chunk_number,
            "start_time": serialize_for_json(chunk_start_time),
            "end_time": serialize_for_json(chunk_end_time),
            "duration_seconds": chunk_duration_seconds,
        },
        "event": {
            "label": event_label,
            "rule_index": rule_index,
            "timestamp": serialize_for_json(chunk_start_time),
        },
        "agent": {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "camera_id": camera_id,
        },
        "camera": {
            "owner_user_id": owner_user_id,
            "device_id": device_id,
        },
        "video": {
            "data_base64": video_base64,
            "format": "mp4",
            "fps": fps,
            "resolution": {
                "width": resolution[0],
                "height": resolution[1],
            },
        },
        "metadata": {
            "session_id": session_id,
            "chunk_sequence": chunk_number,
        }
    }
    
    # Send to Kafka
    try:
        settings = get_settings()
        video_size_mb = len(video_base64) * 3 / 4 / (1024 * 1024)  # Approximate size in MB
        print(
            f"[event_notifier] 📤 Sending video chunk to Kafka: "
            f"session={session_id} | chunk={chunk_number} | final={is_final_chunk} | "
            f"size≈{video_size_mb:.2f}MB"
        )
        
        # Use session_id as key for partitioning (ensures chunks from same session are ordered)
        future = producer.send(
            settings.kafka_events_topic,
            value=payload,
            key=session_id.encode('utf-8') if session_id else None
        )
        
        # Wait for send confirmation (with timeout)
        record_metadata = future.get(timeout=30)  # Longer timeout for video chunks
        print(
            f"[event_notifier] ✅ [SUCCESS] Video chunk added successfully to Kafka!\n"
            f"   ├─ Session ID: {session_id}\n"
            f"   ├─ Chunk Number: {chunk_number}\n"
            f"   ├─ Is Final: {is_final_chunk}\n"
            f"   ├─ Event: '{event_label}'\n"
            f"   ├─ Topic: {record_metadata.topic}\n"
            f"   ├─ Partition: {record_metadata.partition}\n"
            f"   ├─ Offset: {record_metadata.offset}\n"
            f"   └─ Size: ≈{video_size_mb:.2f}MB"
        )
        return True
    except KafkaError as e:
        error_str = str(e)
        if "MessageSizeTooLargeError" in error_str or "MessageSizeTooLarge" in error_str:
            print(f"[event_notifier] ❌ [ERROR] Video chunk too large for Kafka!")
            print(f"[event_notifier] ⚠️  Message size: ≈{video_size_mb:.2f}MB exceeds Kafka limit")
            print(f"[event_notifier] 💡 Solution: Increase Kafka server-side limits:")
            print(f"[event_notifier]    1. Set message.max.bytes in Kafka server config (e.g., 10485760 for 10MB)")
            print(f"[event_notifier]    2. Set replica.fetch.max.bytes in Kafka server config")
            print(f"[event_notifier]    3. Set fetch.message.max.bytes in consumer config")
            print(f"[event_notifier]    4. Restart Kafka brokers after config changes")
            print(f"[event_notifier] ⚠️  Video saved locally but NOT sent to Kafka")
        else:
            print(f"[event_notifier] ❌ [ERROR] Kafka error sending video chunk: {e}")
            print(f"[event_notifier] ⚠️  Video chunk NOT sent - check Kafka connection")
        return False
    except Exception as e:
        error_str = str(e)
        if "MessageSizeTooLargeError" in error_str or "MessageSizeTooLarge" in error_str or "too large" in error_str.lower():
            print(f"[event_notifier] ❌ [ERROR] Video chunk too large for Kafka!")
            print(f"[event_notifier] ⚠️  Message size: ≈{video_size_mb:.2f}MB exceeds Kafka limit")
            print(f"[event_notifier] 💡 Solution: Increase Kafka server-side limits (see above)")
        else:
            print(f"[event_notifier] ❌ [ERROR] Error sending video chunk to Kafka: {e}")
        print(f"[event_notifier] ⚠️  Video chunk NOT sent - check Kafka connection")
        import traceback
        print(f"[event_notifier] Traceback: {traceback.format_exc()}")
        return False


def send_event_to_backend_sync(
    event: Dict[str, Any],
    annotated_frame: np.ndarray,
    agent_id: str,
    agent_name: str,
    camera_id: Optional[str] = None,
    video_timestamp: Optional[str] = None,
    detections: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> bool:
    """
    Send event notification to Kafka (synchronous).
    
    This function maintains backward compatibility with the old HTTP-based API.
    It now uses Kafka instead of HTTP POST requests.
    
    Args:
        event: Event dict with 'label' and optionally 'rule_index'
        annotated_frame: Frame with bounding boxes drawn (numpy array)
        agent_id: Agent identifier
        agent_name: Agent name
        camera_id: Camera identifier (optional)
        video_timestamp: Video timestamp string (optional)
        detections: Detection details (optional)
        session_id: Session identifier for linking to video chunks (optional)
    
    Returns:
        True if sent successfully, False otherwise
    """
    return send_event_to_kafka(
        event=event,
        annotated_frame=annotated_frame,
        agent_id=agent_id,
        agent_name=agent_name,
        camera_id=camera_id,
        video_timestamp=video_timestamp,
        detections=detections,
        session_id=session_id
    )
