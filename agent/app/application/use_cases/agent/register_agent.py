"""
Register Agent Use Case
========================

Use case for registering or updating an agent configuration.
Field names match web backend structure for consistency.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.domain.models.agent import Agent
from app.domain.repositories.agent_repository import AgentRepository
from app.domain.repositories.camera_repository import CameraRepository
from app.utils.datetime_utils import now


class RegisterAgentUseCase:
    """Use case for registering or updating an agent."""
    
    def __init__(self, repository: AgentRepository, camera_repository: CameraRepository):
        self._repository = repository
        self._camera_repository = camera_repository
    
    def execute(
        self,
        id: str,
        name: str,
        camera_id: str,
        model: str,
        fps: Optional[int] = 5,
        rules: List[Dict[str, Any]] = None,
        run_mode: Optional[str] = "continuous",
        interval_minutes: Optional[int] = None,
        check_duration_seconds: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        zone: Optional[Dict[str, Any]] = None,
        requires_zone: bool = False,
        status: str = "PENDING",
        created_at: Optional[datetime] = None,
        owner_user_id: Optional[str] = None,
    ) -> Agent:
        """
        Register or update an agent configuration.
        
        Field names match web backend structure for consistency.
        
        Args:
            id: Unique identifier for the agent (matches web backend)
            name: Agent name (matches web backend)
            camera_id: Camera ID to monitor
            model: Model name (single string, matches web backend)
            fps: Frames per second to process
            rules: List of rule dictionaries (matches web backend)
            run_mode: Run mode ('continuous' or 'patrol')
            interval_minutes: Patrol interval (minutes, matches web backend)
            check_duration_seconds: Patrol check duration (seconds, matches web backend)
            start_time: When to start the agent (matches web backend)
            end_time: When to stop the agent (matches web backend)
            zone: Zone configuration (matches web backend)
            requires_zone: Whether zone is required (matches web backend)
            status: Agent status (matches web backend)
            created_at: Creation timestamp
            owner_user_id: Owner user ID (matches web backend)
        
        Returns:
            Agent entity
        """
        existing_agent = self._repository.find_by_id(id)
        current_time = now()
        
        # Get camera to derive source_uri (internal field)
        camera = self._camera_repository.find_by_id(camera_id)
        if not camera:
            raise ValueError(f"Camera '{camera_id}' not found. Please register the camera first.")
        
        source_uri = camera.stream_url
        
        # Convert model (single string) to model_ids (list) for internal use
        model_ids = [model] if model else []
        
        # Derive task_type (internal field)
        task_type = "object_detection"
        
        if existing_agent:
            # Update existing agent
            existing_agent.name = name
            existing_agent.camera_id = camera_id
            existing_agent.model = model
            existing_agent.fps = fps or 5
            existing_agent.rules = rules or []
            existing_agent.run_mode = run_mode or "continuous"
            existing_agent.interval_minutes = interval_minutes
            existing_agent.check_duration_seconds = check_duration_seconds
            existing_agent.start_time = start_time
            existing_agent.end_time = end_time
            existing_agent.zone = zone
            existing_agent.requires_zone = requires_zone
            existing_agent.status = status
            existing_agent.owner_user_id = owner_user_id
            existing_agent.source_uri = source_uri
            existing_agent.task_type = task_type
            existing_agent.updated_at = current_time
            return self._repository.update(existing_agent)
        else:
            # Create new agent
            new_agent = Agent(
                id=id,
                name=name,
                camera_id=camera_id,
                model=model,
                fps=fps or 5,
                rules=rules or [],
                run_mode=run_mode or "continuous",
                interval_minutes=interval_minutes,
                check_duration_seconds=check_duration_seconds,
                start_time=start_time,
                end_time=end_time,
                zone=zone,
                requires_zone=requires_zone,
                status=status,
                created_at=created_at or current_time,
                owner_user_id=owner_user_id,
                source_uri=source_uri,
                task_type=task_type,
                updated_at=current_time,
            )
            return self._repository.create(new_agent)
