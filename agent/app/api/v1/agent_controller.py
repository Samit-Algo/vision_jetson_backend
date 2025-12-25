"""
Agent Controller
================

FastAPI controller for agent management.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.application.dto.agent_dto import (
    AgentCreateRequest, AgentResponse, AgentDeleteResponse, AgentStreamConfigResponse,
    WebBackendAgentRequest
)
from app.application.services.agent_service import AgentService
from app.api.v1.dependencies import get_agent_service, get_camera_repository
from app.domain.repositories.camera_repository import CameraRepository
from app.utils.datetime_utils import now, parse_iso

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agents"])


@router.post(
    "/create",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register or update an agent",
    description="Register a new agent or update an existing one. Uses web backend format with same field names."
)
async def create_agent(
    request_data: Dict[str, Any] = Body(...),
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    Register or update an agent.
    
    Accepts web backend format with field names: id, name, camera_id, model, fps, rules, 
    run_mode, interval_minutes, check_duration_seconds, start_time, end_time, zone, 
    requires_zone, status, created_at, owner_user_id.
    
    The agent will be saved to MongoDB and the runner will automatically pick it up on the next poll.
    """
    try:
        # Parse web backend format directly (no conversion)
        from datetime import datetime
        
        # Parse datetime strings if provided
        start_time = None
        if request_data.get("start_time"):
            if isinstance(request_data["start_time"], str):
                try:
                    start_time = datetime.fromisoformat(request_data["start_time"].replace("Z", "+00:00"))
                except Exception:
                    try:
                        start_time = datetime.fromisoformat(request_data["start_time"])
                    except Exception:
                        pass
            elif isinstance(request_data["start_time"], datetime):
                start_time = request_data["start_time"]
        
        end_time = None
        if request_data.get("end_time"):
            if isinstance(request_data["end_time"], str):
                try:
                    end_time = datetime.fromisoformat(request_data["end_time"].replace("Z", "+00:00"))
                except Exception:
                    try:
                        end_time = datetime.fromisoformat(request_data["end_time"])
                    except Exception:
                        pass
            elif isinstance(request_data["end_time"], datetime):
                end_time = request_data["end_time"]
        
        created_at = None
        if request_data.get("created_at"):
            if isinstance(request_data["created_at"], str):
                try:
                    created_at = datetime.fromisoformat(request_data["created_at"].replace("Z", "+00:00"))
                except Exception:
                    try:
                        created_at = datetime.fromisoformat(request_data["created_at"])
                    except Exception:
                        pass
            elif isinstance(request_data["created_at"], datetime):
                created_at = request_data["created_at"]
        
        # Register agent with same field names (no conversion)
        agent = agent_service.register_agent(
            id=request_data.get("id"),
            name=request_data.get("name"),
            camera_id=request_data.get("camera_id"),
            model=request_data.get("model"),
            fps=request_data.get("fps", 5),
            rules=request_data.get("rules", []),
            run_mode=request_data.get("run_mode", "continuous"),
            interval_minutes=request_data.get("interval_minutes"),
            check_duration_seconds=request_data.get("check_duration_seconds"),
            start_time=start_time,
            end_time=end_time,
            zone=request_data.get("zone"),
            requires_zone=request_data.get("requires_zone", False),
            status=request_data.get("status", "PENDING"),
            created_at=created_at,
            owner_user_id=request_data.get("owner_user_id"),
        )
        logger.info(f"Agent {agent.id} registered with {len(agent.rules)} rules")
        
        # Convert agent to response format (using same field names)
        return AgentResponse(
            agent_id=agent.id,  # Map id to agent_id for response (backward compatibility)
            task_name=agent.name,  # Map name to task_name for response
            task_type=agent.task_type or "object_detection",
            camera_id=agent.camera_id,
            source_uri=agent.source_uri or "",
            model_ids=agent.model_ids or [agent.model] if agent.model else [],
            fps=agent.fps or 5,
            run_mode=agent.run_mode or "continuous",
            rules=agent.rules if isinstance(agent.rules, list) else [],
            status=agent.status,
            start_at=agent.start_time or now(),  # Map start_time to start_at
            end_at=agent.end_time or now(),  # Map end_time to end_at
            created_at=agent.created_at or now(),
            updated_at=agent.updated_at or now(),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register agent: {e}")


@router.get(
    "/list",
    response_model=List[AgentResponse],
    summary="List all agents",
    description="Get list of all registered agents, optionally filtered by camera_id or status."
)
async def list_agents(
    camera_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    agent_service: AgentService = Depends(get_agent_service)
) -> List[AgentResponse]:
    """List all agents, optionally filtered by camera_id or status."""
    agents = agent_service.list_agents(camera_id, status_filter)
    return [
        AgentResponse(
            agent_id=agent.id,
            task_name=agent.name,
            task_type=agent.task_type or "object_detection",
            camera_id=agent.camera_id,
            source_uri=agent.source_uri or "",
            model_ids=agent.model_ids or [agent.model] if agent.model else [],
            fps=agent.fps or 5,
            run_mode=agent.run_mode or "continuous",
            rules=agent.rules if isinstance(agent.rules, list) else [],
            status=agent.status,
            start_at=agent.start_time or now(),
            end_at=agent.end_time or now(),
            created_at=agent.created_at or now(),
            updated_at=agent.updated_at or now(),
        )
        for agent in agents
    ]


@router.get(
    "/get/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent by ID",
    description="Get details of a specific agent."
)
async def get_agent(
    agent_id: str,
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """Get a specific agent by its ID."""
    agent = agent_service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found")
    return AgentResponse(
        agent_id=agent.id,
        task_name=agent.name,
        task_type=agent.task_type or "object_detection",
        camera_id=agent.camera_id,
        source_uri=agent.source_uri or "",
        model_ids=agent.model_ids or [agent.model] if agent.model else [],
        fps=agent.fps or 5,
        run_mode=agent.run_mode or "continuous",
        rules=agent.rules if isinstance(agent.rules, list) else [],
        status=agent.status,
        start_at=agent.start_time or now(),
        end_at=agent.end_time or now(),
        created_at=agent.created_at or now(),
        updated_at=agent.updated_at or now(),
    )


@router.delete(
    "/remove/{agent_id}",
    response_model=AgentDeleteResponse,
    summary="Remove an agent",
    description="Remove an agent by setting its status to 'cancelled'. The runner will automatically stop processing."
)
async def remove_agent(
    agent_id: str,
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentDeleteResponse:
    """Remove (cancel) an agent."""
    if not agent_service.remove_agent(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found")
    return AgentDeleteResponse(message=f"Agent '{agent_id}' has been marked as cancelled. Worker will stop on next poll.")


@router.get(
    "/{agent_id}/stream-config",
    response_model=AgentStreamConfigResponse,
    summary="Get agent stream configuration",
    description="Get WebRTC configuration for viewing agent-specific live stream (with bounding boxes)."
)
async def get_agent_stream_config(
    agent_id: str,
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentStreamConfigResponse:
    """Get WebRTC configuration for agent stream."""
    try:
        config = agent_service.get_agent_stream_config(agent_id)
        return AgentStreamConfigResponse(**config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get agent stream config: {e}")

