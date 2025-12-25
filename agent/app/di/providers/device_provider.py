from typing import TYPE_CHECKING
from ...domain.repositories.device_repository import DeviceRepository
from ...application.services.device_service import DeviceService

if TYPE_CHECKING:
    from ..base_container import BaseContainer


class DeviceProvider:
    """Device service provider - registers device-related services"""
    
    @staticmethod
    def register(container: "BaseContainer") -> None:
        """
        Register device service.
        Service is created with repository from container.
        """
        # Register DeviceService as singleton
        container.register_singleton(
            DeviceService,
            DeviceService(
                device_repository=container.get(DeviceRepository)
            )
        )

