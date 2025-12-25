"""
Test Kafka Producer
==================

Simple test script to verify Kafka producer initialization and message sending.
Run this script to test if Kafka is properly configured and accessible.

Usage:
    python test_kafka_producer.py
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.utils.event_notifier import get_kafka_producer, send_event_to_kafka
import numpy as np

try:
    import cv2
    cv2_available = True
except ImportError:
    cv2_available = False
    print("[WARNING] OpenCV not available, creating dummy frame")


def create_test_frame() -> np.ndarray:
    """Create a test frame (dummy image)."""
    if cv2_available:
        # Create a simple test image: 640x480 with gradient
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for i in range(480):
            frame[i, :] = [i % 256, (i * 2) % 256, (i * 3) % 256]
        return frame
    else:
        # Dummy frame if OpenCV not available
        return np.zeros((480, 640, 3), dtype=np.uint8)


def test_kafka_producer():
    """Test Kafka producer initialization and message sending."""
    print("=" * 60)
    print("Kafka Producer Test")
    print("=" * 60)
    
    # Test 1: Check configuration
    print("\n[1] Checking Kafka configuration...")
    settings = get_settings()
    print(f"   Bootstrap servers: {settings.kafka_bootstrap_servers}")
    print(f"   Events topic: {settings.kafka_events_topic}")
    
    # Test 2: Initialize producer
    print("\n[2] Initializing Kafka producer...")
    producer = get_kafka_producer()
    if not producer:
        print("   [FAILED] Failed to initialize Kafka producer")
        print("   Make sure:")
        print("   - Kafka is running (docker-compose up -d)")
        print("   - kafka-python is installed (pip install kafka-python)")
        print("   - KAFKA_BOOTSTRAP_SERVERS is set correctly")
        return False
    print("   [SUCCESS] Kafka producer initialized successfully")
    
    # Test 3: Send test event
    print("\n[3] Sending test event to Kafka...")
    test_frame = create_test_frame()
    test_event = {
        "label": "test_event",
        "rule_index": 0
    }
    
    success = send_event_to_kafka(
        event=test_event,
        annotated_frame=test_frame,
        agent_id="test-agent-001",
        agent_name="Test Agent",
        camera_id="test-camera-001",
        video_timestamp="0:00:00.000",
        detections={
            "classes": ["person"],
            "scores": [0.95],
            "boxes": [[100, 100, 200, 200]]
        }
    )
    
    if success:
        print("   [SUCCESS] Test event sent successfully!")
        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)
        return True
    else:
        print("   [FAILED] Failed to send test event")
        print("\n" + "=" * 60)
        print("[FAILED] Test failed")
        print("=" * 60)
        return False


if __name__ == "__main__":
    try:
        success = test_kafka_producer()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

