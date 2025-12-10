"""
Shared configuration management for MCP tools.

Zero-cost configuration with type safety and validation.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class MCPToolConfig(BaseSettings):
    """
    Shared configuration for all MCP tools.

    Loads from environment variables with sensible defaults.
    All MCP tools should use this instead of hardcoded values.
    """

    # Ollama Configuration
    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint"
    )

    default_model: str = Field(
        default="qwen2.5:3b",
        description="Default LLM model for all tools"
    )

    available_models: List[str] = Field(
        default=["qwen2.5:3b", "qwen2.5:7b", "llama3.1:8b", "mistral:latest"],
        description="Available Ollama models"
    )

    # Timeout Configuration
    default_timeout: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Default timeout in seconds"
    )

    # File Handling
    max_file_size_mb: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum file size in MB"
    )

    max_folder_size_mb: int = Field(
        default=500,
        ge=10,
        le=2000,
        description="Maximum total folder size in MB"
    )

    supported_document_formats: List[str] = Field(
        default=[".txt", ".pdf", ".doc", ".docx"],
        description="Supported document formats"
    )

    # Caching
    enable_cache: bool = Field(
        default=True,
        description="Enable document extraction caching"
    )

    cache_dir: str = Field(
        default=".cache/mcp_tools",
        description="Cache directory path"
    )

    cache_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Cache time-to-live in hours"
    )

    # Output Configuration
    output_dir: str = Field(
        default="uploads",
        description="Output directory for generated files"
    )

    output_cleanup_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Auto-delete outputs after N hours"
    )

    # LLM Extraction
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for extraction"
    )

    llm_top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="LLM top_p for extraction"
    )

    max_extraction_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max retries for LLM extraction"
    )

    # Validation
    @field_validator("ollama_url")
    @classmethod
    def validate_ollama_url(cls, v):
        """Validate Ollama URL format"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("ollama_url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("cache_dir", "output_dir")
    @classmethod
    def validate_paths(cls, v):
        """Ensure paths are relative (security)"""
        if os.path.isabs(v):
            raise ValueError(f"Paths must be relative, not absolute: {v}")
        return v

    model_config = {
        "env_file": ".env",
        "env_prefix": "MCP_",  # Environment variables like MCP_OLLAMA_URL
        "case_sensitive": False
    }


# Singleton instance
_config_instance: Optional[MCPToolConfig] = None


def get_config() -> MCPToolConfig:
    """
    Get or create singleton config instance.

    Returns:
        MCPToolConfig: Shared configuration instance

    Example:
        >>> from common.config import get_config
        >>> config = get_config()
        >>> print(config.ollama_url)
        http://localhost:11434
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = MCPToolConfig()
    return _config_instance
