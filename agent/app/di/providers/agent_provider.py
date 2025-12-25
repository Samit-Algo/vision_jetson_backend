from typing import TYPE_CHECKING
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.repositories.camera_repository import CameraRepository
from ...application.services.agent_service import AgentService

if TYPE_CHECKING:
    from ..base_container import BaseContainer


class AgentProvider:
    """Agent service provider - registers agent-related services"""
    
    @staticmethod
    def register(container: "BaseContainer") -> None:
        """
        Register agent service.
        Service is created with repositories from container.
        """
        # Register AgentService as singleton
        container.register_singleton(
            AgentService,
            AgentService(
                repository=container.get(AgentRepository),
                camera_repository=container.get(CameraRepository)
            )
        )

