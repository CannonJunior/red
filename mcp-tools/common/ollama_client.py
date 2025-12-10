"""
Type-safe Ollama API client for MCP tools.

Wrapper around Ollama API with proper error handling.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .config import get_config
from .errors import ExtractionError


class OllamaClient:
    """
    Type-safe Ollama API client.

    Provides consistent interface for LLM calls across all MCP tools.
    """

    def __init__(self, config=None):
        """
        Initialize Ollama client.

        Args:
            config: MCPToolConfig instance (uses default if None)
        """
        self.config = config or get_config()
        self.ollama_url = self.config.ollama_url

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        format: Optional[str] = None
    ) -> str:
        """
        Generate text using Ollama.

        Args:
            prompt: Input prompt
            model: Model name (uses default if None)
            timeout: Timeout in seconds (uses default if None)
            temperature: Temperature (uses config default if None)
            top_p: Top-p sampling (uses config default if None)
            format: Output format ("json" for JSON mode)

        Returns:
            Generated text

        Raises:
            ExtractionError: If API call fails
        """
        model = model or self.config.default_model
        timeout = timeout or self.config.default_timeout
        temperature = temperature if temperature is not None else self.config.llm_temperature
        top_p = top_p if top_p is not None else self.config.llm_top_p

        # Build request
        request_data = {
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'top_p': top_p
            }
        }

        if format:
            request_data['format'] = format

        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=json.dumps(request_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )

            # Make request with timeout
            response = urllib.request.urlopen(req, timeout=timeout)
            result = json.loads(response.read().decode('utf-8'))

            return result.get('response', '')

        except urllib.error.URLError as e:
            raise ExtractionError(
                error_type="ollama_connection_failed",
                message=f"Failed to connect to Ollama: {e.reason}",
                suggestions=[
                    "Check if Ollama is running: ollama serve",
                    f"Verify Ollama URL: {self.ollama_url}",
                    "Check network connectivity"
                ]
            )

        except urllib.error.HTTPError as e:
            raise ExtractionError(
                error_type="ollama_http_error",
                message=f"Ollama HTTP error {e.code}: {e.reason}",
                suggestions=[
                    f"Check if model exists: ollama list | grep {model}",
                    f"Pull model if needed: ollama pull {model}"
                ]
            )

        except TimeoutError:
            raise ExtractionError(
                error_type="ollama_timeout",
                message=f"Ollama request timed out after {timeout}s",
                suggestions=[
                    "Increase timeout value",
                    "Use a smaller/faster model",
                    "Reduce prompt size"
                ]
            )

        except json.JSONDecodeError as e:
            raise ExtractionError(
                error_type="ollama_invalid_response",
                message=f"Invalid JSON response from Ollama: {str(e)}",
                suggestions=[
                    "Check Ollama server logs",
                    "Try restarting Ollama"
                ]
            )

        except Exception as e:
            raise ExtractionError(
                error_type="ollama_unknown_error",
                message=f"Unexpected error calling Ollama: {str(e)}",
                suggestions=[
                    "Check server.py logs for details",
                    "Verify Ollama is working: ollama run " + model
                ]
            )

    async def check_health(self) -> bool:
        """
        Check if Ollama is reachable.

        Returns:
            True if Ollama is healthy, False otherwise
        """
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            response = urllib.request.urlopen(req, timeout=5)
            return response.status == 200
        except Exception:
            return False

    async def list_models(self) -> list:
        """
        List available Ollama models.

        Returns:
            List of model names
        """
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            return [model['name'] for model in data.get('models', [])]
        except Exception:
            return []
