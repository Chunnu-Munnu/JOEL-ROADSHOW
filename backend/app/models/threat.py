from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Index, Boolean ,Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.database import Base

class Threat(Base):
    __tablename__ = "threats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference
    camera_id = Column(UUID(as_uuid=True), ForeignKey('cameras.id'), nullable=False, index=True)
    detection_id = Column(UUID(as_uuid=True), ForeignKey('detections.id'))
    
    # Tracking
    track_id = Column(Integer, nullable=False, index=True)
    global_track_id = Column(String(100), index=True)
    
    # Threat details
    threat_type = Column(String(100), nullable=False, index=True)  # weapon, loitering, unauthorized_vehicle, etc.
    threat_score = Column(Float, nullable=False, index=True)
    threat_level = Column(String(50), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    
    # Behavior analysis
    behavior = Column(String(255))  # loitering, crouching, arms_raised, rapid_movement
    behavior_duration = Column(Float)  # seconds
    
    # Vehicle-specific threats
    unauthorized_plate = Column(String(20))
    restricted_zone_entry = Column(Boolean, default=False)
    
    # Location
    position_x = Column(Integer)
    position_y = Column(Integer)
    zone_name = Column(String(255))
    
    # Evidence
    video_clip_url = Column(String(512))  # MinIO/S3 URL
    snapshot_url = Column(String(512))
    
    # Status
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(255))
    acknowledged_at = Column(DateTime)
    
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(255))
    resolved_at = Column(DateTime)
    resolution_notes = Column(String(1024))
    
    # Alerts sent
    alert_sent_sms = Column(Boolean, default=False)
    alert_sent_email = Column(Boolean, default=False)
    alert_sent_dashboard = Column(Boolean, default=False)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metadata_json = Column(JSON, default={})
    
    __table_args__ = (
        Index('idx_threat_time_level', 'timestamp', 'threat_level'),
        Index('idx_threat_time_camera', 'timestamp', 'camera_id'),
        Index('idx_threat_unresolved', 'is_resolved', 'threat_level'),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "camera_id": str(self.camera_id),
            "track_id": self.track_id,
            "global_track_id": self.global_track_id,
            "threat_type": self.threat_type,
            "threat_score": self.threat_score,
            "threat_level": self.threat_level,
            "behavior": self.behavior,
            "behavior_duration": self.behavior_duration,
            "unauthorized_plate": self.unauthorized_plate,
            "restricted_zone_entry": self.restricted_zone_entry,
            "position": {
                "x": self.position_x,
                "y": self.position_y
            },
            "zone_name": self.zone_name,
            "video_clip_url": self.video_clip_url,
            "snapshot_url": self.snapshot_url,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "is_resolved": self.is_resolved,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "timestamp": self.timestamp.isoformat(),
            "alerts_sent": {
                "sms": self.alert_sent_sms,
                "email": self.alert_sent_email,
                "dashboard": self.alert_sent_dashboard
            }
        }