---
name: code-validation
description: "Comprehensive Python code review and validation toolkit for assessing code quality, identifying issues, and ensuring best practices. When Claude needs to: (1) Review Python code for PEP8 compliance and style issues, (2) Identify potential bugs, security vulnerabilities, and edge cases, (3) Check for proper error handling and documentation, (4) Validate test coverage and code structure, or (5) Suggest performance and architectural improvements. Use for code review and quality assurance, not for writing new code from scratch."
---

# Python Code Review & Validation

## Overview

This skill provides comprehensive code review capabilities including style checking, security analysis, performance optimization, and best practices validation. It includes automated linting tools and detailed review guidelines.

## Quick Start

### Basic Code Review

```python
#!/usr/bin/env python3
"""
Example of well-structured Python code following best practices.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any

def load_config(config_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load configuration from file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary or None if load fails

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    config_path = Path("config.json")
    config = load_config(config_path)
    if config:
        print(f"Loaded config: {config}")
```

## Automated Review Tools

### Using Linting Scripts

Run the automated code review script (see [scripts/run_linters.py](scripts/run_linters.py)):

```bash
python scripts/run_linters.py path/to/code.py
```

This runs:
- **flake8**: Style and PEP8 compliance
- **pylint**: Code quality and potential bugs
- **mypy**: Type checking
- **bandit**: Security vulnerability scanning

## Code Review Checklist

### 1. Style & Formatting
- [ ] PEP8 compliant (line length, naming, spacing)
- [ ] Consistent naming conventions
- [ ] Type hints on all functions
- [ ] Docstrings in Google/NumPy format

### 2. Error Handling
- [ ] Try/except blocks for risky operations
- [ ] Specific exception types (not bare `except:`)
- [ ] Proper error messages and logging
- [ ] Resource cleanup (context managers)

### 3. Security
- [ ] No SQL injection vulnerabilities
- [ ] No command injection (validate subprocess inputs)
- [ ] No hardcoded credentials
- [ ] Input validation for all user data

### 4. Performance
- [ ] No unnecessary loops or iterations
- [ ] Efficient data structures
- [ ] Database queries optimized
- [ ] Proper use of generators for large datasets

### 5. Testing
- [ ] Unit tests for all functions
- [ ] Edge cases covered
- [ ] Mock external dependencies
- [ ] Test coverage >80%

## Quick Reference

| Check Type | Tool | Command |
|------------|------|---------|
| Style (PEP8) | flake8 | `flake8 --max-line-length=100 code.py` |
| Code quality | pylint | `pylint code.py` |
| Type checking | mypy | `mypy code.py` |
| Security | bandit | `bandit -r code.py` |
| Formatting | black | `black code.py` |
| Import sorting | isort | `isort code.py` |
| All checks | Script | `python scripts/run_linters.py code.py` |

## Common Issues & Fixes

### Issue: Missing Error Handling

❌ **Bad:**
```python
def read_file(path):
    return open(path).read()
```

✅ **Good:**
```python
from pathlib import Path
from typing import Optional

def read_file(path: Path) -> Optional[str]:
    """Read file contents with error handling."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {path}", file=sys.stderr)
        return None
    except PermissionError:
        print(f"Error: Permission denied: {path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return None
```

### Issue: Missing Type Hints

❌ **Bad:**
```python
def process(data):
    return data.upper()
```

✅ **Good:**
```python
def process(data: str) -> str:
    """Convert string to uppercase."""
    return data.upper()
```

### Issue: Hardcoded Values

❌ **Bad:**
```python
def connect():
    db = connect_db("localhost", 5432, "mydb")
    return db
```

✅ **Good:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class DbConfig:
    host: str
    port: int
    database: str

def load_db_config() -> DbConfig:
    """Load database config from environment or config file."""
    import os
    return DbConfig(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'mydb')
    )

def connect(config: Optional[DbConfig] = None) -> Any:
    """Connect to database using configuration."""
    if config is None:
        config = load_db_config()
    return connect_db(config.host, config.port, config.database)
```

## Advanced Topics

### Security Review
For detailed security patterns and OWASP Top 10 checks, see [references/security-patterns.md](references/security-patterns.md)

### Performance Optimization
For profiling and optimization techniques, see [references/performance-patterns.md](references/performance-patterns.md)

### Testing Strategies
For test coverage and testing patterns, see [references/testing-patterns.md](references/testing-patterns.md)

## Troubleshooting

### Tool Installation Issues

**Problem**: `flake8` or `pylint` not found
**Solution**: Install dev dependencies:
```bash
pip install flake8 pylint mypy bandit black isort
```

**Problem**: Type checking fails on third-party libraries
**Solution**: Install type stubs:
```bash
pip install types-requests types-PyYAML
```

### Common False Positives

**flake8 E501**: Line too long (>79 chars)
- Configure: `flake8 --max-line-length=100`
- Or add `.flake8` config file

**pylint C0103**: Invalid name
- Disable for specific cases: `# pylint: disable=invalid-name`

**mypy errors on dynamic code**
- Use `# type: ignore` for unavoidable dynamic cases
- Or use `cast()` for type assertions
