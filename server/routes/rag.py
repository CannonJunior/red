"""RAG route handlers for document ingestion and querying."""

import os
from pathlib import Path
from debug_logger import debug_log

try:
    from rag_api import (
        handle_rag_status_request,
        handle_rag_search_request,
        handle_rag_query_request,
        handle_rag_ingest_request,
        handle_rag_documents_request,
        handle_rag_analytics_request,
        handle_rag_document_delete_request
    )
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


def handle_rag_status_api(handler):
    """Handle RAG status API requests."""
    try:
        status_result = handle_rag_status_request()
        debug_log(f"RAG status: {status_result.get('status', 'unknown')}", "🔍")
        handler.send_json_response(status_result)
    except Exception as e:
        print(f"❌ RAG status API error: {e}")
        handler.send_json_response({'error': f'RAG status error: {str(e)}'}, 500)


def handle_rag_search_api(handler):
    """Handle RAG search API requests."""
    try:
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        query = request_data.get('query', '').strip()
        max_results = request_data.get('max_results', 5)

        if not query:
            handler.send_json_response({'error': 'Query is required'}, 400)
            return

        search_result = handle_rag_search_request(query, max_results)
        debug_log(f"RAG search: '{query}' -> {search_result.get('results', []).__len__()} results", "🔍")
        handler.send_json_response(search_result)
    except Exception as e:
        print(f"❌ RAG search API error: {e}")
        handler.send_json_response({'error': f'RAG search error: {str(e)}'}, 500)


def handle_rag_query_api(handler):
    """Handle RAG query API requests."""
    try:
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        query = request_data.get('query', '').strip()
        max_context = request_data.get('max_context', 5)

        if not query:
            handler.send_json_response({'error': 'Query is required'}, 400)
            return

        query_result = handle_rag_query_request(query, max_context)
        debug_log(f"RAG query: '{query}' -> {query_result.get('status', 'unknown')}", "🤖")
        handler.send_json_response(query_result)
    except Exception as e:
        print(f"❌ RAG query API error: {e}")
        handler.send_json_response({'error': f'RAG query error: {str(e)}'}, 500)


def handle_rag_ingest_api(handler):
    """Handle RAG document ingestion API requests (supports both FormData files and JSON file paths)."""
    try:
        content_type = handler.headers.get('Content-Type', '')

        if content_type.startswith('multipart/form-data'):
            # Handle file upload via FormData
            _handle_file_upload(handler)
        else:
            # Handle JSON request with file path
            request_data = handler.get_request_body()
            if request_data is None:
                handler.send_json_response({'error': 'Invalid JSON'}, 400)
                return

            file_path = request_data.get('file_path', '').strip()

            if not file_path:
                handler.send_json_response({'error': 'File path is required'}, 400)
                return

            ingest_result = handle_rag_ingest_request(file_path)
            debug_log(f"RAG ingest: '{file_path}' -> {ingest_result.get('status', 'unknown')}", "📄")
            handler.send_json_response(ingest_result)

    except Exception as e:
        print(f"❌ RAG ingest API error: {e}")
        handler.send_json_response({'error': f'RAG ingest error: {str(e)}'}, 500)


def _handle_file_upload(handler):
    """Handle multipart form data file upload."""
    import cgi

    try:
        # Parse multipart form data
        content_type = handler.headers.get('Content-Type', '')

        # Create a temporary environment variable for CGI
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': handler.headers.get('Content-Length', '0')
        }

        form = cgi.FieldStorage(
            fp=handler.rfile,
            headers=handler.headers,
            environ=environ
        )

        # Get the uploaded file
        if 'file' not in form:
            handler.send_json_response({'error': 'No file uploaded'}, 400)
            return

        file_item = form['file']
        if not file_item.filename:
            handler.send_json_response({'error': 'No file selected'}, 400)
            return

        # Extract workspace/knowledge_base parameter
        knowledge_base = 'default'
        if 'knowledge_base' in form:
            knowledge_base = form['knowledge_base'].value

        debug_log(f"File upload for workspace: {knowledge_base}", "📤")

        # Create uploads directory if it doesn't exist
        uploads_dir = Path('uploads')
        uploads_dir.mkdir(exist_ok=True)

        # Save uploaded file
        file_path = uploads_dir / file_item.filename
        with open(file_path, 'wb') as f:
            f.write(file_item.file.read())

        debug_log(f"File uploaded: {file_item.filename} -> {file_path}", "📤")

        # Process the uploaded file with RAG system
        try:
            debug_log(f"Starting RAG ingestion for: {file_path} (workspace: {knowledge_base})", "🔄")
            ingest_result = handle_rag_ingest_request(str(file_path), knowledge_base)
            debug_log(f"RAG ingest: '{file_path}' -> {ingest_result.get('status', 'unknown')}", "📄")

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
            debug_log(f"Cleaned up temporary file: {file_path}", "🧹")
        except OSError as cleanup_error:
            print(f"⚠️  Could not clean up file {file_path}: {cleanup_error}")

        handler.send_json_response(ingest_result)

    except Exception as e:
        print(f"❌ File upload error: {e}")
        handler.send_json_response({'error': f'File upload failed: {str(e)}'}, 500)


def handle_rag_documents_api(handler):
    """Handle RAG documents listing API requests."""
    try:
        # Extract workspace parameter from request
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return
        workspace = request_data.get('workspace', 'default')

        documents_result = handle_rag_documents_request(workspace)
        debug_log(f"RAG documents: {len(documents_result.get('documents', []))} documents found for workspace '{workspace}'", "📋")
        handler.send_json_response(documents_result)

    except Exception as e:
        print(f"❌ RAG documents API error: {e}")
        handler.send_json_response({'error': f'Failed to load documents: {str(e)}'}, 500)


def handle_rag_analytics_api(handler):
    """Handle RAG analytics API requests."""
    try:
        analytics_result = handle_rag_analytics_request()
        debug_log(f"RAG analytics: {analytics_result.get('document_count', 0)} docs, {analytics_result.get('chunk_count', 0)} chunks", "📊")
        handler.send_json_response(analytics_result)

    except Exception as e:
        print(f"❌ RAG analytics API error: {e}")
        handler.send_json_response({'error': f'Failed to load analytics: {str(e)}'}, 500)


def handle_rag_upload_api(handler):
    """Handle RAG file upload API requests."""
    try:
        debug_log(f"RAG upload request received", "📤")

        handler.send_json_response({
            'status': 'success',
            'message': 'File uploaded successfully'
        })

    except Exception as e:
        print(f"❌ RAG upload API error: {e}")
        handler.send_json_response({'error': f'Upload failed: {str(e)}'}, 500)


def handle_rag_document_delete_api(handler, document_id):
    """Handle RAG document deletion API requests."""
    try:
        # Extract workspace parameter from request
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return
        workspace = request_data.get('workspace', 'default')

        debug_log(f"RAG delete request for document: {document_id} from workspace: {workspace}", "🗑️")

        # Call the actual delete function from RAG API
        result = handle_rag_document_delete_request(document_id, workspace)

        if result.get("status") == "success":
            handler.send_json_response({
                'status': 'success',
                'message': result.get('message', f'Document {document_id} deleted successfully'),
                'document_id': document_id,
                'timestamp': result.get('timestamp')
            })
        else:
            handler.send_json_response({
                'status': 'error',
                'error': result.get('message', f'Failed to delete document {document_id}'),
                'document_id': document_id
            }, 400)

    except Exception as e:
        print(f"❌ RAG document delete API error: {e}")
        handler.send_json_response({'error': f'Delete failed: {str(e)}'}, 500)
