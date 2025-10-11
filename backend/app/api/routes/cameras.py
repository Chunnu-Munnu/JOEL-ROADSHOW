from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List
from datetime import datetime
import uuid

from app.models.database import get_db
from app.models.camera import Camera
from pydantic import BaseModel

router = APIRouter()

# Pydantic schemas
class CameraCreate(BaseModel):
    name: str
    stream_url: str
    stream_type: str = "rtsp"
    latitude: float
    longitude: float
    altitude: float = 0.0
    address: str = ""
    coverage_radius: float = 100.0
    field_of_view: float = 90.0
    camera_angle: float = 0.0
    zone_name: str = ""
    zone_type: str = "public"
    restricted_zone: bool = False
    resolution_width: int = 1280
    resolution_height: int = 720
    fps: int = 10

class CameraUpdate(BaseModel):
    name: str = None
    stream_url: str = None
    latitude: float = None
    longitude: float = None
    address: str = None
    zone_name: str = None
    zone_type: str = None
    restricted_zone: bool = None
    status: str = None
    is_active: bool = None

@router.get("/")
async def get_all_cameras(db: AsyncSession = Depends(get_db)):
    """Get all cameras"""
    query = select(Camera).where(Camera.is_active == True)
    result = await db.execute(query)
    cameras = result.scalars().all()
    
    return {
        "total": len(cameras),
        "cameras": [camera.to_dict() for camera in cameras]
    }

@router.get("/{camera_id}")
async def get_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    """Get single camera by ID"""
    query = select(Camera).where(Camera.id == camera_id)
    result = await db.execute(query)
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return camera.to_dict()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_camera(camera_data: CameraCreate, db: AsyncSession = Depends(get_db)):
    """Create new camera"""
    camera = Camera(
        id=uuid.uuid4(),
        **camera_data.dict()
    )
    
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    
    return camera.to_dict()

@router.put("/{camera_id}")
async def update_camera(camera_id: str, camera_data: CameraUpdate, 
                       db: AsyncSession = Depends(get_db)):
    """Update camera"""
    query = select(Camera).where(Camera.id == camera_id)
    result = await db.execute(query)
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Update fields
    update_data = camera_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(camera, field, value)
    
    camera.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(camera)
    
    return camera.to_dict()

@router.delete("/{camera_id}")
async def delete_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    """Delete camera (soft delete)"""
    query = select(Camera).where(Camera.id == camera_id)
    result = await db.execute(query)
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    camera.is_active = False
    camera.status = "deleted"
    await db.commit()
    
    return {"message": "Camera deleted successfully"}

@router.post("/{camera_id}/heartbeat")
async def camera_heartbeat(camera_id: str, db: AsyncSession = Depends(get_db)):
    """Update camera heartbeat"""
    query = select(Camera).where(Camera.id == camera_id)
    result = await db.execute(query)
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    camera.last_heartbeat = datetime.utcnow()
    camera.status = "online"
    await db.commit()
    
    return {"status": "ok", "timestamp": camera.last_heartbeat.isoformat()}