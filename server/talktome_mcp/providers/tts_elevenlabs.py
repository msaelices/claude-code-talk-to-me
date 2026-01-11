"""ElevenLabs TTS provider for cloud-based text-to-speech synthesis."""

import io
import logging
import os
from typing import Optional, Dict, Any

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
        Convert MP3 audio to PCM 16-bit 22050Hz mono using pydub.

        Note: pydub requires ffmpeg to be installed for MP3 decoding.
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            raise RuntimeError(
                "pydub is required for MP3 conversion. Install it with: pip install pydub"
            )

        # Convert MP3 to audio segment (in memory, no temp files)
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))

        # Convert to required format: 22050Hz, mono, 16-bit
        audio = audio.set_frame_rate(22050).set_channels(1)

        # Export as raw PCM (use s16le format directly instead of raw with codec)
        pcm_io = io.BytesIO()
        audio.export(pcm_io, format='s16le')

        return pcm_io.getvalue()
