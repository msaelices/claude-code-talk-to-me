"""Piper TTS provider for local text-to-speech synthesis."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .base import TTSProvider

logger = logging.getLogger(__name__)


class PiperTTSProvider(TTSProvider):
    """Piper neural TTS provider for fast local speech synthesis."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Model configuration - resolve relative to server directory or project root
        default_model = Path("models/piper/en_US-amy-medium.onnx")

        # Get model path from config, env var, or default
        model_path_str = config.get("model_path", os.getenv("TALKTOME_PIPER_MODEL_PATH", str(default_model)))
        self.model_path = Path(model_path_str)

        # If relative path and doesn't exist, try resolving from project root
        if not self.model_path.is_absolute() and not self.model_path.exists():
            # Get the directory containing this file (server/talktome_mcp/providers/)
            # and go up to project root (need to go up 3 levels: providers/ -> talktome_mcp/ -> server/ -> project_root/)
            providers_dir = Path(__file__).parent
            talktome_mcp_dir = providers_dir.parent
            server_dir = talktome_mcp_dir.parent
            project_root = server_dir.parent
            alternative_path = project_root / self.model_path

            if alternative_path.exists():
                self.model_path = alternative_path

        # Voice parameters
        self.speaker_id = config.get("speaker_id")
        self.length_scale = config.get("length_scale")  # Speaking rate
        self.noise_scale = config.get("noise_scale")  # Variation in speech
        self.noise_w = config.get("noise_w")  # Phoneme duration variation

        # Verify model exists
        if not self.model_path.exists():
            logger.warning(f"Piper model not found at {self.model_path}")
            logger.warning("Please run: python3 download-models.py")

        # Convert to absolute path for subprocess AFTER path resolution
        self.model_path = self.model_path.resolve()

        logger.info(f"Using Piper model: {self.model_path}")

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to speech audio.

        Args:
            text: Text to synthesize

        Returns:
            Audio data as bytes (PCM 16-bit, 22050Hz)
        """
        import tempfile

        # Create a temporary file for input text
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(text)
            input_file = f.name

        # Create a temporary file for output audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_file = f.name

        try:
            # Build command arguments
            cmd = [
                sys.executable,
                "-m",
                "piper",
                "-m",
                str(self.model_path),
                "-i",
                input_file,  # Input file
                "-o",
                output_file,  # Output file
                "--quiet",
            ]  # Suppress progress output

            # Debug: log the command
            logger.debug(f"Running Piper command: {' '.join(cmd)}")

            # Add optional voice parameters
            if self.speaker_id is not None:
                cmd.extend(["--speaker", str(self.speaker_id)])
            if self.length_scale is not None:
                cmd.extend(["--length-scale", str(self.length_scale)])
            if self.noise_scale is not None:
                cmd.extend(["--noise-scale", str(self.noise_scale)])
            if self.noise_w is not None:
                cmd.extend(["--noise-w", str(self.noise_w)])

            # Run Piper asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                raise RuntimeError(f"Piper synthesis failed: {error_msg}")

            # Read the output WAV file and extract PCM data
            with open(output_file, "rb") as f:
                # Skip WAV header (44 bytes) and return raw PCM
                f.seek(44)
                audio_data = f.read()

            # Debug: log what we received
            logger.debug(f"Piper returned {len(audio_data)} bytes of audio, stderr: {len(stderr)} bytes")
            if stderr:
                logger.warning(f"Piper stderr: {stderr.decode('utf-8', errors='replace')[:200]}")

            # Return raw PCM audio (22050Hz, 16-bit mono)
            return audio_data

        finally:
            # Clean up temporary files
            Path(input_file).unlink(missing_ok=True)
            Path(output_file).unlink(missing_ok=True)
