"""
Initialize TRINETRA database and load configuration data
Run this once before starting the backend server
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import init_db, async_session_maker
from app.models.camera import Camera
from app.models.vehicle import Vehicle
import uuid

async def load_cameras():
    """Load cameras from configuration file"""
    print("📹 Loading camera configurations...")
    
    config_path = Path(__file__).parent.parent / 'data' / 'camera_locations.json'
    
    if not config_path.exists():
        print(f"❌ Camera config not found: {config_path}")
        return
    
    with open(config_path) as f:
        data = json.load(f)
    
    async with async_session_maker() as session:
        for cam_data in data['cameras']:
            # Check if camera already exists
            existing = await session.get(Camera, uuid.UUID(cam_data.get('id', str(uuid.uuid4()))))
            if existing:
                print(f"   ⏭️  Camera '{cam_data['name']}' already exists, skipping")
                continue
            
            camera = Camera(
                id=uuid.UUID(cam_data.get('id', str(uuid.uuid4()))) if 'id' in cam_data else uuid.uuid4(),
                name=cam_data['name'],
                stream_url=cam_data['stream_url'],
                stream_type=cam_data['stream_type'],
                latitude=cam_data['latitude'],
                longitude=cam_data['longitude'],
                altitude=cam_data.get('altitude', 0.0),
                address=cam_data.get('address', ''),
                coverage_radius=cam_data.get('coverage_radius', 100.0),
                field_of_view=cam_data.get('field_of_view', 90.0),
                camera_angle=cam_data.get('camera_angle', 0.0),
                zone_name=cam_data.get('zone_name', ''),
                zone_type=cam_data.get('zone_type', 'public'),
                restricted_zone=cam_data.get('restricted_zone', False),
                resolution_width=cam_data.get('resolution_width', 1280),
                resolution_height=cam_data.get('resolution_height', 720),
                fps=cam_data.get('fps', 10),
                status='offline',
                is_active=True
            )
            
            session.add(camera)
            print(f"   ✅ Added camera: {cam_data['name']}")
        
        await session.commit()
    
    print(f"✅ Loaded {len(data['cameras'])} cameras")

async def load_vehicles():
    """Load authorized vehicles from configuration file"""
    print("🚗 Loading vehicle whitelist...")
    
    config_path = Path(__file__).parent.parent / 'data' / 'vehicle_whitelist.json'
    
    if not config_path.exists():
        print(f"❌ Vehicle config not found: {config_path}")
        return
    
    with open(config_path) as f:
        data = json.load(f)
    
    async with async_session_maker() as session:
        for veh_data in data['vehicles']:
            vehicle = Vehicle(
                license_plate=veh_data['license_plate'],
                plate_state=veh_data.get('plate_state'),
                plate_format=veh_data.get('plate_format', 'civilian_new'),
                vehicle_type=veh_data.get('vehicle_type', 'car'),
                make=veh_data.get('make'),
                model=veh_data.get('model'),
                color=veh_data.get('color'),
                is_authorized=veh_data.get('is_authorized', False),
                clearance_level=veh_data.get('clearance_level'),
                authorized_zones=veh_data.get('authorized_zones', []),
                owner_name=veh_data.get('owner_name'),
                owner_contact=veh_data.get('owner_contact'),
                owner_unit=veh_data.get('owner_unit'),
                owner_rank=veh_data.get('owner_rank'),
                is_permanent=veh_data.get('is_permanent', True),
                is_blacklisted=veh_data.get('is_blacklisted', False),
                blacklist_reason=veh_data.get('blacklist_reason'),
                notes=veh_data.get('notes')
            )
            
            session.add(vehicle)
            print(f"   ✅ Added vehicle: {veh_data['license_plate']}")
        
        await session.commit()
    
    print(f"✅ Loaded {len(data['vehicles'])} vehicles")

async def main():
    """Main initialization function"""
    print("\n" + "="*60)
    print("🚀 TRINETRA Database Initialization")
    print("="*60 + "\n")
    
    try:
        # Create database tables
        print("📊 Creating database tables...")
        await init_db()
        print("✅ Database tables created\n")
        
        # Load configuration data
        await load_cameras()
        print()
        await load_vehicles()
        
        print("\n" + "="*60)
        print("✅ Database initialization complete!")
        print("="*60 + "\n")
        print("Next steps:")
        print("1. Start backend: uvicorn app.main:app --reload")
        print("2. Access API docs: http://localhost:8000/docs")
        print("3. Start frontend: cd ../frontend && npm run dev\n")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())