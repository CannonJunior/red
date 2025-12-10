# MCP Tools Shared Architecture Design
**Version**: 2.0
**Date**: 2025-12-08
**Status**: Architecture Design - Pre-Implementation

---

## Executive Summary

This document describes a **refactored, shared architecture** for all MCP tools in the RED project. The design eliminates code duplication, establishes common patterns, and enables rapid development of new tools through composition and inheritance.

**Key Principles**:
- **DRY (Don't Repeat Yourself)**: Shared infrastructure in `mcp-tools/common/`
- **Strategy Pattern**: Pluggable extraction strategies with automatic fall-through
- **Composition over Inheritance**: Mix-and-match capabilities
- **Zero-Cost**: All operations local, no cloud dependencies
- **Type Safety**: Pydantic models throughout
- **Testability**: Mock-friendly, dependency injection

---

## 1. ARCHITECTURE OVERVIEW

### 1.1 Directory Structure

```
mcp-tools/
├── common/                              # Shared infrastructure (NEW)
│   ├── __init__.py
│   ├── config.py                        # Shared configuration management
│   ├── document_loader.py               # Multi-format document loading
│   ├── extraction/                      # Extraction strategies package
│   │   ├── __init__.py
│   │   ├── base.py                      # Base strategy class
│   │   ├── llm_smart.py                 # LLM smart extraction
│   │   ├── llm_structured.py            # LLM JSON schema extraction
│   │   ├── keyword_matching.py          # Fuzzy keyword matching
│   │   ├── manual_mapping.py            # JSON file mapping
│   │   └── chain.py                     # Strategy chaining (fall-through)
│   ├── template_server.py               # Base template server class
│   ├── cache.py                         # Document caching layer
│   ├── errors.py                        # Custom exception classes
│   ├── validation.py                    # Input validation utilities
│   └── ollama_client.py                 # Ollama API wrapper
│
├── whitepaper_review_server.py          # REFACTORED to use common/
├── powerpoint_template_server.py        # NEW (PowerPoint filling)
├── word_template_server.py              # FUTURE (Word filling)
├── excel_template_server.py             # FUTURE (Excel filling)
├── project_tools_config.json            # Tool definitions
└── ARCHITECTURE_DESIGN.md               # This document
```

### 1.2 Module Responsibilities

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| `config.py` | Configuration management, environment variables | Pydantic |
| `document_loader.py` | Load documents from files/folders | python-docx, PyPDF2 |
| `extraction/` | Data extraction strategies | Ollama, document_loader |
| `template_server.py` | Base class for template filling | All common modules |
| `cache.py` | Hash-based caching with invalidation | hashlib, json |
| `errors.py` | Structured error types | - |
| `validation.py` | File/folder validation | pathlib |
| `ollama_client.py` | Type-safe Ollama API wrapper | urllib, Pydantic |

---

## 2. SHARED INFRASTRUCTURE DESIGN

### 2.1 Configuration Management (`common/config.py`)

**Purpose**: Single source of truth for all MCP tool settings

```python
from pydantic import BaseSettings, validator, Field
from typing import List, Optional
import os

class MCPToolConfig(BaseSettings):
    """
    Shared configuration for all MCP tools.

    Loads from environment variables with sensible defaults.
    All MCP tools should use this instead of hardcoded values.
    """

    # Ollama Configuration
    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint"
    )

    default_model: str = Field(
        default="qwen2.5:3b",
        description="Default LLM model for all tools"
    )

    available_models: List[str] = Field(
        default=["qwen2.5:3b", "qwen2.5:7b", "llama3.1:8b"],
        description="Available Ollama models"
    )

    # Timeout Configuration
    default_timeout: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Default timeout in seconds"
    )

    # File Handling
    max_file_size_mb: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum file size in MB"
    )

    max_folder_size_mb: int = Field(
        default=500,
        ge=10,
        le=2000,
        description="Maximum total folder size in MB"
    )

    supported_document_formats: List[str] = Field(
        default=[".txt", ".pdf", ".doc", ".docx"],
        description="Supported document formats"
    )

    supported_template_formats: List[str] = Field(
        default=[".pptx", ".docx", ".xlsx"],
        description="Supported template formats"
    )

    # Caching
    enable_cache: bool = Field(
        default=True,
        description="Enable document extraction caching"
    )

    cache_dir: str = Field(
        default=".cache/mcp_tools",
        description="Cache directory path"
    )

    cache_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Cache time-to-live in hours"
    )

    # Output Configuration
    output_dir: str = Field(
        default="uploads",
        description="Output directory for generated files"
    )

    output_cleanup_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Auto-delete outputs after N hours"
    )

    # LLM Extraction
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for extraction"
    )

    llm_top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="LLM top_p for extraction"
    )

    max_extraction_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max retries for LLM extraction"
    )

    # Validation
    @validator("ollama_url")
    def validate_ollama_url(cls, v):
        """Validate Ollama URL format"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("ollama_url must start with http:// or https://")
        return v.rstrip("/")

    @validator("cache_dir", "output_dir")
    def validate_paths(cls, v):
        """Ensure paths are relative (security)"""
        if os.path.isabs(v):
            raise ValueError(f"Paths must be relative, not absolute: {v}")
        return v

    class Config:
        env_file = ".env"
        env_prefix = "MCP_"  # Environment variables like MCP_OLLAMA_URL
        case_sensitive = False

# Singleton instance
_config_instance: Optional[MCPToolConfig] = None

def get_config() -> MCPToolConfig:
    """Get or create singleton config instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = MCPToolConfig()
    return _config_instance
```

**Benefits**:
- ✅ Type-safe configuration
- ✅ Automatic validation
- ✅ Environment variable support
- ✅ Single place to update defaults
- ✅ Easy to mock for testing

**Usage**:
```python
from common.config import get_config

config = get_config()
print(config.ollama_url)  # http://localhost:11434
print(config.max_file_size_mb)  # 100
```

---

### 2.2 Document Loader (`common/document_loader.py`)

**Purpose**: Unified document loading for all MCP tools

```python
from pathlib import Path
from typing import Dict, List, Optional, Union, Literal
from dataclasses import dataclass
import asyncio
import mimetypes

# Document processing libraries
import docx
from PyPDF2 import PdfReader

from .config import get_config
from .errors import DocumentLoadError
from .cache import DocumentCache

@dataclass
class DocumentMetadata:
    """Metadata about a loaded document"""
    file_path: str
    file_name: str
    file_size: int
    format: str
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    char_count: int = 0
    load_time_ms: float = 0.0

@dataclass
class LoadedDocument:
    """A loaded document with text content and metadata"""
    text: str
    metadata: DocumentMetadata

    def __len__(self):
        return len(self.text)

    def summary(self) -> str:
        """Return a summary string"""
        return (
            f"{self.metadata.file_name} "
            f"({self.metadata.format}, "
            f"{self.metadata.char_count:,} chars)"
        )

class DocumentLoader:
    """
    Universal document loader for all MCP tools.

    Supports:
    - Single files
    - Directories (recursive)
    - Multiple formats (.txt, .pdf, .docx)
    - Caching
    - Async loading
    - Size limits
    """

    def __init__(self, config=None, cache=None):
        """
        Initialize document loader.

        Args:
            config: MCPToolConfig instance (uses default if None)
            cache: DocumentCache instance (creates if None)
        """
        self.config = config or get_config()
        self.cache = cache or DocumentCache(
            cache_dir=self.config.cache_dir,
            enabled=self.config.enable_cache
        )

    async def load(
        self,
        path: Union[str, Path],
        recursive: bool = True,
        formats: Optional[List[str]] = None
    ) -> List[LoadedDocument]:
        """
        Load document(s) from file or directory.

        Args:
            path: File path or directory path
            recursive: Recursively load from subdirectories
            formats: Allowed file formats (uses config default if None)

        Returns:
            List of LoadedDocument objects

        Raises:
            DocumentLoadError: If path invalid or loading fails
        """
        path = Path(path)
        formats = formats or self.config.supported_document_formats

        # Validate path exists
        if not path.exists():
            raise DocumentLoadError(
                error_type="path_not_found",
                message=f"Path does not exist: {path}",
                suggestions=[
                    "Check the file/folder path is correct",
                    "Ensure you have read permissions"
                ]
            )

        # Single file
        if path.is_file():
            return [await self._load_single_file(path)]

        # Directory
        elif path.is_dir():
            return await self._load_directory(path, recursive, formats)

        else:
            raise DocumentLoadError(
                error_type="invalid_path_type",
                message=f"Path is neither file nor directory: {path}"
            )

    async def _load_directory(
        self,
        dir_path: Path,
        recursive: bool,
        formats: List[str]
    ) -> List[LoadedDocument]:
        """Load all documents from directory"""

        documents = []
        total_size = 0

        # Find matching files
        pattern = "**/*" if recursive else "*"
        for file_path in dir_path.glob(pattern):
            if not file_path.is_file():
                continue

            # Check format
            if file_path.suffix.lower() not in formats:
                continue

            # Check size limit
            file_size = file_path.stat().st_size
            total_size += file_size

            if total_size > self.config.max_folder_size_mb * 1024 * 1024:
                raise DocumentLoadError(
                    error_type="folder_too_large",
                    message=f"Folder exceeds size limit: {total_size / (1024*1024):.1f}MB",
                    suggestions=[
                        f"Maximum folder size: {self.config.max_folder_size_mb}MB",
                        "Remove large files or split into multiple folders"
                    ]
                )

            # Load document
            try:
                doc = await self._load_single_file(file_path)
                documents.append(doc)
            except DocumentLoadError as e:
                # Log warning but continue with other files
                print(f"Warning: Could not load {file_path.name}: {e.message}")

        if len(documents) == 0:
            raise DocumentLoadError(
                error_type="no_documents_found",
                message=f"No documents found in {dir_path}",
                suggestions=[
                    f"Supported formats: {', '.join(formats)}",
                    f"Recursive: {recursive}"
                ]
            )

        return documents

    async def _load_single_file(self, file_path: Path) -> LoadedDocument:
        """Load a single document file"""

        import time
        start_time = time.time()

        # Check cache first
        cached = self.cache.get(str(file_path))
        if cached is not None:
            return cached

        # Validate file size
        file_size = file_path.stat().st_size
        max_size = self.config.max_file_size_mb * 1024 * 1024

        if file_size > max_size:
            raise DocumentLoadError(
                error_type="file_too_large",
                message=f"File exceeds size limit: {file_size / (1024*1024):.1f}MB",
                suggestions=[
                    f"Maximum file size: {self.config.max_file_size_mb}MB",
                    "Split file into smaller parts"
                ],
                context={"file_path": str(file_path)}
            )

        # Load based on format
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".txt":
                text = self._load_txt(file_path)
            elif suffix == ".pdf":
                text = self._load_pdf(file_path)
            elif suffix in [".doc", ".docx"]:
                text = self._load_docx(file_path)
            else:
                raise DocumentLoadError(
                    error_type="unsupported_format",
                    message=f"Unsupported file format: {suffix}",
                    suggestions=[
                        f"Supported formats: {', '.join(self.config.supported_document_formats)}"
                    ]
                )

        except Exception as e:
            raise DocumentLoadError(
                error_type="load_failed",
                message=f"Failed to load {file_path.name}: {str(e)}",
                suggestions=[
                    "Ensure file is not corrupted",
                    "Check file permissions"
                ],
                context={"file_path": str(file_path), "error": str(e)}
            )

        # Create metadata
        load_time = (time.time() - start_time) * 1000
        metadata = DocumentMetadata(
            file_path=str(file_path),
            file_name=file_path.name,
            file_size=file_size,
            format=suffix,
            word_count=len(text.split()),
            char_count=len(text),
            load_time_ms=load_time
        )

        # Create document
        document = LoadedDocument(text=text, metadata=metadata)

        # Cache it
        self.cache.set(str(file_path), document)

        return document

    def _load_txt(self, file_path: Path) -> str:
        """Load plain text file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _load_pdf(self, file_path: Path) -> str:
        """Load PDF file"""
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n\n".join(text_parts)

    def _load_docx(self, file_path: Path) -> str:
        """Load Word document"""
        doc = docx.Document(file_path)
        text_parts = []
        for paragraph in doc.paragraphs:
            text_parts.append(paragraph.text)

        # Also extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                text_parts.append(row_text)

        return "\n".join(text_parts)

    def combine_documents(
        self,
        documents: List[LoadedDocument],
        strategy: Literal["concatenate", "sections", "metadata"] = "sections"
    ) -> str:
        """
        Combine multiple documents into a single text.

        Args:
            documents: List of LoadedDocument objects
            strategy: How to combine
                - "concatenate": Simple join with separator
                - "sections": Add section headers per document
                - "metadata": Include file metadata in headers

        Returns:
            Combined text string
        """
        if strategy == "concatenate":
            return "\n\n".join(doc.text for doc in documents)

        elif strategy == "sections":
            parts = []
            for i, doc in enumerate(documents, 1):
                parts.append(f"--- Document {i}: {doc.metadata.file_name} ---")
                parts.append(doc.text)
                parts.append("")
            return "\n".join(parts)

        elif strategy == "metadata":
            parts = []
            for i, doc in enumerate(documents, 1):
                parts.append(f"--- Document {i} ---")
                parts.append(f"File: {doc.metadata.file_name}")
                parts.append(f"Format: {doc.metadata.format}")
                parts.append(f"Size: {doc.metadata.char_count:,} characters")
                parts.append(f"Words: {doc.metadata.word_count:,}")
                parts.append("---")
                parts.append(doc.text)
                parts.append("")
            return "\n".join(parts)

        else:
            raise ValueError(f"Unknown strategy: {strategy}")
```

**Benefits**:
- ✅ Single implementation for all tools
- ✅ Async-ready for performance
- ✅ Built-in caching
- ✅ Rich metadata
- ✅ Structured error handling
- ✅ Table extraction from Word docs

---

### 2.3 Extraction Strategies (`common/extraction/`)

**Purpose**: Pluggable extraction strategies with automatic fall-through

#### 2.3.1 Base Strategy (`common/extraction/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

class ConfidenceLevel(str, Enum):
    """Confidence level for extracted data"""
    HIGH = "high"      # 80-100%
    MEDIUM = "medium"  # 50-79%
    LOW = "low"        # 0-49%
    UNKNOWN = "unknown"

@dataclass
class ExtractionResult:
    """Result of data extraction"""
    placeholder: str
    value: str
    confidence: ConfidenceLevel
    source: Optional[str] = None  # Source location (doc name, section)
    metadata: Dict[str, Any] = None  # Additional metadata

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ExtractionResponse:
    """Response from extraction strategy"""
    results: Dict[str, ExtractionResult]  # {placeholder_name: ExtractionResult}
    strategy_name: str
    success: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def get_value(self, placeholder: str, default: str = "") -> str:
        """Get extracted value for placeholder"""
        result = self.results.get(placeholder)
        return result.value if result else default

    def get_confidence(self, placeholder: str) -> ConfidenceLevel:
        """Get confidence level for placeholder"""
        result = self.results.get(placeholder)
        return result.confidence if result else ConfidenceLevel.UNKNOWN

class ExtractionStrategy(ABC):
    """
    Abstract base class for extraction strategies.

    Strategies extract data from documents to fill template placeholders.
    Each strategy implements a different approach (LLM, keyword matching, etc.)
    """

    def __init__(self, config=None):
        """
        Initialize strategy.

        Args:
            config: MCPToolConfig instance
        """
        from ..config import get_config
        self.config = config or get_config()

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name (e.g., 'llm_smart', 'keyword_matching')"""
        pass

    @property
    def priority(self) -> int:
        """
        Priority for fall-through chain (lower = higher priority).

        Default priorities:
        - Manual mapping: 0 (highest)
        - LLM structured: 10
        - LLM smart: 20
        - Keyword matching: 30 (lowest)
        """
        return 50

    @abstractmethod
    async def extract(
        self,
        documents: str,
        placeholders: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResponse:
        """
        Extract data for placeholders from documents.

        Args:
            documents: Combined document text
            placeholders: List of placeholder names to extract
            context: Optional context (e.g., template type, user hints)

        Returns:
            ExtractionResponse with results
        """
        pass

    def can_handle(self, placeholders: List[str]) -> bool:
        """
        Check if strategy can handle these placeholders.

        Default: Can handle any placeholders.
        Override for strategies with specific requirements.
        """
        return True
```

#### 2.3.2 LLM Smart Extraction (`common/extraction/llm_smart.py`)

```python
import time
import json
from typing import List, Dict, Any, Optional
from .base import (
    ExtractionStrategy,
    ExtractionResponse,
    ExtractionResult,
    ConfidenceLevel
)
from ..ollama_client import OllamaClient
from ..errors import ExtractionError

class LLMSmartExtraction(ExtractionStrategy):
    """
    Smart LLM-based extraction strategy.

    Uses natural language prompting to extract relevant content
    for each placeholder from documents.
    """

    def __init__(self, config=None, ollama_client=None):
        super().__init__(config)
        self.ollama = ollama_client or OllamaClient(config=self.config)

    @property
    def name(self) -> str:
        return "llm_smart"

    @property
    def priority(self) -> int:
        return 20  # High priority (but lower than structured)

    async def extract(
        self,
        documents: str,
        placeholders: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResponse:
        """Extract using smart LLM prompting"""

        start_time = time.time()
        context = context or {}

        try:
            # Build prompt
            prompt = self._build_prompt(documents, placeholders, context)

            # Call LLM
            response = await self.ollama.generate(
                prompt=prompt,
                model=context.get("model", self.config.default_model),
                timeout=context.get("timeout", self.config.default_timeout),
                temperature=self.config.llm_temperature,
                format="json"  # Request JSON output
            )

            # Parse response
            results = self._parse_response(response, placeholders)

            execution_time = (time.time() - start_time) * 1000

            return ExtractionResponse(
                results=results,
                strategy_name=self.name,
                success=True,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ExtractionResponse(
                results={},
                strategy_name=self.name,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )

    def _build_prompt(
        self,
        documents: str,
        placeholders: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Build LLM prompt for extraction"""

        # Truncate documents if too long
        max_doc_length = 10000  # ~2500 words
        if len(documents) > max_doc_length:
            documents = documents[:max_doc_length] + "\n\n[... truncated ...]"

        prompt = f"""You are a data extraction assistant. Extract relevant content from documents to fill template placeholders.

PLACEHOLDERS TO FILL:
{self._format_placeholders(placeholders)}

DOCUMENTS:
{documents}

INSTRUCTIONS:
For each placeholder, extract the most relevant content from the documents.
- Keep extractions concise (1-3 sentences or specific data point)
- If a placeholder name suggests a specific type (e.g., "date", "number"), extract accordingly
- Assign confidence: "high" (80-100%), "medium" (50-79%), "low" (0-49%)
- Include source document location if multiple documents

Return JSON with this structure:
{{
  "placeholder_name": {{
    "value": "extracted content",
    "confidence": "high|medium|low",
    "source": "Document 1, Section X" (optional)
  }},
  ...
}}

Only return the JSON, no other text."""

        return prompt

    def _format_placeholders(self, placeholders: List[str]) -> str:
        """Format placeholder list for prompt"""
        return "\n".join(f"- {{{{{p}}}}}" for p in placeholders)

    def _parse_response(
        self,
        response: str,
        placeholders: List[str]
    ) -> Dict[str, ExtractionResult]:
        """Parse LLM JSON response"""

        results = {}

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(response[start:end])
                except json.JSONDecodeError:
                    raise ExtractionError(
                        error_type="invalid_llm_response",
                        message="LLM did not return valid JSON"
                    )
            else:
                raise ExtractionError(
                    error_type="invalid_llm_response",
                    message="LLM did not return JSON"
                )

        # Parse each placeholder
        for placeholder in placeholders:
            if placeholder in data:
                item = data[placeholder]

                # Handle different response formats
                if isinstance(item, str):
                    # Simple string response
                    value = item
                    confidence = ConfidenceLevel.MEDIUM
                    source = None
                elif isinstance(item, dict):
                    # Structured response
                    value = item.get("value", "")
                    confidence_str = item.get("confidence", "medium").lower()
                    confidence = self._parse_confidence(confidence_str)
                    source = item.get("source")
                else:
                    continue

                results[placeholder] = ExtractionResult(
                    placeholder=placeholder,
                    value=value,
                    confidence=confidence,
                    source=source
                )

        return results

    def _parse_confidence(self, confidence_str: str) -> ConfidenceLevel:
        """Parse confidence string to enum"""
        mapping = {
            "high": ConfidenceLevel.HIGH,
            "medium": ConfidenceLevel.MEDIUM,
            "low": ConfidenceLevel.LOW
        }
        return mapping.get(confidence_str.lower(), ConfidenceLevel.MEDIUM)
```

#### 2.3.3 Keyword Matching Extraction (`common/extraction/keyword_matching.py`)

```python
import re
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
import time

from .base import (
    ExtractionStrategy,
    ExtractionResponse,
    ExtractionResult,
    ConfidenceLevel
)

class KeywordMatchingExtraction(ExtractionStrategy):
    """
    Keyword matching extraction strategy (fallback).

    Uses fuzzy string matching to find placeholder keywords
    in documents and extract surrounding content.
    """

    @property
    def name(self) -> str:
        return "keyword_matching"

    @property
    def priority(self) -> int:
        return 30  # Lowest priority (fallback)

    async def extract(
        self,
        documents: str,
        placeholders: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResponse:
        """Extract using keyword matching"""

        start_time = time.time()
        results = {}

        # Split documents into sentences
        sentences = self._split_sentences(documents)

        for placeholder in placeholders:
            # Generate keywords from placeholder name
            keywords = self._generate_keywords(placeholder)

            # Find best matching sentence
            best_match = self._find_best_match(keywords, sentences)

            if best_match:
                results[placeholder] = best_match

        execution_time = (time.time() - start_time) * 1000

        return ExtractionResponse(
            results=results,
            strategy_name=self.name,
            success=True,
            execution_time_ms=execution_time
        )

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (could use nltk for better results)
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _generate_keywords(self, placeholder: str) -> List[str]:
        """
        Generate keywords from placeholder name.

        Example:
        - "company_name" → ["company", "name", "organization"]
        - "q4_revenue" → ["q4", "revenue", "fourth quarter"]
        """
        # Split camelCase and snake_case
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', placeholder)
        words = [w.lower() for w in words]

        # Add common synonyms
        synonyms = {
            "name": ["title", "designation"],
            "date": ["time", "when"],
            "revenue": ["income", "earnings", "sales"],
            "cost": ["expense", "price"],
            "company": ["organization", "business", "firm"],
            "q1": ["first quarter", "Q1"],
            "q2": ["second quarter", "Q2"],
            "q3": ["third quarter", "Q3"],
            "q4": ["fourth quarter", "Q4"]
        }

        all_keywords = words.copy()
        for word in words:
            if word in synonyms:
                all_keywords.extend(synonyms[word])

        return all_keywords

    def _find_best_match(
        self,
        keywords: List[str],
        sentences: List[str]
    ) -> Optional[ExtractionResult]:
        """Find best matching sentence for keywords"""

        best_score = 0.0
        best_sentence = None
        best_keyword = None

        for sentence in sentences:
            sentence_lower = sentence.lower()

            for keyword in keywords:
                # Fuzzy match
                if keyword in sentence_lower:
                    # Exact match
                    score = 1.0
                else:
                    # Use difflib for fuzzy matching
                    words_in_sentence = sentence_lower.split()
                    scores = [
                        SequenceMatcher(None, keyword, word).ratio()
                        for word in words_in_sentence
                    ]
                    score = max(scores) if scores else 0.0

                if score > best_score:
                    best_score = score
                    best_sentence = sentence
                    best_keyword = keyword

        if best_sentence and best_score > 0.6:  # Threshold
            # Determine confidence based on score
            if best_score >= 0.9:
                confidence = ConfidenceLevel.HIGH
            elif best_score >= 0.7:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW

            return ExtractionResult(
                placeholder="",  # Will be set by caller
                value=best_sentence,
                confidence=confidence,
                source=f"Keyword match: '{best_keyword}' (score: {best_score:.2f})"
            )

        return None
```

#### 2.3.4 Strategy Chain (`common/extraction/chain.py`)

```python
import asyncio
from typing import List, Dict, Any, Optional
import time

from .base import (
    ExtractionStrategy,
    ExtractionResponse,
    ExtractionResult,
    ConfidenceLevel
)
from ..errors import ExtractionError

class StrategyChain:
    """
    Chain multiple extraction strategies with automatic fall-through.

    Tries strategies in priority order. If a strategy fails or returns
    low confidence results, falls through to next strategy.

    Example:
        chain = StrategyChain([
            ManualMappingExtraction(),      # Try manual mapping first
            LLMStructuredExtraction(),       # Then LLM structured
            LLMSmartExtraction(),            # Then LLM smart
            KeywordMatchingExtraction()      # Finally keyword matching
        ])

        result = await chain.extract(documents, placeholders)
    """

    def __init__(
        self,
        strategies: List[ExtractionStrategy],
        min_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        fallback_threshold: float = 0.5  # 50% of placeholders must succeed
    ):
        """
        Initialize strategy chain.

        Args:
            strategies: List of strategies (will be sorted by priority)
            min_confidence: Minimum confidence to accept results
            fallback_threshold: Fraction of placeholders that must be
                               filled to skip fallback strategies
        """
        self.strategies = sorted(strategies, key=lambda s: s.priority)
        self.min_confidence = min_confidence
        self.fallback_threshold = fallback_threshold

    async def extract(
        self,
        documents: str,
        placeholders: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResponse:
        """
        Extract using strategy chain with fall-through.

        Returns:
            Combined ExtractionResponse with best results from all strategies
        """
        start_time = time.time()
        context = context or {}

        # Track results per placeholder
        best_results: Dict[str, ExtractionResult] = {}
        strategies_used = []
        errors = []

        # Try each strategy
        for strategy in self.strategies:
            # Check if strategy can handle these placeholders
            if not strategy.can_handle(placeholders):
                continue

            # Find unfilled placeholders
            unfilled = [
                p for p in placeholders
                if p not in best_results or
                   self._is_low_confidence(best_results[p])
            ]

            if not unfilled:
                # All placeholders filled with good confidence
                break

            # Run strategy
            try:
                response = await strategy.extract(documents, unfilled, context)
                strategies_used.append(strategy.name)

                if response.success:
                    # Update best results
                    for placeholder, result in response.results.items():
                        # Only update if better than existing
                        if (placeholder not in best_results or
                            self._is_better(result, best_results[placeholder])):
                            best_results[placeholder] = result
                else:
                    errors.append(f"{strategy.name}: {response.error}")

            except Exception as e:
                errors.append(f"{strategy.name}: {str(e)}")

            # Check if we have enough results to stop
            coverage = len(best_results) / len(placeholders)
            if coverage >= self.fallback_threshold:
                # Check if most results meet minimum confidence
                good_results = sum(
                    1 for r in best_results.values()
                    if not self._is_low_confidence(r)
                )
                if good_results / len(best_results) >= 0.8:  # 80% good
                    break

        execution_time = (time.time() - start_time) * 1000

        # Return combined response
        return ExtractionResponse(
            results=best_results,
            strategy_name=f"chain({', '.join(strategies_used)})",
            success=len(best_results) > 0,
            error="; ".join(errors) if errors else None,
            execution_time_ms=execution_time
        )

    def _is_low_confidence(self, result: ExtractionResult) -> bool:
        """Check if result has low confidence"""
        confidence_order = [
            ConfidenceLevel.UNKNOWN,
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH
        ]

        result_level = confidence_order.index(result.confidence)
        min_level = confidence_order.index(self.min_confidence)

        return result_level < min_level

    def _is_better(
        self,
        new_result: ExtractionResult,
        old_result: ExtractionResult
    ) -> bool:
        """Check if new result is better than old result"""
        confidence_order = [
            ConfidenceLevel.UNKNOWN,
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH
        ]

        new_level = confidence_order.index(new_result.confidence)
        old_level = confidence_order.index(old_result.confidence)

        return new_level > old_level
```

**Benefits of Strategy Pattern + Chain**:
- ✅ Automatic fall-through resilience
- ✅ Easy to add new strategies
- ✅ Strategies can be tested independently
- ✅ Confidence-based selection
- ✅ Per-placeholder optimization (different strategies for different placeholders)

---

### 2.4 Template Server Base Class (`common/template_server.py`)

**Purpose**: Abstract base class for all template filling servers

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from .config import get_config
from .document_loader import DocumentLoader, LoadedDocument
from .extraction.chain import StrategyChain
from .extraction.base import ExtractionResponse
from .errors import TemplateError

class TemplateFillingServer(ABC):
    """
    Abstract base class for template filling servers.

    Provides common infrastructure for PowerPoint, Word, Excel, etc.
    Subclasses implement format-specific methods.
    """

    def __init__(
        self,
        tool_id: str,
        config=None,
        document_loader=None,
        extraction_chain=None
    ):
        """
        Initialize template server.

        Args:
            tool_id: MCP tool identifier
            config: MCPToolConfig instance
            document_loader: DocumentLoader instance
            extraction_chain: StrategyChain instance
        """
        self.config = config or get_config()
        self.document_loader = document_loader or DocumentLoader(config=self.config)
        self.extraction_chain = extraction_chain  # Set by subclass
        self.mcp = FastMCP(tool_id)

        # Register MCP tools
        self._register_tools()

    @property
    @abstractmethod
    def template_format(self) -> str:
        """Template file format (e.g., '.pptx', '.docx')"""
        pass

    @abstractmethod
    async def _load_template(self, template_path: str) -> Any:
        """
        Load template file.

        Returns:
            Format-specific template object (e.g., Presentation, Document)
        """
        pass

    @abstractmethod
    async def _extract_placeholders(
        self,
        template: Any,
        style: str = "mustache"
    ) -> Dict[str, Any]:
        """
        Extract placeholders from template.

        Args:
            template: Template object
            style: Placeholder style ("mustache", "bracket", "custom")

        Returns:
            Dict mapping placeholder names to placeholder objects
        """
        pass

    @abstractmethod
    async def _fill_placeholders(
        self,
        template: Any,
        placeholders: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Any:
        """
        Fill placeholders with extracted data.

        Args:
            template: Template object
            placeholders: Placeholder objects from _extract_placeholders
            data: Extracted data mapping

        Returns:
            Filled template object
        """
        pass

    @abstractmethod
    async def _save_template(
        self,
        template: Any,
        output_path: str
    ) -> str:
        """
        Save filled template.

        Args:
            template: Filled template object
            output_path: Output file path

        Returns:
            Absolute path to saved file
        """
        pass

    def _register_tools(self):
        """Register MCP tools (implemented by subclass)"""
        pass

    async def run(self):
        """Run the MCP server"""
        await self.mcp.run()
```

---

## 3. POWERPOINT SERVER IMPLEMENTATION

### 3.1 PowerPoint Template Server (`powerpoint_template_server.py`)

```python
#!/usr/bin/env python3
"""
PowerPoint Template Filling MCP Server

Fills PowerPoint templates with data extracted from document folders.
Zero-cost, locally-running MCP server using python-pptx and Ollama.
"""

import asyncio
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE_TYPE

# Common infrastructure
from common.config import get_config
from common.template_server import TemplateFillingServer
from common.document_loader import DocumentLoader
from common.extraction.chain import StrategyChain
from common.extraction.llm_smart import LLMSmartExtraction
from common.extraction.keyword_matching import KeywordMatchingExtraction
from common.extraction.manual_mapping import ManualMappingExtraction
from common.errors import TemplateError, ExtractionError

class PowerPointTemplateServer(TemplateFillingServer):
    """
    MCP server for filling PowerPoint templates.

    Features:
    - {{mustache}} placeholder support
    - Text, table, and chart filling
    - Multi-format document extraction
    - LLM-powered smart extraction with fallback
    - Template formatting preservation
    """

    def __init__(self, config=None):
        # Create extraction chain with fall-through
        extraction_chain = StrategyChain([
            ManualMappingExtraction(config=config),      # Priority 0
            LLMSmartExtraction(config=config),            # Priority 20
            KeywordMatchingExtraction(config=config)      # Priority 30
        ])

        super().__init__(
            tool_id="powerpoint-template-fill",
            config=config,
            extraction_chain=extraction_chain
        )

    @property
    def template_format(self) -> str:
        return ".pptx"

    async def _load_template(self, template_path: str) -> Presentation:
        """Load PowerPoint template"""
        try:
            return Presentation(template_path)
        except Exception as e:
            raise TemplateError(
                error_type="invalid_template",
                message=f"Failed to load PowerPoint template: {str(e)}",
                suggestions=[
                    "Ensure file is valid .pptx format",
                    "Try opening in PowerPoint to check for corruption"
                ]
            )

    async def _extract_placeholders(
        self,
        template: Presentation,
        style: str = "mustache"
    ) -> Dict[str, List[Any]]:
        """
        Extract placeholders from PowerPoint template.

        Returns:
            Dict mapping placeholder names to list of shape objects
        """
        placeholders = {}

        # Regex for different styles
        patterns = {
            "mustache": r'\{\{(\w+)\}\}',
            "bracket": r'\[(\w+)\]',
            "custom": r'<(\w+)>'
        }
        pattern = re.compile(patterns.get(style, patterns["mustache"]))

        # Scan all slides
        for slide_num, slide in enumerate(template.slides, 1):
            # Scan all shapes
            for shape in slide.shapes:
                # Check if shape has text
                if not shape.has_text_frame:
                    continue

                # Scan text in shape
                text = shape.text_frame.text
                matches = pattern.findall(text)

                for placeholder_name in matches:
                    if placeholder_name not in placeholders:
                        placeholders[placeholder_name] = []

                    placeholders[placeholder_name].append({
                        "slide_num": slide_num,
                        "shape": shape,
                        "original_text": text,
                        "type": "text"
                    })

                # Check for table placeholders
                if shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                    table_placeholders = self._extract_table_placeholders(
                        shape.table,
                        pattern,
                        slide_num
                    )
                    for name, items in table_placeholders.items():
                        if name not in placeholders:
                            placeholders[name] = []
                        placeholders[name].extend(items)

        return placeholders

    def _extract_table_placeholders(
        self,
        table: Any,
        pattern: re.Pattern,
        slide_num: int
    ) -> Dict[str, List[Any]]:
        """Extract placeholders from table"""
        placeholders = {}

        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                text = cell.text
                matches = pattern.findall(text)

                for placeholder_name in matches:
                    if placeholder_name not in placeholders:
                        placeholders[placeholder_name] = []

                    placeholders[placeholder_name].append({
                        "slide_num": slide_num,
                        "table": table,
                        "row": row_idx,
                        "col": col_idx,
                        "cell": cell,
                        "original_text": text,
                        "type": "table_cell"
                    })

        return placeholders

    async def _fill_placeholders(
        self,
        template: Presentation,
        placeholders: Dict[str, List[Any]],
        data: Dict[str, Any]
    ) -> Presentation:
        """Fill placeholders with extracted data"""

        for placeholder_name, locations in placeholders.items():
            # Get extracted value
            value = data.get(placeholder_name, f"{{{{{placeholder_name}}}}}")

            # Fill all locations
            for location in locations:
                if location["type"] == "text":
                    self._fill_text_placeholder(location, value)
                elif location["type"] == "table_cell":
                    self._fill_table_cell(location, value)

        return template

    def _fill_text_placeholder(self, location: Dict[str, Any], value: str):
        """Fill text placeholder in shape"""
        shape = location["shape"]
        original_text = location["original_text"]

        # Replace placeholder in text
        new_text = re.sub(
            r'\{\{' + re.escape(location.get("placeholder_name", "")) + r'\}\}',
            value,
            original_text
        )

        # Preserve formatting: clear and rewrite
        text_frame = shape.text_frame
        text_frame.clear()

        # Add paragraph with value
        p = text_frame.paragraphs[0] if text_frame.paragraphs else text_frame.add_paragraph()
        p.text = new_text

    def _fill_table_cell(self, location: Dict[str, Any], value: str):
        """Fill table cell placeholder"""
        cell = location["cell"]
        original_text = location["original_text"]

        # Replace placeholder
        new_text = re.sub(
            r'\{\{' + re.escape(location.get("placeholder_name", "")) + r'\}\}',
            value,
            original_text
        )

        cell.text = new_text

    async def _save_template(
        self,
        template: Presentation,
        output_path: str
    ) -> str:
        """Save filled PowerPoint"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        template.save(str(output_path))
        return str(output_path.absolute())

    def _register_tools(self):
        """Register MCP tools"""

        @self.mcp.tool()
        async def fill_powerpoint_template(
            template_path: str,
            documents_folder: str,
            output_path: Optional[str] = "filled_presentation.pptx",
            placeholder_style: str = "mustache",
            extraction_strategy: str = "llm_smart",
            model: Optional[str] = None,
            timeout_seconds: Optional[int] = None,
            preserve_formatting: bool = True
        ) -> str:
            """
            Fill PowerPoint template with data from documents.

            Args:
                template_path: Path to .pptx template
                documents_folder: Folder with source documents
                output_path: Output file path
                placeholder_style: "mustache", "bracket", or "custom"
                extraction_strategy: "llm_smart", "keyword_matching", "manual_map"
                model: LLM model to use
                timeout_seconds: Timeout in seconds
                preserve_formatting: Preserve template formatting

            Returns:
                JSON with status and output path
            """
            # Implementation in next section
            pass

async def main():
    """Main entry point"""
    import os
    server = PowerPointTemplateServer()
    await server.run()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 4. IMPLEMENTATION TIMELINE

### Phase 0: Shared Infrastructure (3-4 hours)
**Priority**: CRITICAL - Must be done first

1. **Hour 1**: `common/config.py` + `common/errors.py`
2. **Hour 2**: `common/document_loader.py` + tests
3. **Hour 3**: `common/extraction/base.py` + `llm_smart.py`
4. **Hour 4**: `common/extraction/keyword_matching.py` + `chain.py`

**Deliverable**: Shared modules with unit tests

### Phase 1: PowerPoint Tool MVP (2-3 hours)
**Priority**: HIGH

1. **Hour 1**: `powerpoint_template_server.py` basic structure
2. **Hour 2**: Text placeholder extraction and filling
3. **Hour 3**: End-to-end test + frontend integration

**Deliverable**: Working PowerPoint tool with text-only

### Phase 2: Table & Chart Support (2-3 hours)
**Priority**: MEDIUM

1. **Hour 1**: Table placeholder extraction
2. **Hour 2**: Table filling implementation
3. **Hour 3**: Chart placeholder support (basic)

**Deliverable**: Full PowerPoint support

### Phase 3: Polish & Testing (2 hours)
**Priority**: MEDIUM

1. **Hour 1**: Comprehensive error handling
2. **Hour 2**: Integration tests + documentation

**Deliverable**: Production-ready tool

**Total**: 9-12 hours (1.5-2 days)

---

## 5. SUCCESS CRITERIA

### Functional Requirements
- ✅ Fills PowerPoint templates with {{mustache}} placeholders
- ✅ Extracts data from .txt, .docx, .pdf folders
- ✅ LLM smart extraction with keyword matching fallback
- ✅ Supports text and table placeholders
- ✅ Preserves template formatting
- ✅ Zero-cost local operation

### Performance Requirements
- ✅ Process 10-slide template with 20 placeholders in < 60 seconds
- ✅ Handle folders with 10-50 documents
- ✅ 90%+ extraction accuracy for clear placeholders

### Code Quality Requirements
- ✅ 0% code duplication (shared infrastructure)
- ✅ 80%+ test coverage for common modules
- ✅ Type hints throughout
- ✅ Comprehensive error messages

### Extensibility Requirements
- ✅ Easy to add Word template tool (reuse 80% of code)
- ✅ Easy to add new extraction strategies
- ✅ Easy to add new placeholder styles

---

## CONCLUSION

This architecture provides:

1. **Shared Infrastructure**: Eliminates duplication across MCP tools
2. **Resilient Extraction**: Multi-strategy chain with automatic fall-through
3. **Table/Chart Support**: Full PowerPoint feature coverage
4. **Type Safety**: Pydantic models and type hints throughout
5. **Testability**: Mock-friendly design, dependency injection
6. **Extensibility**: Easy to add Word, Excel, Google Slides tools
7. **Zero-Cost**: Fully local operation

**Next Steps**: Review architecture, then implement Phase 0 (shared infrastructure).
