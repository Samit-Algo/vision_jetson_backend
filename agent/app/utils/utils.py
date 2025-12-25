"""
Utility helpers
---------------

Role:
- Time helpers for consistent ISO formatting and robust ISO parsing.

Functions:
- iso_now(): 'YYYY-MM-DDTHH:MM:SSZ' (uses centralized timezone from config).
- parse_iso(s): safely parse ISO-8601 string to datetime (returns None on error).

Used by:
- supervisor.py, detector.py, subscriber.py, runner.py for timestamps and heartbeats.

NOTE: These functions now use the centralized datetime utilities from app.utils.datetime_utils
for consistency across the application.
"""
from datetime import datetime
from typing import Optional

# Import from centralized datetime utils
from app.utils.datetime_utils import now_iso, parse_iso as _parse_iso


def iso_now() -> str:
    """
    Return the current time in ISO 8601 format (uses centralized timezone from config).
    
    This function now uses the centralized datetime utility to ensure consistent
    timezone handling across the application.
    """
    return now_iso()


def parse_iso(dt: Optional[str]) -> Optional[datetime]:
    """
    Convert an ISO 8601 string (e.g., 2025-11-10T08:00:00Z) into a datetime object.
    
    This function now uses the centralized datetime utility to ensure consistent
    timezone handling across the application.
    """
    return _parse_iso(dt)


