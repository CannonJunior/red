"""
Source Code Statistics and Tree API.

Walks the RED project directory and returns:
  - Aggregate stats (file count, directory count, total lines, total size)
  - Full hierarchical file tree with per-file line counts

Endpoint: GET /api/source-tree
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Project root — two levels up from server/routes/
_ROOT = Path(__file__).resolve().parent.parent.parent

# Directories to skip entirely
_SKIP_DIRS = {
    ".git", ".venv", "__pycache__", "node_modules",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "outputs", ".claude", "memory",
}

# File extensions treated as text (lines counted)
_TEXT_EXTS = {
    ".py", ".js", ".html", ".css", ".json", ".md",
    ".txt", ".sh", ".yaml", ".yml", ".toml", ".cfg",
    ".ini", ".mojo", ".sql",
}

# Binary / large artefact extensions — tracked for size but not line-counted
_BINARY_EXTS = {
    ".pyc", ".pptx", ".xlsx", ".docx", ".db", ".sqlite",
    ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".mp3", ".mp4", ".wav",
}

# Max tree depth to prevent extremely deep recursion on huge trees
_MAX_DEPTH = 5


def _count_lines(path: Path) -> int:
    """
    Count lines in a text file.

    Args:
        path: File path.

    Returns:
        int: Line count, or 0 on read error.
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _build_tree(path: Path, depth: int = 0) -> List[Dict[str, Any]]:
    """
    Recursively build a serialisable file tree for a directory.

    Args:
        path: Directory to scan.
        depth: Current recursion depth.

    Returns:
        List[Dict]: Child nodes sorted directories-first, then by name.
    """
    if depth > _MAX_DEPTH:
        return []

    items: List[Dict[str, Any]] = []
    try:
        entries = sorted(
            path.iterdir(),
            # Reason: directories first, then alphabetical within each group
            key=lambda e: (e.is_file(), e.name.lower()),
        )
    except PermissionError:
        return items

    for entry in entries:
        # Skip hidden files/dirs except .env.example (useful to show)
        if entry.name.startswith(".") and entry.name != ".env.example":
            continue

        if entry.is_dir():
            if entry.name in _SKIP_DIRS:
                continue
            children = _build_tree(entry, depth + 1)
            # Aggregate line/file counts upward so the UI can show totals
            total_lines = sum(
                (c.get("lines") or 0) + (c.get("total_lines") or 0)
                for c in children
            )
            file_count = sum(
                1 if c["type"] == "file" else c.get("file_count", 0)
                for c in children
            )
            items.append({
                "name":        entry.name,
                "type":        "directory",
                "children":    children,
                "file_count":  file_count,
                "total_lines": total_lines,
            })

        elif entry.is_file():
            if entry.suffix in _BINARY_EXTS:
                continue
            try:
                size = entry.stat().st_size
            except OSError:
                size = 0

            lines = _count_lines(entry) if entry.suffix in _TEXT_EXTS else 0
            items.append({
                "name":      entry.name,
                "type":      "file",
                "extension": entry.suffix.lstrip(".") or "txt",
                "lines":     lines,
                "size":      size,
            })

    return items


def _gather_stats(tree: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Traverse the tree and sum aggregate totals.

    Args:
        tree: Root-level items from _build_tree().

    Returns:
        Dict with keys: files, directories, total_lines, total_size.
    """
    files = dirs = lines = size = 0

    def _walk(items: List[Dict[str, Any]]) -> None:
        nonlocal files, dirs, lines, size
        for item in items:
            if item["type"] == "file":
                files += 1
                lines += item.get("lines", 0)
                size  += item.get("size", 0)
            else:
                dirs += 1
                _walk(item.get("children", []))

    _walk(tree)
    return {
        "files":       files,
        "directories": dirs,
        "total_lines": lines,
        "total_size":  size,
    }


def handle_source_tree_api(handler) -> None:
    """
    Handle GET /api/source-tree — return project statistics and file tree.

    Response JSON:
        {
            "stats": {"files": 142, "directories": 28,
                      "total_lines": 45230, "total_size": 1234567},
            "tree":  [...]
        }
    """
    try:
        tree = _build_tree(_ROOT)
        stats = _gather_stats(tree)
        handler.send_json_response({"stats": stats, "tree": tree})
    except Exception as exc:
        logger.error("source-tree API error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 500)
