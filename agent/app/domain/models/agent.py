"""
Agent Model
===========

Domain model representing an automation agent/task.
Field names match web backend structure for consistency.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentRule(BaseModel):
    """A single rule/condition for an agent."""
    type: str = Field(..., description="Rule type (e.g., 'class_presence', 'count_at_least', 'detection_rule')")
    class_name: Optional[str] = Field(None, description="Target class to detect (e.g., 'person', 'car')")
    label: Optional[str] = Field(None, description="Human-readable label for this rule")
    min_count: Optional[int] = Field(None, description="Minimum count required (for count-based rules)")
    confidence: Optional[float] = Field(None, description="Confidence threshold")
    
    class Config:
        allow_population_by_field_name = True
        extra = "allow"  # Allow additional fields from web backend


class Agent(BaseModel):
    """
    Domain model representing an automation agent/task.
    
    Field names match web backend structure for consistency.
    """
    id: str = Field(..., description="Unique identifier for the agent (matches web backend)")
    name: str = Field(..., description="Agent name (matches web backend)")
    camera_id: str = Field(..., description="Camera ID to monitor")
    model: str = Field(..., description="Model name (single model string, matches web backend)")
    fps: Optional[int] = Field(5, description="Frames per second to process")
    rules: List[Dict[str, Any]] = Field(default_factory=list, description="List of rules (matches web backend)")
    run_mode: Optional[str] = Field("continuous", description="Run mode: 'continuous' or 'patrol'")
    interval_minutes: Optional[int] = Field(None, description="Patrol interval (minutes, matches web backend)")
    check_duration_seconds: Optional[int] = Field(None, description="Patrol check duration (seconds, matches web backend)")
    start_time: Optional[datetime] = Field(None, description="Start time (matches web backend)")
    end_time: Optional[datetime] = Field(None, description="End time (matches web backend)")
    zone: Optional[Dict[str, Any]] = Field(None, description="Zone configuration (matches web backend)")
    requires_zone: bool = Field(False, description="Whether zone is required (matches web backend)")
    status: str = Field("PENDING", description="Current status (matches web backend)")
    created_at: Optional[datetime] = Field(None, description="Timestamp when the agent was created")
    owner_user_id: Optional[str] = Field(None, description="Owner user ID (matches web backend)")
    
    # Internal fields (not in web backend)
    task_type: Optional[str] = Field("object_detection", description="Type of task (internal, derived)")
    source_uri: Optional[str] = Field(None, description="RTSP URL (internal, derived from camera)")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp (internal)")
    
    def is_active(self) -> bool:
        """Check if agent is in an active state (matches web backend status values)."""
        return self.status in ["PENDING", "ACTIVE", "RUNNING", "pending", "scheduled", "running", None]
