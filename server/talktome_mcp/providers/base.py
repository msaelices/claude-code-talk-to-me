"""Base provider interfaces for CallMe MCP."""

import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Dict, Any

from ..utils import split_into_sentences

logger = logging.getLogger(__name__)


class PhoneProvider(ABC):
    """Abstract base class for phone/audio providers."""

    @abstractmethod
    async def make_call(self, phone_number: str) -> str:
        """
        Initiate a call/audio session.

        Args:
            phone_number: Target number (or "local" for local audio)

        Returns:
            Call ID for the session
        """
        pass

    @abstractmethod
    async def hang_up(self, call_id: str) -> None:
        """End a call/audio session."""
        pass

    @abstractmethod
    async def send_audio(self, call_id: str, audio: bytes) -> None:
        """Send audio data to the call."""
        pass

    async def wait_for_playback_complete(self, call_id: str, timeout: float = 10.0) -> None:
        """Wait for all queued audio to finish playing. Default implementation does nothing."""
        pass

    @abstractmethod
    async def pause_recording(self, call_id: str) -> None:
        """Pause recording to prevent audio feedback during TTS playback."""
        pass

    @abstractmethod
    async def resume_recording(self, call_id: str) -> None:
        """Resume recording after TTS playback completes."""
        pass

    @abstractmethod
    async def get_audio_stream(self, call_id: str) -> AsyncGenerator[bytes, None]:
        """Get incoming audio stream from the call."""
        pass

    @abstractmethod
    async def is_call_active(self, call_id: str) -> bool:
        """Check if a call is still active."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up provider resources."""
        pass


class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """
        Convert text to speech audio.

        Args:
            text: Text to synthesize

        Returns:
            Audio data as bytes (PCM 16-bit)
        """
        pass

    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized audio in chunks for lower latency.

        Splits text into sentences and synthesizes each one,
        yielding audio chunks as they're ready.

        Args:
            text: Text to synthesize

        Yields:
            Audio chunks as bytes
        """
        sentences = split_into_sentences(text)

        if len(sentences) <= 1:
            # Short text - just synthesize all at once
            audio = await self.synthesize(text)
            if audio:
                yield audio
            return

        # Process sentences sequentially
        for sentence in sentences:
            if sentence:
                try:
                    audio = await self.synthesize(sentence)
                    if audio:
                        yield audio
                except Exception as e:
                    logger.error(f"Error generating audio chunk: {e}")
                    # Continue with other chunks even if one fails


class STTProvider(ABC):
    """Abstract base class for speech-to-text providers."""

    @abstractmethod
    async def transcribe(self, audio: bytes) -> str:
        """
        Transcribe audio to text.

        Args:
            audio: Audio data as bytes (PCM 16-bit)

        Returns:
            Transcribed text
        """
        pass


class RealtimeSTTProvider(STTProvider):
    """Abstract base class for real-time streaming STT providers."""

    @abstractmethod
    async def start_stream(self) -> None:
        """Start the STT stream."""
        pass

    @abstractmethod
    async def stop_stream(self) -> None:
        """Stop the STT stream."""
        pass

    @abstractmethod
    async def process_audio_chunk(self, audio: bytes) -> Optional[str]:
        """
        Process an audio chunk and return transcription if available.

        Args:
            audio: Audio chunk as bytes

        Returns:
            Transcribed text if a sentence/phrase is complete, None otherwise
        """
        pass

    @abstractmethod
    async def get_final_transcription(self) -> str:
        """Get the final transcription when stream ends."""
        pass


class Call:
    """Represents an active call/audio session."""

    def __init__(self, call_id: str):
        self.id = call_id
        self.active = True
        self.metadata: Dict[str, Any] = {}

    async def end(self) -> None:
        """End the call."""
        self.active = False