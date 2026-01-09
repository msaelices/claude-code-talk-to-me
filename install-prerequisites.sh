#!/bin/bash

# Install prerequisites for local TTS/STT on Linux
# This script installs Whisper (STT) and Piper (TTS) with their dependencies

set -e

echo "======================================"
echo "CallMe Local Mode Prerequisites Setup"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

echo ""
echo "Installing Python packages..."
echo "=============================="

# Install Whisper with optimizations
echo "Installing faster-whisper (optimized Whisper implementation)..."
pip install --upgrade faster-whisper

# Install Piper TTS
echo "Installing Piper TTS..."
pip install --upgrade piper-tts

# Install voice activity detection
echo "Installing Silero VAD..."
pip install --upgrade silero-vad

# Install audio libraries
echo "Installing audio libraries..."
pip install --upgrade sounddevice numpy scipy

# Optional: Install streaming support
echo "Installing optional streaming support..."
pip install --upgrade websockets asyncio

echo ""
echo "Checking system audio dependencies..."
echo "======================================"

# Check for PulseAudio or PipeWire
if command -v pactl &> /dev/null; then
    echo "✓ PulseAudio/PipeWire detected"
    pactl info | grep "Server Name" || true
else
    echo "⚠ PulseAudio/PipeWire not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y pulseaudio-utils
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y pulseaudio-utils
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm pulseaudio
    else
        echo "Warning: Could not install PulseAudio. Please install manually."
    fi
fi

# Check for ffmpeg (useful for audio format conversion)
if command -v ffmpeg &> /dev/null; then
    echo "✓ ffmpeg detected"
else
    echo "⚠ ffmpeg not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y ffmpeg
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm ffmpeg
    else
        echo "Warning: Could not install ffmpeg. Please install manually."
    fi
fi

echo ""
echo "Creating models directory..."
echo "============================="
mkdir -p models
mkdir -p models/whisper
mkdir -p models/piper

echo ""
echo "======================================"
echo "Installation complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Download Whisper model: python3 download-models.py"
echo "2. Test audio: python3 test-audio.py"
echo "3. Configure environment: cp .env.example .env.local"
echo ""
echo "To activate the virtual environment in the future:"
echo "  source venv/bin/activate"
echo ""