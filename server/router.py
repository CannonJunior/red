"""
server/router.py — Lightweight URL router for CustomHTTPRequestHandler.

Routes are ordered tuples: (method, match_fn, action_name).
`match_fn(path)` returns True when the route applies.
`action_name` is the no-argument method name on the handler instance.

All handler methods must be *argument-free* — they extract any path
parameters from `self.path` internally.

Usage:
    from server.router import Router

    _router = Router()
    _router.add('GET',  lambda p: p == '/api/health',  'handle_health_api')
    _router.add('DELETE', lambda p: p.startswith('/api/items/'), 'handle_item_delete_api')

    # In do_GET / do_POST / do_DELETE:
    if _router.dispatch('GET', self.path, self):
        return
    self.send_error(404, f"Not found: {self.path}")
"""

from typing import Callable, List, NamedTuple


class _Route(NamedTuple):
    method: str
    match: Callable[[str], bool]
    action: str  # name of zero-arg method on the handler instance


class Router:
    """Ordered route registry with O(n) dispatch."""

    def __init__(self) -> None:
        self._routes: List[_Route] = []

    def add(self, method: str, match: Callable[[str], bool], action: str) -> None:
        """
        Register a route.

        Args:
            method: HTTP verb ('GET', 'POST', 'DELETE', 'PUT').
            match: Callable that returns True when the path matches.
            action: Zero-argument method name on the handler instance.
        """
        self._routes.append(_Route(method.upper(), match, action))

    def dispatch(self, method: str, path: str, handler) -> bool:
        """
        Find and invoke the first matching route.

        Args:
            method: HTTP verb of the incoming request.
            path: Request path (may include query string).
            handler: Handler instance (has self.path etc.).

        Returns:
            True if a route matched and was invoked, False otherwise.
        """
        method = method.upper()
        # Strip query string for matching
        bare = path.split('?')[0]
        for route in self._routes:
            if route.method == method and route.match(bare):
                getattr(handler, route.action)()
                return True
        return False
