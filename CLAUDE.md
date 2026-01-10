# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TalkToMe is a Claude Code plugin (MCP server) that enables Claude to communicate via local audio - using your computer's microphone and speakers for real-time voice conversations. Written in Python 3.10+, using the MCP SDK, and communicating via the Model Context Protocol (MCP).

## Development Commands

### Setup and Run
```bash
# Install Python dependencies (requires uv)
cd server && uv pip install -e .

# Run the MCP server
uv run -m talktome_mcp.server
```

### Model Setup
```bash
# Install prerequisites (system packages)
./install-prerequisites.sh

# Download models
uv run python3 download-models.py

# Test audio system
uv run python3 test-audio.py
```

### Environment Configuration
Copy `.env.example` to `.env.local` and configure:
- Audio system (TALKTOME_AUDIO_SYSTEM: pulseaudio, pipewire, or alsa)
- TTS provider (TALKTOME_TTS_PROVIDER: piper or elevenlabs)
- STT provider (TALKTOME_STT_PROVIDER: whisper)
- Model paths and performance settings (WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE)

## Architecture

### Provider Pattern
The codebase uses abstract provider interfaces in `server/talktome_mcp/providers/base.py`:
- **PhoneProvider**: Abstract audio I/O interface (LocalPhoneProvider for system audio)
- **TTSProvider**: Abstract text-to-speech (PiperTTSProvider for local, ElevenLabsTTSProvider for cloud)
- **STTProvider**: Abstract speech-to-text (WhisperSTTProvider for local)
- **RealtimeSTTProvider**: Extends STTProvider for streaming audio with VAD (Voice Activity Detection)

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
4. **Audio Pipeline** → Background task streams mic audio → RealtimeSTTProvider → transcript updates
5. **TTS Output** → `speak()` synthesizes text → sends to PhoneProvider for playback

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
- TTS output: 16-bit PCM, 22-24kHz mono
- STT input: 16-bit PCM, 16kHz mono

### RealtimeSTTProvider Streaming
The WhisperSTTProvider implements streaming transcription:
- `start_stream()`: Initializes Whisper model and VAD
- `process_audio_chunk()`: Processes audio chunks, returns transcribed text when silence is detected
- `get_final_transcription()`: Returns any remaining buffered transcription
- Uses `TALKTOME_STT_SILENCE_DURATION_MS` (default 800ms) to detect speech end

### CallManager Lifecycle
- Only one active call at a time (tracked by `active_call_id`)
- Transcript persists until `end_call()` is called
- Background audio processing task runs continuously while call is active
- `processing_audio` flag prevents concurrent audio processing

### Provider-Specific Details
- **Piper TTS**: Uses ONNX models for fast neural synthesis (runs as Python module via piper-tts package)
- **Whisper STT**: Uses faster-whisper library directly in Python (not subprocess)
- **Local Audio**: Uses sounddevice library for cross-platform audio I/O (PortAudio wrapper)

## Important Notes

- Python 3.10+ required (for MCP SDK and async features)
- Uses MCP SDK (mcp>=1.0.0) with FastMCP-like pattern
- Direct Python integration with Whisper and Piper (no subprocesses)
- Logging goes to stderr (stdout is reserved for MCP communication)
- Models are cached in `~/.cache/huggingface/hub/` (Whisper) and local `models/` directory (Piper)