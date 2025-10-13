"""
Snapshot Manager - Saves threat images for approval
"""
import cv2
import os
import time
import json
import base64
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages threat snapshots for notification approval"""
    
    def __init__(self, snapshot_dir: str = "snapshots"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(exist_ok=True)
        
        # Store pending notifications: {snapshot_id: {...}}
        self.pending_notifications = {}
        self.notification_counter = 0
        
        logger.info(f"📸 Snapshot manager initialized: {self.snapshot_dir}")
    
    def save_threat_snapshot(self, frame, threat: Dict[str, Any]) -> str:
        """
        Save a snapshot of a HIGH/CRITICAL threat
        
        Returns:
            snapshot_id: Unique identifier for this threat
        """
        try:
            # Generate unique ID
            snapshot_id = f"threat_{int(time.time())}_{threat['track_id']}"
            
            # Crop region around threat (with padding)
            x1, y1, x2, y2 = threat['bbox']
            h, w = frame.shape[:2]
            
            # Add 20% padding
            padding = 50
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(w, x2 + padding)
            y2 = min(h, y2 + padding)
            
            cropped = frame[y1:y2, x1:x2]
            
            # Save image
            image_path = self.snapshot_dir / f"{snapshot_id}.jpg"
            cv2.imwrite(str(image_path), cropped)
            
            # Save metadata
            metadata = {
                'snapshot_id': snapshot_id,
                'timestamp': threat['timestamp'],
                'camera_id': threat['camera_id'],
                'track_id': threat['track_id'],
                'threat_type': threat['type'],
                'threat_level': threat['level'],
                'score': threat['score'],
                'behaviors': threat['behaviors'],
                'position': threat['position'],
                'metadata': threat['metadata'],
                'status': 'pending',  # pending, approved, rejected
                'image_path': str(image_path)
            }
            
            metadata_path = self.snapshot_dir / f"{snapshot_id}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Store in memory for quick access
            self.pending_notifications[snapshot_id] = metadata
            
            logger.info(f"📸 Snapshot saved: {snapshot_id} - {threat['type']}")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None
    
    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get all pending threat notifications"""
        pending = []
        
        for snapshot_id, data in self.pending_notifications.items():
            if data['status'] == 'pending':
                # Convert image to base64 for frontend
                try:
                    with open(data['image_path'], 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    pending.append({
                        **data,
                        'image_base64': image_data
                    })
                except Exception as e:
                    logger.error(f"Error loading snapshot {snapshot_id}: {e}")
        
        return pending
    
    def approve_notification(self, snapshot_id: str) -> Dict[str, Any]:
        """Approve a threat notification - ready for blockchain logging"""
        if snapshot_id not in self.pending_notifications:
            return None
        
        self.pending_notifications[snapshot_id]['status'] = 'approved'
        
        # Update metadata file
        metadata_path = self.snapshot_dir / f"{snapshot_id}.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.pending_notifications[snapshot_id], f, indent=2)
        
        logger.info(f"✅ Threat approved: {snapshot_id}")
        return self.pending_notifications[snapshot_id]
    
    def reject_notification(self, snapshot_id: str):
        """Reject a threat notification (false positive)"""
        if snapshot_id not in self.pending_notifications:
            return
        
        self.pending_notifications[snapshot_id]['status'] = 'rejected'
        
        # Update metadata file
        metadata_path = self.snapshot_dir / f"{snapshot_id}.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.pending_notifications[snapshot_id], f, indent=2)
        
        logger.info(f"❌ Threat rejected: {snapshot_id}")
    
    def cleanup_old_snapshots(self, max_age_hours: int = 24):
        """Remove snapshots older than specified hours"""
        current_time = time.time()
        
        for snapshot_file in self.snapshot_dir.glob("*.json"):
            try:
                with open(snapshot_file, 'r') as f:
                    metadata = json.load(f)
                
                age_hours = (current_time - metadata['timestamp']) / 3600
                
                if age_hours > max_age_hours:
                    # Remove image and metadata
                    snapshot_id = metadata['snapshot_id']
                    image_file = self.snapshot_dir / f"{snapshot_id}.jpg"
                    
                    if image_file.exists():
                        image_file.unlink()
                    snapshot_file.unlink()
                    
                    if snapshot_id in self.pending_notifications:
                        del self.pending_notifications[snapshot_id]
                    
                    logger.info(f"🗑️  Cleaned up old snapshot: {snapshot_id}")
                    
            except Exception as e:
                logger.error(f"Error cleaning snapshot: {e}")
    
    def load_pending_from_disk(self):
        """Load pending notifications from disk on startup"""
        for metadata_file in self.snapshot_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                if metadata['status'] == 'pending':
                    self.pending_notifications[metadata['snapshot_id']] = metadata
                    
            except Exception as e:
                logger.error(f"Error loading pending notification: {e}")