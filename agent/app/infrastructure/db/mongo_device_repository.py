"""
MongoDB Device Repository
==========================

Concrete implementation of DeviceRepository using MongoDB.
"""
from typing import List, Optional
from pymongo import ReturnDocument

from app.domain.models.device import Device
from app.domain.repositories.device_repository import DeviceRepository
from app.domain.constants.device_fields import DeviceFields
from app.infrastructure.db.mongo_connection import get_mongo_client
from app.utils.datetime_utils import now


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
            device_id=doc[DeviceFields.DEVICE_ID],
            web_backend_url=doc[DeviceFields.WEB_BACKEND_URL],
            user_id=doc[DeviceFields.USER_ID],
            name=doc.get(DeviceFields.NAME),
            status=doc.get(DeviceFields.STATUS, "active"),
            created_at=doc.get(DeviceFields.CREATED_AT, now()),
            updated_at=doc.get(DeviceFields.UPDATED_AT, now()),
        )
    
    def _to_document(self, device: Device) -> dict:
        """Convert Device entity to MongoDB document."""
        return {
            DeviceFields.DEVICE_ID: device.device_id,
            DeviceFields.WEB_BACKEND_URL: device.web_backend_url,
            DeviceFields.USER_ID: device.user_id,
            DeviceFields.NAME: device.name,
            DeviceFields.STATUS: device.status,
            DeviceFields.CREATED_AT: device.created_at,
            DeviceFields.UPDATED_AT: device.updated_at,
        }
    
    def create(self, device: Device) -> Device:
        """Create a new device."""
        device.created_at = now()
        device.updated_at = now()
        
        doc = self._to_document(device)
        self._collection.insert_one(doc)
        
        return device
    
    def update(self, device: Device) -> Device:
        """Update an existing device."""
        device.updated_at = now()
        
        doc = self._to_document(device)
        result = self._collection.find_one_and_update(
            {DeviceFields.DEVICE_ID: device.device_id},
            {"$set": {k: v for k, v in doc.items() if k != DeviceFields.CREATED_AT}},
            return_document=ReturnDocument.AFTER,
        )
        
        if not result:
            raise ValueError(f"Device '{device.device_id}' not found")
        
        return self._to_entity(result)
    
    def find_by_id(self, device_id: str) -> Optional[Device]:
        """Find a device by its ID."""
        doc = self._collection.find_one({DeviceFields.DEVICE_ID: device_id})
        if not doc:
            return None
        return self._to_entity(doc)
    
    def find_by_user_id(self, user_id: str) -> List[Device]:
        """Find all devices for a user."""
        docs = self._collection.find({DeviceFields.USER_ID: user_id}).sort(DeviceFields.CREATED_AT, -1)
        return [self._to_entity(doc) for doc in docs]
    
    def find_all_active(self) -> List[Device]:
        """Find all active devices."""
        docs = self._collection.find({DeviceFields.STATUS: {"$ne": "inactive"}}).sort(DeviceFields.CREATED_AT, -1)
        return [self._to_entity(doc) for doc in docs]
    
    def delete(self, device_id: str) -> bool:
        """Delete (deactivate) a device."""
        result = self._collection.update_one(
            {DeviceFields.DEVICE_ID: device_id},
            {
                "$set": {
                    DeviceFields.STATUS: "inactive",
                    DeviceFields.UPDATED_AT: now(),
                }
            }
        )
        return result.matched_count > 0
    
    def exists(self, device_id: str) -> bool:
        """Check if a device exists."""
        count = self._collection.count_documents({DeviceFields.DEVICE_ID: device_id}, limit=1)
        return count > 0

