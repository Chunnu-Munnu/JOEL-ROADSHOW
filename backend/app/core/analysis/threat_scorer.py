from typing import List, Dict, Any, Optional
from collections import defaultdict
import time
import numpy as np
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class ThreatScorer:
    """Behavioral threat analysis and scoring engine"""
    
    def __init__(self):
        # Track history: {camera_id: {track_id: [(timestamp, position, data), ...]}}
        self.track_history = defaultdict(lambda: defaultdict(list))
        
        # First seen timestamp for each track
        self.track_first_seen = {}
        
        # Threat score cache
        self.threat_cache = {}
        
        # Behavioral patterns
        self.behavior_weights = {
            'weapon_detected': 1.0,
            'loitering': 0.6,
            'crouching': 0.4,
            'arms_raised': 0.5,
            'crawling': 0.7,
            'rapid_movement': 0.3,
            'unauthorized_vehicle': 0.8,
            'vehicle_stationary': 0.6,
            'restricted_zone': 0.9,
            'repeated_zone_entry': 0.7,
            'group_coordination': 0.75
        }
    
    def analyze_threats(self, 
                       detections: List[Dict[str, Any]], 
                       camera_id: str,
                       camera_info: Dict[str, Any],
                       vehicle_validations: Dict[str, Dict] = None) -> List[Dict[str, Any]]:
        """
        Analyze detections and generate threat scores
        
        Args:
            detections: List of detection dictionaries from YOLODetector
            camera_id: ID of the camera
            camera_info: Camera metadata (location, zone info)
            vehicle_validations: Results from PlateValidator
        
        Returns:
            List of threat dictionaries
        """
        threats = []
        current_time = time.time()
        
        # Update tracking history
        self._update_history(detections, camera_id, current_time)
        
        # Analyze each detection
        for det in detections:
            track_id = det['track_id']
            if track_id < 0:  # Invalid track
                continue
            
            threat_score = 0.0
            threat_behaviors = []
            threat_type = 'normal'
            
            # 1. WEAPON DETECTION (CRITICAL)
            if det.get('weapon'):
                threat_score = 1.0
                threat_behaviors.append('weapon_detected')
                threat_type = 'armed_person'
                logger.warning(f"WEAPON DETECTED: Track {track_id} with {det['weapon']['type']}")
            
            # 2. UNAUTHORIZED VEHICLE
            if det['class'] in ['car', 'truck', 'bus', 'motorcycle']:
                vehicle_threat = self._analyze_vehicle_threat(
                    det, track_id, camera_id, current_time,
                    vehicle_validations, camera_info
                )
                threat_score = max(threat_score, vehicle_threat['score'])
                threat_behaviors.extend(vehicle_threat['behaviors'])
                if vehicle_threat['type']:
                    threat_type = vehicle_threat['type']
            
            # 3. PERSON-SPECIFIC THREATS
            if det['class'] == 'person':
                person_threat = self._analyze_person_threat(
                    det, track_id, camera_id, current_time, camera_info
                )
                threat_score = max(threat_score, person_threat['score'])
                threat_behaviors.extend(person_threat['behaviors'])
                if person_threat['type']:
                    threat_type = person_threat['type']
            
            # 4. RESTRICTED ZONE VIOLATION
            if camera_info.get('restricted_zone', False):
                zone_threat = self._analyze_zone_violation(
                    det, camera_info
                )
                threat_score = max(threat_score, zone_threat['score'])
                threat_behaviors.extend(zone_threat['behaviors'])
            
            # Only report significant threats
            if threat_score >= 0.4 or threat_type != 'normal':
                threat_level = self._get_threat_level(threat_score)
                
                threats.append({
                    'track_id': track_id,
                    'class': det['class'],
                    'score': min(threat_score, 1.0),
                    'level': threat_level,
                    'behaviors': threat_behaviors,
                    'type': threat_type,
                    'position': det['center'],
                    'bbox': det['bbox'],
                    'camera_id': camera_id,
                    'zone_name': camera_info.get('zone_name'),
                    'timestamp': current_time,
                    'metadata': {
                        'pose': det.get('pose'),
                        'weapon': det.get('weapon'),
                        'vehicle_plate': det.get('vehicle_plate')
                    }
                })
        
        # 5. GROUP BEHAVIOR ANALYSIS
        group_threats = self._analyze_group_behaviors(detections, camera_id, current_time)
        threats.extend(group_threats)
        
        return threats
    
    def _analyze_vehicle_threat(self, detection: Dict, track_id: int, 
                                camera_id: str, current_time: float,
                                vehicle_validations: Dict, 
                                camera_info: Dict) -> Dict:
        """Analyze vehicle-specific threats"""
        score = 0.0
        behaviors = []
        threat_type = None
        
        # Check authorization status
        plate = detection.get('vehicle_plate')
        if plate and vehicle_validations and plate in vehicle_validations:
            validation = vehicle_validations[plate]
            
            if not validation['is_authorized']:
                if validation['threat_level'] == 'CRITICAL':
                    score = 0.95
                    threat_type = 'blacklisted_vehicle'
                elif validation['threat_level'] == 'HIGH':
                    score = 0.85
                    threat_type = 'unauthorized_vehicle'
                else:
                    score = 0.7
                    threat_type = 'unverified_vehicle'
                
                behaviors.append('unauthorized_vehicle')
        
        # Check if stationary for too long
        if self._is_vehicle_stationary(track_id, camera_id, current_time):
            score = max(score, 0.6)
            behaviors.append('vehicle_stationary')
            if not threat_type:
                threat_type = 'suspicious_parking'
        
        # Check for repeated passes (reconnaissance)
        if self._has_repeated_passes(track_id, camera_id):
            score = max(score, 0.7)
            behaviors.append('repeated_passes')
            if not threat_type:
                threat_type = 'reconnaissance'
        
        return {
            'score': score,
            'behaviors': behaviors,
            'type': threat_type
        }
    
    def _analyze_person_threat(self, detection: Dict, track_id: int,
                               camera_id: str, current_time: float,
                               camera_info: Dict) -> Dict:
        """Analyze person-specific threats"""
        score = 0.0
        behaviors = []
        threat_type = None
        
        # Pose-based threats
        pose = detection.get('pose')
        if pose == 'crouching':
            score = 0.4
            behaviors.append('crouching')
            threat_type = 'suspicious_posture'
        elif pose == 'arms_raised':
            score = 0.5
            behaviors.append('arms_raised')
            threat_type = 'threatening_gesture'
        elif pose == 'crawling':
            score = 0.7
            behaviors.append('crawling')
            threat_type = 'infiltration_attempt'
        
        # Loitering detection
        if self._is_loitering(track_id, camera_id, current_time):
            score = max(score, 0.6)
            behaviors.append('loitering')
            if not threat_type:
                threat_type = 'loitering'
        
        # Rapid movement (running)
        if self._is_moving_rapidly(track_id, camera_id):
            score = max(score, 0.3)
            behaviors.append('rapid_movement')
        
        # Repeated zone entry
        if self._has_repeated_zone_entries(track_id, camera_id):
            score = max(score, 0.7)
            behaviors.append('repeated_zone_entry')
            if not threat_type:
                threat_type = 'surveillance'
        
        return {
            'score': score,
            'behaviors': behaviors,
            'type': threat_type
        }
    
    def _analyze_zone_violation(self, detection: Dict, 
                                camera_info: Dict) -> Dict:
        """Analyze restricted zone violations"""
        score = 0.0
        behaviors = []
        
        if camera_info.get('zone_type') == 'high_security':
            score = 0.9
            behaviors.append('restricted_zone')
        elif camera_info.get('zone_type') == 'restricted':
            score = 0.7
            behaviors.append('restricted_zone')
        
        return {
            'score': score,
            'behaviors': behaviors
        }
    
    def _analyze_group_behaviors(self, detections: List[Dict],
                                 camera_id: str, current_time: float) -> List[Dict]:
        """Detect coordinated group movements"""
        threats = []
        
        # Get all person detections
        persons = [d for d in detections if d['class'] == 'person']
        
        if len(persons) >= 3:
            # Check for coordinated movement
            positions = np.array([p['center'] for p in persons])
            
            # Calculate pairwise distances
            if len(positions) > 0:
                from scipy.spatial.distance import pdist, squareform
                distances = squareform(pdist(positions))
                
                # Check if group is clustered (mean distance < threshold)
                mean_distance = np.mean(distances[distances > 0])
                
                if mean_distance < 200:  # pixels - they're close together
                    threats.append({
                        'track_id': -1,  # Group threat, no single track
                        'class': 'group',
                        'score': 0.75,
                        'level': 'HIGH',
                        'behaviors': ['group_coordination'],
                        'type': 'coordinated_group',
                        'position': list(np.mean(positions, axis=0).astype(int)),
                        'bbox': None,
                        'camera_id': camera_id,
                        'timestamp': current_time,
                        'metadata': {
                            'group_size': len(persons),
                            'mean_distance': mean_distance
                        }
                    })
        
        return threats
    
    def _is_loitering(self, track_id: int, camera_id: str, 
                     current_time: float) -> bool:
        """Check if object has been stationary"""
        history = self.track_history[camera_id][track_id]
        
        if len(history) < 2:
            return False
        
        # Check movement over threshold time
        first_time, first_pos, _ = history[0]
        last_time, last_pos, _ = history[-1]
        
        duration = current_time - first_time
        distance = np.linalg.norm(np.array(first_pos) - np.array(last_pos))
        
        return (duration > settings.LOITER_THRESHOLD_SECONDS and 
                distance < 50)  # Less than 50 pixels movement
    
    def _is_vehicle_stationary(self, track_id: int, camera_id: str,
                               current_time: float) -> bool:
        """Check if vehicle is parked for too long"""
        history = self.track_history[camera_id][track_id]
        
        if len(history) < 10:
            return False
        
        # Check last 10 positions
        recent = history[-10:]
        positions = [pos for _, pos, _ in recent]
        
        max_movement = 0
        for i in range(len(positions) - 1):
            movement = np.linalg.norm(np.array(positions[i]) - np.array(positions[i+1]))
            max_movement = max(max_movement, movement)
        
        # Vehicle is stationary if max movement < 20 pixels
        first_time = recent[0][0]
        duration = current_time - first_time
        
        return max_movement < 20 and duration > settings.VEHICLE_STATIONARY_THRESHOLD
    
    def _is_moving_rapidly(self, track_id: int, camera_id: str) -> bool:
        """Check for rapid movement"""
        history = self.track_history[camera_id][track_id]
        
        if len(history) < 5:
            return False
        
        recent = history[-5:]
        start_time, start_pos, _ = recent[0]
        end_time, end_pos, _ = recent[-1]
        
        distance = np.linalg.norm(np.array(start_pos) - np.array(end_pos))
        time_diff = end_time - start_time
        
        if time_diff == 0:
            return False
        
        speed = distance / time_diff  # pixels per second
        
        return speed > settings.RAPID_MOVEMENT_THRESHOLD
    
    def _has_repeated_zone_entries(self, track_id: int, camera_id: str) -> bool:
        """Check if object entered zone multiple times"""
        # This would require cross-camera tracking
        # Simplified version: check if track ID appeared, disappeared, reappeared
        history = self.track_history[camera_id][track_id]
        return len(history) > 100  # Placeholder logic
    
    def _has_repeated_passes(self, track_id: int, camera_id: str) -> bool:
        """Check if vehicle made multiple passes"""
        # Similar to repeated zone entries
        history = self.track_history[camera_id][track_id]
        return len(history) > 150  # Placeholder
    
    def _update_history(self, detections: List[Dict], 
                       camera_id: str, current_time: float):
        """Update tracking history"""
        active_tracks = set()
        
        for det in detections:
            track_id = det['track_id']
            if track_id < 0:
                continue
            
            active_tracks.add(track_id)
            
            # Add to history
            self.track_history[camera_id][track_id].append((
                current_time,
                det['center'],
                det
            ))
            
            # Keep only last 5 minutes of history
            self.track_history[camera_id][track_id] = [
                (t, pos, data) for t, pos, data in self.track_history[camera_id][track_id]
                if current_time - t < 300
            ]
            
            # Track first seen time
            if track_id not in self.track_first_seen:
                self.track_first_seen[track_id] = current_time
        
        # Clean up old tracks
        for track_id in list(self.track_history[camera_id].keys()):
            if track_id not in active_tracks:
                history = self.track_history[camera_id][track_id]
                if history:
                    last_seen = history[-1][0]
                    if current_time - last_seen > 60:  # 1 minute
                        del self.track_history[camera_id][track_id]
                        if track_id in self.track_first_seen:
                            del self.track_first_seen[track_id]
    
    def _get_threat_level(self, score: float) -> str:
        """Convert threat score to level"""
        if score >= settings.CRITICAL_THREAT_SCORE:
            return 'CRITICAL'
        elif score >= settings.HIGH_THREAT_SCORE:
            return 'HIGH'
        elif score >= settings.MEDIUM_THREAT_SCORE:
            return 'MEDIUM'
        else:
            return 'LOW'