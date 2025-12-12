## Server Refactoring Guide

### Overview

This document describes the modular server architecture designed to replace the monolithic `server.py` (2,421 lines).

### Current State

**server.py** contains:
- 1 class (`CustomHTTPRequestHandler`)
- 50+ handler methods
- HTTP verb methods (GET, POST, DELETE, HEAD, OPTIONS)
- Utility methods (send_json_response, get_content_type, etc.)
- Route dispatch logic
- Business logic integration

### Problems with Monolithic Design

1. **Maintainability**: Hard to navigate 2,400+ lines
2. **Testing**: Difficult to test individual components
3. **Collaboration**: Merge conflicts in team environment
4. **Modularity**: Violates single responsibility principle
5. **Code reuse**: Duplicate logic across routes

### New Modular Architecture

```
server/
├── __init__.py              # Package initialization
├── CLAUDE.md                # Server-specific guidelines
├── base.py                  # Base HTTP request handler
├── routes/                  # Route handlers (mixins)
│   ├── __init__.py
│   ├── chat.py             # Chat API routes (~300 lines)
│   ├── rag.py              # RAG API routes (~250 lines)
│   ├── cag.py              # CAG API routes (~200 lines)
│   ├── search.py           # Search API routes (~150 lines)
│   ├── agents.py           # Agent management routes (~200 lines)
│   ├── mcp.py              # MCP tool routes (~400 lines)
│   └── static.py           # Static file serving (~100 lines)
├── middleware/              # Request/response processing
│   └── __init__.py
└── utils/                   # Shared utilities
    ├── __init__.py
    ├── response.py         # Response helpers (~70 lines)
    └── system.py           # System checks (~150 lines)
```

### Design Patterns

#### 1. Mixins Pattern

Each route module is a mixin that can be combined with the base handler:

```python
# server/routes/chat.py
class ChatRoutes:
    """Mixin for chat-related routes."""

    @rate_limit(requests_per_minute=60, burst=10)
    @validate_request(ChatRequest)
    def handle_chat_api(self):
        """Handle chat API requests."""
        # Implementation here
        pass

# server/base.py
from server.routes.chat import ChatRoutes
from server.routes.rag import RAGRoutes

class ModularHTTPHandler(ChatRoutes, RAGRoutes, BaseHTTPRequestHandler):
    """HTTP handler composed of route mixins."""
    pass
```

#### 2. Utility Functions

Common operations extracted to utility modules:

```python
# server/utils/response.py
def send_json_response(handler, data, status_code=200):
    """Send JSON response with proper headers."""
    # Implementation

# Usage in routes
from server.utils.response import send_json_response

class ChatRoutes:
    def handle_chat_api(self):
        send_json_response(self, {'message': 'Hello'})
```

#### 3. System Initialization

Centralized system availability checking:

```python
# server/utils/system.py
def initialize_systems():
    """Initialize all optional systems."""
    # Check RAG availability
    # Check CAG availability
    # etc.

# Returns status of all systems
```

### Migration Strategy

#### Phase 1: Create Parallel Structure (CURRENT)

1. ✅ Create `server/` directory structure
2. ✅ Create utility modules (`response.py`, `system.py`)
3. ✅ Document architecture and patterns
4. ⏳ Create example route modules
5. ⏳ Create `app.py` demonstrating new structure

**Status**: Foundation complete, examples pending

#### Phase 2: Gradual Route Migration

1. Extract one route at a time to `server/routes/`
2. Update `app.py` to use the new route
3. Test both old and new implementations
4. Once verified, mark route as migrated

**Priority Order**:
1. Static file serving (simplest)
2. Search routes (moderate complexity)
3. RAG routes (uses existing rag_api)
4. CAG routes (uses existing cag_api)
5. Agent routes (most complex)
6. Chat routes (integrates multiple systems)

#### Phase 3: Complete Migration

1. All routes migrated to `server/routes/`
2. `server.py` deprecated in favor of `app.py`
3. Remove duplicate code
4. Update documentation
5. Update deployment scripts

### Benefits of New Architecture

1. **Modularity**: Each route module <500 lines
2. **Testability**: Easy to test individual routes
3. **Maintainability**: Clear separation of concerns
4. **Collaboration**: Reduced merge conflicts
5. **Code Reuse**: Shared utilities prevent duplication
6. **Extensibility**: Easy to add new routes
7. **Documentation**: Self-documenting through structure

### Code Size Comparison

**Before**:
- server.py: 2,421 lines
- Total: 2,421 lines

**After** (estimated):
- server/base.py: ~150 lines
- server/routes/*.py: ~1,600 lines (8 files × 200 lines avg)
- server/utils/*.py: ~220 lines
- server/middleware/*.py: ~100 lines (future)
- app.py: ~100 lines
- **Total: ~2,170 lines** (251 lines saved)

**Key Improvement**: Not line count, but organization
- Largest file: ~400 lines (mcp.py)
- Average file: ~180 lines
- All files <500 lines (project standard)

### Testing Strategy

#### Unit Testing

```python
# tests/server/routes/test_chat.py
import unittest
from server.routes.chat import ChatRoutes
from unittest.mock import Mock

class TestChatRoutes(unittest.TestCase):
    def setUp(self):
        self.handler = Mock(spec=ChatRoutes)

    def test_handle_chat_api(self):
        # Test chat endpoint
        pass
```

#### Integration Testing

```python
# tests/server/test_integration.py
import requests

class TestServer(unittest.TestCase):
    def test_chat_endpoint(self):
        response = requests.post(
            'http://localhost:9090/api/chat',
            json={'message': 'Hello'}
        )
        self.assertEqual(response.status_code, 200)
```

### Example Route Module

```python
# server/routes/chat.py
"""Chat API routes."""

from rate_limiter import rate_limit
from request_validation import validate_request, ChatRequest
from server.utils.response import send_json_response, send_error_response
from ollama_config import ollama_config


class ChatRoutes:
    """Mixin providing chat-related routes."""

    @rate_limit(requests_per_minute=60, burst=10)
    @validate_request(ChatRequest)
    def handle_chat_api(self):
        """
        Handle chat API requests.

        Processes chat messages, optionally integrates RAG/MCP tools,
        and returns LLM responses.
        """
        data = self.validated_data

        # Extract request parameters
        message = data.message
        model = data.model or 'qwen2.5:3b'

        # Check if RAG should be triggered
        if self.should_trigger_rag(message):
            response = self.get_rag_enhanced_response(message, model)
        else:
            response = self.get_standard_ollama_response(message, model)

        send_json_response(self, response)

    def should_trigger_rag(self, message):
        """Check if message should trigger RAG system."""
        # Implementation
        pass

    def get_rag_enhanced_response(self, message, model):
        """Get response enhanced with RAG context."""
        # Implementation
        pass

    def get_standard_ollama_response(self, message, model):
        """Get standard Ollama response."""
        # Implementation
        pass
```

### Deployment

#### Using New Modular Server

```bash
# Start new modular server
python3 app.py

# Or with port specification
PORT=9090 python3 app.py
```

#### Using Legacy Server

```bash
# Start original monolithic server (still works)
python3 server.py
```

### Next Steps

1. **Create Example Routes**: Implement 2-3 route modules as examples
2. **Create app.py**: New entry point using modular structure
3. **Migration Guide**: Step-by-step guide for migrating routes
4. **Testing**: Add unit tests for new modules
5. **Documentation**: Update README with new architecture
6. **Gradual Migration**: Move routes one at a time
7. **Deprecation**: Eventually deprecate server.py

### Timeline Estimate

- ✅ **Phase 1** (Foundation): 4 hours - COMPLETED
- ✅ **Phase 2** (Example Routes): 6 hours - COMPLETED
- ⏳ **Phase 3** (Full Migration): 8-10 hours
- ⏳ **Phase 4** (Testing & Documentation): 4 hours

**Total**: 22-24 hours (10 hours completed, 12-14 hours remaining)

### Current Status

**Phase 1 Completed**:
- ✅ Directory structure created
- ✅ Utility modules (response.py, system.py)
- ✅ Documentation (this file, CLAUDE.md)
- ✅ Static file routes example

**Phase 2 Completed**:
- ✅ Search route module (server/routes/search.py - 148 lines)
- ✅ RAG route module (server/routes/rag.py - 197 lines)
- ✅ CAG route module (server/routes/cag.py - 168 lines)
- ✅ Base handler class with mixins (server/base.py - 245 lines)
- ✅ New app.py entry point (80 lines)
- ✅ System availability decorator fixed
- ✅ All endpoints tested and working

**Pending**:
- ❌ Chat route migration
- ❌ Agent route migration
- ❌ MCP route migration
- ❌ Full route migration
- ❌ Comprehensive testing
- ❌ Deployment updates

### Conclusion

The modular architecture provides:
- Clear separation of concerns
- Easier testing and maintenance
- Better collaboration support
- Extensible design for future features

The foundation is complete. Next step is creating example route modules to demonstrate the pattern and provide a migration template.
