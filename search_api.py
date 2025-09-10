"""
Search API Integration for Robobrain Server
Provides REST API endpoints for the Universal Search System.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from search_system import (
    UniversalSearchSystem, SearchFilter, SearchableObject, 
    Folder, Tag, ObjectType
)

# Configure logging
logger = logging.getLogger(__name__)

# Global search system instance
search_system = None

def init_search_system():
    """Initialize the search system."""
    global search_system
    if search_system is None:
        search_system = UniversalSearchSystem()
        logger.info("Search system initialized")
    return search_system

def handle_search_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle universal search API requests."""
    try:
        system = init_search_system()
        
        # Parse search parameters
        query = request_data.get('query', '')
        object_types = request_data.get('object_types', [])
        tags = request_data.get('tags', [])
        folder_ids = request_data.get('folder_ids', [])
        is_pinned = request_data.get('is_pinned')
        is_shared = request_data.get('is_shared')
        is_archived = request_data.get('is_archived')
        author = request_data.get('author')
        date_from = request_data.get('date_from')
        date_to = request_data.get('date_to')
        limit = request_data.get('limit', 50)
        offset = request_data.get('offset', 0)
        
        # Parse smart search if query contains prefixes
        if any(prefix in query for prefix in ['pinned:', 'shared:', 'archived:', 'type:', 'tag:', 'folder:']):
            search_filter = system.parse_smart_search(query)
        else:
            # Convert object types from strings to enums
            parsed_object_types = []
            for obj_type in object_types:
                try:
                    parsed_object_types.append(ObjectType(obj_type))
                except ValueError:
                    continue
            
            # Parse dates
            parsed_date_from = None
            parsed_date_to = None
            if date_from:
                try:
                    parsed_date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                except:
                    pass
            if date_to:
                try:
                    parsed_date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                except:
                    pass
            
            search_filter = SearchFilter(
                query=query,
                object_types=parsed_object_types if parsed_object_types else None,
                tags=tags if tags else None,
                folder_ids=folder_ids if folder_ids else None,
                is_pinned=is_pinned,
                is_shared=is_shared,
                is_archived=is_archived,
                author=author,
                date_from=parsed_date_from,
                date_to=parsed_date_to,
                limit=limit,
                offset=offset
            )
        
        # Perform search
        results = system.search(search_filter)
        
        return {
            "status": "success",
            "data": results
        }
        
    except Exception as e:
        logger.error(f"Search API error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def handle_folders_request() -> Dict[str, Any]:
    """Handle folders listing API request."""
    try:
        system = init_search_system()
        folders = system.get_folders()
        
        return {
            "status": "success",
            "folders": folders
        }
        
    except Exception as e:
        logger.error(f"Folders API error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def handle_create_folder_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle folder creation API request."""
    try:
        system = init_search_system()
        
        # Parse folder data
        folder = Folder(
            id=request_data.get('id', f"folder_{datetime.now().timestamp()}"),
            name=request_data.get('name', ''),
            parent_id=request_data.get('parent_id'),
            color=request_data.get('color', '#3B82F6'),
            icon=request_data.get('icon', 'folder'),
            object_types=[ObjectType(t) for t in request_data.get('object_types', [])],
            is_shared=request_data.get('is_shared', False)
        )
        
        success = system.create_folder(folder)
        
        if success:
            return {
                "status": "success",
                "folder": {
                    "id": folder.id,
                    "name": folder.name,
                    "parent_id": folder.parent_id,
                    "color": folder.color,
                    "icon": folder.icon,
                    "object_types": [t.value for t in folder.object_types],
                    "is_shared": folder.is_shared,
                    "created_date": folder.created_date.isoformat()
                }
            }
        else:
            return {
                "status": "error",
                "message": "Failed to create folder"
            }
        
    except Exception as e:
        logger.error(f"Create folder API error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def handle_tags_request() -> Dict[str, Any]:
    """Handle tags listing API request."""
    try:
        system = init_search_system()
        tags = system.get_tags()
        
        return {
            "status": "success",
            "tags": tags
        }
        
    except Exception as e:
        logger.error(f"Tags API error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def handle_add_object_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle adding a searchable object API request."""
    try:
        system = init_search_system()
        
        # Parse object data
        obj = SearchableObject(
            id=request_data.get('id', ''),
            type=ObjectType(request_data.get('type', 'document')),
            title=request_data.get('title', ''),
            content=request_data.get('content'),
            metadata=request_data.get('metadata', {}),
            tags=request_data.get('tags', []),
            folder_id=request_data.get('folder_id'),
            is_pinned=request_data.get('is_pinned', False),
            is_shared=request_data.get('is_shared', False),
            is_archived=request_data.get('is_archived', False),
            author=request_data.get('author')
        )
        
        success = system.add_object(obj)
        
        if success:
            return {
                "status": "success",
                "message": f"Object {obj.id} added successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to add object"
            }
        
    except Exception as e:
        logger.error(f"Add object API error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def handle_update_object_request(object_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle updating a searchable object API request."""
    try:
        system = init_search_system()
        
        # Get existing object first (simplified for this implementation)
        request_data['id'] = object_id
        return handle_add_object_request(request_data)  # Uses INSERT OR REPLACE
        
    except Exception as e:
        logger.error(f"Update object API error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def handle_delete_object_request(object_id: str) -> Dict[str, Any]:
    """Handle deleting a searchable object API request."""
    try:
        system = init_search_system()
        
        success = system.delete_object(object_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Object {object_id} deleted successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to delete object"
            }
        
    except Exception as e:
        logger.error(f"Delete object API error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def sync_existing_data():
    """Sync existing application data into the search system."""
    try:
        system = init_search_system()
        
        # Sync RAG documents
        try:
            from rag_api import rag_service
            if rag_service.available:
                documents_data = rag_service.get_documents()
                if documents_data.get('status') == 'success':
                    for doc in documents_data.get('documents', []):
                        search_obj = SearchableObject(
                            id=f"rag_doc_{doc.get('id', 'unknown')}",
                            type=ObjectType.DOCUMENT,
                            title=doc.get('name', 'Unknown Document'),
                            content=f"Document type: {doc.get('type', 'Unknown')}. Size: {doc.get('size', 'Unknown')} bytes. Chunks: {doc.get('chunks', 0)}",
                            metadata={
                                'file_type': doc.get('type'),
                                'file_size': doc.get('size'),
                                'chunk_count': doc.get('chunks'),
                                'source_path': doc.get('source_path')
                            },
                            tags=['document', 'rag-system'],
                            created_date=datetime.fromisoformat(doc.get('uploadDate', datetime.now().isoformat())),
                            is_shared=False,
                            author='system'
                        )
                        system.add_object(search_obj)
                        logger.info(f"Synced RAG document: {search_obj.title}")
        except Exception as e:
            logger.warning(f"Could not sync RAG documents: {e}")
        
        # Add sample chat objects for demonstration
        sample_chats = [
            {
                'id': 'chat_sample_1',
                'title': 'Introduction to Machine Learning',
                'content': 'A comprehensive discussion about machine learning fundamentals, neural networks, and AI applications.',
                'tags': ['ai', 'machine-learning', 'education'],
                'is_pinned': True
            },
            {
                'id': 'chat_sample_2', 
                'title': 'Project Planning Discussion',
                'content': 'Detailed conversation about project requirements, timelines, and resource allocation.',
                'tags': ['project', 'planning', 'work'],
                'folder_id': 'folder_work'
            }
        ]
        
        for chat_data in sample_chats:
            search_obj = SearchableObject(
                id=chat_data['id'],
                type=ObjectType.CHAT,
                title=chat_data['title'],
                content=chat_data['content'],
                tags=chat_data['tags'],
                folder_id=chat_data.get('folder_id'),
                is_pinned=chat_data.get('is_pinned', False),
                author='user'
            )
            system.add_object(search_obj)
            logger.info(f"Synced sample chat: {search_obj.title}")
        
        # Create sample folders
        sample_folders = [
            {
                'id': 'folder_work',
                'name': 'Work Projects',
                'color': '#10B981',
                'icon': 'briefcase',
                'object_types': [ObjectType.CHAT, ObjectType.DOCUMENT, ObjectType.PROJECT]
            },
            {
                'id': 'folder_personal',
                'name': 'Personal',
                'color': '#8B5CF6',
                'icon': 'user',
                'object_types': [ObjectType.CHAT, ObjectType.DOCUMENT]
            }
        ]
        
        for folder_data in sample_folders:
            folder = Folder(
                id=folder_data['id'],
                name=folder_data['name'],
                color=folder_data['color'],
                icon=folder_data['icon'],
                object_types=folder_data['object_types']
            )
            system.create_folder(folder)
            logger.info(f"Created sample folder: {folder.name}")
        
        logger.info("Data synchronization completed")
        
    except Exception as e:
        logger.error(f"Data sync error: {e}")

# Auto-sync data when module is imported
def initialize_search_api():
    """Initialize the search API and sync existing data."""
    try:
        init_search_system()
        sync_existing_data()
        logger.info("Search API initialized successfully")
    except Exception as e:
        logger.error(f"Search API initialization error: {e}")

# Initialize when imported
initialize_search_api()