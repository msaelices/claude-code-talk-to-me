#!/bin/bash

# Install prerequisites for local TTS/STT on Linux and macOS
# This script installs Whisper (STT) and Piper (TTS) with their dependencies

set -e

echo "======================================"
echo "TalkToMe Local Mode Prerequisites Setup"
echo "======================================"
echo ""

# Detect operating system
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=Linux;;
    Darwin*)    PLATFORM=macOS;;
    *)          PLATFORM="UNKNOWN:${OS}"
esac

echo "Detected platform: $PLATFORM"
echo ""

# macOS-specific: Check for Homebrew
if [ "$PLATFORM" = "macOS" ]; then
    if ! command -v brew &> /dev/null; then
        echo "Error: Homebrew is not installed. Please install it first:"
        echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        exit 1
    fi
    echo "✓ Homebrew detected"
fi

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
echo "Installing Python packages with uv..."
echo "======================================"

# Install Whisper with optimizations
echo "Installing faster-whisper (optimized Whisper implementation)..."
uv pip install --upgrade faster-whisper

# Install Piper TTS
echo "Installing Piper TTS..."
uv pip install --upgrade piper-tts

# Install voice activity detection
echo "Installing Silero VAD..."
uv pip install --upgrade silero-vad

# Install audio libraries
echo "Installing audio libraries..."
uv pip install --upgrade sounddevice numpy scipy

# Optional: Install streaming support
echo "Installing optional streaming support..."
uv pip install --upgrade websockets asyncio

# Install MCP server dependencies
echo "Installing MCP server dependencies..."
cd server && uv pip install -e . && cd ..

echo ""
echo "Checking system audio dependencies..."
echo "======================================"

if [ "$PLATFORM" = "macOS" ]; then
    # macOS uses CoreAudio (built-in, no installation needed)
    echo "✓ CoreAudio detected (built-in on macOS)"

    # Install PortAudio for sounddevice support
    if ! brew list portaudio &> /dev/null; then
        echo "Installing PortAudio..."
        brew install portaudio
    else
        echo "✓ PortAudio detected"
    fi

    # Check for ffmpeg
    if command -v ffmpeg &> /dev/null; then
        echo "✓ ffmpeg detected"
    else
        echo "⚠ ffmpeg not found. Installing..."
        brew install ffmpeg
    fi
else
    # Linux: Check for PulseAudio or PipeWire
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
echo "1. Download models: uv run python3 download-models.py"
echo "2. Test audio: uv run python3 test-audio.py"
echo "3. Configure environment: cp .env.example .env.local"
echo ""