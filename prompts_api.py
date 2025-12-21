"""
Prompts API Module - MCP-integrated prompt management system.

This module provides zero-cost, local prompt storage and retrieval
for the RAG system with Model Context Protocol (MCP) integration.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid


class PromptsManager:
    """
    Manages prompts storage and retrieval with MCP integration.

    Zero-cost local SQLite database storage for 5-user scale.
    """

    def __init__(self, db_path: str = "search_system.db"):
        """
        Initialize the prompts manager.

        Args:
            db_path (str): Path to SQLite database file.
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize prompts table in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create prompts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                mcp_enabled INTEGER DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompts_name
            ON prompts(name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompts_usage
            ON prompts(usage_count DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompts_created
            ON prompts(created_at DESC)
        """)

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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

        try:
            # Generate unique ID
            prompt_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            tags_json = json.dumps(tags or [])

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO prompts
                (id, name, content, description, tags, mcp_enabled, usage_count, last_used, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (prompt_id, name, content, description or f'Custom prompt: {name}',
                  tags_json, 1 if mcp_enabled else 0, 0, None, now, now))

            conn.commit()
            conn.close()

            print(f"✅ Created prompt: {name} ({prompt_id})")

            return {
                'status': 'success',
                'message': f'Prompt "{name}" created successfully',
                'data': {
                    'id': prompt_id,
                    'name': name,
                    'content': content,
                    'description': description or f'Custom prompt: {name}',
                    'tags': tags or [],
                    'mcp_enabled': mcp_enabled,
                    'usage_count': 0,
                    'last_used': None,
                    'created_at': now,
                    'updated_at': now
                }
            }

        except sqlite3.IntegrityError:
            return {
                'status': 'error',
                'message': f'Prompt with name "{name}" already exists'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create prompt: {str(e)}'
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
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if prompt_id:
                cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
            elif name:
                cursor.execute("SELECT * FROM prompts WHERE LOWER(name) = LOWER(?)", (name,))
            else:
                return {
                    'status': 'error',
                    'message': 'Either prompt_id or name is required'
                }

            row = cursor.fetchone()
            conn.close()

            if not row:
                identifier = prompt_id or name
                return {
                    'status': 'error',
                    'message': f'Prompt with {"ID" if prompt_id else "name"} "{identifier}" not found'
                }

            return {
                'status': 'success',
                'data': {
                    'id': row['id'],
                    'name': row['name'],
                    'content': row['content'],
                    'description': row['description'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'mcp_enabled': bool(row['mcp_enabled']),
                    'usage_count': row['usage_count'],
                    'last_used': row['last_used'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get prompt: {str(e)}'
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
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM prompts"
            params = []

            if mcp_only:
                query += " WHERE mcp_enabled = 1"

            query += " ORDER BY usage_count DESC, name ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            prompts_list = []
            for row in rows:
                prompt_data = {
                    'id': row['id'],
                    'name': row['name'],
                    'content': row['content'],
                    'description': row['description'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'mcp_enabled': bool(row['mcp_enabled']),
                    'usage_count': row['usage_count'],
                    'last_used': row['last_used'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }

                # Apply tag filter
                if tags:
                    prompt_tags = set(prompt_data['tags'])
                    if not set(tags).intersection(prompt_tags):
                        continue

                prompts_list.append(prompt_data)

            return {
                'status': 'success',
                'count': len(prompts_list),
                'prompts': prompts_list
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to list prompts: {str(e)}',
                'count': 0,
                'prompts': []
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
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check if prompt exists
            cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                return {
                    'status': 'error',
                    'message': f'Prompt with ID "{prompt_id}" not found'
                }

            # Validate name if provided
            if name is not None:
                if not name or not name.replace('_', '').isalnum():
                    conn.close()
                    return {
                        'status': 'error',
                        'message': 'Prompt name must be alphanumeric (underscores allowed, no spaces)'
                    }

                # Check for name conflicts (excluding current prompt)
                cursor.execute("SELECT id FROM prompts WHERE LOWER(name) = LOWER(?) AND id != ?", (name, prompt_id))
                conflict = cursor.fetchone()
                if conflict:
                    conn.close()
                    return {
                        'status': 'error',
                        'message': f'Prompt with name "{name}" already exists'
                    }

            # Build update query
            update_fields = []
            update_values = []

            if name is not None:
                update_fields.append("name = ?")
                update_values.append(name)

            if content is not None:
                update_fields.append("content = ?")
                update_values.append(content)

            if description is not None:
                update_fields.append("description = ?")
                update_values.append(description)

            if tags is not None:
                update_fields.append("tags = ?")
                update_values.append(json.dumps(tags))

            if mcp_enabled is not None:
                update_fields.append("mcp_enabled = ?")
                update_values.append(1 if mcp_enabled else 0)

            if not update_fields:
                conn.close()
                return {'status': 'error', 'message': 'No fields to update'}

            update_fields.append("updated_at = ?")
            update_values.append(datetime.now().isoformat())

            update_values.append(prompt_id)

            cursor.execute(f"""
                UPDATE prompts
                SET {', '.join(update_fields)}
                WHERE id = ?
            """, update_values)

            conn.commit()
            conn.close()

            print(f"✅ Updated prompt: {name or row['name']} ({prompt_id})")

            return self.get_prompt(prompt_id=prompt_id)

        except sqlite3.IntegrityError:
            return {
                'status': 'error',
                'message': f'Prompt with name "{name}" already exists'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to update prompt: {str(e)}'
            }

    def delete_prompt(self, prompt_id: str) -> Dict:
        """
        Delete a prompt.

        Args:
            prompt_id (str): Prompt ID to delete.

        Returns:
            dict: Status message.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get prompt name before deleting
            cursor.execute("SELECT name FROM prompts WHERE id = ?", (prompt_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                return {
                    'status': 'error',
                    'message': f'Prompt with ID "{prompt_id}" not found'
                }

            prompt_name = row['name']

            cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

            conn.commit()
            conn.close()

            print(f"🗑️  Deleted prompt: {prompt_name} ({prompt_id})")

            return {
                'status': 'success',
                'message': f'Prompt "{prompt_name}" deleted successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to delete prompt: {str(e)}'
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
            prompt_id_to_update = prompt['id']

            try:
                # Update usage statistics
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE prompts
                    SET usage_count = usage_count + 1,
                        last_used = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), prompt_id_to_update))

                conn.commit()
                conn.close()

                return {
                    'status': 'success',
                    'data': {
                        'id': prompt['id'],
                        'name': prompt['name'],
                        'content': prompt['content'],
                        'description': prompt['description']
                    }
                }

            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Failed to update usage statistics: {str(e)}'
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
        try:
            query_lower = query.lower()
            conn = self._get_connection()
            cursor = conn.cursor()

            # Search in name and description using LIKE
            cursor.execute("""
                SELECT * FROM prompts
                WHERE LOWER(name) LIKE ?
                   OR LOWER(description) LIKE ?
                   OR LOWER(tags) LIKE ?
                ORDER BY
                    CASE
                        WHEN LOWER(name) LIKE ? THEN 1
                        WHEN LOWER(description) LIKE ? THEN 2
                        WHEN LOWER(tags) LIKE ? THEN 3
                        ELSE 4
                    END,
                    usage_count DESC,
                    name ASC
            """, (f'%{query_lower}%', f'%{query_lower}%', f'%{query_lower}%',
                  f'%{query_lower}%', f'%{query_lower}%', f'%{query_lower}%'))

            rows = cursor.fetchall()
            conn.close()

            matching_prompts = []
            for row in rows:
                matching_prompts.append({
                    'id': row['id'],
                    'name': row['name'],
                    'content': row['content'],
                    'description': row['description'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'mcp_enabled': bool(row['mcp_enabled']),
                    'usage_count': row['usage_count'],
                    'last_used': row['last_used'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })

            return {
                'status': 'success',
                'count': len(matching_prompts),
                'prompts': matching_prompts
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to search prompts: {str(e)}',
                'count': 0,
                'prompts': []
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
