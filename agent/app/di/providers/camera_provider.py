from typing import TYPE_CHECKING
from ...domain.repositories.camera_repository import CameraRepository
from ...application.services.camera_service import CameraService

if TYPE_CHECKING:
    from ..base_container import BaseContainer


class CameraProvider:
    """Camera service provider - registers camera-related services"""
    
    @staticmethod
    def register(container: "BaseContainer") -> None:
        """
        Register camera service.
        Service is created with repository from container.
        """
        # Register CameraService as singleton
        container.register_singleton(
            CameraService,
            CameraService(
                camera_repository=container.get(CameraRepository)
            )
        )

