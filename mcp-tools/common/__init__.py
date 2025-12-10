"""
Common infrastructure for MCP tools.

Zero-cost, shared modules for all MCP tools in the RED project.
"""

__version__ = "1.0.0"

from .config import MCPToolConfig, get_config
from .errors import (
    MCPToolError,
    DocumentLoadError,
    ExtractionError,
    TemplateError
)

__all__ = [
    "MCPToolConfig",
    "get_config",
    "MCPToolError",
    "DocumentLoadError",
    "ExtractionError",
    "TemplateError",
]
