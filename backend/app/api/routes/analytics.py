from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Dict
from datetime import datetime, timedelta

from app.models.database import get_db
from app.models.threat import Threat
from app.models.detection import Detection
from app.models.camera import Camera

router = APIRouter()

@router.get("/timeline")
async def get_threat_timeline(
    hours: int = Query(default=24, le=168),
    interval_minutes: int = Query(default=60),
    db: AsyncSession = Depends(get_db)
):
    """Get threat timeline with time-series data"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(Threat).where(Threat.timestamp >= cutoff_time)
    result = await db.execute(query)
    threats = result.scalars().all()
    
    # Group by time intervals
    timeline = {}
    for threat in threats:
        # Round to nearest interval
        interval_start = threat.timestamp.replace(
            minute=(threat.timestamp.minute // interval_minutes) * interval_minutes,
            second=0,
            microsecond=0
        )
        
        key = interval_start.isoformat()
        if key not in timeline:
            timeline[key] = {
                "timestamp": key,
                "total": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        
        timeline[key]["total"] += 1
        timeline[key][threat.threat_level.lower()] += 1
    
    return {
        "interval_minutes": interval_minutes,
        "timeline": sorted(timeline.values(), key=lambda x: x["timestamp"])
    }

@router.get("/heatmap")
async def get_threat_heatmap(
    days: int = Query(default=7, le=30),
    db: AsyncSession = Depends(get_db)
):
    """Get geospatial heatmap of threats"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    # Get threats with camera locations
    query = select(Threat, Camera).join(
        Camera, Threat.camera_id == Camera.id
    ).where(Threat.timestamp >= cutoff_time)
    
    result = await db.execute(query)
    rows = result.all()
    
    heatmap_data = []
    for threat, camera in rows:
        heatmap_data.append({
            "latitude": camera.latitude,
            "longitude": camera.longitude,
            "intensity": threat.threat_score,
            "level": threat.threat_level,
            "zone": camera.zone_name,
            "timestamp": threat.timestamp.isoformat()
        })
    
    return {
        "period_days": days,
        "total_points": len(heatmap_data),
        "heatmap": heatmap_data
    }

@router.get("/detection-stats")
async def get_detection_stats(
    hours: int = Query(default=24, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get detection statistics"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(Detection).where(Detection.timestamp >= cutoff_time)
    result = await db.execute(query)
    detections = result.scalars().all()
    
    # Calculate statistics
    stats = {
        "total_detections": len(detections),
        "by_class": {},
        "unique_tracks": len(set(d.track_id for d in detections)),
        "weapons_detected": 0,
        "vehicles_detected": 0,
        "persons_detected": 0
    }
    
    for det in detections:
        class_name = det.object_class
        if class_name not in stats["by_class"]:
            stats["by_class"][class_name] = 0
        stats["by_class"][class_name] += 1
        
        if det.weapon_type:
            stats["weapons_detected"] += 1
        if class_name in ['car', 'truck', 'bus', 'motorcycle']:
            stats["vehicles_detected"] += 1
        if class_name == 'person':
            stats["persons_detected"] += 1
    
    return stats

@router.get("/camera-performance")
async def get_camera_performance(
    days: int = Query(default=7, le=30),
    db: AsyncSession = Depends(get_db)
):
    """Get performance metrics for each camera"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    # Get all cameras
    camera_query = select(Camera).where(Camera.is_active == True)
    camera_result = await db.execute(camera_query)
    cameras = camera_result.scalars().all()
    
    performance = []
    for camera in cameras:
        # Get threats for this camera
        threat_query = select(Threat).where(
            and_(
                Threat.camera_id == camera.id,
                Threat.timestamp >= cutoff_time
            )
        )
        threat_result = await db.execute(threat_query)
        threats = threat_result.scalars().all()
        
        # Get detections for this camera
        det_query = select(Detection).where(
            and_(
                Detection.camera_id == camera.id,
                Detection.timestamp >= cutoff_time
            )
        )
        det_result = await db.execute(det_query)
        detections = det_result.scalars().all()
        
        performance.append({
            "camera_id": str(camera.id),
            "camera_name": camera.name,
            "zone": camera.zone_name,
            "status": camera.status,
            "total_detections": len(detections),
            "total_threats": len(threats),
            "critical_threats": len([t for t in threats if t.threat_level == 'CRITICAL']),
            "uptime_percentage": 95.0,  # TODO: Calculate from heartbeats
            "last_heartbeat": camera.last_heartbeat.isoformat() if camera.last_heartbeat else None
        })
    
    return {
        "period_days": days,
        "cameras": performance
    }

@router.get("/top-threats")
async def get_top_threats(
    days: int = Query(default=7, le=30),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get top threats by score"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    query = select(Threat, Camera).join(
        Camera, Threat.camera_id == Camera.id
    ).where(
        Threat.timestamp >= cutoff_time
    ).order_by(Threat.threat_score.desc()).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    top_threats = []
    for threat, camera in rows:
        threat_dict = threat.to_dict()
        threat_dict["camera_name"] = camera.name
        threat_dict["camera_zone"] = camera.zone_name
        top_threats.append(threat_dict)
    
    return {
        "period_days": days,
        "threats": top_threats
    }

@router.get("/export/csv")
async def export_threats_csv(
    days: int = Query(default=7, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Export threats to CSV format"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    query = select(Threat, Camera).join(
        Camera, Threat.camera_id == Camera.id
    ).where(Threat.timestamp >= cutoff_time)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Timestamp', 'Camera Name', 'Zone', 'Threat Type', 
        'Threat Level', 'Threat Score', 'Behavior', 'Status'
    ])
    
    # Data
    for threat, camera in rows:
        writer.writerow([
            threat.timestamp.isoformat(),
            camera.name,
            camera.zone_name,
            threat.threat_type,
            threat.threat_level,
            threat.threat_score,
            threat.behavior,
            'Resolved' if threat.is_resolved else 'Active'
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=trinetra_threats_{days}days.csv"}
    )