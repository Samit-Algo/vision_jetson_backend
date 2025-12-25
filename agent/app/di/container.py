# Local application imports
from .base_container import BaseContainer
from .providers import (
    CameraProvider,
    DeviceProvider,
    DatabaseProvider,
    RepositoryProvider,
    AgentProvider,
)


class DIContainer(BaseContainer):
    """
    Main dependency injection container.
    Composes all providers in the correct order.
    
    Registration order is important:
    1. Database connections (DatabaseProvider)
    2. Repositories (RepositoryProvider) - depends on database
    3. Services (CameraProvider, AgentProvider, DeviceProvider) - depend on repositories
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.setup()
    
    def setup(self) -> None:
        """
        Setup dependency registrations by composing all providers.
        Order matters: database → repositories → services
        """
        # Step 1: Register database connections (foundation)
        DatabaseProvider.register(self)
        
        # Step 2: Register repositories (depends on database)
        RepositoryProvider.register(self)
        
        # Step 3: Register services (depends on repositories)
        CameraProvider.register(self)
        AgentProvider.register(self)
        DeviceProvider.register(self)
        
        # Future providers can be added here:
        # StreamingProvider.register(self)
        # NotificationProvider.register(self)


# Global container instance (singleton pattern)
_container: DIContainer | None = None


def get_container() -> DIContainer:
    """
    Get the global DI container instance (singleton pattern)
    
    Returns:
        DIContainer instance with all dependencies registered
    """
    global _container
    if _container is None:
        _container = DIContainer()
    return _container

