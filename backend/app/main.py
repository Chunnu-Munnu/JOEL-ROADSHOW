"""
TRINETRA - Main Application Server
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import cv2
import asyncio
import base64
from datetime import datetime
import uvicorn
import numpy as np

# CORRECT IMPORTS - Based on your folder structure
from app.core.detection.yolo_detector import YOLODetector
from app.core.analysis.threat_scorer import ThreatScorer

app = FastAPI(title="TRINETRA", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize with error handling
detector = None
analyzer = None

try:
    print("🔄 Loading YOLO detector...")
    detector = YOLODetector()
    print("✅ YOLO detector loaded!")
except Exception as e:
    print(f"⚠️  Warning: Could not load detector: {e}")

try:
    print("🔄 Loading threat scorer...")
    analyzer = ThreatScorer()
    print("✅ Threat scorer loaded!")
except Exception as e:
    print(f"⚠️  Warning: Could not load analyzer: {e}")

@app.on_event("startup")
async def startup():
    print("\n" + "="*60)
    print("🚀 TRINETRA SYSTEM STARTED")
    print("="*60)
    print(f"📡 Server: http://localhost:8000")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print("="*60 + "\n")

@app.get("/")
async def root():
    return {
        "status": "TRINETRA Active",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "detector": detector is not None,
        "analyzer": analyzer is not None
    }

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "components": {
            "detector": "loaded" if detector else "not loaded",
            "analyzer": "loaded" if analyzer else "not loaded"
        }
    }

def clean_detection_obj(det):
    """
    Returns a detection dict with all NumPy types converted to Python types.
    Only runs on final output, so does not affect YOLO internals or performance.
    """
    res = {}
    for k, v in det.items():
        if isinstance(v, np.integer):
            res[k] = int(v)
        elif isinstance(v, np.floating):
            res[k] = float(v)
        elif isinstance(v, np.ndarray):
            res[k] = v.tolist()
        else:
            res[k] = v
    return res

def clean_threat_obj(threat):
    """
    Same conversion for threat object.
    """
    res = {}
    for k, v in threat.items():
        if isinstance(v, np.integer):
            res[k] = int(v)
        elif isinstance(v, np.floating):
            res[k] = float(v)
        elif isinstance(v, np.ndarray):
            res[k] = v.tolist()
        else:
            res[k] = v
    return res

@app.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    await websocket.accept()
    print("📹 Client connected to video stream")
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        await websocket.send_json({
            "error": "Cannot open camera"
        })
        await websocket.close()
        return
    
    try:
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            frame = cv2.resize(frame, (854, 480))
            
            # Run detection
            detections = []
            if detector:
                try:
                    detections = detector.detect(frame)
                except Exception as e:
                    print(f"Detection error: {e}")
            
            clean_detections = [clean_detection_obj(det) for det in detections]

            # Analyze threats
            threats = []
            if analyzer and detections:
                try:
                    camera_info = {
                        'zone_name': 'Default Zone',
                        'zone_type': 'public',
                        'restricted_zone': False
                    }
                    threats = analyzer.analyze_threats(
                        clean_detections, 
                        'laptop_cam',
                        camera_info
                    )
                except Exception as e:
                    print(f"Threat analysis error: {e}")
            
            clean_threats = [clean_threat_obj(threat) for threat in threats]

            # Draw boxes
            annotated_frame = frame.copy()
            if detector and clean_detections:
                try:
                    annotated_frame = detector.draw_detections(
                        frame, clean_detections, clean_threats
                    )
                except Exception as e:
                    print(f"Drawing error: {e}")
            
            # Encode and send
            _, buffer = cv2.imencode('.jpg', annotated_frame,
                                     [cv2.IMWRITE_JPEG_QUALITY, 65])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            response = {
                "frame": frame_base64,
                "detections": clean_detections,
                "threats": clean_threats,
                "timestamp": datetime.now().isoformat(),
                "frame_number": int(frame_count)
            }
            try:
                await websocket.send_json(response)
            except TypeError as e:
                print("❌ Serialization error:", e)
                print("❌ Problematic data:", response)
            
            await asyncio.sleep(0.033)  # ~30fps target
            
    except WebSocketDisconnect:
        print("📹 Client disconnected")
    except Exception as e:
        print(f"❌ Stream error: {e}")
    finally:
        cap.release()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
