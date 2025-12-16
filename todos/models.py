"""Data models for TODO list feature."""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json


@dataclass
class User:
    """User model for multi-user support."""

    id: str
    username: str
    email: str
    display_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'display_name': self.display_name,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data: Dict) -> 'User':
        """Create user from dictionary."""
        return User(
            id=data['id'],
            username=data['username'],
            email=data['email'],
            display_name=data.get('display_name'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


@dataclass
class TodoList:
    """Todo list model for organizing todos."""

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    color: str = '#3B82F6'
    icon: str = 'list'
    is_shared: bool = False
    metadata: Dict = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert todo list to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'icon': self.icon,
            'is_shared': self.is_shared,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data: Dict) -> 'TodoList':
        """Create todo list from dictionary."""
        return TodoList(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            description=data.get('description'),
            color=data.get('color', '#3B82F6'),
            icon=data.get('icon', 'list'),
            is_shared=data.get('is_shared', False),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


@dataclass
class Todo:
    """Todo item model."""

    id: str
    user_id: str
    title: str
    list_id: Optional[str] = None
    description: Optional[str] = None
    status: str = 'pending'
    priority: str = 'medium'
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    reminder_date: Optional[str] = None
    reminder_time: Optional[str] = None
    bucket: str = 'inbox'
    tags: List[str] = field(default_factory=list)
    subtasks: List[Dict] = field(default_factory=list)
    parent_id: Optional[str] = None
    assigned_to: Optional[str] = None
    recurrence: Optional[str] = None
    position: int = 0
    metadata: Dict = field(default_factory=dict)
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert todo to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'list_id': self.list_id,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date,
            'due_time': self.due_time,
            'reminder_date': self.reminder_date,
            'reminder_time': self.reminder_time,
            'bucket': self.bucket,
            'tags': self.tags,
            'subtasks': self.subtasks,
            'parent_id': self.parent_id,
            'assigned_to': self.assigned_to,
            'recurrence': self.recurrence,
            'position': self.position,
            'metadata': self.metadata,
            'completed_at': self.completed_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Todo':
        """Create todo from dictionary."""
        return Todo(
            id=data['id'],
            user_id=data['user_id'],
            title=data['title'],
            list_id=data.get('list_id'),
            description=data.get('description'),
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'medium'),
            due_date=data.get('due_date'),
            due_time=data.get('due_time'),
            reminder_date=data.get('reminder_date'),
            reminder_time=data.get('reminder_time'),
            bucket=data.get('bucket', 'inbox'),
            tags=data.get('tags', []),
            subtasks=data.get('subtasks', []),
            parent_id=data.get('parent_id'),
            assigned_to=data.get('assigned_to'),
            recurrence=data.get('recurrence'),
            position=data.get('position', 0),
            metadata=data.get('metadata', {}),
            completed_at=data.get('completed_at'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def is_overdue(self) -> bool:
        """Check if todo is overdue."""
        if not self.due_date or self.status == 'completed':
            return False

        try:
            due = datetime.fromisoformat(self.due_date)
            return due.date() < datetime.now().date()
        except:
            return False

    def is_due_today(self) -> bool:
        """Check if todo is due today."""
        if not self.due_date:
            return False

        try:
            due = datetime.fromisoformat(self.due_date)
            return due.date() == datetime.now().date()
        except:
            return False


@dataclass
class Tag:
    """Tag model for organizing todos."""

    id: str
    user_id: str
    name: str
    color: str = '#6B7280'
    created_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert tag to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'color': self.color,
            'created_at': self.created_at
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Tag':
        """Create tag from dictionary."""
        return Tag(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            color=data.get('color', '#6B7280'),
            created_at=data.get('created_at')
        )


@dataclass
class TodoHistory:
    """History entry for todo changes."""

    id: str
    todo_id: str
    user_id: str
    action: str
    changes: Dict = field(default_factory=dict)
    created_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert history entry to dictionary."""
        return {
            'id': self.id,
            'todo_id': self.todo_id,
            'user_id': self.user_id,
            'action': self.action,
            'changes': self.changes,
            'created_at': self.created_at
        }

    @staticmethod
    def from_dict(data: Dict) -> 'TodoHistory':
        """Create history entry from dictionary."""
        return TodoHistory(
            id=data['id'],
            todo_id=data['todo_id'],
            user_id=data['user_id'],
            action=data['action'],
            changes=data.get('changes', {}),
            created_at=data.get('created_at')
        )
