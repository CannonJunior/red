# Security Patterns & OWASP Top 10 Checks

This reference provides detailed security review patterns for Python code, focusing on OWASP Top 10 vulnerabilities.

## Table of Contents

1. [SQL Injection](#sql-injection)
2. [Command Injection](#command-injection)
3. [XSS (Cross-Site Scripting)](#xss)
4. [Insecure Deserialization](#insecure-deserialization)
5. [Sensitive Data Exposure](#sensitive-data-exposure)
6. [Authentication & Session Management](#authentication--session-management)
7. [Path Traversal](#path-traversal)
8. [Dependency Vulnerabilities](#dependency-vulnerabilities)

## SQL Injection

### Vulnerable Pattern

❌ **Never do this:**
```python
def get_user(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return db.execute(query)
```

### Secure Pattern

✅ **Always use parameterized queries:**
```python
def get_user(username: str) -> Optional[Dict]:
    """Get user by username (SQL injection safe)."""
    query = "SELECT * FROM users WHERE username = ?"
    return db.execute(query, (username,))
```

### With ORMs (SQLAlchemy)

✅ **Use ORM query builders:**
```python
from sqlalchemy import select
from models import User

def get_user(username: str) -> Optional[User]:
    """Get user by username using ORM."""
    stmt = select(User).where(User.username == username)
    return session.execute(stmt).scalar_one_or_none()
```

## Command Injection

### Vulnerable Pattern

❌ **Never use shell=True with user input:**
```python
import subprocess

def ping_host(hostname):
    subprocess.run(f"ping -c 1 {hostname}", shell=True)
```

### Secure Pattern

✅ **Use list arguments without shell:**
```python
import subprocess
import shlex
from typing import List

def ping_host(hostname: str) -> bool:
    """Ping host safely (command injection safe)."""
    # Validate hostname format
    if not hostname.replace('.', '').replace('-', '').isalnum():
        raise ValueError("Invalid hostname format")

    try:
        result = subprocess.run(
            ['ping', '-c', '1', hostname],
            capture_output=True,
            timeout=5,
            check=False
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
```

## XSS (Cross-Site Scripting)

### Web Framework Examples

✅ **Use framework escaping (Flask):**
```python
from flask import Flask, render_template_string, escape
from markupsafe import Markup

app = Flask(__name__)

@app.route('/user/<username>')
def show_user(username: str):
    # Automatic escaping in templates
    return render_template_string(
        '<h1>User: {{ username }}</h1>',
        username=username
    )

# For raw HTML (dangerous - only if absolutely necessary)
def render_safe_html(content: str):
    # Sanitize first with bleach or similar
    import bleach
    safe_content = bleach.clean(
        content,
        tags=['p', 'br', 'strong', 'em'],
        strip=True
    )
    return Markup(safe_content)
```

## Insecure Deserialization

### Vulnerable Pattern

❌ **Never use pickle with untrusted data:**
```python
import pickle

def load_data(serialized_data):
    return pickle.loads(serialized_data)  # DANGEROUS!
```

### Secure Pattern

✅ **Use JSON for untrusted data:**
```python
import json
from typing import Any, Dict

def load_data(serialized_data: str) -> Dict[str, Any]:
    """Safely deserialize data."""
    try:
        data = json.loads(serialized_data)
        # Validate structure
        if not isinstance(data, dict):
            raise ValueError("Expected dictionary")
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
```

## Sensitive Data Exposure

### Credentials Management

❌ **Never hardcode credentials:**
```python
DATABASE_URL = "postgresql://user:password@localhost/db"
API_KEY = "sk_live_abc123xyz"
```

✅ **Use environment variables:**
```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    database_url: str
    api_key: str

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment."""
        database_url = os.getenv('DATABASE_URL')
        api_key = os.getenv('API_KEY')

        if not database_url:
            raise ValueError("DATABASE_URL not set")
        if not api_key:
            raise ValueError("API_KEY not set")

        return cls(database_url=database_url, api_key=api_key)

# Use python-dotenv for local development
from dotenv import load_dotenv
load_dotenv()

config = Config.from_env()
```

### Password Hashing

❌ **Never store plain text passwords:**
```python
def create_user(username, password):
    db.execute("INSERT INTO users VALUES (?, ?)", (username, password))
```

✅ **Use bcrypt or argon2:**
```python
import bcrypt
from typing import str

def hash_password(password: str) -> bytes:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def verify_password(password: str, hashed: bytes) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def create_user(username: str, password: str):
    """Create user with hashed password."""
    hashed_password = hash_password(password)
    db.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, hashed_password)
    )
```

## Authentication & Session Management

### Secure Session Handling (Flask)

```python
from flask import Flask, session
from datetime import timedelta
import secrets

app = Flask(__name__)

# Generate strong secret key
app.secret_key = secrets.token_hex(32)

# Configure secure sessions
app.config.update(
    SESSION_COOKIE_SECURE=True,  # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,  # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1)
)

@app.route('/login', methods=['POST'])
def login():
    # Authenticate user
    if authenticate(username, password):
        session['user_id'] = user.id
        session['csrf_token'] = secrets.token_hex(16)
        return redirect('/dashboard')
    return 'Invalid credentials', 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
```

## Path Traversal

### Vulnerable Pattern

❌ **Never concatenate user input to file paths:**
```python
def read_file(filename):
    with open(f"/var/data/{filename}") as f:
        return f.read()
# Attacker could use: ../../../etc/passwd
```

### Secure Pattern

✅ **Validate and resolve paths:**
```python
from pathlib import Path
from typing import Optional

def read_file(filename: str, base_dir: Path = Path("/var/data")) -> Optional[str]:
    """Read file safely (path traversal safe)."""
    # Validate filename (no path separators)
    if '/' in filename or '\\' in filename:
        raise ValueError("Invalid filename: path separators not allowed")

    # Construct and resolve path
    file_path = (base_dir / filename).resolve()

    # Ensure resolved path is within base directory
    if not file_path.is_relative_to(base_dir):
        raise ValueError("Path traversal attempt detected")

    # Check file exists
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    # Read file
    with open(file_path, 'r') as f:
        return f.read()
```

## Dependency Vulnerabilities

### Scanning Dependencies

```bash
# Install safety
pip install safety

# Scan for known vulnerabilities
safety check

# Scan requirements file
safety check -r requirements.txt

# Output JSON
safety check --json
```

### Automated Scanning Script

```python
#!/usr/bin/env python3
"""Scan dependencies for known vulnerabilities."""

import subprocess
import json
import sys

def scan_dependencies():
    """Scan installed packages for vulnerabilities."""
    try:
        result = subprocess.run(
            ['safety', 'check', '--json'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            vulnerabilities = json.loads(result.stdout)
            print(f"❌ Found {len(vulnerabilities)} vulnerabilities:")
            for vuln in vulnerabilities:
                print(f"\n  Package: {vuln['package']}")
                print(f"  Installed: {vuln['installed_version']}")
                print(f"  Vulnerability: {vuln['vulnerability']}")
                print(f"  Fix: Upgrade to {vuln['fixed_version']}")
            sys.exit(1)
        else:
            print("✅ No known vulnerabilities found")
            sys.exit(0)

    except FileNotFoundError:
        print("❌ safety not installed. Install with: pip install safety")
        sys.exit(1)

if __name__ == "__main__":
    scan_dependencies()
```

## Security Checklist

- [ ] No SQL injection (parameterized queries)
- [ ] No command injection (no shell=True with user input)
- [ ] Proper input validation on all user data
- [ ] XSS prevention (framework escaping)
- [ ] No insecure deserialization (avoid pickle)
- [ ] Credentials in environment variables, not code
- [ ] Passwords properly hashed (bcrypt/argon2)
- [ ] Secure session configuration
- [ ] Path traversal prevention
- [ ] Dependencies scanned for vulnerabilities
- [ ] HTTPS enforced in production
- [ ] Rate limiting on authentication endpoints
- [ ] CSRF protection enabled
- [ ] Security headers configured
