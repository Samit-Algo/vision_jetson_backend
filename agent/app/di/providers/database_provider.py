from typing import TYPE_CHECKING
from ...infrastructure.db.mongo_connection import get_mongo_client

if TYPE_CHECKING:
    from ..base_container import BaseContainer


class DatabaseProvider:
    """Centralized database connection provider - single source of truth for all DB connections"""
    
    @staticmethod
    def register(container: "BaseContainer") -> None:
        """
        Register all database connections in the container.
        This is the ONLY place where database connections are registered.
        Change database here, and all repositories automatically get the new connection.
        """
        # Get MongoDB client manager instance
        mongo_client = get_mongo_client()
        
        # Register MongoDB client as singleton
        container.register_singleton("mongo_client", mongo_client)
        
        # Future database connections can be added here:
        # container.register_singleton("postgres_client", get_postgres_client())

