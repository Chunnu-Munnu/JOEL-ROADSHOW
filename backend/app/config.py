"""
Configuration settings for TRINETRA
"""
import os
from pathlib import Path

class Settings:
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    MODELS_DIR = BASE_DIR / "models"
    SNAPSHOTS_DIR = BASE_DIR / "snapshots"
    
    # YOLO Models
    YOLO_PERSON_MODEL = str(MODELS_DIR / "yolov8n.pt")
    YOLO_POSE_MODEL = str(MODELS_DIR / "yolov8n-pose.pt")
    YOLO_WEAPON_MODEL = str(MODELS_DIR / "weapon_yolov8.pt")
    
    # Threat Detection Thresholds
    STANDING_THRESHOLD_SECONDS = 10.0      # 10 seconds → HIGH
    CROUCHING_THRESHOLD_SECONDS = 10.0     # 10 seconds → CRITICAL
    CRAWLING_IMMEDIATE = True              # Instant HIGH risk
    GROUP_SIZE_THRESHOLD = 6               # 6+ people → HIGH
    
    # Weapon Detection
    WEAPON_CONFIDENCE_THRESHOLD = 0.5      # Minimum confidence
    WEAPON_FRAME_CONSISTENCY = 3           # Must appear in 3+ frames
    
    # Movement Detection (for loitering)
    MAX_MOVEMENT_PIXELS = 100              # Max pixels to still be "stationary"
    
    # Threat Levels
    HIGH_THREAT_SCORE = 0.7                # Score >= 0.7 triggers notification
    CRITICAL_THREAT_SCORE = 0.9            # Score >= 0.9 is CRITICAL
    
    # Blockchain
    BLOCKCHAIN_RPC = os.getenv("BLOCKCHAIN_RPC", "http://127.0.0.1:8545")
    CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
    
    # Roboflow (fallback for weapons)
    ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
    ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID", "")
    
    # Snapshot Storage
    MAX_SNAPSHOTS = 100                    # Keep last 100 snapshots
    SNAPSHOT_RETENTION_HOURS = 24          # Delete after 24 hours

settings = Settings()