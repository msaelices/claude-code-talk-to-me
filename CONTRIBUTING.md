# Contributing to TalkToMe

This guide covers development setup, debugging, and how to contribute to TalkToMe.

## Development Setup

First, install system dependencies as described in the [README](README.md#1-install-system-dependencies-required).

### Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/msaelices/claude-code-talk-to-me.git
cd claude-code-talk-to-me

# Install Python dependencies
cd server
pip install -e .

# Or using uv
uv pip install -e .
```

### Download Models

```bash
# Interactive model download
uv run python3 download-models.py
```

Or download manually:
- **Whisper**: Auto-downloads on first use to `~/.cache/huggingface/hub/`
- **Piper**: Download to `models/piper/` from [Hugging Face](https://huggingface.co/rhasspy/piper-voices)

### Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
# Audio system (pulseaudio, pipewire, or alsa)
TALKTOME_AUDIO_SYSTEM=pulseaudio

# TTS provider (piper for local, elevenlabs for cloud)
TALKTOME_TTS_PROVIDER=piper
TALKTOME_PIPER_SPEED=0.85

# STT provider
TALKTOME_STT_PROVIDER=whisper
TALKTOME_WHISPER_MODEL=base

# Timeout for user speech (ms)
TALKTOME_TRANSCRIPT_TIMEOUT_MS=180000
```

### Run the Server

```bash
cd server
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

## Manual Plugin Installation (for debugging)

If the marketplace installation doesn't work, use this manual method:

### Add to Claude Code Config

Add to `~/.config/claude-code/config.json`:

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

Replace `/path/to/claude-code-talk-to-me` with the actual path.

### Configure Permissions

```
/allowed-tools mcp__talktome__*
```

Or add to `~/.claude/settings.json`:
```json
{
  "allowedTools": ["mcp__talktome__*"]
}
```

---

## Testing

### Test Audio System

```bash
uv run python3 test-audio.py
```

This tests:
- Audio device detection
- Microphone recording
- Speaker playback
- PulseAudio/PipeWire connectivity
- Piper TTS synthesis
- Whisper STT transcription

### Test Individual Components

```bash
# Test Whisper model loading
uv run python3 test-whisper-download.py

# Test audio playback
paplay /usr/share/sounds/freedesktop/stereo/bell.oga

# Test microphone
arecord -d 5 test.wav && aplay test.wav
```

---

## Debugging

### Common Issues

**No audio output:**
```bash
pactl info | grep "Default Sink"
speaker-test -t wav -c 2
```

**No audio input:**
```bash
pactl info | grep "Default Source"
arecord -d 5 test.wav && aplay test.wav
```

**Whisper model not loading:**
```bash
# Clear and re-download
rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-*
uv run python3 test-whisper-download.py
```

**Permission issues:**
```bash
sudo usermod -a -G audio $USER
# Log out and back in
```

### Enable Debug Logging

Set environment variable:
```bash
export TALKTOME_LOG_LEVEL=DEBUG
uv run -m talktome_mcp.server
```

---

## Adding New Providers

### TTS Provider

1. Create `server/talktome_mcp/providers/tts_yourprovider.py`
2. Implement the `TTSProvider` interface from `providers/base.py`:
   ```python
   class YourTTSProvider(TTSProvider):
       async def synthesize(self, text: str) -> bytes:
           # Return 16-bit PCM audio at 22-24kHz mono
           pass
   ```
3. Update `providers/__init__.py` to export your provider
4. Add configuration to `.env.example`
5. Update `server.py` to support your provider

### STT Provider

1. Create `server/talktome_mcp/providers/stt_yourprovider.py`
2. Implement the `RealtimeSTTProvider` interface:
   ```python
   class YourSTTProvider(RealtimeSTTProvider):
       async def start_stream(self) -> None: ...
       async def process_audio_chunk(self, audio_data: bytes) -> Optional[str]: ...
       async def get_final_transcription(self) -> Optional[str]: ...
       async def stop_stream(self) -> None: ...
   ```
3. Update `providers/__init__.py`
4. Add configuration to `.env.example`
5. Update `server.py`

---

## Code Style

This project uses:
- **ruff** for linting and formatting
- **pre-commit** hooks for automated checks

Setup:
```bash
pre-commit install
```

Run manually:
```bash
ruff check server/
ruff format server/
```

---

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `uv run python3 test-audio.py`
5. Run linting: `ruff check --fix server/ && ruff format server/`
6. Commit with clear message
7. Push and create PR

---

## Architecture Overview

```
server/talktome_mcp/
├── server.py           # MCP server entry point, tool definitions
├── call_manager.py     # Orchestrates audio sessions
├── utils.py            # Helper functions
└── providers/
    ├── base.py         # Abstract interfaces
    ├── phone_local.py  # Local audio I/O (sounddevice)
    ├── tts_piper.py    # Piper TTS provider
    ├── tts_elevenlabs.py # ElevenLabs TTS provider
    └── stt_whisper.py  # Whisper STT provider
```

### Audio Flow

1. `server.py` receives MCP tool call
2. `CallManager` manages session state
3. `LocalPhoneProvider` handles mic/speaker I/O
4. `WhisperSTTProvider` transcribes speech
5. `PiperTTSProvider` synthesizes responses
