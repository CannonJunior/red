"""
server/router.py — Lightweight URL router for CustomHTTPRequestHandler.

Routes are stored per HTTP method so dispatch only scans same-method routes
(O(k) where k is the count for that verb, not O(n) total).

`match_fn(path)` returns True when the route applies.
`action` is either a no-argument method name on the handler instance
or a callable(handler) that handles the request directly.

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

from typing import Callable, Dict, List, NamedTuple, Union


class _Route(NamedTuple):
    method: str
    match: Callable[[str], bool]
    action: Union[str, Callable]  # method name OR callable(handler)


class Router:
    """Route registry with per-method O(k) dispatch."""

    def __init__(self) -> None:
        # Keyed by uppercase HTTP verb → ordered list of routes for that verb.
        self._routes: Dict[str, List[_Route]] = {}

    def add(self, method: str, match: Callable[[str], bool], action: Union[str, Callable]) -> None:
        """
        Register a route.

        Args:
            method: HTTP verb ('GET', 'POST', 'DELETE', 'PUT').
            match: Callable that returns True when the path matches.
            action: Zero-argument method name on the handler instance,
                    OR a callable(handler) that handles the request directly.
        """
        verb = method.upper()
        if verb not in self._routes:
            self._routes[verb] = []
        self._routes[verb].append(_Route(verb, match, action))

    def dispatch(self, method: str, path: str, handler) -> bool:
        """
        Find and invoke the first matching route for this HTTP method.

        Args:
            method: HTTP verb of the incoming request.
            path: Request path (may include query string).
            handler: Handler instance (has self.path etc.).

        Returns:
            True if a route matched and was invoked, False otherwise.
        """
        verb = method.upper()
        routes = self._routes.get(verb)
        if not routes:
            return False
        # Strip query string for matching
        bare = path.split('?')[0]
        for route in routes:
            if route.match(bare):
                if callable(route.action) and not isinstance(route.action, str):
                    route.action(handler)
                else:
                    getattr(handler, route.action)()
                return True
        return False
