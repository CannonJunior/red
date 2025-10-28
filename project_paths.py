"""
Project Path Utilities - Dynamic path resolution for portability.

This module provides utilities to resolve paths relative to the project root,
making the codebase portable across different installations and users.

Usage:
    from project_paths import get_project_root, resolve_path

    # Get project root
    root = get_project_root()

    # Resolve relative path
    uploads_dir = resolve_path("uploads")
    config_dir = resolve_path("agent-system/config")
"""

import os
from pathlib import Path


def get_project_root() -> Path:
    """
    Get the project root directory dynamically.

    Walks up the directory tree from this file until it finds the project root
    (identified by the presence of pyproject.toml or CLAUDE.md).

    Returns:
        Path: Absolute path to the project root directory
    """
    # Start from this file's directory
    current = Path(__file__).resolve().parent

    # This file should be at the project root, so just return its parent
    # But verify by checking for project markers
    if (current / "pyproject.toml").exists() or (current / "CLAUDE.md").exists():
        return current

    # Fallback: walk up to find markers
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / "CLAUDE.md").exists():
            return current
        current = current.parent

    # If nothing found, return this file's parent directory
    return Path(__file__).resolve().parent


def resolve_path(relative_path: str) -> str:
    """
    Resolve a path relative to the project root.

    Args:
        relative_path: Path relative to project root (e.g., "uploads", "chromadb_data")

    Returns:
        str: Absolute path as string
    """
    root = get_project_root()
    return str(root / relative_path)


def expand_path_variables(path: str) -> str:
    """
    Expand path variables in configuration strings.

    Supports:
    - ${PROJECT_ROOT} - expands to project root directory
    - ${HOME} - expands to user home directory
    - Environment variables via ${VAR_NAME}

    Args:
        path: Path string that may contain variables

    Returns:
        str: Path with variables expanded
    """
    if "${PROJECT_ROOT}" in path:
        path = path.replace("${PROJECT_ROOT}", str(get_project_root()))

    if "${HOME}" in path:
        path = path.replace("${HOME}", str(Path.home()))

    # Expand other environment variables
    path = os.path.expandvars(path)

    return path


# Cache the project root for performance
_PROJECT_ROOT = None


def get_cached_project_root() -> Path:
    """Get cached project root for better performance."""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = get_project_root()
    return _PROJECT_ROOT


# Convenience constant for quick access
PROJECT_ROOT = get_project_root()
