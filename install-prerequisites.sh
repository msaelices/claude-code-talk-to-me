#!/bin/bash

# Install prerequisites for TalkToMe cloud mode on Linux
# This script installs audio system dependencies for local microphone/speaker access

set -e

echo "======================================"
echo "TalkToMe Cloud Mode Prerequisites Setup"
echo "======================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.10+ first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VERSION"

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

# Check for ffmpeg (required for ElevenLabs MP3 to PCM conversion)
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
        echo "ffmpeg is required for audio format conversion."
    fi
fi

echo ""
echo "Installing MCP server dependencies..."
echo "====================================="
cd server && uv pip install -e . && cd ..

echo ""
echo "======================================"
echo "Installation complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Get your ElevenLabs API key from https://elevenlabs.io"
echo "2. Configure environment: cp .env.example .env.local"
echo "3. Set your API key: TALKTOME_ELEVENLABS_API_KEY=your_key_here"
echo "4. Test audio: uv run python3 test-audio.py"
echo ""
