from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vehicle import Vehicle
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class PlateValidator:
    """Validate license plates against authorized vehicle database"""
    
    async def check_authorization(self, 
                                  plate: str, 
                                  zone_name: str,
                                  db: AsyncSession) -> Dict[str, any]:
        """
        Check if a vehicle plate is authorized for the current zone
        
        Returns:
            {
                'is_authorized': bool,
                'vehicle_info': dict or None,
                'reason': str,
                'threat_level': str
            }
        """
        try:
            # Query database for this plate
            query = select(Vehicle).where(
                Vehicle.license_plate == plate.upper(),
                Vehicle.is_active == True
            )
            result = await db.execute(query)
            vehicle = result.scalar_one_or_none()
            
            # Plate not in database
            if not vehicle:
                return {
                    'is_authorized': False,
                    'vehicle_info': None,
                    'reason': f'Unknown vehicle: {plate}',
                    'threat_level': 'HIGH',
                    'action': 'ALERT_AND_INTERCEPT'
                }
            
            # Check if blacklisted
            if vehicle.is_blacklisted:
                return {
                    'is_authorized': False,
                    'vehicle_info': vehicle.to_dict(),
                    'reason': f'Blacklisted: {vehicle.blacklist_reason}',
                    'threat_level': 'CRITICAL',
                    'action': 'IMMEDIATE_RESPONSE'
                }
            
            # Check zone authorization
            if not vehicle.is_authorized:
                return {
                    'is_authorized': False,
                    'vehicle_info': vehicle.to_dict(),
                    'reason': 'Vehicle not authorized',
                    'threat_level': 'HIGH',
                    'action': 'ALERT_AND_VERIFY'
                }
            
            # Check if authorized for this specific zone
            if zone_name and vehicle.authorized_zones:
                if zone_name not in vehicle.authorized_zones:
                    return {
                        'is_authorized': False,
                        'vehicle_info': vehicle.to_dict(),
                        'reason': f'Not authorized for zone: {zone_name}',
                        'threat_level': 'MEDIUM',
                        'action': 'ALERT_AND_VERIFY'
                    }
            
            # Check validity period
            from datetime import datetime
            now = datetime.utcnow()
            
            if not vehicle.is_permanent:
                if vehicle.authorization_end and now > vehicle.authorization_end:
                    return {
                        'is_authorized': False,
                        'vehicle_info': vehicle.to_dict(),
                        'reason': 'Authorization expired',
                        'threat_level': 'MEDIUM',
                        'action': 'ALERT_AND_VERIFY'
                    }
                
                if vehicle.authorization_start and now < vehicle.authorization_start:
                    return {
                        'is_authorized': False,
                        'vehicle_info': vehicle.to_dict(),
                        'reason': 'Authorization not yet active',
                        'threat_level': 'MEDIUM',
                        'action': 'ALERT_AND_VERIFY'
                    }
            
            # All checks passed - authorized
            return {
                'is_authorized': True,
                'vehicle_info': vehicle.to_dict(),
                'reason': 'Authorized vehicle',
                'threat_level': 'NONE',
                'action': 'LOG_ONLY'
            }
            
        except Exception as e:
            logger.error(f"Plate validation error: {e}")
            return {
                'is_authorized': False,
                'vehicle_info': None,
                'reason': f'System error: {str(e)}',
                'threat_level': 'MEDIUM',
                'action': 'MANUAL_REVIEW'
            }