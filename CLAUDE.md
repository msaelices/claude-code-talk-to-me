# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TalkToMe is a Claude Code plugin (MCP server) that enables Claude to communicate via local audio - using your computer's microphone and speakers for real-time voice conversations. Written in Python 3.10+, using the FastMCP framework, and communicating via the Model Context Protocol (MCP).

## Development Commands

### Setup and Run
```bash
# Install Python dependencies
cd server && pip install -r requirements.txt

# Run the MCP server
python3 -m talktome_mcp.server
```

### Python Environment Setup
```bash
# Install prerequisites
./install-prerequisites.sh

# Download models
source venv/bin/activate
python3 download-models.py

# Test audio system
python3 test-audio.py
```

### Environment Configuration
Copy `.env.example` to `.env.local` and configure:
- Audio system (TALKTOME_AUDIO_SYSTEM: pulseaudio, pipewire, or alsa)
- TTS provider (TALKTOME_TTS_PROVIDER: piper or openai)
- STT provider (TALKTOME_STT_PROVIDER: whisper or openai)
- Model paths and configurations

## Architecture

### Provider Pattern
The codebase uses abstract provider interfaces in `/server/talktome_mcp/providers/`:
- **PhoneProvider**: Interface for audio I/O (LocalPhoneProvider for system audio)
- **TTSProvider**: Text-to-speech (PiperTTSProvider for local)
- **STTProvider**: Speech-to-text (WhisperSTTProvider for local)

Provider selection happens in `server.py` based on environment variables.

### Audio Flow
1. **MCP Tool Call** → `server.py` receives `initiate_call` tool request
2. **Audio Manager** → `call_manager.py` manages audio session state
3. **Local Audio** → `phone_local.py` handles microphone/speaker I/O using sounddevice
4. **Audio Pipeline** → Direct audio streaming to/from system
5. **STT/TTS** → Real-time transcription and synthesis

### MCP Tools
Defined in `/server/talktome_mcp/server.py`:
- `initiate_call`: Starts an audio conversation session
- `speak`: Speaks text through the active audio session
- `get_transcript`: Gets the conversation transcript
- `end_call`: Terminates the active audio session
- `test_audio`: Tests audio system components

## Key Implementation Details

### Audio Format
- System audio: 16-bit PCM, 16kHz mono (recording)
- TTS output: 16-bit PCM, 22-24kHz mono
- STT input: 16-bit PCM, 16kHz mono

### Provider-Specific Details
- **Piper TTS**: Uses ONNX models for fast neural synthesis (runs as Python module)
- **Whisper STT**: Uses faster-whisper library directly in Python
- **Local Audio**: Uses sounddevice library for cross-platform audio I/O

## Important Notes

- Python 3.10+ required (for MCP SDK and async features)
- Uses FastMCP framework for MCP server implementation
- Direct Python integration with Whisper and Piper (no subprocesses)
- Logging goes to stderr (stdout is reserved for MCP communication)