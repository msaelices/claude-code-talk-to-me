"""ElevenLabs TTS provider for cloud-based text-to-speech synthesis."""

import asyncio
import io
import logging
import os
from typing import AsyncGenerator, Optional, Dict, Any

from .base import TTSProvider

logger = logging.getLogger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider for high-quality cloud speech synthesis."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Get API key from config, env var, or raise error
        self.api_key = config.get('api_key',
                                  os.getenv('TALKTOME_ELEVENLABS_API_KEY',
                                           os.getenv('ELEVENLABS_API_KEY')))

        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key not found. Set TALKTOME_ELEVENLABS_API_KEY or "
                "ELEVENLABS_API_KEY environment variable, or pass api_key in config."
            )

        # Voice configuration
        self.voice_id = config.get('voice_id',
                                   os.getenv('TALKTOME_ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM'))  # Default: "Rachel"
        self.model_id = config.get('model_id',
                                   os.getenv('TALKTOME_ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2'))  # Default: Multilingual v2
        self.stability = config.get('stability',
                                    os.getenv('TALKTOME_ELEVENLABS_STABILITY'))
        self.similarity_boost = config.get('similarity_boost',
                                           os.getenv('TALKTOME_ELEVENLABS_SIMILARITY_BOOST'))

        # API endpoint
        self.base_url = "https://api.elevenlabs.io/v1"

        logger.info(f"ElevenLabs TTS initialized with voice: {self.voice_id}, model: {self.model_id}")

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to speech audio.

        Args:
            text: Text to synthesize

        Returns:
            Audio data as bytes (PCM 16-bit, 22050Hz mono)
        """
        if not text or not text.strip():
            return b''

        import aiohttp

        url = f"{self.base_url}/text-to-speech/{self.voice_id}"

        # Build request payload
        payload = {
            "text": text,
            "model_id": self.model_id,
        }

        # Add optional voice settings
        voice_settings = {}
        if self.stability is not None:
            voice_settings['stability'] = float(self.stability)
        if self.similarity_boost is not None:
            voice_settings['similarity_boost'] = float(self.similarity_boost)

        if voice_settings:
            payload['voice_settings'] = voice_settings

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"ElevenLabs API error (status {response.status}): {error_text}"
                        )

                    # ElevenLabs returns MP3 audio
                    mp3_data = await response.read()

                    # Convert MP3 to PCM
                    pcm_data = await self._mp3_to_pcm(mp3_data)

                    return pcm_data

        except aiohttp.ClientError as e:
            logger.error(f"ElevenLabs request failed: {e}")
            raise RuntimeError(f"ElevenLabs TTS request failed: {e}")

    async def _mp3_to_pcm(self, mp3_data: bytes) -> bytes:
        """
        Convert MP3 audio to PCM 16-bit 22050Hz mono.

        This is a simplified implementation. In production, you'd use ffmpeg
        or a proper audio library like pydub.
        """
        import tempfile
        import subprocess

        # Try using ffmpeg for conversion
        try:
            # Create temp files
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as mp3_file:
                mp3_file.write(mp3_data)
                mp3_path = mp3_file.name

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                wav_path = wav_file.name

            # Use ffmpeg to convert: MP3 -> WAV (PCM 16-bit, 22050Hz, mono)
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-i', mp3_path,
                '-f', 'wav',
                '-ar', '22050',  # Sample rate
                '-ac', '1',      # Mono
                '-acodec', 'pcm_s16le',  # 16-bit little-endian PCM
                '-loglevel', 'error',  # Suppress output
                wav_path
            )
            await process.communicate()

            if process.returncode != 0:
                raise RuntimeError("ffmpeg conversion failed")

            # Read the WAV file and skip header
            with open(wav_path, 'rb') as f:
                # Skip WAV header (44 bytes)
                f.seek(44)
                pcm_data = f.read()

            # Clean up temp files
            try:
                os.unlink(mp3_path)
            except:
                pass
            try:
                os.unlink(wav_path)
            except:
                pass

            return pcm_data

        except (FileNotFoundError, RuntimeError) as e:
            # Fallback: try using pydub if available
            try:
                from pydub import AudioSegment

                # Convert MP3 to audio
                audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))

                # Convert to required format: 22050Hz, mono, 16-bit
                audio = audio.set_frame_rate(22050)
                audio = audio.set_channels(1)

                # Export as raw PCM
                import io
                pcm_io = io.BytesIO()
                audio.export(pcm_io, format='raw', codec='pcm_s16le')

                return pcm_io.getvalue()

            except ImportError:
                logger.error("Neither ffmpeg nor pydub available for MP3 conversion")
                raise RuntimeError(
                    "ElevenLabs returns MP3 format. Please install ffmpeg or "
                    "install pydub: pip install pydub"
                )

    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized audio in chunks.

        Note: ElevenLabs streaming API is available but requires websocket.
        For simplicity, this implementation uses the regular HTTP API.

        Args:
            text: Text to synthesize

        Yields:
            Audio chunks as bytes
        """
        # Split text into sentences for streaming
        import re
        sentences = re.findall(r'[^.!?]+[.!?]+|[^.!?]+$', text)

        if len(sentences) <= 1:
            # Short text - just synthesize all at once
            audio = await self.synthesize(text)
            if audio:
                yield audio
            return

        # Process sentences sequentially
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                try:
                    audio = await self.synthesize(sentence)
                    if audio:
                        yield audio
                except Exception as e:
                    logger.error(f"Error generating audio chunk: {e}")
                    # Continue with other chunks even if one fails

    @staticmethod
    async def validate_installation() -> bool:
        """Check if ElevenLabs is configured and accessible."""
        try:
            provider = ElevenLabsTTSProvider()
            # Try a simple synthesis
            test_audio = await provider.synthesize("test")
            return len(test_audio) > 0
        except Exception as e:
            logger.warning(f"ElevenLabs validation failed: {e}")
            return False
