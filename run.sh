#!/bin/bash
# Sport Vision — One-click Launcher
# https://github.com/MindDock/sport-vision

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ⚡ Sport Vision — AI Motion Analysis"
echo "  ====================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.9+"
    exit 1
fi

# Create venv if not exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# Download model if not exists
MODEL_PATH="models/pose_landmarker_lite.task"
if [ ! -f "$MODEL_PATH" ]; then
    echo "🧠 Downloading MediaPipe Pose model..."
    mkdir -p models
    curl -sL -o "$MODEL_PATH" \
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    echo "   ✅ Model downloaded ($(du -h "$MODEL_PATH" | cut -f1))"
fi

# Create directories
mkdir -p demo_videos uploads

echo ""
echo "  🚀 Starting Sport Vision..."
echo "  → http://localhost:8000"
echo ""
echo "  💡 Put .mp4 files in ./demo_videos/ for demos"
echo ""

# Start server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
