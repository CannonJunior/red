# RFP Shredding Skill - Comprehensive Implementation Plan

**Date**: 2025-12-23
**Status**: Planning Phase - No Code Written
**Project Integration**: RAG System / Agent-Native Architecture

---

## Executive Summary

This plan outlines the creation of a production-grade "shredding" skill for processing government RFPs (Requests for Proposals), with primary focus on SAM.gov solicitations. The skill will automate requirement extraction, compliance matrix generation, and task assignment while integrating seamlessly with the existing project infrastructure.

**Key Capabilities**:
- Extract requirements from Section C (Technical), Section L (Instructions), Section M (Evaluation)
- Identify mandatory vs optional requirements using compliance keywords ("shall", "must", "will")
- Generate compliance matrices in Excel/CSV format
- Assign tasks to team members (including AI agents)
- Track compliance status and proposal gaps
- Integrate with existing Opportunities, TODO, and Agent systems

---

## Table of Contents

1. [Research Findings](#research-findings)
2. [Project Integration Analysis](#project-integration-analysis)
3. [Technical Architecture](#technical-architecture)
4. [Data Models](#data-models)
5. [Skill Structure](#skill-structure)
6. [Implementation Phases](#implementation-phases)
7. [API Integration](#api-integration)
8. [User Interface Integration](#user-interface-integration)
9. [Testing Strategy](#testing-strategy)
10. [Success Metrics](#success-metrics)

---

## Research Findings

### Government RFP Structure (FAR Uniform Contract Format)

Based on [Federal Acquisition Regulation §15.204-1](https://www.acquisition.gov/far/15.204-1):

**Section C - Description/Specifications/Statement of Work**
- Contains technical requirements, performance specifications
- Statement of Work (SOW) or Statement of Objectives (SOO)
- Most critical for requirement extraction
- Contains "shall", "must", "will" compliance keywords

**Section L - Instructions, Conditions, and Notices to Offerors**
- Proposal format, structure, page limitations
- Submission deadline and method
- Volume organization requirements
- **Non-compliance = automatic rejection**

**Section M - Evaluation Factors for Award**
- Evaluation criteria and scoring weights
- How proposals will be assessed
- Must align with Section L instructions
- Critical for win strategy

### RFP Shredding Process

[Source: Lohfeld Consulting](https://lohfeldconsulting.com/blog/2022/02/tips-for-shredding-rfps-quickly-and-accurately/), [APMP Western](https://apmp-western.org/wp-content/uploads/2023/10/WRC2023-Conniff-Shred-For-Success.pdf)

**Definition**: Stripping an RFP sentence-by-sentence to extract specific requirements into a structured compliance matrix.

**Process**:
1. **Initial Parse**: Extract all text from RFP document
2. **Section Identification**: Classify content by section (C, L, M)
3. **Requirement Extraction**: Identify sentences with compliance keywords
4. **Classification**: Mandatory vs optional, technical vs administrative
5. **Task Creation**: Convert requirements into actionable tasks
6. **Assignment**: Allocate to team members or agents
7. **Matrix Generation**: Create tracking spreadsheet

**Compliance Keywords** (priority order):
- **Mandatory**: "shall", "must", "will", "required"
- **Recommended**: "should", "may want to"
- **Optional**: "may", "can", "could"
- **Context**: "if...then", "when", "in the event"

### Industry Standard Compliance Matrix

[Source: Responsive.io](https://www.responsive.io/blog/proposal-compliance-matrix), [VisibleThread](https://www.visiblethread.com/blog/what-is-a-compliance-matrix-and-how-can-you-build-one/)

**Standard Columns**:
1. **Req ID**: Unique identifier (e.g., "C-001", "L-015", "M-003")
2. **Section**: RFP section reference (C, L, M, etc.)
3. **Page/Para**: Source location (page number, paragraph)
4. **Requirement Text**: Extracted requirement (full sentence)
5. **Compliance Type**: Mandatory/Recommended/Optional
6. **Compliance Status**: Fully/Partially/Not Compliant (F/P/N)
7. **Proposal Reference**: Where requirement is addressed in proposal
8. **Assignee**: Person or agent responsible
9. **Due Date**: Task deadline
10. **Status**: Not Started/In Progress/Complete
11. **Priority**: High/Medium/Low
12. **Risk Level**: Red/Yellow/Green
13. **Notes**: Additional context or concerns

### AI/NLP Techniques for Automation

[Source: DeepRFP](https://deeprfp.com/ai-rfp-software/rfp-shredding-software/), [Narwin.ai](https://narwin.ai/natural-language-processing-how-ai-reads-and-understands-rfps/)

**Modern Approaches**:
- **Document Parsing**: Extract text from PDF/Word (Docling: 97.9% accuracy)
- **NER (Named Entity Recognition)**: Identify dates, agencies, contacts
- **Requirement Classification**: Context-aware keyword detection
- **Dependency Analysis**: Identify requirement relationships
- **Large Language Models**: Understand intent beyond keywords

**Legacy vs AI-Powered**:
- ❌ Legacy: Simple keyword matching, misses context
- ✅ AI-Powered: Understands "if X, then shall Y" conditional requirements
- ✅ AI-Powered: Identifies implicit requirements from context
- ✅ AI-Powered: Detects contradictions between sections

---

## Project Integration Analysis

### Existing Infrastructure Capabilities

**Document Processing** (`rag-system/document_processor.py`):
- ✅ Docling integration for PDF extraction (97.9% accuracy)
- ✅ Supports PDF, Word, Excel, TXT files
- ✅ Intelligent chunking with overlap
- ✅ Markdown export from PDF
- **Gap**: No section detection or requirement classification

**Opportunities System** (`opportunities_api.py`):
- ✅ SQLite storage for opportunities
- ✅ Task management with assignments
- ✅ Status tracking (open, in_progress, won, lost)
- ✅ Gantt chart visualization
- ✅ Task history tracking
- **Gap**: No compliance matrix structure, no requirement-level detail

**TODO System** (`todos.db`, `todos.js`):
- ✅ Task lists and buckets (today, upcoming, someday)
- ✅ User assignment
- ✅ Quick-add functionality
- **Gap**: Not linked to opportunities or requirements

**Agent System** (`agent_system/`):
- ✅ Ollama-based local agents
- ✅ MCP server integration
- ✅ Skills system (can assign tasks to agents!)
- ✅ Redis event streaming
- **Opportunity**: Agents can be assigned as "team members" for requirements

**RAG System**:
- ✅ Local embeddings (Sentence Transformers)
- ✅ Vector search
- ✅ Document chunking and retrieval
- **Opportunity**: Find similar requirements across historical RFPs

**Search System** (`search_system.py`):
- ✅ Universal search across object types
- ✅ Tag system, folders, metadata
- **Opportunity**: Add "requirement" as new searchable object type

### Integration Points

**Primary Integration**:
```
RFP Document (PDF)
    ↓
Docling Extraction
    ↓
Shredding Skill (NLP + Rules)
    ↓
├─→ Compliance Matrix (Excel/CSV export)
├─→ Opportunity (name, description, metadata)
├─→ Tasks (one per requirement)
│   └─→ Assigned to: Users or AI Agents
├─→ Requirements DB (new table in opportunities.db)
└─→ Search Index (for finding requirements)
```

**Data Flow**:
1. **Upload RFP PDF** → Store in `uploads/rfps/`
2. **Extract Text** → Docling → Markdown with sections
3. **Parse Sections** → Identify C, L, M using headers
4. **Extract Requirements** → NLP: keyword detection + LLM validation
5. **Create Opportunity** → opportunities_api.create_opportunity()
6. **Generate Tasks** → One task per requirement
7. **Assign Tasks** → Users or AI agents (from agent_system)
8. **Export Matrix** → Excel file with all columns
9. **Index Requirements** → Add to search_system for discovery

---

## Technical Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  Shredding Skill                        │
│  (.claude/skills/shredding/)                            │
└─────────────────┬───────────────────────────────────────┘
                  │
      ┌───────────┴──────────────┐
      │                          │
┌─────▼─────┐            ┌───────▼──────┐
│  Scripts  │            │  References   │
└─────┬─────┘            └──────────────┘
      │
      ├─→ shred_rfp.py (Main shredding script)
      ├─→ generate_matrix.py (Excel output)
      ├─→ extract_sections.py (Section parser)
      ├─→ classify_requirements.py (NLP classification)
      └─→ assign_tasks.py (Task creation + assignment)

┌─────────────────────────────────────────────────────────┐
│          RFP Processing Pipeline                        │
└───────────┬─────────────────────────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
┌───▼────────┐  ┌────▼─────────┐
│  Document  │  │  Requirement │
│  Processor │  │  Extractor   │
│  (Docling) │  │  (Ollama)    │
└───┬────────┘  └────┬─────────┘
    │                │
    └────────┬───────┘
             │
    ┌────────▼──────────┐
    │  Shredding Engine │
    │  (Orchestrator)   │
    └────────┬──────────┘
             │
    ┌────────┴────────────────────────┐
    │                                 │
┌───▼────────┐              ┌─────────▼──────┐
│Requirements│              │  Compliance    │
│   Database │              │     Matrix     │
│ (SQLite)   │              │  (Excel/CSV)   │
└───┬────────┘              └────────────────┘
    │
    ├─→ Opportunities (parent container)
    ├─→ Tasks (per requirement)
    └─→ Search Index (for discovery)
```

### Technology Stack

**Document Processing**:
- Docling (PDF extraction) ✅ Already integrated
- Beautiful Soup (HTML parsing for SAM.gov)
- python-docx (Word documents)
- openpyxl (Excel export)

**NLP / AI**:
- Ollama (local LLM for classification) ✅ Already integrated
- spaCy (NER, sentence segmentation)
- Sentence Transformers (requirement similarity) ✅ Already integrated
- regex (compliance keyword detection)

**Data Storage**:
- SQLite (requirements, compliance matrix) ✅ Already integrated
- pandas (DataFrame manipulation)
- Excel/CSV export

**API Integration**:
- FastAPI endpoints ✅ Already using
- Redis (event streaming) ✅ Already integrated

### Processing Pipeline

**Stage 1: Document Ingestion**
```python
# Input: RFP PDF file
rfp_doc = document_processor.process_document("rfp.pdf")
# Output: Markdown text with sections preserved
```

**Stage 2: Section Detection**
```python
# Use regex + LLM to identify sections
sections = {
    'A': {...},  # Solicitation/Contract
    'B': {...},  # Supplies/Services
    'C': {...},  # Descriptions/Specifications ⭐
    'L': {...},  # Instructions to Offerors ⭐
    'M': {...},  # Evaluation Factors ⭐
}
```

**Stage 3: Requirement Extraction**
```python
# For each section, extract sentences with compliance keywords
requirements = []
for sentence in section_C:
    if has_compliance_keyword(sentence):
        req = {
            'text': sentence,
            'type': classify_compliance_type(sentence),  # Mandatory/Optional
            'section': 'C',
            'page': extract_page_number(sentence),
            'paragraph': extract_paragraph_id(sentence)
        }
        requirements.append(req)
```

**Stage 4: Classification** (Using Ollama LLM)
```python
# Prompt: "Classify this requirement: {requirement_text}"
# Categories:
# - Technical/Management/Cost
# - Deliverable/Process/Compliance
# - Priority: High/Medium/Low
```

**Stage 5: Task Generation**
```python
# Create opportunity
opp = opportunities_api.create_opportunity(
    name=f"RFP: {rfp_title}",
    description=rfp_summary,
    metadata={'rfp_number': '...', 'due_date': '...'}
)

# Create tasks (one per requirement)
for req in requirements:
    task = opportunities_api.create_task(
        opportunity_id=opp['id'],
        name=f"{req['section']}-{req['id']}: {req['text'][:50]}...",
        description=req['text'],
        assigned_to=determine_assignee(req),  # User or AI agent
        start_date=today,
        end_date=rfp_due_date,
        metadata={'requirement': req}
    )
```

**Stage 6: Compliance Matrix Export**
```python
# Generate Excel file
matrix = create_compliance_matrix(requirements, tasks)
matrix.to_excel(f"compliance_matrix_{rfp_number}.xlsx")
```

---

## Data Models

### New Database Tables

**requirements** (extends opportunities.db)
```sql
CREATE TABLE requirements (
    id TEXT PRIMARY KEY,                  -- UUID
    opportunity_id TEXT NOT NULL,         -- FK to opportunities
    task_id TEXT,                         -- FK to tasks (nullable)

    -- Source information
    section TEXT NOT NULL,                -- C, L, M, etc.
    page_number INTEGER,
    paragraph_id TEXT,
    source_text TEXT NOT NULL,            -- Full requirement text

    -- Classification
    compliance_type TEXT NOT NULL,        -- mandatory, recommended, optional
    requirement_category TEXT,            -- technical, management, cost, etc.
    priority TEXT DEFAULT 'medium',       -- high, medium, low
    risk_level TEXT DEFAULT 'green',      -- red, yellow, green

    -- Compliance tracking
    compliance_status TEXT DEFAULT 'not_started',  -- fully, partially, not, not_started
    proposal_reference TEXT,              -- Where addressed in proposal
    assignee_id TEXT,                     -- User or agent ID
    assigned_to_type TEXT,                -- 'user' or 'agent'

    -- Metadata
    keywords TEXT,                        -- JSON array of extracted keywords
    dependencies TEXT,                    -- JSON array of dependent req IDs
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    due_date TIMESTAMP,
    completed_at TIMESTAMP,

    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX idx_requirements_opportunity ON requirements(opportunity_id);
CREATE INDEX idx_requirements_section ON requirements(section);
CREATE INDEX idx_requirements_compliance ON requirements(compliance_status);
CREATE INDEX idx_requirements_assignee ON requirements(assignee_id);
```

**rfp_metadata** (stores RFP document metadata)
```sql
CREATE TABLE rfp_metadata (
    id TEXT PRIMARY KEY,                  -- UUID
    opportunity_id TEXT NOT NULL,         -- FK to opportunities

    -- RFP identification
    rfp_number TEXT,                      -- Solicitation number
    rfp_title TEXT NOT NULL,
    issuing_agency TEXT,
    naics_code TEXT,
    set_aside TEXT,                       -- Small business, 8(a), etc.

    -- Dates
    posted_date TIMESTAMP,
    response_due_date TIMESTAMP,
    questions_due_date TIMESTAMP,

    -- Document info
    file_path TEXT NOT NULL,              -- Path to original PDF
    file_size_bytes INTEGER,
    page_count INTEGER,
    sections_found TEXT,                  -- JSON array: ['A', 'B', 'C', ...]

    -- Processing metadata
    shredded_at TIMESTAMP,
    shredded_by TEXT,                     -- User or agent ID
    total_requirements INTEGER DEFAULT 0,
    mandatory_requirements INTEGER DEFAULT 0,

    -- Source
    source_url TEXT,                      -- SAM.gov URL
    source_system TEXT DEFAULT 'sam.gov',

    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
);
```

### Compliance Matrix Data Structure

**Excel/CSV Output Columns**:
```python
compliance_matrix_columns = [
    'Req ID',                # C-001, L-015, M-003
    'Section',               # C, L, M
    'Page',                  # 15
    'Paragraph',             # 3.2.1
    'Requirement Text',      # "The contractor shall provide..."
    'Compliance Type',       # Mandatory, Recommended, Optional
    'Category',              # Technical, Management, Cost
    'Priority',              # High, Medium, Low
    'Risk',                  # Red, Yellow, Green
    'Compliance Status',     # F (Fully), P (Partially), N (Not)
    'Proposal Section',      # 4.2.3
    'Proposal Page',         # 42
    'Assigned To',           # John Doe / Agent-Research-01
    'Due Date',              # 2025-01-15
    'Status',                # Not Started, In Progress, Complete
    'Notes',                 # Any concerns or clarifications
    'Dependencies',          # Other requirement IDs
    'Keywords',              # shall, security, testing
]
```

---

## Skill Structure

Following [SKILL_CREATION_GUIDE.md](./SKILL_CREATION_GUIDE.md) patterns:

```
.claude/skills/shredding/
├── SKILL.md                              # Main skill documentation
├── scripts/                              # Executable automation scripts
│   ├── shred_rfp.py                     # Main shredding orchestrator
│   ├── extract_sections.py              # Section parser (C, L, M)
│   ├── classify_requirements.py         # NLP requirement classifier
│   ├── generate_matrix.py               # Excel compliance matrix generator
│   ├── assign_tasks.py                  # Task assignment logic
│   ├── import_from_samgov.py            # SAM.gov scraper
│   └── validate_compliance.py           # Check matrix completeness
├── references/                          # Deep reference documentation
│   ├── far-sections-guide.md            # FAR uniform contract format
│   ├── compliance-keywords.md           # Keyword patterns and examples
│   ├── section-l-patterns.md            # Section L analysis patterns
│   ├── section-m-patterns.md            # Section M scoring strategies
│   ├── nlp-techniques.md                # NLP/AI extraction methods
│   └── compliance-matrix-standards.md   # Industry standards and templates
└── examples/                            # Sample RFPs and outputs
    ├── sample_rfp_section_c.txt
    ├── sample_rfp_section_l.txt
    ├── sample_compliance_matrix.xlsx
    └── shredding_output_example.json
```

### SKILL.md Structure

```markdown
---
name: shredding
description: "Government RFP analysis and requirement extraction toolkit for breaking down solicitations into actionable compliance matrices. When Claude needs to: (1) Extract requirements from government RFPs (SAM.gov, Section C/L/M), (2) Generate compliance matrices with task assignments, (3) Classify mandatory vs optional requirements using compliance keywords, (4) Create structured task lists from RFP sections, or (5) Analyze evaluation criteria and proposal instructions. Use for RFP shredding and compliance tracking, not for proposal writing."
---

# RFP Shredding & Compliance Management

## Overview

This skill automates the "shredding" process for government RFPs, particularly SAM.gov solicitations. It extracts requirements from Section C (Technical), Section L (Instructions), and Section M (Evaluation), generating compliance matrices and task assignments.

## Quick Start

### Basic RFP Shredding

```python
#!/usr/bin/env python3
from pathlib import Path
from shredding import RFPShredder

# Initialize shredder
shredder = RFPShredder()

# Process RFP document
result = shredder.shred_rfp(
    file_path="rfp_12345.pdf",
    rfp_number="FA8732-25-R-0001",
    opportunity_name="IT Support Services"
)

# Output:
# - Compliance matrix: compliance_matrix_FA8732-25-R-0001.xlsx
# - Opportunity created with tasks
# - Requirements indexed in search
```

### Extract Specific Section

```python
from shredding.section_parser import SectionParser

parser = SectionParser()
section_c = parser.extract_section("rfp.pdf", section="C")

print(f"Found {len(section_c['requirements'])} requirements in Section C")
```

## Automated Shredding Tools

### Using Shredding Scripts

Run the automated RFP shredding script:

```bash
python scripts/shred_rfp.py rfp_12345.pdf --rfp-number FA8732-25-R-0001
```

This generates:
- **Compliance Matrix**: Excel file with all requirements
- **Opportunity**: Parent container in opportunities system
- **Tasks**: One task per requirement, assigned to team members
- **Search Index**: Requirements searchable across system
```

[... continues with checklists, quick reference tables, examples ...]

---

## Implementation Phases

### Phase 1: Core Document Processing (Week 1)

**Goal**: Extract and parse RFP sections

**Deliverables**:
1. `extract_sections.py` - Identify Sections A-M in RFP PDFs
2. Section detection regex patterns
3. Unit tests for section extraction
4. Integration with existing Docling pipeline

**Technical Tasks**:
- Implement section header detection (regex: `^SECTION [A-M]`, `Part [IVX]+`)
- Handle multi-format headers (centered, bold, underlined)
- Preserve page numbers and paragraph IDs
- Export section-segmented markdown

**Testing**:
- Test with 5 real SAM.gov RFPs
- Verify >95% section detection accuracy
- Handle edge cases (missing sections, combined sections)

### Phase 2: Requirement Extraction (Week 2)

**Goal**: Identify and extract compliance requirements

**Deliverables**:
1. `classify_requirements.py` - NLP requirement extraction
2. Compliance keyword patterns
3. Ollama prompt templates for classification
4. `requirements` database table

**Technical Tasks**:
- Implement keyword detection ("shall", "must", "will")
- Detect conditional requirements ("if X, then shall Y")
- Extract source metadata (page, paragraph)
- Classify compliance type (mandatory/recommended/optional)
- Use Ollama for category classification (technical/management/cost)

**Ollama Prompts**:
```
System: You are an expert at analyzing government RFP requirements.

User: Classify this requirement:
"{requirement_text}"

Respond with JSON:
{
  "compliance_type": "mandatory|recommended|optional",
  "category": "technical|management|cost|deliverable|compliance",
  "priority": "high|medium|low",
  "key_terms": ["term1", "term2"],
  "implicit_requirements": ["..."]
}
```

**Testing**:
- Test with 100 real requirements from Section C/L/M
- Validate classification accuracy >90%
- Handle negations ("shall not", "must not")

### Phase 3: Compliance Matrix Generation (Week 3)

**Goal**: Generate Excel compliance matrices

**Deliverables**:
1. `generate_matrix.py` - Excel export with formatting
2. Compliance matrix template
3. Integration with opportunities system
4. RFP metadata storage

**Technical Tasks**:
- Create Excel file with standard columns
- Apply conditional formatting (red/yellow/green)
- Auto-size columns, freeze header row
- Add filters and sorting
- Link to opportunity and tasks

**Excel Features**:
- Color-coded compliance status
- Dropdown lists for status fields
- Formulas for % completion
- Pivot table for summary stats

### Phase 4: Task Assignment & Integration (Week 4)

**Goal**: Create tasks and assign to team/agents

**Deliverables**:
1. `assign_tasks.py` - Task creation logic
2. Agent assignment rules
3. Integration with opportunities_api
4. UI updates for requirements view

**Technical Tasks**:
- Create opportunity for RFP
- Generate one task per requirement
- Assign to users or AI agents based on category
- Set due dates (work backward from RFP due date)
- Create task dependencies

**Assignment Logic**:
```python
def assign_requirement(requirement):
    if requirement['category'] == 'technical':
        return assign_to_agent('technical-writer-agent')
    elif requirement['category'] == 'cost':
        return assign_to_user('cost-estimator')
    elif requirement['category'] == 'management':
        return assign_to_user('program-manager')
```

### Phase 5: Search & Discovery (Week 5)

**Goal**: Index requirements for search

**Deliverables**:
1. Requirements searchable via search_system
2. Similarity search for historical RFPs
3. Requirement deduplication
4. Cross-RFP analysis

**Technical Tasks**:
- Add "requirement" object type to search_system
- Index requirement text with embeddings
- Find similar requirements across opportunities
- Suggest reusable responses from past proposals

### Phase 6: Advanced Features (Week 6+)

**Optional enhancements**:
1. **SAM.gov Integration**: Scrape RFPs directly from SAM.gov
2. **Automatic Updates**: Monitor amendments, update requirements
3. **Win Theme Extraction**: Identify customer priorities from Section M
4. **Gap Analysis**: Compare requirements to capabilities
5. **Proposal Outline Generator**: Auto-generate proposal structure from Section L

---

## API Integration

### New API Endpoints

**POST /api/shredding/upload-rfp**
```python
{
    "file": <multipart file>,
    "rfp_number": "FA8732-25-R-0001",
    "opportunity_name": "IT Support Services",
    "due_date": "2025-03-15",
    "auto_assign": true  # Auto-assign tasks to agents
}

# Response:
{
    "status": "success",
    "opportunity_id": "uuid",
    "requirements_count": 47,
    "tasks_created": 47,
    "matrix_file": "compliance_matrix_FA8732-25-R-0001.xlsx"
}
```

**GET /api/shredding/requirements/{opportunity_id}**
```python
# List all requirements for an opportunity
{
    "requirements": [
        {
            "id": "uuid",
            "section": "C",
            "page": 15,
            "text": "The contractor shall provide...",
            "compliance_type": "mandatory",
            "status": "in_progress",
            "assigned_to": "agent-technical-writer"
        }
    ]
}
```

**POST /api/shredding/classify-requirement**
```python
{
    "text": "The contractor shall provide documentation"
}

# Response:
{
    "compliance_type": "mandatory",
    "category": "deliverable",
    "priority": "high",
    "keywords": ["shall", "documentation"]
}
```

**GET /api/shredding/matrix/{opportunity_id}**
```python
# Download compliance matrix as Excel
# Returns: application/vnd.ms-excel file
```

### Integration with Existing APIs

**opportunities_api.py** - Add methods:
```python
def create_rfp_opportunity(rfp_metadata, requirements):
    """Create opportunity with RFP-specific metadata."""

def link_requirement_to_task(requirement_id, task_id):
    """Associate requirement with task."""

def get_compliance_summary(opportunity_id):
    """Get compliance statistics (F/P/N counts)."""
```

**search_system.py** - Add requirement object type:
```python
class ObjectType(Enum):
    # ... existing types ...
    REQUIREMENT = "requirement"
```

---

## User Interface Integration

### New UI Components

**1. RFP Upload Modal**
```
┌─────────────────────────────────────────┐
│  Upload RFP for Shredding              │
├─────────────────────────────────────────┤
│                                         │
│  RFP Document: [Browse...] rfp.pdf     │
│                                         │
│  RFP Number: [FA8732-25-R-0001       ] │
│  Opportunity Name: [IT Support Svc  ] │
│  Due Date: [2025-03-15              ] │
│                                         │
│  ☑ Extract requirements               │
│  ☑ Generate compliance matrix         │
│  ☑ Create tasks                       │
│  ☑ Auto-assign to agents              │
│                                         │
│  [Cancel]  [Shred RFP →]               │
└─────────────────────────────────────────┘
```

**2. Compliance Matrix View** (in Opportunities page)
```
┌─────────────────────────────────────────────────────────────┐
│  RFP: IT Support Services (FA8732-25-R-0001)               │
├─────────────────────────────────────────────────────────────┤
│  Compliance: 30/47 Complete (64%)  [═══════════░░░░░]      │
│                                                             │
│  Section  Req ID    Text              Status    Assigned   │
│  ─────────────────────────────────────────────────────────  │
│  ● C      C-001     Contractor shall  ✓ Complete  Agent-1  │
│  ● C      C-002     System must sup..  ⏳ In Prog  John D  │
│  ⚠ L     L-015     Proposal format..  ○ Pending   Sarah M │
│  ● M      M-003     Past performance  ✓ Complete  Agent-2  │
│                                                             │
│  Filter: [All ▼] [Section ▼] [Status ▼]                   │
│                                                             │
│  [Export Matrix ↓]  [View Gantt]  [Assign All]            │
└─────────────────────────────────────────────────────────────┘
```

**3. Requirement Detail Panel**
```
┌─────────────────────────────────────────┐
│  Requirement C-012                      │
├─────────────────────────────────────────┤
│  Section: C (Technical)                 │
│  Page: 23, Para: 3.4.2                 │
│                                         │
│  "The contractor shall provide a       │
│  secure web portal with two-factor     │
│  authentication..."                     │
│                                         │
│  Compliance: Mandatory                  │
│  Category: Technical                    │
│  Priority: High ⚠                      │
│  Risk: Yellow                           │
│                                         │
│  Status: [In Progress ▼]               │
│  Assigned: [Agent-Security ▼]          │
│  Due: 2025-02-15                        │
│                                         │
│  Proposal Reference:                    │
│  Section 4.3, Pages 35-37              │
│                                         │
│  Notes:                                 │
│  [Need to clarify MFA requirements...] │
│                                         │
│  Dependencies:                          │
│  → C-010 (Authentication framework)     │
│  → C-015 (User management)              │
│                                         │
│  [Save]  [Delete]  [Create Task]       │
└─────────────────────────────────────────┘
```

### Integration with Existing Pages

**Opportunities Page**:
- Add "Upload RFP" button in header
- Show RFP-specific metadata (number, due date, agency)
- Display compliance percentage in opportunity card
- Add "Requirements" tab alongside "Tasks"

**Gantt Chart**:
- Visualize requirement deadlines
- Show critical path for RFP response
- Group by section (C, L, M)
- Color-code by compliance status

**Search**:
- Add "Requirements" filter to object types
- Search within requirement text
- Filter by section, compliance type, status

---

## Testing Strategy

### Unit Tests

**Document Processing**:
- Test section extraction with various PDF formats
- Verify page number preservation
- Handle multi-column layouts

**Requirement Extraction**:
- Test compliance keyword detection (100 examples)
- Verify conditional requirement parsing ("if...then")
- Test negation handling ("shall not")

**Classification**:
- Test Ollama classification prompts (50 requirements)
- Validate category accuracy
- Test priority assignment logic

**Matrix Generation**:
- Test Excel formatting and formulas
- Verify column structure
- Test export with 500+ requirements

### Integration Tests

**End-to-End RFP Shredding**:
1. Upload real RFP PDF
2. Extract sections C, L, M
3. Generate requirements
4. Create opportunity + tasks
5. Export compliance matrix
6. Verify data in database

**API Tests**:
- Test all endpoints with valid/invalid data
- Verify error handling
- Test concurrent uploads

### Acceptance Tests

**Real-World Scenarios**:
- Process 10 actual SAM.gov RFPs
- Compare output to manual shredding
- Measure time savings (target: 10x faster)
- Validate accuracy (target: >95%)

---

## Success Metrics

### Performance Metrics

**Speed**:
- Manual shredding: ~40 hours for 100-page RFP
- Automated shredding: <4 hours (10x improvement)
- Section extraction: <5 minutes
- Requirement classification: <30 minutes
- Matrix generation: <1 minute

**Accuracy**:
- Section detection: >95%
- Requirement extraction: >90% (vs manual review)
- Compliance type classification: >85%
- Category classification: >80%

### Adoption Metrics

**Usage**:
- RFPs processed per month: Target 20+
- Requirements extracted: Target 1,000+
- Compliance matrices generated: Target 20+
- Tasks auto-created: Target 1,000+

**Quality**:
- User satisfaction: >4.0/5.0
- False positive rate: <10% (incorrectly identified requirements)
- False negative rate: <5% (missed requirements)
- Matrix completeness: >95% (all fields populated)

### Business Metrics

**Proposal Success**:
- % of RFPs with compliance matrix: Target 100%
- Avg proposal win rate: Baseline → +10%
- RFP response time: Baseline → -30%
- Proposal team efficiency: +50% time savings

---

## Risk Analysis & Mitigation

### Technical Risks

**Risk: PDF parsing failures**
- Mitigation: Fallback to OCR, manual section marking
- Contingency: Support Word/HTML upload

**Risk: Ollama misclassification**
- Mitigation: Human review workflow, correction feedback loop
- Contingency: Rule-based fallback for critical requirements

**Risk: Section header variations**
- Mitigation: Extensive regex patterns, machine learning for header detection
- Contingency: Manual section selection UI

### Operational Risks

**Risk: User adoption resistance**
- Mitigation: Training, documentation, success stories
- Contingency: Hybrid manual/auto approach

**Risk: Data quality issues**
- Mitigation: Validation checks, automated testing
- Contingency: Manual review checkpoints

---

## Future Enhancements

### Phase 7+: Advanced Features

**1. SAM.gov Live Integration**
- Auto-download RFPs matching NAICS codes
- Monitor for amendments
- Track Q&A postings

**2. Proposal Co-Pilot**
- Suggest responses from historical proposals
- Auto-fill low-risk requirements
- Generate proposal outline from Section L

**3. Win Strategy Analysis**
- Extract customer priorities from Section M
- Identify discriminators vs table stakes
- Suggest win themes

**4. Collaborative Review**
- Multi-user requirement review
- Comments and annotations
- Approval workflows

**5. Analytics Dashboard**
- RFP pipeline visualization
- Compliance trends over time
- Team workload balancing
- Win/loss analysis by requirement type

---

## Sources & References

### Government RFP Resources
- [Federal Acquisition Regulation (FAR)](https://www.acquisition.gov/far/)
- [SAM.gov - Government Contracts](https://sam.gov/)
- [Uniform Contract Format (FAR §15.204-1)](https://www.acquisition.gov/far/15.204-1)

### RFP Shredding Best Practices
- [Lohfeld Consulting - Tips for Shredding RFPs](https://lohfeldconsulting.com/blog/2022/02/tips-for-shredding-rfps-quickly-and-accurately/)
- [APMP Western - Shred for Success](https://apmp-western.org/wp-content/uploads/2023/10/WRC2023-Conniff-Shred-For-Success.pdf)
- [GovContractAI - Decoding RFP Sections](https://govcontractai.com/blog/decoding-rfp-sections-evaluation-criteria)

### Compliance Matrix Standards
- [Responsive.io - Compliance Matrix Guide](https://www.responsive.io/blog/proposal-compliance-matrix)
- [VisibleThread - What is a Compliance Matrix](https://www.visiblethread.com/blog/what-is-a-compliance-matrix-and-how-can-you-build-one/)
- [Inventive.ai - Compliance Matrix Templates](https://www.inventive.ai/blog-posts/compliance-matrix-template-proposals)

### AI/NLP for RFP Analysis
- [DeepRFP - AI RFP Shredding Software](https://deeprfp.com/ai-rfp-software/rfp-shredding-software/)
- [Narwin.ai - NLP for RFPs](https://narwin.ai/natural-language-processing-how-ai-reads-and-understands-rfps/)
- [Unanet - Streamline Government Proposals with AI](https://unanet.com/proposal-ai/insights/streamline-government-proposals-with-ai-rfp-shredding-compliance-and-competitive-edge)

---

## Conclusion

This implementation plan provides a comprehensive roadmap for building a production-grade RFP shredding skill that:

✅ Leverages existing project infrastructure (Docling, Ollama, opportunities_api)
✅ Follows industry best practices for government proposals
✅ Implements progressive disclosure skill patterns
✅ Integrates seamlessly with current UI/UX
✅ Provides measurable ROI (10x time savings, >90% accuracy)
✅ Scales to handle multiple concurrent RFPs

**Next Step**: Review this plan, validate integration points, and proceed to Phase 1 implementation upon approval.

---

**Plan Status**: ✅ Complete - Ready for Review
**Code Status**: ⏸️ No code written (as requested)
**Estimated Total Development**: 6-8 weeks
**Estimated ROI**: 10x time savings on RFP analysis
