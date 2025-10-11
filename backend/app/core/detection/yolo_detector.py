from ultralytics import YOLO
import cv2
import numpy as np
from typing import List, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class YOLODetector:
    """YOLOv8 detection engine for persons, vehicles, and weapons"""
    
    def __init__(self):
        logger.info("Initializing YOLO models...")
        
        # Load models
        try:
            self.person_vehicle_model = YOLO(settings.YOLO_PERSON_MODEL)
            self.pose_model = YOLO(settings.YOLO_POSE_MODEL)
            
            # Load custom weapon detector if available
            try:
                self.weapon_model = YOLO(settings.YOLO_WEAPON_MODEL)
                self.has_weapon_detector = True
            except:
                logger.warning("Weapon detector model not found. Weapon detection disabled.")
                self.has_weapon_detector = False
            
            logger.info("YOLO models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO models: {e}")
            raise
        
        # Classes we care about from COCO dataset
        self.target_classes = {
            'person', 'car', 'truck', 'bus', 'motorcycle', 'bicycle'
        }
        
        # Weapon classes (if custom model is trained)
        self.weapon_classes = {
            'pistol', 'rifle', 'knife', 'grenade', 'rpg'
        }
    
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run detection on a single frame
        
        Returns:
            List of detection dictionaries with bbox, class, confidence, pose
        """
        detections = []
        
        try:
            # Run person/vehicle detection
            results = self.person_vehicle_model.track(
                frame,
                persist=True,
                conf=settings.DETECTION_CONFIDENCE,
                verbose=False,
                tracker="bytetrack.yaml"
            )
            
            # Run pose estimation for persons
            pose_results = self.pose_model(
                frame,
                conf=settings.DETECTION_CONFIDENCE,
                verbose=False
            )
            
            # Run weapon detection if available
            weapon_detections = {}
            if self.has_weapon_detector:
                weapon_results = self.weapon_model(
                    frame,
                    conf=settings.WEAPON_CONFIDENCE,
                    verbose=False
                )
                weapon_detections = self._process_weapon_results(weapon_results)
            
            # Process results
            if len(results) > 0:
                boxes = results[0].boxes
                
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = self.person_vehicle_model.names[cls]
                    
                    # Only process target classes
                    if class_name not in self.target_classes:
                        continue
                    
                    # Get track ID
                    track_id = int(box.id[0]) if box.id is not None else -1
                    
                    # Build detection object
                    detection = {
                        'track_id': track_id,
                        'class': class_name,
                        'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'center': [int((x1 + x2) / 2), int((y1 + y2) / 2)],
                        'pose': None,
                        'weapon': None
                    }
                    
                    # Add pose for persons
                    if class_name == 'person' and pose_results[0].keypoints is not None:
                        detection['pose'] = self._extract_pose(pose_results[0], i)
                    
                    # Check if this detection overlaps with a weapon
                    if class_name == 'person':
                        detection['weapon'] = self._check_weapon_association(
                            detection['bbox'], 
                            weapon_detections
                        )
                    
                    detections.append(detection)
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
        
        return detections
    
    def _extract_pose(self, pose_result, detection_idx: int) -> str:
        """Extract and classify pose from keypoints"""
        try:
            keypoints = pose_result.keypoints.xy[detection_idx].cpu().numpy()
            
            if len(keypoints) < 17:  # COCO pose has 17 keypoints
                return 'unknown'
            
            # Keypoint indices (COCO format)
            # 0: nose, 5: left_shoulder, 6: right_shoulder
            # 7: left_elbow, 8: right_elbow, 9: left_wrist, 10: right_wrist
            # 11: left_hip, 12: right_hip, 13: left_knee, 14: right_knee
            
            # Check if crouching (knees significantly above hips)
            if (keypoints[13][1] > keypoints[11][1] + 50 and 
                keypoints[14][1] > keypoints[12][1] + 50):
                return 'crouching'
            
            # Check if arms raised (wrists above shoulders)
            if (keypoints[9][1] < keypoints[5][1] - 30 or 
                keypoints[10][1] < keypoints[6][1] - 30):
                return 'arms_raised'
            
            # Check if lying/crawling (nose close to hip level)
            if keypoints[0][1] > keypoints[11][1] - 50:
                return 'crawling'
            
            return 'standing'
            
        except Exception as e:
            logger.debug(f"Pose extraction error: {e}")
            return 'unknown'
    
    def _process_weapon_results(self, weapon_results) -> Dict[str, Any]:
        """Process weapon detection results"""
        weapons = {}
        
        if len(weapon_results) > 0:
            boxes = weapon_results[0].boxes
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                weapon_type = self.weapon_model.names[cls]
                
                weapons[i] = {
                    'type': weapon_type,
                    'confidence': conf,
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'center': [int((x1 + x2) / 2), int((y1 + y2) / 2)]
                }
        
        return weapons
    
    def _check_weapon_association(self, person_bbox: List[int], 
                                   weapons: Dict) -> Dict[str, Any]:
        """Check if a weapon overlaps with a person detection"""
        if not weapons:
            return None
        
        px1, py1, px2, py2 = person_bbox
        
        for weapon_id, weapon in weapons.items():
            wx1, wy1, wx2, wy2 = weapon['bbox']
            
            # Check for intersection
            if not (wx2 < px1 or wx1 > px2 or wy2 < py1 or wy1 > py2):
                return {
                    'type': weapon['type'],
                    'confidence': weapon['confidence']
                }
        
        return None
    
    def draw_detections(self, frame: np.ndarray, 
                       detections: List[Dict[str, Any]],
                       threats: List[Dict[str, Any]] = None) -> np.ndarray:
        """Draw bounding boxes and labels on frame"""
        annotated = frame.copy()
        
        # Create threat score lookup
        threat_lookup = {}
        if threats:
            for threat in threats:
                threat_lookup[threat['track_id']] = threat
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            track_id = det['track_id']
            class_name = det['class']
            
            # Determine color based on threat level
            threat = threat_lookup.get(track_id)
            if threat:
                score = threat['score']
                if score >= settings.CRITICAL_THREAT_SCORE:
                    color = (0, 0, 255)  # Red
                elif score >= settings.HIGH_THREAT_SCORE:
                    color = (0, 165, 255)  # Orange
                elif score >= settings.MEDIUM_THREAT_SCORE:
                    color = (0, 255, 255)  # Yellow
                else:
                    color = (0, 255, 0)  # Green
            else:
                color = (0, 255, 0)  # Green (normal)
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Build label
            label = f"{class_name} #{track_id}"
            if det['pose']:
                label += f" | {det['pose']}"
            if det['weapon']:
                label += f" | WEAPON: {det['weapon']['type']}"
            if threat:
                label += f" | {threat['threat_level']} ({threat['score']:.2f})"
            
            # Draw label background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(annotated, 
                         (x1, y1 - label_size[1] - 10),
                         (x1 + label_size[0], y1),
                         color, -1)
            
            # Draw label text
            cv2.putText(annotated, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return annotated