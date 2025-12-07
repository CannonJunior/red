"""
Prompts API Module - MCP-integrated prompt management system.

This module provides zero-cost, local prompt storage and retrieval
for the RAG system with Model Context Protocol (MCP) integration.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid


class PromptsManager:
    """
    Manages prompts storage and retrieval with MCP integration.

    Zero-cost local JSON storage for 5-user scale.
    """

    def __init__(self, storage_path: str = "prompts_storage.json"):
        """
        Initialize the prompts manager.

        Args:
            storage_path (str): Path to JSON storage file.
        """
        self.storage_path = Path(storage_path)
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, dict]:
        """
        Load prompts from JSON storage.

        Returns:
            dict: Dictionary of prompts keyed by prompt_id.
        """
        if not self.storage_path.exists():
            # Initialize with empty storage
            self._save_prompts({})
            return {}

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Error loading prompts: {e}, initializing empty storage")
            return {}

    def _save_prompts(self, prompts: Dict[str, dict]) -> None:
        """
        Save prompts to JSON storage.

        Args:
            prompts (dict): Dictionary of prompts to save.
        """
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(prompts, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"❌ Error saving prompts: {e}")

    def create_prompt(self, name: str, content: str, description: str = "",
                     tags: List[str] = None, mcp_enabled: bool = True) -> Dict:
        """
        Create a new prompt.

        Args:
            name (str): Prompt name (used for /name quick-reference).
            content (str): The actual prompt content/template.
            description (str): Description of what the prompt does.
            tags (list): Tags for categorization.
            mcp_enabled (bool): Whether this prompt is available via MCP.

        Returns:
            dict: Created prompt data with status.
        """
        # Validate name (no spaces, alphanumeric + underscores only)
        if not name or not name.replace('_', '').isalnum():
            return {
                'status': 'error',
                'message': 'Prompt name must be alphanumeric (underscores allowed, no spaces)'
            }

        # Check if prompt name already exists
        for prompt_id, prompt in self.prompts.items():
            if prompt.get('name', '').lower() == name.lower():
                return {
                    'status': 'error',
                    'message': f'Prompt with name "{name}" already exists'
                }

        # Generate unique ID
        prompt_id = str(uuid.uuid4())

        # Create prompt object
        prompt_data = {
            'id': prompt_id,
            'name': name,
            'content': content,
            'description': description or f'Custom prompt: {name}',
            'tags': tags or [],
            'mcp_enabled': mcp_enabled,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'usage_count': 0,
            'last_used': None
        }

        # Save to storage
        self.prompts[prompt_id] = prompt_data
        self._save_prompts(self.prompts)

        print(f"✅ Created prompt: {name} ({prompt_id})")

        return {
            'status': 'success',
            'message': f'Prompt "{name}" created successfully',
            'data': prompt_data
        }

    def get_prompt(self, prompt_id: Optional[str] = None, name: Optional[str] = None) -> Dict:
        """
        Retrieve a prompt by ID or name.

        Args:
            prompt_id (str): Prompt ID.
            name (str): Prompt name.

        Returns:
            dict: Prompt data or error.
        """
        if prompt_id:
            if prompt_id in self.prompts:
                return {
                    'status': 'success',
                    'data': self.prompts[prompt_id]
                }
            return {
                'status': 'error',
                'message': f'Prompt with ID "{prompt_id}" not found'
            }

        if name:
            for prompt_id, prompt in self.prompts.items():
                if prompt.get('name', '').lower() == name.lower():
                    return {
                        'status': 'success',
                        'data': prompt
                    }
            return {
                'status': 'error',
                'message': f'Prompt with name "{name}" not found'
            }

        return {
            'status': 'error',
            'message': 'Either prompt_id or name is required'
        }

    def list_prompts(self, tags: List[str] = None, mcp_only: bool = False) -> Dict:
        """
        List all prompts with optional filtering.

        Args:
            tags (list): Filter by tags.
            mcp_only (bool): Only return MCP-enabled prompts.

        Returns:
            dict: List of prompts.
        """
        prompts_list = []

        for prompt_id, prompt in self.prompts.items():
            # Apply filters
            if mcp_only and not prompt.get('mcp_enabled', False):
                continue

            if tags:
                prompt_tags = set(prompt.get('tags', []))
                if not set(tags).intersection(prompt_tags):
                    continue

            prompts_list.append(prompt)

        # Sort by usage count (most used first), then by name
        prompts_list.sort(key=lambda p: (-p.get('usage_count', 0), p.get('name', '')))

        return {
            'status': 'success',
            'count': len(prompts_list),
            'prompts': prompts_list
        }

    def update_prompt(self, prompt_id: str, name: Optional[str] = None,
                     content: Optional[str] = None, description: Optional[str] = None,
                     tags: Optional[List[str]] = None, mcp_enabled: Optional[bool] = None) -> Dict:
        """
        Update an existing prompt.

        Args:
            prompt_id (str): Prompt ID to update.
            name (str): New name (optional).
            content (str): New content (optional).
            description (str): New description (optional).
            tags (list): New tags (optional).
            mcp_enabled (bool): MCP enablement status (optional).

        Returns:
            dict: Updated prompt data or error.
        """
        if prompt_id not in self.prompts:
            return {
                'status': 'error',
                'message': f'Prompt with ID "{prompt_id}" not found'
            }

        prompt = self.prompts[prompt_id]

        # Update fields
        if name is not None:
            # Validate name
            if not name or not name.replace('_', '').isalnum():
                return {
                    'status': 'error',
                    'message': 'Prompt name must be alphanumeric (underscores allowed, no spaces)'
                }

            # Check for name conflicts (excluding current prompt)
            for pid, p in self.prompts.items():
                if pid != prompt_id and p.get('name', '').lower() == name.lower():
                    return {
                        'status': 'error',
                        'message': f'Prompt with name "{name}" already exists'
                    }

            prompt['name'] = name

        if content is not None:
            prompt['content'] = content

        if description is not None:
            prompt['description'] = description

        if tags is not None:
            prompt['tags'] = tags

        if mcp_enabled is not None:
            prompt['mcp_enabled'] = mcp_enabled

        prompt['updated_at'] = datetime.now().isoformat()

        self._save_prompts(self.prompts)

        print(f"✅ Updated prompt: {prompt['name']} ({prompt_id})")

        return {
            'status': 'success',
            'message': f'Prompt "{prompt["name"]}" updated successfully',
            'data': prompt
        }

    def delete_prompt(self, prompt_id: str) -> Dict:
        """
        Delete a prompt.

        Args:
            prompt_id (str): Prompt ID to delete.

        Returns:
            dict: Status message.
        """
        if prompt_id not in self.prompts:
            return {
                'status': 'error',
                'message': f'Prompt with ID "{prompt_id}" not found'
            }

        prompt_name = self.prompts[prompt_id].get('name', 'Unknown')
        del self.prompts[prompt_id]
        self._save_prompts(self.prompts)

        print(f"🗑️  Deleted prompt: {prompt_name} ({prompt_id})")

        return {
            'status': 'success',
            'message': f'Prompt "{prompt_name}" deleted successfully'
        }

    def use_prompt(self, prompt_id: Optional[str] = None, name: Optional[str] = None) -> Dict:
        """
        Mark a prompt as used and return its content.

        Args:
            prompt_id (str): Prompt ID.
            name (str): Prompt name.

        Returns:
            dict: Prompt content and metadata.
        """
        result = self.get_prompt(prompt_id=prompt_id, name=name)

        if result['status'] == 'success':
            prompt = result['data']
            prompt_id = prompt['id']

            # Update usage statistics
            self.prompts[prompt_id]['usage_count'] = prompt.get('usage_count', 0) + 1
            self.prompts[prompt_id]['last_used'] = datetime.now().isoformat()
            self._save_prompts(self.prompts)

            return {
                'status': 'success',
                'data': {
                    'id': prompt['id'],
                    'name': prompt['name'],
                    'content': prompt['content'],
                    'description': prompt['description']
                }
            }

        return result

    def search_prompts(self, query: str) -> Dict:
        """
        Search prompts by name, description, or tags.

        Args:
            query (str): Search query.

        Returns:
            dict: List of matching prompts.
        """
        query_lower = query.lower()
        matching_prompts = []

        for prompt_id, prompt in self.prompts.items():
            # Search in name, description, and tags
            if (query_lower in prompt.get('name', '').lower() or
                query_lower in prompt.get('description', '').lower() or
                any(query_lower in tag.lower() for tag in prompt.get('tags', []))):
                matching_prompts.append(prompt)

        # Sort by relevance (name match > description match > tag match)
        def relevance_score(p):
            score = 0
            if query_lower in p.get('name', '').lower():
                score += 10
            if query_lower in p.get('description', '').lower():
                score += 5
            if any(query_lower in tag.lower() for tag in p.get('tags', [])):
                score += 2
            return -score  # Negative for descending sort

        matching_prompts.sort(key=relevance_score)

        return {
            'status': 'success',
            'count': len(matching_prompts),
            'prompts': matching_prompts
        }


# Global prompts manager instance (singleton for 5-user optimization)
_prompts_manager = None


def get_prompts_manager() -> PromptsManager:
    """
    Get the global prompts manager instance.

    Returns:
        PromptsManager: Global prompts manager instance.
    """
    global _prompts_manager
    if _prompts_manager is None:
        _prompts_manager = PromptsManager()
    return _prompts_manager


# API handler functions for server.py integration

def handle_prompts_list_request(query_params: dict = None) -> dict:
    """Handle GET /api/prompts - List all prompts."""
    manager = get_prompts_manager()
    tags = query_params.get('tags', []) if query_params else []
    mcp_only = query_params.get('mcp_only', False) if query_params else False

    return manager.list_prompts(tags=tags, mcp_only=mcp_only)


def handle_prompts_create_request(data: dict) -> dict:
    """Handle POST /api/prompts - Create new prompt."""
    manager = get_prompts_manager()

    name = data.get('name', '').strip()
    content = data.get('content', '').strip()
    description = data.get('description', '').strip()
    tags = data.get('tags', [])
    mcp_enabled = data.get('mcp_enabled', True)

    if not name:
        return {'status': 'error', 'message': 'Prompt name is required'}

    if not content:
        return {'status': 'error', 'message': 'Prompt content is required'}

    return manager.create_prompt(name, content, description, tags, mcp_enabled)


def handle_prompts_get_request(prompt_id: str) -> dict:
    """Handle GET /api/prompts/{prompt_id} - Get prompt by ID."""
    manager = get_prompts_manager()
    return manager.get_prompt(prompt_id=prompt_id)


def handle_prompts_update_request(prompt_id: str, data: dict) -> dict:
    """Handle PUT /api/prompts/{prompt_id} - Update prompt."""
    manager = get_prompts_manager()

    return manager.update_prompt(
        prompt_id=prompt_id,
        name=data.get('name'),
        content=data.get('content'),
        description=data.get('description'),
        tags=data.get('tags'),
        mcp_enabled=data.get('mcp_enabled')
    )


def handle_prompts_delete_request(prompt_id: str) -> dict:
    """Handle DELETE /api/prompts/{prompt_id} - Delete prompt."""
    manager = get_prompts_manager()
    return manager.delete_prompt(prompt_id)


def handle_prompts_use_request(data: dict) -> dict:
    """Handle POST /api/prompts/use - Use a prompt (for quick-reference)."""
    manager = get_prompts_manager()

    prompt_id = data.get('prompt_id')
    name = data.get('name')

    if not prompt_id and not name:
        return {'status': 'error', 'message': 'Either prompt_id or name is required'}

    return manager.use_prompt(prompt_id=prompt_id, name=name)


def handle_prompts_search_request(data: dict) -> dict:
    """Handle POST /api/prompts/search - Search prompts."""
    manager = get_prompts_manager()

    query = data.get('query', '').strip()

    if not query:
        return {'status': 'error', 'message': 'Search query is required'}

    return manager.search_prompts(query)
