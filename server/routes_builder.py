"""
server/routes_builder.py — Application route registry.

Builds and returns a Router with all API routes mapped to callable
handler functions. Feature-gated routes are only registered when the
corresponding module imports successfully.

Usage:
    from server.routes_builder import build_router
    router = build_router()
"""


from server.router import Router
from server.routes.models import handle_models_api as handle_models_route
from server.routes.chat import handle_chat_api as handle_chat_route
from server.routes.rag import (
    handle_rag_status_api as handle_rag_status_route,
    handle_rag_search_api as handle_rag_search_route,
    handle_rag_query_api as handle_rag_query_route,
    handle_rag_ingest_api as handle_rag_ingest_route,
    handle_rag_documents_api as handle_rag_documents_route,
    handle_rag_analytics_api as handle_rag_analytics_route,
    handle_rag_upload_api as handle_rag_upload_route,
    handle_rag_document_delete_api as handle_rag_document_delete_route,
)
from server.routes.cag import (
    handle_cag_status_api as handle_cag_status_route,
    handle_cag_load_api as handle_cag_load_route,
    handle_cag_clear_api as handle_cag_clear_route,
    handle_cag_document_delete_api as handle_cag_document_delete_route,
    handle_cag_query_api as handle_cag_query_route,
)
from server.routes.prompts import (
    handle_prompts_list_api as handle_prompts_list_route,
    handle_prompts_create_api as handle_prompts_create_route,
    handle_prompts_detail_api as handle_prompts_detail_route,
    handle_prompts_update_api as handle_prompts_update_route,
    handle_prompts_delete_api as handle_prompts_delete_route,
    handle_prompts_use_api as handle_prompts_use_route,
    handle_prompts_search_api as handle_prompts_search_route,
)
from server.routes.search import (
    handle_search_api as handle_search_route,
    handle_search_folders_api as handle_search_folders_route,
    handle_search_create_folder_api as handle_search_create_folder_route,
    handle_search_tags_api as handle_search_tags_route,
    handle_search_add_object_api as handle_search_add_object_route,
)
from server.routes.agents import (
    handle_agents_api as handle_agents_route,
    handle_agents_metrics_api as handle_agents_metrics_route,
    handle_agents_detail_api as handle_agents_detail_route,
)
from server.routes.shredding import (
    handle_shredding_shred_api as handle_shredding_shred_route,
    handle_shredding_status_api as handle_shredding_status_route,
    handle_shredding_requirements_api as handle_shredding_requirements_route,
    handle_shredding_requirement_update_api as handle_shredding_req_update_route,
    handle_shredding_matrix_api as handle_shredding_matrix_route,
)
from server.routes.career import (
    handle_career_positions_list_api as handle_career_positions_list_route,
    handle_career_positions_create_api as handle_career_positions_create_route,
    handle_career_candidates_create_api as handle_career_candidates_create_route,
    handle_career_analyze_api as handle_career_analyze_route,
    handle_career_assessment_get_api as handle_career_assessment_get_route,
    handle_career_stats_api as handle_career_stats_route,
    handle_career_list_get_api as handle_career_list_get_route,
    handle_career_list_add_api as handle_career_list_add_route,
    handle_career_list_remove_api as handle_career_list_remove_route,
)
from server.routes.mcp import (
    handle_mcp_servers_api as handle_mcp_servers_route,
    handle_mcp_server_action_api as handle_mcp_server_action_route,
    handle_nlp_parse_task_api as handle_nlp_parse_task_route,
    handle_nlp_capabilities_api as handle_nlp_capabilities_route,
    handle_mcp_metrics_api as handle_mcp_metrics_route,
)
from server.routes.visualizations import (
    handle_knowledge_graph_api as handle_knowledge_graph_route,
    handle_performance_dashboard_api as handle_performance_dashboard_route,
    handle_search_results_api as handle_search_results_route,
)
from server.routes.opportunities import (
    handle_opportunities_list_api as handle_opportunities_list_route,
    handle_opportunities_create_api as handle_opportunities_create_route,
    handle_opportunities_detail_api as handle_opportunities_detail_route,
    handle_opportunities_update_api as handle_opportunities_update_route,
    handle_opportunities_delete_api as handle_opportunities_delete_route,
    handle_tasks_list_api as handle_tasks_list_route,
    handle_tasks_create_api as handle_tasks_create_route,
    handle_task_get_api as handle_task_get_route,
    handle_task_update_api as handle_task_update_route,
    handle_task_delete_api as handle_task_delete_route,
    handle_task_history_api as handle_task_history_route,
    handle_opportunities_delete_all_api as handle_opportunities_delete_all_route,
    handle_opportunities_import_parse_api as handle_opportunities_import_parse_route,
    handle_opportunities_import_confirm_api as handle_opportunities_import_confirm_route,
    handle_opportunities_export_api as handle_opportunities_export_route,
    handle_pipeline_stats_api as handle_pipeline_stats_route,
)
from server.routes.source_tree import handle_source_tree_api as handle_source_tree_route
from server.routes.settings_api import (
    handle_tracking_tasks_settings_get as handle_tracking_tasks_get_route,
    handle_tracking_tasks_settings_put as handle_tracking_tasks_put_route,
)

# Optional feature imports — availability flags set below
OLLAMA_AGENTS_AVAILABLE = False
try:
    from server.routes.ollama_agents import (
        handle_ollama_agents_api as handle_ollama_agents_route,
        handle_ollama_agent_detail_api as handle_ollama_agent_detail_route,
        handle_ollama_agent_invoke_api as handle_ollama_agent_invoke_route,
        handle_ollama_skills_api as handle_ollama_skills_route,
        handle_ollama_status_api as handle_ollama_status_route,
    )
    OLLAMA_AGENTS_AVAILABLE = True
except ImportError:
    pass

RAG_AVAILABLE = False
try:
    import rag_api  # noqa: F401
    RAG_AVAILABLE = True
except ImportError:
    pass

CAG_AVAILABLE = False
try:
    from cag_api import get_cag_manager  # noqa: F401
    CAG_AVAILABLE = True
except ImportError:
    pass

AGENT_SYSTEM_AVAILABLE = False
try:
    from agent_system.mcp.server_manager import ZeroCostMCPServerManager  # noqa: F401
    AGENT_SYSTEM_AVAILABLE = True
except ImportError:
    pass

SEARCH_AVAILABLE = False
try:
    from search_api import handle_search_request  # noqa: F401
    SEARCH_AVAILABLE = True
except ImportError:
    pass

PROMPTS_AVAILABLE = False
try:
    from prompts_api import handle_prompts_list_request  # noqa: F401
    PROMPTS_AVAILABLE = True
except ImportError:
    pass

CAPTURE_AVAILABLE = False
try:
    from server.routes.capture import (
        handle_contacts_list_api as handle_contacts_list_route,
        handle_contacts_create_api as handle_contacts_create_route,
        handle_contact_update_api as handle_contact_update_route,
        handle_contact_delete_api as handle_contact_delete_route,
        handle_competitors_list_api as handle_competitors_list_route,
        handle_competitors_create_api as handle_competitors_create_route,
        handle_competitor_update_api as handle_competitor_update_route,
        handle_competitor_delete_api as handle_competitor_delete_route,
        handle_activities_list_api as handle_activities_list_route,
        handle_activities_create_api as handle_activities_create_route,
        handle_activity_delete_api as handle_activity_delete_route,
        handle_win_strategy_get_api as handle_win_strategy_get_route,
        handle_win_strategy_put_api as handle_win_strategy_put_route,
        handle_ptw_get_api as handle_ptw_get_route,
        handle_ptw_put_api as handle_ptw_put_route,
    )
    CAPTURE_AVAILABLE = True
    print("✅ Capture system loaded successfully")
except ImportError as e:
    print(f"⚠️  Capture system not available: {e}")

PROPOSALS_AVAILABLE = False
try:
    from server.routes.proposals import (
        handle_proposals_list_api as handle_proposals_list_route,
        handle_proposals_create_api as handle_proposals_create_route,
        handle_proposals_detail_api as handle_proposals_detail_route,
        handle_proposals_update_api as handle_proposals_update_route,
        handle_proposals_delete_api as handle_proposals_delete_route,
        handle_proposals_advance_api as handle_proposals_advance_route,
        handle_proposals_schedule_api as handle_proposals_schedule_route,
        handle_proposals_folders_api as handle_proposals_folders_route,
        handle_proposals_bid_no_bid_get_api as handle_proposals_bnb_get_route,
        handle_proposals_bid_no_bid_post_api as handle_proposals_bnb_post_route,
    )
    PROPOSALS_AVAILABLE = True
except ImportError:
    pass

TRACKING_AVAILABLE = False
try:
    from server.routes.tracking import (
        handle_proposal_items_list_api as handle_proposal_items_list_route,
        handle_proposal_items_create_api as handle_proposal_items_create_route,
        handle_proposal_item_update_api as handle_proposal_item_update_route,
        handle_proposal_item_delete_api as handle_proposal_item_delete_route,
        handle_bnb_items_list_api as handle_bnb_items_list_route,
        handle_bnb_items_create_api as handle_bnb_items_create_route,
        handle_bnb_item_update_api as handle_bnb_item_update_route,
        handle_bnb_item_delete_api as handle_bnb_item_delete_route,
        handle_hotwash_items_list_api as handle_hotwash_items_list_route,
        handle_hotwash_items_create_api as handle_hotwash_items_create_route,
        handle_hotwash_item_update_api as handle_hotwash_item_update_route,
        handle_hotwash_item_delete_api as handle_hotwash_item_delete_route,
        handle_all_tasks_list_api as handle_all_tasks_list_route,
    )
    TRACKING_AVAILABLE = True
    print("✅ Tracking lists loaded successfully")
except ImportError as e:
    print(f"⚠️  Tracking lists not available: {e}")

TODOS_AVAILABLE = False
try:
    from server.routes.todos import (
        handle_users_list_api as handle_users_list_route,
        handle_users_create_api as handle_users_create_route,
        handle_users_detail_api as handle_users_detail_route,
        handle_users_update_api as handle_users_update_route,
        handle_users_delete_api as handle_users_delete_route,
        handle_lists_list_api as handle_lists_list_route,
        handle_lists_create_api as handle_lists_create_route,
        handle_lists_detail_api as handle_lists_detail_route,
        handle_lists_update_api as handle_lists_update_route,
        handle_lists_delete_api as handle_lists_delete_route,
        handle_lists_share_api as handle_lists_share_route,
        handle_lists_unshare_api as handle_lists_unshare_route,
        handle_lists_shares_api as handle_lists_shares_route,
        handle_shared_lists_api as handle_shared_lists_route,
        handle_todos_list_api as handle_todos_list_route,
        handle_todos_create_api as handle_todos_create_route,
        handle_todos_detail_api as handle_todos_detail_route,
        handle_todos_update_api as handle_todos_update_route,
        handle_todos_delete_api as handle_todos_delete_route,
        handle_todos_complete_api as handle_todos_complete_route,
        handle_todos_archive_api as handle_todos_archive_route,
        handle_todos_today_api as handle_todos_today_route,
        handle_todos_upcoming_api as handle_todos_upcoming_route,
        handle_todos_search_api as handle_todos_search_route,
        handle_todos_parse_api as handle_todos_parse_route,
        handle_tags_list_api as handle_tags_list_route,
        handle_tags_create_api as handle_tags_create_route,
        handle_tags_detail_api as handle_tags_detail_route,
        handle_tags_update_api as handle_tags_update_route,
        handle_tags_delete_api as handle_tags_delete_route,
        handle_todos_history_api as handle_todos_history_route,
    )
    TODOS_AVAILABLE = True
    print("✅ TODO system loaded successfully")
except ImportError as e:
    print(f"⚠️  TODO system not available: {e}")


def _qp(path: str) -> dict:
    """Parse query string from a URL path."""
    from urllib.parse import parse_qs
    if '?' not in path:
        return {}
    return parse_qs(path.split('?', 1)[1])


def _last(path: str) -> str:
    """Extract the last path segment, stripping query string."""
    return path.split('?')[0].split('/')[-1]


def _second_last(path: str) -> str:
    """Extract the second-to-last path segment, stripping query string."""
    return path.split('?')[0].split('/')[-2]


def build_router() -> Router:
    """Build and return the application router with all registered routes."""
    r = Router()

    # ---- GET ----------------------------------------------------------------
    r.add('GET', lambda p: p == '/api/rag/documents' and RAG_AVAILABLE,       handle_rag_documents_route)
    r.add('GET', lambda p: p == '/api/rag/analytics' and RAG_AVAILABLE,       handle_rag_analytics_route)
    r.add('GET', lambda p: p == '/api/search/folders' and SEARCH_AVAILABLE,   handle_search_folders_route)
    r.add('GET', lambda p: p == '/api/search/tags' and SEARCH_AVAILABLE,      handle_search_tags_route)
    r.add('GET', lambda p: p == '/api/visualizations/knowledge-graph',        handle_knowledge_graph_route)
    r.add('GET', lambda p: p == '/api/visualizations/performance',            handle_performance_dashboard_route)
    r.add('GET', lambda p: p == '/api/visualizations/search-results',         handle_search_results_route)
    r.add('GET', lambda p: p == '/api/agents' and AGENT_SYSTEM_AVAILABLE,                    handle_agents_route)
    r.add('GET', lambda p: p == '/api/agents/metrics' and AGENT_SYSTEM_AVAILABLE,            handle_agents_metrics_route)
    r.add('GET', lambda p: p.startswith('/api/agents/') and AGENT_SYSTEM_AVAILABLE,          handle_agents_detail_route)
    r.add('GET', lambda p: p == '/api/ollama/status',                         handle_ollama_status_route if OLLAMA_AGENTS_AVAILABLE else handle_models_route)
    r.add('GET', lambda p: p == '/api/ollama/agents',                         handle_ollama_agents_route if OLLAMA_AGENTS_AVAILABLE else handle_models_route)
    r.add('GET', lambda p: p == '/api/ollama/skills',                         handle_ollama_skills_route if OLLAMA_AGENTS_AVAILABLE else handle_models_route)
    r.add('GET', lambda p: p.startswith('/api/ollama/agents/'),               handle_ollama_agent_detail_route if OLLAMA_AGENTS_AVAILABLE else handle_models_route)
    r.add('GET', lambda p: p == '/api/mcp/servers' and AGENT_SYSTEM_AVAILABLE,               handle_mcp_servers_route)
    r.add('GET', lambda p: p.startswith('/api/mcp/servers/') and AGENT_SYSTEM_AVAILABLE,     handle_mcp_server_action_route)
    r.add('GET', lambda p: p == '/api/mcp/metrics' and AGENT_SYSTEM_AVAILABLE,               handle_mcp_metrics_route)
    r.add('GET', lambda p: p == '/api/nlp/capabilities' and AGENT_SYSTEM_AVAILABLE,          handle_nlp_capabilities_route)
    r.add('GET', lambda p: p == '/api/prompts' and PROMPTS_AVAILABLE,                        handle_prompts_list_route)
    r.add('GET', lambda p: p.startswith('/api/prompts/') and PROMPTS_AVAILABLE,              handle_prompts_detail_route)
    r.add('GET', lambda p: p.startswith('/api/shredding/status/'),            lambda h: handle_shredding_status_route(h, h.path, _qp(h.path)))
    r.add('GET', lambda p: p.startswith('/api/shredding/requirements/'),      lambda h: handle_shredding_requirements_route(h, h.path, _qp(h.path)))
    r.add('GET', lambda p: p.startswith('/api/shredding/matrix/'),            lambda h: handle_shredding_matrix_route(h, h.path, _qp(h.path)))
    r.add('GET', lambda p: p == '/api/todos/users' and TODOS_AVAILABLE,                      handle_users_list_route)
    r.add('GET', lambda p: (p == '/api/todos/lists' or p.startswith('/api/todos/lists?')) and TODOS_AVAILABLE, handle_lists_list_route)
    r.add('GET', lambda p: p == '/api/todos/shared' and TODOS_AVAILABLE,                     handle_shared_lists_route)
    r.add('GET', lambda p: p == '/api/todos/today' and TODOS_AVAILABLE,                      handle_todos_today_route)
    r.add('GET', lambda p: p == '/api/todos/upcoming' and TODOS_AVAILABLE,                   handle_todos_upcoming_route)
    r.add('GET', lambda p: p == '/api/todos/search' and TODOS_AVAILABLE,                     handle_todos_search_route)
    r.add('GET', lambda p: p == '/api/todos/tags' and TODOS_AVAILABLE,                       handle_tags_list_route)
    r.add('GET', lambda p: (p == '/api/todos' or p.startswith('/api/todos?')) and TODOS_AVAILABLE, handle_todos_list_route)
    r.add('GET', lambda p: p.startswith('/api/todos/lists/') and p.endswith('/shares') and TODOS_AVAILABLE, lambda h: handle_lists_shares_route(h, _second_last(h.path)))
    r.add('GET', lambda p: p.startswith('/api/todos/users/') and TODOS_AVAILABLE,            lambda h: handle_users_detail_route(h, _last(h.path)))
    r.add('GET', lambda p: p.startswith('/api/todos/lists/') and TODOS_AVAILABLE,            lambda h: handle_lists_detail_route(h, _last(h.path)))
    r.add('GET', lambda p: p.startswith('/api/todos/tags/') and TODOS_AVAILABLE,             lambda h: handle_tags_detail_route(h, _last(h.path)))
    r.add('GET', lambda p: p.startswith('/api/todos/') and p.endswith('/history') and TODOS_AVAILABLE, lambda h: handle_todos_history_route(h, _second_last(h.path)))
    r.add('GET', lambda p: p.startswith('/api/todos/') and TODOS_AVAILABLE,                  lambda h: handle_todos_detail_route(h, _last(h.path)))
    r.add('GET', lambda p: p == '/api/career/list',                           handle_career_list_get_route)
    r.add('GET', lambda p: p == '/api/career/positions' or p.startswith('/api/career/positions?'), handle_career_positions_list_route)
    r.add('GET', lambda p: p == '/api/career/stats',                          handle_career_stats_route)
    r.add('GET', lambda p: p.startswith('/api/career/assessments/'),          lambda h: handle_career_assessment_get_route(h, _last(h.path)))
    r.add('GET', lambda p: p == '/api/pipeline/stats',                        handle_pipeline_stats_route)
    r.add('GET', lambda p: p.startswith('/api/opportunities/export'),         handle_opportunities_export_route)
    r.add('GET', lambda p: p == '/api/opportunities',                         handle_opportunities_list_route)
    r.add('GET', lambda p: p.startswith('/api/opportunities/') and '/tasks' in p, lambda h: handle_tasks_list_route(h, h.path.split('?')[0].split('/')[3]))
    r.add('GET', lambda p: p.startswith('/api/tasks/') and p.endswith('/history'), lambda h: handle_task_history_route(h, _second_last(h.path)))
    r.add('GET', lambda p: p.startswith('/api/tasks/'),                       lambda h: handle_task_get_route(h, _last(h.path)))
    r.add('GET', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/contacts'),     handle_contacts_list_route)
    r.add('GET', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/competitors'),  handle_competitors_list_route)
    r.add('GET', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/activities'),   handle_activities_list_route)
    r.add('GET', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/win-strategy'), handle_win_strategy_get_route)
    r.add('GET', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/ptw'),          handle_ptw_get_route)
    r.add('GET', lambda p: p.startswith('/api/opportunities/'),               handle_opportunities_detail_route)
    r.add('GET', lambda p: p == '/api/source-tree',                           handle_source_tree_route)
    r.add('GET', lambda p: p == '/api/proposals' and PROPOSALS_AVAILABLE,                    handle_proposals_list_route)
    r.add('GET', lambda p: p.startswith('/api/proposals/') and p.endswith('/schedule') and PROPOSALS_AVAILABLE, handle_proposals_schedule_route)
    r.add('GET', lambda p: p.startswith('/api/proposals/') and p.endswith('/bid-no-bid') and PROPOSALS_AVAILABLE, handle_proposals_bnb_get_route)
    r.add('GET', lambda p: p.startswith('/api/proposals/') and PROPOSALS_AVAILABLE,          handle_proposals_detail_route)
    r.add('GET', lambda p: p == '/api/proposal-items' and TRACKING_AVAILABLE,  handle_proposal_items_list_route)
    r.add('GET', lambda p: p == '/api/bnb-items' and TRACKING_AVAILABLE,       handle_bnb_items_list_route)
    r.add('GET', lambda p: p == '/api/hotwash-items' and TRACKING_AVAILABLE,   handle_hotwash_items_list_route)
    r.add('GET', lambda p: p == '/api/all-tasks' and TRACKING_AVAILABLE,       handle_all_tasks_list_route)
    r.add('GET', lambda p: p == '/api/settings/tracking-tasks',               handle_tracking_tasks_get_route)

    # ---- POST ---------------------------------------------------------------
    r.add('POST', lambda p: p == '/api/chat',                                 handle_chat_route)
    r.add('POST', lambda p: p == '/api/models',                               handle_models_route)
    r.add('POST', lambda p: p == '/api/rag/status' and RAG_AVAILABLE,         handle_rag_status_route)
    r.add('POST', lambda p: p == '/api/rag/search' and RAG_AVAILABLE,         handle_rag_search_route)
    r.add('POST', lambda p: p == '/api/rag/query' and RAG_AVAILABLE,          handle_rag_query_route)
    r.add('POST', lambda p: p == '/api/rag/ingest' and RAG_AVAILABLE,         handle_rag_ingest_route)
    r.add('POST', lambda p: p == '/api/rag/upload' and RAG_AVAILABLE,         handle_rag_upload_route)
    r.add('POST', lambda p: p == '/api/rag/documents' and RAG_AVAILABLE,      handle_rag_documents_route)
    r.add('POST', lambda p: p == '/api/cag/status' and CAG_AVAILABLE,         handle_cag_status_route)
    r.add('POST', lambda p: p == '/api/cag/load' and CAG_AVAILABLE,           handle_cag_load_route)
    r.add('POST', lambda p: p == '/api/cag/clear' and CAG_AVAILABLE,          handle_cag_clear_route)
    r.add('POST', lambda p: p == '/api/cag/query' and CAG_AVAILABLE,          handle_cag_query_route)
    r.add('POST', lambda p: p == '/api/agents' and AGENT_SYSTEM_AVAILABLE,                   handle_agents_route)
    r.add('POST', lambda p: p.startswith('/api/agents/') and AGENT_SYSTEM_AVAILABLE,         handle_agents_detail_route)
    r.add('POST', lambda p: p == '/api/ollama/agents',                        handle_ollama_agents_route if OLLAMA_AGENTS_AVAILABLE else handle_models_route)
    r.add('POST', lambda p: p.startswith('/api/ollama/agents/') and '/invoke' in p, handle_ollama_agent_invoke_route if OLLAMA_AGENTS_AVAILABLE else handle_models_route)
    r.add('POST', lambda p: p.startswith('/api/ollama/agents/'),              handle_ollama_agent_detail_route if OLLAMA_AGENTS_AVAILABLE else handle_models_route)
    r.add('POST', lambda p: p == '/api/mcp/servers' and AGENT_SYSTEM_AVAILABLE,              handle_mcp_servers_route)
    r.add('POST', lambda p: p.startswith('/api/mcp/servers/') and AGENT_SYSTEM_AVAILABLE,    handle_mcp_server_action_route)
    r.add('POST', lambda p: p == '/api/nlp/parse-task' and AGENT_SYSTEM_AVAILABLE,           handle_nlp_parse_task_route)
    r.add('POST', lambda p: p == '/api/search' and SEARCH_AVAILABLE,                         handle_search_route)
    r.add('POST', lambda p: p == '/api/search/folders' and SEARCH_AVAILABLE,                 handle_search_create_folder_route)
    r.add('POST', lambda p: p == '/api/search/objects' and SEARCH_AVAILABLE,                 handle_search_add_object_route)
    r.add('POST', lambda p: p == '/api/career/list',                          handle_career_list_add_route)
    r.add('POST', lambda p: p == '/api/career/positions',                     handle_career_positions_create_route)
    r.add('POST', lambda p: p == '/api/career/candidates',                    handle_career_candidates_create_route)
    r.add('POST', lambda p: p == '/api/career/analyze',                       handle_career_analyze_route)
    r.add('POST', lambda p: p == '/api/shredding/shred',                      lambda h: handle_shredding_shred_route(h, h.path, _qp(h.path)))
    r.add('POST', lambda p: p == '/api/prompts' and PROMPTS_AVAILABLE,                       handle_prompts_create_route)
    r.add('POST', lambda p: p == '/api/prompts/use' and PROMPTS_AVAILABLE,                   handle_prompts_use_route)
    r.add('POST', lambda p: p == '/api/prompts/search' and PROMPTS_AVAILABLE,                handle_prompts_search_route)
    r.add('POST', lambda p: p.startswith('/api/prompts/') and PROMPTS_AVAILABLE,             handle_prompts_update_route)
    r.add('POST', lambda p: p == '/api/todos/users' and TODOS_AVAILABLE,                     handle_users_create_route)
    r.add('POST', lambda p: p == '/api/todos/lists' and TODOS_AVAILABLE,                     handle_lists_create_route)
    r.add('POST', lambda p: p == '/api/todos/tags' and TODOS_AVAILABLE,                      handle_tags_create_route)
    r.add('POST', lambda p: p == '/api/todos/parse' and TODOS_AVAILABLE,                     handle_todos_parse_route)
    r.add('POST', lambda p: p == '/api/todos/search' and TODOS_AVAILABLE,                    handle_todos_search_route)
    r.add('POST', lambda p: p == '/api/todos' and TODOS_AVAILABLE,                           handle_todos_create_route)
    r.add('POST', lambda p: p.startswith('/api/todos/lists/') and p.endswith('/share') and TODOS_AVAILABLE, lambda h: handle_lists_share_route(h, _second_last(h.path)))
    r.add('POST', lambda p: p.startswith('/api/todos/') and p.endswith('/complete') and TODOS_AVAILABLE, lambda h: handle_todos_complete_route(h, _second_last(h.path)))
    r.add('POST', lambda p: p.startswith('/api/todos/') and p.endswith('/archive') and TODOS_AVAILABLE, lambda h: handle_todos_archive_route(h, _second_last(h.path)))
    r.add('POST', lambda p: p.startswith('/api/todos/') and TODOS_AVAILABLE,                 lambda h: handle_todos_update_route(h, _last(h.path)))
    r.add('POST', lambda p: p == '/api/opportunities/import/parse',           handle_opportunities_import_parse_route)
    r.add('POST', lambda p: p == '/api/opportunities/import/confirm',         handle_opportunities_import_confirm_route)
    r.add('POST', lambda p: p == '/api/opportunities',                        handle_opportunities_create_route)
    r.add('POST', lambda p: p.startswith('/api/opportunities/') and '/tasks' in p, lambda h: handle_tasks_create_route(h, h.path.split('?')[0].split('/')[3]))
    r.add('POST', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/contacts'),    handle_contacts_create_route)
    r.add('POST', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/competitors'), handle_competitors_create_route)
    r.add('POST', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/activities'),  handle_activities_create_route)
    r.add('POST', lambda p: p.startswith('/api/tasks/'),                      lambda h: handle_task_update_route(h, _last(h.path)))
    r.add('POST', lambda p: p.startswith('/api/opportunities/'),              handle_opportunities_update_route)
    r.add('POST', lambda p: p == '/api/proposal-items' and TRACKING_AVAILABLE,  handle_proposal_items_create_route)
    r.add('POST', lambda p: p == '/api/bnb-items' and TRACKING_AVAILABLE,       handle_bnb_items_create_route)
    r.add('POST', lambda p: p == '/api/hotwash-items' and TRACKING_AVAILABLE,   handle_hotwash_items_create_route)
    r.add('POST', lambda p: p == '/api/proposals' and PROPOSALS_AVAILABLE,                   handle_proposals_create_route)
    r.add('POST', lambda p: p.startswith('/api/proposals/') and p.endswith('/advance') and PROPOSALS_AVAILABLE, handle_proposals_advance_route)
    r.add('POST', lambda p: p.startswith('/api/proposals/') and p.endswith('/folders') and PROPOSALS_AVAILABLE, handle_proposals_folders_route)
    r.add('POST', lambda p: p.startswith('/api/proposals/') and p.endswith('/bid-no-bid') and PROPOSALS_AVAILABLE, handle_proposals_bnb_post_route)

    # ---- DELETE -------------------------------------------------------------
    r.add('DELETE', lambda p: p.startswith('/api/rag/documents/') and RAG_AVAILABLE,         lambda h: handle_rag_document_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/cag/documents/') and CAG_AVAILABLE,         lambda h: handle_cag_document_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/prompts/') and PROMPTS_AVAILABLE,           lambda h: handle_prompts_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/career/list/'),              lambda h: handle_career_list_remove_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/ollama/agents/') and OLLAMA_AGENTS_AVAILABLE, handle_ollama_agent_detail_route)
    r.add('DELETE', lambda p: p.startswith('/api/todos/users/') and TODOS_AVAILABLE,         lambda h: handle_users_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/todos/lists/') and '/share' in p and TODOS_AVAILABLE, lambda h: handle_lists_unshare_route(h, _second_last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/todos/lists/') and TODOS_AVAILABLE,         lambda h: handle_lists_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/todos/tags/') and TODOS_AVAILABLE,          lambda h: handle_tags_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/todos/') and TODOS_AVAILABLE,               lambda h: handle_todos_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/tasks/'),                    lambda h: handle_task_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and '/contacts/'    in p, handle_contact_delete_route)
    r.add('DELETE', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and '/competitors/' in p, handle_competitor_delete_route)
    r.add('DELETE', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and '/activities/'  in p, handle_activity_delete_route)
    r.add('DELETE', lambda p: p == '/api/opportunities',                      handle_opportunities_delete_all_route)
    r.add('DELETE', lambda p: p.startswith('/api/opportunities/'),            lambda h: handle_opportunities_delete_route(h, _last(h.path)))
    r.add('DELETE', lambda p: p.startswith('/api/proposal-items/') and TRACKING_AVAILABLE, handle_proposal_item_delete_route)
    r.add('DELETE', lambda p: p.startswith('/api/bnb-items/') and TRACKING_AVAILABLE,      handle_bnb_item_delete_route)
    r.add('DELETE', lambda p: p.startswith('/api/hotwash-items/') and TRACKING_AVAILABLE,  handle_hotwash_item_delete_route)
    r.add('DELETE', lambda p: p.startswith('/api/proposals/') and PROPOSALS_AVAILABLE,       handle_proposals_delete_route)

    # ---- PUT ----------------------------------------------------------------
    r.add('PUT', lambda p: p.startswith('/api/shredding/requirements/'),      lambda h: handle_shredding_req_update_route(h, h.path, _qp(h.path)))
    r.add('PUT', lambda p: p.startswith('/api/prompts/') and PROMPTS_AVAILABLE,              handle_prompts_update_route)
    r.add('PUT', lambda p: p.startswith('/api/ollama/agents/') and OLLAMA_AGENTS_AVAILABLE,  handle_ollama_agent_detail_route)
    r.add('PUT', lambda p: p.startswith('/api/todos/users/') and TODOS_AVAILABLE,            lambda h: handle_users_update_route(h, _last(h.path)))
    r.add('PUT', lambda p: p.startswith('/api/todos/lists/') and TODOS_AVAILABLE,            lambda h: handle_lists_update_route(h, _last(h.path)))
    r.add('PUT', lambda p: p.startswith('/api/todos/tags/') and TODOS_AVAILABLE,             lambda h: handle_tags_update_route(h, _last(h.path)))
    r.add('PUT', lambda p: p.startswith('/api/todos/') and TODOS_AVAILABLE,                  lambda h: handle_todos_update_route(h, _last(h.path)))
    r.add('PUT', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and '/contacts/'    in p, handle_contact_update_route)
    r.add('PUT', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and '/competitors/' in p, handle_competitor_update_route)
    r.add('PUT', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/win-strategy'), handle_win_strategy_put_route)
    r.add('PUT', lambda p: CAPTURE_AVAILABLE and p.startswith('/api/opportunities/') and p.endswith('/ptw'),          handle_ptw_put_route)
    r.add('PUT', lambda p: p.startswith('/api/opportunities/'),               handle_opportunities_update_route)
    r.add('PUT', lambda p: p.startswith('/api/proposal-items/') and TRACKING_AVAILABLE, handle_proposal_item_update_route)
    r.add('PUT', lambda p: p.startswith('/api/bnb-items/') and TRACKING_AVAILABLE,      handle_bnb_item_update_route)
    r.add('PUT', lambda p: p.startswith('/api/hotwash-items/') and TRACKING_AVAILABLE,  handle_hotwash_item_update_route)
    r.add('PUT', lambda p: p == '/api/settings/tracking-tasks',               handle_tracking_tasks_put_route)
    r.add('PUT', lambda p: p.startswith('/api/proposals/') and PROPOSALS_AVAILABLE,          handle_proposals_update_route)

    return r
