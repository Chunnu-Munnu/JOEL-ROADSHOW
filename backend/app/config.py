from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "TRINETRA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://trinetra:secure_password@localhost:5432/trinetra_db"
    DATABASE_POOL_SIZE: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # YOLO Models
    YOLO_PERSON_MODEL: str = "models/yolov8n.pt"
    YOLO_POSE_MODEL: str = "models/yolov8n-pose.pt"
    YOLO_WEAPON_MODEL: str = "models/weapon_detector_v1.pt"
    
    # Detection Thresholds
    DETECTION_CONFIDENCE: float = 0.5
    WEAPON_CONFIDENCE: float = 0.7
    TRACKING_MAX_AGE: int = 30
    TRACKING_MIN_HITS: int = 3
    
    # Threat Scoring
    LOITER_THRESHOLD_SECONDS: float = 15.0
    VEHICLE_STATIONARY_THRESHOLD: float = 300.0  # 5 minutes
    RAPID_MOVEMENT_THRESHOLD: float = 150.0  # pixels per second
    
    # Alert Thresholds
    CRITICAL_THREAT_SCORE: float = 0.9
    HIGH_THREAT_SCORE: float = 0.7
    MEDIUM_THREAT_SCORE: float = 0.5
    
    # Notifications
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    ALERT_PHONE_NUMBERS: list = ["+919876543210"]  # Military contacts
    
    SENDGRID_API_KEY: Optional[str] = None
    ALERT_EMAIL_ADDRESSES: list = ["security@military.gov.in"]
    
    # MinIO/S3 Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "trinetra-videos"
    MINIO_SECURE: bool = False
    
    # Video Storage
    VIDEO_CLIP_DURATION: int = 30  # seconds
    VIDEO_RETENTION_DAYS: int = 30
    
    # Camera Configuration
    MAX_CAMERAS: int = 100
    VIDEO_FPS: int = 10  # Process at 10 FPS to save resources
    FRAME_WIDTH: int = 1280
    FRAME_HEIGHT: int = 720
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MESSAGE_QUEUE_SIZE: int = 100
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()