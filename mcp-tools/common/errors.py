"""
Custom exception classes for MCP tools.

Structured errors with actionable suggestions.
"""

from typing import List, Dict, Any, Optional


class MCPToolError(Exception):
    """
    Base exception for all MCP tool errors.

    Provides structured error information with suggestions.
    """

    def __init__(
        self,
        error_type: str,
        message: str,
        suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize MCP tool error.

        Args:
            error_type: Error type identifier (e.g., "file_not_found")
            message: Human-readable error message
            suggestions: List of actionable suggestions
            context: Additional error context
        """
        self.error_type = error_type
        self.message = message
        self.suggestions = suggestions or []
        self.context = context or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for JSON serialization.

        Returns:
            Dict with error details
        """
        return {
            "error": self.error_type,
            "message": self.message,
            "suggestions": self.suggestions,
            "context": self.context
        }

    def __str__(self) -> str:
        """String representation with suggestions"""
        parts = [f"{self.error_type}: {self.message}"]
        if self.suggestions:
            parts.append("\nSuggestions:")
            for suggestion in self.suggestions:
                parts.append(f"  - {suggestion}")
        return "\n".join(parts)


class DocumentLoadError(MCPToolError):
    """Error loading document(s)"""
    pass


class ExtractionError(MCPToolError):
    """Error extracting data from documents"""
    pass


class TemplateError(MCPToolError):
    """Error loading or processing template"""
    pass


class ValidationError(MCPToolError):
    """Input validation error"""
    pass
