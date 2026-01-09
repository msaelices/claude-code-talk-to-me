#!/usr/bin/env python3
"""
Download and setup models for Whisper STT and Piper TTS
"""

import os
import sys
import json
import hashlib
import urllib.request
from pathlib import Path
from typing import Dict, Optional

# Model configurations
WHISPER_MODELS = {
    "tiny": {
        "description": "Tiny model (39 MB) - Fastest, lowest accuracy",
        "size_mb": 39,
        "relative_speed": 1.0
    },
    "base": {
        "description": "Base model (74 MB) - Good balance of speed and accuracy",
        "size_mb": 74,
        "relative_speed": 0.7
    },
    "small": {
        "description": "Small model (244 MB) - Better accuracy, slower",
        "size_mb": 244,
        "relative_speed": 0.4
    },
    "medium": {
        "description": "Medium model (769 MB) - High accuracy, requires more resources",
        "size_mb": 769,
        "relative_speed": 0.2
    },
    "large-v3": {
        "description": "Large v3 model (1550 MB) - Best accuracy, slowest",
        "size_mb": 1550,
        "relative_speed": 0.1
    }
}

PIPER_VOICES = {
    "en_US-amy-medium": {
        "description": "Amy - American English, female, medium quality",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
        "size_mb": 63
    },
    "en_US-danny-low": {
        "description": "Danny - American English, male, low quality (fastest)",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low/en_US-danny-low.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low/en_US-danny-low.onnx.json",
        "size_mb": 18
    },
    "en_US-libritts_r-medium": {
        "description": "LibriTTS - American English, neutral, medium quality",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json",
        "size_mb": 63
    },
    "en_GB-alan-medium": {
        "description": "Alan - British English, male, medium quality",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx",
        "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json",
        "size_mb": 63
    }
}


def download_file(url: str, destination: Path, description: str) -> bool:
    """Download a file with progress indicator"""
    try:
        print(f"Downloading {description}...")
        print(f"From: {url}")
        print(f"To: {destination}")

        # Create parent directory if it doesn't exist
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Download with progress
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0

            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"Progress: {progress:.1f}%", end='\r')

        print(f"\n✓ Downloaded {description}")
        return True
    except Exception as e:
        print(f"\n✗ Failed to download {description}: {e}")
        return False


def setup_whisper_models():
    """Download and setup Whisper models"""
    print("\n" + "="*50)
    print("WHISPER STT MODELS")
    print("="*50)

    print("\nAvailable Whisper models:")
    for i, (name, info) in enumerate(WHISPER_MODELS.items(), 1):
        print(f"{i}. {name}: {info['description']}")

    # Get user selection
    while True:
        try:
            choice = input("\nSelect model (1-5, or 'skip' to skip): ").strip()
            if choice.lower() == 'skip':
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(WHISPER_MODELS):
                model_name = list(WHISPER_MODELS.keys())[idx]
                break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or 'skip'.")

    print(f"\nSelected: {model_name}")
    print("Note: faster-whisper will download the model on first use.")
    print("The model will be cached in ~/.cache/huggingface/")

    # Create a test script to trigger download
    test_script = Path("test-whisper-download.py")
    test_content = f"""#!/usr/bin/env python3
from faster_whisper import WhisperModel
import sys

print("Downloading and loading Whisper model: {model_name}")
print("This may take a few minutes on first run...")

try:
    model = WhisperModel("{model_name}", device="cpu", compute_type="int8")
    print("✓ Model loaded successfully!")
    print(f"Model cached for future use.")
except Exception as e:
    print(f"✗ Failed to load model: {{e}}")
    sys.exit(1)
"""

    test_script.write_text(test_content)
    test_script.chmod(0o755)

    print(f"\nCreated test script: {test_script}")
    print("Run it to download the model: python3 test-whisper-download.py")

    return model_name


def setup_piper_voices():
    """Download Piper TTS voices"""
    print("\n" + "="*50)
    print("PIPER TTS VOICES")
    print("="*50)

    print("\nAvailable Piper voices:")
    for i, (name, info) in enumerate(PIPER_VOICES.items(), 1):
        print(f"{i}. {name}: {info['description']}")

    # Get user selection
    while True:
        try:
            choice = input("\nSelect voice (1-4, or 'skip' to skip): ").strip()
            if choice.lower() == 'skip':
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(PIPER_VOICES):
                voice_name = list(PIPER_VOICES.keys())[idx]
                break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or 'skip'.")

    voice_info = PIPER_VOICES[voice_name]

    # Download paths
    models_dir = Path("models/piper")
    models_dir.mkdir(parents=True, exist_ok=True)

    onnx_path = models_dir / f"{voice_name}.onnx"
    config_path = models_dir / f"{voice_name}.onnx.json"

    # Download model
    success = True
    if not onnx_path.exists():
        success = download_file(voice_info["url"], onnx_path, f"{voice_name} model")
    else:
        print(f"✓ {voice_name} model already exists")

    # Download config
    if success and not config_path.exists():
        success = download_file(voice_info["config_url"], config_path, f"{voice_name} config")
    elif success:
        print(f"✓ {voice_name} config already exists")

    if success:
        print(f"\n✓ Successfully set up {voice_name}")
        return str(onnx_path)
    else:
        print(f"\n✗ Failed to set up {voice_name}")
        return None


def create_config_file(whisper_model: Optional[str], piper_voice_path: Optional[str]):
    """Create a configuration file with the selected models"""
    config = {
        "whisper": {
            "model": whisper_model or "base",
            "device": "auto",
            "compute_type": "auto"
        },
        "piper": {
            "voice_path": piper_voice_path or "models/piper/en_US-amy-medium.onnx"
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_duration_ms": 30
        }
    }

    config_path = Path("models/config.json")
    config_path.parent.mkdir(exist_ok=True)

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\nCreated configuration file: {config_path}")
    return config_path


def main():
    print("="*60)
    print("CallMe Local Mode - Model Setup")
    print("="*60)

    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("\n⚠ Warning: Not running in a virtual environment.")
        print("Consider activating venv first: source venv/bin/activate")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)

    # Setup Whisper
    whisper_model = setup_whisper_models()

    # Setup Piper
    piper_voice = setup_piper_voices()

    # Create config file
    if whisper_model or piper_voice:
        create_config_file(whisper_model, piper_voice)

    print("\n" + "="*60)
    print("Setup complete!")
    print("="*60)

    if whisper_model:
        print(f"\nWhisper model selected: {whisper_model}")
        print("Run 'python3 test-whisper-download.py' to download it")

    if piper_voice:
        print(f"\nPiper voice downloaded: {piper_voice}")

    print("\nNext steps:")
    print("1. Test audio setup: python3 test-audio.py")
    print("2. Configure environment: cp .env.example .env.local")
    print("3. Run the local mode: cd server && bun run dev")


if __name__ == "__main__":
    main()