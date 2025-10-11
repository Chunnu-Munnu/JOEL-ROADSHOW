from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.database import Base

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # License plate info
    license_plate = Column(String(20), nullable=False, unique=True, index=True)
    plate_state = Column(String(5))  # e.g., "KA" for Karnataka
    plate_format = Column(String(50))  # e.g., "civilian", "military", "government"
    
    # Vehicle details
    vehicle_type = Column(String(100))  # car, truck, bus, motorcycle, military_vehicle
    make = Column(String(100))
    model = Column(String(100))
    color = Column(String(50))
    
    # Authorization
    is_authorized = Column(Boolean, default=False)
    clearance_level = Column(String(50))  # public, restricted, confidential, secret
    authorized_zones = Column(JSON, default=list)  # List of zone names
    
    # Owner information
    owner_name = Column(String(255))
    owner_contact = Column(String(20))
    owner_unit = Column(String(255))  # Military unit or department
    owner_rank = Column(String(100))  # For military personnel
    
    # Validity
    authorization_start = Column(DateTime)
    authorization_end = Column(DateTime)
    is_permanent = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_blacklisted = Column(Boolean, default=False)
    blacklist_reason = Column(String(512))
    
    # Metadata
    notes = Column(String(1024))
    metadata_json = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "license_plate": self.license_plate,
            "plate_state": self.plate_state,
            "plate_format": self.plate_format,
            "vehicle_type": self.vehicle_type,
            "make": self.make,
            "model": self.model,
            "color": self.color,
            "is_authorized": self.is_authorized,
            "clearance_level": self.clearance_level,
            "authorized_zones": self.authorized_zones,
            "owner": {
                "name": self.owner_name,
                "contact": self.owner_contact,
                "unit": self.owner_unit,
                "rank": self.owner_rank
            },
            "validity": {
                "start": self.authorization_start.isoformat() if self.authorization_start else None,
                "end": self.authorization_end.isoformat() if self.authorization_end else None,
                "is_permanent": self.is_permanent
            },
            "is_active": self.is_active,
            "is_blacklisted": self.is_blacklisted,
            "blacklist_reason": self.blacklist_reason,
            "notes": self.notes
        }