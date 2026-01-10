"""Piper TTS provider for local text-to-speech synthesis."""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any
import sys
import re

from .base import TTSProvider

logger = logging.getLogger(__name__)


class PiperTTSProvider(TTSProvider):
    """Piper neural TTS provider for fast local speech synthesis."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Model configuration - resolve relative to server directory or project root
        default_model = Path('models/piper/en_US-amy-medium.onnx')

        # Get model path from config, env var, or default
        model_path_str = config.get('model_path',
                                    os.getenv('TALKTOME_PIPER_MODEL_PATH', str(default_model)))
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
        self.speaker_id = config.get('speaker_id')
        self.length_scale = config.get('length_scale')  # Speaking rate
        self.noise_scale = config.get('noise_scale')    # Variation in speech
        self.noise_w = config.get('noise_w')            # Phoneme duration variation

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
        # Build command arguments
        cmd = [sys.executable, '-m', 'piper',
               '-m', str(self.model_path),
               '--output-raw',  # Output raw PCM
               '--quiet']       # Suppress progress output

        # Add optional voice parameters
        if self.speaker_id is not None:
            cmd.extend(['--speaker', str(self.speaker_id)])
        if self.length_scale is not None:
            cmd.extend(['--length-scale', str(self.length_scale)])
        if self.noise_scale is not None:
            cmd.extend(['--noise-scale', str(self.noise_scale)])
        if self.noise_w is not None:
            cmd.extend(['--noise-w', str(self.noise_w)])

        # Run Piper asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Send text and get audio
        stdout, stderr = await process.communicate(text.encode('utf-8'))

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else 'Unknown error'
            raise RuntimeError(f"Piper synthesis failed: {error_msg}")

        # Return raw PCM audio (22050Hz, 16-bit mono)
        return stdout

    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized audio in chunks for lower latency.

        Args:
            text: Text to synthesize

        Yields:
            Audio chunks as bytes
        """
        # Split text into sentences for streaming
        sentences = self._split_into_sentences(text)

        if len(sentences) <= 1:
            # Short text - just synthesize all at once
            audio = await self.synthesize(text)
            yield audio
            return

        # Process sentences in parallel for streaming
        tasks = [self.synthesize(sentence) for sentence in sentences]

        # Yield audio chunks as they complete
        for task in asyncio.as_completed(tasks):
            try:
                audio = await task
                if audio:
                    yield audio
            except Exception as e:
                logger.error(f"Error generating audio chunk: {e}")
                # Continue with other chunks even if one fails

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences for streaming synthesis."""
        # Simple sentence splitter - splits on punctuation while keeping it
        sentences = re.findall(r'[^.!?]+[.!?]+|[^.!?]+$', text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    async def validate_installation() -> bool:
        """Check if Piper is installed and accessible."""
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'piper', '--help',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=5)
            return process.returncode == 0
        except (asyncio.TimeoutError, FileNotFoundError):
            return False

    @staticmethod
    async def get_available_voices() -> list[str]:
        """Get list of available Piper models."""
        models_dir = Path('models/piper')
        if not models_dir.exists():
            return []

        return [str(f) for f in models_dir.glob('*.onnx')]