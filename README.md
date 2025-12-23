# Robobrain - Web Application: Red features

A basic web application with Open WebUI's look and feel, designed to add agentic UI features for day-to-day work assistance.

## Features

- **Modern UI Design**: Based on Open WebUI's clean, responsive interface
- **Dark/Light Mode**: Automatic theme detection with manual toggle
- **Responsive Layout**: Works on desktop and mobile devices
- **Chat Interface**: Ready for AI assistant integration
- **Modular Architecture**: Structured for easy extension

### Ollama Agents
- **Zero-Cost Local Agents**: Create and run AI agents using local Ollama models (qwen2.5:3b, mistral, llama2)
- **Skills System**: Equip agents with reusable skills (PDF extraction, data analysis, code validation)
- **Agent Management**: Full CRUD operations - create, view, edit, and delete agents
- **@ Mention Autocomplete**: Invoke named agents in chat using @ mentions with keyboard navigation
- **Real-time Execution**: Agents run locally with no API costs

## Quick Start

1. **Start Ollama:**
   ```bash
   ollama serve
   ```

2. **Start the server:**
   ```bash
   ./start.sh
   ```

   Or manually:
   ```bash
   uv run server.py
   ```

3. **Open in browser:**
   - Navigate to http://localhost:9090
   - The application will load automatically

## Using Ollama Agents

### Creating an Agent

1. Navigate to the **Agents** interface in the sidebar
2. Click **+ Create Agent**
3. Fill in the agent details:
   - **Name**: A descriptive name for your agent
   - **Description**: What the agent does
   - **Model**: Select from available Ollama models (default: qwen2.5:3b)
   - **Skills**: Choose from available skills (pdf, xlsx, docx, pptx from Anthropic plugins, or local skills: data-analysis, code-validation)
   - **Capabilities**: Add capability tags for organization
4. Click **Create Agent**

### Available Skills

**Anthropic Plugin Skills** (from document-skills plugin):
- **pdf**: Comprehensive PDF manipulation toolkit - extract text/tables, create PDFs, merge/split documents, fill forms
- **xlsx**: Spreadsheet creation, editing, and analysis with formulas and formatting
- **docx**: Word document creation and editing
- **pptx**: PowerPoint presentation creation
- **And 12 more**: mcp-builder, skill-creator, webapp-testing, brand-guidelines, etc.

**Local Custom Skills**:
- **data-analysis**: Analyze CSV/JSON data and generate formatted reports with pandas
- **code-validation**: Review Python code for quality, security, and best practices

### Editing an Agent

1. In the Agents interface, find the agent you want to modify
2. Click the **Edit** button on the agent card
3. Update any fields (name, description, model, skills, capabilities)
4. Click **Save Changes**

### Using @ Mentions in Chat

1. In the chat interface, type `@` to trigger agent autocomplete
2. Use arrow keys to navigate the list of available agents
3. Press **Tab** or **Enter** to select an agent
4. The agent name will be inserted into your message
5. Type your message after the agent name
6. Send the message - the system will route it to the specified agent

**Format**: `@AgentName your message here`

**Examples**:
- `@PDFHelper How do I extract tables from a multi-page PDF?`
- `@DataAnalyst Can you help me analyze sales trends in a CSV file?`
- `@CodeReviewer Review this Python function for security issues`

The agent will respond using its configured skills and model. Agent responses appear in the chat with metadata showing:
- Agent name
- Model used
- Response time
- Zero cost (local execution)

### Keyboard Shortcuts

**Autocomplete Navigation**:
- `/` - Trigger prompt autocomplete (inserts saved prompt templates)
- `#` - Trigger MCP tool autocomplete
- `@` - Trigger agent mention autocomplete
- **Arrow Up/Down** - Navigate autocomplete list
- **Tab** or **Enter** - Select highlighted item
- **Escape** - Close autocomplete

**Request Cancellation**:
- Press **ESC** once during a request to see cancellation confirmation
- Press **ESC** again within 3 seconds to cancel the current request
- The system will stop processing and display a cancellation message

### Using Prompts with / Autocomplete

1. In the chat interface, type `/` to trigger prompt autocomplete
2. Start typing to filter prompts by name or description
3. Use arrow keys to navigate the filtered list
4. Press **Tab** or **Enter** to select a prompt
5. The prompt content will be inserted at the cursor position
6. Complete the prompt and send your message

**Available Prompts**:
- `/code_review` - Review code for best practices and bugs
- `/explain` - Explain a concept in simple terms
- `/summarize` - Summarize text concisely
- `/debug` - Debug code and find issues

**Example Usage**:
```
Type: /explain
→ Autocomplete shows prompts
→ Select "/explain"
→ Inserted: "Please explain the following concept in simple, easy-to-understand terms:"
→ Add: "quantum entanglement"
→ Send message
```

**Creating Custom Prompts**:
Custom prompts can be created via the Prompts interface in the sidebar. Each prompt has:
- **Name**: Short identifier (e.g., "explain", "code_review")
- **Description**: Brief explanation of the prompt's purpose
- **Content**: The actual prompt template text
- **Usage Tracking**: Automatically tracks how many times each prompt is used

### Example Workflows

**PDF Document Processing**:
1. Create an agent with `pdf` skill (from Anthropic plugin) named "PDFHelper"
2. In chat: `@PDFHelper Extract all text from this 50-page research paper`
3. The agent responds with code and instructions using pdfplumber

**Data Analysis & Reporting**:
1. Create an agent with `data-analysis` skill named "DataAnalyst"
2. In chat: `@DataAnalyst Analyze quarterly_sales.csv and find top products`
3. The agent provides pandas code for analysis and report generation

**Code Quality Review**:
1. Create an agent with `code-validation` skill named "CodeReviewer"
2. In chat: `@CodeReviewer Check this authentication function for security flaws`
3. The agent reviews code against best practices and security standards

**Multi-Skill Agent**:
1. Create an agent with multiple skills: `["pdf", "data-analysis"]`
2. The agent can handle both PDF extraction and data analysis tasks
3. Example: Extract data from PDFs then analyze it

### API Endpoints

The agent system exposes the following REST API endpoints:

- `GET /api/ollama/agents` - List all agents
- `POST /api/ollama/agents` - Create a new agent
- `GET /api/ollama/agents/{id}` - Get agent details
- `PUT /api/ollama/agents/{id}` - Update an agent
- `DELETE /api/ollama/agents/{id}` - Delete an agent
- `POST /api/ollama/agents/{id}/invoke` - Invoke an agent with a message
- `GET /api/ollama/skills` - List available skills
- `GET /api/ollama/status` - Check Ollama status and available models

**Example API Usage**:

```bash
# Create an agent
curl -X POST http://localhost:9090/api/ollama/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PDFHelper",
    "description": "Helps with PDF extraction",
    "model": "qwen2.5:3b",
    "skills": ["pdf"],
    "capabilities": ["PDF Analysis"]
  }'

# Invoke an agent
curl -X POST http://localhost:9090/api/ollama/agents/agent_123/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I extract text from a PDF?"}'

# Update an agent (add more skills)
curl -X PUT http://localhost:9090/api/ollama/agents/agent_123 \
  -H "Content-Type: application/json" \
  -d '{
    "skills": ["pdf", "data-analysis"]
  }'
```

## Architecture

### Frontend Structure
- `index.html` - Main application layout
- `styles.css` - Tailwind CSS with custom styling
- `app.js` - JavaScript application logic
- `robobrain.svg` - Logo and favicon

### Key Components
- **ThemeManager**: Handles dark/light mode switching
- **ChatInterface**: Manages message input and display
- **Navigation**: Sidebar navigation handling
- **IntegrationManager**: Placeholder for future API integrations

### Design System
- **Framework**: Tailwind CSS
- **Typography**: Inter font family
- **Colors**: Neutral grays with blue accents
- **Layout**: Sidebar + main content area
- **Responsive**: Mobile-first design

## Development

### File Structure
```
<project-root>/
├── index.html          # Main HTML file
├── styles.css          # Custom CSS styles
├── app.js             # JavaScript application
├── server.py          # Development server
├── start.sh           # Server start script (with port cleanup)
├── robobrain.svg      # Logo/favicon
├── MEMOIZE.md         # Project inputs
├── CLAUDE.md          # Development instructions
└── README.md          # This file
```

### Integration Points
The application includes placeholder functions for:
- API endpoint calls
- WebSocket connections
- Agent interactions
- File upload handling

### Server Configuration
- **Port**: 9090 (web application port)
- **CORS**: Enabled for development
- **Static Files**: Served from current directory
- **Routing**: Basic SPA routing support

## Future Enhancements

The application is structured to support:
- Real-time chat with AI agents
- File upload and processing
- Multi-modal interactions
- Advanced workflow commands
- Backend API integration

## Browser Compatibility

- Modern browsers with ES6+ support
- Chrome, Firefox, Safari, Edge
- Mobile browsers (iOS Safari, Chrome Mobile)

## Notes

This is a basic implementation focusing on UI/UX foundations. Backend integration and advanced features are structured but not implemented, following the requirement to add only what's necessary for the basic web application.
