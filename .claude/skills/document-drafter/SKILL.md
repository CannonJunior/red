---
name: document-drafter
description: "GovCon proposal document drafting engine. When Claude needs to: (1) Draft Technical, Management, or Past Performance volumes from RFP requirements, (2) Map shredding output (requirements CSV/JSON) to proposal section headings, (3) Generate section prose via Ollama using Shipley-aligned prompts, (4) Produce formatted .docx files from base templates, (5) Create compliance matrices showing requirement-to-section mapping. Use AFTER the shredding skill has extracted requirements from the RFP."
---

# Document Drafter

## Overview

This skill drafts proposal volumes from RFP requirements extracted by the shredding skill. It maps requirements to appropriate sections, generates compliant prose via Ollama, and produces formatted DOCX files ready for proposal team review.

**Key Capabilities**:
- Load requirements from shredding output (JSON or CSV)
- Map requirements to Technical / Management / Past Performance sections
- Generate Shipley-aligned section prose via Ollama
- Output volume-level DOCX files using base templates
- Track compliance: which requirements each section addresses

## Workflow Position

```
[shredding] → requirements.json → document-drafter → volume_drafts/*.docx → [review]
```

## Quick Start

### Draft a Full Technical Volume

```
User: "Draft the Technical Volume for FA8612-25-R-0001 using the shredded requirements"

Claude runs document-drafter to:
1. Load requirements from outputs/shredding/FA8612-25-R-0001/requirements.json
2. Map requirements to Technical Volume sections (SOW → Approach, risks → Risk Management)
3. Generate section prose for each mapped section via Ollama
4. Write outputs/proposal/FA8612-25-R-0001/FA8612-25-R-0001_technical_volume_YYYY-MM-DD.docx
```

### Draft from CSV Requirements

```
User: "Create proposal drafts from the requirements in outputs/shredding/ABC-001/reqs.csv"

Claude runs document-drafter to:
1. Load requirements from CSV (columns: id, category, text, reference, priority)
2. Map all categories to target volumes
3. Draft all volumes where requirements were mapped
4. Report: N sections, M requirements addressed, volumes written
```

### Draft a Specific Volume Only

```
User: "Draft just the Management Volume for proposal XYZ"

Claude runs document-drafter specifying volumes=["management_volume"]
```

## Requirements File Format

The shredding skill outputs requirements in this format:

**JSON** (`requirements.json`):
```json
[
  {
    "id": "REQ-001",
    "category": "technical_requirement",
    "text": "The contractor shall provide 24/7 NOC support.",
    "reference": "SOW 3.2.1",
    "priority": "shall"
  }
]
```

**CSV** (`requirements.csv`):
```
id,category,text,reference,priority
REQ-001,technical_requirement,"The contractor shall provide 24/7 NOC support.",SOW 3.2.1,shall
```

## Category → Section Mapping

| Category | Target Volume | Target Section |
|---|---|---|
| `technical_requirement` | Technical | 2.0 Technical Approach |
| `security_requirement` | Technical | 2.2 Technical Solution |
| `risk_item` | Technical | 5.0 Risk Management |
| `management_requirement` | Management | 1.0 Management Approach |
| `staffing_requirement` | Management | 3.0 Key Personnel |
| `transition_requirement` | Management | 4.0 Transition Plan |
| `quality_requirement` | Management | 5.0 Quality Assurance Plan |
| `past_performance_requirement` | Past Performance | 2.0 Reference 1 |

Override via `SECTION_MAP_FILE` environment variable (path to JSON mapping file).

## Python API

```python
from proposal.document_generator import (
    draft_proposal,
    load_requirements_from_json,
    load_requirements_from_csv,
)

# Load requirements from shredding output
reqs = load_requirements_from_json(Path("outputs/shredding/FA001/requirements.json"))

# Draft all volumes
result = draft_proposal(
    requirements=reqs,
    proposal_title="AFRL AI Research Support",
    solicitation_number="FA8612-25-R-0001",
    company_name="Acme Federal Solutions",
    # Optionally limit volumes:
    volumes=["technical_volume", "management_volume"],
)

print(result.volumes_written)   # Dict[volume_name, Path]
print(result.sections_generated)
print(result.errors)
```

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `TEMPLATES_DIR` | `templates/proposal/` | Base .docx template directory |
| `OUTPUTS_DIR` | `outputs/proposal/` | Where to write draft files |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model for prose generation |
| `DOC_MAX_TOKENS` | `800` | Max tokens per section |
| `DOC_TEMPERATURE` | `0.4` | Ollama temperature |
| `SECTION_MAP_FILE` | (none) | JSON override for section mapping |

## Ollama Fallback

If Ollama is unavailable, each section receives a labeled placeholder:

```
[ DRAFT REQUIRED — Section: 2.0 Technical Approach ]

This section addresses requirements: REQ-001, REQ-002, REQ-003

Please draft content that addresses each requirement. Refer to the
requirements matrix for compliance mapping.
```

This ensures the document is always produced — the proposal team can fill
in placeholders manually if generation fails.

## Outputs

Generated files follow the naming convention:
```
outputs/proposal/{solicitation_number}/{sol_number}_{volume}_{YYYY-MM-DD}.docx
```

Example:
```
outputs/proposal/FA8612-25-R-0001/
  FA8612-25-R-0001_technical_volume_2026-03-29.docx
  FA8612-25-R-0001_management_volume_2026-03-29.docx
```

## Regenerating Templates

If base templates are missing, regenerate them:

```bash
uv run templates/proposal/generate_templates.py
```
