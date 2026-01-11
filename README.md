# TalkToMe - Local Voice Communication for Claude

**Let Claude communicate with you through your computer's microphone and speakers.**

Have natural voice conversations with Claude using local audio. Start a task, walk away. Your computer speaks when Claude is done, stuck, or needs a decision.

<img src="./static/taxi-driver.jpg" width="500" alt="TalkToMe - Voice conversations with Claude">

- **Zero cost** - No phone charges, no API costs for communication (optional ElevenLabs available)
- **Privacy-first** - All audio processing can happen locally on your machine
- **Multi-turn conversations** - Talk through decisions naturally
- **Tool-use composable** - Claude can e.g. do a web search while talking with you

---

## Features

- 🎙️ **Local Speech-to-Text** using Whisper
- 🔊 **Text-to-Speech** using Piper neural TTS (local) or ElevenLabs (cloud)
- 🎧 **System Audio Integration** - Works with PulseAudio, PipeWire, or ALSA
- 💻 **Cross-Platform** - Linux support (Windows/Mac with modifications)
- 🔒 **Privacy** - All processing can be done locally without cloud services
- ⚡ **Fast** - Sub-second response times with local models

---

## Quick Start

### 1. Install System Dependencies (Required)

TalkToMe requires audio and Python packages that must be installed via your system package manager:

**Ubuntu/Debian:**
```bash
sudo apt-get install pulseaudio-utils python3 python3-pip ffmpeg
```

**Fedora:**
```bash
sudo dnf install pulseaudio-utils python3 python3-pip ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S pulseaudio python python-pip ffmpeg
```

### 2. Install via Claude Code Marketplace

```
/plugin marketplace add msaelices/claude-code-talk-to-me
/plugin install talktome@msaelices
```

> **Note**: First startup downloads models (~140 MB). Subsequent starts are instant.

### 3. (Optional) Configure Models

Before starting Claude, you can set environment variables to choose different models:

```bash
export TALKTOME_WHISPER_MODEL=small      # Default: base (options: tiny, base, small, medium, large-v3)
export TALKTOME_PIPER_VOICE=en_US-danny-low  # Default: en_US-amy-medium
```

Skip this step to use the recommended defaults.

### 4. Configure Permissions

```
/allowed-tools mcp__talktome__*
```

That's it! Ask Claude to use TalkToMe and start talking.

> **Having issues?** See [CONTRIBUTING.md](CONTRIBUTING.md) for manual installation and debugging.

---

## Permissions & Hands-Free Operation

For natural voice conversations, TalkToMe tools need to run without permission prompts.

**For truly hands-free operation**, run Claude Code in "YOLO mode":

```bash
claude --dangerously-skip-permissions
```

> ⚠️ **Warning**: Only use this if you trust the tasks you're asking Claude to perform.

**Alternative: Sound notification hook**

Play a sound when Claude needs input:

```json
// In ~/.claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "paplay /usr/share/sounds/freedesktop/stereo/bell.oga"
          }
        ]
      }
    ]
  }
}
```

---

## How to Use

With TalkToMe installed, simply ask Claude to use it:

```
You: "Use the talk to me skill to ask me what to work on"
```

Claude will then:
1. Start a voice session
2. Speak to you through your speakers
3. Listen to your responses via microphone
4. Work silently on long tasks, then speak up when done or needs input

### Quick Tips

- **Speak naturally** - No need for perfect diction
- **Be specific** - "Users can't log in after password reset" is better than "fix the bug"
- **Step away** - Claude will speak up when done or needs a decision
- **End anytime** - Say "that's all" or press Ctrl+C

### Example Session

```
You: "Use talk to me to help me refactor my code"

Claude (voice): "Hi! What would you like me to work on?"

You: "The authentication module is messy. Can you clean it up?"

Claude (voice): "Got it! Let me examine it first..."

[Silence while Claude works...]

Claude (voice): "I found several issues. Should I start by extracting the validation logic?"

You: "Yes, please."

Claude (voice): "On it! I'm extracting the validation into a separate service..."

[More silence while Claude works...]

Claude (voice): "Done! The code is much cleaner now. Should I add tests?"

You: "That would be great."

Claude (voice): "I'll create unit tests now... Done! Anything else?"

You: "No, that's everything. Thanks!"

Claude (voice): "You're welcome!"
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

## Conversation Flow

TalkToMe supports natural turn-taking voice conversations:

```python
# 1. Start conversation with a question (blocks for response)
result = await initiate_call(message="Hi! I'm ready to help. What would you like me to do?")
user_response = result['user_response']  # e.g., "Help me debug my authentication code"

# 2. Continue with follow-up questions (each blocks for response)
result = await continue_call(message="Got it. What's the issue with the auth code?")
user_response = result['user_response']  # e.g., "Users can't log in after password reset"

# 3. Acknowledge before long tasks (non-blocking)
await speak(message="Let me investigate the password reset flow. This might take a minute...")
# Do your investigation...
# code review, file search, etc.

# 4. Continue with findings (blocks for response)
result = await continue_call(message="I found the bug! The token expiration wasn't set correctly. Should I fix it?")
user_response = result['user_response']  # e.g., "Yes, please fix it"

# 5. End the conversation
await end_call()
```

**Key patterns:**
- Use `initiate_call(message)` or `continue_call(message)` when you **need a response**
- Use `speak(message)` when you just want to **acknowledge** before doing work
- The conversation tools block until the user speaks or timeout (default: 3 minutes)

---

## Tools

### `initiate_call`
Start an audio conversation with an optional initial message. Waits for and returns the user's response.

```python
# Start conversation with initial question (blocks for response)
result = await initiate_call(message="Hey! I finished the auth system. What should I work on next?")
# Returns: {"success": true, "call_id": "local-1", "user_response": "Add some tests"}

# Or start without initial message
result = await initiate_call()
# Returns: {"success": true, "call_id": "local-1", ...}
```

### `continue_call`
Continue an active conversation with a follow-up message. Waits for and returns the user's response.

```python
# Continue conversation (blocks for response)
result = await continue_call(message="Got it. Should I add unit tests or integration tests?")
# Returns: {"success": true, "user_response": "Both please", "call_id": "local-1"}
```

### `speak`
Speak text through the active audio session **without waiting** for a response. Use this to acknowledge requests or provide status updates before starting time-consuming operations.

```python
# Acknowledge without waiting (non-blocking)
await speak(text="Let me search for that information. Give me a moment...")
# Continue with your long-running task
results = await perform_search()
# Then continue the conversation
result = await continue_call(message=f"I found {len(results)} results. What would you like to know?")
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

### Model Auto-Download

Models are automatically downloaded on first startup. Configure which models to use via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TALKTOME_PIPER_VOICE` | `en_US-amy-medium` | Piper TTS voice to download |
| `TALKTOME_WHISPER_MODEL` | `base` | Whisper STT model to download |

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

**Optional Cloud Mode** (if using ElevenLabs):
- **ElevenLabs TTS**: ~$0.30/min (Starter plan)

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
TALKTOME_TTS_PROVIDER=elevenlabs    # Cloud TTS (ElevenLabs)
TALKTOME_ELEVENLABS_API_KEY=your_api_key_here
TALKTOME_ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Optional: Rachel voice
```

**ElevenLabs TTS Configuration**:
- Get your API key from https://elevenlabs.io
- Default voice is "Rachel" (`21m00Tcm4TlvDq8ikWAM`)
- Default model is `eleven_multilingual_v2`
- Optional parameters:
  - `TALKTOME_ELEVENLABS_STABILITY` (0.0-1.0, default: varies by voice)
  - `TALKTOME_ELEVENLABS_SIMILARITY_BOOST` (0.0-1.0, default: varies by voice)

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Manual installation for debugging
- Testing and debugging guides
- How to add new TTS/STT providers
- Code style and PR process

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
