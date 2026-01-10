# TalkToMe - Local Voice Communication for Claude

**Let Claude communicate with you through your computer's microphone and speakers.**

Start a task, walk away. Your computer speaks when Claude is done, stuck, or needs a decision. Have natural voice conversations with Claude using local audio.

<img src="./static/taxi-driver.jpg" width="800" alt="TalkToMe - Voice conversations with Claude">

- **Zero cost** - No phone charges, no API costs for communication (only optional OpenAI for better quality)
- **Privacy-first** - All audio processing can happen locally on your machine
- **Multi-turn conversations** - Talk through decisions naturally
- **Low latency** - Direct audio I/O without network delays
- **Tool-use composable** - Claude can e.g. do a web search while talking with you

---

## Features

- 🎙️ **Local Speech-to-Text** using Whisper (or OpenAI)
- 🔊 **Local Text-to-Speech** using Piper neural TTS (or OpenAI)
- 🎧 **System Audio Integration** - Works with PulseAudio, PipeWire, or ALSA
- 💻 **Cross-Platform** - Linux support (Windows/Mac with modifications)
- 🔒 **Privacy** - All processing can be done locally without cloud services
- ⚡ **Fast** - Sub-second response times with local models

---

## Quick Start

### 1. Install System Requirements

**Linux** (Ubuntu/Debian/Fedora):
```bash
# Install audio system (if not already present)
sudo apt-get install pulseaudio-utils  # Or pipewire-pulse for PipeWire

# Install Python 3.10+ and uv
sudo apt-get install python3
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install ffmpeg (optional, for audio format conversion)
sudo apt-get install ffmpeg
```

### 2. Install Python Dependencies

```bash
# Clone the repository
git clone https://github.com/msaelices/claude-code-talk-to-me.git
cd claude-code-talk-to-me

# Run the installation script
./install-prerequisites.sh
```

This installs:
- **faster-whisper** - Optimized Whisper for speech recognition
- **piper-tts** - Fast neural text-to-speech
- **sounddevice** - Audio I/O library

### 3. Download Models

```bash
# Download models interactively
uv run python3 download-models.py
```

Choose:
- **Whisper model**: `base` (recommended - good balance of speed/accuracy)
- **Piper voice**: `en_US-amy-medium` (recommended - natural female voice)

### 4. Test Your Audio

```bash
# Test audio devices and models
uv run python3 test-audio.py
```

This will:
- List available audio devices
- Test microphone recording
- Test speaker playback
- Verify TTS and STT are working

### 5. Configure Environment

```bash
# Copy the example configuration
cp .env.example .env.local

# Edit with your preferences (or use defaults)
nano .env.local
```

Basic configuration (defaults work for most):
```env
# Audio system (pulseaudio, pipewire, or alsa)
TALKTOME_AUDIO_SYSTEM=pulseaudio

# TTS provider (piper for local, openai for cloud)
TALKTOME_TTS_PROVIDER=piper

# STT provider (whisper for local, openai for cloud)
TALKTOME_STT_PROVIDER=whisper

# Whisper model (tiny, base, small, medium, large-v3)
TALKTOME_WHISPER_MODEL=base
```

### 6. Install the Python MCP Server

```bash
cd server
uv pip install -e .
```

### 7. Install in Claude Code

Add the MCP server to your Claude Code configuration (`~/.config/claude-code/config.json`):

```json
{
  "mcpServers": {
    "talktome": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/claude-code-talk-to-me/server",
        "-m",
        "talktome_mcp.server"
      ],
      "env": {
        "TALKTOME_AUDIO_SYSTEM": "pulseaudio",
        "TALKTOME_TTS_PROVIDER": "piper",
        "TALKTOME_STT_PROVIDER": "whisper",
        "TALKTOME_WHISPER_MODEL": "base"
      }
    }
  }
}
```

Replace `/path/to/claude-code-talk-to-me` with the actual path to the repository.

### 8. Run the Server (for testing)

```bash
uv run -m talktome_mcp.server
```

You should see:
```
TalkToMe MCP server ready (Local Mode)
Audio: local
TTS: piper
STT: whisper

Microphone and speakers ready for communication
```

---

## How It Works

```
Claude Code                    TalkToMe MCP Server (local)
    │                                    │
    │  "I finished the feature..."       │
    ▼                                    ▼
Plugin ────stdio──────────────────► MCP Server
                                         │
                                         ├─► Local Audio System
                                         │   (PulseAudio/PipeWire)
                                         │
                                         ├─► Microphone Input
                                         │   └─► Whisper STT
                                         │       └─► Text transcript
                                         │
                                         └─► Speaker Output
                                             └─► Piper TTS
                                                 └─► Audio playback
```

The MCP server runs locally and directly interfaces with your system's audio.

---

## Tools

### `initiate_call`
Start an audio conversation.

```python
result = await initiate_call()
# Returns: {"success": true, "call_id": "local-1", ...}
```

### `speak`
Speak text through the active audio session.

```python
result = await speak(text="Hey! I finished the auth system. What should I work on next?")
# Returns: {"success": true, "status": "Speech sent successfully"}
```

### `get_transcript`
Get the current conversation transcript.

```python
result = await get_transcript()
# Returns: {"success": true, "transcript": [...], "call_active": true}
```

### `end_call`
End the conversation.

```python
result = await end_call()
# Returns: {"success": true, "call_id": "local-1", "duration": "2:45", ...}
```

---

## Configuration Options

### Whisper STT Models

| Model | Size | Accuracy | Speed | Use Case |
|-------|------|----------|-------|----------|
| `tiny` | 39 MB | 85% | Fastest | Quick testing |
| `base` | 74 MB | 90% | Fast | **Recommended** |
| `small` | 244 MB | 93% | Medium | Better accuracy |
| `medium` | 769 MB | 95% | Slow | High accuracy |
| `large-v3` | 1.5 GB | 98% | Slowest | Best accuracy |

### Piper TTS Voices

Download additional voices from [Hugging Face](https://huggingface.co/rhasspy/piper-voices):
- `en_US-amy-medium` - American female (recommended)
- `en_US-danny-low` - American male (fast)
- `en_GB-alan-medium` - British male
- `en_US-libritts_r-medium` - Neutral voice

### Performance Tuning

For **faster response** (lower quality):
```env
TALKTOME_WHISPER_MODEL=tiny
TALKTOME_WHISPER_COMPUTE_TYPE=int8
```

For **better quality** (slower):
```env
TALKTOME_WHISPER_MODEL=small
TALKTOME_WHISPER_DEVICE=cuda  # If you have NVIDIA GPU
```

---

## Costs

**Local Mode**: **FREE** 🎉
- No phone charges
- No cloud API costs
- All processing on your machine

**Optional Cloud Mode** (if using OpenAI):
- Speech-to-text: ~$0.006/min
- Text-to-speech: ~$0.02/min
- Total: ~$0.026/min

---

## Troubleshooting

### No Audio Output
```bash
# Check audio devices
pactl info | grep "Default Sink"

# Test speakers directly
speaker-test -t wav -c 2
```

### No Audio Input
```bash
# Check microphone
pactl info | grep "Default Source"

# Test recording
arecord -d 5 test.wav && aplay test.wav
```

### Whisper Model Not Loading
```bash
# Re-download the model
rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-*
uv run python3 test-whisper-download.py
```

### High CPU Usage
- Use smaller Whisper model (`tiny` or `base`)
- Enable int8 quantization: `TALKTOME_WHISPER_COMPUTE_TYPE=int8`

### Permission Issues
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and back in
```

---

## Advanced Usage

### GPU Acceleration (NVIDIA)

```bash
# Install CUDA support
uv pip install nvidia-cublas-cu11 nvidia-cudnn-cu11
uv pip install faster-whisper --upgrade

# Configure for GPU
echo "TALKTOME_WHISPER_DEVICE=cuda" >> .env.local
echo "TALKTOME_WHISPER_COMPUTE_TYPE=float16" >> .env.local
```

### Hybrid Mode

Use local STT with cloud TTS for best quality:
```env
TALKTOME_STT_PROVIDER=whisper       # Local STT
TALKTOME_TTS_PROVIDER=openai        # Cloud TTS
TALKTOME_OPENAI_API_KEY=sk-xxx
```

### Custom Voices

```bash
# Download additional Piper voices
cd models/piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Update configuration
echo "TALKTOME_PIPER_MODEL_PATH=models/piper/en_US-lessac-medium.onnx" >> .env.local
```

---

## Development

```bash
cd server
uv pip install -e .  # Install dependencies
uv run -m talktome_mcp.server    # Run the server
```

To add new TTS/STT providers:
1. Create provider in `server/talktome_mcp/providers/`
2. Implement the provider interface in `providers/base.py`
3. Update `providers/__init__.py`
4. Add configuration to `.env.example`

---

## System Requirements

- **OS**: Linux (Ubuntu/Debian/Fedora/Arch)
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 500MB for models
- **Audio**: Working microphone and speakers
- **Python**: 3.10 or higher (for MCP SDK)

---

## Security & Privacy

- ✅ **No data leaves your machine** (in local mode)
- ✅ **No third-party services** required
- ✅ **No API keys needed** (for basic operation)
- ✅ **Open source** - audit the code yourself

---

## License

MIT

---

## Acknowledgments

This project was inspired by [call-me](https://github.com/ZeframLou/call-me/) by ZeframLou, but instead of phone calls in TS this is local voice tools in Python.
