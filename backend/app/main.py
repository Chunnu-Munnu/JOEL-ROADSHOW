from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import cv2
import asyncio
import json
import base64
from detection import TRINETRADetector
from threat_scoring import ThreatAnalyzer

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize detection engine
detector = TRINETRADetector()
analyzer = ThreatAnalyzer()

@app.get("/")
async def root():
    return {"status": "TRINETRA Active", "version": "1.0"}

@app.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    await websocket.accept()
    
    # Open webcam (0 = default camera)
    cap = cv2.VideoCapture(0)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run detection
            detections = detector.detect(frame)
            
            # Analyze threats
            threats = analyzer.analyze(detections, frame)
            
            # Draw bounding boxes
            annotated_frame = detector.draw_detections(frame, detections, threats)
            
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Send to frontend
            await websocket.send_json({
                "frame": frame_base64,
                "detections": detections,
                "threats": threats,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            await asyncio.sleep(0.1)  # ~10 FPS
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cap.release()
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)