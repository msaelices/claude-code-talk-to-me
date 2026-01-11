"""Utility functions for TalkToMe MCP."""

import re
from typing import Any, Dict, Optional


def success_response(data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Create a standardized success response.

    Args:
        data: Optional dict of additional data to include
        **kwargs: Additional key-value pairs to include

    Returns:
        Dict with success=True and any additional data
    """
    result = {"success": True}
    if data:
        result.update(data)
    result.update(kwargs)
    return result


def error_response(error: str, **kwargs) -> Dict[str, Any]:
    """Create a standardized error response.

    Args:
        error: Error message
        **kwargs: Additional key-value pairs (e.g., call_id)

    Returns:
        Dict with success=False and error message
    """
    result = {"success": False, "error": error}
    result.update(kwargs)
    return result


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences for streaming synthesis.

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    sentences = re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", text)
    return [s.strip() for s in sentences if s.strip()]
