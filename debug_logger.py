"""
Debug logging utility for the RED project.

Provides conditional logging based on DEBUG_MODE environment variable.
This allows production deployments to have clean logs while enabling
detailed debug output during development.
"""

import os
from datetime import datetime
from typing import Optional


# Read DEBUG_MODE from environment variable
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')


def debug_log(message: str, emoji: str = "🔍") -> None:
    """
    Log a debug message only if DEBUG_MODE is enabled.

    Args:
        message: The message to log
        emoji: Optional emoji prefix (default: 🔍)

    Usage:
        debug_log("Processing request data")
        debug_log("MCP Tool call: review_whitepaper", "🔧")
    """
    if DEBUG_MODE:
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"{emoji} [{timestamp}] {message}")


def info_log(message: str, emoji: str = "ℹ️") -> None:
    """
    Log an informational message (always shown).

    Args:
        message: The message to log
        emoji: Optional emoji prefix (default: ℹ️)

    Usage:
        info_log("Server started on port 9090")
        info_log("RAG query completed", "✅")
    """
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"{emoji} [{timestamp}] {message}")


def error_log(message: str, emoji: str = "❌", exception: Optional[Exception] = None) -> None:
    """
    Log an error message (always shown).

    Args:
        message: The error message to log
        emoji: Optional emoji prefix (default: ❌)
        exception: Optional exception object to include traceback

    Usage:
        error_log("Failed to connect to database")
        error_log("RAG query failed", exception=e)
    """
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"{emoji} [{timestamp}] {message}")

    if exception and DEBUG_MODE:
        import traceback
        print(f"   Exception details: {type(exception).__name__}: {str(exception)}")
        traceback.print_exc()


def success_log(message: str, emoji: str = "✅") -> None:
    """
    Log a success message (always shown).

    Args:
        message: The success message to log
        emoji: Optional emoji prefix (default: ✅)

    Usage:
        success_log("Document uploaded successfully")
        success_log("Server started on port 9090", "🚀")
    """
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"{emoji} [{timestamp}] {message}")


def warning_log(message: str, emoji: str = "⚠️") -> None:
    """
    Log a warning message (always shown).

    Args:
        message: The warning message to log
        emoji: Optional emoji prefix (default: ⚠️)

    Usage:
        warning_log("Using fallback configuration")
        warning_log("Rate limit approaching")
    """
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"{emoji} [{timestamp}] {message}")


def set_debug_mode(enabled: bool) -> None:
    """
    Programmatically enable or disable debug mode.

    Args:
        enabled: Whether to enable debug mode

    Usage:
        set_debug_mode(True)  # Enable debug logging
        set_debug_mode(False) # Disable debug logging
    """
    global DEBUG_MODE
    DEBUG_MODE = enabled


def is_debug_enabled() -> bool:
    """
    Check if debug mode is currently enabled.

    Returns:
        True if debug mode is enabled, False otherwise

    Usage:
        if is_debug_enabled():
            # Perform expensive debug operation
            pass
    """
    return DEBUG_MODE
