# Performance Optimization Patterns

This reference provides patterns for identifying and fixing performance issues in Python code.

## Table of Contents

1. [Profiling Code](#profiling-code)
2. [Algorithm Optimization](#algorithm-optimization)
3. [Data Structure Selection](#data-structure-selection)
4. [Database Query Optimization](#database-query-optimization)
5. [Memory Management](#memory-management)
6. [Concurrency](#concurrency)

## Profiling Code

### Using cProfile

```python
import cProfile
import pstats
from pstats import SortKey

def profile_function(func, *args, **kwargs):
    """Profile a function and print stats."""
    profiler = cProfile.Profile()
    profiler.enable()

    result = func(*args, **kwargs)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.TIME)
    stats.print_stats(20)  # Top 20 functions

    return result

# Usage
result = profile_function(my_slow_function, arg1, arg2)
```

### Using line_profiler

```bash
# Install
pip install line_profiler

# Add @profile decorator to functions
# Run with:
kernprof -l -v script.py
```

```python
# In code:
@profile  # Added by line_profiler
def slow_function():
    # Line-by-line timing
    data = []
    for i in range(1000000):
        data.append(i ** 2)
    return data
```

## Algorithm Optimization

### Inefficient Loop Patterns

❌ **Bad: Growing list in loop**
```python
def process_data(items):
    result = []
    for item in items:
        result.append(expensive_operation(item))
    return result
```

✅ **Good: List comprehension**
```python
def process_data(items):
    return [expensive_operation(item) for item in items]
```

✅ **Better: Generator for large datasets**
```python
def process_data(items):
    """Process items lazily (memory efficient)."""
    return (expensive_operation(item) for item in items)
```

### Nested Loop Optimization

❌ **Bad: O(n²) lookup**
```python
def find_matches(list1, list2):
    matches = []
    for item1 in list1:
        for item2 in list2:
            if item1 == item2:
                matches.append(item1)
    return matches
```

✅ **Good: O(n) with set**
```python
def find_matches(list1, list2):
    """Find matches efficiently using set intersection."""
    return list(set(list1) & set(list2))
```

## Data Structure Selection

### Dictionary vs List for Lookups

❌ **Bad: O(n) list lookup**
```python
users = [('alice', 25), ('bob', 30), ('charlie', 35)]

def get_age(name):
    for user_name, age in users:
        if user_name == name:
            return age
    return None
```

✅ **Good: O(1) dict lookup**
```python
users = {'alice': 25, 'bob': 30, 'charlie': 35}

def get_age(name):
    return users.get(name)
```

### Set for Membership Testing

❌ **Bad: O(n) list membership**
```python
seen = []
for item in items:
    if item not in seen:  # Slow for large lists
        process(item)
        seen.append(item)
```

✅ **Good: O(1) set membership**
```python
seen = set()
for item in items:
    if item not in seen:  # Fast O(1) lookup
        process(item)
        seen.add(item)
```

### deque for Queue Operations

❌ **Bad: List as queue (O(n) pop from front)**
```python
queue = []
queue.append(item)  # O(1)
first = queue.pop(0)  # O(n) - slow!
```

✅ **Good: deque for queue (O(1) both ends)**
```python
from collections import deque

queue = deque()
queue.append(item)  # O(1)
first = queue.popleft()  # O(1) - fast!
```

## Database Query Optimization

### N+1 Query Problem

❌ **Bad: N+1 queries**
```python
# SQLAlchemy example
users = session.query(User).all()  # 1 query

# N additional queries!
for user in users:
    posts = user.posts  # Separate query for each user
    print(f"{user.name}: {len(posts)} posts")
```

✅ **Good: Eager loading**
```python
from sqlalchemy.orm import selectinload

# Single query with JOIN
users = session.query(User).options(
    selectinload(User.posts)
).all()

for user in users:
    posts = user.posts  # No additional query
    print(f"{user.name}: {len(posts)} posts")
```

### Batch Operations

❌ **Bad: Individual inserts**
```python
for item in items:
    db.execute("INSERT INTO table VALUES (?)", (item,))
    db.commit()  # Commit each time - slow!
```

✅ **Good: Batch insert**
```python
# Batch insert
db.executemany(
    "INSERT INTO table VALUES (?)",
    [(item,) for item in items]
)
db.commit()  # Single commit
```

### Query Indexing

```sql
-- Add indexes for commonly queried columns
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_at ON posts(created_at);

-- Composite index for multi-column queries
CREATE INDEX idx_posts_user_created ON posts(user_id, created_at);
```

```python
# Verify index usage with EXPLAIN
def check_query_performance(query):
    """Check if query uses indexes."""
    explain = db.execute(f"EXPLAIN QUERY PLAN {query}")
    print(explain.fetchall())
```

## Memory Management

### Generator Expressions

❌ **Bad: Load entire dataset into memory**
```python
def process_large_file(filename):
    # Loads entire file into memory
    lines = open(filename).readlines()
    return [process_line(line) for line in lines]
```

✅ **Good: Process line-by-line**
```python
def process_large_file(filename):
    """Process file line-by-line (memory efficient)."""
    with open(filename, 'r') as f:
        for line in f:  # Reads one line at a time
            yield process_line(line)
```

### Avoid Unnecessary Copies

❌ **Bad: Multiple list copies**
```python
def filter_and_sort(data):
    filtered = [x for x in data if x > 0]  # Copy 1
    sorted_data = sorted(filtered)  # Copy 2
    return sorted_data[:10]  # Copy 3
```

✅ **Good: Chain operations efficiently**
```python
import heapq

def filter_and_sort(data):
    """Get top 10 positive values efficiently."""
    # Generator (no copy) + heap (no full sort)
    positive = (x for x in data if x > 0)
    return heapq.nlargest(10, positive)
```

## Concurrency

### Threading for I/O-Bound Tasks

```python
from concurrent.futures import ThreadPoolExecutor
from typing import List
import requests

def fetch_url(url: str) -> str:
    """Fetch single URL."""
    response = requests.get(url)
    return response.text

def fetch_urls_parallel(urls: List[str]) -> List[str]:
    """Fetch multiple URLs in parallel."""
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_url, urls))
    return results
```

### Multiprocessing for CPU-Bound Tasks

```python
from concurrent.futures import ProcessPoolExecutor
from typing import List

def cpu_intensive_task(data):
    """CPU-intensive operation."""
    return sum(i ** 2 for i in range(data))

def process_parallel(data_list: List[int]) -> List[int]:
    """Process data using multiple CPU cores."""
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(cpu_intensive_task, data_list))
    return results
```

### Async for I/O-Bound Tasks (Modern Approach)

```python
import asyncio
import aiohttp
from typing import List

async def fetch_url_async(session, url: str) -> str:
    """Fetch URL asynchronously."""
    async with session.get(url) as response:
        return await response.text()

async def fetch_urls_async(urls: List[str]) -> List[str]:
    """Fetch multiple URLs asynchronously."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url_async(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
    return results

# Usage
urls = ['http://example.com', 'http://example.org']
results = asyncio.run(fetch_urls_async(urls))
```

## Performance Checklist

- [ ] Profile code to identify bottlenecks
- [ ] Use appropriate data structures (set for lookups, deque for queues)
- [ ] Avoid nested loops where possible (use sets, dicts)
- [ ] Use generators for large datasets
- [ ] Batch database operations
- [ ] Add database indexes for common queries
- [ ] Use eager loading to prevent N+1 queries
- [ ] Use threading/async for I/O-bound tasks
- [ ] Use multiprocessing for CPU-bound tasks
- [ ] Avoid unnecessary data copies
- [ ] Cache expensive computations
- [ ] Use built-in functions (they're optimized in C)

## Profiling Quick Reference

| Tool | Purpose | Usage |
|------|---------|-------|
| cProfile | Function-level profiling | `python -m cProfile script.py` |
| line_profiler | Line-by-line profiling | `kernprof -l -v script.py` |
| memory_profiler | Memory usage tracking | `python -m memory_profiler script.py` |
| py-spy | Sampling profiler (no code changes) | `py-spy top -- python script.py` |
| timeit | Micro-benchmarking | `python -m timeit "code here"` |
