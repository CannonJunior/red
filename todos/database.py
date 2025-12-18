"""Database operations for TODO list feature."""

import sqlite3
import json
from typing import Dict, List, Optional
from pathlib import Path

from .config import TODOS_DB_PATH


class TodoDatabase:
    """Handle all database operations for todos."""

    def __init__(self, db_path: str = TODOS_DB_PATH):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema and indexes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Todo Lists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todo_lists (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                color TEXT DEFAULT '#3B82F6',
                icon TEXT DEFAULT 'list',
                is_shared INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Todos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id TEXT PRIMARY KEY,
                list_id TEXT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                due_time TEXT,
                reminder_date TEXT,
                reminder_time TEXT,
                bucket TEXT DEFAULT 'inbox',
                tags TEXT,
                subtasks TEXT,
                parent_id TEXT,
                assigned_to TEXT,
                recurrence TEXT,
                position INTEGER DEFAULT 0,
                metadata TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (list_id) REFERENCES todo_lists(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES todos(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#6B7280',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        """)

        # Todo history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todo_history (
                id TEXT PRIMARY KEY,
                todo_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                changes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (todo_id) REFERENCES todos(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Shared lists access table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS list_shares (
                id TEXT PRIMARY KEY,
                list_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                permission TEXT DEFAULT 'view',
                created_at TEXT NOT NULL,
                FOREIGN KEY (list_id) REFERENCES todo_lists(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(list_id, user_id)
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_user ON todos(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_list ON todos(list_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos(due_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_bucket ON todos(bucket)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_assigned ON todos(assigned_to)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todo_lists_user ON todo_lists(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_user ON tags(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_todo ON todo_history(todo_id, created_at DESC)")

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # User operations
    def create_user(self, user_data: Dict) -> Dict:
        """Create a new user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (id, username, email, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_data['id'],
                user_data['username'],
                user_data['email'],
                user_data.get('display_name'),
                user_data['created_at'],
                user_data['updated_at']
            ))
            conn.commit()
            return {'status': 'success', 'user': user_data}
        except sqlite3.IntegrityError as e:
            return {'status': 'error', 'message': f'User already exists: {str(e)}'}
        finally:
            conn.close()

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def list_users(self) -> List[Dict]:
        """List all users."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_user(self, user_id: str, updates: Dict) -> Dict:
        """Update a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            set_clauses = []
            params = []

            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)

            params.append(user_id)
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"

            cursor.execute(query, params)
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to update user: {str(e)}'}
        finally:
            conn.close()

    def delete_user(self, user_id: str) -> Dict:
        """Delete a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to delete user: {str(e)}'}
        finally:
            conn.close()

    # Todo List operations
    def create_todo_list(self, list_data: Dict) -> Dict:
        """Create a new todo list."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO todo_lists
                (id, user_id, name, description, color, icon, is_shared, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                list_data['id'],
                list_data['user_id'],
                list_data['name'],
                list_data.get('description'),
                list_data.get('color', '#3B82F6'),
                list_data.get('icon', 'list'),
                list_data.get('is_shared', False),
                json.dumps(list_data.get('metadata', {})),
                list_data['created_at'],
                list_data['updated_at']
            ))
            conn.commit()
            return {'status': 'success', 'list': list_data}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to create list: {str(e)}'}
        finally:
            conn.close()

    def get_todo_list(self, list_id: str) -> Optional[Dict]:
        """Get todo list by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM todo_lists WHERE id = ?", (list_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            data = dict(row)
            data['metadata'] = json.loads(data.get('metadata', '{}'))
            data['is_shared'] = bool(data.get('is_shared', 0))
            return data
        return None

    def list_todo_lists(self, user_id: str) -> List[Dict]:
        """List all todo lists for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                tl.*,
                COUNT(t.id) as total_tasks
            FROM todo_lists tl
            LEFT JOIN todos t ON t.list_id = tl.id
            WHERE tl.user_id = ?
            GROUP BY tl.id
            ORDER BY tl.created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            data = dict(row)
            data['metadata'] = json.loads(data.get('metadata', '{}'))
            data['is_shared'] = bool(data.get('is_shared', 0))
            result.append(data)
        return result

    def update_todo_list(self, list_id: str, updates: Dict) -> Dict:
        """Update a todo list."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            set_clauses = []
            params = []

            for key, value in updates.items():
                if key in ['metadata'] and isinstance(value, dict):
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ?")
                params.append(value)

            params.append(list_id)
            query = f"UPDATE todo_lists SET {', '.join(set_clauses)} WHERE id = ?"

            cursor.execute(query, params)
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to update list: {str(e)}'}
        finally:
            conn.close()

    def delete_todo_list(self, list_id: str) -> Dict:
        """Delete a todo list."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM todo_lists WHERE id = ?", (list_id,))
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to delete list: {str(e)}'}
        finally:
            conn.close()

    # Todo operations
    def create_todo(self, todo_data: Dict) -> Dict:
        """Create a new todo."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO todos
                (id, list_id, user_id, title, description, status, priority,
                 due_date, due_time, reminder_date, reminder_time, bucket,
                 tags, subtasks, parent_id, assigned_to, recurrence, position,
                 metadata, completed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                todo_data['id'],
                todo_data.get('list_id'),
                todo_data['user_id'],
                todo_data['title'],
                todo_data.get('description'),
                todo_data.get('status', 'pending'),
                todo_data.get('priority', 'medium'),
                todo_data.get('due_date'),
                todo_data.get('due_time'),
                todo_data.get('reminder_date'),
                todo_data.get('reminder_time'),
                todo_data.get('bucket', 'inbox'),
                json.dumps(todo_data.get('tags', [])),
                json.dumps(todo_data.get('subtasks', [])),
                todo_data.get('parent_id'),
                todo_data.get('assigned_to'),
                todo_data.get('recurrence'),
                todo_data.get('position', 0),
                json.dumps(todo_data.get('metadata', {})),
                todo_data.get('completed_at'),
                todo_data['created_at'],
                todo_data['updated_at']
            ))
            conn.commit()
            return {'status': 'success', 'todo': todo_data}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to create todo: {str(e)}'}
        finally:
            conn.close()

    def get_todo(self, todo_id: str) -> Optional[Dict]:
        """Get todo by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._parse_todo_row(row)
        return None

    def list_todos(self, user_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """List todos for a user with optional filters."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM todos WHERE user_id = ?"
        params = [user_id]

        if filters:
            if filters.get('list_id'):
                query += " AND list_id = ?"
                params.append(filters['list_id'])
            if filters.get('status'):
                query += " AND status = ?"
                params.append(filters['status'])
            if filters.get('bucket'):
                query += " AND bucket = ?"
                params.append(filters['bucket'])
            if filters.get('assigned_to'):
                query += " AND assigned_to = ?"
                params.append(filters['assigned_to'])

        query += " ORDER BY position ASC, created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._parse_todo_row(row) for row in rows]

    def update_todo(self, todo_id: str, updates: Dict) -> Dict:
        """Update a todo."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Build dynamic update query
            set_clauses = []
            params = []

            for key, value in updates.items():
                if key in ['tags', 'subtasks', 'metadata'] and isinstance(value, (list, dict)):
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ?")
                params.append(value)

            params.append(todo_id)
            query = f"UPDATE todos SET {', '.join(set_clauses)} WHERE id = ?"

            cursor.execute(query, params)
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to update todo: {str(e)}'}
        finally:
            conn.close()

    def delete_todo(self, todo_id: str) -> Dict:
        """Delete a todo."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to delete todo: {str(e)}'}
        finally:
            conn.close()

    def _parse_todo_row(self, row: sqlite3.Row) -> Dict:
        """Parse a todo row from database."""
        data = dict(row)
        data['tags'] = json.loads(data.get('tags', '[]'))
        data['subtasks'] = json.loads(data.get('subtasks', '[]'))
        data['metadata'] = json.loads(data.get('metadata', '{}'))
        return data

    # Tag operations
    def create_tag(self, tag_data: Dict) -> Dict:
        """Create a new tag."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO tags (id, user_id, name, color, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tag_data['id'],
                tag_data['user_id'],
                tag_data['name'],
                tag_data.get('color', '#6B7280'),
                tag_data['created_at']
            ))
            conn.commit()
            return {'status': 'success', 'tag': tag_data}
        except sqlite3.IntegrityError:
            return {'status': 'error', 'message': 'Tag already exists'}
        finally:
            conn.close()

    def list_tags(self, user_id: str) -> List[Dict]:
        """List all tags for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tags
            WHERE user_id = ?
            ORDER BY name ASC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_tag(self, tag_id: str) -> Optional[Dict]:
        """Get tag by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def update_tag(self, tag_id: str, updates: Dict) -> Dict:
        """Update a tag."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            set_clauses = []
            params = []

            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)

            params.append(tag_id)
            query = f"UPDATE tags SET {', '.join(set_clauses)} WHERE id = ?"

            cursor.execute(query, params)
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to update tag: {str(e)}'}
        finally:
            conn.close()

    def delete_tag(self, tag_id: str) -> Dict:
        """Delete a tag."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to delete tag: {str(e)}'}
        finally:
            conn.close()

    # List sharing operations
    def share_list(self, share_data: Dict) -> Dict:
        """Share a list with a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO list_shares (id, list_id, user_id, permission, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                share_data['id'],
                share_data['list_id'],
                share_data['user_id'],
                share_data.get('permission', 'view'),
                share_data['created_at']
            ))
            conn.commit()
            return {'status': 'success', 'share': share_data}
        except sqlite3.IntegrityError:
            return {'status': 'error', 'message': 'List already shared with this user'}
        finally:
            conn.close()

    def unshare_list(self, list_id: str, user_id: str) -> Dict:
        """Remove list sharing."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM list_shares
                WHERE list_id = ? AND user_id = ?
            """, (list_id, user_id))
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to unshare list: {str(e)}'}
        finally:
            conn.close()

    def get_list_shares(self, list_id: str) -> List[Dict]:
        """Get all users a list is shared with."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ls.*, u.username, u.email, u.display_name
            FROM list_shares ls
            JOIN users u ON ls.user_id = u.id
            WHERE ls.list_id = ?
            ORDER BY ls.created_at DESC
        """, (list_id,))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_shared_lists(self, user_id: str) -> List[Dict]:
        """Get all lists shared with a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT tl.*, ls.permission, ls.created_at as shared_at
            FROM list_shares ls
            JOIN todo_lists tl ON ls.list_id = tl.id
            WHERE ls.user_id = ?
            ORDER BY ls.created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            data = dict(row)
            data['metadata'] = json.loads(data.get('metadata', '{}'))
            data['is_shared'] = True
            result.append(data)
        return result

    def check_list_permission(self, list_id: str, user_id: str) -> Optional[str]:
        """Check user's permission level for a list."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if owner
        cursor.execute("SELECT user_id FROM todo_lists WHERE id = ?", (list_id,))
        row = cursor.fetchone()
        if row and row[0] == user_id:
            conn.close()
            return 'admin'

        # Check if shared
        cursor.execute("""
            SELECT permission FROM list_shares
            WHERE list_id = ? AND user_id = ?
        """, (list_id, user_id))
        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0]
        return None

    # History operations
    def add_history(self, history_data: Dict) -> Dict:
        """Add a history entry."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO todo_history (id, todo_id, user_id, action, changes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                history_data['id'],
                history_data['todo_id'],
                history_data['user_id'],
                history_data['action'],
                json.dumps(history_data.get('changes', {})),
                history_data['created_at']
            ))
            conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to add history: {str(e)}'}
        finally:
            conn.close()

    def get_todo_history(self, todo_id: str) -> List[Dict]:
        """Get history for a todo."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM todo_history
            WHERE todo_id = ?
            ORDER BY created_at DESC
        """, (todo_id,))
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            data = dict(row)
            data['changes'] = json.loads(data.get('changes', '{}'))
            result.append(data)
        return result
