from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.database import Base

class Detection(Base):
    __tablename__ = "detections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Camera reference
    camera_id = Column(UUID(as_uuid=True), ForeignKey('cameras.id'), nullable=False, index=True)
    
    # Tracking
    track_id = Column(Integer, nullable=False, index=True)
    global_track_id = Column(String(100), index=True)  # Cross-camera tracking ID
    
    # Detection details
    object_class = Column(String(100), nullable=False, index=True)  # person, car, truck, weapon
    confidence = Column(Float, nullable=False)
    
    # Bounding box
    bbox_x1 = Column(Integer)
    bbox_y1 = Column(Integer)
    bbox_x2 = Column(Integer)
    bbox_y2 = Column(Integer)
    
    # Center position
    center_x = Column(Integer)
    center_y = Column(Integer)
    
    # Additional attributes
    pose = Column(String(50))  # standing, crouching, arms_raised, etc.
    weapon_type = Column(String(100))  # gun, knife, rifle, etc.
    
    # Vehicle-specific
    vehicle_plate = Column(String(20), index=True)
    vehicle_color = Column(String(50))
    vehicle_make = Column(String(100))
    
    # Metadata
    frame_number = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metadata_json = Column(JSON, default={})
    
    # Create composite index for time-series queries
    __table_args__ = (
        Index('idx_detection_time_camera', 'timestamp', 'camera_id'),
        Index('idx_detection_time_class', 'timestamp', 'object_class'),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "camera_id": str(self.camera_id),
            "track_id": self.track_id,
            "global_track_id": self.global_track_id,
            "object_class": self.object_class,
            "confidence": self.confidence,
            "bbox": {
                "x1": self.bbox_x1,
                "y1": self.bbox_y1,
                "x2": self.bbox_x2,
                "y2": self.bbox_y2
            },
            "center": {
                "x": self.center_x,
                "y": self.center_y
            },
            "pose": self.pose,
            "weapon_type": self.weapon_type,
            "vehicle_plate": self.vehicle_plate,
            "vehicle_color": self.vehicle_color,
            "timestamp": self.timestamp.isoformat()
        }