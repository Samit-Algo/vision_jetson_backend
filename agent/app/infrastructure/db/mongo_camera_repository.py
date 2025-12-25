"""
MongoDB Camera Repository
=========================

Concrete implementation of CameraRepository using MongoDB.
"""
from typing import List, Optional
from pymongo import ReturnDocument

from app.domain.models.camera import Camera
from app.domain.repositories.camera_repository import CameraRepository
from app.domain.constants.camera_fields import CameraFields
from app.infrastructure.db.mongo_connection import get_mongo_client
from app.utils.datetime_utils import now


class MongoCameraRepository(CameraRepository):
    """
    MongoDB implementation of CameraRepository.
    
    Handles all camera persistence operations using MongoDB.
    """
    
    COLLECTION_NAME = "cameras"
    
    def __init__(self):
        """Initialize repository with MongoDB client."""
        self._client = get_mongo_client()
        self._collection = self._client.get_collection(self.COLLECTION_NAME)
    
    def _to_entity(self, doc: dict) -> Camera:
        """Convert MongoDB document to Camera entity."""
        # Support both old and new field names for backward compatibility
        camera_id = doc.get(CameraFields.ID) or doc.get("camera_id")
        owner_user_id = doc.get(CameraFields.OWNER_USER_ID) or doc.get("user_id")
        name = doc.get(CameraFields.NAME) or doc.get("camera_name")
        stream_url = doc.get(CameraFields.STREAM_URL) or doc.get("rtsp_url")
        
        return Camera(
            id=camera_id,
            owner_user_id=owner_user_id,
            name=name,
            stream_url=stream_url,
            device_id=doc.get(CameraFields.DEVICE_ID),
            status=doc.get(CameraFields.STATUS, "active"),
            created_at=doc.get(CameraFields.CREATED_AT, now()),
            updated_at=doc.get(CameraFields.UPDATED_AT, now()),
        )
    
    def _to_document(self, camera: Camera) -> dict:
        """Convert Camera entity to MongoDB document."""
        return {
            CameraFields.ID: camera.id,
            CameraFields.OWNER_USER_ID: camera.owner_user_id,
            CameraFields.NAME: camera.name,
            CameraFields.STREAM_URL: camera.stream_url,
            CameraFields.DEVICE_ID: camera.device_id,
            CameraFields.STATUS: camera.status,
            CameraFields.CREATED_AT: camera.created_at,
            CameraFields.UPDATED_AT: camera.updated_at,
        }
    
    def create(self, camera: Camera) -> Camera:
        """Create a new camera."""
        camera.created_at = now()
        camera.updated_at = now()
        
        doc = self._to_document(camera)
        self._collection.insert_one(doc)
        
        return camera
    
    def update(self, camera: Camera) -> Camera:
        """Update an existing camera."""
        camera.updated_at = now()
        
        doc = self._to_document(camera)
        # Support both old and new field names for query
        result = self._collection.find_one_and_update(
            {"$or": [{CameraFields.ID: camera.id}, {"camera_id": camera.id}]},
            {"$set": {k: v for k, v in doc.items() if k != CameraFields.CREATED_AT}},
            return_document=ReturnDocument.AFTER,
        )
        
        if not result:
            raise ValueError(f"Camera '{camera.id}' not found")
        
        return self._to_entity(result)
    
    def find_by_id(self, camera_id: str) -> Optional[Camera]:
        """Find a camera by its ID."""
        # Support both old and new field names
        doc = self._collection.find_one({"$or": [{CameraFields.ID: camera_id}, {"camera_id": camera_id}]})
        if not doc:
            return None
        return self._to_entity(doc)
    
    def find_by_user_id(self, user_id: str) -> List[Camera]:
        """Find all cameras for a user."""
        # Support both old and new field names
        docs = self._collection.find({"$or": [{CameraFields.OWNER_USER_ID: user_id}, {"user_id": user_id}]}).sort(CameraFields.CREATED_AT, -1)
        return [self._to_entity(doc) for doc in docs]
    
    def find_all_active(self) -> List[Camera]:
        """Find all active cameras."""
        docs = self._collection.find({CameraFields.STATUS: {"$ne": "inactive"}}).sort(CameraFields.CREATED_AT, -1)
        return [self._to_entity(doc) for doc in docs]
    
    def delete(self, camera_id: str) -> bool:
        """Delete (deactivate) a camera."""
        result = self._collection.update_one(
            {"$or": [{CameraFields.ID: camera_id}, {"camera_id": camera_id}]},
            {
                "$set": {
                    CameraFields.STATUS: "inactive",
                    CameraFields.UPDATED_AT: now(),
                }
            }
        )
        return result.matched_count > 0
    
    def exists(self, camera_id: str) -> bool:
        """Check if a camera exists."""
        count = self._collection.count_documents({"$or": [{CameraFields.ID: camera_id}, {"camera_id": camera_id}]}, limit=1)
        return count > 0

