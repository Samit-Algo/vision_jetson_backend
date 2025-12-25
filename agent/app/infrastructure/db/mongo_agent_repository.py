"""
MongoDB Agent Repository
========================

Concrete implementation of AgentRepository using MongoDB.
"""
from typing import List, Optional
from datetime import datetime
import logging
from pymongo.collection import Collection
from pymongo import ReturnDocument
from app.domain.models.agent import Agent, AgentRule
from app.domain.repositories.agent_repository import AgentRepository
from app.domain.constants.agent_fields import AgentFields
from app.infrastructure.db.mongo_connection import get_mongo_client
from app.utils.datetime_utils import now, parse_iso, to_iso

logger = logging.getLogger(__name__)


class MongoAgentRepository(AgentRepository):
    """MongoDB implementation of AgentRepository."""
    
    def __init__(self):
        self._client = get_mongo_client()
        self._collection: Collection = self._client.get_collection("Agents")
    
    def _to_entity(self, doc: dict) -> Agent:
        """Convert MongoDB document to Agent entity."""
        if not doc:
            raise ValueError("Document cannot be empty")
        
        # Convert datetime fields from MongoDB format to ISO strings
        doc = dict(doc)  # Make a copy to avoid modifying original
        
        # Support both old and new field names for backward compatibility
        # Old: agent_id, task_name, start_at, end_at
        # New: id, name, start_time, end_time
        if "agent_id" in doc and AgentFields.ID not in doc:
            doc[AgentFields.ID] = doc["agent_id"]
        if "task_name" in doc and AgentFields.NAME not in doc:
            doc[AgentFields.NAME] = doc["task_name"]
        if "start_at" in doc and AgentFields.START_TIME not in doc:
            doc[AgentFields.START_TIME] = doc["start_at"]
        if "end_at" in doc and AgentFields.END_TIME not in doc:
            doc[AgentFields.END_TIME] = doc["end_at"]
        
        # Handle datetime fields - MongoDB stores as datetime, convert to ISO string for Pydantic
        datetime_fields = [AgentFields.CREATED_AT, AgentFields.UPDATED_AT, AgentFields.START_TIME, AgentFields.END_TIME, "start_at", "end_at"]
        for field in datetime_fields:
            if isinstance(doc.get(field), datetime):
                doc[field] = doc[field].isoformat() + "Z"
        
        # Convert model_ids to model if needed (for backward compatibility)
        if "model_ids" in doc and doc["model_ids"] and AgentFields.MODEL not in doc:
            doc[AgentFields.MODEL] = doc["model_ids"][0] if isinstance(doc["model_ids"], list) and doc["model_ids"] else ""
        
        return Agent(**doc)
    
    def _to_document(self, agent: Agent) -> dict:
        """Convert Agent entity to MongoDB document."""
        # Use model_dump to get all fields
        agent_dict = agent.model_dump(exclude_none=False)
        
        # Rules are already dicts, no need to serialize
        if not agent_dict.get(AgentFields.RULES):
            agent_dict[AgentFields.RULES] = []
        
        
        # Convert ISO string dates back to datetime for MongoDB
        datetime_fields = [AgentFields.CREATED_AT, AgentFields.UPDATED_AT, AgentFields.START_TIME, AgentFields.END_TIME]
        for field in datetime_fields:
            if isinstance(agent_dict.get(field), str):
                parsed_dt = parse_iso(agent_dict[field])
                if parsed_dt:
                    agent_dict[field] = parsed_dt
        
        return agent_dict
    
    def create(self, agent: Agent) -> Agent:
        """Create a new agent in MongoDB."""
        agent_dict = self._to_document(agent)
        self._collection.insert_one(agent_dict)
        return agent
    
    def update(self, agent: Agent) -> Agent:
        """Update an existing agent in MongoDB."""
        agent_dict = self._to_document(agent)
        # Support both old and new field names for query
        result = self._collection.find_one_and_update(
            {"$or": [{AgentFields.ID: agent.id}, {"agent_id": agent.id}]},
            {"$set": agent_dict},
            return_document=ReturnDocument.AFTER
        )
        if not result:
            raise ValueError(f"Agent with ID {agent.id} not found for update.")
        return self._to_entity(result)
    
    def find_by_id(self, agent_id: str) -> Optional[Agent]:
        """Find an agent by id."""
        # Support both old and new field names
        doc = self._collection.find_one({"$or": [{AgentFields.ID: agent_id}, {"agent_id": agent_id}]})
        return self._to_entity(doc) if doc else None
    
    def find_by_camera_id(self, camera_id: str) -> List[Agent]:
        """Find all agents for a specific camera."""
        docs = list(self._collection.find({AgentFields.CAMERA_ID: camera_id}).sort(AgentFields.CREATED_AT, -1))
        return [self._to_entity(doc) for doc in docs]
    
    def find_all_active(self) -> List[Agent]:
        """Find all active agents (PENDING, ACTIVE, RUNNING, or None status - matches web backend)."""
        # Support both old format (lowercase) and new format (uppercase) for backward compatibility
        docs = list(self._collection.find({
            AgentFields.STATUS: {"$in": ["PENDING", "ACTIVE", "RUNNING", "pending", "scheduled", "running", None]}
        }).sort(AgentFields.CREATED_AT, 1))
        return [self._to_entity(doc) for doc in docs]
    
    def delete(self, agent_id: str) -> bool:
        """Delete (cancel) an agent by setting status to 'cancelled'."""
        result = self._collection.update_one(
            {"$or": [{AgentFields.ID: agent_id}, {"agent_id": agent_id}]},
            {"$set": {AgentFields.STATUS: "cancelled", AgentFields.UPDATED_AT: now()}}
        )
        return result.matched_count > 0
    
    def exists(self, agent_id: str) -> bool:
        """Check if an agent exists."""
        count = self._collection.count_documents({"$or": [{AgentFields.ID: agent_id}, {"agent_id": agent_id}]}, limit=1)
        return count > 0

