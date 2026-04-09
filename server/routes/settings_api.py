"""Settings API route handlers — GET/PUT for configurable tracking task templates and categories.

Config files are cached in memory after first read and invalidated on write.
This eliminates repeated disk I/O on hot paths (opportunity updates, task kanban loads).
"""

import json
from pathlib import Path
from server.utils.error_handler import error_handler

_TEMPLATES_PATH  = Path(__file__).parent.parent.parent / 'config' / 'tracking_task_templates.json'
_CATEGORIES_PATH = Path(__file__).parent.parent.parent / 'config' / 'categories.json'

# In-memory caches — None means "not yet loaded from disk"
# Thread safety: Python's GIL makes simple assignment atomic; worst case is two threads
# both read from disk on first access, which is safe (idempotent and rare).
_templates_cache:  dict | None = None
_categories_cache: dict | None = None

_DEFAULT_CATEGORIES = {
    "task_statuses": [
        {"slug": "not_started", "label": "Not Started", "headerClass": "bg-gray-400",   "colorClass": "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300",              "order": 1},
        {"slug": "in_progress", "label": "In Progress", "headerClass": "bg-blue-500",   "colorClass": "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300",            "order": 2},
        {"slug": "pending",     "label": "Pending",     "headerClass": "bg-yellow-500", "colorClass": "bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300",    "order": 3},
        {"slug": "completed",   "label": "Completed",   "headerClass": "bg-green-500",  "colorClass": "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300",        "order": 4},
    ],
    "workflow_stages": [
        {"slug": "01-qual",     "label": "01-Qualification",      "headerClass": "bg-blue-500",    "order": 1},
        {"slug": "02-lead",     "label": "02-Long Lead",          "headerClass": "bg-indigo-500",  "order": 2},
        {"slug": "03-bid",      "label": "03-Bid Decision",       "headerClass": "bg-purple-500",  "order": 3},
        {"slug": "04-progress", "label": "04-In Progress",        "headerClass": "bg-yellow-500",  "order": 4},
        {"slug": "05-review",   "label": "05-Waiting/Review",     "headerClass": "bg-orange-500",  "order": 5},
        {"slug": "06-nego",     "label": "06-In Negotiation",     "headerClass": "bg-amber-500",   "order": 6},
        {"slug": "07-won",      "label": "07-Closed Won",         "headerClass": "bg-green-600",   "order": 7},
        {"slug": "08-lost",     "label": "08-Closed Lost",        "headerClass": "bg-red-500",     "order": 8},
        {"slug": "09-nobid",    "label": "09-Closed No Bid",      "headerClass": "bg-gray-500",    "order": 9},
        {"slug": "20-other",    "label": "20-Closed Other",       "headerClass": "bg-slate-500",   "order": 10},
        {"slug": "98-vehicle",  "label": "98-Awarded Contract",   "headerClass": "bg-emerald-600", "order": 11},
        {"slug": "99-complete", "label": "99-Completed Contract", "headerClass": "bg-teal-600",    "order": 12},
    ],
}

_DEFAULT_TEMPLATES = {
    "templates": [
        {
            "trigger": "proposal",
            "enabled": True,
            "task_name": "Schedule Proposal Kickoff",
            "task_description": "Schedule and conduct a Proposal Kickoff meeting to align the team on capture strategy, roles, timeline, and win themes.",
        },
        {
            "trigger": "bnb",
            "enabled": True,
            "task_name": "Schedule Bid No-Bid Meeting",
            "task_description": "Schedule and conduct the Bid No-Bid decision meeting to evaluate opportunity fit, available resources, and competitive position.",
        },
        {
            "trigger": "hotwash",
            "enabled": True,
            "task_name": "Schedule Hotwash Meeting",
            "task_description": "Schedule and conduct a Hotwash post-action review to capture lessons learned, outcomes, and action items for future pursuits.",
        },
    ]
}


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def _load_templates() -> dict:
    """
    Return task templates config, reading from disk only on first call.

    Returns:
        dict: Template config with 'templates' list.
    """
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache
    loaded: dict | None = None
    try:
        if _TEMPLATES_PATH.exists():
            loaded = json.loads(_TEMPLATES_PATH.read_text())
    except Exception:
        pass
    _templates_cache = loaded if loaded is not None else _DEFAULT_TEMPLATES
    return _templates_cache


def _save_templates(data: dict) -> None:
    """
    Persist task templates to disk and update the in-memory cache.

    Args:
        data (dict): Template config with 'templates' list.
    """
    global _templates_cache
    _TEMPLATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TEMPLATES_PATH.write_text(json.dumps(data, indent=2))
    _templates_cache = data


def get_task_templates() -> list[dict]:
    """
    Return the cached template list for use by other modules.

    Returns:
        list[dict]: Enabled and disabled templates from config.
    """
    return _load_templates().get('templates', [])


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def _load_categories() -> dict:
    """
    Return categories config, reading from disk only on first call.

    Returns:
        dict: Categories config with 'task_statuses' and 'workflow_stages' lists.
    """
    global _categories_cache
    if _categories_cache is not None:
        return _categories_cache
    loaded: dict | None = None
    try:
        if _CATEGORIES_PATH.exists():
            loaded = json.loads(_CATEGORIES_PATH.read_text())
    except Exception:
        pass
    _categories_cache = loaded if loaded is not None else _DEFAULT_CATEGORIES
    return _categories_cache


def _save_categories(data: dict) -> None:
    """
    Persist categories config to disk and update the in-memory cache.

    Args:
        data (dict): Categories config with 'task_statuses' and 'workflow_stages' lists.
    """
    global _categories_cache
    _CATEGORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CATEGORIES_PATH.write_text(json.dumps(data, indent=2))
    _categories_cache = data


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@error_handler
def handle_categories_get(handler):
    """
    GET /api/settings/categories — return current categories config.

    Args:
        handler: HTTP request handler instance.
    """
    handler.send_json_response(_load_categories())


@error_handler
def handle_categories_put(handler):
    """
    PUT /api/settings/categories — update categories config.

    Args:
        handler: HTTP request handler instance.
    """
    data = handler.get_request_body()
    if data is None or ('task_statuses' not in data and 'workflow_stages' not in data):
        handler.send_json_response({'error': 'Missing task_statuses or workflow_stages field'}, 400)
        return
    _save_categories(data)
    handler.send_json_response({'status': 'success', **data})


@error_handler
def handle_tracking_tasks_settings_get(handler):
    """
    GET /api/settings/tracking-tasks — return current task templates.

    Args:
        handler: HTTP request handler instance.
    """
    handler.send_json_response(_load_templates())


@error_handler
def handle_tracking_tasks_settings_put(handler):
    """
    PUT /api/settings/tracking-tasks — update task templates.

    Args:
        handler: HTTP request handler instance.
    """
    data = handler.get_request_body()
    if data is None or 'templates' not in data:
        handler.send_json_response({'error': 'Missing templates field'}, 400)
        return
    _save_templates(data)
    handler.send_json_response({'status': 'success', 'templates': data['templates']})
