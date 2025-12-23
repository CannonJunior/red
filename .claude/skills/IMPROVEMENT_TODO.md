# Skills Improvement TODO List

This document outlines specific improvements needed for the custom skills in `.claude/skills/` based on comparison with Anthropic's production skills.

## Summary of Current State

### Current Custom Skills
**Note**: PDF functionality is now provided by the Anthropic `pdf` skill from the document-skills plugin. This TODO focuses on improving the remaining local skills.

1. **data-analysis** - Basic pandas data analysis
2. **code-validation** - Python code review patterns

### Key Gaps Identified

| Feature | Current Skills | Anthropic Skills | Gap |
|---------|---------------|------------------|-----|
| Description depth | 1 sentence | 2-3 sentences with use cases | ⚠️ High |
| Progressive disclosure | None | references/ + scripts/ | ⚠️ High |
| Scripts | None | 5-8 scripts per skill | ⚠️ High |
| Quick Reference tables | None | Present | ⚠️ Medium |
| Troubleshooting | Minimal | Comprehensive | ⚠️ Medium |
| Industry standards | None | Financial model standards, etc. | ⚠️ Medium |
| Complete examples | Partial | Full runnable code | ⚠️ Low |
| File organization | Flat | Progressive disclosure | ⚠️ High |

---

## Priority 1: Critical Improvements

### 1.1 Enhance Skill Descriptions

**Current State:**
- Descriptions are too brief
- Don't specify when to use vs not use
- Missing numbered use cases

**Action Items:**

#### pdf-extraction/SKILL.md
```yaml
# Current
description: Extract text and tables from PDF files, handle multiple pages, and export to text format. Use when the user needs to extract or parse text content from PDF documents.

# Improved
description: "Comprehensive PDF text and table extraction toolkit for analyzing document content, handling multi-page documents, and exporting to structured formats. When Claude needs to: (1) Extract text from PDF documents, (2) Parse tables from PDFs to CSV/Excel, (3) Handle scanned PDFs with OCR, (4) Batch process multiple PDF files, or (5) Analyze PDF document structure. Not for PDF creation or form filling - see pdf skill for those tasks."
```

#### data-analysis/SKILL.md
```yaml
# Current
description: Analyze data from CSV/JSON files and generate formatted reports with findings. Use when analyzing datasets, creating reports, or summarizing data insights.

# Improved
description: "Comprehensive data analysis and reporting toolkit for exploring datasets, identifying trends, and generating formatted analytical reports. When Claude needs to: (1) Analyze CSV/JSON/Excel datasets, (2) Generate statistical summaries and visualizations, (3) Identify patterns and trends in data, (4) Create formatted analysis reports with findings, or (5) Clean and transform data for analysis. Use for exploratory data analysis and reporting, not for machine learning model training."
```

#### code-validation/SKILL.md
```yaml
# Current
description: Review Python code for quality, style compliance, and potential issues. Use when analyzing code quality, checking style consistency, or validating scripts.

# Improved
description: "Python code review and validation toolkit for assessing code quality, identifying issues, and ensuring best practices. When Claude needs to: (1) Review Python code for PEP8 compliance and style issues, (2) Identify potential bugs and edge cases, (3) Check for security vulnerabilities, (4) Validate error handling and documentation, or (5) Suggest performance improvements. Use for code review and quality assurance, not for writing new code from scratch."
```

**Priority:** 🔴 High
**Effort:** 1 hour
**Impact:** High - Better skill activation

---

### 1.2 Add Progressive Disclosure Structure

**Current State:**
- All content in single SKILL.md file
- No separation of concerns
- Cannot load content conditionally

**Action Items:**

#### pdf-extraction/ - Add reference files

Create structure:
```
pdf-extraction/
├── SKILL.md (main quick start + overview)
├── references/
│   ├── table-extraction.md (detailed table parsing)
│   ├── ocr-scanned-pdfs.md (OCR workflows)
│   └── batch-processing.md (multi-file processing)
└── scripts/
    ├── extract_text.py
    ├── extract_tables.py
    └── extract_with_ocr.py
```

**SKILL.md updates:**
- Keep quick start example
- Add links to reference files
- Remove detailed explanations (move to references/)

**Priority:** 🔴 High
**Effort:** 3 hours
**Impact:** High - Reduced context window usage

#### data-analysis/ - Add reference files

Create structure:
```
data-analysis/
├── SKILL.md (main quick start + overview)
├── references/
│   ├── statistical-analysis.md
│   ├── visualization.md
│   ├── time-series.md
│   └── data-cleaning.md
└── scripts/
    ├── generate_summary.py
    ├── create_report.py
    └── validate_data.py
```

**Priority:** 🔴 High
**Effort:** 3 hours
**Impact:** High - Better organization

#### code-validation/ - Add reference files

Create structure:
```
code-validation/
├── SKILL.md (main checklist + overview)
├── references/
│   ├── security-patterns.md
│   ├── performance-patterns.md
│   └── testing-patterns.md
└── scripts/
    ├── run_linters.py
    ├── check_security.py
    └── validate_tests.py
```

**Priority:** 🔴 High
**Effort:** 3 hours
**Impact:** High - More comprehensive reviews

---

### 1.3 Add Executable Scripts

**Current State:**
- No scripts directory
- All operations described as code snippets
- Claude rewrites same code repeatedly

**Action Items:**

#### pdf-extraction/scripts/

**extract_text.py**
```python
#!/usr/bin/env python3
"""
Extract all text from a PDF file.

Usage:
    python extract_text.py <input.pdf> <output.txt>
"""

import sys
import pdfplumber
import json

def main():
    if len(sys.argv) != 3:
        print("Usage: python extract_text.py <input.pdf> <output.txt>", file=sys.stderr)
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with pdfplumber.open(input_pdf) as pdf:
            text = ""
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"--- Page {i+1} ---\n{page_text}\n\n"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)

        print(json.dumps({
            "status": "success",
            "message": f"Extracted text to {output_file}",
            "pages": len(pdf.pages)
        }))

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**extract_tables.py** - Similar structure for table extraction
**extract_with_ocr.py** - OCR workflow script

**Priority:** 🔴 High
**Effort:** 4 hours
**Impact:** High - Deterministic operations

#### data-analysis/scripts/

**generate_summary.py** - Statistical summary generation
**create_report.py** - Formatted report creation
**validate_data.py** - Data quality checks

**Priority:** 🔴 High
**Effort:** 4 hours
**Impact:** High - Reliable analysis

#### code-validation/scripts/

**run_linters.py** - Run pylint, flake8, black
**check_security.py** - Security vulnerability scanning
**validate_tests.py** - Test coverage analysis

**Priority:** 🔴 High
**Effort:** 4 hours
**Impact:** High - Automated validation

---

## Priority 2: Important Improvements

### 2.1 Add Quick Reference Tables

**Current State:**
- No quick reference sections
- Users must read entire document

**Action Items:**

#### pdf-extraction/SKILL.md - Add table

```markdown
## Quick Reference

| Task | Tool | Command |
|------|------|---------|
| Extract all text | pdfplumber | `python scripts/extract_text.py input.pdf output.txt` |
| Extract tables | pdfplumber | `python scripts/extract_tables.py input.pdf output.csv` |
| OCR scanned PDF | pytesseract | `python scripts/extract_with_ocr.py input.pdf output.txt` |
| Batch processing | custom | See [batch-processing.md](references/batch-processing.md) |
```

**Priority:** 🟡 Medium
**Effort:** 1 hour
**Impact:** Medium - Faster reference

#### data-analysis/SKILL.md - Add table

```markdown
## Quick Reference

| Analysis Type | Function | Script |
|--------------|----------|--------|
| Summary statistics | pandas.describe() | `python scripts/generate_summary.py data.csv` |
| Trend analysis | pandas groupby/rolling | See [time-series.md](references/time-series.md) |
| Data cleaning | pandas dropna/fillna | See [data-cleaning.md](references/data-cleaning.md) |
| Report generation | markdown + pandas | `python scripts/create_report.py data.csv report.md` |
```

**Priority:** 🟡 Medium
**Effort:** 1 hour
**Impact:** Medium - Better UX

#### code-validation/SKILL.md - Add table

```markdown
## Quick Reference

| Check Type | Tool | Script |
|------------|------|--------|
| Style (PEP8) | flake8 | `python scripts/run_linters.py code.py` |
| Security | bandit | `python scripts/check_security.py code.py` |
| Type checking | mypy | Include in run_linters.py |
| Test coverage | pytest-cov | `python scripts/validate_tests.py` |
```

**Priority:** 🟡 Medium
**Effort:** 1 hour
**Impact:** Medium - Clear guidance

---

### 2.2 Expand Troubleshooting Sections

**Current State:**
- Minimal troubleshooting
- Missing common issues

**Action Items:**

#### pdf-extraction/SKILL.md

```markdown
## Troubleshooting

### Common Issues

**Scanned PDFs (no extractable text)**
- **Symptom**: Empty or garbled text output
- **Solution**: Use OCR with pytesseract: `python scripts/extract_with_ocr.py`
- **Requirements**: Install tesseract-ocr system package

**Encoding errors with special characters**
- **Symptom**: UnicodeDecodeError or strange characters
- **Solution**: Always use `encoding='utf-8'` when writing files
- **Example**: Scripts automatically handle UTF-8

**Tables not detected**
- **Symptom**: Table data appears as plain text
- **Solution**: Adjust table detection settings in pdfplumber
- **See**: [table-extraction.md](references/table-extraction.md) for advanced options

**Large PDFs timeout or crash**
- **Symptom**: Memory errors or long processing time
- **Solution**: Process page by page or use batch processing
- **See**: [batch-processing.md](references/batch-processing.md)
```

**Priority:** 🟡 Medium
**Effort:** 2 hours
**Impact:** Medium - Fewer errors

---

### 2.3 Add Complete Runnable Examples

**Current State:**
- Examples missing imports
- No error handling shown
- Snippets vs complete code

**Action Items:**

Update all code examples to be complete:

```python
# ❌ Current (incomplete)
with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i+1} ---")
        text = page.extract_text()
        print(text)

# ✅ Improved (complete)
import pdfplumber
import sys

def extract_pdf_text(pdf_path):
    """Extract text from all pages of a PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    all_text.append(f"--- Page {i+1} ---\n{text}")
            return "\n\n".join(all_text)
    except FileNotFoundError:
        print(f"Error: File {pdf_path} not found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error processing PDF: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <file.pdf>")
        sys.exit(1)

    text = extract_pdf_text(sys.argv[1])
    if text:
        print(text)
```

**Priority:** 🟡 Medium
**Effort:** 2 hours
**Impact:** Medium - Better examples

---

## Priority 3: Nice-to-Have Improvements

### 3.1 Add Industry-Specific Standards

**For data-analysis skill:**

Add section on data analysis best practices:

```markdown
## Data Analysis Standards

### Reporting Requirements

**Always include in reports:**
- Data source and date collected
- Sample size and coverage
- Statistical confidence levels
- Assumptions and limitations
- Methodology description

### Number Formatting

- **Percentages**: One decimal (e.g., 15.3%)
- **Currency**: Include currency symbol and units
- **Large numbers**: Use thousands separators (1,234,567)
- **Precision**: Match precision to data quality

### Visualization Guidelines

- Always label axes
- Include units in axis labels
- Add data source in caption
- Use colorblind-friendly palettes
- Include sample size in title
```

**Priority:** 🟢 Low
**Effort:** 2 hours
**Impact:** Low - Professional polish

### 3.2 Add Assets (if applicable)

**For data-analysis:**

```
data-analysis/
└── assets/
    ├── report-template.md
    └── color-palettes.json
```

**Priority:** 🟢 Low
**Effort:** 1 hour
**Impact:** Low - Consistency

---

## Implementation Timeline

### Week 1: Priority 1 (Critical)
- [ ] Day 1-2: Enhance all skill descriptions (3 hours)
- [ ] Day 3-4: Add progressive disclosure structure (9 hours)
- [ ] Day 5: Create first set of scripts for pdf-extraction (4 hours)

### Week 2: Priority 1 Continued
- [ ] Day 1: Create scripts for data-analysis (4 hours)
- [ ] Day 2: Create scripts for code-validation (4 hours)
- [ ] Day 3-4: Create reference files for all skills (8 hours)

### Week 3: Priority 2 (Important)
- [ ] Day 1: Add quick reference tables (3 hours)
- [ ] Day 2: Expand troubleshooting sections (6 hours)
- [ ] Day 3: Update all examples to be complete (6 hours)

### Week 4: Priority 3 (Nice-to-Have)
- [ ] Day 1: Add industry standards (4 hours)
- [ ] Day 2: Create assets (2 hours)
- [ ] Day 3: Final review and testing (6 hours)

**Total Estimated Effort:** ~60 hours

---

## Testing Checklist

After implementing improvements, verify:

### For Each Skill:

- [ ] Description is comprehensive (2-3 sentences)
- [ ] Lists numbered use cases
- [ ] States when NOT to use
- [ ] SKILL.md is under 500 lines
- [ ] Has Quick Start section
- [ ] Has Quick Reference table
- [ ] Has Troubleshooting section
- [ ] All examples are complete and runnable
- [ ] All reference files are linked
- [ ] All scripts have error handling
- [ ] All scripts accept CLI arguments
- [ ] All scripts return JSON for structured data
- [ ] No extraneous files (README, etc.)

### Integration Testing:

- [ ] Skill activates at appropriate times
- [ ] Reference files load when needed
- [ ] Scripts execute without errors
- [ ] Examples run successfully
- [ ] Error messages are clear and helpful

---

## Metrics for Success

Track improvements with these metrics:

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Avg description length | 15 words | 50 words | - |
| Scripts per skill | 0 | 3-5 | - |
| Reference files per skill | 0 | 2-4 | - |
| SKILL.md line count | 50 | <500 | - |
| Complete examples | 0% | 100% | - |
| Has quick reference | 0/3 | 3/3 | - |
| Has troubleshooting | 0/3 | 3/3 | - |

---

## Resources

- See [SKILL_CREATION_GUIDE.md](SKILL_CREATION_GUIDE.md) for detailed patterns
- Review Anthropic skills at `/home/junior/.claude/plugins/cache/anthropic-agent-skills/`
- Test skills by running Claude Code and triggering them

---

## Notes

**Key Learnings from Anthropic Skills:**

1. **Progressive disclosure is critical** - Don't load everything at once
2. **Scripts provide deterministic reliability** - Stop rewriting the same code
3. **Comprehensive descriptions drive activation** - Be thorough in frontmatter
4. **Reference files keep SKILL.md lean** - Move details to conditional loading
5. **Quick reference tables improve UX** - Fast lookup without reading everything
6. **Troubleshooting prevents common errors** - Address known issues proactively
7. **Complete examples are essential** - Show imports, error handling, full context
8. **Industry standards add professionalism** - Domain-specific conventions matter
