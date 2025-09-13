#!/usr/bin/env python3
"""
Simple HTTP server for the Robobrain UI web application.
Serves static files on port 9090.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import mimetypes
from pathlib import Path

# Import Ollama configuration
from ollama_config import ollama_config

# Import RAG functionality
try:
    from rag_api import handle_rag_status_request, handle_rag_search_request, handle_rag_query_request, handle_rag_ingest_request, handle_rag_documents_request, handle_rag_analytics_request, handle_rag_document_delete_request
    RAG_AVAILABLE = True
    print("✅ RAG system loaded successfully")
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"⚠️  RAG system not available: {e}")

# Import Search functionality
try:
    from search_api import handle_search_request, handle_folders_request, handle_create_folder_request, handle_tags_request, handle_add_object_request, handle_update_object_request, handle_delete_object_request
    SEARCH_AVAILABLE = True
    print("✅ Search system loaded successfully")
except ImportError as e:
    SEARCH_AVAILABLE = False
    print(f"⚠️  Search system not available: {e}")


class CustomHTTPRequestHandler(BaseHTTPRequestHandler):
    """Custom handler to serve static files with proper MIME types."""
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            # Handle API routes
            if self.path.startswith('/api/'):
                # RAG API endpoints
                if self.path == '/api/rag/documents' and RAG_AVAILABLE:
                    self.handle_rag_documents_api()
                    return
                elif self.path == '/api/rag/analytics' and RAG_AVAILABLE:
                    self.handle_rag_analytics_api()
                    return
                # Search API endpoints
                elif self.path == '/api/search/folders' and SEARCH_AVAILABLE:
                    self.handle_search_folders_api()
                    return
                elif self.path == '/api/search/tags' and SEARCH_AVAILABLE:
                    self.handle_search_tags_api()
                    return
                else:
                    self.send_error(404, f"API endpoint not found: {self.path}")
                    return
            
            # Handle root path
            if self.path == '/':
                self.path = '/index.html'
            
            # Remove leading slash and resolve file path
            file_path = self.path.lstrip('/')
            full_path = os.path.join(os.getcwd(), file_path)
            
            print(f"Request: {self.path} -> {file_path}")
            
            # Check if file exists
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                self.send_error(404, f"File not found: {self.path}")
                return
            
            # Determine content type
            content_type = self.get_content_type(file_path)
            
            # Read and serve file
            with open(full_path, 'rb') as f:
                content = f.read()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache')
            # Add CORS headers
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Send content
            self.wfile.write(content)
            
            print(f"✅ Served {file_path} as {content_type}")
            
        except Exception as e:
            print(f"❌ Error serving {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def do_POST(self):
        """Handle POST requests for API endpoints."""
        try:
            # Parse request path
            if self.path == '/api/chat':
                self.handle_chat_api()
            elif self.path == '/api/models':
                self.handle_models_api()
            elif self.path == '/api/rag/status' and RAG_AVAILABLE:
                self.handle_rag_status_api()
            elif self.path == '/api/rag/search' and RAG_AVAILABLE:
                self.handle_rag_search_api()
            elif self.path == '/api/rag/query' and RAG_AVAILABLE:
                self.handle_rag_query_api()
            elif self.path == '/api/rag/ingest' and RAG_AVAILABLE:
                self.handle_rag_ingest_api()
            elif self.path == '/api/rag/upload' and RAG_AVAILABLE:
                self.handle_rag_upload_api()
            elif self.path == '/api/rag/documents' and RAG_AVAILABLE:
                self.handle_rag_documents_api()
            # Search API endpoints
            elif self.path == '/api/search' and SEARCH_AVAILABLE:
                self.handle_search_api()
            elif self.path == '/api/search/folders' and SEARCH_AVAILABLE:
                self.handle_search_create_folder_api()
            elif self.path == '/api/search/objects' and SEARCH_AVAILABLE:
                self.handle_search_add_object_api()
            else:
                self.send_error(404, f"API endpoint not found: {self.path}")
                
        except Exception as e:
            print(f"❌ Error handling POST {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def do_DELETE(self):
        """Handle DELETE requests for API endpoints."""
        try:
            # Parse request path for DELETE operations
            if self.path.startswith('/api/rag/documents/') and RAG_AVAILABLE:
                # Extract document ID from path
                document_id = self.path.split('/')[-1]
                self.handle_rag_document_delete_api(document_id)
            else:
                self.send_error(404, f"API endpoint not found: {self.path}")
                
        except Exception as e:
            print(f"❌ Error handling DELETE {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def handle_chat_api(self):
        """Handle chat API requests with MCP-style RAG tool integration."""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Extract message, model, and workspace
            message = request_data.get('message', '').strip()
            model = request_data.get('model', 'qwen2.5:3b')  # Default to smaller model
            workspace = request_data.get('workspace', 'default')  # Extract workspace
            
            if not message:
                self.send_json_response({'error': 'Message is required'}, 400)
                return
            
            print(f"💬 Chat request: {message[:50]}... (model: {model})")
            
            # Check if RAG should be used based on query patterns
            should_use_rag = RAG_AVAILABLE and self.should_trigger_rag(message)
            
            if should_use_rag:
                # Use RAG-enhanced response
                response_text, model_used, sources = self.get_rag_enhanced_response(message, model, workspace)
                print(f"🧠 RAG-enhanced response: {response_text[:50]}...")

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
                    'timestamp': ''
                })
            else:
                # Use robust Ollama configuration for standard response
                print(f"📤 Making standard Ollama request with model: {model}")
                result = ollama_config.generate_response(model, message)
                
                if result['success']:
                    response_text = result['data'].get('response', 'Sorry, I could not generate a response.')
                    print(f"🤖 Standard Ollama response: {response_text[:50]}...")
                    
                    # Send response back to client
                    self.send_json_response({
                        'response': response_text,
                        'model': model,
                        'rag_enabled': False,
                        'timestamp': result['data'].get('created_at', ''),
                        'connection_attempt': result['attempt']
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
    
    def handle_models_api(self):
        """Handle models API requests to get available Ollama models."""
        try:
            # Use robust Ollama configuration to get models
            print("📋 Requesting available Ollama models...")
            result = ollama_config.get_available_models()
            
            if result['success']:
                models = [model['name'] for model in result['data'].get('models', [])]
                print(f"📋 Available models: {models}")
                
                self.send_json_response({
                    'models': models,
                    'count': len(models),
                    'connection_attempt': result['attempt']
                })
            else:
                print(f"❌ Failed to get models: {result['error']}")
                self.send_json_response({
                    'error': f"Failed to get models: {result['error']}",
                    'models': [],
                    'count': 0,
                    'connection_attempt': result['attempt']
                }, 503)
            
        except Exception as e:
            print(f"❌ Models API error: {e}")
            self.send_json_response({'error': f'Models API error: {str(e)}'}, 500)
    
    def handle_rag_status_api(self):
        """Handle RAG status API requests."""
        try:
            status_result = handle_rag_status_request()
            print(f"🔍 RAG status: {status_result.get('status', 'unknown')}")
            self.send_json_response(status_result)
        except Exception as e:
            print(f"❌ RAG status API error: {e}")
            self.send_json_response({'error': f'RAG status error: {str(e)}'}, 500)
    
    def handle_rag_search_api(self):
        """Handle RAG search API requests."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            query = request_data.get('query', '').strip()
            max_results = request_data.get('max_results', 5)
            
            if not query:
                self.send_json_response({'error': 'Query is required'}, 400)
                return
            
            search_result = handle_rag_search_request(query, max_results)
            print(f"🔍 RAG search: '{query}' -> {search_result.get('results', []).__len__()} results")
            self.send_json_response(search_result)
        except Exception as e:
            print(f"❌ RAG search API error: {e}")
            self.send_json_response({'error': f'RAG search error: {str(e)}'}, 500)
    
    def handle_rag_query_api(self):
        """Handle RAG query API requests."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            query = request_data.get('query', '').strip()
            max_context = request_data.get('max_context', 5)
            
            if not query:
                self.send_json_response({'error': 'Query is required'}, 400)
                return
            
            query_result = handle_rag_query_request(query, max_context)
            print(f"🤖 RAG query: '{query}' -> {query_result.get('status', 'unknown')}")
            self.send_json_response(query_result)
        except Exception as e:
            print(f"❌ RAG query API error: {e}")
            self.send_json_response({'error': f'RAG query error: {str(e)}'}, 500)
    
    def handle_rag_ingest_api(self):
        """Handle RAG document ingestion API requests (supports both FormData files and JSON file paths)."""
        try:
            content_type = self.headers.get('Content-Type', '')
            
            if content_type.startswith('multipart/form-data'):
                # Handle file upload via FormData
                self._handle_file_upload()
            else:
                # Handle JSON request with file path
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                
                file_path = request_data.get('file_path', '').strip()
                
                if not file_path:
                    self.send_json_response({'error': 'File path is required'}, 400)
                    return
                
                ingest_result = handle_rag_ingest_request(file_path)
                print(f"📄 RAG ingest: '{file_path}' -> {ingest_result.get('status', 'unknown')}")
                self.send_json_response(ingest_result)
                
        except Exception as e:
            print(f"❌ RAG ingest API error: {e}")
            self.send_json_response({'error': f'RAG ingest error: {str(e)}'}, 500)

    def _handle_file_upload(self):
        """Handle multipart form data file upload."""
        import cgi
        import tempfile
        import os
        
        try:
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            
            # Create a temporary environment variable for CGI
            environ = {
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': content_type,
                'CONTENT_LENGTH': self.headers.get('Content-Length', '0')
            }
            
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ=environ
            )
            
            # Get the uploaded file
            if 'file' not in form:
                self.send_json_response({'error': 'No file uploaded'}, 400)
                return
            
            file_item = form['file']
            if not file_item.filename:
                self.send_json_response({'error': 'No file selected'}, 400)
                return
            
            # Extract workspace/knowledge_base parameter
            knowledge_base = 'default'
            if 'knowledge_base' in form:
                knowledge_base = form['knowledge_base'].value
            
            print(f"📤 File upload for workspace: {knowledge_base}")
            
            # Create uploads directory if it doesn't exist
            uploads_dir = Path('uploads')
            uploads_dir.mkdir(exist_ok=True)
            
            # Save uploaded file
            file_path = uploads_dir / file_item.filename
            with open(file_path, 'wb') as f:
                f.write(file_item.file.read())
            
            print(f"📤 File uploaded: {file_item.filename} -> {file_path}")
            
            # Process the uploaded file with RAG system
            try:
                print(f"🔄 Starting RAG ingestion for: {file_path} (workspace: {knowledge_base})")
                ingest_result = handle_rag_ingest_request(str(file_path), knowledge_base)
                print(f"📄 RAG ingest: '{file_path}' -> {ingest_result.get('status', 'unknown')}")
                
                if ingest_result.get('status') == 'error':
                    print(f"❌ RAG ingestion failed: {ingest_result.get('message', 'Unknown error')}")
                    
            except Exception as ingest_error:
                print(f"❌ RAG ingestion exception for '{file_path}': {ingest_error}")
                import traceback
                traceback.print_exc()
                ingest_result = {
                    'status': 'error',
                    'message': f'RAG ingestion failed: {str(ingest_error)}'
                }
            
            # Clean up uploaded file after processing (optional)
            try:
                os.remove(file_path)
                print(f"🧹 Cleaned up temporary file: {file_path}")
            except OSError as cleanup_error:
                print(f"⚠️  Could not clean up file {file_path}: {cleanup_error}")
            
            self.send_json_response(ingest_result)
            
        except Exception as e:
            print(f"❌ File upload error: {e}")
            self.send_json_response({'error': f'File upload failed: {str(e)}'}, 500)
    
    def should_trigger_rag(self, message):
        """Determine if RAG should be used for this message."""
        # Keywords that suggest the user wants information from documents
        rag_triggers = [
            # Question words
            'what', 'how', 'when', 'where', 'why', 'which', 'who',
            # Information seeking
            'explain', 'describe', 'tell me about', 'information about',
            'details about', 'summary of', 'analyze', 'analysis',
            # Document-specific
            'document', 'file', 'data', 'spreadsheet', 'csv', 'table',
            'report', 'content', 'contains', 'mentions',
            # Search patterns
            'find', 'search', 'look for', 'show me', 'list',
            # Knowledge queries
            'know about', 'learn about', 'understand'
        ]
        
        message_lower = message.lower()
        
        # Check if message contains RAG trigger words
        for trigger in rag_triggers:
            if trigger in message_lower:
                return True
        
        # Check if it's a question (ends with ?)
        if message.strip().endswith('?'):
            return True
        
        return False
    
    def get_rag_enhanced_response(self, message, model, workspace='default'):
        """Get RAG-enhanced response using MCP-style tool integration."""
        try:
            # Use the RAG query endpoint
            rag_result = handle_rag_query_request(message, max_context=5, workspace=workspace)
            
            if rag_result['status'] == 'success':
                response_text = rag_result['answer']
                sources = rag_result.get('sources', [])
                model_used = rag_result.get('model_used', model)
                
                # Debug: Print sources information
                print(f"🔍 RAG Debug - Sources count: {len(sources)}")
                print(f"🔍 RAG Debug - Sources type: {type(sources)}")
                if sources:
                    print(f"🔍 RAG Debug - First source: {sources[0]}")
                else:
                    print(f"🔍 RAG Debug - RAG result keys: {rag_result.keys()}")
                
                # Add source attribution if sources exist
                if sources:
                    # Extract unique document names from sources
                    document_names = set()
                    for source in sources:
                        if 'metadata' in source and 'source' in source['metadata']:
                            file_path = source['metadata']['source']
                            # Extract just the filename from the full path
                            document_name = os.path.basename(file_path)
                            document_names.add(document_name)
                    
                    if document_names:
                        doc_list = ', '.join(sorted(document_names))
                        source_info = f"\n\n📚 Sources consulted: {doc_list}"
                    else:
                        source_info = f"\n\n📚 Sources consulted: {len(sources)} document(s)"
                    
                    response_text += source_info
                
                return response_text, model_used, sources
            else:
                # Fallback to standard Ollama if RAG fails
                print(f"⚠️ RAG failed, falling back to standard response: {rag_result.get('message', 'Unknown error')}")
                return self.get_standard_ollama_response(message, model), model, []
                
        except Exception as e:
            print(f"❌ RAG enhancement error: {e}")
            return self.get_standard_ollama_response(message, model), model, []
    
    def get_standard_ollama_response(self, message, model):
        """Get standard Ollama response without RAG using robust configuration."""
        print(f"📤 Making fallback Ollama request with model: {model}")
        result = ollama_config.generate_response(model, message)
        
        if result['success']:
            response_text = result['data'].get('response', 'Sorry, I could not generate a response.')
            print(f"🤖 Fallback Ollama response: {response_text[:50]}...")
            return response_text
        else:
            error_msg = f"Ollama connection failed after {result['attempt']} attempts: {result['error']}"
            print(f"❌ Standard Ollama request failed: {error_msg}")
            return f"Sorry, I'm currently unable to process your request. {error_msg}"
    
    # Search API handlers
    def handle_search_api(self):
        """Handle universal search API requests."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            search_result = handle_search_request(request_data)
            print(f"🔍 Search: '{request_data.get('query', '')}' -> {search_result.get('data', {}).get('total_count', 0)} results")
            self.send_json_response(search_result)
            
        except Exception as e:
            print(f"❌ Search API error: {e}")
            self.send_json_response({'error': f'Search failed: {str(e)}'}, 500)
    
    def handle_search_folders_api(self):
        """Handle folders listing API requests."""
        try:
            if self.command == 'GET':
                # GET request - list folders
                folders_result = handle_folders_request()
                print(f"📁 Folders: {len(folders_result.get('folders', []))} folders")
                self.send_json_response(folders_result)
            else:
                # POST request - create folder
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                
                create_result = handle_create_folder_request(request_data)
                print(f"📁 Create folder: {request_data.get('name', 'Unknown')}")
                self.send_json_response(create_result)
            
        except Exception as e:
            print(f"❌ Folders API error: {e}")
            self.send_json_response({'error': f'Folders operation failed: {str(e)}'}, 500)
    
    def handle_search_create_folder_api(self):
        """Handle folder creation API requests."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            create_result = handle_create_folder_request(request_data)
            print(f"📁 Create folder: {request_data.get('name', 'Unknown')}")
            self.send_json_response(create_result)
            
        except Exception as e:
            print(f"❌ Create folder API error: {e}")
            self.send_json_response({'error': f'Create folder failed: {str(e)}'}, 500)
    
    def handle_search_tags_api(self):
        """Handle tags listing API requests."""
        try:
            tags_result = handle_tags_request()
            print(f"🏷️  Tags: {len(tags_result.get('tags', []))} tags")
            self.send_json_response(tags_result)
            
        except Exception as e:
            print(f"❌ Tags API error: {e}")
            self.send_json_response({'error': f'Tags operation failed: {str(e)}'}, 500)
    
    def handle_search_add_object_api(self):
        """Handle adding searchable objects API requests."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            add_result = handle_add_object_request(request_data)
            print(f"➕ Add object: {request_data.get('title', 'Unknown')} ({request_data.get('type', 'unknown')})")
            self.send_json_response(add_result)
            
        except Exception as e:
            print(f"❌ Add object API error: {e}")
            self.send_json_response({'error': f'Add object failed: {str(e)}'}, 500)

    def send_json_response(self, data, status_code=200):
        """Send a JSON response."""
        response_json = json.dumps(data)
        response_bytes = response_json.encode('utf-8')
        
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        self.wfile.write(response_bytes)
    
    def do_HEAD(self):
        """Handle HEAD requests (like GET but without body)."""
        try:
            # Handle root path
            if self.path == '/':
                self.path = '/index.html'
            
            # Remove leading slash and resolve file path
            file_path = self.path.lstrip('/')
            full_path = os.path.join(os.getcwd(), file_path)
            
            # Check if file exists
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                self.send_error(404, f"File not found: {self.path}")
                return
            
            # Get file size and content type
            file_size = os.path.getsize(full_path)
            content_type = self.get_content_type(file_path)
            
            # Send headers only (no body for HEAD)
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
        except Exception as e:
            print(f"❌ Error handling HEAD {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def get_content_type(self, file_path):
        """Determine content type based on file extension."""
        # Define explicit mappings for web files
        content_types = {
            '.html': 'text/html; charset=utf-8',
            '.htm': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.svg': 'image/svg+xml',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.ico': 'image/x-icon',
        }
        
        # Get file extension
        _, ext = os.path.splitext(file_path.lower())
        
        # Return specific type or default
        return content_types.get(ext, 'text/plain')
    
    def log_message(self, format, *args):
        """Override to provide cleaner logging."""
        return  # Disable default logging to reduce noise

    def handle_rag_documents_api(self):
        """Handle RAG documents listing API requests."""
        try:
            # Extract workspace parameter from request
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                workspace = request_data.get('workspace', 'default')
            else:
                workspace = 'default'
            
            documents_result = handle_rag_documents_request(workspace)
            print(f"📋 RAG documents: {len(documents_result.get('documents', []))} documents found for workspace '{workspace}'")
            self.send_json_response(documents_result)
            
        except Exception as e:
            print(f"❌ RAG documents API error: {e}")
            self.send_json_response({'error': f'Failed to load documents: {str(e)}'}, 500)

    def handle_rag_analytics_api(self):
        """Handle RAG analytics API requests."""
        try:
            analytics_result = handle_rag_analytics_request()
            print(f"📊 RAG analytics: {analytics_result.get('document_count', 0)} docs, {analytics_result.get('chunk_count', 0)} chunks")
            self.send_json_response(analytics_result)
            
        except Exception as e:
            print(f"❌ RAG analytics API error: {e}")
            self.send_json_response({'error': f'Failed to load analytics: {str(e)}'}, 500)

    def handle_rag_upload_api(self):
        """Handle RAG file upload API requests."""
        try:
            # For now, just return success
            # This should eventually implement actual file upload and ingestion
            print(f"📤 RAG upload request received")
            
            self.send_json_response({
                'status': 'success',
                'message': 'File uploaded successfully'
            })
            
        except Exception as e:
            print(f"❌ RAG upload API error: {e}")
            self.send_json_response({'error': f'Upload failed: {str(e)}'}, 500)

    def handle_rag_document_delete_api(self, document_id):
        """Handle RAG document deletion API requests."""
        try:
            # Extract workspace parameter from request
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                workspace = request_data.get('workspace', 'default')
            else:
                workspace = 'default'
            
            print(f"🗑️ RAG delete request for document: {document_id} from workspace: {workspace}")
            
            # Call the actual delete function from RAG API
            result = handle_rag_document_delete_request(document_id, workspace)
            
            if result.get("status") == "success":
                self.send_json_response({
                    'status': 'success',
                    'message': result.get('message', f'Document {document_id} deleted successfully'),
                    'document_id': document_id,
                    'timestamp': result.get('timestamp')
                })
            else:
                self.send_json_response({
                    'status': 'error',
                    'error': result.get('message', f'Failed to delete document {document_id}'),
                    'document_id': document_id
                }, 400)
            
        except Exception as e:
            print(f"❌ RAG document delete API error: {e}")
            self.send_json_response({'error': f'Delete failed: {str(e)}'}, 500)


def main():
    """Start the development server."""
    port = 9090
    server_address = ('localhost', port)
    
    try:
        # Change to the directory containing the web files
        web_dir = Path(__file__).parent
        os.chdir(web_dir)
        
        # Verify required files exist
        if not os.path.exists('index.html'):
            print("❌ Error: index.html not found in current directory")
            sys.exit(1)
        
        # Create and start the server
        httpd = HTTPServer(server_address, CustomHTTPRequestHandler)
        
        print(f"🚀 Robobrain UI Server starting...")
        print(f"📁 Serving files from: {web_dir}")
        print(f"🌐 Server running at: http://localhost:{port}")
        print(f"🔗 Open in browser: http://localhost:{port}")
        print(f"⏹️  Press Ctrl+C to stop the server")
        print(f"💡 Started with: uv run server.py")
        print(f"🔍 Available files:")
        
        # List available files
        for file in os.listdir('.'):
            if not file.startswith('.'):
                print(f"   - {file}")
        
        # Start serving
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped by user")
        if 'httpd' in locals():
            httpd.server_close()
        sys.exit(0)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ Port {port} is already in use. Please try a different port or stop the existing server.")
        else:
            print(f"❌ Network error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
