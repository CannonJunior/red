# TODO List Implementation Plan
## Agent-Native Task Management System

**Date**: December 15, 2025
**Version**: 2.0 (Second Implementation Attempt)
**Status**: Planning Phase

---

## Executive Summary

This document outlines the implementation plan for a comprehensive TODO list feature within the RED RAG system. The feature is inspired by industry-leading task management applications (Todoist, TickTick, Things 3) while maintaining our core principles: zero-cost, MCP-native architecture, and modular design.

**CRITICAL LESSON FROM FIRST ATTEMPT**: The previous implementation broke general services across the application. This plan includes specific safeguards to prevent similar issues.

---

## Research Findings

### Industry Leaders Analysis

#### 1. Todoist (2025 Features)
**Key Features:**
- Natural language input for task creation ("Submit report on Friday")
- Flexible project organization with labels and filters
- Cross-platform synchronization
- AI assistant for prioritization and scheduling (2025 update)
- Two-way calendar integration (Google Calendar + Outlook)
- Email integration with automatic summarization
- 80+ integrations
- SOC2 Type I certified

**Architecture Insights:**
- Cloud-based with seamless device synchronization
- Natural language processing for date/time extraction
- Flexible project/label/filter organization
- Strong integration ecosystem

**Sources:**
- [Todoist Review 2025: Features, Pricing, Is It Worth It?](https://www.joshdolin.com/mindscapes-blog/todoist-review-2025)
- [Todoist for Project Management](https://everhour.com/blog/todoist-for-project-management/)
- [Todoist Features](https://www.todoist.com/features)

#### 2. TickTick (2025 Features)
**Key Features:**
- Natural language processing for task details
- Multiple views: Kanban, Timeline, Calendar, List
- Pomodoro timer integration
- Cloud synchronization across all devices
- Offline functionality with auto-sync
- SSL encryption for security
- Two-Step Verification (2025 update)
- Notion Integration (2025 update)
- Countdown feature for deadlines

**Architecture Insights:**
- Cloud-based with offline-first design
- Real-time synchronization
- Multiple view types for different workflows
- Strong security focus (SSL + 2FA)

**Sources:**
- [TickTick Software Overview 2025](https://www.softwareadvice.com/project-management/ticktick-profile/)
- [TickTick Review 2025](https://research.com/software/reviews/ticktick)
- [TickTick Features](https://ticktick.com/features)

#### 3. Things 3 (2025 Features)
**Key Features:**
- Getting Things Done (GTD) methodology
- Organization via Projects, Areas, and Tags
- Today, This Evening, Someday buckets
- Calendar integration (Apple Calendar)
- Quick capture with Inbox
- Logbook for automatic work journal
- Rebuilt cloud infrastructure using Swift on server (2025)
- Clean, minimalist design

**Architecture Insights:**
- Recently rebuilt entire cloud infrastructure (2025)
- Swift on server for faster performance
- Apple ecosystem focus
- GTD-based workflow organization
- Automatic work journal (Logbook)

**Sources:**
- [Organizing Life With Things 3 in 2025](https://block81.com/blog/organizing-my-life-with-things-3-in-2025)
- [Things 3 Review: Pros, Cons, Features & Pricing](https://thedigitalprojectmanager.com/tools/things-3-review/)
- [Things Blog - Cultured Code](https://culturedcode.com/things/blog/)

#### Video Reviews & Popular References
**MKBHD (Marques Brownlee):**
- Uses TickTick as his favorite to-do app
- Featured in "What's on my Tech: 2019!" video
- Confirmed preference on social media multiple times
- App visible on his home screen in 2024 videos

**Francesco D'Alessio (Keep Productive):**
- 400K+ YouTube subscribers covering productivity tools
- Extensive coverage of Todoist, TickTick, and Things 3
- Focuses on comparative reviews and app workflows

**Sources:**
- [TickTick vs Things 3 Comparison](https://nerdynav.com/ticktick-vs-things-3/)
- [Mark Ellis Reviews](https://markellisreviews.com/reviews/ive-switched-to-do-list-apps-things-vs-ticktick/)
- [Todoist vs TickTick Comparison 2025](https://zapier.com/blog/ticktick-vs-todoist/)

### Key Patterns Identified

1. **Natural Language Input**: All three apps support NLP for task creation
2. **Flexible Organization**: Projects/Areas + Tags/Labels system
3. **Multiple Views**: Different visualization modes (list, kanban, calendar)
4. **Smart Scheduling**: Today, Upcoming, Someday buckets
5. **Offline-First**: Local storage with cloud sync
6. **Integration Ecosystem**: Calendar, email, other tools
7. **Security**: Encryption and authentication
8. **Cross-Platform**: Consistent experience across devices

---

## System Architecture

### Core Principles

1. **Modular Design**: No file exceeds 500 lines
2. **MCP-Native**: Every function exposed as MCP tool
3. **Multi-User Support**: Team-based task tracking
4. **Zero-Cost**: Local SQLite storage, no cloud dependencies
5. **Integration-Ready**: Accessible from Chat, API, and UI
6. **Isolated Implementation**: No modifications to existing general services

### File Structure

```
/home/junior/src/red/
├── todos/                          # New TODO feature directory
│   ├── __init__.py
│   ├── CLAUDE.md                   # Port 9090 requirement + feature docs
│   ├── config.py                   # Configuration settings
│   ├── models.py                   # Data models (Todo, TodoList, User)
│   ├── database.py                 # Database operations (< 500 lines)
│   ├── manager.py                  # Business logic (< 500 lines)
│   ├── nlp_parser.py              # Natural language processing
│   ├── mcp_tools.py               # MCP tool definitions
│   └── utils.py                   # Helper functions
│
├── server/routes/
│   └── todos.py                    # Route handlers (< 500 lines)
│
├── server.py                       # Add TODO routes registration
│
├── index.html                      # Add TODO UI components
│
└── app.js                          # Add TODO JavaScript handlers
```

### Database Schema

**todos.db** (Separate database file to avoid breaking existing services)

```sql
-- Users table (for multi-user support)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Todo Lists table (like Projects in Todoist)
CREATE TABLE IF NOT EXISTS todo_lists (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#3B82F6',
    icon TEXT DEFAULT 'list',
    is_shared BOOLEAN DEFAULT 0,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Todos table
CREATE TABLE IF NOT EXISTS todos (
    id TEXT PRIMARY KEY,
    list_id TEXT,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',      -- pending, in_progress, completed, archived
    priority TEXT DEFAULT 'medium',     -- low, medium, high, urgent
    due_date TEXT,
    due_time TEXT,
    reminder_date TEXT,
    reminder_time TEXT,
    bucket TEXT DEFAULT 'inbox',        -- inbox, today, upcoming, someday
    tags TEXT,                          -- JSON array
    subtasks TEXT,                      -- JSON array of subtask objects
    parent_id TEXT,                     -- For subtasks
    assigned_to TEXT,                   -- User ID for team features
    recurrence TEXT,                    -- Recurrence rule (daily, weekly, etc)
    position INTEGER DEFAULT 0,         -- For manual ordering
    metadata TEXT,                      -- JSON for extensibility
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (list_id) REFERENCES todo_lists(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES todos(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

-- Tags table (for better organization)
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#6B7280',
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
);

-- Todo history table (for audit trail)
CREATE TABLE IF NOT EXISTS todo_history (
    id TEXT PRIMARY KEY,
    todo_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,               -- created, updated, completed, deleted
    changes TEXT,                       -- JSON of what changed
    created_at TEXT NOT NULL,
    FOREIGN KEY (todo_id) REFERENCES todos(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Shared lists access table
CREATE TABLE IF NOT EXISTS list_shares (
    id TEXT PRIMARY KEY,
    list_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    permission TEXT DEFAULT 'view',     -- view, edit, admin
    created_at TEXT NOT NULL,
    FOREIGN KEY (list_id) REFERENCES todo_lists(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(list_id, user_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_todos_user ON todos(user_id);
CREATE INDEX IF NOT EXISTS idx_todos_list ON todos(list_id);
CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status);
CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos(due_date);
CREATE INDEX IF NOT EXISTS idx_todos_bucket ON todos(bucket);
CREATE INDEX IF NOT EXISTS idx_todos_assigned ON todos(assigned_to);
CREATE INDEX IF NOT EXISTS idx_todo_lists_user ON todo_lists(user_id);
CREATE INDEX IF NOT EXISTS idx_tags_user ON tags(user_id);
CREATE INDEX IF NOT EXISTS idx_history_todo ON todo_history(todo_id, created_at DESC);
```

---

## API Design

### RESTful Endpoints

```
# User Management
GET    /api/todos/users              - List all users
POST   /api/todos/users              - Create user
GET    /api/todos/users/{id}         - Get user details
PUT    /api/todos/users/{id}         - Update user
DELETE /api/todos/users/{id}         - Delete user

# Todo Lists
GET    /api/todos/lists              - List user's todo lists
POST   /api/todos/lists              - Create new list
GET    /api/todos/lists/{id}         - Get list details
PUT    /api/todos/lists/{id}         - Update list
DELETE /api/todos/lists/{id}         - Delete list
POST   /api/todos/lists/{id}/share   - Share list with users

# Todos
GET    /api/todos                    - List todos (with filters)
POST   /api/todos                    - Create todo (supports NLP)
GET    /api/todos/{id}               - Get todo details
PUT    /api/todos/{id}               - Update todo
DELETE /api/todos/{id}               - Delete todo
POST   /api/todos/{id}/complete      - Mark as complete
POST   /api/todos/{id}/archive       - Archive todo
GET    /api/todos/{id}/history       - Get todo history

# Smart Queries
GET    /api/todos/today              - Get today's todos
GET    /api/todos/upcoming           - Get upcoming todos
GET    /api/todos/someday            - Get someday todos
GET    /api/todos/overdue            - Get overdue todos
GET    /api/todos/search?q={query}   - Search todos

# Tags
GET    /api/todos/tags               - List user's tags
POST   /api/todos/tags               - Create tag
PUT    /api/todos/tags/{id}          - Update tag
DELETE /api/todos/tags/{id}          - Delete tag

# NLP Processing
POST   /api/todos/parse              - Parse natural language to todo
```

### Request/Response Examples

**Create Todo (Natural Language):**
```json
POST /api/todos
{
  "input": "Submit quarterly report by Friday 3pm #work @high",
  "user_id": "user-123"
}

Response:
{
  "status": "success",
  "todo": {
    "id": "todo-456",
    "title": "Submit quarterly report",
    "due_date": "2025-12-19",
    "due_time": "15:00",
    "tags": ["work"],
    "priority": "high",
    "bucket": "today"
  }
}
```

**Create Todo (Structured):**
```json
POST /api/todos
{
  "title": "Buy groceries",
  "description": "Milk, eggs, bread",
  "due_date": "2025-12-16",
  "priority": "medium",
  "tags": ["personal", "shopping"],
  "list_id": "list-789",
  "user_id": "user-123"
}
```

---

## MCP Integration

### MCP Tools Exposed

```python
# Tool: create_todo
{
  "name": "create_todo",
  "description": "Create a new todo item with natural language support",
  "input_schema": {
    "type": "object",
    "properties": {
      "input": {"type": "string"},
      "user_id": {"type": "string"}
    }
  }
}

# Tool: list_todos
{
  "name": "list_todos",
  "description": "List todos with optional filters",
  "input_schema": {
    "type": "object",
    "properties": {
      "user_id": {"type": "string"},
      "bucket": {"type": "string"},
      "status": {"type": "string"},
      "list_id": {"type": "string"}
    }
  }
}

# Tool: update_todo
{
  "name": "update_todo",
  "description": "Update a todo item",
  "input_schema": {
    "type": "object",
    "properties": {
      "todo_id": {"type": "string"},
      "updates": {"type": "object"}
    }
  }
}

# Tool: complete_todo
{
  "name": "complete_todo",
  "description": "Mark a todo as completed",
  "input_schema": {
    "type": "object",
    "properties": {
      "todo_id": {"type": "string"}
    }
  }
}

# Tool: search_todos
{
  "name": "search_todos",
  "description": "Search todos by text query",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "user_id": {"type": "string"}
    }
  }
}
```

### Chat Integration Examples

```
User: "Add a todo to call mom tomorrow"
Assistant: [Uses create_todo MCP tool]
Response: "✅ I've added 'Call mom' to your todo list for tomorrow."

User: "What do I need to do today?"
Assistant: [Uses list_todos with bucket='today']
Response: "You have 5 tasks for today:
1. Submit quarterly report (due 3pm) 🔴
2. Team meeting (due 2pm)
3. Review pull requests
..."

User: "Mark 'Submit quarterly report' as done"
Assistant: [Uses complete_todo]
Response: "✅ Great job! I've marked 'Submit quarterly report' as completed."
```

---

## Natural Language Processing

### Parser Implementation

```python
# todos/nlp_parser.py

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TodoNLPParser:
    """Parse natural language input into structured todo data."""

    # Priority markers
    PRIORITY_MARKERS = {
        '@high': 'high',
        '@urgent': 'urgent',
        '@medium': 'medium',
        '@low': 'low',
        '!': 'high',
        '!!': 'urgent'
    }

    # Date patterns
    DATE_PATTERNS = {
        r'today': lambda: datetime.now(),
        r'tomorrow': lambda: datetime.now() + timedelta(days=1),
        r'next week': lambda: datetime.now() + timedelta(weeks=1),
        r'monday|tuesday|wednesday|thursday|friday|saturday|sunday': 'parse_weekday',
        r'in (\d+) days?': 'parse_relative_days',
        r'(\d{4})-(\d{2})-(\d{2})': 'parse_iso_date',
    }

    # Time patterns
    TIME_PATTERNS = {
        r'(\d{1,2}):(\d{2})\s*(am|pm)?': 'parse_time',
        r'(\d{1,2})\s*(am|pm)': 'parse_simple_time',
    }

    def parse(self, input_text: str) -> Dict:
        """Parse natural language input into todo structure."""
        result = {
            'title': '',
            'tags': [],
            'priority': 'medium',
            'due_date': None,
            'due_time': None,
            'bucket': 'inbox'
        }

        # Extract tags (#tag)
        tags = re.findall(r'#(\w+)', input_text)
        result['tags'] = tags

        # Extract priority markers
        for marker, priority in self.PRIORITY_MARKERS.items():
            if marker in input_text:
                result['priority'] = priority
                input_text = input_text.replace(marker, '')

        # Extract date
        date_info = self._extract_date(input_text)
        if date_info:
            result['due_date'] = date_info['date']
            result['bucket'] = self._determine_bucket(date_info['date'])
            input_text = date_info['remaining_text']

        # Extract time
        time_info = self._extract_time(input_text)
        if time_info:
            result['due_time'] = time_info['time']
            input_text = time_info['remaining_text']

        # Clean up title
        result['title'] = self._clean_title(input_text)

        return result
```

---

## UI Components

### Sidebar Integration

Add to Lists submenu (after Opportunities):

```html
<!-- In index.html, within lists-submenu -->
<button class="sub-nav-item expandable-nav-item ..." data-list="todos">
    <span class="flex items-center justify-between">
        <span class="flex items-center">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round"
                      stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
            </svg>
            TODO Lists
        </span>
        <svg class="w-3 h-3 expand-icon transition-transform" ...>
            <path d="M19 9l-7 7-7-7"/>
        </svg>
    </span>
</button>

<!-- TODO Lists dropdown -->
<div id="todo-lists-dropdown" class="ml-6 mt-1 space-y-1 hidden">
    <!-- Dynamic todo lists will be populated here -->
</div>
```

### Main View Components

```html
<!-- TODO List Main View -->
<div id="todos-view" class="main-view hidden">
    <!-- Header -->
    <div class="view-header">
        <h2>TODO Lists</h2>
        <button id="create-todo-btn">+ New Todo</button>
    </div>

    <!-- Bucket Tabs -->
    <div class="bucket-tabs">
        <button class="bucket-tab active" data-bucket="today">Today</button>
        <button class="bucket-tab" data-bucket="upcoming">Upcoming</button>
        <button class="bucket-tab" data-bucket="inbox">Inbox</button>
        <button class="bucket-tab" data-bucket="someday">Someday</button>
    </div>

    <!-- Quick Add (Natural Language) -->
    <div class="quick-add">
        <input type="text" placeholder="Add a task... (e.g., 'Call mom tomorrow @high #personal')" />
    </div>

    <!-- Todo List -->
    <div class="todos-container">
        <!-- Todos will be rendered here -->
    </div>

    <!-- List View Selector -->
    <div class="view-selector">
        <button data-view="list">List</button>
        <button data-view="kanban">Kanban</button>
        <button data-view="calendar">Calendar</button>
    </div>
</div>
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal**: Basic TODO CRUD operations

**Tasks**:
1. Create `/todos` directory structure
2. Implement database schema and migrations
3. Create data models (`models.py`)
4. Implement database operations (`database.py`)
5. Create basic manager (`manager.py`)
6. Add route handlers (`server/routes/todos.py`)
7. Register routes in `server.py` **WITHOUT** modifying existing routes
8. Create unit tests

**Deliverables**:
- Working API endpoints for basic CRUD
- SQLite database with proper indexes
- Comprehensive tests
- CLAUDE.md in `/todos` directory

**Safety Checks**:
- ✅ No modifications to existing service files
- ✅ Separate database file (todos.db)
- ✅ Isolated route registration
- ✅ All files under 500 lines

### Phase 2: Multi-User & Lists (Week 2)
**Goal**: User management and list organization

**Tasks**:
1. Implement user management
2. Add todo lists functionality
3. Implement list sharing
4. Add tag management
5. Create history tracking
6. Update API endpoints
7. Add authentication/authorization
8. Create tests for multi-user scenarios

**Deliverables**:
- User CRUD operations
- Todo lists with sharing
- Tag management
- Audit trail

**Safety Checks**:
- ✅ User isolation working correctly
- ✅ No data leakage between users
- ✅ Proper foreign key constraints

### Phase 3: Natural Language Processing (Week 3)
**Goal**: Smart task creation with NLP

**Tasks**:
1. Implement NLP parser (`nlp_parser.py`)
2. Add date/time extraction
3. Add priority detection
4. Add tag extraction
5. Integrate with Ollama for advanced NLP (optional)
6. Create parse endpoint
7. Update create_todo to support NLP input
8. Add comprehensive NLP tests

**Deliverables**:
- Working NLP parser
- Support for natural language in create_todo
- Fallback to structured input
- NLP accuracy tests

**Safety Checks**:
- ✅ Graceful fallback if NLP fails
- ✅ No breaking changes to API
- ✅ Optional Ollama integration (not required)

### Phase 4: MCP Integration (Week 4)
**Goal**: Expose todos via MCP tools

**Tasks**:
1. Create MCP tool definitions (`mcp_tools.py`)
2. Implement tool handlers
3. Register MCP server
4. Test tools with chat interface
5. Add error handling for MCP calls
6. Create MCP documentation
7. Add integration tests

**Deliverables**:
- 6+ MCP tools exposed
- Chat integration working
- Error handling
- MCP tool documentation

**Safety Checks**:
- ✅ No interference with existing MCP servers
- ✅ Proper error responses
- ✅ Tool isolation

### Phase 5: UI Implementation (Week 5)
**Goal**: Rich UI for todo management

**Tasks**:
1. Add sidebar navigation
2. Create main todo view
3. Implement bucket tabs
4. Add quick-add input
5. Create todo list rendering
6. Implement inline editing
7. Add drag-and-drop reordering
8. Create modal for detailed editing
9. Add view switcher (list/kanban/calendar)
10. Style with Tailwind CSS

**Deliverables**:
- Complete UI in sidebar
- Multiple view modes
- Responsive design
- Keyboard shortcuts

**Safety Checks**:
- ✅ No conflicts with existing UI
- ✅ Consistent styling
- ✅ Mobile responsive

### Phase 6: Advanced Features (Week 6)
**Goal**: Power user features

**Tasks**:
1. Implement recurring todos
2. Add subtasks support
3. Create reminder system
4. Add search functionality
5. Implement filters and sorting
6. Add bulk operations
7. Create export functionality
8. Add keyboard shortcuts
9. Implement undo/redo

**Deliverables**:
- Recurring tasks
- Nested subtasks
- Advanced search
- Power user features

### Phase 7: Testing & Optimization (Week 7)
**Goal**: Production readiness

**Tasks**:
1. Comprehensive integration tests
2. Performance testing
3. Database optimization
4. Code review and refactoring
5. Documentation completion
6. Security audit
7. Multi-user stress testing
8. Browser compatibility testing

**Deliverables**:
- 90%+ test coverage
- Performance benchmarks
- Security review
- Complete documentation

---

## Critical Safeguards

### Lessons from First Attempt

**What Broke Before**:
1. Modified existing service files directly
2. Shared database tables with existing features
3. Changed route registration logic
4. No isolation between features

**How We'll Prevent It**:

1. **Isolated File Structure**
   - All TODO code in `/todos` directory
   - Separate database file (`todos.db`)
   - Own route handler file (`server/routes/todos.py`)
   - No modifications to existing files except minimal imports

2. **Clean Route Registration**
   ```python
   # In server.py - ADD ONLY, don't modify existing

   # Import TODO routes (new section)
   try:
       from server.routes.todos import (
           handle_todos_list_api,
           handle_todos_create_api,
           # ... other handlers
       )
       TODOS_AVAILABLE = True
   except ImportError:
       TODOS_AVAILABLE = False

   # In do_POST method - ADD at end of elif chain
   elif self.path == '/api/todos' and TODOS_AVAILABLE:
       handle_todos_list_api(self)
   elif self.path.startswith('/api/todos/') and TODOS_AVAILABLE:
       # Handle specific todo routes
       ...
   ```

3. **Database Isolation**
   - Use separate `todos.db` file
   - No foreign keys to other databases
   - Self-contained schema
   - Optional integration via API only

4. **Module Independence**
   ```python
   # todos/__init__.py
   """
   TODO List module - completely independent feature.
   Can be disabled by removing TODOS_AVAILABLE flag.
   """

   # All imports are self-contained
   # No dependencies on other features except:
   # - debug_logger (logging only)
   # - ollama_config (optional NLP only)
   ```

5. **Feature Flag**
   - `TODOS_AVAILABLE` flag to enable/disable
   - Graceful degradation if disabled
   - No impact on other features if unavailable

6. **Testing Strategy**
   - Test with feature enabled
   - Test with feature disabled
   - Test that disabling doesn't break app
   - Test that other features work independently

---

## Configuration

### todos/config.py

```python
"""Configuration for TODO list feature."""

import os
from pathlib import Path

# Database configuration
TODOS_DB_PATH = os.getenv('TODOS_DB_PATH', 'todos.db')

# Feature flags
ENABLE_NLP = os.getenv('TODOS_ENABLE_NLP', 'true').lower() == 'true'
ENABLE_OLLAMA_NLP = os.getenv('TODOS_ENABLE_OLLAMA', 'false').lower() == 'true'

# Limits (for 5-user scale)
MAX_USERS = int(os.getenv('TODOS_MAX_USERS', '5'))
MAX_LISTS_PER_USER = int(os.getenv('TODOS_MAX_LISTS', '50'))
MAX_TODOS_PER_LIST = int(os.getenv('TODOS_MAX_TODOS', '1000'))

# NLP configuration
NLP_DATE_LOOKAHEAD_DAYS = int(os.getenv('TODOS_NLP_LOOKAHEAD', '90'))

# Default values
DEFAULT_BUCKET = 'inbox'
DEFAULT_PRIORITY = 'medium'
DEFAULT_STATUS = 'pending'

# Color palette for lists
LIST_COLORS = [
    '#EF4444',  # Red
    '#F59E0B',  # Amber
    '#10B981',  # Green
    '#3B82F6',  # Blue
    '#8B5CF6',  # Purple
    '#EC4899',  # Pink
]
```

### Port Configuration

As per CLAUDE.md requirement, all TODO endpoints will run on **port 9090** alongside existing services.

---

## Testing Strategy

### Unit Tests

```python
# tests/test_todos_database.py
def test_create_todo():
    """Test creating a new todo."""
    pass

def test_list_todos_by_user():
    """Test listing todos filtered by user."""
    pass

def test_update_todo_status():
    """Test updating todo status."""
    pass

# tests/test_todos_nlp.py
def test_parse_date_today():
    """Test parsing 'today' in input."""
    pass

def test_parse_priority_markers():
    """Test parsing @high, @urgent markers."""
    pass

# tests/test_todos_api.py
def test_create_todo_endpoint():
    """Test POST /api/todos."""
    pass

def test_isolation_from_other_features():
    """Test that todos don't interfere with other features."""
    pass
```

### Integration Tests

```python
def test_chat_integration():
    """Test creating todo via chat MCP tool."""
    pass

def test_multi_user_isolation():
    """Test that users can't see each other's todos."""
    pass

def test_list_sharing():
    """Test sharing a list between users."""
    pass
```

---

## Success Criteria

### Functional Requirements
- ✅ Create, read, update, delete todos
- ✅ Natural language input support
- ✅ Multi-user with isolation
- ✅ Todo lists organization
- ✅ Tags and filtering
- ✅ Multiple view modes
- ✅ MCP integration for chat access
- ✅ Team collaboration (shared lists)

### Technical Requirements
- ✅ No file exceeds 500 lines
- ✅ Separate database file
- ✅ Zero cost (local only)
- ✅ All endpoints on port 9090
- ✅ MCP tools exposed
- ✅ 90%+ test coverage
- ✅ No breaking changes to existing features

### Quality Requirements
- ✅ Response time < 200ms for CRUD operations
- ✅ Supports up to 5 users efficiently
- ✅ Mobile-responsive UI
- ✅ Keyboard shortcuts
- ✅ Graceful error handling
- ✅ Comprehensive documentation

---

## Risk Mitigation

### Risk 1: Breaking Existing Services
**Mitigation**:
- Separate database file
- Isolated module structure
- Feature flag for easy disable
- No modifications to existing code
- Comprehensive regression tests

### Risk 2: Performance Degradation
**Mitigation**:
- Database indexes on all query fields
- Pagination for large lists
- Lazy loading in UI
- Performance benchmarks
- Query optimization

### Risk 3: User Data Conflicts
**Mitigation**:
- Strong user isolation
- Foreign key constraints
- Transaction management
- Audit trail
- Data validation

### Risk 4: MCP Integration Issues
**Mitigation**:
- Separate MCP server for todos
- Error handling in all tools
- Fallback mechanisms
- Comprehensive tool tests
- Clear error messages

---

## Future Enhancements

### Phase 8+ (Post-MVP)
1. **Calendar Integration**
   - Sync with external calendars
   - Visual calendar view
   - Time blocking

2. **Mobile App**
   - Progressive Web App (PWA)
   - Offline support
   - Push notifications

3. **Advanced Collaboration**
   - Real-time updates (WebSockets)
   - Comments on todos
   - Activity feed
   - @mentions

4. **Productivity Features**
   - Pomodoro timer integration
   - Time tracking
   - Productivity analytics
   - Focus mode

5. **Integrations**
   - Email integration
   - Slack notifications
   - GitHub issues sync
   - Import from other tools

6. **AI Enhancements**
   - Smart prioritization
   - Task breakdown suggestions
   - Deadline prediction
   - Workload balancing

---

## References

### Industry Research
- [Todoist Review 2025](https://www.joshdolin.com/mindscapes-blog/todoist-review-2025)
- [TickTick Features](https://ticktick.com/features)
- [Things 3 Review](https://thedigitalprojectmanager.com/tools/things-3-review/)
- [Todoist vs TickTick Comparison](https://zapier.com/blog/ticktick-vs-todoist/)
- [TickTick vs Things 3](https://nerdynav.com/ticktick-vs-things-3/)

### Video Reviews
- MKBHD (Marques Brownlee) - TickTick user and advocate
- Francesco D'Alessio (Keep Productive) - Comprehensive app reviews
- Mark Ellis Reviews - Task app comparisons

### Technical Documentation
- SQLite: https://www.sqlite.org/docs.html
- MCP Protocol: Internal documentation
- Ollama NLP: https://ollama.ai/docs

---

## Conclusion

This implementation plan provides a comprehensive roadmap for building a production-ready TODO list feature that:

1. **Learns from industry leaders** (Todoist, TickTick, Things 3)
2. **Maintains system integrity** (isolated, modular, tested)
3. **Supports the team** (multi-user, collaboration)
4. **Integrates seamlessly** (MCP, Chat, UI)
5. **Scales appropriately** (5-user optimization)
6. **Follows best practices** (zero-cost, local-first, well-documented)

The modular architecture ensures that this feature can be developed, tested, and deployed without risking the stability of existing services - addressing the critical lesson learned from the first implementation attempt.

**Next Steps**:
1. Review and approve this plan
2. Begin Phase 1 implementation
3. Incremental testing at each phase
4. User feedback after each phase
5. Iterate based on real-world usage

---

**Document Version**: 2.0
**Last Updated**: December 15, 2025
**Status**: Ready for Implementation
**Estimated Timeline**: 7 weeks to MVP, with phased rollout
