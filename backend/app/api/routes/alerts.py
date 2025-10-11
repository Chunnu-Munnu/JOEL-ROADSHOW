from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.database import get_db
from app.models.threat import Threat
from pydantic import BaseModel

router = APIRouter()

class AlertAcknowledge(BaseModel):
    acknowledged_by: str
    notes: str = ""

class AlertResolve(BaseModel):
    resolved_by: str
    resolution_notes: str

@router.get("/")
async def get_alerts(
    level: Optional[str] = None,
    camera_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get alerts with filters"""
    query = select(Threat).order_by(desc(Threat.timestamp))
    
    # Apply filters
    conditions = []
    if level:
        conditions.append(Threat.threat_level == level.upper())
    if camera_id:
        conditions.append(Threat.camera_id == camera_id)
    if resolved is not None:
        conditions.append(Threat.is_resolved == resolved)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    threats = result.scalars().all()
    
    return {
        "total": len(threats),
        "alerts": [threat.to_dict() for threat in threats]
    }

@router.get("/active")
async def get_active_alerts(db: AsyncSession = Depends(get_db)):
    """Get all active (unresolved) alerts"""
    query = select(Threat).where(
        Threat.is_resolved == False
    ).order_by(desc(Threat.threat_score))
    
    result = await db.execute(query)
    threats = result.scalars().all()
    
    return {
        "total": len(threats),
        "critical": len([t for t in threats if t.threat_level == 'CRITICAL']),
        "high": len([t for t in threats if t.threat_level == 'HIGH']),
        "medium": len([t for t in threats if t.threat_level == 'MEDIUM']),
        "alerts": [threat.to_dict() for threat in threats]
    }

@router.get("/recent")
async def get_recent_alerts(
    hours: int = Query(default=24, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get alerts from last N hours"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(Threat).where(
        Threat.timestamp >= cutoff_time
    ).order_by(desc(Threat.timestamp))
    
    result = await db.execute(query)
    threats = result.scalars().all()
    
    return {
        "hours": hours,
        "total": len(threats),
        "alerts": [threat.to_dict() for threat in threats]
    }

@router.get("/{alert_id}")
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Get single alert by ID"""
    query = select(Threat).where(Threat.id == alert_id)
    result = await db.execute(query)
    threat = result.scalar_one_or_none()
    
    if not threat:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return threat.to_dict()

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    ack_data: AlertAcknowledge,
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge an alert"""
    query = select(Threat).where(Threat.id == alert_id)
    result = await db.execute(query)
    threat = result.scalar_one_or_none()
    
    if not threat:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    threat.is_acknowledged = True
    threat.acknowledged_by = ack_data.acknowledged_by
    threat.acknowledged_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Alert acknowledged", "alert": threat.to_dict()}

@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolve_data: AlertResolve,
    db: AsyncSession = Depends(get_db)
):
    """Resolve an alert"""
    query = select(Threat).where(Threat.id == alert_id)
    result = await db.execute(query)
    threat = result.scalar_one_or_none()
    
    if not threat:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    threat.is_resolved = True
    threat.resolved_by = resolve_data.resolved_by
    threat.resolved_at = datetime.utcnow()
    threat.resolution_notes = resolve_data.resolution_notes
    
    await db.commit()
    
    return {"message": "Alert resolved", "alert": threat.to_dict()}

@router.get("/stats/summary")
async def get_alert_stats(
    days: int = Query(default=7, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get alert statistics summary"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    query = select(Threat).where(Threat.timestamp >= cutoff_time)
    result = await db.execute(query)
    threats = result.scalars().all()
    
    # Calculate statistics
    stats = {
        "total_alerts": len(threats),
        "by_level": {
            "critical": len([t for t in threats if t.threat_level == 'CRITICAL']),
            "high": len([t for t in threats if t.threat_level == 'HIGH']),
            "medium": len([t for t in threats if t.threat_level == 'MEDIUM']),
            "low": len([t for t in threats if t.threat_level == 'LOW'])
        },
        "by_type": {},
        "resolved": len([t for t in threats if t.is_resolved]),
        "unresolved": len([t for t in threats if not t.is_resolved]),
        "average_response_time": 0,  # TODO: Calculate
        "period_days": days
    }
    
    # Count by type
    for threat in threats:
        threat_type = threat.threat_type
        if threat_type not in stats["by_type"]:
            stats["by_type"][threat_type] = 0
        stats["by_type"][threat_type] += 1
    
    return stats