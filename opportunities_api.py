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
        """Initialize opportunities table in database."""
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
