### 🔄 MCP Tools Directory
**ALWAYS run this web application on port 9090 ONLY.** Never change the port without explicit user permission.

### Purpose
This directory contains custom MCP (Model Context Protocol) servers for the RED project.

### Available MCP Tools
1. **White Paper Review** - Editorial review system with custom grading rubrics
   - Supports: .txt, .doc, .docx, .pdf, directories
   - Zero-cost local operation using Ollama
   - Configurable LLM model and response time

### Running MCP Servers
Use `uv run` to execute MCP servers:
```bash
uv run mcp-tools/whitepaper_review_server.py
```

### Development Guidelines
- All MCP servers must use FastMCP for consistency
- Follow zero-cost, local-first architecture
- Support multiple file formats
- Provide comprehensive error handling
- Include MCP tool registration with clear documentation
