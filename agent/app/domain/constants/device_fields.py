"""Constants for Device model field names"""


class DeviceFields:
    """Field name constants for Device model"""
    DEVICE_ID = "device_id"
    WEB_BACKEND_URL = "web_backend_url"
    USER_ID = "user_id"
    NAME = "name"
    STATUS = "status"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    
    # MongoDB specific
    MONGO_ID = "_id"  # MongoDB's internal _id field

