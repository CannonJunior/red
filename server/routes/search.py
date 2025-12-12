"""
Search API routes.

Handles universal search functionality including:
- Chat/document search
- Folder management
- Tag management
- Object CRUD operations
"""

from rate_limiter import rate_limit
from request_validation import validate_request, SearchRequest, SearchCreateFolderRequest, SearchAddObjectRequest
from server_decorators import require_system
from debug_logger import debug_log

# Import system availability flags
from server.utils.system import SEARCH_AVAILABLE


class SearchRoutes:
    """Mixin providing search-related routes."""

    @rate_limit(requests_per_minute=120, burst=20)
    @validate_request(SearchRequest)
    @require_system('search')
    def handle_search_api(self):
        """
        Handle universal search API requests.

        POST /api/search
        Body: {"query": "search terms", "filters": {...}}

        Returns search results across chats, documents, and other objects.
        """
        try:
            from search_api import handle_search_request

            data = self.validated_data
            result = handle_search_request(data.dict())

            self.send_json_response(result)

        except Exception as e:
            debug_log(f"Search error: {e}", "❌")
            self.send_error_response(f"Search failed: {str(e)}", 500)

    @require_system('search')
    def handle_search_folders_api(self):
        """
        Get all folders.

        GET /api/search/folders

        Returns list of all folders in the search system.
        """
        try:
            from search_api import handle_folders_request

            result = handle_folders_request()
            self.send_json_response(result)

        except Exception as e:
            debug_log(f"Folders fetch error: {e}", "❌")
            self.send_error_response(f"Failed to fetch folders: {str(e)}", 500)

    @validate_request(SearchCreateFolderRequest)
    @require_system('search')
    def handle_search_create_folder_api(self):
        """
        Create a new folder.

        POST /api/search/folders
        Body: {"name": "folder name", "parent_id": "optional parent"}

        Creates a new folder in the search system.
        """
        try:
            from search_api import handle_create_folder_request

            data = self.validated_data
            result = handle_create_folder_request(data.dict())

            self.send_json_response(result, 201)

        except Exception as e:
            debug_log(f"Folder creation error: {e}", "❌")
            self.send_error_response(f"Failed to create folder: {str(e)}", 500)

    @require_system('search')
    def handle_search_tags_api(self):
        """
        Get all tags.

        GET /api/search/tags

        Returns list of all tags used in the search system.
        """
        try:
            from search_api import handle_tags_request

            result = handle_tags_request()
            self.send_json_response(result)

        except Exception as e:
            debug_log(f"Tags fetch error: {e}", "❌")
            self.send_error_response(f"Failed to fetch tags: {str(e)}", 500)

    @validate_request(SearchAddObjectRequest)
    @require_system('search')
    def handle_search_add_object_api(self):
        """
        Add a new searchable object.

        POST /api/search/objects
        Body: {
            "type": "chat|document|note",
            "title": "object title",
            "content": "object content",
            ...
        }

        Adds a new object to the search index.
        """
        try:
            from search_api import handle_add_object_request

            data = self.validated_data
            result = handle_add_object_request(data.dict())

            self.send_json_response(result, 201)

        except Exception as e:
            debug_log(f"Object add error: {e}", "❌")
            self.send_error_response(f"Failed to add object: {str(e)}", 500)

    @require_system('search')
    def handle_search_delete_object_api(self, object_id: str):
        """
        Delete a searchable object.

        DELETE /api/search/objects/{object_id}

        Removes an object from the search index.
        """
        try:
            from search_api import handle_delete_object_request

            result = handle_delete_object_request(object_id)
            self.send_json_response(result)

        except Exception as e:
            debug_log(f"Object delete error: {e}", "❌")
            self.send_error_response(f"Failed to delete object: {str(e)}", 500)
