"""Settings API route handlers — GET/PUT for configurable tracking task templates."""

import json
from pathlib import Path
from server.utils.error_handler import error_handler

_TEMPLATES_PATH = Path(__file__).parent.parent.parent / 'config' / 'tracking_task_templates.json'

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


def _load_templates() -> dict:
    """
    Load task templates from config file, falling back to defaults.

    Returns:
        dict: Template config with 'templates' list.
    """
    try:
        if _TEMPLATES_PATH.exists():
            return json.loads(_TEMPLATES_PATH.read_text())
    except Exception:
        pass
    return _DEFAULT_TEMPLATES


def _save_templates(data: dict) -> None:
    """
    Persist task templates to config file.

    Args:
        data (dict): Template config with 'templates' list.
    """
    _TEMPLATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TEMPLATES_PATH.write_text(json.dumps(data, indent=2))


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
