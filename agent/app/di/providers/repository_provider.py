from typing import TYPE_CHECKING
from ...domain.repositories.camera_repository import CameraRepository
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.repositories.device_repository import DeviceRepository
from ...infrastructure.db.mongo_camera_repository import MongoCameraRepository
from ...infrastructure.db.mongo_agent_repository import MongoAgentRepository
from ...infrastructure.db.mongo_device_repository import MongoDeviceRepository

if TYPE_CHECKING:
    from ..base_container import BaseContainer


class RepositoryProvider:
    """Repository registration provider - wires domain interfaces to infrastructure implementations"""
    
    @staticmethod
    def register(container: "BaseContainer") -> None:
        """
        Register all repository implementations.
        Gets database client from database provider and creates repository instances.
        """
        # Get MongoDB client from database provider
        mongo_client = container.get("mongo_client")
        
        # Register repository implementations
        # Domain interfaces -> Infrastructure implementations
        container.register_singleton(
            CameraRepository,
            MongoCameraRepository()
        )
        
        container.register_singleton(
            AgentRepository,
            MongoAgentRepository()
        )
        
        container.register_singleton(
            DeviceRepository,
            MongoDeviceRepository()
        )

