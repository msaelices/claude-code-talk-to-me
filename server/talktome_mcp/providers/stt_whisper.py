"""Whisper STT provider using faster-whisper."""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
import numpy as np
from faster_whisper import WhisperModel
import torch
import io
import wave

from .base import RealtimeSTTProvider

logger = logging.getLogger(__name__)


class WhisperSTTProvider(RealtimeSTTProvider):
    """Whisper-based speech-to-text provider with VAD support."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Model configuration
        self.model_name = config.get('model_name', os.getenv('TALKTOME_WHISPER_MODEL', 'base'))
        self.device = config.get('device', os.getenv('TALKTOME_WHISPER_DEVICE', 'auto'))
        self.compute_type = config.get('compute_type', os.getenv('TALKTOME_WHISPER_COMPUTE_TYPE', 'auto'))

        # Detection configuration
        self.chunk_duration_ms = config.get('chunk_duration_ms', 2000)
        self.silence_duration_ms = config.get('silence_duration_ms',
                                             int(os.getenv('TALKTOME_STT_SILENCE_DURATION_MS', '800')))
        self.vad_threshold = config.get('vad_threshold', 0.5)

        # Auto-detect device if needed
        if self.device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # Auto-detect compute type
        if self.compute_type == 'auto':
            if self.device == 'cuda':
                self.compute_type = 'float16'
            else:
                self.compute_type = 'int8'

        logger.info(f"Loading Whisper model: {self.model_name} on {self.device} with {self.compute_type}")

        # Initialize model
        self.model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type
        )

        # Initialize VAD
        try:
            self._init_vad()
        except Exception as e:
            logger.warning(f"VAD initialization failed: {e}. Continuing without VAD.")
            self.vad_model = None

        # Stream state
        self.audio_buffer = bytearray()
        self.sample_rate = 16000
        self.streaming = False
        self.silence_samples = 0
        self.silence_threshold = int(self.silence_duration_ms * self.sample_rate / 1000)

    def _init_vad(self):
        """Initialize Silero VAD model."""
        try:
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            self.vad_model = model
            self.get_speech_timestamps = utils[0]
        except Exception as e:
            logger.error(f"Failed to load VAD model: {e}")
            self.vad_model = None

    async def transcribe(self, audio: bytes) -> str:
        """Transcribe complete audio to text."""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

        # Run transcription
        segments, info = self.model.transcribe(
            audio_array,
            beam_size=5,
            language='en',
            vad_filter=True if self.vad_model else False
        )

        # Combine segments
        transcription = ' '.join(segment.text.strip() for segment in segments)
        return transcription

    async def start_stream(self) -> None:
        """Start streaming transcription."""
        self.streaming = True
        self.audio_buffer = bytearray()
        self.silence_samples = 0
        logger.info("Started Whisper streaming")

    async def stop_stream(self) -> None:
        """Stop streaming transcription."""
        self.streaming = False
        logger.info("Stopped Whisper streaming")

    async def process_audio_chunk(self, audio: bytes) -> Optional[str]:
        """
        Process audio chunk and return transcription when speech ends.

        Args:
            audio: Audio chunk as bytes (PCM 16-bit)

        Returns:
            Transcribed text when sentence completes, None otherwise
        """
        if not self.streaming:
            return None

        # Add to buffer
        self.audio_buffer.extend(audio)

        # Check for voice activity
        if self.vad_model:
            audio_array = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_array)

            speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()

            if speech_prob < self.vad_threshold:
                self.silence_samples += len(audio) // 2  # 16-bit samples
            else:
                self.silence_samples = 0

        else:
            # Simple amplitude-based detection
            audio_array = np.frombuffer(audio, dtype=np.int16)
            max_amplitude = np.max(np.abs(audio_array))

            if max_amplitude < 500:  # Threshold for silence
                self.silence_samples += len(audio) // 2
            else:
                self.silence_samples = 0

        # Check if we have enough silence to transcribe
        if self.silence_samples >= self.silence_threshold and len(self.audio_buffer) > 0:
            # Process buffered audio
            result = await self.transcribe(bytes(self.audio_buffer))

            # Clear buffer
            self.audio_buffer = bytearray()
            self.silence_samples = 0

            if result.strip():
                logger.info(f"Transcribed: {result}")
                return result

        return None

    async def get_final_transcription(self) -> str:
        """Get final transcription of any remaining audio."""
        if len(self.audio_buffer) > 0:
            result = await self.transcribe(bytes(self.audio_buffer))
            self.audio_buffer = bytearray()
            return result
        return ""