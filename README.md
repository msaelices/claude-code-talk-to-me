# TalkToMe - Voice Communication for Claude

**Let Claude communicate with you through your computer's microphone and speakers.**

Have natural voice conversations with Claude using your local audio hardware. Start a task, walk away. Your computer speaks when Claude is done, stuck, or needs a decision.

<img src="./static/taxi-driver.jpg" width="500" alt="TalkToMe - Voice conversations with Claude">

- **Simple setup** - Just install and add your API key. No model downloads, no GPU setup
- **Cross-platform** - Works on Linux, macOS, and Windows (with audio support)
- **Multi-turn conversations** - Talk through decisions naturally
- **Tool-use composable** - Claude can do web searches, edit code, etc. while talking with you

---

## Features

- **Cloud Speech-to-Text** using ElevenLabs real-time transcription
- **Cloud Text-to-Speech** using ElevenLabs high-quality voices
- **System Audio Integration** - Works with PulseAudio, PipeWire, or ALSA
- **Cross-Platform** - Linux, macOS, Windows support
- **Fast Setup** - No ML model downloads, no GPU configuration
- **Low Resource Usage** - ~50MB storage, 1-2GB RAM

---

## Quick Start

### 1. Install System Dependencies (Linux)

TalkToMe requires audio packages for microphone/speaker access:

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

**macOS:**
```bash
brew install ffmpeg
```

### 2. Get Your ElevenLabs API Key

1. Sign up at [https://elevenlabs.io](https://elevenlabs.io)
2. Go to Profile Settings → API Keys
3. Copy your API key

### 3. Install via Claude Code Marketplace

```
/plugin marketplace add msaelices/claude-code-talk-to-me
/plugin install talktome@msaelices
```

### 4. Configure Your API Key

```bash
# Create local config file
cp .env.example .env.local

# Edit .env.local and add your API key
TALKTOME_ELEVENLABS_API_KEY=your_api_key_here
```

### 5. Configure Permissions

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

> **Warning**: Only use this if you trust the tasks you're asking Claude to perform.

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
                                         │   └─► ElevenLabs STT (cloud)
                                         │       └─► Text transcript
                                         │
                                         └─► Speaker Output
                                             └─► ElevenLabs TTS (cloud)
                                                 └─► Audio playback
```

The MCP server runs locally and interfaces with your system's audio hardware. Speech processing is handled by ElevenLabs cloud services for high quality and simple setup.

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

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TALKTOME_ELEVENLABS_API_KEY` | (required) | Your ElevenLabs API key |
| `TALKTOME_TTS_PROVIDER` | `elevenlabs` | TTS provider |
| `TALKTOME_STT_PROVIDER` | `elevenlabs` | STT provider |
| `TALKTOME_ELEVENLABS_VOICE_ID` | `21m00Tcm4TlvDq8ikWAM` | Voice to use (Rachel) |
| `TALKTOME_ELEVENLABS_MODEL_ID` | `eleven_multilingual_v2` | TTS model |
| `TALKTOME_ELEVENLABS_STT_MODEL` | `scribe_v2_realtime` | STT model |

### Voice Options

ElevenLabs provides many high-quality voices. Find voice IDs at [https://elevenlabs.io/voice-library](https://elevenlabs.io/voice-library).

Popular voices:
- `21m00Tcm4TlvDq8ikWAM` - Rachel (default, female)
- `ErXwobaYiN019PkySvjV` - Antoni (male)
- `EXAVITQu4vr4xnSDxMaL` - Bella (female)
- `MF3mGyEYCl7XYWbV9V6O` - Elli (female)

---

## Costs

TalkToMe uses ElevenLabs cloud services. Pricing as of 2024:

| Service | Cost | Notes |
|---------|------|-------|
| **ElevenLabs TTS** | ~$0.30/min | Based on character count |
| **ElevenLabs STT** | ~$0.10/min | Based on audio duration |

**Estimated cost per conversation:**
- Short (2-3 exchanges): ~$0.05-0.10
- Medium (10 min): ~$0.40-0.50
- Long (30 min): ~$1.00-1.50

ElevenLabs offers a free tier with limited usage to get started.

> **Tip:** For lower costs, consider using ElevenLabs for TTS only and a cheaper STT provider (future feature).

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

### API Key Issues
```bash
# Verify your API key is set
echo $TALKTOME_ELEVENLABS_API_KEY

# Test the API directly
curl -X GET "https://api.elevenlabs.io/v1/user" \
  -H "xi-api-key: YOUR_API_KEY"
```

### Rate Limits / Quota Exceeded
- Check your ElevenLabs usage at https://elevenlabs.io/usage
- Upgrade your plan if needed
- Wait for quota reset (monthly)

### Permission Issues
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and back in
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

- **OS**: Linux, macOS, Windows (with audio support)
- **RAM**: 1-2GB
- **Storage**: ~50MB
- **Audio**: Working microphone and speakers
- **Python**: 3.10 or higher
- **Network**: Internet connection required for cloud services

---

## Privacy & Data

TalkToMe uses cloud services for speech processing:

- **Audio data** is sent to ElevenLabs for processing
- ElevenLabs privacy policy applies: https://elevenlabs.io/privacy
- No audio is stored locally by TalkToMe
- Conversation transcripts are kept in memory only (cleared on restart)

If you need fully local/private processing, consider the older v2.x releases which supported local Whisper/Piper models.

---

## License

MIT

---

## Acknowledgments

This project was inspired by [call-me](https://github.com/ZeframLou/call-me/) by ZeframLou, but instead of phone calls in TS this is local voice tools in Python.
