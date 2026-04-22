"""
opportunities_api.py — Core opportunities CRUD for OpportunitiesManager.

Task management and pipeline stats live in opportunities_tasks_mixin.py.
Schema creation lives in opportunities_schema.py.
Module-level request handler functions live in opportunities_handlers.py.

Public surface (re-exported for backwards compatibility):
    OpportunitiesManager
    get_opportunities_manager
    handle_opportunities_* / handle_tasks_* / handle_pipeline_stats_request
"""

import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from server.db_pool import get_db as _get_db
    _USE_POOL = True
except ImportError:
    _USE_POOL = False

from config.database import DEFAULT_DB
from opportunities_schema import init_opportunities_schema
from opportunities_tasks_mixin import _TasksMixin


class OpportunitiesManager(_TasksMixin):
    """Manage opportunities with SQLite storage and knowledge graph integration."""

    def __init__(self, db_path: str = DEFAULT_DB):
        """Initialize opportunities manager."""
        self.db_path = db_path
        self._init_database()

    def _connect(self):
        """
        Return a context manager for a database connection.

        Uses the thread-local pool when available, falls back to a plain
        sqlite3.connect otherwise.

        Returns:
            Context manager yielding sqlite3.Connection.
        """
        if _USE_POOL:
            return _get_db(self.db_path)
        from contextlib import contextmanager

        @contextmanager
        def _plain():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        return _plain()

    def _init_database(self):
        """Initialize all tables and indexes via the schema module."""
        conn = sqlite3.connect(self.db_path)
        init_opportunities_schema(conn)
        conn.close()

    # -------------------------------------------------------------------------
    # Opportunity CRUD
    # -------------------------------------------------------------------------

    def create_opportunity(self, name: str, description: str = "",
                           status: str = "open", priority: str = "medium",
                           value: float = 0.0, tags: List[str] = None,
                           metadata: Dict = None,
                           pipeline_stage: str = "identified",
                           probability: str = "",
                           proposal_due_date: str = "",
                           opp_number: str = "",
                           is_iwa: str = "",
                           owning_org: str = "",
                           proposal_folder: str = "",
                           agency: str = "",
                           solicitation_link: str = "",
                           deal_type: str = "") -> Dict:
        """
        Create a new opportunity.

        Args:
            name: Opportunity name.
            description: Detailed description.
            status: Legacy status field (open, in_progress, won, lost).
            priority: Priority level (low, medium, high).
            value: Estimated contract value ($).
            tags: List of tags.
            metadata: Additional metadata.
            pipeline_stage: Workflow pipeline stage slug.
            probability: Probability of win (e.g. "25%").
            proposal_due_date: Proposal due date string.
            opp_number: CRM opportunity number.
            is_iwa: Is IWA flag ("yes"/"no").
            owning_org: Owning organization / division.
            proposal_folder: URL or path to proposal folder.
            agency: Client agency name.
            solicitation_link: Link to solicitation (SAM.gov etc.).
            deal_type: Deal type (e.g. "New Business", "Recompete").

        Returns:
            Created opportunity data dict.
        """
        try:
            opportunity_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            tags_json = json.dumps(tags or [])
            metadata_json = json.dumps(metadata or {})

            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO opportunities
                (id, name, description, status, priority, value, tags, metadata,
                 pipeline_stage, probability, proposal_due_date, opp_number, is_iwa,
                 owning_org, proposal_folder, agency, solicitation_link, deal_type,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (opportunity_id, name, description, status, priority, value,
                  tags_json, metadata_json, pipeline_stage,
                  probability, proposal_due_date, opp_number, is_iwa,
                  owning_org, proposal_folder, agency, solicitation_link, deal_type,
                  now, now))

            conn.commit()

            self._add_to_knowledge_graph(opportunity_id, name, description, tags or [])

            return {
                'status': 'success',
                'opportunity': {
                    'id': opportunity_id, 'name': name, 'description': description,
                    'status': status, 'pipeline_stage': pipeline_stage,
                    'priority': priority, 'value': value,
                    'tags': tags or [], 'metadata': metadata or {},
                    'probability': probability, 'proposal_due_date': proposal_due_date,
                    'opp_number': opp_number, 'is_iwa': is_iwa,
                    'owning_org': owning_org, 'proposal_folder': proposal_folder,
                    'agency': agency, 'solicitation_link': solicitation_link,
                    'deal_type': deal_type, 'created_at': now, 'updated_at': now,
                }
            }

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to create opportunity: {str(e)}'}

    def list_opportunities(self, status: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> Dict:
        """
        List opportunities with optional status filter and pagination.

        Args:
            status: Optional status filter.
            limit: Maximum results (default 100).
            offset: Records to skip for pagination (default 0).

        Returns:
            Dict with opportunities list, total count, and pagination metadata.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                if status:
                    total = cursor.execute(
                        "SELECT COUNT(*) FROM opportunities WHERE status = ?", (status,)
                    ).fetchone()[0]
                    cursor.execute("""
                        SELECT id, name, description, status, pipeline_stage, priority,
                               value, tags, metadata, probability, proposal_due_date,
                               opp_number, is_iwa, owning_org, proposal_folder, agency,
                               solicitation_link, deal_type, created_at, updated_at
                        FROM opportunities
                        WHERE status = ?
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                    """, (status, limit, offset))
                else:
                    total = cursor.execute(
                        "SELECT COUNT(*) FROM opportunities"
                    ).fetchone()[0]
                    cursor.execute("""
                        SELECT id, name, description, status, pipeline_stage, priority,
                               value, tags, metadata, probability, proposal_due_date,
                               opp_number, is_iwa, owning_org, proposal_folder, agency,
                               solicitation_link, deal_type, created_at, updated_at
                        FROM opportunities
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                    """, (limit, offset))

                rows = cursor.fetchall()

            def _row(r):
                return {
                    'id': r['id'], 'name': r['name'], 'description': r['description'],
                    'status': r['status'],
                    'pipeline_stage': r['pipeline_stage'] or 'identified',
                    'priority': r['priority'], 'value': r['value'],
                    'tags': json.loads(r['tags']) if r['tags'] else [],
                    'metadata': json.loads(r['metadata']) if r['metadata'] else {},
                    'probability': r['probability'] or '',
                    'proposal_due_date': r['proposal_due_date'] or '',
                    'opp_number': r['opp_number'] or '',
                    'is_iwa': r['is_iwa'] or '',
                    'owning_org': r['owning_org'] or '',
                    'proposal_folder': r['proposal_folder'] or '',
                    'agency': r['agency'] or '',
                    'solicitation_link': r['solicitation_link'] or '',
                    'deal_type': r['deal_type'] or '',
                    'created_at': r['created_at'], 'updated_at': r['updated_at'],
                }

            opportunities = [_row(r) for r in rows]
            return {
                'status': 'success',
                'opportunities': opportunities,
                'count': len(opportunities),
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + len(opportunities)) < total,
            }

        except Exception as e:
            return {
                'status': 'error', 'message': f'Failed to list opportunities: {str(e)}',
                'opportunities': [], 'count': 0, 'total': 0,
                'limit': limit, 'offset': offset, 'has_more': False,
            }

    def get_opportunity(self, opportunity_id: str) -> Dict:
        """
        Get a specific opportunity by ID.

        Args:
            opportunity_id: Opportunity ID.

        Returns:
            Opportunity data dict.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name, description, status, pipeline_stage, priority,
                       value, tags, metadata, probability, proposal_due_date,
                       opp_number, is_iwa, owning_org, proposal_folder, agency,
                       solicitation_link, deal_type, created_at, updated_at
                FROM opportunities WHERE id = ?
            """, (opportunity_id,))

            row = cursor.fetchone()
            if not row:
                return {'status': 'error', 'message': 'Opportunity not found'}

            return {
                'status': 'success',
                'opportunity': {
                    'id': row['id'], 'name': row['name'],
                    'description': row['description'], 'status': row['status'],
                    'pipeline_stage': row['pipeline_stage'] or 'identified',
                    'priority': row['priority'], 'value': row['value'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'probability': row['probability'] or '',
                    'proposal_due_date': row['proposal_due_date'] or '',
                    'opp_number': row['opp_number'] or '',
                    'is_iwa': row['is_iwa'] or '',
                    'owning_org': row['owning_org'] or '',
                    'proposal_folder': row['proposal_folder'] or '',
                    'agency': row['agency'] or '',
                    'solicitation_link': row['solicitation_link'] or '',
                    'deal_type': row['deal_type'] or '',
                    'created_at': row['created_at'], 'updated_at': row['updated_at'],
                }
            }

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to get opportunity: {str(e)}'}

    def update_opportunity(self, opportunity_id: str, **updates) -> Dict:
        """
        Update an opportunity.

        Args:
            opportunity_id: Opportunity ID.
            **updates: Fields to update.

        Returns:
            Updated opportunity data dict.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            _updatable = [
                'name', 'description', 'status', 'pipeline_stage', 'priority', 'value',
                'probability', 'proposal_due_date', 'opp_number', 'is_iwa',
                'owning_org', 'proposal_folder', 'agency', 'solicitation_link', 'deal_type',
            ]
            update_fields = [f"{f} = ?" for f in _updatable if f in updates]
            update_values = [updates[f] for f in _updatable if f in updates]

            if 'tags' in updates:
                update_fields.append("tags = ?")
                update_values.append(json.dumps(updates['tags']))

            if 'metadata' in updates:
                update_fields.append("metadata = ?")
                update_values.append(json.dumps(updates['metadata']))

            if not update_fields:
                return {'status': 'error', 'message': 'No fields to update'}

            update_fields.append("updated_at = ?")
            update_values.extend([datetime.now().isoformat(), opportunity_id])

            cursor.execute(
                f"UPDATE opportunities SET {', '.join(update_fields)} WHERE id = ?",
                update_values,
            )
            conn.commit()

            if 'name' in updates or 'description' in updates or 'tags' in updates:
                self._update_knowledge_graph(opportunity_id, updates)

            return self.get_opportunity(opportunity_id)

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to update opportunity: {str(e)}'}

    def delete_opportunity(self, opportunity_id: str) -> Dict:
        """
        Delete an opportunity.

        Args:
            opportunity_id: Opportunity ID.

        Returns:
            Success status dict.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("DELETE FROM opportunities WHERE id = ?", (opportunity_id,))
            conn.commit()
            self._remove_from_knowledge_graph(opportunity_id)

            return {'status': 'success', 'message': 'Opportunity deleted successfully'}

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to delete opportunity: {str(e)}'}

    # -------------------------------------------------------------------------
    # Knowledge Graph helpers (optional RAG integration)
    # -------------------------------------------------------------------------

    def _add_to_knowledge_graph(self, opportunity_id: str, name: str,
                                description: str, tags: List[str]):
        """Add opportunity to knowledge graph for RAG reference."""
        try:
            from rag_api import handle_rag_ingest_request

            opportunity_text = (
                f"Opportunity: {name}\nID: {opportunity_id}\n"
                f"Description: {description}\nTags: {', '.join(tags)}\n"
                f"Type: Business Opportunity\n"
            )
            temp_file = Path(f"/tmp/opportunity_{opportunity_id}.txt")
            temp_file.write_text(opportunity_text)
            handle_rag_ingest_request(str(temp_file), workspace='opportunities')
            temp_file.unlink()
        except Exception as e:
            print(f"Note: Could not add to knowledge graph: {e}")

    def _update_knowledge_graph(self, opportunity_id: str, updates: Dict):
        """Update opportunity in knowledge graph (delete + re-add)."""
        try:
            self._remove_from_knowledge_graph(opportunity_id)
            result = self.get_opportunity(opportunity_id)
            if result['status'] == 'success':
                opp = result['opportunity']
                self._add_to_knowledge_graph(
                    opportunity_id, opp['name'], opp['description'], opp['tags']
                )
        except Exception as e:
            print(f"Note: Could not update knowledge graph: {e}")

    def _remove_from_knowledge_graph(self, opportunity_id: str):
        """Remove opportunity from knowledge graph."""
        try:
            from rag_api import handle_rag_document_delete_request
            handle_rag_document_delete_request(
                f"opportunity_{opportunity_id}", workspace='opportunities'
            )
        except Exception as e:
            print(f"Note: Could not remove from knowledge graph: {e}")
