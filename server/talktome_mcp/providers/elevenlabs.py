"""ElevenLabs providers for cloud-based text-to-speech and speech-to-text."""

import asyncio
import base64
import io
import json
import logging
import os
from typing import Any, Dict, Optional

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

    Uses the ElevenLabs WebSocket API for streaming speech-to-text with
    Voice Activity Detection (VAD) for automatic speech end detection.
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

        # Model configuration
        self.model_id = config.get("model_id", os.getenv("TALKTOME_ELEVENLABS_STT_MODEL", "scribe_v2_realtime"))
        self.language_code = config.get("language_code", os.getenv("TALKTOME_ELEVENLABS_LANGUAGE", "en"))

        # VAD configuration
        self.vad_silence_threshold = config.get(
            "vad_silence_threshold",
            float(os.getenv("TALKTOME_STT_SILENCE_DURATION_MS", "800")) / 1000.0,  # Convert ms to seconds
        )
        self.vad_threshold = config.get("vad_threshold", float(os.getenv("TALKTOME_STT_VAD_THRESHOLD", "0.4")))
        self.min_speech_duration_ms = config.get(
            "min_speech_duration_ms", int(os.getenv("TALKTOME_STT_MIN_SPEECH_MS", "250"))
        )
        self.min_silence_duration_ms = config.get(
            "min_silence_duration_ms", int(os.getenv("TALKTOME_STT_MIN_SILENCE_MS", "500"))
        )

        # Audio configuration - matches LocalPhoneProvider output
        self.sample_rate = 16000

        # WebSocket state
        self.ws = None
        self.streaming = False
        self.receive_task = None
        self.transcription_buffer = []
        self.pending_transcription: Optional[str] = None
        self._transcription_event = None

        logger.info(f"ElevenLabs STT initialized with model: {self.model_id}")

    async def transcribe(self, audio: bytes) -> str:
        """
        One-shot transcription using HTTP API.

        Args:
            audio: Audio data as bytes (PCM 16-bit, 16kHz mono)

        Returns:
            Transcribed text
        """
        import aiohttp

        url = "https://api.elevenlabs.io/v1/speech-to-text"

        headers = {"xi-api-key": self.api_key}

        # Create form data with audio file
        form_data = aiohttp.FormData()
        form_data.add_field("file", audio, filename="audio.pcm", content_type="audio/pcm")
        form_data.add_field("model_id", self.model_id)
        if self.language_code:
            form_data.add_field("language_code", self.language_code)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form_data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"ElevenLabs STT API error (status {response.status}): {error_text}")

                    result = await response.json()
                    return result.get("text", "")

        except aiohttp.ClientError as e:
            logger.error(f"ElevenLabs STT request failed: {e}")
            raise RuntimeError(f"ElevenLabs STT request failed: {e}")

    async def start_stream(self) -> None:
        """Start WebSocket streaming connection for real-time transcription."""
        import websockets

        # Build WebSocket URL with query parameters
        params = [
            f"model_id={self.model_id}",
            "audio_format=pcm_16000",
            "commit_strategy=vad",  # Use VAD for automatic speech detection
            f"vad_silence_threshold_secs={self.vad_silence_threshold}",
            f"vad_threshold={self.vad_threshold}",
            f"min_speech_duration_ms={self.min_speech_duration_ms}",
            f"min_silence_duration_ms={self.min_silence_duration_ms}",
        ]
        if self.language_code:
            params.append(f"language_code={self.language_code}")

        url = f"wss://api.elevenlabs.io/v1/speech-to-text/realtime?{'&'.join(params)}"
        headers = {"xi-api-key": self.api_key}

        try:
            self.ws = await websockets.connect(url, additional_headers=headers)
            self.streaming = True
            self.transcription_buffer = []
            self.pending_transcription = None
            self._transcription_event = asyncio.Event()

            # Wait for session started message
            session_msg = await asyncio.wait_for(self.ws.recv(), timeout=10.0)
            data = json.loads(session_msg)
            if data.get("message_type") == "session_started":
                logger.info(f"ElevenLabs STT session started: {data}")
            else:
                logger.warning(f"Unexpected first message: {data}")

            # Start background task to receive transcriptions
            self.receive_task = asyncio.create_task(self._receive_transcripts())

            logger.info("ElevenLabs STT streaming started")

        except Exception as e:
            logger.error(f"Failed to start ElevenLabs STT stream: {e}")
            self.streaming = False
            raise RuntimeError(f"Failed to start ElevenLabs STT stream: {e}")

    async def stop_stream(self) -> None:
        """Stop streaming connection."""
        self.streaming = False

        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None

        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            self.ws = None

        logger.info("ElevenLabs STT streaming stopped")

    async def process_audio_chunk(self, audio: bytes) -> Optional[str]:
        """
        Process an audio chunk and return transcription when available.

        Args:
            audio: Audio chunk as bytes (PCM 16-bit, 16kHz mono)

        Returns:
            Transcribed text when speech end is detected, None otherwise
        """
        if not self.streaming or not self.ws:
            return None

        try:
            # Encode audio as base64 and send to WebSocket
            audio_b64 = base64.b64encode(audio).decode("utf-8")
            message = json.dumps(
                {
                    "message_type": "input_audio_chunk",
                    "audio_base_64": audio_b64,
                    "commit": False,
                    "sample_rate": self.sample_rate,
                }
            )
            await self.ws.send(message)

            # Check if we have a pending transcription from the receive task
            if self.pending_transcription:
                result = self.pending_transcription
                self.pending_transcription = None
                return result

            return None

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return None

    async def get_final_transcription(self) -> str:
        """Get any remaining buffered transcription."""
        if not self.ws:
            return ""

        try:
            # Send commit message to flush any remaining audio
            message = json.dumps(
                {
                    "message_type": "input_audio_chunk",
                    "audio_base_64": "",
                    "commit": True,
                    "sample_rate": self.sample_rate,
                }
            )
            await self.ws.send(message)

            # Wait briefly for final transcription
            await asyncio.sleep(0.5)

            # Collect any remaining transcriptions
            if self.pending_transcription:
                self.transcription_buffer.append(self.pending_transcription)
                self.pending_transcription = None

            result = " ".join(self.transcription_buffer)
            self.transcription_buffer = []
            return result

        except Exception as e:
            logger.error(f"Error getting final transcription: {e}")
            return ""

    async def _receive_transcripts(self) -> None:
        """Background task to receive transcriptions from WebSocket."""
        while self.streaming and self.ws:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=30.0)
                data = json.loads(message)
                msg_type = data.get("message_type", "")

                if msg_type == "partial_transcript":
                    # Partial transcripts are intermediate results, log but don't use
                    text = data.get("text", "")
                    if text:
                        logger.debug(f"Partial transcript: {text}")

                elif msg_type == "committed_transcript":
                    # Committed transcript is a final result
                    text = data.get("text", "")
                    if text:
                        logger.info(f"Committed transcript: {text}")
                        self.pending_transcription = text
                        if self._transcription_event:
                            self._transcription_event.set()

                elif msg_type == "committed_transcript_with_timestamps":
                    # Committed transcript with word timestamps
                    text = data.get("text", "")
                    if text:
                        logger.info(f"Committed transcript (with timestamps): {text}")
                        self.pending_transcription = text
                        if self._transcription_event:
                            self._transcription_event.set()

                elif msg_type in ("scribe_error", "input_error"):
                    logger.error(f"ElevenLabs STT error: {data}")

                elif msg_type.startswith("scribe_"):
                    # Handle various error types
                    logger.warning(f"ElevenLabs STT message: {data}")

            except asyncio.TimeoutError:
                # No message received, continue waiting
                continue

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error receiving transcript: {e}")
                if not self.streaming:
                    break
                await asyncio.sleep(0.1)
