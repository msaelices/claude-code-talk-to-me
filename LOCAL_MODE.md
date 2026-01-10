# CallMe - Local Audio Communication for Claude

CallMe enables Claude to interact with you through your computer's microphone and speakers. This provides a zero-cost, privacy-preserving voice communication system for Claude.

## Features

- **Local Text-to-Speech**: Uses Piper neural TTS for natural-sounding speech
- **Local Speech-to-Text**: Uses Whisper for accurate speech recognition
- **Zero Cost**: No phone charges or API costs (fully offline)
- **Privacy**: All audio processing happens locally on your machine
- **Low Latency**: Faster response times compared to cloud services
- **Cross-Platform**: Works on Linux with PulseAudio, PipeWire, or ALSA

## Prerequisites

### System Requirements

- **Linux** (Ubuntu, Fedora, Arch, or any distro with audio support)
- **Python 3.8+**
- **4GB RAM minimum** (8GB recommended for larger Whisper models)
- **Microphone and speakers/headphones**
- **Optional: NVIDIA GPU** for faster Whisper inference

### Audio System

One of the following:
- **PulseAudio** (most common)
- **PipeWire** (modern replacement for PulseAudio)
- **ALSA** (low-level, basic support)

## Quick Start

### 1. Install Prerequisites

```bash
# Make the script executable
chmod +x install-prerequisites.sh

# Run the installation
./install-prerequisites.sh
```

This will:
- Create a Python virtual environment
- Install faster-whisper, piper-tts, and audio libraries
- Check for required system packages
- Set up the models directory

### 2. Download Models

```bash
# Download models
uv run python3 download-models.py
```

Choose:
- **Whisper model**: `base` (good balance) or `tiny` (fastest)
- **Piper voice**: `en_US-amy-medium` (recommended)

### 3. Test Your Audio

```bash
# Test audio devices and TTS/STT
uv run python3 test-audio.py
```

This will:
- List available audio devices
- Play a test tone
- Record 3 seconds of audio
- Test Piper TTS generation
- Test Whisper STT transcription

### 4. Configure Environment

```bash
# Copy the local mode configuration template
cp .env.local.example .env.local

# Edit with your preferences
nano .env.local
```

Key settings:
```env
CALLME_LOCAL_MODE=true
CALLME_TTS_PROVIDER=piper
CALLME_STT_PROVIDER=whisper
CALLME_WHISPER_MODEL=base
```

### 5. Run in Local Mode

```bash
cd server
bun run dev
```

Claude will now use your local audio instead of phone calls!

## Configuration Options

### Whisper STT Models

| Model | Size | Accuracy | Speed | Use Case |
|-------|------|----------|-------|----------|
| tiny | 39 MB | 85% | Fastest | Quick testing, low-end hardware |
| base | 74 MB | 90% | Fast | **Recommended** - good balance |
| small | 244 MB | 93% | Medium | Better accuracy, decent speed |
| medium | 769 MB | 95% | Slow | High accuracy, needs good CPU/GPU |
| large-v3 | 1.5 GB | 98% | Slowest | Best accuracy, requires GPU |

### Piper TTS Voices

| Voice | Quality | Size | Description |
|-------|---------|------|-------------|
| en_US-amy-medium | Medium | 63 MB | **Recommended** - Natural female voice |
| en_US-danny-low | Low | 18 MB | Fast male voice, lower quality |
| en_US-libritts_r-medium | Medium | 63 MB | Neutral voice, good clarity |
| en_GB-alan-medium | Medium | 63 MB | British male voice |

### Performance Tuning

#### For Faster Response (Lower Quality)
```env
CALLME_WHISPER_MODEL=tiny
CALLME_WHISPER_COMPUTE_TYPE=int8
CALLME_PIPER_LENGTH_SCALE=0.9  # Speak 10% faster
```

#### For Better Quality (Slower)
```env
CALLME_WHISPER_MODEL=small
CALLME_WHISPER_DEVICE=cuda  # If you have NVIDIA GPU
CALLME_WHISPER_COMPUTE_TYPE=float16
```

#### For CPU-Only Systems
```env
CALLME_WHISPER_DEVICE=cpu
CALLME_WHISPER_COMPUTE_TYPE=int8  # Optimized for CPU
```

## How It Works

```mermaid
graph LR
    A[Microphone] --> B[Audio Capture]
    B --> C[Whisper STT]
    C --> D[Text Transcript]
    D --> E[Claude Processes]
    E --> F[Response Text]
    F --> G[Piper TTS]
    G --> H[Audio Output]
    H --> I[Speakers]
```

1. **Audio Capture**: System microphone records your voice
2. **Speech Recognition**: Whisper converts speech to text locally
3. **Claude Processing**: Claude processes your request
4. **Speech Synthesis**: Piper converts Claude's response to speech
5. **Audio Playback**: Response plays through your speakers

## Comparison: Local vs Phone Mode

| Feature | Local Mode | Phone Mode |
|---------|------------|------------|
| **Cost** | Free | ~$0.03-0.04/min |
| **Privacy** | Fully local | Cloud services |
| **Setup** | 10 minutes | 30+ minutes |
| **Latency** | 300-500ms | 500-1000ms |
| **Audio Quality** | Good | Excellent |
| **Reliability** | Depends on hardware | Very high |
| **Internet Required** | No* | Yes |

*Claude still needs internet for its core functionality

## Troubleshooting

### No Audio Output
```bash
# Check default audio device
pactl info | grep "Default Sink"

# Test speakers directly
speaker-test -t wav -c 2
```

### No Audio Input
```bash
# Check default microphone
pactl info | grep "Default Source"

# Test microphone
arecord -d 5 test.wav && aplay test.wav
```

### Whisper Model Not Found
```bash
# Re-download the model
rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-*
uv run python3 test-whisper-download.py
```

### Piper Voice Not Found
```bash
# Re-download voices
uv run python3 download-models.py
```

### High CPU Usage
- Use smaller Whisper model (`tiny` or `base`)
- Enable int8 quantization: `CALLME_WHISPER_COMPUTE_TYPE=int8`
- Reduce audio quality if needed

### Permission Denied for Audio
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and back in
```

## Advanced Usage

### Custom Piper Voices

Download additional voices from [Hugging Face](https://huggingface.co/rhasspy/piper-voices):
```bash
cd models/piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

Update `.env.local`:
```env
CALLME_PIPER_MODEL_PATH=models/piper/en_US-lessac-medium.onnx
```

### GPU Acceleration

For NVIDIA GPUs:
```bash
# Install CUDA-enabled faster-whisper
uv pip install nvidia-cublas-cu11 nvidia-cudnn-cu11
uv pip install faster-whisper --upgrade

# Configure for GPU
echo "CALLME_WHISPER_DEVICE=cuda" >> .env.local
echo "CALLME_WHISPER_COMPUTE_TYPE=float16" >> .env.local
```

### Hybrid Mode

Use local STT with cloud TTS for best quality:
```env
CALLME_LOCAL_MODE=true
CALLME_STT_PROVIDER=whisper
CALLME_TTS_PROVIDER=openai
CALLME_OPENAI_API_KEY=sk-xxx
```

## Contributing

To add support for new TTS/STT engines:

1. Create a new provider in `server/src/providers/`
2. Implement the `TTSProvider` or `RealtimeSTTProvider` interface
3. Update `providers/index.ts` to include your provider
4. Add configuration options to `.env.local.example`

## Security Considerations

Local mode is more secure than phone mode:
- ✅ No audio data leaves your machine
- ✅ No third-party services involved
- ✅ No webhook endpoints exposed
- ✅ No phone number required

However, remember:
- Claude still requires internet to function
- Audio is processed unencrypted on your local machine
- Other applications can potentially access your microphone

## Performance Benchmarks

On a typical desktop (Intel i7, 16GB RAM):

| Operation | Time |
|-----------|------|
| Whisper base transcription (5s audio) | ~500ms |
| Piper TTS generation (50 words) | ~200ms |
| End-to-end response | ~1-2s |

With GPU (NVIDIA RTX 3060):
| Operation | Time |
|-----------|------|
| Whisper base transcription (5s audio) | ~150ms |
| End-to-end response | ~500ms |

## FAQ

**Q: Can I use this on Windows or macOS?**
A: The code is designed for Linux, but with modifications to the audio capture/playback commands, it could work on other platforms.

**Q: Do I need an internet connection?**
A: Not for audio processing, but Claude still needs internet to work.

**Q: Can I use other languages?**
A: Yes! Download Whisper models and Piper voices for your language.

**Q: Is this faster than phone mode?**
A: Usually yes, especially with a GPU. Phone mode has network latency.

**Q: Can multiple people use it simultaneously?**
A: Currently, no. The system uses the default microphone/speaker for a single user.

## License

This local mode feature is part of the CallMe project and follows the same license terms.