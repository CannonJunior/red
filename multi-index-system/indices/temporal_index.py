"""
Temporal Index Implementation

Provides version control, temporal queries, and document history tracking.
Supports time-travel queries and change analysis.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
import sqlite3
from pathlib import Path
import hashlib

try:
    from ..config.settings import get_config
    from .base import IndexInterface, IndexCapabilities, QueryResult, IndexStats
except ImportError:
    from config.settings import get_config
    from indices.base import IndexInterface, IndexCapabilities, QueryResult, IndexStats

logger = logging.getLogger(__name__)

class TemporalIndex(IndexInterface):
    """
    SQLite-based temporal index for document versioning and time-travel queries.

    Features:
    - Document version history
    - Time-travel queries (point-in-time snapshots)
    - Change tracking and diff analysis
    - Temporal aggregations
    - Multi-workspace support
    """

    def __init__(self, index_name: str, data_path: str, config: Dict[str, Any]):
        super().__init__(index_name, data_path, config)

        self.connection = None
        self.db_path = self.data_path / f"{index_name}_temporal.db"
        self.initialized_workspaces = set()

        # Configuration
        self.max_versions_per_document = config.get('max_versions_per_document', 50)
        self.retention_days = config.get('retention_days', 365)
        self.enable_compression = config.get('enable_compression', True)

    async def initialize(self) -> bool:
        """Initialize SQLite temporal database."""
        try:
            # Create data directory
            self.data_path.mkdir(parents=True, exist_ok=True)

            # Connect to SQLite
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row

            # Enable WAL mode for better concurrency
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA foreign_keys=ON")

            self.logger.info(f"Temporal index initialized at {self.db_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize temporal index: {e}")
            return False

    async def shutdown(self):
        """Gracefully shutdown the temporal index."""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
                self.initialized_workspaces.clear()
                self.logger.info("Temporal index shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during temporal index shutdown: {e}")

    async def insert(self, documents: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Insert new document versions."""
        if not self.connection:
            raise RuntimeError("Temporal index not initialized")

        workspace = self._validate_workspace(workspace)
        prepared_docs = self._prepare_documents(documents)

        if not prepared_docs:
            return {"status": "error", "message": "No valid documents to insert"}

        start_time = datetime.now()

        try:
            await self._ensure_workspace_tables(workspace)

            cursor = self.connection.cursor()
            versions_table = self._get_versions_table_name(workspace)
            snapshots_table = self._get_snapshots_table_name(workspace)

            inserted_count = 0

            for doc in prepared_docs:
                doc_id = doc['id']
                current_time = datetime.now()

                # Check if document already exists
                cursor.execute(f"""
                    SELECT version_number FROM {versions_table}
                    WHERE document_id = ?
                    ORDER BY version_number DESC
                    LIMIT 1
                """, (doc_id,))

                result = cursor.fetchone()
                next_version = (result[0] + 1) if result else 1

                # Calculate content hash for deduplication
                content_hash = self._calculate_content_hash(doc)

                # Check if content actually changed
                if next_version > 1:
                    cursor.execute(f"""
                        SELECT content_hash FROM {versions_table}
                        WHERE document_id = ? AND version_number = ?
                    """, (doc_id, next_version - 1))

                    last_hash = cursor.fetchone()
                    if last_hash and last_hash[0] == content_hash:
                        self.logger.debug(f"Document {doc_id} unchanged, skipping version")
                        continue

                # Insert new version
                cursor.execute(f"""
                    INSERT INTO {versions_table}
                    (document_id, version_number, content_hash, title, author,
                     content, metadata, created_at, operation_type, change_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    next_version,
                    content_hash,
                    doc.get('title', ''),
                    doc.get('author', ''),
                    self._extract_content(doc),
                    json.dumps(self._extract_metadata(doc)),
                    current_time.isoformat(),
                    'insert' if next_version == 1 else 'update',
                    self._generate_change_summary(doc, next_version == 1)
                ))

                # Update current snapshot
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {snapshots_table}
                    (document_id, current_version, title, author, content,
                     metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    next_version,
                    doc.get('title', ''),
                    doc.get('author', ''),
                    self._extract_content(doc),
                    json.dumps(self._extract_metadata(doc)),
                    current_time.isoformat(),
                    current_time.isoformat()
                ))

                inserted_count += 1

                # Clean up old versions if needed
                await self._cleanup_old_versions(doc_id, workspace)

            self.connection.commit()

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            return {
                "status": "success",
                "documents_inserted": inserted_count,
                "execution_time": execution_time,
                "workspace": workspace
            }

        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Temporal insert failed: {e}")
            return {"status": "error", "message": str(e)}

    async def update(self, document_updates: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Update documents (creates new versions)."""
        # For temporal index, updates are just inserts of new versions
        return await self.insert(document_updates, workspace)

    async def delete(self, document_ids: List[str], workspace: str = "default") -> Dict[str, Any]:
        """Soft delete documents (mark as deleted with tombstone)."""
        if not self.connection:
            raise RuntimeError("Temporal index not initialized")

        workspace = self._validate_workspace(workspace)
        start_time = datetime.now()

        try:
            await self._ensure_workspace_tables(workspace)

            cursor = self.connection.cursor()
            versions_table = self._get_versions_table_name(workspace)
            snapshots_table = self._get_snapshots_table_name(workspace)

            deleted_count = 0
            current_time = datetime.now()

            for doc_id in document_ids:
                # Get current version
                cursor.execute(f"""
                    SELECT version_number FROM {versions_table}
                    WHERE document_id = ?
                    ORDER BY version_number DESC
                    LIMIT 1
                """, (doc_id,))

                result = cursor.fetchone()
                if not result:
                    continue

                next_version = result[0] + 1

                # Insert tombstone version
                cursor.execute(f"""
                    INSERT INTO {versions_table}
                    (document_id, version_number, content_hash, title, author,
                     content, metadata, created_at, operation_type, change_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    next_version,
                    'deleted',
                    '',
                    '',
                    '',
                    json.dumps({"deleted": True}),
                    current_time.isoformat(),
                    'delete',
                    'Document deleted'
                ))

                # Remove from current snapshots
                cursor.execute(f"DELETE FROM {snapshots_table} WHERE document_id = ?", (doc_id,))

                deleted_count += 1

            self.connection.commit()

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            return {
                "status": "success",
                "documents_deleted": deleted_count,
                "execution_time": execution_time
            }

        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Temporal delete failed: {e}")
            return {"status": "error", "message": str(e)}

    async def query(self, query_params: Dict[str, Any], workspace: str = "default") -> QueryResult:
        """Execute temporal query."""
        if not self.connection:
            raise RuntimeError("Temporal index not initialized")

        workspace = self._validate_workspace(workspace)
        start_time = datetime.now()

        try:
            await self._ensure_workspace_tables(workspace)

            query_type = query_params.get('query_type', 'current')

            if query_type == 'current':
                return await self._query_current_state(query_params, workspace)
            elif query_type == 'point_in_time':
                return await self._query_point_in_time(query_params, workspace)
            elif query_type == 'version_history':
                return await self._query_version_history(query_params, workspace)
            elif query_type == 'changes_between':
                return await self._query_changes_between(query_params, workspace)
            elif query_type == 'temporal_aggregation':
                return await self._query_temporal_aggregation(query_params, workspace)
            else:
                raise ValueError(f"Unknown query type: {query_type}")

        except Exception as e:
            self.logger.error(f"Temporal query failed: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check temporal index health."""
        health_data = {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        try:
            # Check SQLite connection
            if self.connection:
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                if cursor.fetchone()[0] == 1:
                    health_data["checks"]["sqlite_connection"] = "healthy"
                else:
                    health_data["checks"]["sqlite_connection"] = "unhealthy"
            else:
                health_data["checks"]["sqlite_connection"] = "disconnected"
                return health_data

            # Check database file
            if self.db_path.exists():
                size_mb = self.db_path.stat().st_size / (1024 * 1024)
                health_data["checks"]["database_file"] = f"healthy ({size_mb:.1f}MB)"
            else:
                health_data["checks"]["database_file"] = "missing"

            # Check workspaces
            health_data["checks"]["workspaces"] = f"{len(self.initialized_workspaces)} initialized"

            # Check version counts
            if self.initialized_workspaces:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {self._get_versions_table_name(list(self.initialized_workspaces)[0])}
                """)
                version_count = cursor.fetchone()[0]
                health_data["checks"]["total_versions"] = f"{version_count} versions"

            # Overall status
            if health_data["checks"]["sqlite_connection"] == "healthy":
                health_data["status"] = "healthy"

        except Exception as e:
            health_data["checks"]["error"] = str(e)

        return health_data

    def get_capabilities(self) -> Set[IndexCapabilities]:
        """Return supported capabilities."""
        return {
            IndexCapabilities.TEMPORAL_QUERIES,
            IndexCapabilities.EXACT_MATCH,
            IndexCapabilities.RANGE_QUERIES,
            IndexCapabilities.AGGREGATION
        }

    async def optimize(self) -> Dict[str, Any]:
        """Optimize temporal index performance."""
        try:
            optimization_results = {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "optimizations": []
            }

            if not self.connection:
                return {"status": "failed", "error": "Database not connected"}

            cursor = self.connection.cursor()

            # Clean up old versions for all workspaces
            for workspace in self.initialized_workspaces:
                cleaned_versions = await self._cleanup_all_old_versions(workspace)
                optimization_results["optimizations"].append({
                    "workspace": workspace,
                    "action": "cleaned_old_versions",
                    "versions_removed": cleaned_versions
                })

                # Analyze tables
                versions_table = self._get_versions_table_name(workspace)
                snapshots_table = self._get_snapshots_table_name(workspace)

                cursor.execute(f"ANALYZE {versions_table}")
                cursor.execute(f"ANALYZE {snapshots_table}")

                optimization_results["optimizations"].append({
                    "workspace": workspace,
                    "action": "tables_analyzed"
                })

            # Vacuum database
            try:
                cursor.execute("VACUUM")
                optimization_results["optimizations"].append({
                    "action": "database_vacuumed"
                })
            except Exception as e:
                optimization_results["optimizations"].append({
                    "action": "vacuum_failed",
                    "error": str(e)
                })

            self.connection.commit()
            return optimization_results

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def get_stats(self) -> IndexStats:
        """Get comprehensive temporal index statistics."""
        try:
            total_documents = 0
            total_versions = 0

            if self.connection:
                cursor = self.connection.cursor()

                for workspace in self.initialized_workspaces:
                    try:
                        versions_table = self._get_versions_table_name(workspace)
                        snapshots_table = self._get_snapshots_table_name(workspace)

                        # Count current documents
                        cursor.execute(f"SELECT COUNT(*) FROM {snapshots_table}")
                        total_documents += cursor.fetchone()[0]

                        # Count total versions
                        cursor.execute(f"SELECT COUNT(*) FROM {versions_table}")
                        total_versions += cursor.fetchone()[0]

                    except Exception:
                        pass

            # Get database file size
            storage_size = 0
            if self.db_path.exists():
                storage_size = self.db_path.stat().st_size

            return IndexStats(
                document_count=total_documents,
                storage_size_bytes=storage_size,
                avg_query_time=self.get_avg_query_time(),
                total_queries=self.query_count,
                last_updated=self.last_query_time or datetime.now(),
                health_status="healthy" if self.connection else "disconnected",
                capabilities=self.get_capabilities()
            )

        except Exception as e:
            self.logger.error(f"Failed to get temporal index stats: {e}")
            return IndexStats(
                document_count=0,
                storage_size_bytes=0,
                avg_query_time=0.0,
                total_queries=0,
                last_updated=datetime.now(),
                health_status="error",
                capabilities=set()
            )

    # Helper methods

    async def _ensure_workspace_tables(self, workspace: str):
        """Ensure workspace tables exist."""
        if workspace in self.initialized_workspaces:
            return

        versions_table = self._get_versions_table_name(workspace)
        snapshots_table = self._get_snapshots_table_name(workspace)

        cursor = self.connection.cursor()

        # Create versions table (stores all document versions)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {versions_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                title TEXT,
                author TEXT,
                content TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                change_summary TEXT,
                UNIQUE(document_id, version_number)
            )
        """)

        # Create snapshots table (stores current state)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {snapshots_table} (
                document_id TEXT PRIMARY KEY,
                current_version INTEGER NOT NULL,
                title TEXT,
                author TEXT,
                content TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create indexes
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{workspace}_versions_doc_id ON {versions_table}(document_id)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{workspace}_versions_created_at ON {versions_table}(created_at)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{workspace}_snapshots_updated_at ON {snapshots_table}(updated_at)")

        self.connection.commit()
        self.initialized_workspaces.add(workspace)

    def _get_versions_table_name(self, workspace: str) -> str:
        """Get versions table name for workspace."""
        return f"temporal_versions_{workspace.replace('-', '_')}"

    def _get_snapshots_table_name(self, workspace: str) -> str:
        """Get snapshots table name for workspace."""
        return f"temporal_snapshots_{workspace.replace('-', '_')}"

    def _calculate_content_hash(self, document: Dict[str, Any]) -> str:
        """Calculate hash of document content for change detection."""
        content = self._extract_content(document)
        metadata = self._extract_metadata(document)

        hash_data = {
            'content': content,
            'title': document.get('title', ''),
            'metadata': metadata
        }

        content_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def _extract_content(self, document: Dict[str, Any]) -> str:
        """Extract content from document."""
        content_fields = ['content', 'text', 'body']
        for field in content_fields:
            if field in document and document[field]:
                return str(document[field])
        return ''

    def _extract_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for storage."""
        excluded_fields = {'id', 'content', 'text', 'body', 'title', 'author'}
        return {k: v for k, v in document.items()
                if k not in excluded_fields and not k.startswith('_')}

    def _generate_change_summary(self, document: Dict[str, Any], is_new: bool) -> str:
        """Generate summary of changes."""
        if is_new:
            return "Document created"

        # Simple change detection based on field presence
        changes = []
        if document.get('title'):
            changes.append("title")
        if document.get('content') or document.get('text'):
            changes.append("content")
        if document.get('metadata'):
            changes.append("metadata")

        return f"Updated: {', '.join(changes)}" if changes else "Document updated"

    async def _cleanup_old_versions(self, document_id: str, workspace: str):
        """Clean up old versions for a specific document."""
        versions_table = self._get_versions_table_name(workspace)
        cursor = self.connection.cursor()

        # Keep only the most recent N versions
        cursor.execute(f"""
            DELETE FROM {versions_table}
            WHERE document_id = ? AND id NOT IN (
                SELECT id FROM {versions_table}
                WHERE document_id = ?
                ORDER BY version_number DESC
                LIMIT ?
            )
        """, (document_id, document_id, self.max_versions_per_document))

    async def _cleanup_all_old_versions(self, workspace: str) -> int:
        """Clean up old versions for all documents in workspace."""
        versions_table = self._get_versions_table_name(workspace)
        cursor = self.connection.cursor()

        # Clean up by retention period
        cutoff_date = (datetime.now() - timedelta(days=self.retention_days)).isoformat()

        cursor.execute(f"""
            DELETE FROM {versions_table}
            WHERE created_at < ? AND operation_type != 'delete'
        """, (cutoff_date,))

        return cursor.rowcount

    # Query method implementations

    async def _query_current_state(self, query_params: Dict[str, Any], workspace: str) -> QueryResult:
        """Query current state of documents."""
        snapshots_table = self._get_snapshots_table_name(workspace)
        cursor = self.connection.cursor()

        # Build query
        limit = query_params.get('limit', 100)
        order_by = query_params.get('order_by', 'updated_at DESC')

        sql = f"""
            SELECT document_id, current_version, title, author, content, metadata, created_at, updated_at
            FROM {snapshots_table}
            ORDER BY {order_by}
            LIMIT ?
        """

        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()

        documents = []
        for row in rows:
            doc = dict(row)
            if doc['metadata']:
                try:
                    doc['metadata'] = json.loads(doc['metadata'])
                except Exception:
                    doc['metadata'] = {}
            documents.append(doc)

        execution_time = (datetime.now() - query_params.get('_start_time', datetime.now())).total_seconds()

        return QueryResult(
            documents=documents,
            metadata={"query_type": "current_state", "workspace": workspace},
            total_found=len(documents),
            execution_time=execution_time,
            index_used=self.index_name
        )

    async def _query_point_in_time(self, query_params: Dict[str, Any], workspace: str) -> QueryResult:
        """Query state at a specific point in time."""
        target_time = query_params.get('timestamp')
        if not target_time:
            raise ValueError("timestamp required for point_in_time query")

        versions_table = self._get_versions_table_name(workspace)
        cursor = self.connection.cursor()

        # Find latest version for each document before target time
        sql = f"""
            SELECT v1.document_id, v1.version_number, v1.title, v1.author,
                   v1.content, v1.metadata, v1.created_at, v1.operation_type
            FROM {versions_table} v1
            WHERE v1.created_at <= ?
            AND v1.version_number = (
                SELECT MAX(v2.version_number)
                FROM {versions_table} v2
                WHERE v2.document_id = v1.document_id
                AND v2.created_at <= ?
            )
            AND v1.operation_type != 'delete'
            ORDER BY v1.created_at DESC
        """

        cursor.execute(sql, (target_time, target_time))
        rows = cursor.fetchall()

        documents = []
        for row in rows:
            doc = dict(row)
            if doc['metadata']:
                try:
                    doc['metadata'] = json.loads(doc['metadata'])
                except Exception:
                    doc['metadata'] = {}
            documents.append(doc)

        execution_time = (datetime.now() - query_params.get('_start_time', datetime.now())).total_seconds()

        return QueryResult(
            documents=documents,
            metadata={"query_type": "point_in_time", "timestamp": target_time, "workspace": workspace},
            total_found=len(documents),
            execution_time=execution_time,
            index_used=self.index_name
        )

    async def _query_version_history(self, query_params: Dict[str, Any], workspace: str) -> QueryResult:
        """Query version history for specific documents."""
        document_id = query_params.get('document_id')
        if not document_id:
            raise ValueError("document_id required for version_history query")

        versions_table = self._get_versions_table_name(workspace)
        cursor = self.connection.cursor()

        sql = f"""
            SELECT document_id, version_number, title, author, content, metadata,
                   created_at, operation_type, change_summary
            FROM {versions_table}
            WHERE document_id = ?
            ORDER BY version_number DESC
        """

        cursor.execute(sql, (document_id,))
        rows = cursor.fetchall()

        documents = []
        for row in rows:
            doc = dict(row)
            if doc['metadata']:
                try:
                    doc['metadata'] = json.loads(doc['metadata'])
                except Exception:
                    doc['metadata'] = {}
            documents.append(doc)

        execution_time = (datetime.now() - query_params.get('_start_time', datetime.now())).total_seconds()

        return QueryResult(
            documents=documents,
            metadata={"query_type": "version_history", "document_id": document_id, "workspace": workspace},
            total_found=len(documents),
            execution_time=execution_time,
            index_used=self.index_name
        )

    async def _query_changes_between(self, query_params: Dict[str, Any], workspace: str) -> QueryResult:
        """Query changes between two time periods."""
        start_time = query_params.get('start_time')
        end_time = query_params.get('end_time')

        if not start_time or not end_time:
            raise ValueError("start_time and end_time required for changes_between query")

        versions_table = self._get_versions_table_name(workspace)
        cursor = self.connection.cursor()

        sql = f"""
            SELECT document_id, version_number, title, author, content, metadata,
                   created_at, operation_type, change_summary
            FROM {versions_table}
            WHERE created_at >= ? AND created_at <= ?
            ORDER BY created_at DESC
        """

        cursor.execute(sql, (start_time, end_time))
        rows = cursor.fetchall()

        documents = []
        for row in rows:
            doc = dict(row)
            if doc['metadata']:
                try:
                    doc['metadata'] = json.loads(doc['metadata'])
                except Exception:
                    doc['metadata'] = {}
            documents.append(doc)

        execution_time = (datetime.now() - query_params.get('_start_time', datetime.now())).total_seconds()

        return QueryResult(
            documents=documents,
            metadata={
                "query_type": "changes_between",
                "start_time": start_time,
                "end_time": end_time,
                "workspace": workspace
            },
            total_found=len(documents),
            execution_time=execution_time,
            index_used=self.index_name
        )

    async def _query_temporal_aggregation(self, query_params: Dict[str, Any], workspace: str) -> QueryResult:
        """Query temporal aggregations (document counts by time period)."""
        time_bucket = query_params.get('time_bucket', 'day')  # hour, day, week, month
        start_time = query_params.get('start_time')
        end_time = query_params.get('end_time')

        versions_table = self._get_versions_table_name(workspace)
        cursor = self.connection.cursor()

        # Build time bucket SQL
        if time_bucket == 'hour':
            time_format = "strftime('%Y-%m-%d %H:00:00', created_at)"
        elif time_bucket == 'day':
            time_format = "date(created_at)"
        elif time_bucket == 'week':
            time_format = "date(created_at, 'weekday 0', '-6 days')"
        elif time_bucket == 'month':
            time_format = "strftime('%Y-%m-01', created_at)"
        else:
            time_format = "date(created_at)"

        where_clause = ""
        params = []
        if start_time and end_time:
            where_clause = "WHERE created_at >= ? AND created_at <= ?"
            params = [start_time, end_time]

        sql = f"""
            SELECT {time_format} as time_bucket,
                   COUNT(*) as total_operations,
                   COUNT(CASE WHEN operation_type = 'insert' THEN 1 END) as inserts,
                   COUNT(CASE WHEN operation_type = 'update' THEN 1 END) as updates,
                   COUNT(CASE WHEN operation_type = 'delete' THEN 1 END) as deletes
            FROM {versions_table}
            {where_clause}
            GROUP BY {time_format}
            ORDER BY time_bucket DESC
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        documents = [dict(row) for row in rows]

        execution_time = (datetime.now() - query_params.get('_start_time', datetime.now())).total_seconds()

        return QueryResult(
            documents=documents,
            metadata={
                "query_type": "temporal_aggregation",
                "time_bucket": time_bucket,
                "workspace": workspace
            },
            total_found=len(documents),
            execution_time=execution_time,
            index_used=self.index_name
        )