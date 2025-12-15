"""
Opportunities API for managing business opportunities and tracking.

Stores opportunities in both SQLite and knowledge graph for reference.
"""

import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class OpportunitiesManager:
    """Manage opportunities with SQLite storage and knowledge graph integration."""

    def __init__(self, db_path: str = "search_system.db"):
        """Initialize opportunities manager."""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize opportunities and tasks tables in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create opportunities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'medium',
                value REAL DEFAULT 0.0,
                tags TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_opportunities_status
            ON opportunities(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_opportunities_created
            ON opportunities(created_at DESC)
        """)

        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                assigned_to TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for tasks
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_opportunity
            ON tasks(opportunity_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_dates
            ON tasks(start_date, end_date)
        """)

        # Create task_history table for tracking edits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT,
                progress INTEGER,
                assigned_to TEXT,
                edited_by TEXT,
                edited_at TEXT NOT NULL,
                change_description TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)

        # Create index for task history
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_history_task
            ON task_history(task_id, edited_at DESC)
        """)

        conn.commit()
        conn.close()

    def create_opportunity(self, name: str, description: str = "",
                          status: str = "open", priority: str = "medium",
                          value: float = 0.0, tags: List[str] = None,
                          metadata: Dict = None) -> Dict:
        """
        Create a new opportunity.

        Args:
            name: Opportunity name
            description: Detailed description
            status: Status (open, in_progress, won, lost)
            priority: Priority level (low, medium, high)
            value: Estimated value
            tags: List of tags
            metadata: Additional metadata

        Returns:
            Created opportunity data
        """
        try:
            opportunity_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            tags_json = json.dumps(tags or [])
            metadata_json = json.dumps(metadata or {})

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO opportunities
                (id, name, description, status, priority, value, tags, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (opportunity_id, name, description, status, priority, value,
                  tags_json, metadata_json, now, now))

            conn.commit()
            conn.close()

            # Add to knowledge graph
            self._add_to_knowledge_graph(opportunity_id, name, description, tags or [])

            return {
                'status': 'success',
                'opportunity': {
                    'id': opportunity_id,
                    'name': name,
                    'description': description,
                    'status': status,
                    'priority': priority,
                    'value': value,
                    'tags': tags or [],
                    'metadata': metadata or {},
                    'created_at': now,
                    'updated_at': now
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create opportunity: {str(e)}'
            }

    def list_opportunities(self, status: Optional[str] = None) -> Dict:
        """
        List all opportunities, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of opportunities
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if status:
                cursor.execute("""
                    SELECT * FROM opportunities
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT * FROM opportunities
                    ORDER BY created_at DESC
                """)

            rows = cursor.fetchall()
            conn.close()

            opportunities = []
            for row in rows:
                opportunities.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'status': row['status'],
                    'priority': row['priority'],
                    'value': row['value'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })

            return {
                'status': 'success',
                'opportunities': opportunities,
                'count': len(opportunities)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to list opportunities: {str(e)}',
                'opportunities': [],
                'count': 0
            }

    def get_opportunity(self, opportunity_id: str) -> Dict:
        """
        Get a specific opportunity by ID.

        Args:
            opportunity_id: Opportunity ID

        Returns:
            Opportunity data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM opportunities WHERE id = ?
            """, (opportunity_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return {
                    'status': 'error',
                    'message': 'Opportunity not found'
                }

            return {
                'status': 'success',
                'opportunity': {
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'status': row['status'],
                    'priority': row['priority'],
                    'value': row['value'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get opportunity: {str(e)}'
            }

    def update_opportunity(self, opportunity_id: str, **updates) -> Dict:
        """
        Update an opportunity.

        Args:
            opportunity_id: Opportunity ID
            **updates: Fields to update

        Returns:
            Updated opportunity data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build update query
            update_fields = []
            update_values = []

            for field in ['name', 'description', 'status', 'priority', 'value']:
                if field in updates:
                    update_fields.append(f"{field} = ?")
                    update_values.append(updates[field])

            if 'tags' in updates:
                update_fields.append("tags = ?")
                update_values.append(json.dumps(updates['tags']))

            if 'metadata' in updates:
                update_fields.append("metadata = ?")
                update_values.append(json.dumps(updates['metadata']))

            if not update_fields:
                return {'status': 'error', 'message': 'No fields to update'}

            update_fields.append("updated_at = ?")
            update_values.append(datetime.now().isoformat())

            update_values.append(opportunity_id)

            cursor.execute(f"""
                UPDATE opportunities
                SET {', '.join(update_fields)}
                WHERE id = ?
            """, update_values)

            conn.commit()
            conn.close()

            # Update knowledge graph if name or description changed
            if 'name' in updates or 'description' in updates or 'tags' in updates:
                self._update_knowledge_graph(opportunity_id, updates)

            return self.get_opportunity(opportunity_id)

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to update opportunity: {str(e)}'
            }

    def delete_opportunity(self, opportunity_id: str) -> Dict:
        """
        Delete an opportunity.

        Args:
            opportunity_id: Opportunity ID

        Returns:
            Success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM opportunities WHERE id = ?", (opportunity_id,))

            conn.commit()
            conn.close()

            # Remove from knowledge graph
            self._remove_from_knowledge_graph(opportunity_id)

            return {
                'status': 'success',
                'message': 'Opportunity deleted successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to delete opportunity: {str(e)}'
            }

    def _add_to_knowledge_graph(self, opportunity_id: str, name: str,
                                description: str, tags: List[str]):
        """Add opportunity to knowledge graph for RAG reference."""
        try:
            # Try to import RAG API to add to knowledge graph
            from rag_api import handle_rag_ingest_request

            # Create a text document for the opportunity
            opportunity_text = f"""
Opportunity: {name}
ID: {opportunity_id}
Description: {description}
Tags: {', '.join(tags)}
Type: Business Opportunity
"""

            # Write to temp file
            temp_file = Path(f"/tmp/opportunity_{opportunity_id}.txt")
            temp_file.write_text(opportunity_text)

            # Ingest into RAG system
            handle_rag_ingest_request(str(temp_file), workspace='opportunities')

            # Clean up temp file
            temp_file.unlink()

        except Exception as e:
            # Knowledge graph integration is optional
            print(f"Note: Could not add to knowledge graph: {e}")

    def _update_knowledge_graph(self, opportunity_id: str, updates: Dict):
        """Update opportunity in knowledge graph."""
        # For now, we'll delete and re-add
        # A more sophisticated approach would update the specific chunks
        try:
            self._remove_from_knowledge_graph(opportunity_id)

            # Get current opportunity data
            result = self.get_opportunity(opportunity_id)
            if result['status'] == 'success':
                opp = result['opportunity']
                self._add_to_knowledge_graph(
                    opportunity_id,
                    opp['name'],
                    opp['description'],
                    opp['tags']
                )
        except Exception as e:
            print(f"Note: Could not update knowledge graph: {e}")

    def _remove_from_knowledge_graph(self, opportunity_id: str):
        """Remove opportunity from knowledge graph."""
        try:
            from rag_api import handle_rag_document_delete_request
            handle_rag_document_delete_request(f"opportunity_{opportunity_id}", workspace='opportunities')
        except Exception as e:
            print(f"Note: Could not remove from knowledge graph: {e}")

    # Task Management Methods

    def create_task(self, opportunity_id: str, name: str, start_date: str, end_date: str,
                   description: str = "", status: str = "pending", progress: int = 0,
                   assigned_to: str = "") -> Dict:
        """
        Create a new task for an opportunity.

        Args:
            opportunity_id: Parent opportunity ID
            name: Task name
            start_date: Task start date (ISO format)
            end_date: Task end date (ISO format)
            description: Task description
            status: Task status (pending, in_progress, completed)
            progress: Progress percentage (0-100)
            assigned_to: Person assigned to the task

        Returns:
            Created task data
        """
        try:
            task_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO tasks
                (id, opportunity_id, name, description, start_date, end_date,
                 status, progress, assigned_to, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, opportunity_id, name, description, start_date, end_date,
                  status, progress, assigned_to, now, now))

            conn.commit()
            conn.close()

            return {
                'status': 'success',
                'task': {
                    'id': task_id,
                    'opportunity_id': opportunity_id,
                    'name': name,
                    'description': description,
                    'start_date': start_date,
                    'end_date': end_date,
                    'status': status,
                    'progress': progress,
                    'assigned_to': assigned_to,
                    'created_at': now,
                    'updated_at': now
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create task: {str(e)}'
            }

    def list_tasks(self, opportunity_id: str) -> Dict:
        """
        List all tasks for an opportunity.

        Args:
            opportunity_id: Opportunity ID

        Returns:
            List of tasks
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM tasks
                WHERE opportunity_id = ?
                ORDER BY start_date ASC
            """, (opportunity_id,))

            rows = cursor.fetchall()
            conn.close()

            tasks = []
            for row in rows:
                tasks.append({
                    'id': row['id'],
                    'opportunity_id': row['opportunity_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'start_date': row['start_date'],
                    'end_date': row['end_date'],
                    'status': row['status'],
                    'progress': row['progress'],
                    'assigned_to': row['assigned_to'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })

            return {
                'status': 'success',
                'tasks': tasks,
                'count': len(tasks)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to list tasks: {str(e)}',
                'tasks': [],
                'count': 0
            }

    def update_task(self, task_id: str, edited_by: str = "system", **updates) -> Dict:
        """
        Update a task and save history.

        Args:
            task_id: Task ID
            edited_by: User who made the edit
            **updates: Fields to update

        Returns:
            Updated task data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get current task state for history
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            current_task = cursor.fetchone()

            if not current_task:
                conn.close()
                return {'status': 'error', 'message': 'Task not found'}

            # Save current state to history
            history_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            # Determine what changed
            changes = []
            for field in ['name', 'description', 'start_date', 'end_date', 'status', 'progress', 'assigned_to']:
                if field in updates and updates[field] != current_task[field]:
                    old_val = current_task[field] or "None"
                    new_val = updates[field] or "None"
                    changes.append(f"{field}: '{old_val}' → '{new_val}'")

            change_description = "; ".join(changes) if changes else "No changes"

            cursor.execute("""
                INSERT INTO task_history
                (id, task_id, opportunity_id, name, description, start_date, end_date,
                 status, progress, assigned_to, edited_by, edited_at, change_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                history_id, task_id, current_task['opportunity_id'],
                current_task['name'], current_task['description'],
                current_task['start_date'], current_task['end_date'],
                current_task['status'], current_task['progress'],
                current_task['assigned_to'], edited_by, now, change_description
            ))

            # Build update query
            update_fields = []
            update_values = []

            for field in ['name', 'description', 'start_date', 'end_date', 'status', 'progress', 'assigned_to']:
                if field in updates:
                    update_fields.append(f"{field} = ?")
                    update_values.append(updates[field])

            if not update_fields:
                conn.close()
                return {'status': 'error', 'message': 'No fields to update'}

            update_fields.append("updated_at = ?")
            update_values.append(now)

            update_values.append(task_id)

            cursor.execute(f"""
                UPDATE tasks
                SET {', '.join(update_fields)}
                WHERE id = ?
            """, update_values)

            conn.commit()
            conn.close()

            return self.get_task(task_id)

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to update task: {str(e)}'
            }

    def get_task(self, task_id: str) -> Dict:
        """Get a specific task by ID."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return {'status': 'error', 'message': 'Task not found'}

            return {
                'status': 'success',
                'task': {
                    'id': row['id'],
                    'opportunity_id': row['opportunity_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'start_date': row['start_date'],
                    'end_date': row['end_date'],
                    'status': row['status'],
                    'progress': row['progress'],
                    'assigned_to': row['assigned_to'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get task: {str(e)}'
            }

    def get_task_history(self, task_id: str) -> Dict:
        """Get edit history for a task."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM task_history
                WHERE task_id = ?
                ORDER BY edited_at DESC
            """, (task_id,))

            rows = cursor.fetchall()
            conn.close()

            history_items = []
            for row in rows:
                history_items.append({
                    'id': row['id'],
                    'task_id': row['task_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'start_date': row['start_date'],
                    'end_date': row['end_date'],
                    'status': row['status'],
                    'progress': row['progress'],
                    'assigned_to': row['assigned_to'],
                    'edited_by': row['edited_by'],
                    'edited_at': row['edited_at'],
                    'change_description': row['change_description']
                })

            return {
                'status': 'success',
                'history': history_items,
                'count': len(history_items)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get task history: {str(e)}'
            }

    def delete_task(self, task_id: str) -> Dict:
        """Delete a task."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

            conn.commit()
            conn.close()

            return {
                'status': 'success',
                'message': 'Task deleted successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to delete task: {str(e)}'
            }


# Global instance
_opportunities_manager = None


def get_opportunities_manager() -> OpportunitiesManager:
    """Get or create the global opportunities manager instance."""
    global _opportunities_manager
    if _opportunities_manager is None:
        _opportunities_manager = OpportunitiesManager()
    return _opportunities_manager


# API Request Handlers
def handle_opportunities_list_request(filters: Dict = None) -> Dict:
    """Handle list opportunities request."""
    manager = get_opportunities_manager()
    status = filters.get('status') if filters else None
    return manager.list_opportunities(status=status)


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
        metadata=data.get('metadata', {})
    )


def handle_opportunities_get_request(opportunity_id: str) -> Dict:
    """Handle get opportunity request."""
    manager = get_opportunities_manager()
    return manager.get_opportunity(opportunity_id)


def handle_opportunities_update_request(opportunity_id: str, data: Dict) -> Dict:
    """Handle update opportunity request."""
    manager = get_opportunities_manager()
    return manager.update_opportunity(opportunity_id, **data)


def handle_opportunities_delete_request(opportunity_id: str) -> Dict:
    """Handle delete opportunity request."""
    manager = get_opportunities_manager()
    return manager.delete_opportunity(opportunity_id)


# Task Request Handlers
def handle_tasks_list_request(opportunity_id: str) -> Dict:
    """Handle list tasks request."""
    manager = get_opportunities_manager()
    return manager.list_tasks(opportunity_id)


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
        assigned_to=data.get('assigned_to', '')
    )


def handle_tasks_update_request(task_id: str, data: Dict) -> Dict:
    """Handle update task request."""
    manager = get_opportunities_manager()
    return manager.update_task(task_id, **data)


def handle_task_get_request(task_id: str) -> Dict:
    """Handle get task request."""
    manager = get_opportunities_manager()
    return manager.get_task(task_id)


def handle_tasks_delete_request(task_id: str) -> Dict:
    """Handle delete task request."""
    manager = get_opportunities_manager()
    return manager.delete_task(task_id)


def handle_task_history_request(task_id: str) -> Dict:
    """Handle get task history request."""
    manager = get_opportunities_manager()
    return manager.get_task_history(task_id)
