"""Configuration for TODO list feature."""

import os
from pathlib import Path

# Database configuration
TODOS_DB_PATH = os.getenv('TODOS_DB_PATH', 'todos.db')

# Feature flags
ENABLE_NLP = os.getenv('TODOS_ENABLE_NLP', 'true').lower() == 'true'
ENABLE_OLLAMA_NLP = os.getenv('TODOS_ENABLE_OLLAMA', 'false').lower() == 'true'

# Limits (for 5-user scale)
MAX_USERS = int(os.getenv('TODOS_MAX_USERS', '5'))
MAX_LISTS_PER_USER = int(os.getenv('TODOS_MAX_LISTS', '50'))
MAX_TODOS_PER_LIST = int(os.getenv('TODOS_MAX_TODOS', '1000'))

# NLP configuration
NLP_DATE_LOOKAHEAD_DAYS = int(os.getenv('TODOS_NLP_LOOKAHEAD', '90'))

# Default values
DEFAULT_BUCKET = 'inbox'
DEFAULT_PRIORITY = 'medium'
DEFAULT_STATUS = 'pending'

# Valid status values
VALID_STATUSES = ['pending', 'in_progress', 'completed', 'archived']

# Valid priority values
VALID_PRIORITIES = ['low', 'medium', 'high', 'urgent']

# Valid bucket values
VALID_BUCKETS = ['inbox', 'today', 'upcoming', 'someday']

# Color palette for lists
LIST_COLORS = [
    '#EF4444',  # Red
    '#F59E0B',  # Amber
    '#10B981',  # Green
    '#3B82F6',  # Blue
    '#8B5CF6',  # Purple
    '#EC4899',  # Pink
    '#14B8A6',  # Teal
    '#F97316',  # Orange
]

# Default icons for lists
LIST_ICONS = [
    'list',
    'briefcase',
    'home',
    'shopping-cart',
    'heart',
    'star',
    'flag',
    'calendar',
]
