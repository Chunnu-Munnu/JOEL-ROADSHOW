"""
app/core/analysis/threat_scorer.py
Behavioral threat analysis with temporal tracking
"""
from typing import List, Dict, Any
from collections import defaultdict
import time
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Thresholds
STANDING_THRESHOLD_SECONDS = 10.0
CROUCHING_THRESHOLD_SECONDS = 10.0
MAX_MOVEMENT_PIXELS = 100
GROUP_SIZE_THRESHOLD = 6


class ThreatScorer:
    """Behavioral threat analysis with temporal tracking"""
    
    def __init__(self):
        # Track history: {camera_id: {track_id: [(timestamp, position, pose, data), ...]}}
        self.track_history = defaultdict(lambda: defaultdict(list))
        self.track_first_seen = {}
        self.high_risk_tracks = set()  # Once flagged, stays red
        
    def analyze_threats(self, detections: List[Dict[str, Any]], camera_id: str, camera_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze detections and generate threats"""
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
            is_high_risk = False
            
            # 🔫 WEAPON DETECTION = INSTANT CRITICAL
            if det.get('weapon'):
                threat_score = 1.0
                threat_behaviors.append('weapon_detected')
                weapon_type = det['weapon']['type']
                threat_type = f"armed_person_{weapon_type}"
                is_high_risk = True
                self.high_risk_tracks.add(track_id)
                logger.critical(f"🔫 WEAPON: Track {track_id} - {weapon_type}")
            
            # 👤 PERSON BEHAVIOR ANALYSIS
            if det['class'] == 'person':
                person_threat = self._analyze_person_threat(det, track_id, camera_id, current_time)
                
                if person_threat['score'] > threat_score:
                    threat_score = person_threat['score']
                    threat_behaviors.extend(person_threat['behaviors'])
                    threat_type = person_threat['type'] or threat_type
                
                if person_threat['is_high_risk']:
                    is_high_risk = True
                    self.high_risk_tracks.add(track_id)
            
            # Keep track flagged as high risk
            if track_id in self.high_risk_tracks:
                is_high_risk = True
                threat_score = max(threat_score, 0.7)
            
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
                'is_high_risk': is_high_risk,
                'metadata': {
                    'pose': det.get('pose'),
                    'weapon': det.get('weapon'),
                    'confidence': det.get('confidence', 0.0)
                }
            })
        
        # 👥 GROUP ANALYSIS
        group_threats = self._analyze_group_behaviors(detections, camera_id, current_time)
        threats.extend(group_threats)
        
        return threats
    
    def _analyze_person_threat(self, detection: Dict, track_id: int, camera_id: str, current_time: float) -> Dict:
        """Analyze person threats - STANDING, CROUCHING, CRAWLING"""
        score = 0.0
        behaviors = []
        threat_type = None
        is_high_risk = False
        
        history = self.track_history[camera_id][track_id]
        
        if len(history) < 2:
            return {'score': 0.0, 'behaviors': [], 'type': None, 'is_high_risk': False}
        
        first_time, first_pos, first_pose, _ = history[0]
        duration = current_time - first_time
        
        # Calculate movement
        distance = np.linalg.norm(np.array(detection['center']) - np.array(first_pos))
        
        pose = detection.get('pose', 'unknown')
        
        # 🤸 CRAWLING = INSTANT CRITICAL
        if pose == 'crawling':
            score = 0.95
            behaviors.append('crawling_detected')
            threat_type = 'person_crawling_infiltration'
            is_high_risk = True
            logger.critical(f"🚨 CRAWLING: Track {track_id}")
        
        # 🧎 CROUCHING 10+ SECONDS = CRITICAL
        elif pose == 'crouching':
            crouching_duration = self._get_pose_duration(history, 'crouching', current_time)
            
            if crouching_duration >= CROUCHING_THRESHOLD_SECONDS:
                score = 0.95
                behaviors.append(f'crouching_{int(crouching_duration)}s')
                threat_type = 'person_crouching_suspicious'
                is_high_risk = True
                logger.critical(f"🚨 CROUCHING: Track {track_id} for {crouching_duration:.1f}s")
            elif crouching_duration >= 3.0:
                score = 0.6
                behaviors.append('crouching_detected')
                threat_type = 'person_crouching'
        
        # ⏱️ STANDING STILL 10+ SECONDS = HIGH (LOITERING)
        elif pose == 'standing':
            if duration >= STANDING_THRESHOLD_SECONDS and distance < MAX_MOVEMENT_PIXELS:
                # Check if really stationary
                recent_positions = [pos for t, pos, p, _ in history[-20:]]
                if len(recent_positions) >= 2:
                    movements = [
                        np.linalg.norm(np.array(recent_positions[i]) - np.array(recent_positions[0]))
                        for i in range(len(recent_positions))
                    ]
                    max_movement = max(movements) if movements else 0
                    
                    if max_movement < MAX_MOVEMENT_PIXELS:
                        score = 0.85
                        behaviors.append(f'loitering_{int(duration)}s')
                        threat_type = 'person_loitering_suspicious'
                        is_high_risk = True
                        logger.warning(f"⚠️  LOITERING: Track {track_id} for {duration:.1f}s")
        
        return {
            'score': score, 
            'behaviors': behaviors, 
            'type': threat_type,
            'is_high_risk': is_high_risk
        }
    
    def _get_pose_duration(self, history, target_pose: str, current_time: float) -> float:
        """Calculate how long a person has been in a specific pose"""
        duration = 0.0
        for i in range(len(history) - 1, -1, -1):
            t, pos, pose, _ = history[i]
            if pose != target_pose:
                break
            duration = current_time - t
        return duration
    
    def _analyze_group_behaviors(self, detections: List[Dict], camera_id: str, current_time: float) -> List[Dict]:
        """Detect large groups (6+ people)"""
        threats = []
        persons = [d for d in detections if d['class'] == 'person']
        
        if len(persons) >= GROUP_SIZE_THRESHOLD:
            positions = np.array([p['center'] for p in persons])
            
            threats.append({
                'track_id': -1,
                'class': 'group',
                'score': 0.8,
                'level': 'HIGH',
                'behaviors': ['large_group_assembly'],
                'type': 'group_assembly_suspicious',
                'position': list(np.mean(positions, axis=0).astype(int)),
                'bbox': None,
                'camera_id': camera_id,
                'timestamp': current_time,
                'is_high_risk': True,
                'metadata': {'group_size': len(persons)}
            })
            logger.warning(f"👥 GROUP: {len(persons)} people detected")
        
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
                det.get('pose', 'unknown'),
                det
            ))
            
            # Keep last 5 minutes
            self.track_history[camera_id][track_id] = [
                (t, pos, pose, data) for t, pos, pose, data in self.track_history[camera_id][track_id]
                if current_time - t < 300
            ]
            
            if track_id not in self.track_first_seen:
                self.track_first_seen[track_id] = current_time
        
        # Cleanup old tracks
        for track_id in list(self.track_history[camera_id].keys()):
            if track_id not in active_tracks:
                history = self.track_history[camera_id][track_id]
                if history and (current_time - history[-1][0] > 60):
                    del self.track_history[camera_id][track_id]
                    if track_id in self.track_first_seen:
                        del self.track_first_seen[track_id]
                    if track_id in self.high_risk_tracks:
                        self.high_risk_tracks.discard(track_id)
                        logger.info(f"✅ Track {track_id} left camera")
    
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