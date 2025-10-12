"""
app/core/detection/yolo_detector.py
YOLO detection with weapon confidence tracking (3+ frames)
"""
from ultralytics import YOLO
from collections import defaultdict
import numpy as np
import cv2
import os
import logging

logger = logging.getLogger(__name__)


class YOLODetector:
    """YOLO detector with multi-frame weapon validation"""

    def __init__(self):
        logger.info("🔄 Initializing YOLO models...")

        self.target_classes = {'person', 'car', 'truck', 'bus', 'motorcycle', 'bicycle'}
        self.has_weapon_detector = False
        self.weapon_model = None
        
        # Track weapon detections: {track_id: [(frame_num, confidence, type), ...]}
        self.weapon_tracking = defaultdict(list)
        self.frame_number = 0

        try:
            # Load models from environment or default paths
            yolo_person = os.getenv("YOLO_PERSON_MODEL", "models/yolov8n.pt")
            yolo_pose = os.getenv("YOLO_POSE_MODEL", "models/yolov8n-pose.pt")
            yolo_weapon = os.getenv("YOLO_WEAPON_MODEL", "models/weapon_yolov8.pt")

            self.person_vehicle_model = YOLO(yolo_person)
            self.pose_model = YOLO(yolo_pose)

            # Load weapon detector if available
            if os.path.exists(yolo_weapon):
                try:
                    self.weapon_model = YOLO(yolo_weapon)
                    self.has_weapon_detector = True
                    logger.info("✅ Weapon detection model loaded")
                except Exception as e:
                    logger.warning(f"⚠️  Weapon model failed: {e}")
            else:
                logger.warning("⚠️  No weapon detection model found")

            logger.info("✅ YOLO initialization complete")
        except Exception as e:
            logger.error(f"❌ Model loading failed: {e}")
            raise

    def detect(self, frame: np.ndarray):
        """Run detection pipeline"""
        detections = []
        self.frame_number += 1
        
        try:
            # Person/vehicle tracking
            results = self.person_vehicle_model.track(
                frame, 
                persist=True, 
                conf=0.3,  # Confidence threshold
                tracker="bytetrack.yaml"
            )
            
            # Pose estimation
            pose_results = self.pose_model(frame, conf=0.3)

            # Weapon detection
            weapon_detections = {}
            if self.has_weapon_detector:
                weapon_results = self.weapon_model(frame, conf=0.4)  # Higher threshold
                weapon_detections = self._process_weapon_results(weapon_results)

            # Process detections
            if len(results) > 0 and hasattr(results[0], 'boxes'):
                boxes = results[0].boxes
                
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = self.person_vehicle_model.names[cls]

                    if class_name not in self.target_classes:
                        continue

                    track_id = int(box.id[0]) if box.id is not None else -1
                    
                    detection = {
                        'track_id': track_id,
                        'class': class_name,
                        'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'center': [int((x1 + x2) / 2), int((y1 + y2) / 2)],
                        'pose': None,
                        'weapon': None
                    }
                    
                    # Extract pose for persons
                    if class_name == 'person':
                        if pose_results and hasattr(pose_results[0], "keypoints"):
                            detection['pose'] = self._extract_pose(pose_results[0], i)
                        
                        # Check weapon with consistency requirement
                        if track_id >= 0:
                            weapon = self._check_weapon_consistency(
                                track_id, 
                                detection['bbox'], 
                                weapon_detections
                            )
                            detection['weapon'] = weapon
                    
                    detections.append(detection)
                    
        except Exception as e:
            logger.error(f"❌ Detection error: {e}")
            
        # Cleanup old weapon tracking
        self._cleanup_weapon_tracking()
        
        return detections

    def _extract_pose(self, pose_result, detection_idx: int) -> str:
        """Extract pose from keypoints - CRAWLING, CROUCHING, STANDING"""
        try:
            if detection_idx >= len(pose_result.keypoints.xy):
                return 'unknown'
                
            keypoints = pose_result.keypoints.xy[detection_idx].cpu().numpy()
            
            if len(keypoints) < 17:
                return 'unknown'
            
            # COCO keypoint indices
            nose = keypoints[0]
            left_hip = keypoints[11]
            right_hip = keypoints[12]
            left_knee = keypoints[13]
            right_knee = keypoints[14]
            
            # Check if keypoints are valid
            if nose[0] == 0 or left_hip[0] == 0 or right_hip[0] == 0:
                return 'unknown'
            
            avg_hip_y = (left_hip[1] + right_hip[1]) / 2
            
            # CRAWLING: nose close to hip level (low position)
            if nose[1] >= avg_hip_y - 40:
                return 'crawling'
            
            # CROUCHING: knees significantly above hips (bent position)
            if (left_knee[0] > 0 and right_knee[0] > 0 and
                left_knee[1] < left_hip[1] - 50 and 
                right_knee[1] < right_hip[1] - 50):
                return 'crouching'
            
            # STANDING: default upright
            return 'standing'
            
        except Exception as e:
            logger.debug(f"Pose error: {e}")
            return 'unknown'

    def _process_weapon_results(self, weapon_results):
        """Process YOLO weapon detections"""
        weapons = {}
        
        if len(weapon_results) > 0 and hasattr(weapon_results[0], 'boxes'):
            boxes = weapon_results[0].boxes
            
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                weapon_type = self.weapon_model.names[cls]
                
                # Only high confidence
                if conf >= 0.4:
                    weapons[i] = {
                        'type': weapon_type,
                        'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'center': [int((x1 + x2) / 2), int((y1 + y2) / 2)]
                    }
        
        return weapons

    def _check_weapon_consistency(self, track_id, person_bbox, weapons):
        """
        Weapon detection with CONSISTENCY (3+ frames)
        Prevents false positives
        """
        if not weapons:
            return None
            
        px1, py1, px2, py2 = person_bbox
        
        # Check for overlap
        detected_weapon = None
        for weapon in weapons.values():
            wx1, wy1, wx2, wy2 = weapon['bbox']
            
            # Intersection check
            if not (wx2 < px1 or wx1 > px2 or wy2 < py1 or wy1 > py2):
                detected_weapon = weapon
                break
        
        if detected_weapon:
            # Add to tracking history
            self.weapon_tracking[track_id].append((
                self.frame_number,
                detected_weapon['confidence'],
                detected_weapon['type']
            ))
            
            # Keep last 10 frames only
            self.weapon_tracking[track_id] = self.weapon_tracking[track_id][-10:]
            
            # Check consistency: detected in 3+ of last 5 frames
            recent = [
                (f, c, t) for f, c, t in self.weapon_tracking[track_id]
                if self.frame_number - f <= 5
            ]
            
            if len(recent) >= 3:
                # Get most common weapon type
                types = [t for f, c, t in recent]
                most_common = max(set(types), key=types.count)
                avg_conf = np.mean([c for f, c, t in recent])
                
                logger.warning(f"🔫 CONFIRMED WEAPON: Track {track_id} - {most_common} (frames: {len(recent)})")
                
                return {
                    'type': most_common,
                    'confidence': float(avg_conf),
                    'frame_count': len(recent)
                }
        
        return None
    
    def _cleanup_weapon_tracking(self):
        """Remove stale weapon tracking data"""
        to_remove = []
        
        for track_id, frames in self.weapon_tracking.items():
            # Remove if no detections in last 30 frames
            recent = [f for f, c, t in frames if self.frame_number - f <= 30]
            if not recent:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.weapon_tracking[track_id]

    def draw_detections(self, frame, detections, threats=None):
        """Draw bounding boxes - RED for high risk"""
        annotated = frame.copy()
        threat_lookup = {th['track_id']: th for th in threats} if threats else {}
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            track_id = det['track_id']
            class_name = det['class']
            
            # Default GREEN
            color = (0, 255, 0)
            thickness = 2
            
            # Check threat status
            threat = threat_lookup.get(track_id)
            
            if threat and threat.get('is_high_risk'):
                # RED for high risk (stays red)
                color = (0, 0, 255)
                thickness = 3
            elif threat:
                score = threat['score']
                if score >= 0.9:
                    color = (0, 0, 255)  # Red
                    thickness = 3
                elif score >= 0.7:
                    color = (0, 165, 255)  # Orange
                elif score >= 0.5:
                    color = (0, 255, 255)  # Yellow
            
            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
            
            # Build label
            label_parts = [f"{class_name} #{track_id}"]
            
            if det['pose'] and det['pose'] != 'unknown':
                label_parts.append(det['pose'].upper())
            
            if det['weapon']:
                weapon_label = f"⚠️  {det['weapon']['type'].upper()}"
                if 'frame_count' in det['weapon']:
                    weapon_label += f" ({det['weapon']['frame_count']}f)"
                label_parts.append(weapon_label)
            
            if threat:
                label_parts.append(f"{threat['level']} ({threat['score']:.2f})")
            
            label = " | ".join(label_parts)
            
            # Draw label background
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_thickness = 2
            (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, font_thickness)
            
            cv2.rectangle(
                annotated, 
                (x1, y1 - text_height - 10), 
                (x1 + text_width, y1), 
                color, 
                -1
            )
            cv2.putText(
                annotated, 
                label, 
                (x1, y1 - 5), 
                font, 
                font_scale, 
                (255, 255, 255), 
                font_thickness
            )
        
        return annotated