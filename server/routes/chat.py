"""
Chat API routes.

Handles chat functionality including:
- Standard chat with Ollama
- RAG-enhanced chat
- CAG-enhanced chat
- MCP tool integration
- Model listing
"""

import os
import json
from rate_limiter import rate_limit
from request_validation import validate_request, ChatRequest
from debug_logger import debug_log
import ollama_config


class ChatRoutes:
    """Mixin providing chat-related routes."""

    @rate_limit(requests_per_minute=60, burst=10)
    @validate_request(ChatRequest)
    def handle_chat_api(self):
        """
        Handle chat API requests with MCP-style RAG tool integration.

        POST /api/chat
        Body: {
            "message": "user message",
            "model": "qwen2.5:3b",
            "workspace": "default",
            "knowledge_mode": "rag|cag|none",
            "mcp_tool_call": {...}
        }

        Supports three modes:
        - RAG: Retrieval-Augmented Generation with vector search
        - CAG: Cache-Augmented Generation with preloaded context
        - Standard: Direct LLM chat
        """
        try:
            # Use validated data
            message = self.validated_data.message
            model = self.validated_data.model
            workspace = self.validated_data.workspace
            knowledge_mode = self.validated_data.knowledge_mode
            mcp_tool_call = self.validated_data.mcp_tool_call

            # Handle MCP tool calls
            if mcp_tool_call:
                debug_log(f"MCP Tool call: {mcp_tool_call.get('tool_name', 'unknown')}", "🔧")
                self.handle_mcp_tool_call(mcp_tool_call, model)
                return

            debug_log(f"Chat request: {message[:50]}... (model: {model}, knowledge_mode: {knowledge_mode})", "💬")

            # Import availability flags
            from server.utils.system import RAG_AVAILABLE, CAG_AVAILABLE

            # Determine which mode to use based on knowledge_mode parameter
            use_rag = knowledge_mode == 'rag' and RAG_AVAILABLE
            use_cag = knowledge_mode == 'cag' and CAG_AVAILABLE

            if use_rag:
                # Use RAG-enhanced response
                response_text, model_used, sources, token_info = self.get_rag_enhanced_response(message, model, workspace)
                debug_log(f"RAG-enhanced response: {response_text[:50]}...", "🧠")

                # Count unique source files instead of chunks
                unique_sources = set()
                if sources:
                    for source in sources:
                        if 'metadata' in source and 'source' in source['metadata']:
                            file_path = source['metadata']['source']
                            document_name = os.path.basename(file_path)
                            unique_sources.add(document_name)

                # Send RAG response back to client
                self.send_json_response({
                    'response': response_text,
                    'model': model_used,
                    'rag_enabled': True,
                    'sources_used': len(unique_sources),
                    'timestamp': '',
                    'tokens_used': token_info.get('total_tokens', 0),
                    'prompt_tokens': token_info.get('prompt_tokens', 0),
                    'completion_tokens': token_info.get('completion_tokens', 0)
                })
            elif use_cag:
                # Use CAG-enhanced response (with preloaded context)
                debug_log(f"Making CAG request with model: {model}", "💾")
                result = ollama_config.generate_response(model, message)

                if result['success']:
                    response_text = result['data'].get('response', 'Sorry, I could not generate a response.')
                    debug_log(f"CAG response: {response_text[:50]}...", "💾")

                    # Extract token usage from Ollama response
                    prompt_tokens = result['data'].get('prompt_eval_count', 0)
                    completion_tokens = result['data'].get('eval_count', 0)
                    total_tokens = prompt_tokens + completion_tokens

                    # Send response back to client (with cag_enabled flag)
                    self.send_json_response({
                        'response': response_text,
                        'model': model,
                        'rag_enabled': False,
                        'cag_enabled': True,
                        'timestamp': result['data'].get('created_at', ''),
                        'connection_attempt': result['attempt'],
                        'tokens_used': total_tokens,
                        'prompt_tokens': prompt_tokens,
                        'completion_tokens': completion_tokens
                    })
                else:
                    print(f"❌ Ollama request failed: {result['error']}")
                    self.send_json_response({
                        'error': f"Ollama request failed: {result['error']}",
                        'connection_attempt': result['attempt']
                    }, 503)
            else:
                # Use robust Ollama configuration for standard response (no knowledge base)
                debug_log(f"Making standard Ollama request with model: {model}", "📤")
                result = ollama_config.generate_response(model, message)

                if result['success']:
                    response_text = result['data'].get('response', 'Sorry, I could not generate a response.')
                    debug_log(f"Standard response: {response_text[:50]}...", "🤖")

                    # Extract token usage from Ollama response
                    prompt_tokens = result['data'].get('prompt_eval_count', 0)
                    completion_tokens = result['data'].get('eval_count', 0)
                    total_tokens = prompt_tokens + completion_tokens

                    # Send response back to client
                    self.send_json_response({
                        'response': response_text,
                        'model': model,
                        'rag_enabled': False,
                        'timestamp': result['data'].get('created_at', ''),
                        'connection_attempt': result['attempt'],
                        'tokens_used': total_tokens,
                        'prompt_tokens': prompt_tokens,
                        'completion_tokens': completion_tokens
                    })
                else:
                    print(f"❌ Ollama request failed: {result['error']}")
                    self.send_json_response({
                        'error': f"Ollama request failed: {result['error']}",
                        'connection_attempt': result['attempt']
                    }, 503)

        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            self.send_json_response({'error': 'Invalid JSON in request'}, 400)

        except Exception as e:
            print(f"❌ Chat API error: {e}")
            self.send_json_response({'error': f'Chat API error: {str(e)}'}, 500)

    def get_rag_enhanced_response(self, message, model, workspace='default'):
        """
        Get RAG-enhanced response with vector search.

        Args:
            message: User message
            model: LLM model to use
            workspace: Workspace/collection name

        Returns:
            Tuple of (response_text, model_used, sources, token_info)
        """
        try:
            from rag_api import handle_rag_query_request

            # Query RAG system
            rag_result = handle_rag_query_request({
                'query': message,
                'collection': workspace,
                'model': model
            })

            response_text = rag_result.get('answer', 'No response generated')
            sources = rag_result.get('sources', [])
            model_used = rag_result.get('model', model)

            # Token info
            token_info = {
                'total_tokens': rag_result.get('total_tokens', 0),
                'prompt_tokens': rag_result.get('prompt_tokens', 0),
                'completion_tokens': rag_result.get('completion_tokens', 0)
            }

            return response_text, model_used, sources, token_info

        except Exception as e:
            debug_log(f"RAG query error: {e}", "❌")
            # Fallback to standard response
            result = ollama_config.generate_response(model, message)
            if result['success']:
                return (
                    result['data'].get('response', ''),
                    model,
                    [],
                    {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}
                )
            else:
                return ("Error generating response", model, [], {})

    def handle_models_api(self):
        """
        Get list of available models from Ollama.

        GET /api/models

        Returns list of models with metadata.
        """
        try:
            models = ollama_config.list_models()

            if models:
                self.send_json_response({
                    'models': models,
                    'count': len(models)
                })
            else:
                self.send_json_response({
                    'error': 'No models available'
                }, 503)

        except Exception as e:
            debug_log(f"Models API error: {e}", "❌")
            self.send_json_response({
                'error': f'Failed to fetch models: {str(e)}'
            }, 500)
