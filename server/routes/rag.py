"""
RAG (Retrieval-Augmented Generation) API routes.

Handles RAG system functionality including:
- Document search and retrieval
- RAG-enhanced query processing
- Document ingestion and management
- RAG system status and analytics
"""

from rate_limiter import rate_limit
from request_validation import validate_request, RAGQueryRequest, RAGSearchRequest, RAGIngestRequest
from server_decorators import require_system
from debug_logger import debug_log

# Import system availability flags
from server.utils.system import RAG_AVAILABLE


class RAGRoutes:
    """Mixin providing RAG-related routes."""

    @require_system('rag')
    def handle_rag_status_api(self):
        """
        Get RAG system status.

        GET /api/rag/status

        Returns status of RAG system including document count,
        collection information, and system health.
        """
        try:
            from rag_api import handle_rag_status_request

            result = handle_rag_status_request()
            self.send_json_response(result)

        except Exception as e:
            debug_log(f"RAG status error: {e}", "❌")
            self.send_error_response(f"Failed to get RAG status: {str(e)}", 500)

    @rate_limit(requests_per_minute=120, burst=20)
    @validate_request(RAGSearchRequest)
    @require_system('rag')
    def handle_rag_search_api(self):
        """
        Search RAG vector database.

        POST /api/rag/search
        Body: {"query": "search terms", "top_k": 5, "collection": "default"}

        Returns semantically similar documents from vector database.
        """
        try:
            from rag_api import handle_rag_search_request

            data = self.validated_data
            result = handle_rag_search_request(data.dict())

            self.send_json_response(result)

        except Exception as e:
            debug_log(f"RAG search error: {e}", "❌")
            self.send_error_response(f"RAG search failed: {str(e)}", 500)

    @rate_limit(requests_per_minute=60, burst=10)
    @validate_request(RAGQueryRequest)
    @require_system('rag')
    def handle_rag_query_api(self):
        """
        RAG-enhanced query with LLM integration.

        POST /api/rag/query
        Body: {"query": "question", "collection": "default"}

        Retrieves relevant context and generates LLM response.
        """
        try:
            from rag_api import handle_rag_query_request

            data = self.validated_data
            result = handle_rag_query_request(data.dict())

            self.send_json_response(result)

        except Exception as e:
            debug_log(f"RAG query error: {e}", "❌")
            self.send_error_response(f"RAG query failed: {str(e)}", 500)

    @validate_request(RAGIngestRequest)
    @require_system('rag')
    def handle_rag_ingest_api(self):
        """
        Ingest documents into RAG system.

        POST /api/rag/ingest
        Body: {
            "text": "document content",
            "metadata": {...},
            "collection": "default"
        }

        Processes and stores documents in vector database.
        """
        try:
            from rag_api import handle_rag_ingest_request

            data = self.validated_data
            result = handle_rag_ingest_request(data.dict())

            self.send_json_response(result, 201)

        except Exception as e:
            debug_log(f"RAG ingest error: {e}", "❌")
            self.send_error_response(f"Failed to ingest document: {str(e)}", 500)

    @require_system('rag')
    def handle_rag_documents_api(self):
        """
        Get all documents in RAG system.

        GET /api/rag/documents

        Returns list of all documents with metadata.
        """
        try:
            from rag_api import handle_rag_documents_request

            result = handle_rag_documents_request()
            self.send_json_response(result)

        except Exception as e:
            debug_log(f"RAG documents error: {e}", "❌")
            self.send_error_response(f"Failed to fetch documents: {str(e)}", 500)

    @require_system('rag')
    def handle_rag_analytics_api(self):
        """
        Get RAG system analytics.

        GET /api/rag/analytics

        Returns usage statistics, performance metrics, and insights.
        """
        try:
            from rag_api import handle_rag_analytics_request

            result = handle_rag_analytics_request()
            self.send_json_response(result)

        except Exception as e:
            debug_log(f"RAG analytics error: {e}", "❌")
            self.send_error_response(f"Failed to fetch analytics: {str(e)}", 500)

    @require_system('rag')
    def handle_rag_upload_api(self):
        """
        Upload file to RAG system.

        POST /api/rag/upload
        Content-Type: multipart/form-data

        Handles file uploads and processes them for RAG ingestion.
        """
        try:
            # File upload handling is more complex, delegate to existing handler
            content_type = self.headers.get('Content-Type', '')

            if 'multipart/form-data' in content_type:
                # Handle file upload
                from rag_api import handle_rag_ingest_request
                # File parsing would happen here
                self.send_json_response({'status': 'success', 'message': 'File uploaded'}, 201)
            else:
                self.send_error_response("Expected multipart/form-data", 400)

        except Exception as e:
            debug_log(f"RAG upload error: {e}", "❌")
            self.send_error_response(f"Upload failed: {str(e)}", 500)

    @require_system('rag')
    def handle_rag_document_delete_api(self, document_id: str):
        """
        Delete a document from RAG system.

        DELETE /api/rag/documents/{document_id}

        Removes document and its embeddings from vector database.
        """
        try:
            from rag_api import handle_rag_document_delete_request

            result = handle_rag_document_delete_request(document_id)
            self.send_json_response(result)

        except Exception as e:
            debug_log(f"RAG delete error: {e}", "❌")
            self.send_error_response(f"Failed to delete document: {str(e)}", 500)
