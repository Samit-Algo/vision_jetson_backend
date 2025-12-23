"""
MongoDB Device Repository Implementation
=========================================

Concrete implementation of DeviceRepository using MongoDB.
"""
from datetime import datetime
from typing import List, Optional
from pymongo import ReturnDocument

from agent.domain.entities.device import Device
from agent.domain.repositories.device_repository import DeviceRepository
from agent.infrastructure.database.mongo_client import get_mongo_client


class MongoDeviceRepository(DeviceRepository):
    """
    MongoDB implementation of DeviceRepository.
    
    Handles all device persistence operations using MongoDB.
    """
    
    COLLECTION_NAME = "devices"
    
    def __init__(self):
        """Initialize repository with MongoDB client."""
        self._client = get_mongo_client()
        self._collection = self._client.get_collection(self.COLLECTION_NAME)
    
    def _to_entity(self, doc: dict) -> Device:
        """Convert MongoDB document to Device entity."""
        return Device(
            device_id=doc["device_id"],
            web_backend_url=doc["web_backend_url"],
            user_id=doc["user_id"],
            name=doc.get("name"),
            status=doc.get("status", "active"),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
        )
    
    def _to_document(self, device: Device) -> dict:
        """Convert Device entity to MongoDB document."""
        return {
            "device_id": device.device_id,
            "web_backend_url": device.web_backend_url,
            "user_id": device.user_id,
            "name": device.name,
            "status": device.status,
            "created_at": device.created_at,
            "updated_at": device.updated_at,
        }
    
    def create(self, device: Device) -> Device:
        """Create a new device."""
        device.created_at = datetime.utcnow()
        device.updated_at = datetime.utcnow()
        
        doc = self._to_document(device)
        self._collection.insert_one(doc)
        
        return device
    
    def update(self, device: Device) -> Device:
        """Update an existing device."""
        device.updated_at = datetime.utcnow()
        
        doc = self._to_document(device)
        result = self._collection.find_one_and_update(
            {"device_id": device.device_id},
            {"$set": {k: v for k, v in doc.items() if k != "created_at"}},
            return_document=ReturnDocument.AFTER,
        )
        
        if not result:
            raise ValueError(f"Device '{device.device_id}' not found")
        
        return self._to_entity(result)
    
    def find_by_id(self, device_id: str) -> Optional[Device]:
        """Find a device by its ID."""
        doc = self._collection.find_one({"device_id": device_id})
        if not doc:
            return None
        return self._to_entity(doc)
    
    def find_by_user_id(self, user_id: str) -> List[Device]:
        """Find all devices for a user."""
        docs = self._collection.find({"user_id": user_id}).sort("created_at", -1)
        return [self._to_entity(doc) for doc in docs]
    
    def find_all_active(self) -> List[Device]:
        """Find all active devices."""
        docs = self._collection.find({"status": {"$ne": "inactive"}}).sort("created_at", -1)
        return [self._to_entity(doc) for doc in docs]
    
    def delete(self, device_id: str) -> bool:
        """Delete (deactivate) a device."""
        result = self._collection.update_one(
            {"device_id": device_id},
            {
                "$set": {
                    "status": "inactive",
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        return result.matched_count > 0
    
    def exists(self, device_id: str) -> bool:
        """Check if a device exists."""
        count = self._collection.count_documents({"device_id": device_id}, limit=1)
        return count > 0

