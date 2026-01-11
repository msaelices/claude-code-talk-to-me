#!/usr/bin/env python3
"""
Non-interactive setup script for TalkToMe plugin.
Downloads models and checks audio devices during plugin startup.
All output goes to stderr (stdout reserved for MCP communication).
"""

import os
import sys
import urllib.request
from pathlib import Path


# Output to stderr only
def log(msg: str) -> None:
    print(msg, file=sys.stderr)


# Piper voice configurations
PIPER_VOICES = {
    "en_US-amy-medium": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
    },
    "en_US-danny-low": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low/en_US-danny-low.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low/en_US-danny-low.onnx.json",
    },
    "en_US-libritts_r-medium": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json",
    },
    "en_GB-alan-medium": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json",
    },
}


def download_file(url: str, destination: Path, description: str) -> bool:
    """Download a file with progress indicator."""
    try:
        log(f"Downloading {description}...")
        destination.parent.mkdir(parents=True, exist_ok=True)

        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0

            with open(destination, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        log(f"  Progress: {progress:.0f}%")

        log(f"  Done: {destination}")
        return True
    except Exception as e:
        log(f"  Failed: {e}")
        return False


def setup_piper_model() -> bool:
    """Download Piper TTS model if missing."""
    voice_name = os.getenv("TALKTOME_PIPER_VOICE", "en_US-amy-medium")

    if voice_name not in PIPER_VOICES:
        log(f"Unknown Piper voice: {voice_name}, using en_US-amy-medium")
        voice_name = "en_US-amy-medium"

    voice_info = PIPER_VOICES[voice_name]
    models_dir = Path("models/piper")
    onnx_path = models_dir / f"{voice_name}.onnx"
    config_path = models_dir / f"{voice_name}.onnx.json"

    # Check if already exists
    if onnx_path.exists() and config_path.exists():
        log(f"Piper model already exists: {voice_name}")
        return True

    log(f"Setting up Piper TTS voice: {voice_name}")

    # Download model
    if not onnx_path.exists():
        if not download_file(voice_info["url"], onnx_path, f"{voice_name} model"):
            return False

    # Download config
    if not config_path.exists():
        if not download_file(
            voice_info["config_url"], config_path, f"{voice_name} config"
        ):
            return False

    return True


def setup_whisper_model() -> bool:
    """Pre-download Whisper STT model if missing."""
    model_name = os.getenv("TALKTOME_WHISPER_MODEL", "base")

    log(f"Checking Whisper model: {model_name}")

    try:
        # Import faster_whisper to trigger model download
        from faster_whisper import WhisperModel

        # This will download the model if not cached
        log("Loading Whisper model (downloads if needed)...")
        WhisperModel(model_name, device="cpu", compute_type="int8")
        log(f"Whisper model ready: {model_name}")
        return True
    except ImportError:
        log("faster-whisper not installed, skipping Whisper setup")
        return False
    except Exception as e:
        log(f"Failed to setup Whisper model: {e}")
        return False


def check_audio_devices() -> bool:
    """Check that audio input/output devices exist (non-interactive)."""
    log("Checking audio devices...")

    try:
        import sounddevice as sd

        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        output_devices = [d for d in devices if d["max_output_channels"] > 0]

        if not input_devices:
            log("  Warning: No input devices (microphone) found")
        else:
            log(f"  Input devices: {len(input_devices)} found")

        if not output_devices:
            log("  Warning: No output devices (speakers) found")
        else:
            log(f"  Output devices: {len(output_devices)} found")

        return len(input_devices) > 0 and len(output_devices) > 0
    except ImportError:
        log("  sounddevice not installed, skipping audio check")
        return True
    except Exception as e:
        log(f"  Audio check failed: {e}")
        return False


def main():
    log("=" * 50)
    log("TalkToMe Plugin Setup")
    log("=" * 50)

    # Setup Piper TTS model
    piper_ok = setup_piper_model()

    # Setup Whisper STT model
    whisper_ok = setup_whisper_model()

    # Check audio devices
    audio_ok = check_audio_devices()

    log("=" * 50)
    if piper_ok and whisper_ok and audio_ok:
        log("Setup complete!")
    else:
        log("Setup completed with warnings (see above)")
    log("=" * 50)

    # Always exit 0 to not block plugin startup
    return 0


if __name__ == "__main__":
    sys.exit(main())
