# Directory Structure & Organization

**Date**: 2025-12-26
**Purpose**: Document the project's directory organization and file placement conventions

---

## Overview

This project follows a structured approach to organizing code, skills, outputs, and documentation. This document explains the purpose of each directory and where different types of files should be placed.

---

## Top-Level Directory Structure

```
/home/junior/src/red/
├── .claude/                    # Claude Code configuration
│   └── skills/                 # Skill definitions (NOT implementations)
│       └── <skill-name>/
│           ├── SKILL.md        # Skill documentation
│           ├── scripts/        # CLI scripts that use core libraries
│           ├── examples/       # Usage examples
│           └── references/     # Reference documentation
│
├── <feature>/                  # Core implementation libraries
│   ├── __init__.py
│   ├── *.py                    # Implementation modules
│   └── README.md               # Library documentation
│
├── outputs/                    # Generated artifacts (NOT tracked in git)
│   └── <skill-name>/
│       └── <artifact-type>/
│
├── docs/                       # Documentation and implementation notes
│   └── <feature>/
│
├── tests/                      # Test suites
│   └── <feature>/
│
├── data/                       # Input data (datasets, documents)
│   └── <category>/
│
├── migrations/                 # Database migrations
├── rag_system/                 # RAG system components
├── agent-system/               # Agent framework
├── server/                     # Web server components
├── workflows/                  # Workflow definitions
├── monitoring/                 # Monitoring and observability
└── CLAUDE.md                   # Project instructions for Claude
```

---

## Directory Details

### `.claude/skills/` - Skill Definitions

**Purpose**: Skill definitions and CLI scripts

**Contains**:
- `SKILL.md` - Skill documentation and examples
- `scripts/` - CLI scripts that import from core libraries
- `examples/` - Usage examples
- `references/` - Reference documentation

**Does NOT Contain**:
- Implementation code (goes in core libraries)
- Generated outputs (goes in `outputs/`)
- Test files (goes in `tests/`)

**Example**: `.claude/skills/shredding/`
```
.claude/skills/shredding/
├── SKILL.md                    # Skill definition
├── scripts/
│   ├── shred_rfp.py           # CLI script (imports from shredding/)
│   └── check_status.py         # Status checker
├── examples/
│   └── basic_usage.py          # Example scripts
└── references/
    └── FAR_sections.md         # Reference docs
```

---

### `<feature>/` - Core Implementation Libraries

**Purpose**: Core implementation code for features/skills

**Contains**:
- Python modules (`.py` files)
- `__init__.py` for package initialization
- `README.md` for library documentation
- Unit tests in corresponding `tests/<feature>/`

**Does NOT Contain**:
- Skill definitions (goes in `.claude/skills/`)
- Generated outputs (goes in `outputs/`)
- Implementation notes (goes in `docs/`)

**Example**: `shredding/`
```
shredding/
├── __init__.py
├── requirement_classifier.py   # Classification logic
├── requirement_extractor.py    # Extraction logic
├── rfp_shredder.py            # Main orchestrator
├── section_parser.py          # Section parsing
└── README.md                  # Library documentation
```

**Usage**: Skills import from these libraries
```python
# In .claude/skills/shredding/scripts/shred_rfp.py
from shredding.rfp_shredder import RFPShredder
```

---

### `outputs/` - Generated Artifacts (NOT in git)

**Purpose**: Store all generated artifacts from skills

**Contains**:
- CSV files
- Excel files
- Reports (HTML, PDF)
- Visualizations
- Exports

**Organized By**: `outputs/<skill-name>/<artifact-type>/`

**Filename Convention**: `<identifier>_<artifact-type>_<YYYY-MM-DD>.<ext>`

**Examples**:
```
outputs/
├── shredding/
│   ├── compliance-matrices/
│   │   ├── FA8612-21-S-C001_compliance_matrix_2025-12-26.csv
│   │   ├── CSO-001_compliance_matrix_2025-12-26.csv
│   │   └── CSO-002_compliance_matrix_2025-12-26.csv
│   └── requirement-extracts/
│       └── RFP-12345_requirements_2025-12-26.json
│
├── data-analysis/
│   ├── reports/
│   │   └── sales_analysis_2025-12-26.html
│   └── visualizations/
│       └── trends_chart_2025-12-26.png
│
└── shared/
    └── exports/
        └── combined_data_2025-12-26.xlsx
```

**Git Status**: Excluded via `.gitignore`

---

### `docs/` - Documentation & Implementation Notes

**Purpose**: Store implementation documentation, design notes, and results

**Contains**:
- Implementation summaries
- Test results
- Design decisions
- Architecture diagrams
- Feature specifications

**Organized By**: `docs/<feature>/`

**Examples**:
```
docs/
├── shredding/
│   ├── CSO_FORMAT_SUPPORT_SUMMARY.md
│   ├── CSO_IMPLEMENTATION_COMPLETE.md
│   ├── CSO_PDF_FIX_RESULTS.md
│   └── FINAL_CSO_IMPLEMENTATION_RESULTS.md
│
├── data-analysis/
│   └── STATISTICAL_METHODS.md
│
└── architecture/
    ├── RAG_SYSTEM_DESIGN.md
    └── AGENT_ARCHITECTURE.md
```

**Git Status**: Tracked (committed to repository)

---

### `tests/` - Test Suites

**Purpose**: Unit tests, integration tests, and test utilities

**Structure**: Mirrors main codebase structure

**Examples**:
```
tests/
├── shredding/
│   ├── test_requirement_classifier.py
│   ├── test_requirement_extractor.py
│   ├── test_section_parser.py
│   ├── test_integration.py
│   └── test_e2e_cli.py
│
└── rag_system/
    ├── test_document_processor.py
    └── test_chunker.py
```

---

### `data/` - Input Data

**Purpose**: Store input datasets, documents, and reference data

**Contains**:
- RFP documents
- Training data
- Test datasets
- Reference documents

**Examples**:
```
data/
├── JADC2/
│   ├── FA8612-21-S-C001.txt
│   ├── 20210628_CSO_Call_001_DevSecOps_Network_FINAL.pdf
│   └── JADC2+CSO+Call+002+SDWAN_Bakeoff.pdf
│
├── training/
│   └── sample_rfps/
│
└── reference/
    └── FAR_templates/
```

---

## Why This Structure?

### Separation of Concerns

**Skills vs Implementation**:
- **`.claude/skills/<skill>/`** = Skill definition (what the skill does, how to use it)
- **`<feature>/`** = Implementation (how it actually works)
- This follows Anthropic's guidance: skills should be thin wrappers

**Outputs vs Source**:
- **`outputs/`** = Generated artifacts (changes frequently, not tracked)
- **Source directories** = Implementation code (tracked in git)
- Keeps working directory clean and organized

**Documentation vs Code**:
- **`docs/`** = Implementation notes, design decisions, results
- **`<feature>/README.md`** = API documentation for libraries
- **`.claude/skills/<skill>/SKILL.md`** = User-facing skill documentation

### Benefits

1. **Clean Top-Level Directory**: No clutter from generated files
2. **Predictable Locations**: Always know where to find things
3. **Easy Cleanup**: Can safely delete `outputs/` without losing code
4. **Git-Friendly**: Generated artifacts excluded, documentation tracked
5. **Skill Portability**: Skills can be shared with clear dependencies
6. **Scalability**: Structure supports many skills without confusion

---

## File Naming Conventions

### Generated Artifacts

**Pattern**: `<identifier>_<artifact-type>_<YYYY-MM-DD>.<ext>`

**Examples**:
- `FA8612-21-S-C001_compliance_matrix_2025-12-26.csv`
- `RFP-12345_requirements_2025-12-26.json`
- `sales_report_2025-12-26.html`

**Benefits**:
- Sortable by date
- Prevents overwrites
- Clear identification
- Consistent format

### Documentation Files

**Pattern**: `<TOPIC>_<TYPE>.md`

**Examples**:
- `CSO_FORMAT_SUPPORT_SUMMARY.md`
- `CSO_IMPLEMENTATION_COMPLETE.md`
- `STATISTICAL_METHODS.md`

**Benefits**:
- Uppercase for visibility
- Descriptive names
- Categorized by topic

---

## Git Tracking

### Tracked (Committed)

- `.claude/skills/` - Skill definitions
- `<feature>/` - Core libraries
- `tests/` - Test suites
- `docs/` - Documentation
- `CLAUDE.md` - Project instructions
- `.gitignore` - Git configuration

### Not Tracked (Ignored)

- `outputs/` - Generated artifacts
- `*.csv` - CSV files
- `*.xlsx` - Excel files
- `*.pdf` - PDF files (unless in `docs/` or `data/`)
- `__pycache__/` - Python cache
- `*.db` - Database files
- `.env` - Environment variables

---

## Implementation Guidelines

### Creating a New Skill

1. **Create core library**: `mkdir <feature>/`
2. **Add implementation code**: `<feature>/*.py`
3. **Create skill definition**: `.claude/skills/<feature>/SKILL.md`
4. **Add CLI scripts**: `.claude/skills/<feature>/scripts/*.py`
   - Import from `<feature>/` library
   - Output to `outputs/<feature>/`
5. **Write tests**: `tests/<feature>/`
6. **Document**: `docs/<feature>/`

### Generating Outputs

```python
from pathlib import Path
from datetime import datetime

def get_output_path(skill_name: str, artifact_type: str, filename: str) -> Path:
    """Get standardized output path for skill artifacts."""
    project_root = Path(__file__).parent.parent.parent.parent
    output_dir = project_root / "outputs" / skill_name / artifact_type
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    base_name = Path(filename).stem
    extension = Path(filename).suffix

    return output_dir / f"{base_name}_{timestamp}{extension}"

# Usage
output_file = get_output_path("shredding", "compliance-matrices", "FA8612-21-S-C001.csv")
output_file.write_text(data)
```

### Creating Documentation

```python
from pathlib import Path

def get_docs_path(feature: str, doc_name: str) -> Path:
    """Get standardized documentation path."""
    project_root = Path(__file__).parent.parent.parent.parent
    docs_dir = project_root / "docs" / feature
    docs_dir.mkdir(parents=True, exist_ok=True)

    return docs_dir / doc_name

# Usage
doc_file = get_docs_path("shredding", "IMPLEMENTATION_SUMMARY.md")
doc_file.write_text(content)
```

---

## Common Pitfalls to Avoid

### ❌ DON'T

- Output to top-level directory (creates clutter)
- Put implementation code in `.claude/skills/`
- Put skill definitions in `<feature>/`
- Hardcode output paths
- Commit generated artifacts to git
- Mix documentation with implementation code

### ✅ DO

- Use `outputs/<skill>/<type>/` for all artifacts
- Separate skills (`.claude/skills/`) from implementation (`<feature>/`)
- Include timestamps in output filenames
- Create parent directories with `mkdir(parents=True, exist_ok=True)`
- Document in `docs/<feature>/`
- Follow naming conventions

---

## Summary

**Key Principles**:

1. **Separation**: Skills ≠ Implementation ≠ Outputs ≠ Documentation
2. **Organization**: Predictable directory structure
3. **Cleanliness**: No top-level clutter
4. **Timestamps**: All outputs include dates
5. **Git-Friendly**: Generated files excluded

**Directory Functions**:

- `.claude/skills/` → Skill definitions and CLI scripts
- `<feature>/` → Core implementation libraries
- `outputs/` → Generated artifacts (not tracked)
- `docs/` → Documentation and notes (tracked)
- `tests/` → Test suites
- `data/` → Input datasets

**Remember**: When in doubt, check `CLAUDE.md` for the latest conventions!

---

**Last Updated**: 2025-12-26
**Maintained By**: Development team
**See Also**: `CLAUDE.md`, skill-specific `SKILL.md` files
