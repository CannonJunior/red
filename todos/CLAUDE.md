# TODO List Module

## Overview
This module provides comprehensive task management functionality inspired by industry leaders (Todoist, TickTick, Things 3) while maintaining RED's core principles: zero-cost, MCP-native architecture, and modular design.

## Port Configuration
**CRITICAL**: This module runs on **port 9090** alongside all other RED services. Never change the port without explicit user permission.

## Module Structure
- `config.py` - Configuration and feature flags
- `models.py` - Data models (Todo, TodoList, User)
- `database.py` - Database operations (< 500 lines)
- `manager.py` - Business logic (< 500 lines)
- `nlp_parser.py` - Natural language processing
- `mcp_tools.py` - MCP tool definitions
- `utils.py` - Helper functions

## Key Features
- Natural language input ("Call mom tomorrow @high #personal")
- Multi-user support with isolation
- Todo lists organization
- Tags and filtering
- MCP integration for chat access
- Team collaboration (shared lists)

## Database
Uses separate `todos.db` file to ensure complete isolation from other services.

## Safety Principles
1. **Isolated**: No dependencies on other features except logging
2. **Optional**: Can be disabled via TODOS_AVAILABLE flag
3. **Modular**: Each file under 500 lines
4. **Zero-cost**: Local SQLite only, no external services

## Testing
All tests in `/tests/todos/` directory with comprehensive coverage.
