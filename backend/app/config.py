from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "TRINETRA"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # YOLO Models
    YOLO_PERSON_MODEL: str = "models/yolov8n.pt"
    YOLO_POSE_MODEL: str = "models/yolov8n-pose.pt"
    YOLO_WEAPON_MODEL: str = "models/weapon_yolov8.pt"

    # Detection Thresholds
    DETECTION_CONFIDENCE: float = 0.5
    WEAPON_CONFIDENCE: float = 0.6
    CAMOUFLAGE_CONFIDENCE: float = 0.4

    STANDING_THRESHOLD_SECONDS: float = 10.0
    CROUCHING_THRESHOLD_SECONDS: float = 10.0
    CAMOUFLAGE_LOW_RISK_SECONDS: float = 120.0
    VEHICLE_STATIONARY_THRESHOLD: float = 300.0
    GROUP_SIZE_THRESHOLD: int = 6

    # Alert Thresholds
    CRITICAL_THREAT_SCORE: float = 0.9
    HIGH_THREAT_SCORE: float = 0.7
    MEDIUM_THREAT_SCORE: float = 0.5

    # Snapshot Storage
    SNAPSHOT_DIR: str = "snapshots"
    SNAPSHOT_RETENTION_HOURS: int = 24

    # Camera Configuration
    MAX_CAMERAS: int = 10
    VIDEO_FPS: int = 10
    FRAME_WIDTH: int = 1280
    FRAME_HEIGHT: int = 720

    # Blockchain
    BLOCKCHAIN_RPC_URL: str = "http://localhost:8545"
    BLOCKCHAIN_CONTRACT_ADDRESS: Optional[str] = None

    # Roboflow Inference config (ADDED these lines!)
    ROBOFLOW_API_KEY: Optional[str] = None
    ROBOFLOW_WORKSPACE: Optional[str] = None
    ROBOFLOW_WORKFLOW_ID: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()
