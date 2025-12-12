"""
System availability checks for optional components.

Centralizes the logic for checking if various systems (RAG, CAG, Agent, etc.)
are available and properly initialized.
"""

from typing import Dict, List


# System availability flags (set during initialization)
RAG_AVAILABLE = False
CAG_AVAILABLE = False
AGENT_SYSTEM_AVAILABLE = False
SEARCH_AVAILABLE = False
PROMPTS_AVAILABLE = False
KNOWLEDGE_GRAPH_AVAILABLE = False

# System instances (set during initialization)
cag_manager = None
mcp_manager = None
agent_manager = None
security_manager = None


def get_system_status() -> Dict[str, bool]:
    """
    Get status of all optional systems.

    Returns:
        Dictionary mapping system names to availability status
    """
    return {
        'rag': RAG_AVAILABLE,
        'cag': CAG_AVAILABLE,
        'agent_system': AGENT_SYSTEM_AVAILABLE,
        'search': SEARCH_AVAILABLE,
        'prompts': PROMPTS_AVAILABLE,
        'knowledge_graph': KNOWLEDGE_GRAPH_AVAILABLE
    }


def get_available_systems() -> List[str]:
    """
    Get list of available system names.

    Returns:
        List of system names that are currently available
    """
    status = get_system_status()
    return [name for name, available in status.items() if available]


def require_system(system_name: str) -> bool:
    """
    Check if a required system is available.

    Args:
        system_name: Name of the system to check

    Returns:
        bool: True if system is available, False otherwise
    """
    status = get_system_status()
    return status.get(system_name, False)


def initialize_systems():
    """
    Initialize all optional systems and update availability flags.

    This should be called during server startup to detect and initialize
    all available components.

    Returns:
        Dict with initialization results
    """
    global RAG_AVAILABLE, CAG_AVAILABLE, AGENT_SYSTEM_AVAILABLE
    global SEARCH_AVAILABLE, PROMPTS_AVAILABLE, KNOWLEDGE_GRAPH_AVAILABLE
    global cag_manager, mcp_manager, agent_manager, security_manager

    results = {}

    # Import RAG functionality
    try:
        from rag_api import (
            handle_rag_status_request, handle_rag_search_request,
            handle_rag_query_request, handle_rag_ingest_request
        )
        from knowledge_graph_builder import VectorKnowledgeGraphBuilder
        RAG_AVAILABLE = True
        KNOWLEDGE_GRAPH_AVAILABLE = True
        results['rag'] = 'success'
        print("✅ RAG system loaded successfully")
    except ImportError as e:
        RAG_AVAILABLE = False
        KNOWLEDGE_GRAPH_AVAILABLE = False
        results['rag'] = f'failed: {e}'
        print(f"⚠️  RAG system not available: {e}")

    # Import CAG functionality
    try:
        from cag_api import get_cag_manager
        CAG_AVAILABLE = True
        cag_manager = get_cag_manager()
        results['cag'] = 'success'
        print("✅ CAG system loaded successfully")
    except ImportError as e:
        CAG_AVAILABLE = False
        cag_manager = None
        results['cag'] = f'failed: {e}'
        print(f"⚠️  CAG system not available: {e}")

    # Import Agent system
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        from agent_system.mcp.server_manager import ZeroCostMCPServerManager, initialize_default_servers
        from agent_system.agents.agent_config import MojoOptimizedAgentManager
        from agent_system.security.local_security import ZeroCostLocalSecurity

        AGENT_SYSTEM_AVAILABLE = True
        mcp_manager = initialize_default_servers()
        agent_manager = MojoOptimizedAgentManager()
        security_manager = ZeroCostLocalSecurity()
        results['agent_system'] = 'success'
        print("✅ Agent system loaded successfully")
    except ImportError as e:
        AGENT_SYSTEM_AVAILABLE = False
        mcp_manager = None
        agent_manager = None
        security_manager = None
        results['agent_system'] = f'failed: {e}'
        print(f"⚠️  Agent system not available: {e}")

    # Import Search functionality
    try:
        from search_api import handle_search_request
        SEARCH_AVAILABLE = True
        results['search'] = 'success'
        print("✅ Search system loaded successfully")
    except ImportError as e:
        SEARCH_AVAILABLE = False
        results['search'] = f'failed: {e}'
        print(f"⚠️  Search system not available: {e}")

    # Import Prompts functionality
    try:
        from prompts_api import handle_prompts_list_request
        PROMPTS_AVAILABLE = True
        results['prompts'] = 'success'
        print("✅ Prompts system loaded successfully")
    except ImportError as e:
        PROMPTS_AVAILABLE = False
        results['prompts'] = f'failed: {e}'
        print(f"⚠️  Prompts system not available: {e}")

    return results
