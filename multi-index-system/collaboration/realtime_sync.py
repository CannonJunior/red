"""
Real-time Collaboration Features for Phase 3

Provides real-time synchronization, collaborative editing, and
shared workspace management for multi-user knowledge exploration.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import weakref

try:
    from ..config.settings import get_config
    from ..cache.redis_cache import AdvancedRedisCache
    from ..core.conflict_resolution import ConflictResolver
except ImportError:
    from config.settings import get_config
    from cache.redis_cache import AdvancedRedisCache
    from core.conflict_resolution import ConflictResolver

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of real-time events."""
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    DOCUMENT_EDIT = "document_edit"
    QUERY_SHARE = "query_share"
    ANNOTATION_ADD = "annotation_add"
    ANNOTATION_UPDATE = "annotation_update"
    ANNOTATION_DELETE = "annotation_delete"
    WORKSPACE_UPDATE = "workspace_update"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    CHAT_MESSAGE = "chat_message"
    NOTIFICATION = "notification"

class PermissionLevel(Enum):
    """User permission levels."""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    GUEST = "guest"

@dataclass
class CollaborationEvent:
    """Real-time collaboration event."""
    event_id: str
    event_type: EventType
    workspace_id: str
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class UserPresence:
    """User presence information."""
    user_id: str
    display_name: str
    avatar_url: Optional[str]
    status: str  # active, idle, away
    current_document: Optional[str]
    cursor_position: Optional[Dict[str, Any]]
    last_seen: datetime
    permissions: PermissionLevel

@dataclass
class Annotation:
    """Document annotation for collaboration."""
    annotation_id: str
    document_id: str
    user_id: str
    content: str
    position: Dict[str, Any]  # Position in document
    created_at: datetime
    updated_at: datetime
    replies: List['Annotation']
    resolved: bool
    tags: List[str]

@dataclass
class SharedWorkspace:
    """Shared workspace configuration."""
    workspace_id: str
    name: str
    description: str
    owner_id: str
    members: Dict[str, PermissionLevel]
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class RealtimeCollaborationManager:
    """
    Manages real-time collaboration features.

    Features:
    - Real-time event broadcasting
    - User presence tracking
    - Document annotations and comments
    - Shared workspaces
    - Collaborative query sharing
    - Conflict resolution for concurrent edits
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()

        # Core components
        self.cache = AdvancedRedisCache(config)
        self.conflict_resolver = ConflictResolver()

        # Real-time state
        self.active_workspaces: Dict[str, SharedWorkspace] = {}
        self.user_presence: Dict[str, UserPresence] = {}
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.client_connections: Dict[str, Set[weakref.ref]] = {}

        # Event broadcasting
        self.event_queue = asyncio.Queue()
        self.broadcast_task = None

        # Collaboration settings
        self.max_concurrent_users = config.get('max_concurrent_users', 50)
        self.presence_timeout = config.get('presence_timeout', 300)  # 5 minutes
        self.event_retention = config.get('event_retention', 86400)  # 24 hours

    async def initialize(self):
        """Initialize collaboration manager."""
        try:
            await self.cache.initialize()

            # Load existing workspaces
            await self._load_workspaces()

            # Start event broadcasting
            self.broadcast_task = asyncio.create_task(self._event_broadcaster())

            # Start presence cleanup
            asyncio.create_task(self._presence_cleanup_worker())

            logger.info("Real-time collaboration manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize collaboration manager: {e}")
            raise

    async def create_workspace(self, workspace_name: str, owner_id: str,
                             description: str = "") -> SharedWorkspace:
        """Create a new shared workspace."""
        workspace_id = str(uuid.uuid4())

        workspace = SharedWorkspace(
            workspace_id=workspace_id,
            name=workspace_name,
            description=description,
            owner_id=owner_id,
            members={owner_id: PermissionLevel.OWNER},
            settings={
                'allow_anonymous': False,
                'auto_save': True,
                'version_history': True,
                'real_time_sync': True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.active_workspaces[workspace_id] = workspace

        # Cache workspace
        await self.cache.set(
            f"workspace:{workspace_id}",
            asdict(workspace),
            data_type='collaboration',
            tags=['workspace']
        )

        # Broadcast workspace creation
        await self._broadcast_event(CollaborationEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.WORKSPACE_UPDATE,
            workspace_id=workspace_id,
            user_id=owner_id,
            timestamp=datetime.now(),
            data={
                'action': 'created',
                'workspace': asdict(workspace)
            }
        ))

        logger.info(f"Created workspace {workspace_name} for user {owner_id}")
        return workspace

    async def join_workspace(self, workspace_id: str, user_id: str,
                           display_name: str, avatar_url: Optional[str] = None) -> bool:
        """Join a workspace as a user."""
        try:
            workspace = await self._get_workspace(workspace_id)
            if not workspace:
                logger.warning(f"Workspace {workspace_id} not found")
                return False

            # Check permissions
            if user_id not in workspace.members and not workspace.settings.get('allow_anonymous', False):
                logger.warning(f"User {user_id} not authorized for workspace {workspace_id}")
                return False

            # Create user presence
            presence = UserPresence(
                user_id=user_id,
                display_name=display_name,
                avatar_url=avatar_url,
                status='active',
                current_document=None,
                cursor_position=None,
                last_seen=datetime.now(),
                permissions=workspace.members.get(user_id, PermissionLevel.GUEST)
            )

            self.user_presence[user_id] = presence

            # Cache presence
            await self.cache.set(
                f"presence:{workspace_id}:{user_id}",
                asdict(presence),
                ttl=self.presence_timeout,
                data_type='collaboration',
                tags=['presence', workspace_id]
            )

            # Broadcast join event
            await self._broadcast_event(CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.USER_JOIN,
                workspace_id=workspace_id,
                user_id=user_id,
                timestamp=datetime.now(),
                data={
                    'user_presence': asdict(presence)
                }
            ))

            logger.info(f"User {user_id} joined workspace {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to join workspace: {e}")
            return False

    async def leave_workspace(self, workspace_id: str, user_id: str) -> bool:
        """Leave a workspace."""
        try:
            # Remove presence
            if user_id in self.user_presence:
                del self.user_presence[user_id]

            # Remove cached presence
            await self.cache.delete(f"presence:{workspace_id}:{user_id}", 'collaboration')

            # Broadcast leave event
            await self._broadcast_event(CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.USER_LEAVE,
                workspace_id=workspace_id,
                user_id=user_id,
                timestamp=datetime.now(),
                data={}
            ))

            logger.info(f"User {user_id} left workspace {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to leave workspace: {e}")
            return False

    async def share_query(self, workspace_id: str, user_id: str, query_data: Dict[str, Any]) -> str:
        """Share a query with workspace members."""
        try:
            share_id = str(uuid.uuid4())

            shared_query = {
                'share_id': share_id,
                'query_text': query_data.get('query_text', ''),
                'query_params': query_data.get('query_params', {}),
                'results_preview': query_data.get('results_preview', []),
                'shared_by': user_id,
                'shared_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            }

            # Cache shared query
            await self.cache.set(
                f"shared_query:{share_id}",
                shared_query,
                ttl=86400,  # 24 hours
                data_type='collaboration',
                tags=['shared_query', workspace_id]
            )

            # Broadcast query share event
            await self._broadcast_event(CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.QUERY_SHARE,
                workspace_id=workspace_id,
                user_id=user_id,
                timestamp=datetime.now(),
                data=shared_query
            ))

            logger.info(f"Query shared by {user_id} in workspace {workspace_id}")
            return share_id

        except Exception as e:
            logger.error(f"Failed to share query: {e}")
            return ""

    async def add_annotation(self, workspace_id: str, user_id: str, document_id: str,
                           content: str, position: Dict[str, Any]) -> Optional[Annotation]:
        """Add annotation to a document."""
        try:
            # Check permissions
            workspace = await self._get_workspace(workspace_id)
            if not workspace or user_id not in workspace.members:
                return None

            user_permissions = workspace.members[user_id]
            if user_permissions == PermissionLevel.VIEWER:
                logger.warning(f"User {user_id} lacks annotation permissions")
                return None

            annotation = Annotation(
                annotation_id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                content=content,
                position=position,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                replies=[],
                resolved=False,
                tags=[]
            )

            # Cache annotation
            await self.cache.set(
                f"annotation:{annotation.annotation_id}",
                asdict(annotation),
                data_type='collaboration',
                tags=['annotation', workspace_id, document_id]
            )

            # Broadcast annotation event
            await self._broadcast_event(CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.ANNOTATION_ADD,
                workspace_id=workspace_id,
                user_id=user_id,
                timestamp=datetime.now(),
                data={
                    'annotation': asdict(annotation)
                }
            ))

            logger.info(f"Annotation added by {user_id} on document {document_id}")
            return annotation

        except Exception as e:
            logger.error(f"Failed to add annotation: {e}")
            return None

    async def update_user_presence(self, workspace_id: str, user_id: str,
                                 presence_data: Dict[str, Any]) -> bool:
        """Update user presence information."""
        try:
            if user_id not in self.user_presence:
                return False

            presence = self.user_presence[user_id]

            # Update presence fields
            if 'status' in presence_data:
                presence.status = presence_data['status']
            if 'current_document' in presence_data:
                presence.current_document = presence_data['current_document']
            if 'cursor_position' in presence_data:
                presence.cursor_position = presence_data['cursor_position']

            presence.last_seen = datetime.now()

            # Update cache
            await self.cache.set(
                f"presence:{workspace_id}:{user_id}",
                asdict(presence),
                ttl=self.presence_timeout,
                data_type='collaboration'
            )

            # Broadcast presence update
            await self._broadcast_event(CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.CURSOR_MOVE,
                workspace_id=workspace_id,
                user_id=user_id,
                timestamp=datetime.now(),
                data=presence_data
            ))

            return True

        except Exception as e:
            logger.error(f"Failed to update presence: {e}")
            return False

    async def get_workspace_activity(self, workspace_id: str, limit: int = 50) -> List[CollaborationEvent]:
        """Get recent workspace activity."""
        try:
            # Get cached events
            events_data = await self.cache.get(f"workspace_events:{workspace_id}", 'collaboration')

            if events_data:
                events = [CollaborationEvent(**event_data) for event_data in events_data[-limit:]]
                return events

            return []

        except Exception as e:
            logger.error(f"Failed to get workspace activity: {e}")
            return []

    async def get_active_users(self, workspace_id: str) -> List[UserPresence]:
        """Get currently active users in workspace."""
        try:
            active_users = []
            current_time = datetime.now()

            for user_id, presence in self.user_presence.items():
                # Check if user is still active
                if (current_time - presence.last_seen).total_seconds() < self.presence_timeout:
                    active_users.append(presence)

            return active_users

        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            return []

    async def get_document_annotations(self, workspace_id: str, document_id: str) -> List[Annotation]:
        """Get all annotations for a document."""
        try:
            # Search for annotations by tags
            annotation_keys = await self.cache.get_multi([
                (f"annotation_keys:{workspace_id}:{document_id}", 'collaboration')
            ])

            annotations = []
            if annotation_keys:
                for key in annotation_keys.values():
                    if isinstance(key, list):
                        for annotation_id in key:
                            annotation_data = await self.cache.get(f"annotation:{annotation_id}", 'collaboration')
                            if annotation_data:
                                annotations.append(Annotation(**annotation_data))

            return annotations

        except Exception as e:
            logger.error(f"Failed to get document annotations: {e}")
            return []

    # Event handling

    def register_event_handler(self, event_type: EventType, handler: Callable):
        """Register an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(handler)

    def unregister_event_handler(self, event_type: EventType, handler: Callable):
        """Unregister an event handler."""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass

    async def _broadcast_event(self, event: CollaborationEvent):
        """Broadcast event to all relevant clients."""
        try:
            # Add to event queue for processing
            await self.event_queue.put(event)

            # Cache event for history
            await self._cache_event(event)

            # Call registered handlers
            if event.event_type in self.event_handlers:
                for handler in self.event_handlers[event.event_type]:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Event handler failed: {e}")

        except Exception as e:
            logger.error(f"Failed to broadcast event: {e}")

    async def _event_broadcaster(self):
        """Background task for event broadcasting."""
        while True:
            try:
                # Get event from queue
                event = await self.event_queue.get()

                # Broadcast to workspace members
                workspace_id = event.workspace_id
                if workspace_id in self.client_connections:
                    connections = self.client_connections[workspace_id].copy()

                    for conn_ref in connections:
                        conn = conn_ref()
                        if conn is None:
                            # Clean up dead reference
                            self.client_connections[workspace_id].discard(conn_ref)
                        else:
                            try:
                                # Send event to client connection
                                await conn.send_event(asdict(event))
                            except Exception as e:
                                logger.warning(f"Failed to send event to client: {e}")
                                self.client_connections[workspace_id].discard(conn_ref)

                # Mark task as done
                self.event_queue.task_done()

            except Exception as e:
                logger.error(f"Event broadcaster error: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on persistent errors

    async def _cache_event(self, event: CollaborationEvent):
        """Cache event for history."""
        try:
            workspace_events_key = f"workspace_events:{event.workspace_id}"

            # Get existing events
            existing_events = await self.cache.get(workspace_events_key, 'collaboration') or []

            # Add new event
            existing_events.append(asdict(event))

            # Keep only recent events
            if len(existing_events) > 1000:
                existing_events = existing_events[-1000:]

            # Cache updated events
            await self.cache.set(
                workspace_events_key,
                existing_events,
                ttl=self.event_retention,
                data_type='collaboration',
                tags=['events', event.workspace_id]
            )

        except Exception as e:
            logger.error(f"Failed to cache event: {e}")

    async def _presence_cleanup_worker(self):
        """Background worker to clean up inactive user presence."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute

                current_time = datetime.now()
                inactive_users = []

                for user_id, presence in self.user_presence.items():
                    if (current_time - presence.last_seen).total_seconds() > self.presence_timeout:
                        inactive_users.append(user_id)

                # Remove inactive users
                for user_id in inactive_users:
                    del self.user_presence[user_id]
                    logger.info(f"Cleaned up inactive user presence: {user_id}")

            except Exception as e:
                logger.error(f"Presence cleanup error: {e}")

    async def _load_workspaces(self):
        """Load existing workspaces from cache."""
        try:
            # This would load workspaces from persistent storage
            # For now, start with empty state
            self.active_workspaces = {}

        except Exception as e:
            logger.error(f"Failed to load workspaces: {e}")

    async def _get_workspace(self, workspace_id: str) -> Optional[SharedWorkspace]:
        """Get workspace by ID."""
        if workspace_id in self.active_workspaces:
            return self.active_workspaces[workspace_id]

        # Try to load from cache
        workspace_data = await self.cache.get(f"workspace:{workspace_id}", 'collaboration')
        if workspace_data:
            workspace = SharedWorkspace(**workspace_data)
            self.active_workspaces[workspace_id] = workspace
            return workspace

        return None

    async def shutdown(self):
        """Shutdown collaboration manager."""
        try:
            # Cancel background tasks
            if self.broadcast_task:
                self.broadcast_task.cancel()

            # Clean up connections
            self.client_connections.clear()

            # Shutdown cache
            await self.cache.shutdown()

            logger.info("Collaboration manager shutdown complete")

        except Exception as e:
            logger.error(f"Error during collaboration shutdown: {e}")

# WebSocket connection manager for real-time communication

class WebSocketConnectionManager:
    """Manages WebSocket connections for real-time collaboration."""

    def __init__(self, collaboration_manager: RealtimeCollaborationManager):
        self.collaboration_manager = collaboration_manager
        self.connections: Dict[str, Set[Any]] = {}  # workspace_id -> set of connections

    async def connect(self, websocket, workspace_id: str, user_id: str):
        """Add new WebSocket connection."""
        if workspace_id not in self.connections:
            self.connections[workspace_id] = set()

        self.connections[workspace_id].add(websocket)

        # Set up connection reference for event broadcasting
        if workspace_id not in self.collaboration_manager.client_connections:
            self.collaboration_manager.client_connections[workspace_id] = set()

        # Add weak reference to avoid memory leaks
        conn_ref = weakref.ref(websocket)
        self.collaboration_manager.client_connections[workspace_id].add(conn_ref)

        logger.info(f"WebSocket connected for user {user_id} in workspace {workspace_id}")

    async def disconnect(self, websocket, workspace_id: str, user_id: str):
        """Remove WebSocket connection."""
        if workspace_id in self.connections:
            self.connections[workspace_id].discard(websocket)

            if not self.connections[workspace_id]:
                del self.connections[workspace_id]

        # Clean up collaboration manager references
        if workspace_id in self.collaboration_manager.client_connections:
            refs_to_remove = []
            for conn_ref in self.collaboration_manager.client_connections[workspace_id]:
                if conn_ref() == websocket:
                    refs_to_remove.append(conn_ref)

            for ref in refs_to_remove:
                self.collaboration_manager.client_connections[workspace_id].discard(ref)

        logger.info(f"WebSocket disconnected for user {user_id} in workspace {workspace_id}")

    async def broadcast_to_workspace(self, workspace_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections in workspace."""
        if workspace_id not in self.connections:
            return

        disconnected = set()
        for websocket in self.connections[workspace_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            self.connections[workspace_id].discard(websocket)