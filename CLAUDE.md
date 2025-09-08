### 🔄 Project Awareness & Context
- **NEVER HARDCODE A VALUE** when the same value can be written into a configuration file and read into data instead. Prompt the user if you **ever** create a hard-coded value.
- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn't listed, add it with a brief description and today's date.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use venv_linux** (the virtual environment) whenever executing Python commands, including for unit tests.

### 🌐 Port Management - CRITICAL
- **ALWAYS run this web application on port 8000 ONLY.** Never change the port without explicit user permission.
- **If you need to run another service on a different port, ASK the user first.**
- **The default server port is 8000** - maintain this consistency across all sessions.
- **📋 MEMOIZATION RULE**: Every new directory MUST have a CLAUDE.md file that includes the port 8000 requirement. See `docs/CLAUDE-MEMOIZATION-RULES.md` for details.

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
  For agents this looks like:
    - `agent.py` - Main agent definition and execution logic 
    - `tools.py` - Tool functions used by the agent 
    - `prompts.py` - System prompts
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

### ✅ Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under a “Discovered During Work” section.

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 💬 Chat Commands & MCP Integration
- **Use the established MCP architecture** for adding new chat commands that integrate with external services
- **Follow the command flow**: Chat Interface → MCP Service → MCP Bridge → Python MCP Servers
- **Commands must be prefixed with `/`** to be recognized as workflow commands
- **Use consistent naming**: `/category-action` format (e.g., `/opp-create`, `/note-search`)

#### Creating New Chat Commands (5-Step Process):

**Step 1: Define Command Pattern in `workflow-command-server.py`**
```python
# Add to command_patterns dict in __init__
'command-name': r'^/command[-_]?name\s+(?:"([^"]+)"|(.+))$',

# Add to command_descriptions dict  
'/command-name <param>': 'Description of what the command does',

# Add to workflow keywords list
'command', 'keyword'
```

**Step 2: Add Command Handlers to `workflow-bridge.js`**
```javascript
// Add case to routeCommand() switch statement
case 'handle_command_name':
    return await this.handleCommandName(parameters);

// Implement handler method
async handleCommandName(parameters) {
    console.log('handleCommandName called with parameters:', JSON.stringify(parameters, null, 2));
    
    // Extract parameters with fallbacks
    const param = parameters.raw_params?.[1] || parameters.raw_params?.[2] || parameters.param;
    
    if (!param) {
        throw new Error('Parameter is required');
    }

    // Call MCP server through bridge
    const result = await this.callMCPServer('action_name', { param });
    
    return {
        action: 'handle_command_name',
        result: result,
        message: `✅ Command executed successfully`
    };
}
```

**Step 3: Add Parameter Extraction in `workflow-command-server.py`**
```python
# In execute_workflow_command function, add to parameter extraction logic:
elif action == 'handle_command_name':
    # Extract param from raw_params[1] or raw_params[2] (quoted or unquoted)
    param = raw_params[1] if len(raw_params) > 1 and raw_params[1] else (raw_params[2] if len(raw_params) > 2 and raw_params[2] else None)
    if param:
        parameters = {'param': param}
```

**Step 4: Add MCP Server Actions to `mcp-bridge.js`**
```javascript
// Add case to executeNoteCommand() switch statement
case 'action_name':
    return await this.callMCPTool('server-name', 'tool_name', parameters);
```

**Step 5: Implement MCP Tool in Python Server**
```python
# In appropriate MCP server (e.g., note-taking-server.py)
@mcp.tool(
    name="tool_name",
    description="Description of what the tool does"
)
async def tool_name(self, param: str) -> Dict[str, Any]:
    """
    Tool implementation.
    
    Args:
        param: Parameter description
    
    Returns:
        Dict containing result data
    """
    # Implementation logic
    return {
        'status': 'success',
        'result': 'result_data'
    }
```

#### Parameter Parsing & Escaping:

**Command Format Options:**
- `/command param` - Simple parameter
- `/command "quoted param"` - Quoted parameter with spaces
- `/command param1 param2` - Multiple parameters
- `/command "param 1" param2` - Mixed quoted/unquoted

**Parameter Extraction Arrays:**
- `raw_params[0]` - First captured group (usually first parameter)
- `raw_params[1]` - Second captured group (quoted content)
- `raw_params[2]` - Third captured group (unquoted content)
- Use fallback logic: `param = raw_params[1] || raw_params[2] || parameters.param`

**Quote Escaping Prevention:**
- MCP service automatically processes quotes in `preprocessCommandMessage()`
- Quotes are converted to safe alternatives (spaces to underscores)
- Use `original_input` to preserve user's exact command for display

**Testing Commands:**
```bash
# Test parsing
curl -X POST http://localhost:3001/api/mcp/parse-workflow-command \
  -H "Content-Type: application/json" \
  -d '{"message": "/your-command \"test param\""}'

# Test execution  
curl -X POST http://localhost:3001/api/mcp/execute-workflow-command \
  -H "Content-Type: application/json" \
  -d '{"commandData": {"is_workflow_command": true, "action": "handle_your_command", "raw_params": [null, "test param"]}}'

# Test MCP call
curl -X POST http://localhost:3001/api/mcp/execute-command \
  -H "Content-Type: application/json" \
  -d '{"commandData": {"is_command": true, "action": "your_action", "parameters": {"param": "test"}}}'
```

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.

### 📝 Memoization Instructions
- **Memoize any input given in MEMOIZE.md file.**
- **This project focuses on adding agentic UI features to help users with their day-to-day work.**
