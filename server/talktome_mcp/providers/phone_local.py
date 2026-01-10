"""Local audio phone provider using system audio."""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict
import sounddevice as sd
import numpy as np
from queue import Queue
import threading

from .base import PhoneProvider, Call

logger = logging.getLogger(__name__)


class LocalCall(Call):
    """Represents a local audio call session."""

    def __init__(self, call_id: str, sample_rate: int = 16000, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        super().__init__(call_id)
        self.sample_rate = sample_rate
        self.audio_queue = asyncio.Queue()
        self.recording = True
        self.playback_queue = Queue()
        self.record_thread: Optional[threading.Thread] = None
        self.playback_thread: Optional[threading.Thread] = None
        self.event_loop = event_loop or asyncio.get_event_loop()

    def start_recording(self):
        """Start recording audio from microphone."""
        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"Recording status: {status}")
            if self.recording:
                # Convert to bytes and put in async queue
                audio_bytes = (indata * 32767).astype(np.int16).tobytes()
                asyncio.run_coroutine_threadsafe(
                    self.audio_queue.put(audio_bytes),
                    self.event_loop
                )

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=callback,
            dtype='float32',
            blocksize=int(self.sample_rate * 0.1)  # 100ms chunks
        )
        self.stream.start()

    def pause_recording(self):
        """Pause recording to prevent audio feedback."""
        self.recording = False

    def resume_recording(self):
        """Resume recording after audio playback completes."""
        self.recording = True

    def stop_recording(self):
        """Stop recording audio."""
        self.recording = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()

    def start_playback(self):
        """Start playback thread for audio output."""
        def playback_worker():
            logger.info(f"[{self.call_id}] Playback thread started")
            with sd.OutputStream(
                samplerate=22050,  # Piper TTS outputs at 22050Hz
                channels=1,
                dtype='int16'
            ) as stream:
                while self.active:
                    try:
                        audio = self.playback_queue.get(timeout=0.1)
                        if audio is None:
                            logger.info(f"[{self.call_id}] Playback thread received None, stopping")
                            break
                        # Convert bytes to numpy array
                        samples = np.frombuffer(audio, dtype=np.int16)
                        stream.write(samples)
                    except:
                        continue
            logger.info(f"[{self.call_id}] Playback thread ended")

        self.playback_thread = threading.Thread(target=playback_worker, daemon=True)
        self.playback_thread.start()

    async def play_audio(self, audio: bytes):
        """Queue audio for playback."""
        self.playback_queue.put(audio)

    async def end(self):
        """End the local call."""
        self.stop_recording()
        self.active = False
        if self.playback_thread:
            self.playback_queue.put(None)
            self.playback_thread.join()
        await super().end()


class LocalPhoneProvider(PhoneProvider):
    """Local audio provider using system microphone and speakers."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.calls: Dict[str, LocalCall] = {}
        self.call_counter = 0

    async def make_call(self, phone_number: str) -> str:
        """
        Start a local audio session.

        Args:
            phone_number: Ignored for local provider

        Returns:
            Call ID for the session
        """
        # Clean up any existing calls first to prevent accumulation
        await self.cleanup()

        self.call_counter += 1
        call_id = f"local-{self.call_counter}"

        logger.info(f"Starting local audio session: {call_id}")

        # Get current event loop for use in audio callback thread
        loop = asyncio.get_event_loop()
        call = LocalCall(call_id, event_loop=loop)
        self.calls[call_id] = call

        # Start recording and playback
        call.start_recording()
        call.start_playback()

        return call_id

    async def hang_up(self, call_id: str) -> None:
        """End the audio session."""
        if call_id in self.calls:
            logger.info(f"Ending local audio session: {call_id}")
            call = self.calls[call_id]
            await call.end()
            del self.calls[call_id]

    async def send_audio(self, call_id: str, audio: bytes) -> None:
        """Send audio to speakers."""
        if call_id in self.calls:
            call = self.calls[call_id]
            await call.play_audio(audio)

    async def pause_recording(self, call_id: str) -> None:
        """Pause recording to prevent audio feedback during TTS playback."""
        if call_id in self.calls:
            self.calls[call_id].pause_recording()

    async def resume_recording(self, call_id: str) -> None:
        """Resume recording after TTS playback completes."""
        if call_id in self.calls:
            self.calls[call_id].resume_recording()

    async def get_audio_stream(self, call_id: str) -> AsyncGenerator[bytes, None]:
        """Get audio stream from microphone."""
        if call_id not in self.calls:
            return

        call = self.calls[call_id]

        while call.active:
            try:
                # Get audio chunk with timeout
                audio = await asyncio.wait_for(
                    call.audio_queue.get(),
                    timeout=0.1
                )
                yield audio
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in audio stream: {e}")
                break

    async def is_call_active(self, call_id: str) -> bool:
        """Check if the audio session is active."""
        return call_id in self.calls and self.calls[call_id].active

    async def cleanup(self) -> None:
        """Clean up all active calls."""
        for call_id in list(self.calls.keys()):
            await self.hang_up(call_id)