#!/usr/bin/env python3
"""
Request Validation Middleware
Provides Pydantic-based validation for all API endpoints with security and type safety.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from functools import wraps
import json
from debug_logger import debug_log, error_log


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ChatRequest(BaseModel):
    """Validation schema for /api/chat endpoint."""

    model_config = ConfigDict(extra='forbid')  # Reject unknown fields

    message: str = Field(..., min_length=1, max_length=10000, description="Chat message")
    model: Optional[str] = Field(default='qwen2.5:3b', max_length=100, description="LLM model name")
    workspace: Optional[str] = Field(default='default', max_length=100, description="Workspace identifier")
    knowledge_mode: Optional[Literal['none', 'rag', 'cag']] = Field(default='none', description="Knowledge retrieval mode")
    mcp_tool_call: Optional[Dict[str, Any]] = Field(default=None, description="MCP tool call data")

    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """Remove leading/trailing whitespace and validate non-empty."""
        v = v.strip()
        if not v:
            raise ValueError('Message cannot be empty or whitespace only')
        return v

    @field_validator('model')
    @classmethod
    def validate_model_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate model name format."""
        if v and ('/' in v or '\\' in v or '..' in v):
            raise ValueError('Invalid model name format')
        return v


class RAGQueryRequest(BaseModel):
    """Validation schema for /api/rag/query endpoint."""

    model_config = ConfigDict(extra='forbid')

    query: str = Field(..., min_length=1, max_length=5000, description="Search query")
    max_context: int = Field(default=5, ge=1, le=50, description="Maximum context results")

    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize query string."""
        return v.strip()


class RAGSearchRequest(BaseModel):
    """Validation schema for /api/rag/search endpoint."""

    model_config = ConfigDict(extra='forbid')

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    max_results: int = Field(default=5, ge=1, le=100, description="Maximum results")

    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize query string."""
        return v.strip()


class RAGIngestRequest(BaseModel):
    """Validation schema for /api/rag/ingest endpoint (JSON file path, not multipart)."""

    model_config = ConfigDict(extra='forbid')

    file_path: str = Field(..., min_length=1, max_length=1000, description="Path to document file")

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path is not empty and doesn't contain path traversal."""
        v = v.strip()
        if not v:
            raise ValueError('File path cannot be empty')
        if '..' in v or v.startswith('/etc/') or v.startswith('/root/'):
            raise ValueError('Invalid file path')
        return v


class CAGQueryRequest(BaseModel):
    """Validation schema for /api/cag/query endpoint."""

    model_config = ConfigDict(extra='forbid')

    query: str = Field(..., min_length=1, max_length=5000, description="Query text")
    model: Optional[str] = Field(default='qwen2.5:3b', max_length=100, description="LLM model name")

    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize query string."""
        return v.strip()


class CAGLoadRequest(BaseModel):
    """Validation schema for /api/cag/load endpoint (JSON file path, not multipart)."""

    model_config = ConfigDict(extra='forbid')

    file_path: str = Field(..., min_length=1, max_length=1000, description="Path to document file")

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path is not empty and doesn't contain path traversal."""
        v = v.strip()
        if not v:
            raise ValueError('File path cannot be empty')
        if '..' in v or v.startswith('/etc/') or v.startswith('/root/'):
            raise ValueError('Invalid file path')
        return v


class SearchRequest(BaseModel):
    """Validation schema for /api/search endpoint."""

    model_config = ConfigDict(extra='forbid')

    query: str = Field(..., min_length=0, max_length=1000, description="Search query")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")
    page_size: int = Field(default=50, ge=1, le=500, description="Results per page")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class SearchCreateFolderRequest(BaseModel):
    """Validation schema for creating folders."""

    model_config = ConfigDict(extra='forbid')

    name: str = Field(..., min_length=1, max_length=255, description="Folder name")
    parent_id: Optional[str] = Field(default=None, max_length=100, description="Parent folder ID")
    color: Optional[str] = Field(default=None, max_length=20, description="Folder color")

    @field_validator('name')
    @classmethod
    def validate_folder_name(cls, v: str) -> str:
        """Validate folder name doesn't contain path separators."""
        if '/' in v or '\\' in v:
            raise ValueError('Folder name cannot contain path separators')
        return v.strip()


class SearchAddObjectRequest(BaseModel):
    """Validation schema for adding searchable objects."""

    model_config = ConfigDict(extra='forbid')

    type: Literal['chat', 'knowledge_base', 'document', 'note'] = Field(..., description="Object type")
    title: str = Field(..., min_length=1, max_length=500, description="Object title")
    content: str = Field(..., min_length=0, max_length=1000000, description="Object content")
    folder_id: Optional[str] = Field(default=None, max_length=100, description="Folder ID")
    tags: Optional[List[str]] = Field(default=None, description="Tags list")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    author: Optional[str] = Field(default=None, max_length=100, description="Author name")


class MCPToolExecuteRequest(BaseModel):
    """Validation schema for MCP tool execution."""

    model_config = ConfigDict(extra='allow')  # Allow extra fields for tool inputs

    server_name: str = Field(..., min_length=1, max_length=100, description="MCP server name")
    tool_name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Tool inputs")


# ============================================================================
# VALIDATION DECORATOR
# ============================================================================

def validate_request(schema_class: type[BaseModel]):
    """
    Decorator to validate request body against a Pydantic schema.

    Usage:
        @validate_request(ChatRequest)
        def handle_chat_api(self):
            # Access validated data via self.validated_data
            message = self.validated_data.message
            ...

    Args:
        schema_class: Pydantic BaseModel class for validation

    Returns:
        Decorated function with automatic request validation
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                # Read request body
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    # Allow empty body for GET-like endpoints
                    post_data = b'{}'
                else:
                    post_data = self.rfile.read(content_length)

                # Parse JSON
                try:
                    data = json.loads(post_data.decode('utf-8'))
                except json.JSONDecodeError as e:
                    error_log(f"Invalid JSON in request: {e}")
                    self.send_json_response({
                        'status': 'error',
                        'message': 'Invalid JSON format',
                        'details': str(e)
                    }, 400)
                    return

                # Validate with Pydantic
                try:
                    validated = schema_class(**data)
                    debug_log(f"Request validated successfully for {func.__name__}", "✅")
                except Exception as e:
                    error_log(f"Validation failed for {func.__name__}: {e}")

                    # Extract validation errors
                    if hasattr(e, 'errors'):
                        errors = e.errors()
                        error_details = [
                            {
                                'field': '.'.join(str(loc) for loc in err['loc']),
                                'message': err['msg'],
                                'type': err['type']
                            }
                            for err in errors
                        ]
                    else:
                        error_details = [{'message': str(e)}]

                    self.send_json_response({
                        'status': 'error',
                        'message': 'Request validation failed',
                        'errors': error_details
                    }, 400)
                    return

                # Add validated data to request context
                self.validated_data = validated

                # Call the original function
                return func(self, *args, **kwargs)

            except Exception as e:
                error_log(f"Unexpected error in validation middleware: {e}")
                self.send_json_response({
                    'status': 'error',
                    'message': 'Internal server error during validation'
                }, 500)
                return

        return wrapper
    return decorator


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent injection attacks.

    Args:
        value: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    # Remove null bytes
    value = value.replace('\x00', '')

    # Trim to max length
    if len(value) > max_length:
        value = value[:max_length]

    # Strip whitespace
    value = value.strip()

    return value


def validate_id_format(value: str) -> bool:
    """
    Validate ID format to prevent path traversal.

    Args:
        value: ID string to validate

    Returns:
        True if valid, False otherwise
    """
    # Disallow path separators and parent directory references
    if any(char in value for char in ['/', '\\', '..', '\x00']):
        return False

    # Disallow excessively long IDs
    if len(value) > 100:
        return False

    return True


# ============================================================================
# SCHEMA REGISTRY
# ============================================================================

SCHEMA_REGISTRY = {
    'chat': ChatRequest,
    'rag_query': RAGQueryRequest,
    'rag_search': RAGSearchRequest,
    'rag_ingest': RAGIngestRequest,
    'cag_query': CAGQueryRequest,
    'cag_load': CAGLoadRequest,
    'search': SearchRequest,
    'search_create_folder': SearchCreateFolderRequest,
    'search_add_object': SearchAddObjectRequest,
    'mcp_tool_execute': MCPToolExecuteRequest,
}


def get_schema(name: str) -> Optional[type[BaseModel]]:
    """
    Get validation schema by name.

    Args:
        name: Schema name

    Returns:
        Pydantic schema class or None
    """
    return SCHEMA_REGISTRY.get(name)
