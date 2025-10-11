from ultralytics import YOLO
from inference.models.utils import get_roboflow_model
from dotenv import load_dotenv
import numpy as np
import cv2
import os
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class YOLODetector:
    """YOLOv8 detection engine for persons, vehicles, and weapons"""

    def __init__(self):
        logger.info("Initializing YOLO & Roboflow models...")

        self.target_classes = {'person', 'car', 'truck', 'bus', 'motorcycle', 'bicycle'}
        self.weapon_classes = {'pistol', 'rifle', 'knife', 'grenade', 'rpg'}
        self.has_weapon_detector = False
        self.weapon_model = None
        self.roboflow_model = None

        try:
            # Load YOLO models from environment variables, or swap to direct paths
            yolo_person = os.environ.get("YOLO_PERSON_MODEL")
            yolo_pose = os.environ.get("YOLO_POSE_MODEL")
            yolo_weapon = os.environ.get("YOLO_WEAPON_MODEL")

            self.person_vehicle_model = YOLO(yolo_person)
            self.pose_model = YOLO(yolo_pose)

            # Try load weapon detector
            if yolo_weapon:
                try:
                    self.weapon_model = YOLO(yolo_weapon)
                    self.has_weapon_detector = True
                    logger.info("Loaded YOLO weapon model.")
                except Exception as e:
                    logger.warning(f"Could not load YOLO weapon model: {e}")

            # Fallback to Roboflow for weapons if YOLO not present
            if not self.has_weapon_detector:
                rf_model_id = os.environ.get("ROBOFLOW_MODEL_ID")
                rf_api_key = os.environ.get("ROBOFLOW_API_KEY")
                if rf_model_id and rf_api_key:
                    self.roboflow_model = get_roboflow_model(model_id=rf_model_id, api_key=rf_api_key)
                    logger.info(f"Loaded Roboflow model {rf_model_id}")
                else:
                    logger.error("Roboflow model id or API key missing!")

            logger.info("Model initialization complete.")
        except Exception as e:
            logger.error(f"Failed to load detection models: {e}")
            raise

    def detect(self, frame: np.ndarray):
        detections = []
        try:
            # -- Person/vehicle detection
            results = self.person_vehicle_model.track(frame, persist=True, conf=0.25, tracker="bytetrack.yaml")
            pose_results = self.pose_model(frame, conf=0.25)

            # -- Weapon detection
            weapon_detections = {}
            if self.has_weapon_detector and self.weapon_model:
                weapon_results = self.weapon_model(frame, conf=0.2)
                weapon_detections = self._process_weapon_results(weapon_results)
            elif self.roboflow_model:
                rf_result = self.roboflow_model.infer(image=frame)
                weapon_detections = self._process_roboflow_weapons(rf_result)

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
                        'center': [int((x1 + x2) // 2), int((y1 + y2) // 2)],
                        'pose': None,
                        'weapon': None
                    }
                    # Add pose for persons
                    if class_name == 'person' and pose_results and hasattr(pose_results[0], "keypoints"):
                        detection['pose'] = self._extract_pose(pose_results[0], i)
                    # Check for weapon overlap
                    if class_name == 'person':
                        detection['weapon'] = self._check_weapon_association(detection['bbox'], weapon_detections)
                    detections.append(detection)
        except Exception as e:
            logger.error(f"Detection error: {e}")
        return detections

    def _extract_pose(self, pose_result, detection_idx: int) -> str:
        """Extract and classify pose from keypoints"""
        try:
            keypoints = pose_result.keypoints.xy[detection_idx].cpu().numpy()
            if len(keypoints) < 17:
                return 'unknown'
            # COCO indices: 0-nose, 5-L.sh, 6-R.sh, 7-L.el, 8-R.el, 9-L.w, 10-R.w, 11-L.hip, 12-R.hip, 13-L.knee, 14-R.knee
            # Crouch: knees above hips
            if (keypoints[13][1] > keypoints[11][1] + 50 and keypoints[14][1] > keypoints[12][1] + 50):
                return 'crouching'
            # Arms raised: wrists above shoulders
            if (keypoints[9][1] < keypoints[5][1] - 30 or keypoints[10][1] < keypoints[6][1] - 30):
                return 'arms_raised'
            # Crawling: nose near hips
            if keypoints[0][1] > keypoints[11][1] - 50:
                return 'crawling'
            return 'standing'
        except Exception as e:
            logger.debug(f"Pose extraction error: {e}")
            return 'unknown'

    def _process_weapon_results(self, weapon_results):
        """Process weapon detection results (YOLO)"""
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
                    'center': [int((x1 + x2) // 2), int((y1 + y2) // 2)]
                }
        return weapons

    def _process_roboflow_weapons(self, rf_result):
        """Process weapon detection results (Roboflow)"""
        weapons = {}
        if not rf_result or "predictions" not in rf_result:
            return weapons
        i = 0
        for pred in rf_result["predictions"]:
            if pred.get("class") in ["weapon", "knife", "gun"]:
                box = pred["bounding_box"]
                weapons[i] = {
                    'type': pred["class"],
                    'confidence': pred["confidence"],
                    'bbox': [
                        int(box["x"]),
                        int(box["y"]),
                        int(box["x"] + box["width"]),
                        int(box["y"] + box["height"])
                    ],
                    'center': [
                        int(box["x"] + box["width"] // 2),
                        int(box["y"] + box["height"] // 2)
                    ]
                }
                i += 1
        return weapons

    def _check_weapon_association(self, person_bbox, weapons):
        """Check if a weapon overlaps with a person detection"""
        if not weapons:
            return None
        px1, py1, px2, py2 = person_bbox
        for weapon in weapons.values():
            wx1, wy1, wx2, wy2 = weapon['bbox']
            # Check AABBs for intersection
            if not (wx2 < px1 or wx1 > px2 or wy2 < py1 or wy1 > py2):
                return {'type': weapon['type'], 'confidence': weapon['confidence']}
        return None

    def draw_detections(self, frame, detections, threats=None):
        """Draw bounding boxes and labels on frame"""
        annotated = frame.copy()
        threat_lookup = {th['track_id']: th for th in threats} if threats else {}
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            track_id = det['track_id']
            class_name = det['class']
            # Color based on threat (optional)
            color = (0, 255, 0)
            threat = threat_lookup.get(track_id)
            if threat:
                score = threat['score']
                if score >= 0.9:
                    color = (0, 0, 255)
                elif score >= 0.7:
                    color = (0, 165, 255)
                elif score >= 0.5:
                    color = (0, 255, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name} #{track_id}"
            if det['pose']:
                label += f" | {det['pose']}"
            if det['weapon']:
                label += f" | WEAPON: {det['weapon']['type']}"
            if threat:
                label += f" | {threat['threat_level']} ({threat['score']:.2f})"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(annotated, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1)
            cv2.putText(annotated, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        return annotated
