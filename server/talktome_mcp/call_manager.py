"""Call manager for handling audio communication sessions."""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .providers import (
    PhoneProvider,
    TTSProvider,
    RealtimeSTTProvider,
    LocalPhoneProvider,
    WhisperSTTProvider,
    PiperTTSProvider
)

logger = logging.getLogger(__name__)


# Default timeout for waiting for user speech (3 minutes)
DEFAULT_TRANSCRIPT_TIMEOUT_MS = 180000


class CallManager:
    """Manages phone/audio calls with TTS and STT integration."""

    def __init__(
        self,
        phone_provider: Optional[PhoneProvider] = None,
        tts_provider: Optional[TTSProvider] = None,
        stt_provider: Optional[RealtimeSTTProvider] = None,
        transcript_timeout_ms: int = DEFAULT_TRANSCRIPT_TIMEOUT_MS
    ):
        """
        Initialize call manager with providers.

        Args:
            phone_provider: Provider for phone/audio I/O
            tts_provider: Text-to-speech provider
            stt_provider: Speech-to-text provider
            transcript_timeout_ms: Timeout for waiting for user speech
        """
        self.phone_provider = phone_provider or LocalPhoneProvider()
        self.tts_provider = tts_provider or PiperTTSProvider()
        self.stt_provider = stt_provider or WhisperSTTProvider()
        self.transcript_timeout_ms = transcript_timeout_ms

        self.active_call_id: Optional[str] = None
        self.call_active = False
        self.call_transcript = []
        self.processing_audio = False
        self._pending_transcription: Optional[str] = None
        self._transcription_event = asyncio.Event()

    async def initiate_call(self, phone_number: str = "local") -> Dict[str, Any]:
        """
        Initiate a new call.

        Args:
            phone_number: Phone number or "local" for local audio

        Returns:
            Call status information
        """
        if self.active_call_id:
            return {
                'success': False,
                'error': 'A call is already active',
                'call_id': self.active_call_id
            }

        try:
            # Start the call
            call_id = await self.phone_provider.make_call(phone_number)
            self.active_call_id = call_id
            self.call_active = True
            self.call_transcript = []

            # Start STT stream
            await self.stt_provider.start_stream()

            # Start processing audio in background
            asyncio.create_task(self._process_incoming_audio())

            logger.info(f"Call initiated: {call_id}")

            return {
                'success': True,
                'call_id': call_id,
                'status': 'Call initiated successfully',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to initiate call: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def speak(self, text: str) -> Dict[str, Any]:
        """
        Synthesize and send text as speech to the call.

        Args:
            text: Text to speak

        Returns:
            Operation status
        """
        if not self.active_call_id:
            return {
                'success': False,
                'error': 'No active call'
            }

        try:
            # Add to transcript
            self.call_transcript.append({
                'role': 'assistant',
                'text': text,
                'timestamp': datetime.now().isoformat()
            })

            # Pause recording to prevent audio feedback/echo
            await self.phone_provider.pause_recording(self.active_call_id)

            # Synthesize speech
            logger.info(f"Synthesizing: {text}")

            # Use streaming if available for lower latency
            if hasattr(self.tts_provider, 'synthesize_stream'):
                async for audio_chunk in self.tts_provider.synthesize_stream(text):
                    await self.phone_provider.send_audio(self.active_call_id, audio_chunk)
                    # Wait for this chunk to finish playing before sending the next one
                    # This prevents chunks from piling up and playing in parallel
                    await self.phone_provider.wait_for_playback_complete(self.active_call_id, timeout=5.0)
            else:
                audio = await self.tts_provider.synthesize(text)
                await self.phone_provider.send_audio(self.active_call_id, audio)
                await self.phone_provider.wait_for_playback_complete(self.active_call_id)

            # Resume recording after speech completes
            await self.phone_provider.resume_recording(self.active_call_id)

            return {
                'success': True,
                'status': 'Speech sent successfully'
            }

        except Exception as e:
            logger.error(f"Failed to speak: {e}")
            # Make sure to resume recording even if there's an error
            await self.phone_provider.resume_recording(self.active_call_id)
            return {
                'success': False,
                'error': str(e)
            }

    async def get_transcript(self) -> Dict[str, Any]:
        """
        Get the current call transcript.

        Returns:
            Transcript data
        """
        return {
            'success': True,
            'transcript': self.call_transcript,
            'call_active': self.call_active,
            'call_id': self.active_call_id
        }

    async def end_call(self) -> Dict[str, Any]:
        """
        End the current call.

        Returns:
            Call summary
        """
        if not self.active_call_id:
            return {
                'success': False,
                'error': 'No active call'
            }

        try:
            # Stop audio processing
            self.call_active = False

            # Get final transcription
            final_text = await self.stt_provider.get_final_transcription()
            if final_text:
                self.call_transcript.append({
                    'role': 'user',
                    'text': final_text,
                    'timestamp': datetime.now().isoformat()
                })

            # Stop STT stream
            await self.stt_provider.stop_stream()

            # Hang up the call
            await self.phone_provider.hang_up(self.active_call_id)

            # Prepare summary
            summary = {
                'success': True,
                'call_id': self.active_call_id,
                'duration': self._calculate_duration(),
                'transcript': self.call_transcript,
                'timestamp': datetime.now().isoformat()
            }

            # Clear state
            self.active_call_id = None
            self.call_transcript = []

            logger.info("Call ended successfully")
            return summary

        except Exception as e:
            logger.error(f"Failed to end call: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _process_incoming_audio(self):
        """Background task to process incoming audio."""
        if not self.active_call_id:
            return

        self.processing_audio = True

        try:
            async for audio_chunk in self.phone_provider.get_audio_stream(self.active_call_id):
                if not self.call_active:
                    break

                # Process through STT
                text = await self.stt_provider.process_audio_chunk(audio_chunk)

                if text:
                    # Add to transcript
                    self.call_transcript.append({
                        'role': 'user',
                        'text': text,
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.info(f"User said: {text}")

                    # Signal that transcription is available
                    self._pending_transcription = text
                    self._transcription_event.set()

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
        finally:
            self.processing_audio = False

    async def listen(self, timeout_ms: Optional[int] = None) -> str:
        """
        Listen for user speech and return the transcription.

        This blocks until the user speaks or timeout is reached.

        Args:
            timeout_ms: Timeout in milliseconds (uses default if not specified)

        Returns:
            Transcribed text from user

        Raises:
            asyncio.TimeoutError: If no speech detected within timeout
        """
        if not self.active_call_id:
            raise RuntimeError("No active call")

        timeout_ms = timeout_ms or self.transcript_timeout_ms
        timeout_sec = timeout_ms / 1000

        # Clear previous event
        self._transcription_event.clear()
        self._pending_transcription = None

        # Wait for transcription or timeout
        try:
            await asyncio.wait_for(
                self._transcription_event.wait(),
                timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            logger.warning(f"Listen timeout after {timeout_ms}ms")
            raise

        # Return the transcribed text
        result = self._pending_transcription or ""
        self._pending_transcription = None
        return result

    async def speak_and_listen(self, text: str, timeout_ms: Optional[int] = None) -> str:
        """
        Speak text and then listen for user response.

        Args:
            text: Text to speak
            timeout_ms: Timeout for waiting for response

        Returns:
            User's transcribed response
        """
        await self.speak(text)
        return await self.listen(timeout_ms)

    def _calculate_duration(self) -> str:
        """Calculate call duration from transcript timestamps."""
        if not self.call_transcript:
            return "0:00"

        try:
            first_time = datetime.fromisoformat(self.call_transcript[0]['timestamp'])
            last_time = datetime.fromisoformat(self.call_transcript[-1]['timestamp'])
            duration = last_time - first_time
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            return f"{minutes}:{seconds:02d}"
        except:
            return "unknown"

    async def cleanup(self):
        """Clean up resources."""
        if self.active_call_id:
            await self.end_call()
        await self.phone_provider.cleanup()