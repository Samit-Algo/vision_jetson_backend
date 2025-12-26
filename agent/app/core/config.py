# Standard library imports
import os
from typing import Final, Optional
from dotenv import load_dotenv


class Settings:
    """
    Application settings loaded from environment variables.
    
    This class centralizes all configuration settings for the application.
    All settings are loaded from environment variables with sensible defaults.
    """
    
    def __init__(self) -> None:
        # Load environment variables from .env file
        load_dotenv()
        
        # Timezone Configuration
        # Default to UTC, but can be set via TIMEZONE env var (e.g., "UTC", "America/New_York", "Asia/Kolkata")
        self.timezone: Final[str] = os.getenv("TIMEZONE", "UTC")
        
        # Database Configuration
        self.mongo_uri: Final[str] = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.mongo_database_name: Final[str] = os.getenv("DB_NAME", "algo_vision")
        
        # Agent Runner Configuration
        self.agent_poll_interval_sec: Final[int] = int(
            os.getenv("AGENT_POLL_INTERVAL_SEC", "5")
        )
        
        # Web Backend Configuration (for Jetson backend to connect back)
        self.web_backend_url: Final[str] = os.getenv(
            "WEB_BACKEND_URL",
            "http://localhost:8000"
        )
        
        # AWS TURN Server Configuration (for WebRTC streaming)
        self.aws_turn_ip: Final[Optional[str]] = os.getenv("AWS_TURN_IP")
        self.aws_turn_port: Final[Optional[str]] = os.getenv("AWS_TURN_PORT")
        self.aws_turn_user: Final[Optional[str]] = os.getenv("AWS_TURN_USER")
        self.aws_turn_pass: Final[Optional[str]] = os.getenv("AWS_TURN_PASS")
        
        # Kafka Configuration
        self.kafka_bootstrap_servers: Final[str] = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092"
        )
        self.kafka_events_topic: Final[str] = os.getenv(
            "KAFKA_EVENTS_TOPIC",
            "vision-events"
        )
        
        # Collection Names
        self.cameras_collection: Final[str] = os.getenv("CAMERAS_COLLECTION", "cameras")
        self.agents_collection: Final[str] = os.getenv("AGENTS_COLLECTION", "Agents")
        self.devices_collection: Final[str] = os.getenv("DEVICES_COLLECTION", "devices")
        
        # Event Session Configuration
        self.event_session_timeout_seconds: Final[int] = int(
            os.getenv("EVENT_SESSION_TIMEOUT_SECONDS", "30")
        )
        self.event_video_chunk_duration_seconds: Final[int] = int(
            os.getenv("EVENT_VIDEO_CHUNK_DURATION_SECONDS", "300")  # 5 minutes
        )
        self.event_session_check_interval_seconds: Final[int] = int(
            os.getenv("EVENT_SESSION_CHECK_INTERVAL_SECONDS", "5")
        )
        self.event_video_fps: Final[int] = int(
            os.getenv("EVENT_VIDEO_FPS", "5")
        )
        self.event_video_resolution_width: Final[int] = int(
            os.getenv("EVENT_VIDEO_RESOLUTION_WIDTH", "1280")
        )
        self.event_video_resolution_height: Final[int] = int(
            os.getenv("EVENT_VIDEO_RESOLUTION_HEIGHT", "720")
        )
        # Event Video File Storage
        self.event_video_save_directory: Final[str] = os.getenv(
            "EVENT_VIDEO_SAVE_DIRECTORY",
            os.path.join(os.getcwd(), "event_videos")  # Default: ./event_videos
        )
        self.event_video_save_enabled: Final[bool] = os.getenv(
            "EVENT_VIDEO_SAVE_ENABLED", "true"
        ).lower() in ("true", "1", "yes")


# Global settings instance (singleton pattern)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings (singleton pattern)
    
    Returns:
        Settings instance with all configuration values
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

