"""
Streaming Infrastructure
========================

WebRTC streaming infrastructure components.
Handles frame conversion, WebRTC tracks, and signaling.
Also includes WebSocket fMP4 streaming for agent-processed frames.
"""

from app.infrastructure.streaming.agent_ws_fmp4_service import AgentWsFmp4Service

__all__ = [
    "AgentWsFmp4Service",
]
