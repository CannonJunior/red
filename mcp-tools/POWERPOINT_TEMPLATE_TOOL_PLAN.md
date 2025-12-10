# PowerPoint Template Filling MCP Tool - Implementation Plan

**Date**: 2025-12-08
**Status**: Research & Planning Phase
**Goal**: Create MCP tool that fills PowerPoint templates with data extracted from document folders

---

## 1. RESEARCH SUMMARY

### 1.1 Claude.ai PowerPoint Capabilities

Based on research, Claude.ai (2025) offers:

- **Cross-format work**: Upload PDF reports, get PowerPoint slides ([Anthropic News](https://www.anthropic.com/news/create-files))
- **Template preservation**: Updates content while preserving layout, colors, fonts ([SlideSpeak](https://slidespeak.co/blog/2025/07/21/create-ai-presentations-in-claude-using-mcp/))
- **Technical approach**: Sandboxed Python/JavaScript execution environment ([TechRepublic](https://www.techrepublic.com/article/news-anthropic-update-transforms-claude/))
- **File limits**: 30MB max per file, practical for tens to ~100 slides ([SmartScope](https://smartscope.blog/en/generative-ai/claude/claude-pptx-skill-practical-guide/))
- **Availability**: Claude Pro/Max/Team/Enterprise only ([Skywork AI](https://skywork.ai/blog/in-depth-claude-spreadsheets-documents-powerpoint-slide-decks-2025-review-is-it-worth-the-hype/))

**Key Insight**: Claude uses code execution (Python) to manipulate PowerPoint files, not direct API access.

### 1.2 Open Source MCP PowerPoint Tools

#### Office-PowerPoint-MCP-Server by GongRzhe
- **32 tools in 11 modules**: Comprehensive coverage ([GitHub](https://github.com/GongRzhe/Office-PowerPoint-MCP-Server))
- **Round-trip support**: Template preservation with automatic theme/layout maintenance
- **Modules**: Presentation management, slides, templates, tables/shapes/charts, themes, hyperlinks, connectors, slide masters, transitions
- **License**: MIT

#### powerpoint-mcp by Ichigo3766
- **Fork with enhancements**: Stable Diffusion integration ([GitHub](https://github.com/Ichigo3766/powerpoint-mcp))
- **Multiple slide types**: Title, content, tables, charts, pictures with captions
- **Template support**: Can work with existing .pptx and add slides

#### pptx-xlsx-mcp by jenstangen1
- **COM automation**: Uses pywin32 for Office integration ([GitHub](https://github.com/jenstangen1/pptx-xlsx-mcp))
- **Platform limitation**: Windows-only

### 1.3 Python-pptx Library Best Practices

#### Core Capabilities ([python-pptx docs](https://python-pptx.readthedocs.io/))
- **Placeholder system**: Content boxes at specific positions (title, subtitle, body, images, tables) ([Placeholders Guide](https://python-pptx.readthedocs.io/en/latest/user/placeholders-using.html))
- **Template loading**: Load existing presentations as bases ([CodeRivers](https://coderivers.org/blog/pptx-python/))
- **Text replacement**: Simple string mapping and replacement ([Medium - Alexander Stock](https://medium.com/@alexaae9/effortlessly-replace-text-in-powerpoint-presentations-using-python-5cdc0ee912a3))

#### Critical Limitations
- **Placeholder invalidation**: References become invalid after insert_picture/insert_table ([SoftKraft](https://www.softkraft.co/python-powerpoint-automation/))
- **Formatting loss**: Text assignment replaces all previous formatting
- **No undo**: Changes are permanent once saved

### 1.4 Document Extraction Libraries

#### For Multi-format Support
- **LlamaIndex SimpleDirectoryReader**: Word, PDF, txt, CSV ([Medium - Thomas Jaensch](https://medium.com/@tebugging/summarize-any-text-based-document-with-8-lines-of-python-and-llamaindex-17335986877b))
- **PyMuPDF4LLM**: Markdown extraction with metadata ([PyMuPDF Docs](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/))
- **python-docx + PyPDF2**: Already used in whitepaper-review
- **docx2txt + pypdf**: Lightweight alternatives

#### LLM Integration for Data Extraction
- **LangChain**: Document loaders and summarization chains ([Medium - Francis Benistant](https://2020machinelearning.medium.com/building-a-local-pdf-summarizer-with-llms-from-theory-to-implementation-b2222cdb402e))
- **Ollama**: Zero-cost local LLM (already in use) ([Vincent Codes Finance](https://vincent.codes.finance/posts/documents-llm/))
- **Structured output**: JSON mode for extracting key-value pairs

---

## 2. ARCHITECTURAL ANALYSIS

### 2.1 Existing White Paper Review Pattern

**File**: `mcp-tools/whitepaper_review_server.py`

**Architecture**:
```
WhitePaperReviewServer
├── __init__: Configuration (ollama_url, model, timeout)
├── _register_tools: Decorator-based MCP tool registration
├── _load_document_or_directory: Multi-format document loading
├── _load_single_document: Format-specific extraction
├── _perform_review: LLM interaction via Ollama
└── _format_output: Markdown/JSON/text formatting
```

**UI Configuration**: `project_tools_config.json`
```json
{
  "id": "whitepaper-review",
  "required_inputs": [file selectors],
  "optional_inputs": [model, timeout],
  "environment": {env vars},
  "transport": "stdio"
}
```

**Frontend Integration**: `app.js`
- Autocomplete via `#whitepaper-review` trigger
- Modal form with file pickers
- `executeMCPTool()` sends to backend
- Backend `handle_mcp_tool_call()` executes Python server

### 2.2 Proposed PowerPoint Tool Architecture

```
PowerPointTemplateServer
├── __init__: Configuration
├── _register_tools: MCP tool registration
│   ├── fill_template: Main tool
│   └── batch_fill: Multi-template processing
├── _load_template: Load .pptx template
├── _extract_placeholders: Detect {{placeholder}} markers
├── _load_documents_from_folder: Multi-format extraction
├── _extract_data_with_llm: LLM-based data extraction
├── _map_data_to_placeholders: Match extracted data to placeholders
├── _fill_placeholders: Update template with data
└── _save_presentation: Output filled .pptx
```

---

## 3. DETAILED IMPLEMENTATION PLAN

### 3.1 MCP Tool Configuration

**File**: `mcp-tools/project_tools_config.json`

Add new tool:
```json
{
  "id": "powerpoint-template-fill",
  "name": "PowerPoint Template Fill",
  "description": "Fill PowerPoint template with data extracted from documents",
  "transport": "stdio",
  "command": "uv",
  "args": ["run", "mcp-tools/powerpoint_template_server.py"],
  "cwd": "/home/junior/src/red",
  "environment": {
    "OLLAMA_URL": "http://localhost:11434",
    "DEFAULT_MODEL": "qwen2.5:3b",
    "DEFAULT_TIMEOUT": "180"
  },
  "required_inputs": [
    {
      "name": "template_path",
      "label": "PowerPoint Template",
      "type": "file",
      "accept": ".pptx",
      "description": "PowerPoint template with {{placeholder}} markers"
    },
    {
      "name": "documents_folder",
      "label": "Documents Folder",
      "type": "directory",
      "description": "Folder containing source documents (.txt, .docx, .pdf)"
    }
  ],
  "optional_inputs": [
    {
      "name": "output_path",
      "label": "Output File",
      "type": "text",
      "default": "filled_presentation.pptx",
      "description": "Name for the output PowerPoint file"
    },
    {
      "name": "placeholder_style",
      "label": "Placeholder Format",
      "type": "select",
      "options": [
        {"value": "mustache", "label": "{{placeholder}} (Mustache)"},
        {"value": "bracket", "label": "[PLACEHOLDER] (Brackets)"},
        {"value": "custom", "label": "Custom regex"}
      ],
      "default": "mustache",
      "description": "Placeholder marker style in template"
    },
    {
      "name": "extraction_strategy",
      "label": "Data Extraction",
      "type": "select",
      "options": [
        {"value": "llm_smart", "label": "LLM Smart Extraction (Recommended)"},
        {"value": "llm_structured", "label": "LLM Structured Output"},
        {"value": "keyword_match", "label": "Keyword Matching"},
        {"value": "manual_map", "label": "Manual JSON Mapping"}
      ],
      "default": "llm_smart",
      "description": "How to extract data from documents"
    },
    {
      "name": "mapping_file",
      "label": "Manual Mapping (Optional)",
      "type": "file",
      "accept": ".json",
      "description": "JSON file mapping placeholders to document sections"
    },
    {
      "name": "model",
      "label": "LLM Model",
      "type": "select",
      "options": [
        {"value": "qwen2.5:3b", "label": "Qwen 2.5 3B (Fast)"},
        {"value": "qwen2.5:7b", "label": "Qwen 2.5 7B (Balanced)"},
        {"value": "llama3.1:8b", "label": "Llama 3.1 8B (Quality)"}
      ],
      "default": "qwen2.5:3b",
      "description": "LLM model for data extraction"
    },
    {
      "name": "timeout_seconds",
      "label": "Timeout (seconds)",
      "type": "number",
      "min": 60,
      "max": 600,
      "default": 180,
      "description": "Processing timeout (3 min default)"
    },
    {
      "name": "preserve_formatting",
      "label": "Preserve Formatting",
      "type": "checkbox",
      "default": true,
      "description": "Attempt to preserve template text formatting"
    }
  ]
}
```

### 3.2 Python MCP Server Implementation

**File**: `mcp-tools/powerpoint_template_server.py`

#### 3.2.1 Class Structure

```python
class PowerPointTemplateServer:
    """
    MCP server for filling PowerPoint templates with document data.

    Features:
    - Multi-format template support (.pptx)
    - Multi-format document extraction (.txt, .docx, .pdf)
    - LLM-powered intelligent data extraction
    - Flexible placeholder systems ({{mustache}}, [BRACKET], custom regex)
    - Batch processing for multiple templates
    - Zero-cost local operation
    """
```

#### 3.2.2 Core Methods

**Template Operations**:
- `_load_template(path)`: Load .pptx using python-pptx
- `_extract_placeholders(presentation, style)`: Scan all slides for placeholders
- `_save_presentation(presentation, output_path)`: Save filled presentation

**Document Processing**:
- `_load_documents_from_folder(folder_path)`: Load all supported formats
- `_extract_text_from_document(file_path)`: Per-file extraction (reuse from whitepaper)
- `_combine_documents(doc_list)`: Merge multiple documents intelligently

**LLM Data Extraction**:
- `_extract_data_with_llm(documents, placeholders, strategy)`:
  - Input: Combined document text + list of placeholder names
  - Process: Prompt LLM to extract relevant data for each placeholder
  - Output: Dictionary mapping placeholder names to extracted content

**Placeholder Filling**:
- `_map_data_to_placeholders(extracted_data, placeholders)`: Match data to slots
- `_fill_text_placeholder(shape, text, preserve_formatting)`: Update text boxes
- `_fill_table_placeholder(table, data)`: Update table cells
- `_fill_chart_placeholder(chart, data)`: Update chart data (future)
- `_fill_image_placeholder(placeholder, image_path)`: Insert images

#### 3.2.3 LLM Prompt Strategy

**Approach 1: Smart Extraction (Recommended)**
```
You are a data extraction assistant. Given the following documents and
placeholder names from a PowerPoint template, extract the most relevant
content for each placeholder.

PLACEHOLDERS:
- {{company_name}}
- {{q4_revenue}}
- {{top_3_achievements}}

DOCUMENTS:
[Combined document text]

For each placeholder, provide:
1. The extracted content (1-2 sentences or specific data point)
2. Confidence level (high/medium/low)
3. Source location (document name + section)

Return as JSON.
```

**Approach 2: Structured Output**
```
Extract structured data from documents using JSON schema:
{
  "company_name": {"value": "", "confidence": "", "source": ""},
  "q4_revenue": {"value": "", "confidence": "", "source": ""}
}
```

**Approach 3: Keyword Matching** (fallback, no LLM)
- Use fuzzy string matching to find placeholder keywords in documents
- Extract surrounding sentences

#### 3.2.4 Error Handling

- **Missing placeholders**: Warn user, leave unfilled
- **Failed data extraction**: Return placeholder name as-is with warning
- **LLM timeout**: Fall back to keyword matching
- **Invalid template**: Validate .pptx structure before processing
- **Partial fills**: Allow saving partially filled presentations

### 3.3 Frontend Integration

**File**: `app.js`

Add to `selectMCPTool()` and `executeMCPTool()`:
- Handle directory input type (new)
- File path validation for templates
- Progress indicator for long operations
- Preview of extracted placeholders before filling (optional)

### 3.4 Backend Server Integration

**File**: `server.py`

Add to `handle_mcp_tool_call()`:
- Case for `powerpoint-template-fill`
- Import and instantiate `PowerPointTemplateServer`
- Handle directory paths (not just files)
- Return filled .pptx file (download link or base64)

### 3.5 Dependencies

**New packages** (add to pyproject.toml via `uv add`):
```
python-pptx>=1.0.0  # PowerPoint manipulation
Pillow>=10.0.0      # Image handling (if needed)
```

**Already available**:
- mcp (MCP SDK)
- python-docx (Word documents)
- PyPDF2 (PDF extraction)
- urllib (Ollama API)

---

## 4. IMPLEMENTATION PHASES

### Phase 1: Core Template Filling (MVP)
**Goal**: Basic placeholder replacement with manual JSON mapping

**Features**:
- Load .pptx template
- Extract {{mustache}} style placeholders
- Load manual JSON mapping file
- Fill text placeholders only
- Save output .pptx

**Timeline**: 1-2 hours
**Risk**: Low

### Phase 2: Document Extraction
**Goal**: Auto-load documents from folder

**Features**:
- Load all documents from folder
- Extract text from .txt, .docx, .pdf
- Combine into searchable corpus

**Timeline**: 1 hour
**Risk**: Low (reuse whitepaper code)

### Phase 3: LLM Smart Extraction
**Goal**: Intelligent data extraction using Ollama

**Features**:
- Detect placeholder names
- Prompt LLM with documents + placeholders
- Parse LLM response into key-value pairs
- Map to template placeholders

**Timeline**: 2-3 hours
**Risk**: Medium (prompt engineering)

### Phase 4: Advanced Features
**Goal**: Tables, charts, images, batch processing

**Features**:
- Table cell filling
- Chart data updates
- Image placeholder filling
- Batch process multiple templates
- Multiple placeholder styles ([BRACKET], custom regex)

**Timeline**: 3-4 hours per feature
**Risk**: Medium-High (python-pptx complexity)

### Phase 5: UI Polish
**Goal**: Better UX

**Features**:
- Placeholder preview before filling
- Confidence scores display
- Download link for output file
- Error reporting with suggestions

**Timeline**: 2 hours
**Risk**: Low

---

## 5. CRITICAL REVIEW & IMPROVEMENTS

### 5.1 Architectural Concerns

#### ❌ **PROBLEM: Tight Coupling to PowerPoint**
**Current Plan**: `PowerPointTemplateServer` is PowerPoint-specific

**Issue**:
- Similar tools could be needed for Word templates, Excel templates, Google Slides
- Code duplication across template types
- Violates DRY principle

**IMPROVEMENT**:
```python
# Abstract base class
class TemplateFillingServer:
    """Generic template filling server"""
    def _load_template(self, path): ...
    def _extract_placeholders(self, template): ...
    def _fill_placeholders(self, template, data): ...
    def _save_output(self, template, output_path): ...

# Concrete implementations
class PowerPointTemplateServer(TemplateFillingServer):
    """PowerPoint-specific implementation"""

class WordTemplateServer(TemplateFillingServer):
    """Word-specific implementation"""

class ExcelTemplateServer(TemplateFillingServer):
    """Excel-specific implementation"""
```

**Benefits**:
- Shared document extraction logic
- Shared LLM extraction logic
- Easy to add new template types
- Reduced maintenance burden

#### ❌ **PROBLEM: LLM Extraction is Monolithic**
**Current Plan**: Single `_extract_data_with_llm()` method

**Issue**:
- Different extraction strategies have different implementations
- Hard to test individual strategies
- Hard to add new strategies
- No fallback mechanism

**IMPROVEMENT**: Strategy Pattern
```python
class ExtractionStrategy(ABC):
    @abstractmethod
    async def extract(self, documents, placeholders): ...

class LLMSmartExtraction(ExtractionStrategy):
    async def extract(self, documents, placeholders):
        # Smart LLM extraction with confidence scoring

class LLMStructuredExtraction(ExtractionStrategy):
    async def extract(self, documents, placeholders):
        # JSON schema-based extraction

class KeywordMatchingExtraction(ExtractionStrategy):
    async def extract(self, documents, placeholders):
        # Fuzzy matching fallback

class ManualMappingExtraction(ExtractionStrategy):
    async def extract(self, documents, placeholders):
        # Load from JSON file

# Server uses composition
class PowerPointTemplateServer:
    def __init__(self, extraction_strategy: ExtractionStrategy):
        self.strategy = extraction_strategy
```

**Benefits**:
- Easy to test each strategy independently
- Easy to add new strategies
- Clear separation of concerns
- Can chain strategies (try LLM, fallback to keyword)

#### ❌ **PROBLEM: Document Loading is Copy-Pasted**
**Current Plan**: Copy `_load_document_or_directory()` from whitepaper_review_server.py

**Issue**:
- Code duplication
- Bug fixes must be applied twice
- Inconsistent behavior across tools

**IMPROVEMENT**: Shared Document Processing Module
```python
# mcp-tools/common/document_loader.py
class DocumentLoader:
    """Shared document loading utilities"""

    @staticmethod
    async def load_from_path(path: str, formats: List[str] = None):
        """Load single file or directory"""

    @staticmethod
    async def load_single_file(path: str):
        """Load single file based on extension"""

    @staticmethod
    def get_supported_formats():
        """Return list of supported formats"""

# Usage in both servers
from common.document_loader import DocumentLoader

class WhitePaperReviewServer:
    async def _load_document(self, path):
        return await DocumentLoader.load_from_path(path)

class PowerPointTemplateServer:
    async def _load_documents(self, folder_path):
        return await DocumentLoader.load_from_path(folder_path)
```

**Benefits**:
- Single source of truth
- Easier to add new formats (one place)
- Consistent error handling
- Shared caching layer (future)

#### ❌ **PROBLEM: No Configuration Management**
**Current Plan**: Hard-coded environment variables

**Issue**:
- Each tool duplicates environment setup
- No way to override defaults per-user
- No validation of configuration

**IMPROVEMENT**: Shared Configuration Module
```python
# mcp-tools/common/config.py
from pydantic import BaseSettings, validator

class MCPToolConfig(BaseSettings):
    """Shared configuration for all MCP tools"""
    ollama_url: str = "http://localhost:11434"
    default_model: str = "qwen2.5:3b"
    default_timeout: int = 120
    max_file_size_mb: int = 100
    supported_formats: List[str] = [".txt", ".pdf", ".docx"]

    @validator("ollama_url")
    def validate_url(cls, v):
        # Validate URL format
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Usage
from common.config import MCPToolConfig

class PowerPointTemplateServer:
    def __init__(self):
        self.config = MCPToolConfig()
        self.ollama_url = self.config.ollama_url
```

**Benefits**:
- Type-safe configuration
- Environment variable support
- Validation at startup
- Easy to test with mock configs
- Single place to update defaults

### 5.2 Data Flow Concerns

#### ❌ **PROBLEM: File Return Mechanism Unclear**
**Current Plan**: Return filled .pptx somehow

**Issue**:
- How does user get the file?
- Store on disk? Return base64? Stream?
- What about file cleanup?
- Security implications of file storage

**IMPROVEMENT**: Clear Output Strategy
```python
# Option 1: Save to uploads/ directory with unique ID
output_path = f"/home/junior/src/red/uploads/{unique_id}_filled.pptx"
presentation.save(output_path)
return {
    "status": "success",
    "download_url": f"/api/download/{unique_id}_filled.pptx",
    "file_size": os.path.getsize(output_path),
    "expires_in": "24 hours"
}

# Option 2: Return base64 (small files only)
with open(output_path, 'rb') as f:
    b64_data = base64.b64encode(f.read()).decode()
return {
    "status": "success",
    "file_data": b64_data,
    "file_name": "filled.pptx"
}

# Option 3: Hybrid (use size threshold)
if file_size < 5MB:
    return base64
else:
    return download_url
```

**Recommendation**: Option 3 (Hybrid) with cleanup cron job

#### ❌ **PROBLEM: No Validation of Template Structure**
**Current Plan**: Assume template is valid

**Issue**:
- User uploads corrupt .pptx
- User uploads wrong file type
- Template has no placeholders
- Wasted processing time

**IMPROVEMENT**: Pre-flight Validation
```python
async def _validate_template(self, template_path: str):
    """Validate template before processing"""

    # Check file exists
    if not Path(template_path).exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Check file extension
    if not template_path.endswith('.pptx'):
        raise ValueError("Template must be .pptx format")

    # Check file size
    size_mb = Path(template_path).stat().st_size / (1024 * 1024)
    if size_mb > self.config.max_file_size_mb:
        raise ValueError(f"Template too large: {size_mb:.1f}MB (max {self.config.max_file_size_mb}MB)")

    # Try to load
    try:
        presentation = Presentation(template_path)
    except Exception as e:
        raise ValueError(f"Invalid PowerPoint file: {str(e)}")

    # Check for placeholders
    placeholders = self._extract_placeholders(presentation, style="mustache")
    if len(placeholders) == 0:
        raise ValueError("No placeholders found in template. Use {{placeholder}} format.")

    return {
        "valid": True,
        "slide_count": len(presentation.slides),
        "placeholder_count": len(placeholders),
        "placeholders": list(placeholders.keys())
    }
```

**Benefits**:
- Fail fast with clear error messages
- Better UX (no wasted time)
- Return placeholder preview to user

### 5.3 Scalability Concerns

#### ❌ **PROBLEM: Synchronous Processing Blocks Server**
**Current Plan**: Handle in `handle_mcp_tool_call()` synchronously

**Issue**:
- Large documents + LLM processing takes minutes
- Server thread blocked during processing
- Can't handle concurrent requests
- Poor user experience (no progress updates)

**IMPROVEMENT**: Async Task Queue
```python
# Option 1: Simple background task with polling
import uuid
from threading import Thread

tasks = {}  # {task_id: {"status": "processing", "progress": 45, "result": None}}

def start_background_task(template_path, documents_folder, options):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "queued", "progress": 0}

    def run_task():
        try:
            tasks[task_id]["status"] = "processing"
            # Do actual work
            result = fill_template(...)
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["result"] = result
        except Exception as e:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = str(e)

    Thread(target=run_task, daemon=True).start()
    return task_id

# Frontend polls /api/task-status/{task_id}
```

**Benefits**:
- Non-blocking server
- Progress updates
- Can handle multiple concurrent tasks
- Better error recovery

#### ❌ **PROBLEM: No Caching of Document Extraction**
**Current Plan**: Re-extract documents every time

**Issue**:
- If user runs tool twice on same folder, documents are re-processed
- Wasted CPU and time
- LLM calls are expensive (even local)

**IMPROVEMENT**: Smart Caching
```python
import hashlib
import json
from pathlib import Path

class DocumentCache:
    def __init__(self, cache_dir=".cache/documents"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_folder_hash(self, folder_path):
        """Hash based on folder contents (files + mod times)"""
        folder = Path(folder_path)
        files = sorted(folder.glob("**/*"))
        hash_input = ""
        for f in files:
            if f.is_file():
                hash_input += f"{f.name}:{f.stat().st_mtime}:"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def get_cached_extraction(self, folder_path):
        """Get cached extracted text if available"""
        folder_hash = self.get_folder_hash(folder_path)
        cache_file = self.cache_dir / f"{folder_hash}.json"

        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        return None

    def save_extraction(self, folder_path, extracted_data):
        """Save extracted text to cache"""
        folder_hash = self.get_folder_hash(folder_path)
        cache_file = self.cache_dir / f"{folder_hash}.json"

        with open(cache_file, 'w') as f:
            json.dump(extracted_data, f)
```

**Benefits**:
- 10x+ speedup for repeat operations
- Reduces load on Ollama
- Cache invalidation based on file changes

### 5.4 User Experience Concerns

#### ❌ **PROBLEM: No Preview Before Filling**
**Current Plan**: Fill template immediately

**Issue**:
- User doesn't see what data was extracted
- No chance to review/edit before filling
- Mistakes are expensive (re-run entire process)

**IMPROVEMENT**: Two-Step Process
```
Step 1: Extract & Preview
- Load template, extract placeholders
- Load documents, extract data
- Show user mapping: {{company_name}} → "Acme Corp" (confidence: 95%)
- Allow user to edit extracted values
- Provide "Fill Template" button

Step 2: Fill & Download
- Use user-approved data
- Fill template
- Return download link
```

**Implementation**:
- Add `extract_preview` tool alongside `fill_template` tool
- Store extraction results in session/temp file
- Frontend shows editable table
- User clicks "Fill Template" → calls `fill_template` with edited data

#### ❌ **PROBLEM: Poor Error Messages**
**Current Plan**: Generic "MCP tool error"

**Issue**:
- User doesn't know what went wrong
- Can't fix the problem
- Wasted time debugging

**IMPROVEMENT**: Structured Error Responses
```python
class TemplateFillError(Exception):
    def __init__(self, error_type, message, suggestions=None, context=None):
        self.error_type = error_type  # "invalid_template", "extraction_failed", etc.
        self.message = message
        self.suggestions = suggestions or []
        self.context = context or {}
        super().__init__(message)

    def to_dict(self):
        return {
            "error": self.error_type,
            "message": self.message,
            "suggestions": self.suggestions,
            "context": self.context
        }

# Usage
raise TemplateFillError(
    error_type="no_placeholders_found",
    message="Template contains no placeholders",
    suggestions=[
        "Add {{placeholder}} markers to your template",
        "Check placeholder style setting (currently: mustache)",
        "View placeholder format examples"
    ],
    context={
        "template_path": template_path,
        "slide_count": len(presentation.slides)
    }
)
```

**Benefits**:
- Actionable error messages
- User can self-serve fixes
- Better debugging information

### 5.5 Testing Concerns

#### ❌ **PROBLEM: Hard to Test Without Real Files**
**Current Plan**: Manual testing with actual .pptx files

**Issue**:
- Slow test cycles
- Hard to test edge cases
- Brittle tests (depends on file system)

**IMPROVEMENT**: Mock-Based Unit Tests
```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_presentation():
    """Mock python-pptx Presentation object"""
    pres = Mock()
    pres.slides = [Mock(), Mock()]  # 2 slides
    # Mock text shapes with placeholders
    return pres

def test_extract_placeholders_mustache_style(mock_presentation):
    server = PowerPointTemplateServer()

    # Mock slide with text containing {{company_name}}
    mock_presentation.slides[0].shapes[0].text = "Welcome to {{company_name}}"

    placeholders = server._extract_placeholders(mock_presentation, "mustache")

    assert "company_name" in placeholders
    assert len(placeholders) == 1

def test_llm_extraction_with_timeout():
    server = PowerPointTemplateServer()

    with patch('urllib.request.urlopen', side_effect=TimeoutError):
        result = server._extract_data_with_llm(
            documents=["test doc"],
            placeholders=["company_name"],
            strategy="llm_smart"
        )

    # Should fall back to keyword matching
    assert result["strategy_used"] == "keyword_fallback"
```

**Benefits**:
- Fast tests (no file I/O)
- Repeatable
- Easy to test error conditions
- CI/CD friendly

---

## 6. RECOMMENDED IMPLEMENTATION ORDER

### Phase 0: Refactoring (DO FIRST)
**Goal**: Create shared infrastructure

1. Extract `DocumentLoader` from whitepaper_review_server.py → `mcp-tools/common/document_loader.py`
2. Create `MCPToolConfig` in `mcp-tools/common/config.py`
3. Create `ExtractionStrategy` base class in `mcp-tools/common/extraction_strategies.py`
4. Create `TemplateFillingServer` base class in `mcp-tools/common/template_server.py`
5. Update whitepaper_review_server.py to use shared modules (regression test)

**Why First**:
- Avoids duplicating code
- Sets up proper architecture
- Easier to build PowerPoint tool on solid foundation

### Phase 1: PowerPoint Tool (MVP)
**Goal**: Basic working tool

1. Create `PowerPointTemplateServer(TemplateFillingServer)`
2. Implement manual JSON mapping extraction only
3. Implement text placeholder filling only
4. Add to project_tools_config.json
5. Basic frontend integration
6. End-to-end test

### Phase 2: LLM Extraction
**Goal**: Smart extraction

1. Implement `LLMSmartExtraction` strategy
2. Implement `KeywordMatchingExtraction` fallback
3. Add extraction strategy selection to UI
4. Test with various document types

### Phase 3: Advanced Features
**Goal**: Production-ready

1. Implement validation and error handling
2. Add caching layer
3. Add two-step preview workflow
4. Implement table/chart filling
5. Add batch processing

### Phase 4: Polish
**Goal**: Great UX

1. Progress indicators
2. Better error messages
3. File download mechanism
4. Documentation and examples

---

## 7. RISKS & MITIGATIONS

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| python-pptx limitations (can't handle complex templates) | High | High | Test with real templates early; provide clear documentation on limitations |
| LLM extraction accuracy too low | Medium | High | Implement manual override; provide preview step; fall back to keyword matching |
| Large files cause timeout | Medium | Medium | Increase default timeout; implement chunking; add progress updates |
| Template format incompatibility | Low | Medium | Validate templates; provide template creation guide |
| User confusion about placeholder format | Medium | Low | Auto-detect multiple formats; provide clear examples in UI |
| File storage security issues | Low | High | Use unique IDs; implement expiration; validate paths; use uploads/ directory only |

---

## 8. SUCCESS METRICS

### Functional Requirements
- ✅ Fills PowerPoint template with data from documents
- ✅ Supports .txt, .docx, .pdf source documents
- ✅ Works with common placeholder formats
- ✅ Runs locally (zero-cost)
- ✅ Similar UX to whitepaper-review tool

### Performance Requirements
- Target: Process typical template (10 slides, 20 placeholders, 5 documents) in < 60 seconds
- LLM extraction should work with 90%+ accuracy for clear placeholders
- Support folders with 10-50 documents

### Code Quality Requirements
- Shared code modules to reduce duplication
- 80%+ test coverage for core logic
- Clear error messages with actionable suggestions
- Extensible architecture for future template types

---

## 9. FUTURE ENHANCEMENTS (Out of Scope for v1)

1. **Multi-language support**: Fill templates in different languages
2. **Image generation**: Use Stable Diffusion to generate placeholder images
3. **Chart data extraction**: Parse tables/charts from documents, fill PowerPoint charts
4. **Google Slides support**: Extend to Google Slides API
5. **Excel template filling**: Similar tool for Excel workbooks
6. **Word template filling**: Similar tool for Word documents (mail merge)
7. **Template marketplace**: Pre-built templates for common use cases
8. **Version control**: Track changes to templates and filled documents
9. **Collaboration**: Multiple users can review/edit extracted data before filling
10. **Advanced formatting**: Preserve complex formatting, animations, transitions

---

## 10. CONCLUSION

This plan provides a comprehensive roadmap for implementing a PowerPoint template filling MCP tool that:

✅ **Follows existing patterns**: Similar to whitepaper-review tool
✅ **Uses proven technologies**: python-pptx, Ollama, MCP SDK
✅ **Zero-cost operation**: All local, no API costs
✅ **Extensible architecture**: Easy to add Word, Excel, Google Slides
✅ **Production-ready**: Error handling, validation, caching, testing

**Key Innovation**: LLM-powered smart extraction eliminates manual data mapping, making this tool significantly more useful than traditional mail-merge solutions.

**Recommended Timeline**: 2-3 days for full implementation with all suggested improvements.

---

## SOURCES

### Claude.ai PowerPoint Research
- [Claude can now create and edit files | Anthropic](https://www.anthropic.com/news/create-files)
- [Create AI Presentations in Claude using MCP - SlideSpeak](https://slidespeak.co/blog/2025/07/21/create-ai-presentations-in-claude-using-mcp/)
- [Anthropic's Claude AI Can Now Create Spreadsheets & Presentations - TechRepublic](https://www.techrepublic.com/article/news-anthropic-update-transforms-claude/)
- [10x Your Productivity with Claude PPTX Skill - SmartScope](https://smartscope.blog/en/generative-ai/claude/claude-pptx-skill-practical-guide/)
- [In-Depth Claude Review 2025 - Skywork AI](https://skywork.ai/blog/in-depth-claude-spreadsheets-documents-powerpoint-slide-decks-2025-review-is-it-worth-the-hype/)

### Open Source MCP Tools
- [Office-PowerPoint-MCP-Server - GitHub](https://github.com/GongRzhe/Office-PowerPoint-MCP-Server)
- [powerpoint-mcp - GitHub](https://github.com/Ichigo3766/powerpoint-mcp)
- [pptx-xlsx-mcp - GitHub](https://github.com/jenstangen1/pptx-xlsx-mcp)
- [mcp-powerpoint - GitHub](https://github.com/islem-zaraa/mcp-powerpoint)

### Python-pptx Documentation
- [python-pptx Documentation](https://python-pptx.readthedocs.io/)
- [Working with placeholders - python-pptx](https://python-pptx.readthedocs.io/en/latest/user/placeholders-using.html)
- [Effortlessly Replace Text in PowerPoint Using Python - Medium](https://medium.com/@alexaae9/effortlessly-replace-text-in-powerpoint-presentations-using-python-5cdc0ee912a3)
- [7 Ways to Boost Productivity with Python PowerPoint Automation - SoftKraft](https://www.softkraft.co/python-powerpoint-automation/)
- [Working with PPTX in Python - CodeRivers](https://coderivers.org/blog/pptx-python/)

### Document Extraction & LLM Integration
- [Summarize any text based document with 8 lines of Python - Medium](https://medium.com/@tebugging/summarize-any-text-based-document-with-8-lines-of-python-and-llamaindex-17335986877b)
- [Summarize and query PDFs with AI using Ollama - Vincent Codes Finance](https://vincent.codes.finance/posts/documents-llm/)
- [Building a Local PDF Summarizer with LLMs - Medium](https://2020machinelearning.medium.com/building-a-local-pdf-summarizer-with-llms-from-theory-to-implementation-b2222cdb402e)
- [Using PyMuPDF4LLM - PyMuPDF Documentation](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)

---

**Next Steps**: Review this plan, discuss concerns, then proceed with Phase 0 (Refactoring) implementation.
