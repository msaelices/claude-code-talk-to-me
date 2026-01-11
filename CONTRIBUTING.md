# Contributing to TalkToMe

This guide covers development setup, debugging, and how to contribute to TalkToMe.

## Development Setup

First, install system dependencies as described in the [README](README.md#1-install-system-dependencies-linux).

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

### Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local` with your ElevenLabs API key:
```env
# Required: Your ElevenLabs API key
TALKTOME_ELEVENLABS_API_KEY=your_api_key_here

# TTS configuration
TALKTOME_TTS_PROVIDER=elevenlabs
TALKTOME_ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# STT configuration
TALKTOME_STT_PROVIDER=elevenlabs
TALKTOME_ELEVENLABS_STT_MODEL=scribe_v2
```

### Run the Server

```bash
cd server
uv run -m talktome_mcp.server
```

You should see:
```
TalkToMe Cloud Audio Communication
================================
Ready for voice communication!
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
        "TALKTOME_ELEVENLABS_API_KEY": "your_api_key_here",
        "TALKTOME_TTS_PROVIDER": "elevenlabs",
        "TALKTOME_STT_PROVIDER": "elevenlabs"
      }
    }
  }
}
```

Replace `/path/to/claude-code-talk-to-me` with the actual path.

Then configure permissions as described in the [README](README.md#5-configure-permissions).

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
- ElevenLabs TTS synthesis (if API key configured)

### Test Individual Components

```bash
# Test audio playback
paplay /usr/share/sounds/freedesktop/stereo/bell.oga

# Test microphone
arecord -d 5 test.wav && aplay test.wav

# Test ElevenLabs API
curl -X GET "https://api.elevenlabs.io/v1/user" \
  -H "xi-api-key: YOUR_API_KEY"
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

**API key issues:**
```bash
# Verify your API key is set
echo $TALKTOME_ELEVENLABS_API_KEY

# Test the API directly
curl -X GET "https://api.elevenlabs.io/v1/user" \
  -H "xi-api-key: YOUR_API_KEY"
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
    ├── tts_elevenlabs.py # ElevenLabs TTS provider (HTTP API)
    └── stt_elevenlabs.py # ElevenLabs STT provider (WebSocket API)
```

### Audio Flow

1. `server.py` receives MCP tool call
2. `CallManager` manages session state
3. `LocalPhoneProvider` handles mic/speaker I/O
4. `ElevenLabsSTTProvider` streams audio to cloud for transcription
5. `ElevenLabsTTSProvider` synthesizes responses via cloud API
