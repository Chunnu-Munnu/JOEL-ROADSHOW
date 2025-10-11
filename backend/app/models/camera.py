from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.database import Base

class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    
    # Connection details
    stream_url = Column(String(512), nullable=False)  # RTSP/HTTP/Webcam ID
    stream_type = Column(String(50), default="rtsp")  # rtsp, http, webcam, mobile
    
    # Geolocation
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, default=0.0)
    address = Column(String(512))
    
    # Coverage area
    coverage_radius = Column(Float, default=100.0)  # meters
    field_of_view = Column(Float, default=90.0)  # degrees
    camera_angle = Column(Float, default=0.0)  # orientation in degrees
    
    # Zone assignment
    zone_name = Column(String(255))  # e.g., "Perimeter North", "Gate 5"
    zone_type = Column(String(100))  # public, restricted, high_security
    restricted_zone = Column(Boolean, default=False)
    
    # Status
    status = Column(String(50), default="online")  # online, offline, maintenance
    is_active = Column(Boolean, default=True)
    
    # Technical specs
    resolution_width = Column(Integer, default=1280)
    resolution_height = Column(Integer, default=720)
    fps = Column(Integer, default=10)
    
    # Metadata
    installation_date = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "stream_url": self.stream_url,
            "stream_type": self.stream_type,
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude,
                "address": self.address
            },
            "coverage": {
                "radius": self.coverage_radius,
                "fov": self.field_of_view,
                "angle": self.camera_angle
            },
            "zone": {
                "name": self.zone_name,
                "type": self.zone_type,
                "restricted": self.restricted_zone
            },
            "status": self.status,
            "is_active": self.is_active,
            "resolution": f"{self.resolution_width}x{self.resolution_height}",
            "fps": self.fps,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }