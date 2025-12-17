---
name: code-validation
description: Review Python code for quality, style compliance, and potential issues. Use when analyzing code quality, checking style consistency, or validating scripts.
---

# Code Review & Validation

## Review checklist

When reviewing code, check:
1. Style compliance - Is code PEP8 compliant?
2. Error handling - Are edge cases handled?
3. Documentation - Are functions documented?
4. Performance - Any obvious inefficiencies?
5. Security - Any potential vulnerabilities?

## Common patterns

### Good error handling
```python
try:
    data = open(file_path).read()
except FileNotFoundError:
    print(f"File {file_path} not found")
    data = None
except Exception as e:
    print(f"Error reading file: {e}")
    data = None
```

### Good documentation
```python
def process_data(input_file: str, format: str = "csv") -> dict:
    """
    Process data from input file.

    Args:
        input_file (str): Path to input file
        format (str): File format (csv, json, xml)

    Returns:
        dict: Processed data
    """
```

### Common issues to flag
- Missing type hints
- No error handling
- No docstrings
- Hardcoded values instead of configuration
- Missing input validation
- Inefficient loops or queries
