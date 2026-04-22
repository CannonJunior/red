"""
opportunities_handlers.py — Module-level singleton and request-handler functions.

These thin wrappers delegate to OpportunitiesManager and are the public API
consumed by server/routes/opportunities.py.
"""

from typing import Dict, Optional

from opportunities_api import OpportunitiesManager
from config.database import DEFAULT_DB

_opportunities_manager: Optional[OpportunitiesManager] = None


def get_opportunities_manager() -> OpportunitiesManager:
    """
    Get or create the global OpportunitiesManager singleton.

    Returns:
        Shared OpportunitiesManager instance.
    """
    global _opportunities_manager
    if _opportunities_manager is None:
        _opportunities_manager = OpportunitiesManager()
    return _opportunities_manager


# -------------------------------------------------------------------------
# Opportunity handlers
# -------------------------------------------------------------------------

def handle_opportunities_list_request(filters: Dict = None) -> Dict:
    """Handle list opportunities request."""
    manager = get_opportunities_manager()
    status = filters.get('status') if filters else None
    limit = int(filters.get('limit', 100)) if filters else 100
    offset = int(filters.get('offset', 0)) if filters else 0
    return manager.list_opportunities(status=status, limit=limit, offset=offset)


def handle_opportunities_create_request(data: Dict) -> Dict:
    """Handle create opportunity request."""
    manager = get_opportunities_manager()
    return manager.create_opportunity(
        name=data.get('name', 'Untitled Opportunity'),
        description=data.get('description', ''),
        status=data.get('status', 'open'),
        priority=data.get('priority', 'medium'),
        value=data.get('value', 0.0),
        tags=data.get('tags', []),
        metadata=data.get('metadata', {}),
        pipeline_stage=data.get('pipeline_stage', 'identified'),
        probability=data.get('probability', ''),
        proposal_due_date=data.get('proposal_due_date', ''),
        opp_number=data.get('opp_number', ''),
        is_iwa=data.get('is_iwa', ''),
        owning_org=data.get('owning_org', ''),
        proposal_folder=data.get('proposal_folder', ''),
        agency=data.get('agency', ''),
        solicitation_link=data.get('solicitation_link', ''),
        deal_type=data.get('deal_type', ''),
    )


def handle_opportunities_get_request(opportunity_id: str) -> Dict:
    """Handle get opportunity request."""
    return get_opportunities_manager().get_opportunity(opportunity_id)


def handle_opportunities_update_request(opportunity_id: str, data: Dict) -> Dict:
    """Handle update opportunity request."""
    return get_opportunities_manager().update_opportunity(opportunity_id, **data)


def handle_opportunities_delete_request(opportunity_id: str) -> Dict:
    """Handle delete opportunity request."""
    return get_opportunities_manager().delete_opportunity(opportunity_id)


# -------------------------------------------------------------------------
# Task handlers
# -------------------------------------------------------------------------

def handle_tasks_list_request(opportunity_id: str) -> Dict:
    """Handle list tasks request."""
    return get_opportunities_manager().list_tasks(opportunity_id)


def handle_tasks_create_request(opportunity_id: str, data: Dict) -> Dict:
    """Handle create task request."""
    manager = get_opportunities_manager()
    return manager.create_task(
        opportunity_id=opportunity_id,
        name=data.get('name', 'Untitled Task'),
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        description=data.get('description', ''),
        status=data.get('status', 'pending'),
        progress=data.get('progress', 0),
        assigned_to=data.get('assigned_to', ''),
    )


def handle_tasks_update_request(task_id: str, data: Dict) -> Dict:
    """Handle update task request."""
    return get_opportunities_manager().update_task(task_id, **data)


def handle_task_get_request(task_id: str) -> Dict:
    """Handle get task request."""
    return get_opportunities_manager().get_task(task_id)


def handle_tasks_delete_request(task_id: str) -> Dict:
    """Handle delete task request."""
    return get_opportunities_manager().delete_task(task_id)


def handle_task_history_request(task_id: str) -> Dict:
    """Handle get task history request."""
    return get_opportunities_manager().get_task_history(task_id)


def handle_pipeline_stats_request() -> Dict:
    """
    Compute pipeline health statistics from the opportunities table.

    Returns:
        Dict with keys: total, by_stage, by_priority, win_rate,
        total_value, active_value, won_value.
    """
    return get_opportunities_manager().get_pipeline_stats()
