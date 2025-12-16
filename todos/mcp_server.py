"""
MCP (Model Context Protocol) Server for TODO System.

This module exposes all TODO functionality through standardized MCP interfaces,
enabling AI agents to manage tasks, lists, and collaborate with users via chat.

Tools Provided:
- create_todo: Create a new todo with natural language or structured input
- list_todos: List todos with filtering options
- update_todo: Update an existing todo
- complete_todo: Mark a todo as complete
- delete_todo: Delete a todo
- create_list: Create a new todo list
- share_list: Share a list with another user
- parse_todo: Parse natural language into structured todo data
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Resource, Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP package not available. TODO MCP server will not be functional.")

# Local TODO components
from todos import get_todo_manager
from todos.nlp_parser import parse_natural_language

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TodoMCPServer:
    """
    Agent-native MCP server exposing TODO functionality for AI orchestration.

    This server provides standardized interfaces for:
    - Natural language todo creation
    - Todo management (CRUD operations)
    - List management and sharing
    - Collaboration features
    - NLP parsing
    """

    def __init__(self):
        """Initialize the MCP TODO server."""
        if not MCP_AVAILABLE:
            raise ImportError("MCP package is required for TodoMCPServer")

        self.server = Server("todo-server")
        self.manager = get_todo_manager()

        # Setup MCP tools and resources
        self.setup_tools()
        self.setup_resources()

        logger.info("TODO MCP Server initialized - Ready for agent orchestration")

    def setup_tools(self):
        """Setup MCP tools for AI agent consumption."""

        @self.server.call_tool()
        async def create_todo(
            user_id: str,
            input: Optional[str] = None,
            title: Optional[str] = None,
            list_id: Optional[str] = None,
            priority: Optional[str] = None,
            due_date: Optional[str] = None,
            due_time: Optional[str] = None,
            tags: Optional[List[str]] = None,
            **kwargs
        ) -> str:
            """
            Create a new todo using natural language or structured input.

            Args:
                user_id: User ID creating the todo
                input: Natural language description (e.g., "Submit report by Friday 3pm @high #work")
                title: Todo title (alternative to 'input')
                list_id: Optional list ID to add todo to
                priority: Priority level (low, medium, high, urgent)
                due_date: Due date (YYYY-MM-DD)
                due_time: Due time (HH:MM)
                tags: List of tags
                **kwargs: Additional todo fields

            Returns:
                JSON string with creation result

            Examples:
                # Natural language
                create_todo(user_id="123", input="Buy groceries tomorrow @high #personal")

                # Structured
                create_todo(user_id="123", title="Buy groceries", priority="high", tags=["personal"])
            """
            try:
                # Validate user_id
                if not user_id:
                    return json.dumps({
                        "status": "error",
                        "message": "user_id is required"
                    })

                # Determine if using natural language or structured input
                if input:
                    # Natural language mode
                    parsed = parse_natural_language(input, user_id)

                    if not parsed.get('title'):
                        return json.dumps({
                            "status": "error",
                            "message": "Could not extract a title from input",
                            "input": input
                        })

                    # Use parsed data, allow overrides
                    final_title = title or parsed['title']
                    final_priority = priority or parsed.get('priority', 'medium')
                    final_due_date = due_date or parsed.get('due_date')
                    final_due_time = due_time or parsed.get('due_time')
                    final_tags = tags or parsed.get('tags', [])
                    final_bucket = kwargs.get('bucket') or parsed.get('bucket', 'inbox')

                else:
                    # Structured mode
                    if not title:
                        return json.dumps({
                            "status": "error",
                            "message": "Either 'input' or 'title' is required"
                        })

                    final_title = title
                    final_priority = priority or 'medium'
                    final_due_date = due_date
                    final_due_time = due_time
                    final_tags = tags or []
                    final_bucket = kwargs.get('bucket', 'inbox')

                # Create the todo
                todo_kwargs = {
                    'list_id': list_id,
                    'priority': final_priority,
                    'due_date': final_due_date,
                    'due_time': final_due_time,
                    'bucket': final_bucket,
                    'tags': final_tags
                }

                # Add any additional kwargs
                for key, value in kwargs.items():
                    if key not in todo_kwargs and value is not None:
                        todo_kwargs[key] = value

                result = self.manager.create_todo(user_id, final_title, **todo_kwargs)

                return json.dumps({
                    "status": "success",
                    "message": f"Created todo: {final_title}",
                    "todo": result['todo'],
                    "natural_language_used": bool(input)
                })

            except Exception as e:
                logger.error(f"Error creating todo: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        @self.server.call_tool()
        async def list_todos(
            user_id: str,
            list_id: Optional[str] = None,
            bucket: Optional[str] = None,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            limit: int = 50
        ) -> str:
            """
            List todos with optional filtering.

            Args:
                user_id: User ID to list todos for
                list_id: Filter by list ID
                bucket: Filter by bucket (inbox, today, upcoming, someday)
                status: Filter by status (pending, in_progress, completed, archived)
                priority: Filter by priority (low, medium, high, urgent)
                limit: Maximum number of todos to return (default 50)

            Returns:
                JSON string with todos list
            """
            try:
                if not user_id:
                    return json.dumps({
                        "status": "error",
                        "message": "user_id is required"
                    })

                # Build filter kwargs
                filters = {'user_id': user_id}
                if list_id:
                    filters['list_id'] = list_id
                if bucket:
                    filters['bucket'] = bucket
                if status:
                    filters['status'] = status
                if priority:
                    filters['priority'] = priority

                result = self.manager.list_todos(**filters)

                # Limit results
                todos = result['todos'][:limit] if result['todos'] else []

                return json.dumps({
                    "status": "success",
                    "todos": todos,
                    "count": len(todos),
                    "total_count": result['count'],
                    "filters_applied": {k: v for k, v in filters.items() if k != 'user_id'}
                })

            except Exception as e:
                logger.error(f"Error listing todos: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        @self.server.call_tool()
        async def get_todo(todo_id: str) -> str:
            """
            Get details of a specific todo.

            Args:
                todo_id: Todo ID to retrieve

            Returns:
                JSON string with todo details
            """
            try:
                if not todo_id:
                    return json.dumps({
                        "status": "error",
                        "message": "todo_id is required"
                    })

                result = self.manager.get_todo(todo_id)

                return json.dumps({
                    "status": "success",
                    "todo": result['todo']
                })

            except Exception as e:
                logger.error(f"Error getting todo: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        @self.server.call_tool()
        async def update_todo(
            todo_id: str,
            title: Optional[str] = None,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            due_date: Optional[str] = None,
            due_time: Optional[str] = None,
            bucket: Optional[str] = None,
            tags: Optional[List[str]] = None,
            **kwargs
        ) -> str:
            """
            Update an existing todo.

            Args:
                todo_id: Todo ID to update
                title: New title
                status: New status
                priority: New priority
                due_date: New due date
                due_time: New due time
                bucket: New bucket
                tags: New tags
                **kwargs: Additional fields to update

            Returns:
                JSON string with update result
            """
            try:
                if not todo_id:
                    return json.dumps({
                        "status": "error",
                        "message": "todo_id is required"
                    })

                # Build updates dictionary
                updates = {}
                if title is not None:
                    updates['title'] = title
                if status is not None:
                    updates['status'] = status
                if priority is not None:
                    updates['priority'] = priority
                if due_date is not None:
                    updates['due_date'] = due_date
                if due_time is not None:
                    updates['due_time'] = due_time
                if bucket is not None:
                    updates['bucket'] = bucket
                if tags is not None:
                    updates['tags'] = tags

                # Add any additional kwargs
                for key, value in kwargs.items():
                    if key not in updates and value is not None:
                        updates[key] = value

                if not updates:
                    return json.dumps({
                        "status": "error",
                        "message": "No fields provided to update"
                    })

                result = self.manager.update_todo(todo_id, updates)

                return json.dumps({
                    "status": "success",
                    "message": "Todo updated successfully",
                    "fields_updated": list(updates.keys())
                })

            except Exception as e:
                logger.error(f"Error updating todo: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        @self.server.call_tool()
        async def complete_todo(todo_id: str) -> str:
            """
            Mark a todo as complete.

            Args:
                todo_id: Todo ID to complete

            Returns:
                JSON string with completion result
            """
            try:
                if not todo_id:
                    return json.dumps({
                        "status": "error",
                        "message": "todo_id is required"
                    })

                result = self.manager.complete_todo(todo_id)

                return json.dumps({
                    "status": "success",
                    "message": "Todo marked as complete",
                    "todo_id": todo_id,
                    "completed_at": result.get('completed_at')
                })

            except Exception as e:
                logger.error(f"Error completing todo: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        @self.server.call_tool()
        async def delete_todo(todo_id: str) -> str:
            """
            Delete a todo.

            Args:
                todo_id: Todo ID to delete

            Returns:
                JSON string with deletion result
            """
            try:
                if not todo_id:
                    return json.dumps({
                        "status": "error",
                        "message": "todo_id is required"
                    })

                result = self.manager.delete_todo(todo_id)

                return json.dumps({
                    "status": "success",
                    "message": "Todo deleted successfully",
                    "todo_id": todo_id
                })

            except Exception as e:
                logger.error(f"Error deleting todo: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        @self.server.call_tool()
        async def create_list(
            user_id: str,
            name: str,
            description: Optional[str] = None,
            color: Optional[str] = None,
            icon: Optional[str] = None
        ) -> str:
            """
            Create a new todo list.

            Args:
                user_id: User ID creating the list
                name: List name
                description: Optional description
                color: Optional color hex code
                icon: Optional icon name

            Returns:
                JSON string with creation result
            """
            try:
                if not user_id or not name:
                    return json.dumps({
                        "status": "error",
                        "message": "user_id and name are required"
                    })

                kwargs = {}
                if description:
                    kwargs['description'] = description
                if color:
                    kwargs['color'] = color
                if icon:
                    kwargs['icon'] = icon

                result = self.manager.create_list(user_id, name, **kwargs)

                return json.dumps({
                    "status": "success",
                    "message": f"Created list: {name}",
                    "list": result['list']
                })

            except Exception as e:
                logger.error(f"Error creating list: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        @self.server.call_tool()
        async def share_list(
            list_id: str,
            user_id: str,
            permission: str = "view"
        ) -> str:
            """
            Share a list with another user.

            Args:
                list_id: List ID to share
                user_id: User ID to share with
                permission: Permission level (view, edit, admin)

            Returns:
                JSON string with sharing result
            """
            try:
                if not list_id or not user_id:
                    return json.dumps({
                        "status": "error",
                        "message": "list_id and user_id are required"
                    })

                if permission not in ['view', 'edit', 'admin']:
                    return json.dumps({
                        "status": "error",
                        "message": "permission must be 'view', 'edit', or 'admin'"
                    })

                result = self.manager.share_list(list_id, user_id, permission)

                return json.dumps({
                    "status": "success",
                    "message": f"List shared with user (permission: {permission})",
                    "list_id": list_id,
                    "shared_with": user_id,
                    "permission": permission
                })

            except Exception as e:
                logger.error(f"Error sharing list: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        @self.server.call_tool()
        async def parse_todo(input: str) -> str:
            """
            Parse natural language input into structured todo data.

            This is useful for understanding how the NLP parser will interpret
            user input before creating a todo.

            Args:
                input: Natural language todo description

            Returns:
                JSON string with parsed data

            Example:
                parse_todo("Submit report by Friday 3pm @high #work")
                -> {
                    "title": "Submit report",
                    "due_date": "2025-12-20",
                    "due_time": "15:00",
                    "priority": "high",
                    "tags": ["work"],
                    "bucket": "upcoming"
                }
            """
            try:
                if not input:
                    return json.dumps({
                        "status": "error",
                        "message": "input is required"
                    })

                parsed = parse_natural_language(input)

                return json.dumps({
                    "status": "success",
                    "parsed": parsed,
                    "original_input": input
                })

            except Exception as e:
                logger.error(f"Error parsing todo: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        logger.info("TODO MCP tools registered: 9 tools available")

    def setup_resources(self):
        """Setup MCP resources for context."""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available TODO resources."""
            return [
                Resource(
                    uri="todo://buckets",
                    name="TODO Buckets",
                    description="Available todo bucket categories: inbox, today, upcoming, someday"
                ),
                Resource(
                    uri="todo://priorities",
                    name="Priority Levels",
                    description="Available priority levels: low, medium, high, urgent"
                ),
                Resource(
                    uri="todo://nlp-patterns",
                    name="NLP Patterns",
                    description="Supported natural language patterns for dates, times, priorities, and tags"
                )
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read TODO resource details."""
            if uri == "todo://buckets":
                return json.dumps({
                    "buckets": [
                        {
                            "name": "inbox",
                            "description": "Default bucket for new todos without a due date"
                        },
                        {
                            "name": "today",
                            "description": "Todos due today"
                        },
                        {
                            "name": "upcoming",
                            "description": "Todos due within the next 7 days"
                        },
                        {
                            "name": "someday",
                            "description": "Todos without a specific deadline"
                        }
                    ]
                })
            elif uri == "todo://priorities":
                return json.dumps({
                    "priorities": [
                        {"level": "low", "markers": ["@low"]},
                        {"level": "medium", "markers": ["@medium"], "default": True},
                        {"level": "high", "markers": ["@high", "!"]},
                        {"level": "urgent", "markers": ["@urgent", "!!"]}
                    ]
                })
            elif uri == "todo://nlp-patterns":
                return json.dumps({
                    "date_patterns": [
                        "today", "tomorrow", "next week",
                        "Monday/Tuesday/.../Sunday",
                        "in X days", "YYYY-MM-DD"
                    ],
                    "time_patterns": [
                        "3pm", "11am", "2:30 pm", "9:15 am"
                    ],
                    "priority_markers": [
                        "@high", "@urgent", "@low", "@medium", "!", "!!"
                    ],
                    "tag_pattern": "#tagname"
                })
            else:
                return json.dumps({"error": "Resource not found"})

        logger.info("TODO MCP resources registered")

    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


# Singleton instance
_todo_mcp_server = None


def get_todo_mcp_server() -> Optional[TodoMCPServer]:
    """Get the singleton TODO MCP server instance."""
    global _todo_mcp_server

    if not MCP_AVAILABLE:
        return None

    if _todo_mcp_server is None:
        try:
            _todo_mcp_server = TodoMCPServer()
        except Exception as e:
            logger.error(f"Failed to initialize TODO MCP server: {e}")
            return None

    return _todo_mcp_server


async def main():
    """Main entry point for running the TODO MCP server."""
    server = get_todo_mcp_server()
    if server:
        logger.info("Starting TODO MCP Server...")
        await server.run()
    else:
        logger.error("Failed to start TODO MCP Server")


if __name__ == "__main__":
    asyncio.run(main())
