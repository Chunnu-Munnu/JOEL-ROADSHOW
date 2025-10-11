from typing import List, Dict, Any
from collections import defaultdict
import time
import numpy as np
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class ThreatScorer:
    """Behavioral threat analysis with temporal tracking"""
    
    def __init__(self):
        # Track history: {camera_id: {track_id: [(timestamp, position, data), ...]}}
        self.track_history = defaultdict(lambda: defaultdict(list))
        self.track_first_seen = {}
        
    def analyze_threats(self, detections: List[Dict[str, Any]], camera_id: str, camera_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze detections and generate HIGH risk threats only"""
        threats = []
        current_time = time.time()
        
        self._update_history(detections, camera_id, current_time)
        
        for det in detections:
            track_id = det['track_id']
            if track_id < 0:
                continue
            
            threat_score = 0.0
            threat_behaviors = []
            threat_type = 'normal'
            
            # 🔫 WEAPON DETECTION = INSTANT HIGH RISK
            if det.get('weapon'):
                threat_score = 1.0
                threat_behaviors.append('weapon_detected')
                threat_type = f"armed_person_{det['weapon']['type']}"
                logger.critical(f"🔫 WEAPON DETECTED: Track {track_id} - {det['weapon']['type']}")
            
            # 👤 PERSON-SPECIFIC THREATS
            if det['class'] == 'person':
                person_threat = self._analyze_person_threat(det, track_id, camera_id, current_time)
                threat_score = max(threat_score, person_threat['score'])
                threat_behaviors.extend(person_threat['behaviors'])
                if person_threat['type']:
                    threat_type = person_threat['type']
            
            # 🚗 VEHICLE THREATS
            if det['class'] in ['car', 'truck', 'bus', 'motorcycle']:
                # Only flag if unauthorized (check in main.py with plate validation)
                pass
            
            # 👥 GROUP THREATS (checked separately below)
            
            # ✅ ONLY SEND HIGH RISK TO NOTIFICATIONS
            if threat_score >= settings.HIGH_THREAT_SCORE:
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
                    'timestamp': current_time,
                    'metadata': {
                        'pose': det.get('pose'),
                        'weapon': det.get('weapon'),
                        'is_camouflaged': det.get('is_camouflaged', False)
                    }
                })
        
        # 👥 GROUP BEHAVIOR ANALYSIS (6+ people)
        group_threats = self._analyze_group_behaviors(detections, camera_id, current_time)
        threats.extend(group_threats)
        
        return threats
    
    def _analyze_person_threat(self, detection: Dict, track_id: int, camera_id: str, current_time: float) -> Dict:
        """Analyze person threats with STRICT thresholds"""
        score = 0.0
        behaviors = []
        threat_type = None
        
        history = self.track_history[camera_id][track_id]
        
        if len(history) < 2:
            return {'score': 0.0, 'behaviors': [], 'type': None}
        
        first_time, first_pos, first_data = history[0]
        last_time, last_pos, last_data = history[-1]
        
        duration = current_time - first_time
        distance = np.linalg.norm(np.array(first_pos) - np.array(last_pos))
        
        pose = detection.get('pose')
        
        # ⏱️ STANDING STATIONARY 60+ SECONDS = HIGH RISK
        if pose == 'standing' and duration >= settings.STANDING_THRESHOLD_SECONDS and distance < 50:
            score = 0.8
            behaviors.append('standing_10s')
            threat_type = 'person_standing_still_for_long_time near_sensitive_area'
            logger.warning(f"⏱️ Person #{track_id} standing {duration:.1f}s")
        
        # 🧎 CROUCHING 45+ SECONDS = HIGH RISK
        elif pose == 'crouching' and duration >= settings.CROUCHING_THRESHOLD_SECONDS and distance < 50:
            score = 0.85
            behaviors.append('crouching_45s')
            threat_type = 'suspicious_posture'
            logger.warning(f"🧎 Person #{track_id} crouching {duration:.1f}s")
        
        # 🎭 CAMOUFLAGE ESCALATION (2 minutes → HIGH RISK)
        elif detection.get('is_camouflaged'):
            if duration < settings.CAMOUFLAGE_LOW_RISK_SECONDS:
                score = 0.3  # LOW RISK initially
                behaviors.append('camouflage_detected')
                threat_type = 'possible_wildlife'
            else:
                score = 0.85  # HIGH RISK after 2 minutes
                behaviors.append('camouflage_prolonged')
                threat_type = 'potential_infiltrator'
                logger.warning(f"🎭 Camouflaged entity #{track_id} for {duration:.1f}s")
        
        # 🤸 CRAWLING = MEDIUM RISK (not high enough for notification)
        elif pose == 'crawling':
            score = 0.6  # Won't trigger notification (< 0.7)
            behaviors.append('crawling')
            threat_type = 'infiltration_attempt'
        
        return {'score': score, 'behaviors': behaviors, 'type': threat_type}
    
    def _analyze_group_behaviors(self, detections: List[Dict], camera_id: str, current_time: float) -> List[Dict]:
        """Detect large groups (6+ people)"""
        threats = []
        
        persons = [d for d in detections if d['class'] == 'person']
        
        # 👥 6+ PEOPLE = HIGH RISK
        if len(persons) >= settings.GROUP_SIZE_THRESHOLD:
            positions = np.array([p['center'] for p in persons])
            
            threats.append({
                'track_id': -1,
                'class': 'group',
                'score': 0.8,
                'level': 'HIGH',
                'behaviors': ['large_group'],
                'type': 'group_assembly',
                'position': list(np.mean(positions, axis=0).astype(int)),
                'bbox': None,
                'camera_id': camera_id,
                'timestamp': current_time,
                'metadata': {'group_size': len(persons)}
            })
            logger.warning(f"👥 Large group detected: {len(persons)} people")
        
        return threats
    
    def _update_history(self, detections: List[Dict], camera_id: str, current_time: float):
        """Update tracking history"""
        active_tracks = set()
        
        for det in detections:
            track_id = det['track_id']
            if track_id < 0:
                continue
            
            active_tracks.add(track_id)
            
            self.track_history[camera_id][track_id].append((
                current_time,
                det['center'],
                det
            ))
            
            # Keep last 5 minutes only
            self.track_history[camera_id][track_id] = [
                (t, pos, data) for t, pos, data in self.track_history[camera_id][track_id]
                if current_time - t < 300
            ]
            
            if track_id not in self.track_first_seen:
                self.track_first_seen[track_id] = current_time
        
        # Clean up old tracks
        for track_id in list(self.track_history[camera_id].keys()):
            if track_id not in active_tracks:
                history = self.track_history[camera_id][track_id]
                if history and (current_time - history[-1][0] > 60):
                    del self.track_history[camera_id][track_id]
                    if track_id in self.track_first_seen:
                        del self.track_first_seen[track_id]
    
    def _get_threat_level(self, score: float) -> str:
        """Convert score to threat level"""
        if score >= 0.9:
            return 'CRITICAL'
        elif score >= 0.7:
            return 'HIGH'
        elif score >= 0.5:
            return 'MEDIUM'
        else:
            return 'LOW'