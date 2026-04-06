"""Route handlers for TODO list API endpoints.

This module re-exports all handlers from the focused submodules:
  - todos_users.py   — user CRUD
  - todos_lists.py   — list CRUD + sharing
  - todos_items.py   — todo CRUD, smart queries, NLP parse
  - todos_tags.py    — tag CRUD
"""

from .todos_users import (
    handle_users_list_api,
    handle_users_create_api,
    handle_users_detail_api,
    handle_users_update_api,
    handle_users_delete_api,
)

from .todos_lists import (
    handle_lists_list_api,
    handle_lists_create_api,
    handle_lists_detail_api,
    handle_lists_update_api,
    handle_lists_delete_api,
    handle_lists_share_api,
    handle_lists_unshare_api,
    handle_lists_shares_api,
    handle_shared_lists_api,
)

from .todos_items import (
    handle_todos_list_api,
    handle_todos_create_api,
    handle_todos_detail_api,
    handle_todos_update_api,
    handle_todos_delete_api,
    handle_todos_complete_api,
    handle_todos_archive_api,
    handle_todos_today_api,
    handle_todos_upcoming_api,
    handle_todos_search_api,
    handle_todos_history_api,
    handle_todos_parse_api,
)

from .todos_tags import (
    handle_tags_list_api,
    handle_tags_create_api,
    handle_tags_detail_api,
    handle_tags_update_api,
    handle_tags_delete_api,
)

__all__ = [
    "handle_users_list_api",
    "handle_users_create_api",
    "handle_users_detail_api",
    "handle_users_update_api",
    "handle_users_delete_api",
    "handle_lists_list_api",
    "handle_lists_create_api",
    "handle_lists_detail_api",
    "handle_lists_update_api",
    "handle_lists_delete_api",
    "handle_lists_share_api",
    "handle_lists_unshare_api",
    "handle_lists_shares_api",
    "handle_shared_lists_api",
    "handle_todos_list_api",
    "handle_todos_create_api",
    "handle_todos_detail_api",
    "handle_todos_update_api",
    "handle_todos_delete_api",
    "handle_todos_complete_api",
    "handle_todos_archive_api",
    "handle_todos_today_api",
    "handle_todos_upcoming_api",
    "handle_todos_search_api",
    "handle_todos_history_api",
    "handle_todos_parse_api",
    "handle_tags_list_api",
    "handle_tags_create_api",
    "handle_tags_detail_api",
    "handle_tags_update_api",
    "handle_tags_delete_api",
]
