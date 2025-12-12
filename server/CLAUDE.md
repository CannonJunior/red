### 🔄 Server Module Awareness

This directory contains the modular server architecture.

### 🌐 Port Management - CRITICAL
- **ALWAYS run this web application on port 9090 ONLY.**
- This is inherited from the parent CLAUDE.md

### 📁 Structure

```
server/
├── __init__.py          # Package initialization
├── base.py              # Base HTTP request handler
├── routes/              # Route handlers by feature
│   ├── __init__.py
│   ├── chat.py         # Chat API routes
│   ├── rag.py          # RAG routes
│   ├── cag.py          # CAG routes
│   ├── search.py       # Search routes
│   ├── agents.py       # Agent management routes
│   ├── mcp.py          # MCP tool routes
│   └── static.py       # Static file serving
├── middleware/          # Request/response processing
│   └── __init__.py
└── utils/               # Shared utilities
    ├── __init__.py
    ├── response.py     # Response helpers
    └── system.py       # System availability checks
```

### 📝 Design Principles

1. **Each route module <500 lines** - Follows project convention
2. **Mixins pattern** - Route modules are mixins that extend base handler
3. **Backwards compatible** - Existing server.py continues to work
4. **Gradual migration** - Can adopt modules incrementally
5. **Clear separation** - Routes, middleware, and utilities separated

### 🔄 Migration Strategy

The new modular structure coexists with server.py:
- `server.py` - Original monolithic file (continues to work)
- `app.py` - New entry point using modular structure
- Both can run simultaneously for A/B testing

### 📦 Usage

```python
# New modular approach
from server.app import create_server

server = create_server()
server.serve_forever()
```
