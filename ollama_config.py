"""
Centralized Ollama configuration and connection management.

This module provides robust Ollama connection handling with:
- Environment variable support for different deployment scenarios
- Connection timeout and retry mechanisms
- Consistent error handling across the application
- Health checks and connection validation
- HTTP connection pooling for improved performance
"""

import os
import json
import time
import logging
import urllib.request
import urllib.error
import socket
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

# Import connection pool for performance
from connection_pool import get_http_pool

# Configure logging
logger = logging.getLogger(__name__)

class OllamaConfig:
    """Centralized Ollama configuration and connection management."""
    
    def __init__(self):
        """Initialize Ollama configuration with environment variables and fallbacks."""
        # Configuration from environment variables with sensible defaults
        self.host = os.getenv('OLLAMA_HOST', 'localhost')
        self.port = int(os.getenv('OLLAMA_PORT', '11434'))
        self.base_url = os.getenv('OLLAMA_BASE_URL', f'http://{self.host}:{self.port}')

        # Connection settings
        self.timeout = float(os.getenv('OLLAMA_TIMEOUT', '30.0'))
        self.connect_timeout = float(os.getenv('OLLAMA_CONNECT_TIMEOUT', '10.0'))
        self.max_retries = int(os.getenv('OLLAMA_MAX_RETRIES', '3'))
        self.retry_delay = float(os.getenv('OLLAMA_RETRY_DELAY', '1.0'))

        # API endpoints
        self.generate_endpoint = urljoin(self.base_url, '/api/generate')
        self.tags_endpoint = urljoin(self.base_url, '/api/tags')
        self.chat_endpoint = urljoin(self.base_url, '/api/chat')

        # HTTP connection pool for improved performance
        self.http_pool = get_http_pool()

        logger.info(f"Ollama configuration initialized: {self.base_url} (timeout: {self.timeout}s) with connection pooling")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama server with comprehensive diagnostics."""
        result = {
            'connected': False,
            'base_url': self.base_url,
            'host': self.host,
            'port': self.port,
            'error': None,
            'response_time': None,
            'models_available': False,
            'models': []
        }
        
        start_time = time.time()
        
        try:
            # Test basic socket connection first
            logger.debug(f"Testing socket connection to {self.host}:{self.port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.connect_timeout)
            
            try:
                sock_result = sock.connect_ex((self.host, self.port))
                if sock_result != 0:
                    result['error'] = f"Socket connection failed: Cannot connect to {self.host}:{self.port}"
                    return result
            finally:
                sock.close()
            
            # Test HTTP connection
            logger.debug(f"Testing HTTP connection to {self.tags_endpoint}")
            req = urllib.request.Request(self.tags_endpoint)
            req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_time = time.time() - start_time
                result['response_time'] = round(response_time, 3)
                
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    models = data.get('models', [])
                    
                    result.update({
                        'connected': True,
                        'models_available': len(models) > 0,
                        'models': [model['name'] for model in models]
                    })
                    
                    logger.info(f"Ollama connection successful ({response_time:.3f}s) - {len(models)} models available")
                else:
                    result['error'] = f"HTTP {response.status}: {response.reason}"
                    
        except socket.timeout:
            result['error'] = f"Connection timeout after {self.connect_timeout}s"
        except socket.gaierror as e:
            result['error'] = f"DNS resolution failed: {e}"
        except urllib.error.URLError as e:
            if hasattr(e, 'reason'):
                result['error'] = f"URL error: {e.reason}"
            else:
                result['error'] = f"URL error: {e}"
        except Exception as e:
            result['error'] = f"Connection test failed: {e}"
            logger.exception("Ollama connection test failed")
        
        return result
    
    def make_request(self, endpoint: str, data: Dict[str, Any], method: str = 'POST') -> Dict[str, Any]:
        """Make a robust HTTP request to Ollama with retries and error handling using connection pool."""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Ollama request attempt {attempt + 1}/{self.max_retries} to {endpoint}")

                # Prepare request
                json_data = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(endpoint, data=json_data)
                req.add_header('Content-Type', 'application/json')
                req.get_method = lambda: method

                # Make request using connection pool for better performance
                with self.http_pool.get_connection() as opener:
                    response = opener.open(req, timeout=self.timeout)

                    if response.getcode() == 200:
                        raw_response = response.read().decode('utf-8')

                        # Handle multiple JSON objects or streaming responses
                        try:
                            # Try parsing as single JSON object first
                            result = json.loads(raw_response)
                        except json.JSONDecodeError:
                            # Handle streaming responses (multiple JSON objects)
                            lines = raw_response.strip().split('\n')
                            result = None
                            accumulated_content = ""

                            for line in lines:
                                if line.strip():
                                    try:
                                        parsed_line = json.loads(line)
                                        if parsed_line:
                                            # For chat responses, accumulate content from streaming
                                            if 'message' in parsed_line and 'content' in parsed_line['message']:
                                                content = parsed_line['message']['content']
                                                if content:  # Only accumulate non-empty content
                                                    accumulated_content += content

                                            # Keep updating result with latest response
                                            result = parsed_line
                                    except json.JSONDecodeError:
                                        continue

                            # If we accumulated content, update the final result
                            if result and accumulated_content and 'message' in result:
                                result['message']['content'] = accumulated_content

                            if result is None:
                                raise json.JSONDecodeError("No valid JSON found in response", raw_response, 0)

                        logger.debug(f"Ollama request successful on attempt {attempt + 1}")
                        return {
                            'success': True,
                            'data': result,
                            'attempt': attempt + 1,
                            'error': None
                        }
                    else:
                        last_error = f"HTTP {response.getcode()}"
                        
            except socket.timeout:
                last_error = f"Request timeout after {self.timeout}s"
                logger.warning(f"Ollama request timeout on attempt {attempt + 1}")
            except urllib.error.URLError as e:
                last_error = f"Connection error: {e.reason if hasattr(e, 'reason') else str(e)}"
                logger.warning(f"Ollama connection error on attempt {attempt + 1}: {last_error}")
            except json.JSONDecodeError as e:
                last_error = f"Invalid JSON response: {e}"
                logger.error(f"Ollama JSON decode error on attempt {attempt + 1}: {last_error}")
                break  # Don't retry JSON errors
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.exception(f"Ollama unexpected error on attempt {attempt + 1}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
        
        return {
            'success': False,
            'data': None,
            'attempt': self.max_retries,
            'error': last_error
        }
    
    def generate_response(self, model: str, prompt: str, stream: bool = False) -> Dict[str, Any]:
        """Generate response using Ollama's generate endpoint."""
        data = {
            'model': model,
            'prompt': prompt,
            'stream': stream
        }
        
        return self.make_request(self.generate_endpoint, data)
    
    def chat_response(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate response using Ollama's chat endpoint."""
        data = {
            'model': model,
            'messages': messages
        }
        
        return self.make_request(self.chat_endpoint, data)
    
    def get_available_models(self) -> Dict[str, Any]:
        """Get list of available models from Ollama."""
        return self.make_request(self.tags_endpoint, {}, method='GET')
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration information."""
        return {
            'host': self.host,
            'port': self.port,
            'base_url': self.base_url,
            'timeout': self.timeout,
            'connect_timeout': self.connect_timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'endpoints': {
                'generate': self.generate_endpoint,
                'chat': self.chat_endpoint,
                'tags': self.tags_endpoint
            }
        }

# Global configuration instance
ollama_config = OllamaConfig()

# Convenience functions for backward compatibility
def get_ollama_response(model: str, prompt: str) -> str:
    """Get simple text response from Ollama (backward compatibility)."""
    result = ollama_config.generate_response(model, prompt)
    
    if result['success']:
        return result['data'].get('response', 'No response generated')
    else:
        error_msg = f"Ollama request failed: {result['error']}"
        logger.error(error_msg)
        return f"Error: {result['error']}"

def test_ollama_connection() -> bool:
    """Simple boolean test for Ollama connectivity."""
    result = ollama_config.test_connection()
    return result['connected']

def get_ollama_models() -> List[str]:
    """Get list of available model names."""
    result = ollama_config.get_available_models()
    
    if result['success']:
        models = result['data'].get('models', [])
        return [model['name'] for model in models]
    else:
        logger.error(f"Failed to get models: {result['error']}")
        return []

# Test functionality when run directly
if __name__ == "__main__":
    print("Testing Ollama Configuration...")
    
    # Test connection
    connection_result = ollama_config.test_connection()
    print(f"Connection Test: {json.dumps(connection_result, indent=2)}")
    
    if connection_result['connected']:
        # Test getting models
        models_result = ollama_config.get_available_models()
        print(f"Models Result: {json.dumps(models_result, indent=2)}")
        
        # Test simple response if models are available
        if models_result['success'] and models_result['data']['models']:
            model_name = models_result['data']['models'][0]['name']
            print(f"\nTesting response with model: {model_name}")
            
            response = get_ollama_response(model_name, "What is AI?")
            print(f"Response: {response[:100]}...")
    
    print(f"\nConfiguration Info:")
    print(json.dumps(ollama_config.get_config_info(), indent=2))