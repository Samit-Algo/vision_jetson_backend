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


def get_kafka_producer() -> Optional[Any]:
    """
    Get or create Kafka producer (singleton pattern).
    
    Returns:
        KafkaProducer instance if available, None otherwise
    """
    global _kafka_producer
    
    if not KAFKA_AVAILABLE:
        print("[event_notifier] WARNING: kafka-python not available. Install with: pip install kafka-python")
        return None
    
    if _kafka_producer is None:
        try:
            settings = get_settings()
            _kafka_producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                # Reliability settings
                retries=3,
                acks='all',  # Wait for all replicas to acknowledge
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                # Compression to reduce message size (important for base64 images)
                compression_type='gzip',
                # Timeout settings
                request_timeout_ms=30000,
                delivery_timeout_ms=120000,
            )
            print(f"[event_notifier] [SUCCESS] Kafka producer initialized: {settings.kafka_bootstrap_servers}")
        except Exception as e:
            print(f"[event_notifier] [WARNING] Failed to initialize Kafka producer: {e}")
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
    detections: Optional[Dict[str, Any]] = None
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
        }
    }
    
    # Send to Kafka
    try:
        settings = get_settings()
        # Use agent_id as key for partitioning (ensures events from same agent go to same partition)
        future = producer.send(
            settings.kafka_events_topic,
            value=payload,
            key=agent_id.encode('utf-8') if agent_id else None
        )
        
        # Wait for send confirmation (with timeout)
        record_metadata = future.get(timeout=10)
        print(
            f"[event_notifier] [SUCCESS] Event sent to Kafka: "
            f"topic={record_metadata.topic}, "
            f"partition={record_metadata.partition}, "
            f"offset={record_metadata.offset}, "
            f"label={event.get('label')}"
        )
        return True
    except KafkaError as e:
        print(f"[event_notifier] [ERROR] Kafka error sending event: {e}")
        return False
    except Exception as e:
        print(f"[event_notifier] [ERROR] Error sending event to Kafka: {e}")
        import traceback
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
        detections=detections
    )
