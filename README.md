# 🔱 VISION_X_TRINETRAA

> **Real-time AI-powered surveillance system** with YOLO object detection, threat scoring, WebSocket video streaming, and blockchain incident logging.

---

## 📁 Project Structure

```
VISION_X_TRINETRAA/
├── backend/               # FastAPI server — YOLO detection, WebSocket stream
│   ├── app/
│   │   ├── main.py        # Server entry point
│   │   ├── core/          # Detection & threat scoring logic
│   │   └── api/           # REST API routes
│   ├── test_camera.html   # Frontend UI (open this in browser)
│   ├── requirements.txt   # Python dependencies
│   └── venv/              # Python virtual environment
├── frontend/              # (Placeholder — UI lives in backend/test_camera.html)
├── blockchain/            # Hardhat smart contracts for incident logging
│   ├── contracts/
│   ├── scripts/
│   └── hardhat.config.js
└── README.md
```

---

## ⚙️ Prerequisites

Make sure you have these installed before running anything:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.9+ | https://python.org |
| Node.js | 16+ | https://nodejs.org |
| Yarn | Latest | `npm install -g yarn` |
| Git | Any | https://git-scm.com |

---

## 🚀 How to Run (Step by Step)

You need **2 terminals** to run the full system. Open them separately.

---

### 🖥️ TERMINAL 1 — Backend (FastAPI + YOLO Server)

> **One-time setup** (only needed the first time):

```powershell
cd "d:\Amogh Projects\VISION_X_TRINETRAA\backend"

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install all Python dependencies
pip install -r requirements.txt
```

> **Every time you run the project:**

```powershell
cd "d:\Amogh Projects\VISION_X_TRINETRAA\backend"

# Activate virtual environment
.\venv\Scripts\activate

# Start the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

✅ Backend is live at: **http://localhost:8000**  
📚 API Docs (Swagger): **http://localhost:8000/docs**  
📡 WebSocket endpoint: **ws://localhost:8000/ws/video**

---

### 🌐 TERMINAL 2 — Frontend (Camera UI)

```powershell
cd "d:\Amogh Projects\VISION_X_TRINETRAA\backend"

# Serve the frontend over a local HTTP server
python -m http.server 5500
```

Then open your browser and go to:  
👉 **http://localhost:5500/test_camera.html**

> ⚠️ **Do NOT open `test_camera.html` by double-clicking the file.**  
> It MUST be served via a local HTTP server — otherwise the WebSocket connection will be blocked by the browser's security policy.

---

### ⛓️ TERMINAL 3 — Blockchain (Optional — for incident logging)

> **One-time setup:**

```powershell
cd "d:\Amogh Projects\VISION_X_TRINETRAA\blockchain"

# Install dependencies
yarn install
```

> **Start local blockchain node:**

```powershell
cd "d:\Amogh Projects\VISION_X_TRINETRAA\blockchain"
npx hardhat node
```

> **Deploy smart contracts** (open a 4th terminal while node is running):

```powershell
cd "d:\Amogh Projects\VISION_X_TRINETRAA\blockchain"
npx hardhat run scripts/deploy.js --network localhost
```

---

## 📋 Quick Reference — All Commands at a Glance

| Terminal | Command | What it does |
|----------|---------|--------------|
| 1 | `cd backend` then `.\venv\Scripts\activate` | Activates Python env |
| 1 | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | Starts the AI backend |
| 2 | `cd backend` then `python -m http.server 5500` | Serves the frontend |
| Browser | Open `http://localhost:5500/test_camera.html` | Open the camera UI |
| 3 *(optional)* | `cd blockchain` then `npx hardhat node` | Starts local blockchain |
| 4 *(optional)* | `npx hardhat run scripts/deploy.js --network localhost` | Deploys contracts |

---

## 🔌 System Architecture

```
[Webcam / Drone Camera]
        ↓
[FastAPI Backend — port 8000]
   ├── YOLO Object Detection
   ├── Threat Scorer
   └── WebSocket Stream (/ws/video)
        ↓
[Browser UI — port 5500]
   ├── Live annotated video feed
   ├── Real-time detection list
   └── Threat alert panel
        ↓
[Blockchain — Hardhat]
   └── Immutable incident logging (optional)
```

---

## 🎥 Features

- 🔴 **Live Camera Feed** — Real-time video with YOLO bounding boxes
- 🎯 **Object Detection** — Detects people, weapons, suspicious activity
- ⚠️ **Threat Scoring** — Classifies threats as MEDIUM / HIGH / CRITICAL
- 📊 **Live Stats** — FPS, frame count, detection count shown in real time
- ⛓️ **Blockchain Logging** — Incidents logged on-chain via Hardhat
- 🚁 **Drone Ready** — Swap webcam for drone RTSP stream with 1 line change

---

## 🚁 Connect a Drone Camera

To switch from laptop webcam to a drone/IP camera stream, edit **one line** in `backend/app/main.py`:

```python
# Line 114 — change this:
cap = cv2.VideoCapture(0)              # laptop webcam

# To this (drone/IP cam RTSP stream):
cap = cv2.VideoCapture("rtsp://192.168.1.XXX:8554")
```

Replace `192.168.1.XXX` with your drone/Pi's IP address on the same WiFi network.

---

## 🐛 Common Issues

| Issue | Fix |
|-------|-----|
| `Cannot open camera` error | Make sure no other app is using the webcam |
| WebSocket not connecting | Ensure backend is running on port 8000 first |
| Blank page at localhost:5500 | Make sure you're in the `backend/` folder when running `http.server` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the activated venv |
| YOLO model not loading | Check that model files exist in `backend/models/` |

---

## 📜 License

MIT License — feel free to use and modify.
