"""
Centralized DateTime Utilities
==============================

Provides consistent datetime handling across the entire application.
All datetime operations use the timezone configured in app.core.config.

Functions:
- now(): Returns timezone-aware datetime object
- now_iso(): Returns ISO 8601 string (replaces iso_now)
- parse_iso(): Safely parse ISO 8601 string to datetime
- to_iso(): Convert datetime object to ISO 8601 string

This ensures all datetime operations (create, update, start, stop, etc.)
use the same timezone consistently.
"""
from datetime import datetime, timezone as dt_timezone
from typing import Optional

try:
    import zoneinfo
except ImportError:
    # Python < 3.9 fallback
    try:
        from backports import zoneinfo
    except ImportError:
        zoneinfo = None

from app.core.config import get_settings


def _get_app_timezone() -> dt_timezone:
    """
    Get the application timezone from config.
    Returns timezone object (defaults to UTC if invalid).
    """
    settings = get_settings()
    tz_str = settings.timezone
    
    # Handle UTC explicitly
    if tz_str.upper() == "UTC":
        return dt_timezone.utc
    
    # Try to get timezone from zoneinfo (Python 3.9+)
    if zoneinfo is not None:
        try:
            return zoneinfo.ZoneInfo(tz_str)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            # Fallback to UTC if timezone is invalid
            print(f"[datetime_utils] ⚠️  Invalid timezone '{tz_str}', falling back to UTC")
            return dt_timezone.utc
    
    # Fallback to UTC if zoneinfo is not available
    print(f"[datetime_utils] ⚠️  zoneinfo not available, using UTC")
    return dt_timezone.utc


def now() -> datetime:
    """
    Get current datetime with application-configured timezone.
    
    Returns:
        timezone-aware datetime object
    """
    app_tz = _get_app_timezone()
    return datetime.now(app_tz)


def now_iso() -> str:
    """
    Get current datetime as ISO 8601 string with application-configured timezone.
    
    This replaces the old iso_now() function and ensures consistent timezone usage.
    
    Returns:
        ISO 8601 formatted string (e.g., "2025-12-24T10:30:00+05:30" or "2025-12-24T10:30:00Z")
    """
    dt = now()
    # Format with timezone offset, or 'Z' if UTC
    if dt.tzinfo == dt_timezone.utc:
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return dt.replace(microsecond=0).isoformat()


def parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO 8601 string to datetime object.
    Handles both timezone-aware and naive strings.
    If string is naive, assumes application timezone.
    
    Args:
        dt_str: ISO 8601 string (e.g., "2025-12-24T10:30:00Z" or "2025-12-24T10:30:00+05:30")
    
    Returns:
        timezone-aware datetime object, or None if parsing fails
    """
    if not dt_str:
        return None
    
    try:
        # Replace 'Z' with '+00:00' for parsing
        normalized = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        
        # If timezone-naive, assume application timezone
        if dt.tzinfo is None:
            app_tz = _get_app_timezone()
            dt = dt.replace(tzinfo=app_tz)
        
        return dt
    except Exception:
        return None


def to_iso(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime object to ISO 8601 string.
    If datetime is naive, assumes application timezone.
    
    Args:
        dt: datetime object (timezone-aware or naive)
    
    Returns:
        ISO 8601 formatted string, or None if dt is None
    """
    if dt is None:
        return None
    
    # If naive, assume application timezone
    if dt.tzinfo is None:
        app_tz = _get_app_timezone()
        dt = dt.replace(tzinfo=app_tz)
    
    # Format with timezone offset, or 'Z' if UTC
    if dt.tzinfo == dt_timezone.utc:
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return dt.replace(microsecond=0).isoformat()


# Backward compatibility: alias for iso_now
iso_now = now_iso

