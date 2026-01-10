#!/usr/bin/env python3
"""TalkToMe MCP Server - Local audio communication for Claude."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from mcp import Tool

from .call_manager import CallManager
from .providers import (
    LocalPhoneProvider,
    WhisperSTTProvider,
    PiperTTSProvider
)

# Load environment variables from .env and .env.local
load_dotenv()
# Try to load .env.local from the current directory
env_local_path = Path('.env.local').resolve()
if env_local_path.exists():
    load_dotenv(str(env_local_path), override=True)
    logger.info(f"Loaded .env.local from {env_local_path}")

# Configure logging (stderr only for stdio-based MCP)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]  # IMPORTANT: Use stderr for logging
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("talktome")

# Global call manager instance
call_manager: Optional[CallManager] = None


def init_call_manager():
    """Initialize the call manager with configured providers."""
    global call_manager

    # Get provider configuration from environment
    tts_provider_name = os.getenv('TALKTOME_TTS_PROVIDER', 'piper')
    stt_provider_name = os.getenv('TALKTOME_STT_PROVIDER', 'whisper')

    # Initialize providers based on configuration
    phone_provider = LocalPhoneProvider()

    # TTS Provider
    if tts_provider_name == 'piper':
        # Get TTS configuration
        tts_config = {}
        speed_str = os.getenv('TALKTOME_PIPER_SPEED')
        if speed_str:
            try:
                tts_config['length_scale'] = float(speed_str)
                logger.info(f"Piper TTS speed set to {speed_str}")
            except ValueError:
                logger.warning(f"Invalid TALKTOME_PIPER_SPEED value: {speed_str}, using default")

        tts_provider = PiperTTSProvider(config=tts_config)
    else:
        # Default to Piper if unknown
        logger.warning(f"Unknown TTS provider: {tts_provider_name}, using Piper")
        tts_provider = PiperTTSProvider()

    # STT Provider
    if stt_provider_name == 'whisper':
        stt_provider = WhisperSTTProvider()
    else:
        # Default to Whisper if unknown
        logger.warning(f"Unknown STT provider: {stt_provider_name}, using Whisper")
        stt_provider = WhisperSTTProvider()

    # Create call manager
    call_manager = CallManager(
        phone_provider=phone_provider,
        tts_provider=tts_provider,
        stt_provider=stt_provider
    )

    logger.info("Call manager initialized successfully")


# Initialize on startup
init_call_manager()


# Tool definitions
@mcp.tool(
    name="initiate_call",
    description="Start a local audio communication session using the computer's microphone and speakers. IMPORTANT: Once a call is active, ALL communication with the user must go through voice tools (continue_call, speak, report_completion). Do NOT provide text-only responses during an active call - the user won't see them."
)
async def initiate_call(message: str = "") -> Dict[str, Any]:
    """
    Start a local audio session for voice communication.

    Args:
        message: Optional initial message to speak to the user

    Returns:
        Dict with success status, call details, and user's response if message was provided
    """
    if not call_manager:
        return {
            'success': False,
            'error': 'Call manager not initialized'
        }

    # Initiate the call
    result = await call_manager.initiate_call("local")

    if not result.get('success'):
        return result

    call_id = result.get('call_id')

    # If message provided, speak and wait for response
    if message and call_id:
        try:
            user_response = await call_manager.speak_and_listen(message)
            return {
                'success': True,
                'call_id': call_id,
                'status': 'Call initiated successfully',
                'user_response': user_response,
                'timestamp': result.get('timestamp')
            }
        except asyncio.TimeoutError:
            await call_manager.end_call()
            return {
                'success': False,
                'error': 'Timeout waiting for user response',
                'call_id': call_id
            }

    return result


@mcp.tool(
    name="continue_call",
    description="Continue an active call with a follow-up message. Waits for and returns the user's response."
)
async def continue_call(message: str) -> Dict[str, Any]:
    """
    Continue an active call with a follow-up message.

    Args:
        message: Your follow-up message to speak

    Returns:
        Dict with success status and user's response
    """
    if not call_manager:
        return {
            'success': False,
            'error': 'Call manager not initialized'
        }

    if not call_manager.active_call_id:
        return {
            'success': False,
            'error': 'No active call'
        }

    if not message:
        return {
            'success': False,
            'error': 'Message parameter is required'
        }

    try:
        user_response = await call_manager.speak_and_listen(message)
        return {
            'success': True,
            'user_response': user_response,
            'call_id': call_manager.active_call_id
        }
    except asyncio.TimeoutError:
        return {
            'success': False,
            'error': 'Timeout waiting for user response',
            'call_id': call_manager.active_call_id
        }


@mcp.tool(
    name="speak",
    description="Convert text to speech and play it through the speakers without waiting for a response. Use this to acknowledge requests or provide status updates before starting time-consuming operations."
)
async def speak(text: str) -> Dict[str, Any]:
    """
    Speak text through the active audio session without waiting for response.

    Args:
        text: Text to speak

    Returns:
        Dict with success status
    """
    if not call_manager:
        return {
            'success': False,
            'error': 'Call manager not initialized'
        }

    if not text:
        return {
            'success': False,
            'error': 'Text parameter is required'
        }

    result = await call_manager.speak(text)
    return result


@mcp.tool(
    name="report_completion",
    description="CRITICAL: After completing ANY work during an active call (git push, file edits, etc.), you MUST use this tool to report completion via voice. Do NOT provide text-only summaries - the user is listening, not reading. This speaks your message and waits for their next instruction."
)
async def report_completion(message: str) -> Dict[str, Any]:
    """
    Report task completion and wait for next user instruction.

    This tool combines speaking a completion message with listening for
    the user's next request. Use this after completing work during an
    active call to maintain voice conversation flow.

    Args:
        message: Completion message to speak (e.g., "Done! I've pushed the commits.")

    Returns:
        Dict with success status and user's next response
    """
    if not call_manager:
        return {
            'success': False,
            'error': 'Call manager not initialized'
        }

    if not call_manager.active_call_id:
        return {
            'success': False,
            'error': 'No active call'
        }

    if not message:
        return {
            'success': False,
            'error': 'Message parameter is required'
        }

    try:
        user_response = await call_manager.speak_and_listen(message)
        return {
            'success': True,
            'user_response': user_response,
            'call_id': call_manager.active_call_id
        }
    except asyncio.TimeoutError:
        return {
            'success': False,
            'error': 'Timeout waiting for user response',
            'call_id': call_manager.active_call_id
        }


@mcp.tool(
    name="get_transcript",
    description="Get the transcript of the current or last audio session"
)
async def get_transcript() -> Dict[str, Any]:
    """
    Get the conversation transcript.

    Returns:
        Dict with transcript data
    """
    if not call_manager:
        return {
            'success': False,
            'error': 'Call manager not initialized'
        }

    result = await call_manager.get_transcript()
    return result


@mcp.tool(
    name="end_call",
    description="End the current audio communication session"
)
async def end_call() -> Dict[str, Any]:
    """
    End the active audio session.

    Returns:
        Dict with call summary
    """
    if not call_manager:
        return {
            'success': False,
            'error': 'Call manager not initialized'
        }

    result = await call_manager.end_call()
    return result


@mcp.tool(
    name="test_audio",
    description="Test the audio system setup (microphone, speakers, TTS, STT)"
)
async def test_audio() -> Dict[str, Any]:
    """
    Test audio system components.

    Returns:
        Dict with test results
    """
    results = {
        'microphone': False,
        'speakers': False,
        'tts': False,
        'stt': False
    }

    try:
        # Test microphone
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        results['microphone'] = len(input_devices) > 0

        # Test speakers
        output_devices = [d for d in devices if d['max_output_channels'] > 0]
        results['speakers'] = len(output_devices) > 0

        # Test TTS
        if call_manager and call_manager.tts_provider:
            test_audio = await call_manager.tts_provider.synthesize("Test")
            results['tts'] = len(test_audio) > 0

        # Test STT (check if model loads)
        if call_manager and call_manager.stt_provider:
            results['stt'] = hasattr(call_manager.stt_provider, 'model')

    except Exception as e:
        logger.error(f"Audio test error: {e}")

    return {
        'success': all(results.values()),
        'results': results
    }


async def cleanup():
    """Clean up resources on shutdown."""
    if call_manager:
        await call_manager.cleanup()
    logger.info("Server shutdown complete")


def main():
    """Main entry point for the MCP server."""
    logger.info("Starting TalkToMe MCP Server v2.0.0")

    # Print initialization message to stderr
    print("TalkToMe Local Audio Communication", file=sys.stderr)
    print("================================", file=sys.stderr)
    print("Ready for voice communication!", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        # Run the MCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        # Clean up
        asyncio.run(cleanup())


if __name__ == "__main__":
    main()