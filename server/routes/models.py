"""Models route handlers for Ollama model management."""

from debug_logger import debug_log
from ollama_config import ollama_config
from server.utils.error_handler import error_handler


@error_handler
def handle_models_api(handler):
    """
    Handle models API requests to get available Ollama models.

    Args:
        handler: The HTTP request handler instance
    """
    debug_log("Requesting available Ollama models...", "📋")
    result = ollama_config.get_available_models()

    if result['success']:
        models = [model['name'] for model in result['data'].get('models', [])]
        debug_log(f"Available models: {models}", "📋")
        handler.send_json_response({
            'models': models,
            'count': len(models),
            'connection_attempt': result['attempt']
        })
    else:
        print(f"❌ Failed to get models: {result['error']}")
        handler.send_json_response({
            'error': f"Failed to get models: {result['error']}",
            'models': [],
            'count': 0,
            'connection_attempt': result['attempt']
        }, 503)
