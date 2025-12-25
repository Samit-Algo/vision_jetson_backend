"""
Agent Service
=============

Application service for agent-related operations.
Orchestrates use cases and coordinates business logic.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.domain.models.agent import Agent
from app.domain.repositories.agent_repository import AgentRepository
from app.domain.repositories.camera_repository import CameraRepository
from app.application.use_cases.agent.register_agent import RegisterAgentUseCase
from app.application.use_cases.agent.get_agent_stream_config import GetAgentStreamConfigUseCase


class AgentService:
    """Application service for agent operations."""
    
    def __init__(self, repository: AgentRepository, camera_repository: CameraRepository):
        self._repository = repository
        self._camera_repository = camera_repository
        self._register_use_case = RegisterAgentUseCase(repository, camera_repository)
        self._get_stream_config_use_case = GetAgentStreamConfigUseCase(repository, camera_repository)
    
    def register_agent(
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
        """Register or update an agent. Field names match web backend."""
        return self._register_use_case.execute(
            id=id,
            name=name,
            camera_id=camera_id,
            model=model,
            fps=fps,
            rules=rules,
            run_mode=run_mode,
            interval_minutes=interval_minutes,
            check_duration_seconds=check_duration_seconds,
            start_time=start_time,
            end_time=end_time,
            zone=zone,
            requires_zone=requires_zone,
            status=status,
            created_at=created_at,
            owner_user_id=owner_user_id,
        )
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by its ID."""
        return self._repository.find_by_id(agent_id)
    
    def list_agents(self, camera_id: Optional[str] = None, status: Optional[str] = None) -> List[Agent]:
        """List agents, optionally filtered by camera_id or status."""
        if camera_id:
            return self._repository.find_by_camera_id(camera_id)
        elif status:
            # Filter active agents by status
            all_active = self._repository.find_all_active()
            return [a for a in all_active if a.status == status]
        else:
            return self._repository.find_all_active()
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove (cancel) an agent."""
        return self._repository.delete(agent_id)
    
    def get_agent_stream_config(self, agent_id: str) -> Dict[str, Any]:
        """Get WebRTC configuration for agent stream."""
        return self._get_stream_config_use_case.execute(agent_id)

