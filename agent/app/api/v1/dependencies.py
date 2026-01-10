"""
Dependency Container
====================

Dependency injection container for FastAPI.
Provides singleton instances of repositories and services.
"""
from typing import Dict, Any, Optional

from app.domain.repositories.camera_repository import CameraRepository
from app.domain.repositories.agent_repository import AgentRepository
from app.domain.repositories.device_repository import DeviceRepository
from app.application.services.camera_service import CameraService
from app.application.services.agent_service import AgentService
from app.application.services.device_service import DeviceService
from app.application.services.streaming_service import StreamingService
from app.infrastructure.streaming.agent_ws_fmp4_service import AgentWsFmp4Service
from app.di.container import get_container


# Backward compatibility: Keep old function-based API
# These functions now use the DI container internally
def get_camera_repository() -> CameraRepository:
    """
    Get camera repository instance (singleton).
    
    Returns:
        CameraRepository instance
    """
    container = get_container()
    return container.get(CameraRepository)


def get_camera_service() -> CameraService:
    """
    Get camera service instance (singleton).
    
    Returns:
        CameraService instance
    """
    container = get_container()
    return container.get(CameraService)


def get_streaming_service(shared_store: Dict[str, Any]) -> StreamingService:
    """
    Get streaming service instance (singleton).
    
    Args:
        shared_store: Shared memory dict from multiprocessing.Manager
        
    Returns:
        StreamingService instance
    """
    # StreamingService requires shared_store, so we can't use container for it
    # Keep the old singleton pattern for this special case
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService(shared_store)
    return _streaming_service


_streaming_service: Optional[StreamingService] = None
_agent_ws_service: Optional[AgentWsFmp4Service] = None


def get_agent_ws_service(shared_store: Dict[str, Any]) -> AgentWsFmp4Service:
    """
    Get agent WebSocket fMP4 service instance (singleton).
    
    Args:
        shared_store: Shared memory dict from multiprocessing.Manager
        
    Returns:
        AgentWsFmp4Service instance
    """
    global _agent_ws_service
    if _agent_ws_service is None:
        _agent_ws_service = AgentWsFmp4Service(shared_store)
    return _agent_ws_service


def get_agent_repository() -> AgentRepository:
    """
    Get agent repository instance (singleton).
    
    Returns:
        AgentRepository instance
    """
    container = get_container()
    return container.get(AgentRepository)


def get_agent_service() -> AgentService:
    """
    Get agent service instance (singleton).
    
    Returns:
        AgentService instance
    """
    container = get_container()
    return container.get(AgentService)


def get_device_repository() -> DeviceRepository:
    """
    Get device repository instance (singleton).
    
    Returns:
        DeviceRepository instance
    """
    container = get_container()
    return container.get(DeviceRepository)


def get_device_service() -> DeviceService:
    """
    Get device service instance (singleton).
    
    Returns:
        DeviceService instance
    """
    container = get_container()
    return container.get(DeviceService)
