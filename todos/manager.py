"""Business logic manager for TODO list feature."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .database import TodoDatabase
from .models import User, TodoList, Todo, Tag, TodoHistory
from .config import (
    VALID_STATUSES, VALID_PRIORITIES, VALID_BUCKETS,
    DEFAULT_STATUS, DEFAULT_PRIORITY, DEFAULT_BUCKET
)


class TodoManager:
    """Manage todo operations with business logic."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize todo manager.

        Args:
            db_path: Optional custom database path
        """
        self.db = TodoDatabase(db_path) if db_path else TodoDatabase()

    # User management
    def create_user(self, username: str, email: str, display_name: Optional[str] = None) -> Dict:
        """
        Create a new user.

        Args:
            username: Unique username
            email: Unique email address
            display_name: Optional display name

        Returns:
            Result dictionary with user data or error
        """
        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        user = User(
            id=user_id,
            username=username,
            email=email,
            display_name=display_name or username,
            created_at=now,
            updated_at=now
        )

        result = self.db.create_user(user.to_dict())
        if result['status'] == 'success':
            return {'status': 'success', 'user': user.to_dict()}
        return result

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        return self.db.get_user(user_id)

    def list_users(self) -> List[Dict]:
        """List all users."""
        return self.db.list_users()

    def update_user(self, user_id: str, updates: Dict) -> Dict:
        """
        Update a user.

        Args:
            user_id: User ID
            updates: Dictionary of fields to update

        Returns:
            Result dictionary
        """
        # Add updated_at timestamp
        updates['updated_at'] = datetime.now().isoformat()

        result = self.db.update_user(user_id, updates)
        return result

    def delete_user(self, user_id: str) -> Dict:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            Result dictionary
        """
        return self.db.delete_user(user_id)

    # Todo List management
    def create_list(self, user_id: str, name: str, description: Optional[str] = None,
                    color: str = '#3B82F6', icon: str = 'list') -> Dict:
        """
        Create a new todo list.

        Args:
            user_id: Owner user ID
            name: List name
            description: Optional description
            color: List color (hex)
            icon: List icon name

        Returns:
            Result dictionary with list data or error
        """
        list_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        todo_list = TodoList(
            id=list_id,
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            icon=icon,
            created_at=now,
            updated_at=now
        )

        result = self.db.create_todo_list(todo_list.to_dict())
        if result['status'] == 'success':
            return {'status': 'success', 'list': todo_list.to_dict()}
        return result

    def get_list(self, list_id: str) -> Optional[Dict]:
        """Get todo list by ID."""
        return self.db.get_todo_list(list_id)

    def list_lists(self, user_id: str) -> List[Dict]:
        """List all todo lists for a user."""
        return self.db.list_todo_lists(user_id)

    def update_list(self, list_id: str, updates: Dict) -> Dict:
        """
        Update a todo list.

        Args:
            list_id: List ID
            updates: Dictionary of fields to update

        Returns:
            Result dictionary
        """
        # Add updated_at timestamp
        updates['updated_at'] = datetime.now().isoformat()

        result = self.db.update_todo_list(list_id, updates)
        return result

    def delete_list(self, list_id: str) -> Dict:
        """
        Delete a todo list.

        Args:
            list_id: List ID

        Returns:
            Result dictionary
        """
        return self.db.delete_todo_list(list_id)

    # Todo management
    def create_todo(self, user_id: str, title: str, **kwargs) -> Dict:
        """
        Create a new todo.

        Args:
            user_id: Owner user ID
            title: Todo title
            **kwargs: Additional todo properties

        Returns:
            Result dictionary with todo data or error
        """
        # Validate status
        status = kwargs.get('status', DEFAULT_STATUS)
        if status not in VALID_STATUSES:
            return {'status': 'error', 'message': f'Invalid status: {status}'}

        # Validate priority
        priority = kwargs.get('priority', DEFAULT_PRIORITY)
        if priority not in VALID_PRIORITIES:
            return {'status': 'error', 'message': f'Invalid priority: {priority}'}

        # Validate bucket
        bucket = kwargs.get('bucket', DEFAULT_BUCKET)
        if bucket not in VALID_BUCKETS:
            return {'status': 'error', 'message': f'Invalid bucket: {bucket}'}

        todo_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        todo = Todo(
            id=todo_id,
            user_id=user_id,
            title=title,
            list_id=kwargs.get('list_id'),
            description=kwargs.get('description'),
            status=status,
            priority=priority,
            due_date=kwargs.get('due_date'),
            due_time=kwargs.get('due_time'),
            reminder_date=kwargs.get('reminder_date'),
            reminder_time=kwargs.get('reminder_time'),
            bucket=bucket,
            tags=kwargs.get('tags', []),
            subtasks=kwargs.get('subtasks', []),
            parent_id=kwargs.get('parent_id'),
            assigned_to=kwargs.get('assigned_to'),
            recurrence=kwargs.get('recurrence'),
            position=kwargs.get('position', 0),
            metadata=kwargs.get('metadata', {}),
            created_at=now,
            updated_at=now
        )

        result = self.db.create_todo(todo.to_dict())
        if result['status'] == 'success':
            # Add history entry
            self._add_history(todo_id, user_id, 'created', {'title': title})
            return {'status': 'success', 'todo': todo.to_dict()}
        return result

    def get_todo(self, todo_id: str) -> Optional[Dict]:
        """Get todo by ID."""
        return self.db.get_todo(todo_id)

    def list_todos(self, user_id: str, filters: Optional[Dict] = None) -> Dict:
        """
        List todos for a user with optional filters.

        Args:
            user_id: User ID
            filters: Optional filters (list_id, status, bucket, assigned_to)

        Returns:
            Dictionary with todos list and count
        """
        todos = self.db.list_todos(user_id, filters)
        return {
            'status': 'success',
            'todos': todos,
            'count': len(todos)
        }

    def update_todo(self, todo_id: str, user_id: str, updates: Dict) -> Dict:
        """
        Update a todo.

        Args:
            todo_id: Todo ID
            user_id: User ID (for history)
            updates: Dictionary of fields to update

        Returns:
            Result dictionary
        """
        # Get existing todo
        existing = self.db.get_todo(todo_id)
        if not existing:
            return {'status': 'error', 'message': 'Todo not found'}

        # Validate updates
        if 'status' in updates and updates['status'] not in VALID_STATUSES:
            return {'status': 'error', 'message': f'Invalid status: {updates["status"]}'}

        if 'priority' in updates and updates['priority'] not in VALID_PRIORITIES:
            return {'status': 'error', 'message': f'Invalid priority: {updates["priority"]}'}

        if 'bucket' in updates and updates['bucket'] not in VALID_BUCKETS:
            return {'status': 'error', 'message': f'Invalid bucket: {updates["bucket"]}'}

        # Add updated_at timestamp
        updates['updated_at'] = datetime.now().isoformat()

        # If marking as completed, add completed_at
        if updates.get('status') == 'completed' and existing.get('status') != 'completed':
            updates['completed_at'] = datetime.now().isoformat()

        result = self.db.update_todo(todo_id, updates)
        if result['status'] == 'success':
            # Add history entry
            self._add_history(todo_id, user_id, 'updated', updates)
            return {'status': 'success', 'todo_id': todo_id, 'updates': updates}
        return result

    def delete_todo(self, todo_id: str, user_id: str) -> Dict:
        """
        Delete a todo.

        Args:
            todo_id: Todo ID
            user_id: User ID (for history)

        Returns:
            Result dictionary
        """
        # Get existing todo for history
        existing = self.db.get_todo(todo_id)
        if not existing:
            return {'status': 'error', 'message': 'Todo not found'}

        # Add history entry before deletion
        self._add_history(todo_id, user_id, 'deleted', {'title': existing['title']})

        result = self.db.delete_todo(todo_id)
        return result

    def complete_todo(self, todo_id: str, user_id: str) -> Dict:
        """
        Mark a todo as completed.

        Args:
            todo_id: Todo ID
            user_id: User ID

        Returns:
            Result dictionary
        """
        now = datetime.now().isoformat()
        updates = {
            'status': 'completed',
            'completed_at': now,
            'updated_at': now
        }

        result = self.db.update_todo(todo_id, updates)
        if result['status'] == 'success':
            self._add_history(todo_id, user_id, 'completed', {})
            return {'status': 'success', 'todo_id': todo_id, 'completed_at': now}
        return result

    def archive_todo(self, todo_id: str, user_id: str) -> Dict:
        """
        Archive a todo.

        Args:
            todo_id: Todo ID
            user_id: User ID

        Returns:
            Result dictionary
        """
        updates = {
            'status': 'archived',
            'updated_at': datetime.now().isoformat()
        }

        result = self.db.update_todo(todo_id, updates)
        if result['status'] == 'success':
            self._add_history(todo_id, user_id, 'archived', {})
            return {'status': 'success', 'todo_id': todo_id}
        return result

    # Smart queries
    def get_today_todos(self, user_id: str) -> Dict:
        """Get todos for today."""
        todos = self.db.list_todos(user_id, {'bucket': 'today'})

        # Also include overdue todos
        all_todos = self.db.list_todos(user_id)
        for todo in all_todos:
            todo_obj = Todo.from_dict(todo)
            if todo_obj.is_overdue() and todo['status'] != 'completed':
                todos.append(todo)

        return {
            'status': 'success',
            'todos': todos,
            'count': len(todos)
        }

    def get_upcoming_todos(self, user_id: str) -> Dict:
        """Get upcoming todos."""
        return self.list_todos(user_id, {'bucket': 'upcoming'})

    def get_someday_todos(self, user_id: str) -> Dict:
        """Get someday todos."""
        return self.list_todos(user_id, {'bucket': 'someday'})

    def get_overdue_todos(self, user_id: str) -> Dict:
        """Get overdue todos."""
        all_todos = self.db.list_todos(user_id)
        overdue = []

        for todo in all_todos:
            todo_obj = Todo.from_dict(todo)
            if todo_obj.is_overdue():
                overdue.append(todo)

        return {
            'status': 'success',
            'todos': overdue,
            'count': len(overdue)
        }

    def search_todos(self, user_id: str, query: str) -> Dict:
        """
        Search todos by query.

        Args:
            user_id: User ID
            query: Search query

        Returns:
            Dictionary with matching todos
        """
        all_todos = self.db.list_todos(user_id)
        query_lower = query.lower()

        matches = []
        for todo in all_todos:
            if query_lower in todo['title'].lower():
                matches.append(todo)
            elif todo.get('description') and query_lower in todo['description'].lower():
                matches.append(todo)
            elif any(query_lower in tag.lower() for tag in todo.get('tags', [])):
                matches.append(todo)

        return {
            'status': 'success',
            'todos': matches,
            'count': len(matches),
            'query': query
        }

    # Tag management
    def create_tag(self, user_id: str, name: str, color: str = '#6B7280') -> Dict:
        """
        Create a new tag.

        Args:
            user_id: User ID
            name: Tag name
            color: Tag color (hex)

        Returns:
            Result dictionary with tag data or error
        """
        tag_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        tag = Tag(
            id=tag_id,
            user_id=user_id,
            name=name,
            color=color,
            created_at=now
        )

        result = self.db.create_tag(tag.to_dict())
        if result['status'] == 'success':
            return {'status': 'success', 'tag': tag.to_dict()}
        return result

    def list_tags(self, user_id: str) -> Dict:
        """List all tags for a user."""
        tags = self.db.list_tags(user_id)
        return {
            'status': 'success',
            'tags': tags,
            'count': len(tags)
        }

    def get_tag(self, tag_id: str) -> Optional[Dict]:
        """Get tag by ID."""
        return self.db.get_tag(tag_id)

    def update_tag(self, tag_id: str, updates: Dict) -> Dict:
        """
        Update a tag.

        Args:
            tag_id: Tag ID
            updates: Dictionary of fields to update

        Returns:
            Result dictionary
        """
        result = self.db.update_tag(tag_id, updates)
        return result

    def delete_tag(self, tag_id: str) -> Dict:
        """
        Delete a tag.

        Args:
            tag_id: Tag ID

        Returns:
            Result dictionary
        """
        return self.db.delete_tag(tag_id)

    # List sharing management
    def share_list(self, list_id: str, user_id: str, permission: str = 'view') -> Dict:
        """
        Share a list with a user.

        Args:
            list_id: List ID to share
            user_id: User ID to share with
            permission: Permission level (view, edit, admin)

        Returns:
            Result dictionary
        """
        share_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        share_data = {
            'id': share_id,
            'list_id': list_id,
            'user_id': user_id,
            'permission': permission,
            'created_at': now
        }

        result = self.db.share_list(share_data)
        if result['status'] == 'success':
            # Mark list as shared
            self.db.update_todo_list(list_id, {'is_shared': True})
        return result

    def unshare_list(self, list_id: str, user_id: str) -> Dict:
        """
        Remove list sharing for a user.

        Args:
            list_id: List ID
            user_id: User ID to remove sharing from

        Returns:
            Result dictionary
        """
        return self.db.unshare_list(list_id, user_id)

    def get_list_shares(self, list_id: str) -> Dict:
        """
        Get all users a list is shared with.

        Args:
            list_id: List ID

        Returns:
            Dictionary with shares list
        """
        shares = self.db.get_list_shares(list_id)
        return {
            'status': 'success',
            'shares': shares,
            'count': len(shares)
        }

    def get_shared_lists(self, user_id: str) -> Dict:
        """
        Get all lists shared with a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with shared lists
        """
        lists = self.db.get_shared_lists(user_id)
        return {
            'status': 'success',
            'lists': lists,
            'count': len(lists)
        }

    def check_list_permission(self, list_id: str, user_id: str) -> Optional[str]:
        """
        Check user's permission level for a list.

        Args:
            list_id: List ID
            user_id: User ID

        Returns:
            Permission level (admin, edit, view) or None
        """
        return self.db.check_list_permission(list_id, user_id)

    # History management
    def get_todo_history(self, todo_id: str) -> Dict:
        """Get history for a todo."""
        history = self.db.get_todo_history(todo_id)
        return {
            'status': 'success',
            'history': history,
            'count': len(history)
        }

    # Private helper methods
    def _add_history(self, todo_id: str, user_id: str, action: str, changes: Dict):
        """Add a history entry."""
        history_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        history = TodoHistory(
            id=history_id,
            todo_id=todo_id,
            user_id=user_id,
            action=action,
            changes=changes,
            created_at=now
        )

        self.db.add_history(history.to_dict())


# Global singleton instance
_manager_instance = None


def get_todo_manager(db_path: Optional[str] = None) -> TodoManager:
    """
    Get global todo manager instance.

    Args:
        db_path: Optional custom database path

    Returns:
        TodoManager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = TodoManager(db_path)
    return _manager_instance
