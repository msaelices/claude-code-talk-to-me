# Refactor to cloud-only architecture using ElevenLabs

## Summary

- Refactor TalkToMe to cloud-only architecture using ElevenLabs for both TTS and STT
- Remove all local ML dependencies (torch, faster-whisper, piper-tts, silero-vad)
- Add new `ElevenLabsSTTProvider` with real-time WebSocket streaming
- Simplify installation: ~50MB vs 500MB+, no model downloads needed

## Benefits

| Metric | Before (v2.x) | After (v3.0) |
|--------|---------------|--------------|
| Installation size | 500MB+ | ~50MB |
| Setup time | 20-40 min | ~5 min |
| RAM required | 4-8GB | 1-2GB |
| Cross-platform | Linux only | Linux/macOS/Windows |

## Changes

### New Files
- `server/talktome_mcp/providers/stt_elevenlabs.py` - ElevenLabs real-time STT provider using WebSocket API

### Deleted Files
- `server/talktome_mcp/providers/stt_whisper.py` - Local Whisper STT
- `server/talktome_mcp/providers/tts_piper.py` - Local Piper TTS
- `download-models.py` - Model download script

### Modified Files
- `server/pyproject.toml` - Removed torch, faster-whisper, piper-tts, silero-vad; added websockets; bumped to v3.0.0
- `server/talktome_mcp/server.py` - Changed defaults to ElevenLabs
- `server/talktome_mcp/call_manager.py` - Updated default providers
- `README.md` - Complete rewrite for cloud-only setup with pricing info
- `.env.example` - Rewritten for ElevenLabs configuration
- `CLAUDE.md` - Updated architecture documentation
- `CONTRIBUTING.md` - Updated for cloud-only setup

## Breaking Changes

- Requires ElevenLabs API key (no free/offline mode)
- Local Whisper/Piper providers removed
- Users needing local processing should use v2.x releases

## Test plan

- [ ] Fresh install with `uv pip install -e .` completes quickly
- [ ] Configure `.env.local` with ElevenLabs API key
- [ ] Run `test-audio.py` to verify audio system
- [ ] Test full call flow: `initiate_call` → speak → `end_call`
- [ ] Verify TTS works (ElevenLabs HTTP API)
- [ ] Verify STT works (ElevenLabs WebSocket API)
