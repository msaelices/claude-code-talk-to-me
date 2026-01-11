# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TalkToMe is a Claude Code plugin (MCP server) that enables Claude to communicate via audio - using your computer's microphone and speakers for real-time voice conversations. Written in Python 3.10+, using the MCP SDK, and communicating via the Model Context Protocol (MCP).

**v3.0 is cloud-only**: Speech processing is handled by ElevenLabs cloud services for simple setup and cross-platform compatibility.

## Development Commands

### Setup and Run
```bash
# Install Python dependencies (requires uv)
cd server && uv pip install -e .

# Run the MCP server
uv run -m talktome_mcp.server
```

### Prerequisites
```bash
# Install system audio dependencies
./install-prerequisites.sh

# Test audio system
uv run python3 test-audio.py
```

### Code Quality
```bash
# Install pre-commit hooks (first time setup)
pre-commit install

# Run linting manually
ruff check server/

# Run linting with auto-fix
ruff check --fix server/

# Run formatting
ruff format server/
```

Pre-commit hooks run automatically on `git commit` and include:
- **ruff**: Fast Python linter with auto-fix (`--fix`)
- **ruff-format**: Code formatter (Black-compatible)

### Environment Configuration
Copy `.env.example` to `.env.local` and configure:
- **Required**: TALKTOME_ELEVENLABS_API_KEY (get from https://elevenlabs.io)
- TTS settings (voice ID, model, stability)
- STT settings (model, language, VAD parameters)

## Architecture

### Provider Pattern
The codebase uses abstract provider interfaces in `server/talktome_mcp/providers/base.py`:
- **PhoneProvider**: Abstract audio I/O interface (LocalPhoneProvider for system audio)
- **TTSProvider**: Abstract text-to-speech (ElevenLabsTTSProvider for cloud)
- **STTProvider**: Abstract speech-to-text base class
- **RealtimeSTTProvider**: Extends STTProvider for streaming audio with VAD (ElevenLabsSTTProvider)

Provider selection happens in `server.py` based on environment variables (`TALKTOME_TTS_PROVIDER`, `TALKTOME_STT_PROVIDER`).

### CallManager Architecture
`call_manager.py` orchestrates the entire audio session:
1. Initializes phone/TTS/STT providers based on config
2. Manages call state (active_call_id, transcript, processing flag)
3. Runs background task `_process_incoming_audio()` that continuously streams mic audio through STT
4. Handles transcript tracking with timestamps and roles (user/assistant)

### Audio Flow
1. **MCP Tool Call** → `server.py` receives `initiate_call` tool request
2. **CallManager** → `initiate_call()` starts the session, spawns background audio processing task
3. **LocalPhoneProvider** → `phone_local.py` handles microphone/speaker I/O using sounddevice library
4. **STT Pipeline** → Background task streams mic audio → ElevenLabsSTTProvider (WebSocket) → transcript updates
5. **TTS Output** → `speak()` calls ElevenLabsTTSProvider (HTTP) → sends audio to PhoneProvider for playback

### MCP Tools
Defined in `server/talktome_mcp/server.py`:
- `initiate_call`: Starts an audio conversation session
- `speak`: Speaks text through the active audio session
- `get_transcript`: Gets the conversation transcript
- `end_call`: Terminates the active audio session
- `test_audio`: Tests audio system components

## Key Implementation Details

### Audio Format
- System audio (recording): 16-bit PCM, 16kHz mono
- TTS output: 16-bit PCM, 22050Hz mono (converted from MP3)
- STT input: 16-bit PCM, 16kHz mono

### ElevenLabs STT Streaming
The ElevenLabsSTTProvider implements streaming transcription via WebSocket:
- `start_stream()`: Establishes WebSocket connection to ElevenLabs realtime API
- `process_audio_chunk()`: Sends base64-encoded audio, returns transcribed text when VAD detects speech end
- `get_final_transcription()`: Sends commit message, returns any remaining buffered transcription
- Uses ElevenLabs server-side VAD for speech detection

### ElevenLabs TTS
The ElevenLabsTTSProvider uses the HTTP API:
- `synthesize()`: Sends text to API, receives MP3, converts to PCM
- Returns 22050Hz, 16-bit mono PCM audio
- Requires ffmpeg for MP3 to PCM conversion (via pydub)

### CallManager Lifecycle
- Only one active call at a time (tracked by `active_call_id`)
- Transcript persists until `end_call()` is called
- Background audio processing task runs continuously while call is active
- `processing_audio` flag prevents concurrent audio processing

### Provider Files
- `providers/base.py`: Abstract interfaces
- `providers/phone_local.py`: Local audio I/O via sounddevice
- `providers/tts_elevenlabs.py`: ElevenLabs TTS (HTTP API)
- `providers/stt_elevenlabs.py`: ElevenLabs STT (WebSocket API)

## Important Notes

- Python 3.10+ required (for MCP SDK and async features)
- Uses MCP SDK (mcp>=1.0.0) with FastMCP-like pattern
- Cloud-only architecture - requires ElevenLabs API key
- Logging goes to stderr (stdout is reserved for MCP communication)
- ffmpeg required for MP3 to PCM audio conversion
- No local ML models or GPU required
