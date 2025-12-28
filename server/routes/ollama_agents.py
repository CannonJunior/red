"""Ollama-based agent management route handlers with skills support."""

import time
import uuid
import datetime
from debug_logger import debug_log
from server_decorators import require_system

# Import Ollama agent runtime
try:
    from agent_system.ollama_agent_runtime import (
        get_runtime,
        OllamaAgentConfig
    )
    OLLAMA_AVAILABLE = True
except ImportError as e:
    debug_log(f"⚠️ Ollama agent runtime not available: {e}", "⚠️")
    OLLAMA_AVAILABLE = False


def handle_ollama_agents_api(handler):
    """Handle /api/ollama/agents endpoint."""
    try:
        if not OLLAMA_AVAILABLE:
            handler.send_json_response({
                'error': 'Ollama agent runtime not available'
            }, 503)
            return

        runtime = get_runtime()

        if handler.command == 'GET':
            # List all Ollama agents
            agents = runtime.list_agents()

            handler.send_json_response({
                'status': 'success',
                'agents': agents,
                'count': len(agents),
                'cost': '$0.00',  # Zero cost - local Ollama
                'red_compliant': True
            })

        elif handler.command == 'POST':
            # Create new Ollama agent
            agent_data = handler.get_request_body()
            if agent_data is None:
                handler.send_json_response({'error': 'Invalid JSON'}, 400)
                return

            # Validate required fields
            if 'name' not in agent_data:
                handler.send_json_response({
                    'error': 'name is required'
                }, 400)
                return

            # Generate agent ID
            agent_id = agent_data.get('agent_id') or f"agent_{str(uuid.uuid4())[:8]}"

            # Create agent config
            config = OllamaAgentConfig(
                agent_id=agent_id,
                name=agent_data['name'],
                description=agent_data.get('description', ''),
                model=agent_data.get('model', 'qwen2.5:3b'),
                capabilities=agent_data.get('capabilities', []),
                skills=agent_data.get('skills', []),
                temperature=agent_data.get('temperature', 0.7),
                max_tokens=agent_data.get('max_tokens', 2048)
            )

            try:
                # Create agent with Ollama runtime
                new_agent = runtime.create_agent(config)

                debug_log(f"Created Ollama agent: {new_agent['name']} ({agent_id})", "✅")

                handler.send_json_response({
                    'status': 'success',
                    'message': 'Agent created successfully with Ollama',
                    'data': new_agent
                })

            except RuntimeError as e:
                # Ollama not available
                handler.send_json_response({
                    'status': 'error',
                    'message': str(e),
                    'hint': 'Please start Ollama server: ollama serve'
                }, 503)

            except ValueError as e:
                # Invalid configuration (e.g., unknown skill)
                handler.send_json_response({
                    'status': 'error',
                    'message': str(e)
                }, 400)

        else:
            handler.send_json_response({
                'status': 'error',
                'message': f'Method {handler.command} not allowed'
            }, 405)

    except Exception as e:
        print(f"❌ Ollama agents API error: {e}")
        import traceback
        traceback.print_exc()
        handler.send_json_response({'error': f'Ollama agents API failed: {str(e)}'}, 500)


def handle_ollama_agent_detail_api(handler):
    """Handle /api/ollama/agents/{agent_id} endpoint."""
    try:
        if not OLLAMA_AVAILABLE:
            handler.send_json_response({
                'error': 'Ollama agent runtime not available'
            }, 503)
            return

        runtime = get_runtime()

        # Extract agent_id from path
        path_parts = handler.path.split('?')[0].split('/')

        # Check if this is a status update endpoint
        if len(path_parts) >= 5 and path_parts[-1] == 'status':
            agent_id = path_parts[-2]

            if handler.command == 'PUT':
                # Update agent status
                agent_data = handler.get_request_body()
                if agent_data is None:
                    handler.send_json_response({'error': 'Invalid JSON'}, 400)
                    return

                new_status = agent_data.get('status')
                if new_status not in ['active', 'inactive']:
                    handler.send_json_response({
                        'status': 'error',
                        'message': 'Status must be "active" or "inactive"'
                    }, 400)
                    return

                try:
                    updated_agent = runtime.update_agent_status(agent_id, new_status)

                    if updated_agent:
                        handler.send_json_response({
                            'status': 'success',
                            'message': f'Agent {agent_id} status updated to {new_status}',
                            'data': updated_agent
                        })
                    else:
                        handler.send_json_response({
                            'status': 'error',
                            'message': f'Agent {agent_id} not found'
                        }, 404)
                except Exception as e:
                    handler.send_json_response({
                        'status': 'error',
                        'message': str(e)
                    }, 500)
            else:
                handler.send_json_response({
                    'status': 'error',
                    'message': f'Method {handler.command} not allowed for status endpoint'
                }, 405)
            return

        agent_id = path_parts[-1]

        if handler.command == 'GET':
            # Get agent info
            agent = runtime.get_agent_info(agent_id)

            if agent:
                handler.send_json_response({
                    'status': 'success',
                    'agent': agent
                })
            else:
                handler.send_json_response({
                    'status': 'error',
                    'message': f'Agent {agent_id} not found'
                }, 404)

        elif handler.command == 'PUT':
            # Update agent
            agent_data = handler.get_request_body()
            if agent_data is None:
                handler.send_json_response({'error': 'Invalid JSON'}, 400)
                return

            try:
                updated_agent = runtime.update_agent(agent_id, agent_data)

                if updated_agent:
                    handler.send_json_response({
                        'status': 'success',
                        'message': f'Agent {agent_id} updated successfully',
                        'data': updated_agent
                    })
                else:
                    handler.send_json_response({
                        'status': 'error',
                        'message': f'Agent {agent_id} not found'
                    }, 404)

            except ValueError as e:
                # Invalid configuration (e.g., unknown skill)
                handler.send_json_response({
                    'status': 'error',
                    'message': str(e)
                }, 400)

        elif handler.command == 'DELETE':
            # Delete agent
            deleted = runtime.delete_agent(agent_id)

            if deleted:
                handler.send_json_response({
                    'status': 'success',
                    'message': f'Agent {agent_id} deleted successfully'
                })
            else:
                handler.send_json_response({
                    'status': 'error',
                    'message': f'Agent {agent_id} not found'
                }, 404)

        else:
            handler.send_json_response({
                'status': 'error',
                'message': f'Method {handler.command} not allowed'
            }, 405)

    except Exception as e:
        print(f"❌ Ollama agent detail API error: {e}")
        handler.send_json_response({'error': f'Agent API failed: {str(e)}'}, 500)


def handle_ollama_agent_invoke_api(handler):
    """Handle /api/ollama/agents/{agent_id}/invoke endpoint."""
    try:
        if not OLLAMA_AVAILABLE:
            handler.send_json_response({
                'error': 'Ollama agent runtime not available'
            }, 503)
            return

        runtime = get_runtime()

        # Extract agent_id from path
        path_parts = handler.path.split('/')
        agent_id = path_parts[-2]  # .../agents/{agent_id}/invoke

        if handler.command == 'POST':
            # Invoke agent
            invoke_data = handler.get_request_body()
            if invoke_data is None:
                handler.send_json_response({'error': 'Invalid JSON'}, 400)
                return

            if 'message' not in invoke_data:
                handler.send_json_response({
                    'error': 'message is required'
                }, 400)
                return

            user_message = invoke_data['message']
            kwargs = {
                'temperature': invoke_data.get('temperature'),
                'max_tokens': invoke_data.get('max_tokens')
            }

            # Remove None values
            kwargs = {k: v for k, v in kwargs.items() if v is not None}

            response = runtime.invoke_agent(agent_id, user_message, **kwargs)

            handler.send_json_response(response)

        else:
            handler.send_json_response({
                'status': 'error',
                'message': f'Method {handler.command} not allowed'
            }, 405)

    except ValueError as e:
        handler.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 404)
    except Exception as e:
        print(f"❌ Ollama agent invoke API error: {e}")
        handler.send_json_response({'error': f'Agent invoke API failed: {str(e)}'}, 500)


def handle_ollama_skills_api(handler):
    """Handle /api/ollama/skills endpoint."""
    try:
        if not OLLAMA_AVAILABLE:
            handler.send_json_response({
                'error': 'Ollama agent runtime not available'
            }, 503)
            return

        runtime = get_runtime()

        if handler.command == 'GET':
            # List all available skills
            skills = runtime.list_skills()

            handler.send_json_response({
                'status': 'success',
                'skills': skills,
                'count': len(skills),
                'red_compliant': True
            })

        else:
            handler.send_json_response({
                'status': 'error',
                'message': f'Method {handler.command} not allowed'
            }, 405)

    except Exception as e:
        print(f"❌ Ollama skills API error: {e}")
        handler.send_json_response({'error': f'Skills API failed: {str(e)}'}, 500)


def handle_ollama_status_api(handler):
    """Handle /api/ollama/status endpoint."""
    try:
        if not OLLAMA_AVAILABLE:
            handler.send_json_response({
                'status': 'unavailable',
                'message': 'Ollama agent runtime module not loaded',
                'ollama_running': False
            })
            return

        runtime = get_runtime()

        # Check if Ollama is available
        ollama_available = runtime.check_ollama_available()

        # Get available models
        models = []
        if ollama_available:
            models = runtime.list_ollama_models()

        handler.send_json_response({
            'status': 'success',
            'ollama_running': ollama_available,
            'ollama_url': runtime.ollama_url,
            'models': models,
            'active_agents': len(runtime.active_agents),
            'available_skills': len(runtime.skills_cache),
            'cost': '$0.00',
            'red_compliant': True
        })

    except Exception as e:
        print(f"❌ Ollama status API error: {e}")
        handler.send_json_response({'error': f'Status API failed: {str(e)}'}, 500)
