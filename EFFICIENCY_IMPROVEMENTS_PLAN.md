# Efficiency Improvements Plan

**Date**: 2025-12-09
**Status**: Ready for Implementation
**Estimated Total Time**: 4-6 hours for all quick wins

---

## Quick Wins (No Major Refactoring Required)

### Phase 1: Debug Logging Cleanup (1 hour)

**Priority**: HIGH
**Impact**: Cleaner logs, easier debugging, better production experience

#### 1.1 Create Debug Logging Utility
**File**: `debug_logger.py`
```python
import os
from datetime import datetime

DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

def debug_log(message, emoji="🔍"):
    if DEBUG_MODE:
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"{emoji} [{timestamp}] {message}")

def info_log(message, emoji="ℹ️"):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"{emoji} [{timestamp}] {message}")
```

#### 1.2 Replace Print Statements in server.py
**Locations**: Lines 308, 312, 321, 345, 350, 377, 382, 401, 431-432, 527, 570, 694, 709, 747, 750, etc.

**Before**:
```python
print(f"🔧 MCP Tool call: {tool_name}")
```

**After**:
```python
debug_log(f"MCP Tool call: {tool_name}", "🔧")
```

**Benefits**:
- ~150 lines cleaned up
- Production logs 70% quieter
- Debug mode available via `DEBUG_MODE=true`

---

### Phase 2: Frontend Console Log Cleanup (30 minutes)

**Priority**: MEDIUM
**Impact**: Cleaner browser console, easier frontend debugging

#### 2.1 Add Debug Flag to app.js
**Top of file**:
```javascript
const DEBUG_MODE = localStorage.getItem('DEBUG_MODE') === 'true';

function debugLog(...args) {
    if (DEBUG_MODE) console.log(...args);
}
```

#### 2.2 Replace console.log Statements
**Locations**: 69 instances throughout app.js

**Before**:
```javascript
console.log('MCP Tool inputs collected:', formData);
```

**After**:
```javascript
debugLog('MCP Tool inputs collected:', formData);
```

**Benefits**:
- Clean production console
- Enable with: `localStorage.setItem('DEBUG_MODE', 'true')`
- ~69 statements cleaned up

---

### Phase 3: Availability Check Decorator (45 minutes)

**Priority**: HIGH
**Impact**: Reduce ~250 lines of duplicate code

#### 3.1 Create Decorator
**File**: `server_decorators.py`
```python
from functools import wraps

def require_system(*systems):
    """
    Decorator to check system availability before handler execution.

    Usage:
        @require_system('rag', 'cag')
        def handle_rag_api(self):
            # RAG logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for system in systems:
                available_var = f"{system.upper()}_AVAILABLE"
                if not globals().get(available_var, False):
                    self.send_json_response({
                        'status': 'error',
                        'message': f'{system.upper()} system not available'
                    }, 503)
                    return
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
```

#### 3.2 Apply to Handlers
**Before (5 lines)**:
```python
def handle_rag_api(self):
    if not RAG_AVAILABLE:
        self.send_json_response({
            'status': 'error',
            'message': 'RAG system not available'
        }, 503)
        return
    # handler logic
```

**After (2 lines)**:
```python
@require_system('rag')
def handle_rag_api(self):
    # handler logic
```

**Apply to**: 61+ handlers

**Benefits**:
- ~200 lines removed
- Consistent error handling
- Easier to add new system checks

---

### Phase 4: Static Asset Caching (1 hour)

**Priority**: MEDIUM
**Impact**: Faster page loads, reduced disk I/O

#### 4.1 Implement In-Memory Cache
**File**: `static_cache.py`
```python
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta

class StaticCache:
    def __init__(self, ttl_minutes=60):
        self.cache = {}  # {path: {'content': bytes, 'etag': str, 'expires': datetime}}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, file_path):
        if file_path in self.cache:
            entry = self.cache[file_path]
            if datetime.now() < entry['expires']:
                return entry['content'], entry['etag']
        return None, None

    def set(self, file_path, content):
        etag = hashlib.md5(content).hexdigest()
        self.cache[file_path] = {
            'content': content,
            'etag': etag,
            'expires': datetime.now() + self.ttl
        }
        return etag

    def invalidate(self, file_path):
        if file_path in self.cache:
            del self.cache[file_path]
```

#### 4.2 Use in server.py
**Location**: Lines 178-179

**Before**:
```python
with open(full_path, 'rb') as f:
    content = f.read()
```

**After**:
```python
content, etag = static_cache.get(full_path)
if content is None:
    with open(full_path, 'rb') as f:
        content = f.read()
    etag = static_cache.set(full_path, content)

# Add ETag header
self.send_header('ETag', etag)
```

**Benefits**:
- 10x faster static file serving
- Reduced disk I/O
- Browser caching support

---

### Phase 5: Request Body Parsing Helper (30 minutes)

**Priority**: LOW
**Impact**: ~60 lines reduction, cleaner code

#### 5.1 Add Helper Method to Handler Class
```python
def get_request_body(self):
    """Parse JSON request body safely."""
    try:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))
    except (ValueError, json.JSONDecodeError) as e:
        return None
```

#### 5.2 Use in Handlers
**Before (3 lines)**:
```python
content_length = int(self.headers.get('Content-Length', 0))
post_data = self.rfile.read(content_length)
request_data = json.loads(post_data.decode('utf-8'))
```

**After (1 line)**:
```python
request_data = self.get_request_body()
```

**Apply to**: 20+ handlers

**Benefits**:
- ~60 lines removed
- Consistent error handling
- Easier to add request validation

---

### Phase 6: Remove Duplicate Imports (10 minutes)

**Priority**: LOW
**Impact**: Code cleanliness

#### 6.1 Clean Up server.py
**Remove duplicates at**:
- Lines 47-48 (sys, os already imported at top)
- Lines 418-420 (repeated in function)

**Benefits**:
- Cleaner imports section
- No functional change

---

### Phase 7: Frontend Request Memoization (1 hour)

**Priority**: MEDIUM
**Impact**: Faster UI, reduced server load

#### 7.1 Add Request Cache
**File**: app.js (top level)
```javascript
class RequestCache {
    constructor(ttl = 300000) { // 5 minutes default
        this.cache = new Map();
        this.ttl = ttl;
    }

    get(key) {
        const entry = this.cache.get(key);
        if (entry && Date.now() - entry.timestamp < this.ttl) {
            return entry.data;
        }
        this.cache.delete(key);
        return null;
    }

    set(key, data) {
        this.cache.set(key, { data, timestamp: Date.now() });
    }

    invalidate(pattern) {
        for (const key of this.cache.keys()) {
            if (key.includes(pattern)) {
                this.cache.delete(key);
            }
        }
    }
}

const requestCache = new RequestCache();
```

#### 7.2 Use for Idempotent Requests
**Apply to**: GET requests for models, prompts, search

**Before**:
```javascript
const response = await fetch('/api/models');
```

**After**:
```javascript
let data = requestCache.get('/api/models');
if (!data) {
    const response = await fetch('/api/models');
    data = await response.json();
    requestCache.set('/api/models', data);
}
```

**Benefits**:
- Instant UI updates for cached data
- Reduced server load
- Better perceived performance

---

### Phase 8: CORS Configuration Cleanup (15 minutes)

**Priority**: LOW
**Impact**: Better security, environment-based config

#### 8.1 Move to Environment Variable
**Add to server.py top**:
```python
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
```

#### 8.2 Use in Header Setting
**Before**:
```python
self.send_header('Access-Control-Allow-Origin', '*')
```

**After**:
```python
origin = self.headers.get('Origin', '')
if '*' in ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS:
    self.send_header('Access-Control-Allow-Origin', origin or '*')
```

**Benefits**:
- Environment-based security
- Production-ready CORS
- Easy to configure per deployment

---

## Implementation Order (Recommended)

1. **Phase 3**: Availability Check Decorator (biggest code reduction)
2. **Phase 1**: Debug Logging Cleanup (biggest log improvement)
3. **Phase 4**: Static Asset Caching (biggest performance gain)
4. **Phase 5**: Request Body Parsing Helper (cleanup)
5. **Phase 2**: Frontend Console Log Cleanup (UX improvement)
6. **Phase 7**: Frontend Request Memoization (performance)
7. **Phase 8**: CORS Configuration Cleanup (security)
8. **Phase 6**: Remove Duplicate Imports (final cleanup)

---

## Expected Results

### Code Metrics
- **Lines of code removed**: ~450-500 lines
- **Duplicate code eliminated**: ~70%
- **Files modified**: 3 main files + 3 new utility files

### Performance Metrics
- **Static file serving**: 10x faster (cached)
- **Frontend data fetching**: 100x faster (cached requests)
- **Server logs**: 70% reduction in production mode
- **Memory usage**: +10-20MB for caches (acceptable)

### Development Experience
- **Cleaner logs**: Easy to find actual issues
- **Better debugging**: Toggle debug mode on/off
- **Easier maintenance**: Less duplicate code
- **Consistent patterns**: Decorators and helpers

---

## Testing Checklist

After each phase:
- [ ] Server starts without errors
- [ ] All existing functionality works
- [ ] Debug mode toggle works correctly
- [ ] Static files load correctly
- [ ] API endpoints respond correctly
- [ ] Frontend UI functions normally
- [ ] No console errors

---

## Rollback Plan

Each phase is independent, so rollback is simple:
1. Keep git commits separate per phase
2. If issues occur, revert the specific commit
3. All changes are backwards compatible

---

## Next Steps

1. Review this plan
2. Create feature branch: `git checkout -b efficiency-improvements`
3. Implement phases 1-8 in order
4. Test after each phase
5. Commit with clear messages
6. Merge to main when all tests pass

---

**Total Implementation Time**: 4-6 hours
**Risk Level**: Low (all changes are additive or cosmetic)
**Testing Time**: 1-2 hours
**Total Time**: 6-8 hours for complete implementation
