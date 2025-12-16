"""
TODO List module - completely independent feature.

This module provides comprehensive task management functionality
with multi-user support, natural language processing, and MCP integration.

Can be disabled by removing TODOS_AVAILABLE flag in server.py.
"""

from .manager import TodoManager, get_todo_manager
from .models import User, TodoList, Todo, Tag, TodoHistory
from .database import TodoDatabase
from .config import (
    TODOS_DB_PATH,
    VALID_STATUSES,
    VALID_PRIORITIES,
    VALID_BUCKETS,
    DEFAULT_STATUS,
    DEFAULT_PRIORITY,
    DEFAULT_BUCKET
)

# MCP server (optional - requires mcp package)
try:
    from .mcp_server import TodoMCPServer, get_todo_mcp_server
    MCP_SERVER_AVAILABLE = True
except ImportError:
    MCP_SERVER_AVAILABLE = False
    TodoMCPServer = None
    get_todo_mcp_server = None

__all__ = [
    'TodoManager',
    'get_todo_manager',
    'User',
    'TodoList',
    'Todo',
    'Tag',
    'TodoHistory',
    'TodoDatabase',
    'TODOS_DB_PATH',
    'VALID_STATUSES',
    'VALID_PRIORITIES',
    'VALID_BUCKETS',
    'DEFAULT_STATUS',
    'DEFAULT_PRIORITY',
    'DEFAULT_BUCKET',
    'TodoMCPServer',
    'get_todo_mcp_server',
    'MCP_SERVER_AVAILABLE',
]

__version__ = '1.0.0'
