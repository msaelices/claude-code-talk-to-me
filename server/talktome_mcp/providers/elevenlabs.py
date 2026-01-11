"""ElevenLabs providers for cloud-based text-to-speech and speech-to-text."""

import asyncio
import io
import logging
import os
from typing import Any, Dict, Optional

import numpy as np
from elevenlabs.client import ElevenLabs

from .base import RealtimeSTTProvider, TTSProvider

logger = logging.getLogger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider for high-quality cloud speech synthesis."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Get API key from config, env var, or raise error
        self.api_key = config.get("api_key", os.getenv("TALKTOME_ELEVENLABS_API_KEY", os.getenv("ELEVENLABS_API_KEY")))

        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key not found. Set TALKTOME_ELEVENLABS_API_KEY or "
                "ELEVENLABS_API_KEY environment variable, or pass api_key in config."
            )

        # Voice configuration
        self.voice_id = config.get(
            "voice_id", os.getenv("TALKTOME_ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        )  # Default: "Rachel"
        self.model_id = config.get(
            "model_id", os.getenv("TALKTOME_ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
        )  # Default: Multilingual v2
        self.stability = config.get("stability", os.getenv("TALKTOME_ELEVENLABS_STABILITY"))
        self.similarity_boost = config.get("similarity_boost", os.getenv("TALKTOME_ELEVENLABS_SIMILARITY_BOOST"))

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
            return b""

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
            voice_settings["stability"] = float(self.stability)
        if self.similarity_boost is not None:
            voice_settings["similarity_boost"] = float(self.similarity_boost)

        if voice_settings:
            payload["voice_settings"] = voice_settings

        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": self.api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"ElevenLabs API error (status {response.status}): {error_text}")

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
            raise RuntimeError("pydub is required for MP3 conversion. Install it with: pip install pydub")

        # Convert MP3 to audio segment (in memory, no temp files)
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))

        # Convert to required format: 22050Hz, mono, 16-bit
        audio = audio.set_frame_rate(22050).set_channels(1)

        # Export as raw PCM (use s16le format directly instead of raw with codec)
        pcm_io = io.BytesIO()
        audio.export(pcm_io, format="s16le")

        return pcm_io.getvalue()


class ElevenLabsSTTProvider(RealtimeSTTProvider):
    """ElevenLabs STT provider for real-time cloud speech recognition.

    Uses the ElevenLabs Python SDK with local Voice Activity Detection (VAD)
    to detect speech segments and transcribe them via the batch API.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Get API key from config or environment
        self.api_key = config.get("api_key", os.getenv("TALKTOME_ELEVENLABS_API_KEY", os.getenv("ELEVENLABS_API_KEY")))

        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key not found. Set TALKTOME_ELEVENLABS_API_KEY or "
                "ELEVENLABS_API_KEY environment variable, or pass api_key in config."
            )

        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=self.api_key)

        # Model configuration
        self.model_id = config.get("model_id", os.getenv("TALKTOME_ELEVENLABS_STT_MODEL", "scribe_v2"))
        self.language_code = config.get("language_code", os.getenv("TALKTOME_ELEVENLABS_LANGUAGE", "en"))

        # VAD configuration for local speech detection
        self.energy_threshold = config.get(
            "energy_threshold", float(os.getenv("TALKTOME_STT_ENERGY_THRESHOLD", "0.01"))
        )
        self.silence_duration_ms = config.get(
            "silence_duration_ms", int(os.getenv("TALKTOME_STT_SILENCE_DURATION_MS", "800"))
        )
        self.min_speech_duration_ms = config.get(
            "min_speech_duration_ms", int(os.getenv("TALKTOME_STT_MIN_SPEECH_MS", "250"))
        )

        # Audio configuration - matches LocalPhoneProvider output
        self.sample_rate = 16000
        self.bytes_per_sample = 2  # 16-bit audio

        # Streaming state
        self.streaming = False
        self.audio_buffer = bytearray()
        self.is_speaking = False
        self.silence_samples = 0
        self.speech_samples = 0
        self.pending_transcription: Optional[str] = None

        # Calculate sample counts for timing
        self.silence_samples_threshold = int(self.silence_duration_ms * self.sample_rate / 1000)
        self.min_speech_samples = int(self.min_speech_duration_ms * self.sample_rate / 1000)

        logger.info(f"ElevenLabs STT initialized with model: {self.model_id}")

    async def transcribe(self, audio: bytes) -> str:
        """
        One-shot transcription using the ElevenLabs SDK.

        Args:
            audio: Audio data as bytes (PCM 16-bit, 16kHz mono)

        Returns:
            Transcribed text
        """
        if not audio or len(audio) < 1000:
            return ""

        try:
            # Convert PCM to WAV format for the API
            wav_data = self._pcm_to_wav(audio)

            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(
                None,
                lambda: self.client.speech_to_text.convert(
                    file=io.BytesIO(wav_data),
                    model_id=self.model_id,
                    language_code=self.language_code if self.language_code else None,
                ),
            )

            return transcription.text if transcription and transcription.text else ""

        except Exception as e:
            logger.error(f"ElevenLabs STT transcription failed: {e}")
            return ""

    async def start_stream(self) -> None:
        """Start streaming session for real-time transcription."""
        self.streaming = True
        self.audio_buffer = bytearray()
        self.is_speaking = False
        self.silence_samples = 0
        self.speech_samples = 0
        self.pending_transcription = None
        logger.info("ElevenLabs STT streaming started (local VAD mode)")

    async def stop_stream(self) -> None:
        """Stop streaming session."""
        self.streaming = False
        self.audio_buffer = bytearray()
        self.is_speaking = False
        logger.info("ElevenLabs STT streaming stopped")

    async def process_audio_chunk(self, audio: bytes) -> Optional[str]:
        """
        Process an audio chunk and return transcription when speech ends.

        Uses local VAD to detect speech segments. When the user stops speaking
        (silence detected), sends accumulated audio to the batch API for transcription.

        Args:
            audio: Audio chunk as bytes (PCM 16-bit, 16kHz mono)

        Returns:
            Transcribed text when speech end is detected, None otherwise
        """
        if not self.streaming:
            return None

        # Calculate energy of this chunk for VAD
        energy = self._calculate_energy(audio)
        num_samples = len(audio) // self.bytes_per_sample

        if energy > self.energy_threshold:
            # Speech detected
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_samples = 0
                logger.debug("Speech started")

            self.speech_samples += num_samples
            self.silence_samples = 0
            self.audio_buffer.extend(audio)

        elif self.is_speaking:
            # We were speaking, now silence
            self.silence_samples += num_samples
            self.audio_buffer.extend(audio)  # Include some trailing silence

            if self.silence_samples >= self.silence_samples_threshold:
                # End of speech detected
                logger.debug(f"Speech ended after {self.speech_samples} samples")

                if self.speech_samples >= self.min_speech_samples:
                    # Enough speech to transcribe
                    audio_data = bytes(self.audio_buffer)
                    self.audio_buffer = bytearray()
                    self.is_speaking = False
                    self.speech_samples = 0
                    self.silence_samples = 0

                    # Transcribe the accumulated audio
                    text = await self.transcribe(audio_data)
                    if text:
                        logger.info(f"Transcribed: {text}")
                        return text
                else:
                    # Too short, discard
                    logger.debug("Speech too short, discarding")
                    self.audio_buffer = bytearray()
                    self.is_speaking = False
                    self.speech_samples = 0
                    self.silence_samples = 0

        return None

    async def get_final_transcription(self) -> str:
        """Get any remaining buffered transcription."""
        if len(self.audio_buffer) > 0 and self.speech_samples >= self.min_speech_samples:
            audio_data = bytes(self.audio_buffer)
            self.audio_buffer = bytearray()
            text = await self.transcribe(audio_data)
            return text
        return ""

    def _calculate_energy(self, audio: bytes) -> float:
        """Calculate RMS energy of audio chunk."""
        if len(audio) < 2:
            return 0.0

        # Convert bytes to numpy array (16-bit signed integers)
        samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32)

        # Normalize to [-1, 1] range
        samples = samples / 32768.0

        # Calculate RMS energy
        rms = np.sqrt(np.mean(samples**2))
        return float(rms)

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert raw PCM audio to WAV format."""
        import struct

        # WAV header parameters
        num_channels = 1
        sample_width = 2  # 16-bit

        # Create WAV header
        wav_header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(pcm_data),  # File size - 8
            b"WAVE",
            b"fmt ",
            16,  # fmt chunk size
            1,  # Audio format (PCM)
            num_channels,
            self.sample_rate,
            self.sample_rate * num_channels * sample_width,  # Byte rate
            num_channels * sample_width,  # Block align
            sample_width * 8,  # Bits per sample
            b"data",
            len(pcm_data),
        )

        return wav_header + pcm_data
