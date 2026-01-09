#!/usr/bin/env python3
"""
Test audio input/output and basic TTS/STT functionality
"""

import sys
import time
import json
import wave
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

# Check for required libraries
try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    print("Error: Required libraries not installed.")
    print("Please run: pip install sounddevice numpy")
    sys.exit(1)


def test_audio_devices():
    """List and test audio devices"""
    print("\n" + "="*50)
    print("AUDIO DEVICES TEST")
    print("="*50)

    print("\nAvailable audio devices:")
    print("-" * 40)

    devices = sd.query_devices()

    # Find default devices
    default_input = sd.default.device[0]
    default_output = sd.default.device[1]

    for i, device in enumerate(devices):
        device_type = []
        if device['max_input_channels'] > 0:
            device_type.append("INPUT")
        if device['max_output_channels'] > 0:
            device_type.append("OUTPUT")

        default_marker = ""
        if i == default_input:
            default_marker = " [DEFAULT INPUT]"
        elif i == default_output:
            default_marker = " [DEFAULT OUTPUT]"

        print(f"{i}: {device['name']} ({', '.join(device_type)}){default_marker}")
        print(f"   Sample rate: {device['default_samplerate']} Hz")
        print(f"   Channels: in={device['max_input_channels']}, out={device['max_output_channels']}")

    return True


def test_audio_playback():
    """Test audio output with a simple tone"""
    print("\n" + "="*50)
    print("AUDIO PLAYBACK TEST")
    print("="*50)

    print("\nPlaying test tone (440 Hz for 1 second)...")

    try:
        # Generate a 440 Hz sine wave (A note)
        sample_rate = 44100
        duration = 1.0
        frequency = 440.0

        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = 0.3 * np.sin(2 * np.pi * frequency * t)  # 0.3 amplitude to not be too loud

        sd.play(waveform, sample_rate)
        sd.wait()

        print("✓ Audio playback successful")
        return True
    except Exception as e:
        print(f"✗ Audio playback failed: {e}")
        return False


def test_audio_recording():
    """Test audio input with recording"""
    print("\n" + "="*50)
    print("AUDIO RECORDING TEST")
    print("="*50)

    duration = 3
    sample_rate = 16000  # Standard for speech recognition

    print(f"\nRecording {duration} seconds of audio...")
    print("Please say something!")

    try:
        # Record audio
        recording = sd.rec(int(duration * sample_rate),
                          samplerate=sample_rate,
                          channels=1,
                          dtype='float32')
        sd.wait()

        # Check if we got audio
        max_amplitude = np.max(np.abs(recording))
        print(f"\nMax amplitude: {max_amplitude:.4f}")

        if max_amplitude > 0.001:  # Threshold for detecting sound
            print("✓ Audio recording successful - sound detected")

            # Save to temporary file for inspection
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_path = f.name

            # Convert to int16 for WAV file
            audio_int16 = (recording * 32767).astype(np.int16)

            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 2 bytes for int16
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())

            print(f"✓ Recording saved to: {temp_path}")
            return True, temp_path
        else:
            print("⚠ Warning: No sound detected. Check your microphone.")
            return False, None

    except Exception as e:
        print(f"✗ Audio recording failed: {e}")
        return False, None


def test_piper_tts():
    """Test Piper TTS if available"""
    print("\n" + "="*50)
    print("PIPER TTS TEST")
    print("="*50)

    # Check if Piper is installed
    try:
        import sys
        python_path = sys.executable
        result = subprocess.run([python_path, '-m', 'piper', '--help'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        if result.returncode != 0:
            print("⚠ Piper not found. Install with: pip install piper-tts")
            return False
    except (subprocess.SubprocessError, FileNotFoundError):
        print("⚠ Piper not found. Install with: pip install piper-tts")
        return False

    # Check for model
    models_dir = Path("models/piper")
    onnx_files = list(models_dir.glob("*.onnx")) if models_dir.exists() else []

    if not onnx_files:
        print("⚠ No Piper models found.")
        print("Run: python3 download-models.py")
        return False

    model_path = onnx_files[0]
    print(f"Using model: {model_path.name}")

    # Test TTS
    test_text = "Hello! This is a test of the Piper text to speech system."
    print(f"\nGenerating speech: '{test_text}'")

    try:
        # Generate audio
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            output_path = f.name

        import sys
        python_path = sys.executable
        cmd = [python_path, '-m', 'piper', '-m', str(model_path), '-o', output_path]
        result = subprocess.run(cmd,
                              input=test_text,
                              text=True,
                              capture_output=True,
                              timeout=10)

        if result.returncode == 0:
            print("✓ TTS generation successful")

            # Play the generated audio
            print("Playing generated speech...")
            subprocess.run(['aplay', output_path],
                         capture_output=True,
                         timeout=5)

            print(f"✓ Audio file: {output_path}")
            return True
        else:
            print(f"✗ TTS generation failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"✗ TTS test failed: {e}")
        return False


def test_whisper_stt(audio_file: Optional[str] = None):
    """Test Whisper STT if available"""
    print("\n" + "="*50)
    print("WHISPER STT TEST")
    print("="*50)

    # Check if faster-whisper is installed
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("⚠ faster-whisper not found. Install with: pip install faster-whisper")
        return False

    if not audio_file:
        print("⚠ No audio file provided. Record audio first.")
        return False

    # Load config to get model name
    config_path = Path("models/config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        model_name = config.get("whisper", {}).get("model", "base")
    else:
        model_name = "base"

    print(f"Loading Whisper model: {model_name}")
    print("This may take a moment on first run...")

    try:
        # Load model
        model = WhisperModel(model_name, device="cpu", compute_type="int8")

        # Transcribe
        print(f"\nTranscribing audio file: {audio_file}")
        segments, info = model.transcribe(audio_file, beam_size=5)

        print(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")

        # Get transcription
        transcription = ""
        for segment in segments:
            transcription += segment.text
            print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")

        if transcription:
            print(f"\n✓ Transcription successful: '{transcription.strip()}'")
            return True
        else:
            print("⚠ No speech detected in audio")
            return False

    except Exception as e:
        print(f"✗ STT test failed: {e}")
        return False


def test_pulse_audio():
    """Test PulseAudio/PipeWire"""
    print("\n" + "="*50)
    print("PULSEAUDIO/PIPEWIRE TEST")
    print("="*50)

    try:
        result = subprocess.run(['pactl', 'info'],
                              capture_output=True,
                              text=True,
                              timeout=5)

        if result.returncode == 0:
            # Parse output
            for line in result.stdout.split('\n'):
                if 'Server Name:' in line:
                    server = line.split(':', 1)[1].strip()
                    print(f"✓ Audio server: {server}")
                elif 'Default Sink:' in line:
                    sink = line.split(':', 1)[1].strip()
                    print(f"✓ Default output: {sink}")
                elif 'Default Source:' in line:
                    source = line.split(':', 1)[1].strip()
                    print(f"✓ Default input: {source}")

            return True
        else:
            print("⚠ PulseAudio/PipeWire not running")
            return False

    except Exception as e:
        print(f"⚠ Could not test PulseAudio: {e}")
        return False


def main():
    print("="*60)
    print("CallMe Local Mode - Audio System Test")
    print("="*60)

    results = {}

    # Test audio devices
    results['devices'] = test_audio_devices()

    # Test PulseAudio
    results['pulse'] = test_pulse_audio()

    # Test playback
    results['playback'] = test_audio_playback()

    # Test recording
    recording_success, audio_file = test_audio_recording()
    results['recording'] = recording_success

    # Test TTS
    results['tts'] = test_piper_tts()

    # Test STT with recorded audio
    if audio_file:
        results['stt'] = test_whisper_stt(audio_file)
    else:
        results['stt'] = False

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test.upper():15} {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✓ All tests passed! Audio system is ready.")
    else:
        print("\n⚠ Some tests failed. Please check the output above.")
        print("\nTroubleshooting:")
        if not results['devices']:
            print("- Check that your audio devices are connected")
        if not results['pulse']:
            print("- Install PulseAudio: sudo apt install pulseaudio-utils")
        if not results['recording']:
            print("- Check microphone permissions and settings")
        if not results['tts']:
            print("- Install Piper: pip install piper-tts")
            print("- Download models: python3 download-models.py")
        if not results['stt']:
            print("- Install Whisper: pip install faster-whisper")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())