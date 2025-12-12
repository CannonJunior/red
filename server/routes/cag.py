"""
CAG (Cache-Augmented Generation) API routes.

Handles CAG system functionality including:
- Context loading and management
- CAG-enhanced queries with cached context
- Cache statistics and monitoring
- Document management in CAG cache
"""

from rate_limiter import rate_limit
from request_validation import validate_request, CAGQueryRequest, CAGLoadRequest
from server_decorators import require_system
from debug_logger import debug_log

# Import system availability flags
from server.utils.system import CAG_AVAILABLE


class CAGRoutes:
    """Mixin providing CAG-related routes."""

    @require_system('cag')
    def handle_cag_status_api(self):
        """
        Get CAG system status.

        GET /api/cag/status

        Returns CAG cache status including:
        - Loaded documents and token count
        - Memory usage
        - Cache hit rate
        - Available capacity
        """
        try:
            from cag_api import get_cag_manager

            cag_manager = get_cag_manager()
            status = cag_manager.get_cache_status()

            self.send_json_response(status)

        except Exception as e:
            debug_log(f"CAG status error: {e}", "❌")
            self.send_error_response(f"Failed to get CAG status: {str(e)}", 500)

    @validate_request(CAGLoadRequest)
    @require_system('cag')
    def handle_cag_load_api(self):
        """
        Load documents into CAG cache.

        POST /api/cag/load
        Body: {
            "document_ids": ["id1", "id2"],
            "text": "optional direct text",
            "max_tokens": 50000
        }

        Loads documents into the CAG context cache for fast retrieval.
        """
        try:
            from cag_api import get_cag_manager

            data = self.validated_data
            cag_manager = get_cag_manager()

            # Load documents into cache
            result = cag_manager.load_context(data.dict())

            self.send_json_response({
                'status': 'success',
                'message': 'Documents loaded into CAG cache',
                'data': result
            })

        except Exception as e:
            debug_log(f"CAG load error: {e}", "❌")
            self.send_error_response(f"Failed to load into CAG: {str(e)}", 500)

    @require_system('cag')
    def handle_cag_clear_api(self):
        """
        Clear CAG cache.

        POST /api/cag/clear

        Removes all documents from CAG cache and frees memory.
        """
        try:
            from cag_api import get_cag_manager

            cag_manager = get_cag_manager()
            cag_manager.clear_cache()

            self.send_json_response({
                'status': 'success',
                'message': 'CAG cache cleared'
            })

        except Exception as e:
            debug_log(f"CAG clear error: {e}", "❌")
            self.send_error_response(f"Failed to clear CAG cache: {str(e)}", 500)

    @require_system('cag')
    def handle_cag_document_delete_api(self, document_id: str):
        """
        Remove specific document from CAG cache.

        DELETE /api/cag/documents/{document_id}

        Removes a single document from the cache.
        """
        try:
            from cag_api import get_cag_manager

            cag_manager = get_cag_manager()
            result = cag_manager.remove_document(document_id)

            self.send_json_response({
                'status': 'success',
                'message': f'Document {document_id} removed from CAG cache',
                'data': result
            })

        except Exception as e:
            debug_log(f"CAG document delete error: {e}", "❌")
            self.send_error_response(f"Failed to delete from CAG: {str(e)}", 500)

    @rate_limit(requests_per_minute=30, burst=5)
    @validate_request(CAGQueryRequest)
    @require_system('cag')
    def handle_cag_query_api(self):
        """
        Query with CAG-enhanced context.

        POST /api/cag/query
        Body: {
            "query": "question",
            "model": "qwen2.5:3b",
            "use_cache": true
        }

        Queries LLM with cached context for faster, context-aware responses.
        This endpoint is rate-limited more strictly due to heavy computation.
        """
        try:
            from cag_api import get_cag_manager

            data = self.validated_data
            cag_manager = get_cag_manager()

            # Query with CAG context
            result = cag_manager.query_with_context(
                query=data.query,
                model=data.model or 'qwen2.5:3b'
            )

            self.send_json_response({
                'status': 'success',
                'data': result
            })

        except Exception as e:
            debug_log(f"CAG query error: {e}", "❌")
            self.send_error_response(f"CAG query failed: {str(e)}", 500)
