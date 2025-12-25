---
name: shredding
description: "Government RFP analysis and requirement extraction toolkit for breaking down solicitations into actionable compliance matrices. When Claude needs to: (1) Extract requirements from government RFPs (SAM.gov, FAR Section C/L/M), (2) Generate compliance matrices with task assignments, (3) Classify mandatory vs optional requirements using compliance keywords, (4) Create structured task lists from RFP sections, or (5) Analyze evaluation criteria and proposal instructions. Use for RFP shredding and compliance tracking, not for proposal writing."
---

# RFP Shredding & Compliance Management

## Overview

This skill automates the "shredding" process for government RFPs, particularly SAM.gov solicitations. It extracts requirements from Section C (Technical), Section L (Instructions), and Section M (Evaluation), generating compliance matrices and task assignments for proposal teams.

**Key Capabilities**:
- Extract requirements from RFP PDFs using local AI
- Classify mandatory/recommended/optional requirements
- Generate compliance matrices for tracking
- Assign tasks to team members (users or AI agents)
- Track proposal compliance status
- Export to CSV for external tools

## Quick Start

### Basic RFP Shredding

```python
#!/usr/bin/env python3
"""
Example: Shred an RFP and generate compliance matrix.
"""
import sys
from pathlib import Path
from shredding.rfp_shredder import RFPShredder

def shred_rfp_example():
    """Complete RFP shredding workflow."""
    # Initialize shredder
    shredder = RFPShredder(
        db_path="opportunities.db",
        ollama_url="http://localhost:11434"
    )

    # Shred RFP document
    result = shredder.shred_rfp(
        file_path="rfps/FA8732-25-R-0001.pdf",
        rfp_number="FA8732-25-R-0001",
        opportunity_name="IT Support Services",
        due_date="2025-03-15",
        create_tasks=True,
        auto_assign=True
    )

    if result['status'] == 'success':
        print(f"✅ Shredding complete!")
        print(f"  Opportunity ID: {result['opportunity_id']}")
        print(f"  Requirements extracted: {result['total_requirements']}")
        print(f"  Mandatory: {result['mandatory_count']}")
        print(f"  Tasks created: {result['tasks_created']}")
        print(f"\nCompliance matrix: {result['matrix_file']}")
    else:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    shred_rfp_example()
```

### Extract Specific Section

```python
from shredding.section_parser import SectionParser

# Initialize parser
parser = SectionParser()

# Extract Section C (Technical Requirements)
section_c = parser.extract_section(
    file_path="rfp.pdf",
    section="C"
)

print(f"Section C: {section_c['title']}")
print(f"Pages: {section_c['start_page']} - {section_c['end_page']}")
print(f"Requirements found: {len(section_c['requirements'])}")

for req in section_c['requirements'][:5]:  # First 5
    print(f"\n{req['id']}: {req['text'][:80]}...")
    print(f"  Type: {req['compliance_type']}")
    print(f"  Page: {req['page']}")
```

### Classify Single Requirement

```python
from shredding.requirement_classifier import RequirementClassifier

classifier = RequirementClassifier(ollama_url="http://localhost:11434")

# Classify a requirement
requirement_text = "The contractor shall provide secure authentication using NIST 800-63B standards."

classification = classifier.classify(requirement_text)

print(f"Compliance Type: {classification['compliance_type']}")  # mandatory
print(f"Category: {classification['category']}")  # technical
print(f"Priority: {classification['priority']}")  # high
print(f"Keywords: {classification['keywords']}")  # ['shall', 'secure', 'NIST']
```

## Automated Shredding Tools

### Using Shredding Scripts

Run the automated RFP shredding script (see [scripts/shred_rfp.py](scripts/shred_rfp.py)):

```bash
python scripts/shred_rfp.py rfp_12345.pdf \
    --rfp-number FA8732-25-R-0001 \
    --name "IT Support Services" \
    --due-date 2025-03-15 \
    --create-tasks \
    --auto-assign
```

This generates:
- **Compliance Matrix**: Excel/CSV file with all requirements
- **Opportunity**: Parent container in opportunities system
- **Tasks**: One task per requirement, assigned to team members
- **Search Index**: Requirements searchable across system

### Generate Compliance Matrix Only

```bash
python scripts/generate_matrix.py FA8732-25-R-0001 \
    --output compliance_matrix.xlsx \
    --format excel
```

### Validate Existing Matrix

```bash
python scripts/validate_compliance.py FA8732-25-R-0001 \
    --check-completeness \
    --check-assignments \
    --check-deadlines
```

## RFP Shredding Checklist

### 1. Document Upload
- [ ] RFP PDF accessible
- [ ] RFP number identified
- [ ] Response deadline confirmed
- [ ] Issuing agency noted

### 2. Section Extraction
- [ ] Section C (Technical) identified
- [ ] Section L (Instructions) identified
- [ ] Section M (Evaluation) identified
- [ ] Page numbers preserved

### 3. Requirement Extraction
- [ ] Mandatory requirements identified ("shall", "must", "will")
- [ ] Recommended requirements noted ("should")
- [ ] Optional requirements marked ("may", "can")
- [ ] Conditional requirements captured ("if...then")

### 4. Classification
- [ ] Technical vs management vs cost categorized
- [ ] Priority assigned (high/medium/low)
- [ ] Risk level assessed (red/yellow/green)
- [ ] Keywords extracted

### 5. Task Assignment
- [ ] Tasks created for each requirement
- [ ] Assignees designated (users or agents)
- [ ] Due dates calculated
- [ ] Dependencies identified

### 6. Compliance Tracking
- [ ] Matrix generated
- [ ] Status tracking enabled
- [ ] Proposal references documented
- [ ] Gaps identified

## Quick Reference

| Task | Script | Command |
|------|--------|---------|
| Shred RFP | shred_rfp.py | `python scripts/shred_rfp.py <file>` |
| Extract section | extract_sections.py | `python scripts/extract_sections.py <file> --section C` |
| Classify requirements | classify_requirements.py | `python scripts/classify_requirements.py <file>` |
| Generate matrix | generate_matrix.py | `python scripts/generate_matrix.py <opp_id>` |
| Assign tasks | assign_tasks.py | `python scripts/assign_tasks.py <opp_id>` |
| Validate compliance | validate_compliance.py | `python scripts/validate_compliance.py <opp_id>` |

## Compliance Matrix Columns

| Column | Description | Example |
|--------|-------------|---------|
| Req ID | Unique identifier | C-001, L-015, M-003 |
| Section | RFP section | C, L, M |
| Page | Source page number | 15 |
| Paragraph | Paragraph ID | 3.2.1 |
| Requirement Text | Full requirement | "The contractor shall..." |
| Compliance Type | Mandatory/Optional | Mandatory |
| Category | Technical/Management | Technical |
| Priority | High/Medium/Low | High |
| Risk | Red/Yellow/Green | Yellow |
| Compliance Status | F/P/N/Not Started | Fully |
| Proposal Section | Response location | 4.3 |
| Proposal Page | Response page | 42 |
| Assigned To | Person or agent | John Doe / Agent-Tech |
| Due Date | Task deadline | 2025-03-01 |
| Status | Task status | In Progress |
| Notes | Comments | Need clarification |

## Common Issues & Fixes

### Issue: Section Detection Fails

❌ **Bad: RFP uses non-standard section headers**
```
Problem: Parser can't find "SECTION C" or "Part C"
```

✅ **Good: Use manual section marking**
```python
from shredding.section_parser import SectionParser

parser = SectionParser()

# Manually specify section page ranges
sections = parser.extract_sections(
    file_path="rfp.pdf",
    section_ranges={
        'C': {'start_page': 10, 'end_page': 45},
        'L': {'start_page': 46, 'end_page': 52},
        'M': {'start_page': 53, 'end_page': 58}
    }
)
```

### Issue: Ollama Classification Too Slow

❌ **Bad: Classify requirements one-by-one**
```python
for req in requirements:
    classification = classifier.classify(req['text'])  # Slow!
```

✅ **Good: Batch classification**
```python
from shredding.requirement_classifier import RequirementClassifier

classifier = RequirementClassifier(batch_size=10)

# Classify in batches of 10
classifications = classifier.classify_batch(
    [req['text'] for req in requirements]
)
```

### Issue: Missing Conditional Requirements

❌ **Bad: Simple keyword matching misses conditionals**
```python
if "shall" in text:
    compliance_type = "mandatory"  # Misses "if X, then shall Y"
```

✅ **Good: Use Ollama for context-aware classification**
```python
from shredding.requirement_classifier import RequirementClassifier

classifier = RequirementClassifier()

# Ollama understands conditional requirements
classification = classifier.classify(
    "If the system fails, the contractor shall provide backup within 24 hours."
)
# Returns: compliance_type='mandatory', keywords=['conditional', 'shall', 'backup']
```

### Issue: Large RFPs Timeout

❌ **Bad: Process entire 500-page RFP at once**
```python
result = shredder.shred_rfp("huge_rfp.pdf")  # May timeout
```

✅ **Good: Process sections separately**
```python
from shredding.rfp_shredder import RFPShredder

shredder = RFPShredder()

# Process each section individually
for section in ['C', 'L', 'M']:
    shredder.process_section(
        file_path="huge_rfp.pdf",
        section=section,
        opportunity_id=opp_id
    )
```

## Advanced Topics

### FAR Section Structure
For detailed guidance on Federal Acquisition Regulation sections, see [references/far-sections-guide.md](references/far-sections-guide.md)

### Compliance Keywords
For comprehensive list of compliance keywords and patterns, see [references/compliance-keywords.md](references/compliance-keywords.md)

### Section L Analysis
For proposal instruction analysis patterns, see [references/section-l-patterns.md](references/section-l-patterns.md)

### Section M Scoring
For evaluation criteria and scoring strategies, see [references/section-m-patterns.md](references/section-m-patterns.md)

### NLP Techniques
For advanced requirement extraction methods, see [references/nlp-techniques.md](references/nlp-techniques.md)

## Troubleshooting

### Installation Issues

**Problem**: Ollama not responding
**Solution**: Check Ollama service:
```bash
curl http://localhost:11434/api/tags
# Should return list of models

# If not running:
ollama serve
```

**Problem**: Database not found
**Solution**: Run migration:
```bash
python migrations/001_add_shredding_tables.py
```

### Processing Issues

**Problem**: PDF extraction returns empty text
**Solution**: Check PDF format:
```python
from rag_system.document_processor import DocumentProcessor

processor = DocumentProcessor()
result = processor.process_document("rfp.pdf")

if result['status'] == 'error':
    print(f"Error: {result['error']}")
    # Try OCR or different PDF parser
```

**Problem**: Requirements not classified correctly
**Solution**: Review Ollama prompts:
```bash
# Test classification with verbose output
python scripts/classify_requirements.py rfp.pdf --verbose
```

### Common Errors

**"Section not found"**: RFP uses non-standard headers
- Use manual section marking with page ranges
- Check for Roman numerals (Part I, II, III)

**"No requirements extracted"**: Compliance keywords not detected
- Verify text extraction worked (check for scanned PDF)
- Add custom keywords to detection patterns

**"Classification timeout"**: Too many requirements
- Use batch processing
- Reduce batch size if memory issues

### Performance Tips

- Use batch classification for >20 requirements
- Process sections separately for large RFPs
- Cache Ollama responses for similar requirements
- Run on machine with 8GB+ RAM for best performance
- Use SSD for database storage

## Future Enhancements

### Phase 7+: Proposal Filling
- Auto-populate proposal templates (PowerPoint, Word, PDF)
- Retrieve responses from historical proposals via RAG
- Adapt responses to current RFP context

### Phase 8: Win Theme Extraction
- Extract customer priorities from Section M
- Identify discriminators vs table stakes
- Generate win theme suggestions

### Phase 9: SAM.gov Integration
- Auto-download matching RFPs from SAM.gov API
- Monitor for amendments and updates
- Track Q&A postings

## Support

For issues or questions:
- Check documentation in `references/`
- Review example outputs in `examples/`
- Test with sample RFPs in `examples/`
- Report issues in project issue tracker

---

**Skill Version**: 1.0.0
**Last Updated**: 2025-12-24
**Maintainer**: RAG System Team
