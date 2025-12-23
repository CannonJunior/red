# Skill Creation Guide

This guide provides best practices for creating custom Claude skills based on Anthropic's skill design patterns.

## Overview

Skills are modular, self-contained packages that extend Claude's capabilities by providing specialized knowledge, workflows, and tools. They transform Claude from a general-purpose agent into a specialized agent equipped with domain-specific procedural knowledge.

## Core Principles

### 1. Concise is Key

**The context window is a public good.** Skills share context with system prompts, conversation history, other skills' metadata, and user requests.

- **Default assumption: Claude is already very smart** - Only add context Claude doesn't already have
- Challenge each piece of information: "Does Claude really need this explanation?"
- Prefer concise examples over verbose explanations
- Keep SKILL.md body under 500 lines

### 2. Progressive Disclosure

Use a three-level loading system to manage context efficiently:

1. **Metadata (name + description)** - Always in context (~100 words)
2. **SKILL.md body** - When skill triggers (<5k words)
3. **Bundled resources** - As needed by Claude

### 3. Set Appropriate Degrees of Freedom

- **High freedom (text-based instructions)**: Multiple valid approaches, context-dependent decisions
- **Medium freedom (pseudocode with parameters)**: Preferred patterns with acceptable variation
- **Low freedom (specific scripts)**: Fragile operations requiring consistency

## Skill Anatomy

Every skill consists of:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   ├── description: (required)
│   │   └── license: (optional)
│   └── Markdown instructions (required)
├── scripts/          (optional) - Executable code
├── references/       (optional) - Documentation loaded as needed
└── assets/           (optional) - Files used in output
```

### SKILL.md Structure

#### Frontmatter (YAML)

```yaml
---
name: skill-name
description: Comprehensive description of what this skill does and when to use it. This is CRITICAL - it determines when the skill activates. Be clear and thorough.
license: Optional license information
---
```

**Description Best Practices:**
- Start with the primary use case
- Include specific file types or domains
- List numbered use cases: "(1) Creating..., (2) Reading..., (3) Modifying..."
- Mention when NOT to use the skill

**Examples:**

✅ **Good Description:**
```yaml
description: "Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale."
```

❌ **Poor Description:**
```yaml
description: Extract text from PDF files
```

#### Body Structure

Recommended sections:

1. **Overview** - Brief summary of capabilities
2. **Quick Start** - Minimal working example
3. **Common Tasks** - Organized by use case
4. **Reference** - Tables, commands, troubleshooting
5. **Advanced Features** - Links to reference files

### Bundled Resources

#### scripts/

Executable code for deterministic reliability or frequently rewritten tasks.

**When to include:**
- Same code is repeatedly rewritten
- Deterministic reliability needed
- Complex operations prone to errors

**Example structure:**
```
scripts/
├── extract_form_fields.py
├── fill_pdf_form.py
└── validate_output.py
```

**Best practices:**
- Include error handling
- Accept command-line arguments
- Print clear error messages
- Return JSON for structured data

#### references/

Documentation loaded only when needed.

**When to include:**
- API documentation
- Database schemas
- Domain-specific knowledge
- Detailed workflow guides
- Company policies

**Example structure:**
```
references/
├── api_docs.md
├── schemas.md
└── troubleshooting.md
```

**Best practices:**
- Include table of contents for files >100 lines
- Reference clearly from SKILL.md
- Avoid duplication with SKILL.md
- Keep references one level deep

**Linking pattern:**
```markdown
## Advanced Features

- **Form filling**: See [forms.md](forms.md) for complete guide
- **API reference**: See [reference.md](reference.md) for all methods
```

#### assets/

Files used in output (not loaded into context).

**When to include:**
- Templates
- Images, icons, fonts
- Boilerplate code
- Sample documents

**Example structure:**
```
assets/
├── logo.png
├── template.xlsx
└── boilerplate/
    └── frontend-template/
```

### What NOT to Include

Do NOT create extraneous documentation:
- README.md
- INSTALLATION_GUIDE.md
- QUICK_REFERENCE.md
- CHANGELOG.md

Skills should only contain information needed for an AI agent to do the job.

## Writing Effective Instructions

### Use Progressive Disclosure Patterns

**Pattern 1: High-level guide with references**

```markdown
# PDF Processing

## Quick Start
[basic example]

## Advanced Features
- **Form filling**: See [forms.md](forms.md)
- **API reference**: See [reference.md](reference.md)
```

**Pattern 2: Domain-specific organization**

```
bigquery-skill/
├── SKILL.md
└── references/
    ├── finance.md
    ├── sales.md
    └── product.md
```

When user asks about sales metrics, Claude only reads sales.md.

**Pattern 3: Conditional details**

```markdown
# DOCX Processing

## Creating documents
Use docx-js for new documents.

## Editing documents
For simple edits, modify XML directly.

**For tracked changes**: See [redlining.md](redlining.md)
**For OOXML details**: See [ooxml.md](ooxml.md)
```

### Include Actionable Examples

Show complete, runnable examples:

```python
# Good: Complete example
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

Not just fragments:
```python
# Bad: Incomplete
pdf.pages
```

### Add Quick Reference Tables

```markdown
| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Extract text | pdfplumber | `page.extract_text()` |
| Create PDFs | reportlab | Canvas or Platypus |
```

### Include Troubleshooting

```markdown
## Troubleshooting

- **Scanned PDFs**: If the PDF is an image, use pytesseract with pdf2image
- **Encoding issues**: Save with `encoding='utf-8'`
- **Multiple pages**: Always iterate through `pdf.pages`
```

## Industry-Specific Best Practices

### Financial Models (Excel/XLSX)

**Color Coding Standards:**
- **Blue text**: Hardcoded inputs (RGB: 0,0,255)
- **Black text**: ALL formulas (RGB: 0,0,0)
- **Green text**: Links within workbook (RGB: 0,128,0)
- **Red text**: External file links (RGB: 255,0,0)
- **Yellow background**: Key assumptions (RGB: 255,255,0)

**Number Formatting:**
- Years as text: "2024" not "2,024"
- Currency: $#,##0 format with units in headers
- Zeros as dashes: "$#,##0;($#,##0);-"
- Percentages: 0.0% (one decimal)
- Negatives: Parentheses (123) not minus -123

**Formula Rules:**
- Place ALL assumptions in separate cells
- Use cell references, not hardcoded values
- Document sources in comments
- Verify zero formula errors

### Document Processing

**Always provide:**
- Library import statements
- File path handling
- Error handling examples
- Multiple format support

## Scripts Best Practices

### Structure

```python
#!/usr/bin/env python3
"""
Script description.

Usage:
    python script_name.py <input> <output>
"""

import sys
import json

def main():
    if len(sys.argv) != 3:
        print("Usage: python script_name.py <input> <output>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        # Process
        result = process(input_file)

        # Output as JSON
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"Success: Created {output_file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Return Structured Data

Return JSON for easy parsing:

```python
{
    "status": "success" | "error",
    "message": "Human-readable message",
    "data": { /* structured results */ },
    "errors": [ /* list of errors if any */ ]
}
```

## Testing Your Skills

### Checklist

- [ ] Description clearly states when to use the skill
- [ ] Quick Start example is complete and runnable
- [ ] All referenced files exist and are linked
- [ ] Scripts have error handling and help text
- [ ] SKILL.md is under 500 lines
- [ ] No extraneous documentation files
- [ ] Examples are concise and actionable
- [ ] Tables/references aid quick lookup
- [ ] File structure follows conventions

### Common Mistakes

❌ **Verbose descriptions**
```yaml
description: Extract text from PDFs
```

✅ **Comprehensive descriptions**
```yaml
description: "Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale."
```

❌ **Missing imports/context**
```python
# Bad
text = page.extract_text()
```

✅ **Complete examples**
```python
# Good
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

❌ **Single large file**
```
skill/
└── SKILL.md (1000 lines)
```

✅ **Progressive disclosure**
```
skill/
├── SKILL.md (300 lines)
└── references/
    ├── api_docs.md
    └── advanced.md
```

## Migration Checklist

For existing skills:

1. **Enhance Description**
   - [ ] List all use cases
   - [ ] Specify file types/domains
   - [ ] Clarify when to use vs not use

2. **Improve Structure**
   - [ ] Add Overview section
   - [ ] Ensure Quick Start exists
   - [ ] Add Quick Reference table

3. **Add Progressive Disclosure**
   - [ ] Move detailed content to references/
   - [ ] Add clear links from SKILL.md
   - [ ] Keep SKILL.md under 500 lines

4. **Add Scripts (if applicable)**
   - [ ] Create scripts/ directory
   - [ ] Add error handling
   - [ ] Accept CLI arguments
   - [ ] Return structured data

5. **Add Industry Standards**
   - [ ] Include domain-specific conventions
   - [ ] Add formatting standards
   - [ ] Include validation rules

6. **Improve Examples**
   - [ ] Make examples complete and runnable
   - [ ] Add imports and context
   - [ ] Include error handling
   - [ ] Show multiple use cases

## Examples from Anthropic Skills

### PDF Skill Structure
```
pdf/
├── SKILL.md (7KB - main guide)
├── forms.md (9KB - form filling workflow)
├── reference.md (16KB - advanced features)
├── scripts/
│   ├── check_fillable_fields.py
│   ├── extract_form_field_info.py
│   ├── fill_fillable_fields.py
│   └── convert_pdf_to_images.py
└── LICENSE.txt
```

### XLSX Skill Structure
```
xlsx/
├── SKILL.md (10KB - comprehensive guide)
├── recalc.py (formula recalculation script)
└── LICENSE.txt
```

### Key Patterns

1. **Main SKILL.md**: Quick start + common tasks + references
2. **Reference files**: Detailed workflows (forms.md)
3. **Scripts**: Deterministic operations with clear interfaces
4. **No extraneous files**: No READMEs, no changelogs

## Resources

- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Agent Skills Standard](https://agentskills.io)
- [Claude Skills Documentation](https://support.claude.com/en/articles/12512176-what-are-skills)
- [Creating Custom Skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)
