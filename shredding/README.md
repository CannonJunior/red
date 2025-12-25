# RFP Shredding Module

Automated RFP analysis and requirement extraction for government solicitations.

## Quick Start

### 1. Run Database Migration

```bash
python migrations/001_add_shredding_tables.py
```

### 2. Start Ollama

```bash
ollama serve
```

### 3. Shred an RFP

```python
from shredding.rfp_shredder import RFPShredder

shredder = RFPShredder()

result = shredder.shred_rfp(
    file_path="path/to/rfp.pdf",
    rfp_number="FA8732-25-R-0001",
    opportunity_name="IT Support Services",
    due_date="2025-03-15",
    create_tasks=True,
    auto_assign=True
)

print(f"✅ Extracted {result['total_requirements']} requirements")
print(f"📄 Matrix: {result['matrix_file']}")
```

### 4. Use Web UI

Navigate to: `http://localhost:9090/compliance-matrix.html`

## Module Structure

```
shredding/
├── __init__.py              # Package exports
├── section_parser.py        # Extract FAR sections (C, L, M)
├── requirement_extractor.py # Extract requirements from text
├── requirement_classifier.py # Classify with Ollama
└── rfp_shredder.py         # Main orchestrator
```

## Core Classes

### RFPShredder

Main orchestrator for complete shredding workflow.

**Methods**:
- `shred_rfp()`: Complete workflow (extract → classify → save → tasks)
- `get_opportunity_status()`: Get progress and statistics

### SectionParser

Extracts sections from RFP PDFs.

**Methods**:
- `extract_sections()`: Get all sections
- `extract_section()`: Get specific section (C, L, or M)
- `validate_sections()`: Check for critical sections

### RequirementExtractor

Extracts requirements from section text.

**Methods**:
- `extract_requirements()`: Extract requirements from text
- `deduplicate_requirements()`: Remove duplicates
- `filter_by_section()`: Filter requirements

### RequirementClassifier

Classifies requirements using Ollama LLM.

**Methods**:
- `classify()`: Classify single requirement
- `classify_batch()`: Classify multiple requirements
- `to_dict()`: Convert to dictionary

## Compliance Keywords

### Mandatory
- shall, must, will, required, mandatory

### Recommended
- should, encouraged, recommended, preferred

### Optional
- may, can, could, optional

## Classification Schema

Each requirement is classified with:

- **Compliance Type**: mandatory | recommended | optional
- **Category**: technical | management | cost | deliverable | compliance
- **Priority**: high | medium | low
- **Risk Level**: red | yellow | green
- **Keywords**: List of important terms
- **Entities**: Dates, standards, acronyms

## Database Schema

### requirements table

Stores extracted requirements with 25 columns including:
- Compliance metadata (type, category, priority, risk)
- Proposal tracking (section, page, status)
- Assignment (assignee_id, assignee_type)
- Extracted data (keywords, entities)

### rfp_metadata table

Stores RFP document metadata (30 columns).

## API Endpoints

### POST /api/shredding/shred
Start RFP shredding process.

### GET /api/shredding/status/{opportunity_id}
Get shredding status and progress.

### GET /api/shredding/requirements/{opportunity_id}
List requirements with filtering.

### PUT /api/shredding/requirements/{requirement_id}
Update requirement fields.

### GET /api/shredding/matrix/{opportunity_id}
Export compliance matrix as CSV.

## Example Output

```
✅ RFP SHREDDING COMPLETE
═══════════════════════════════════════

Opportunity ID: 12345678-1234-1234-1234-123456789abc

Requirements Extracted:
  Total:       142
  Mandatory:   98
  Recommended: 32
  Optional:    12

Tasks Created: 142

Compliance Matrix: FA8732-25-R-0001_compliance_matrix.csv

Sections Found:
  Section C: Statement of Work
    Pages: 10-45
  Section L: Instructions to Offerors
    Pages: 46-52
  Section M: Evaluation Criteria
    Pages: 53-58

═══════════════════════════════════════

Compliance Rate: 0.0%
Not Started: 142

Next steps:
  1. Review compliance matrix
  2. Assign requirements to team members
  3. Start addressing requirements
  4. Update compliance status as you progress
```

## Troubleshooting

### Ollama Connection Failed
```bash
curl http://localhost:11434/api/tags
# If fails:
ollama serve
```

### Database Migration Error
```bash
# Check database exists
ls -la opportunities.db

# Re-run migration
python migrations/001_add_shredding_tables.py
```

### Section Detection Failed
Use manual page ranges:
```python
sections = parser.extract_sections(
    file_path="rfp.pdf",
    section_ranges={
        'C': {'start_page': 10, 'end_page': 45},
        'L': {'start_page': 46, 'end_page': 52},
        'M': {'start_page': 53, 'end_page': 58}
    }
)
```

## Dependencies

- **Ollama**: Local LLM (qwen2.5:3b recommended)
- **Docling**: PDF extraction (via DocumentProcessor)
- **SQLite**: Database storage
- **Python 3.12+**: Runtime

## Performance

- **Small RFP** (50 requirements): ~2-3 minutes
- **Medium RFP** (150 requirements): ~5-8 minutes
- **Large RFP** (300+ requirements): ~10-15 minutes

Most time is spent in Ollama classification. Use batch processing for best results.

## See Also

- Full documentation: `.claude/skills/shredding/SKILL.md`
- Implementation summary: `.claude/skills/shredding/IMPLEMENTATION_COMPLETE.md`
- CLI tools: `.claude/skills/shredding/scripts/`
