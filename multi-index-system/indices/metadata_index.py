"""
Metadata Index Implementation using DuckDB

Provides structured data storage and complex analytical queries
for document metadata, relationships, and aggregations.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import json
from pathlib import Path

try:
    from ..config.settings import get_config
    from .base import IndexInterface, IndexCapabilities, QueryResult, IndexStats
except ImportError:
    from config.settings import get_config
    from indices.base import IndexInterface, IndexCapabilities, QueryResult, IndexStats

try:
    import duckdb
except ImportError:
    duckdb = None

logger = logging.getLogger(__name__)

class MetadataIndex(IndexInterface):
    """
    DuckDB-based metadata index for structured queries and analytics.

    Features:
    - Complex SQL queries and aggregations
    - JSON field support for flexible schemas
    - Time-series and temporal queries
    - Multi-workspace data isolation
    - ACID transactions
    """

    def __init__(self, index_name: str, data_path: str, config: Dict[str, Any]):
        super().__init__(index_name, data_path, config)

        self.connection = None
        self.db_path = self.data_path / f"{index_name}.duckdb"
        self.initialized_workspaces = set()

        # Configuration
        self.enable_json_extension = config.get('enable_json_extension', True)
        self.memory_limit = config.get('memory_limit', '1GB')
        self.threads = config.get('threads', 4)

    async def initialize(self) -> bool:
        """Initialize DuckDB connection and create base schema."""
        try:
            if duckdb is None:
                self.logger.error("DuckDB not installed. Run: uv add duckdb")
                return False

            # Create data directory
            self.data_path.mkdir(parents=True, exist_ok=True)

            # Connect to DuckDB
            self.connection = duckdb.connect(str(self.db_path))

            # Configure DuckDB
            self.connection.execute(f"SET memory_limit = '{self.memory_limit}'")
            self.connection.execute(f"SET threads = {self.threads}")

            # Install and load JSON extension if requested
            if self.enable_json_extension:
                try:
                    self.connection.execute("INSTALL json")
                    self.connection.execute("LOAD json")
                except Exception as e:
                    self.logger.warning(f"JSON extension not available: {e}")

            self.logger.info(f"DuckDB metadata index initialized at {self.db_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize DuckDB: {e}")
            return False

    async def shutdown(self):
        """Gracefully shutdown the metadata index."""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
                self.initialized_workspaces.clear()
                self.logger.info("Metadata index shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during metadata index shutdown: {e}")

    async def insert(self, documents: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Insert documents into the metadata index."""
        if not self.connection:
            raise RuntimeError("Metadata index not initialized")

        workspace = self._validate_workspace(workspace)
        prepared_docs = self._prepare_documents(documents)

        if not prepared_docs:
            return {"status": "error", "message": "No valid documents to insert"}

        start_time = datetime.now()

        try:
            # Ensure workspace table exists
            await self._ensure_workspace_table(workspace)

            # Prepare insert data
            insert_data = []
            for doc in prepared_docs:
                row = self._document_to_row(doc)
                insert_data.append(row)

            # Execute batch insert
            table_name = self._get_table_name(workspace)
            placeholders = ', '.join(['?' for _ in self._get_schema_columns()])

            insert_sql = f"""
                INSERT INTO {table_name}
                ({', '.join(self._get_schema_columns())})
                VALUES ({placeholders})
            """

            self.connection.executemany(insert_sql, insert_data)

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            self.logger.info(f"Inserted {len(prepared_docs)} documents into metadata index")

            return {
                "status": "success",
                "documents_inserted": len(prepared_docs),
                "execution_time": execution_time,
                "workspace": workspace
            }

        except Exception as e:
            self.logger.error(f"Metadata insert failed: {e}")
            return {"status": "error", "message": str(e)}

    async def update(self, document_updates: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Update existing documents in the metadata index."""
        if not self.connection:
            raise RuntimeError("Metadata index not initialized")

        workspace = self._validate_workspace(workspace)
        start_time = datetime.now()

        try:
            await self._ensure_workspace_table(workspace)
            table_name = self._get_table_name(workspace)
            updated_count = 0

            for update in document_updates:
                if 'id' not in update:
                    self.logger.warning("Skipping update without document ID")
                    continue

                # Build dynamic update SQL
                set_clauses = []
                values = []

                for column in self._get_schema_columns():
                    if column in update and column != 'id':
                        set_clauses.append(f"{column} = ?")
                        values.append(self._extract_field_value(update, column))

                if not set_clauses:
                    continue

                values.append(update['id'])  # For WHERE clause

                update_sql = f"""
                    UPDATE {table_name}
                    SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """

                result = self.connection.execute(update_sql, values)
                if result.rowcount > 0:
                    updated_count += 1

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            return {
                "status": "success",
                "documents_updated": updated_count,
                "execution_time": execution_time
            }

        except Exception as e:
            self.logger.error(f"Metadata update failed: {e}")
            return {"status": "error", "message": str(e)}

    async def delete(self, document_ids: List[str], workspace: str = "default") -> Dict[str, Any]:
        """Delete documents from the metadata index."""
        if not self.connection:
            raise RuntimeError("Metadata index not initialized")

        workspace = self._validate_workspace(workspace)
        start_time = datetime.now()

        try:
            await self._ensure_workspace_table(workspace)
            table_name = self._get_table_name(workspace)

            # Create placeholders for IN clause
            placeholders = ', '.join(['?' for _ in document_ids])
            delete_sql = f"DELETE FROM {table_name} WHERE id IN ({placeholders})"

            result = self.connection.execute(delete_sql, document_ids)
            deleted_count = result.rowcount

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            return {
                "status": "success",
                "documents_deleted": deleted_count,
                "execution_time": execution_time
            }

        except Exception as e:
            self.logger.error(f"Metadata delete failed: {e}")
            return {"status": "error", "message": str(e)}

    async def query(self, query_params: Dict[str, Any], workspace: str = "default") -> QueryResult:
        """Execute SQL query against the metadata index."""
        if not self.connection:
            raise RuntimeError("Metadata index not initialized")

        workspace = self._validate_workspace(workspace)
        start_time = datetime.now()

        try:
            await self._ensure_workspace_table(workspace)
            table_name = self._get_table_name(workspace)

            # Handle different query types
            if 'sql' in query_params:
                # Direct SQL query
                sql = query_params['sql']
                params = query_params.get('params', [])
            else:
                # Build query from parameters
                sql, params = self._build_query_from_params(query_params, table_name)

            # Execute query
            result = self.connection.execute(sql, params)
            rows = result.fetchall()
            columns = [desc[0] for desc in result.description]

            # Convert rows to documents
            documents = []
            for row in rows:
                doc = dict(zip(columns, row))
                # Parse JSON fields back to objects
                if 'metadata' in doc and doc['metadata']:
                    try:
                        doc['metadata'] = json.loads(doc['metadata'])
                    except Exception:
                        pass
                if 'tags' in doc and doc['tags']:
                    try:
                        doc['tags'] = json.loads(doc['tags'])
                    except Exception:
                        pass
                documents.append(doc)

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            return QueryResult(
                documents=documents,
                metadata={
                    "sql_query": sql,
                    "workspace": workspace,
                    "columns": columns
                },
                total_found=len(documents),
                execution_time=execution_time,
                index_used=self.index_name
            )

        except Exception as e:
            self.logger.error(f"Metadata query failed: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check metadata index health."""
        health_data = {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        try:
            # Check DuckDB connection
            if self.connection:
                # Simple query to test connection
                result = self.connection.execute("SELECT 1")
                if result.fetchone()[0] == 1:
                    health_data["checks"]["duckdb_connection"] = "healthy"
                else:
                    health_data["checks"]["duckdb_connection"] = "unhealthy"
            else:
                health_data["checks"]["duckdb_connection"] = "disconnected"
                return health_data

            # Check database file
            if self.db_path.exists():
                size_mb = self.db_path.stat().st_size / (1024 * 1024)
                health_data["checks"]["database_file"] = f"healthy ({size_mb:.1f}MB)"
            else:
                health_data["checks"]["database_file"] = "missing"

            # Check workspaces
            health_data["checks"]["workspaces"] = f"{len(self.initialized_workspaces)} initialized"

            # Overall status
            if all("healthy" in str(check) or "initialized" in str(check)
                   for check in health_data["checks"].values()):
                health_data["status"] = "healthy"

        except Exception as e:
            health_data["checks"]["error"] = str(e)

        return health_data

    def get_capabilities(self) -> Set[IndexCapabilities]:
        """Return supported capabilities."""
        return {
            IndexCapabilities.EXACT_MATCH,
            IndexCapabilities.RANGE_QUERIES,
            IndexCapabilities.AGGREGATION,
            IndexCapabilities.TEMPORAL_QUERIES
        }

    async def optimize(self) -> Dict[str, Any]:
        """Optimize metadata index performance."""
        try:
            optimization_results = {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "optimizations": []
            }

            if not self.connection:
                return {"status": "failed", "error": "Database not connected"}

            # Analyze tables and create indexes
            for workspace in self.initialized_workspaces:
                table_name = self._get_table_name(workspace)

                # Check if indexes exist, create if needed
                indexes_to_create = [
                    ("idx_id", "id"),
                    ("idx_created_at", "created_at"),
                    ("idx_title", "title"),
                    ("idx_author", "author")
                ]

                for index_name, column in indexes_to_create:
                    try:
                        # Check if index exists
                        check_sql = f"""
                            SELECT name FROM pragma_index_list('{table_name}')
                            WHERE name = '{index_name}'
                        """
                        result = self.connection.execute(check_sql)

                        if not result.fetchone():
                            # Create index
                            create_sql = f"CREATE INDEX {index_name} ON {table_name}({column})"
                            self.connection.execute(create_sql)
                            optimization_results["optimizations"].append({
                                "workspace": workspace,
                                "action": f"created_index_{index_name}",
                                "column": column
                            })

                    except Exception as e:
                        optimization_results["optimizations"].append({
                            "workspace": workspace,
                            "action": f"index_creation_failed",
                            "error": str(e)
                        })

                # Analyze table for query optimization
                try:
                    self.connection.execute(f"ANALYZE {table_name}")
                    optimization_results["optimizations"].append({
                        "workspace": workspace,
                        "action": "analyzed_table"
                    })
                except Exception as e:
                    optimization_results["optimizations"].append({
                        "workspace": workspace,
                        "action": "analyze_failed",
                        "error": str(e)
                    })

            return optimization_results

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def get_stats(self) -> IndexStats:
        """Get comprehensive metadata index statistics."""
        try:
            total_documents = 0

            if self.connection:
                # Count documents across all workspaces
                for workspace in self.initialized_workspaces:
                    try:
                        table_name = self._get_table_name(workspace)
                        result = self.connection.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = result.fetchone()[0]
                        total_documents += count
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
            self.logger.error(f"Failed to get metadata index stats: {e}")
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

    async def _ensure_workspace_table(self, workspace: str):
        """Ensure workspace table exists."""
        if workspace in self.initialized_workspaces:
            return

        table_name = self._get_table_name(workspace)

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id VARCHAR PRIMARY KEY,
                title VARCHAR,
                author VARCHAR,
                category VARCHAR,
                source VARCHAR,
                content_type VARCHAR,
                file_path VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON,
                tags JSON,
                content_preview TEXT,
                content_length INTEGER,
                _indexed_at TIMESTAMP
            )
        """

        self.connection.execute(create_sql)
        self.initialized_workspaces.add(workspace)

    def _get_table_name(self, workspace: str) -> str:
        """Get table name for workspace."""
        return f"metadata_{workspace.replace('-', '_')}"

    def _get_schema_columns(self) -> List[str]:
        """Get list of schema columns."""
        return [
            'id', 'title', 'author', 'category', 'source', 'content_type',
            'file_path', 'created_at', 'metadata', 'tags', 'content_preview',
            'content_length', '_indexed_at'
        ]

    def _document_to_row(self, document: Dict[str, Any]) -> List[Any]:
        """Convert document to database row."""
        row = []

        for column in self._get_schema_columns():
            value = self._extract_field_value(document, column)
            row.append(value)

        return row

    def _extract_field_value(self, document: Dict[str, Any], column: str) -> Any:
        """Extract field value for database storage."""
        if column == 'id':
            return document.get('id')
        elif column == 'title':
            return document.get('title', document.get('name', ''))
        elif column == 'author':
            return document.get('author', document.get('creator', ''))
        elif column == 'category':
            return document.get('category', document.get('type', ''))
        elif column == 'source':
            return document.get('source', document.get('origin', ''))
        elif column == 'content_type':
            return document.get('content_type', document.get('mime_type', ''))
        elif column == 'file_path':
            return document.get('file_path', document.get('path', ''))
        elif column == 'created_at':
            created = document.get('created_at', document.get('timestamp'))
            if created:
                try:
                    return datetime.fromisoformat(created.replace('Z', '+00:00'))
                except Exception:
                    pass
            return datetime.now()
        elif column == 'metadata':
            # Store additional metadata as JSON
            excluded_fields = set(self._get_schema_columns())
            metadata = {k: v for k, v in document.items()
                       if k not in excluded_fields and not k.startswith('_')}
            return json.dumps(metadata) if metadata else None
        elif column == 'tags':
            tags = document.get('tags', document.get('keywords', []))
            if isinstance(tags, list):
                return json.dumps(tags)
            elif isinstance(tags, str):
                return json.dumps([tags])
            return None
        elif column == 'content_preview':
            content = document.get('content', document.get('text', ''))
            return content[:500] if content else None
        elif column == 'content_length':
            content = document.get('content', document.get('text', ''))
            return len(content) if content else 0
        elif column == '_indexed_at':
            return datetime.fromisoformat(document.get('_indexed_at', datetime.now().isoformat()))

        return None

    def _build_query_from_params(self, query_params: Dict[str, Any], table_name: str) -> tuple:
        """Build SQL query from parameters."""
        # Base query
        select_fields = query_params.get('select', '*')
        sql_parts = [f"SELECT {select_fields} FROM {table_name}"]
        params = []

        # WHERE conditions
        where_conditions = []

        # Simple field filters
        for field in ['title', 'author', 'category', 'source']:
            if field in query_params:
                where_conditions.append(f"{field} LIKE ?")
                params.append(f"%{query_params[field]}%")

        # ID filter
        if 'id' in query_params:
            where_conditions.append("id = ?")
            params.append(query_params['id'])

        # Date range filters
        if 'created_after' in query_params:
            where_conditions.append("created_at >= ?")
            params.append(query_params['created_after'])

        if 'created_before' in query_params:
            where_conditions.append("created_at <= ?")
            params.append(query_params['created_before'])

        # Content length filter
        if 'min_content_length' in query_params:
            where_conditions.append("content_length >= ?")
            params.append(query_params['min_content_length'])

        if where_conditions:
            sql_parts.append("WHERE " + " AND ".join(where_conditions))

        # ORDER BY
        order_by = query_params.get('order_by', 'created_at DESC')
        sql_parts.append(f"ORDER BY {order_by}")

        # LIMIT
        limit = query_params.get('limit', 100)
        sql_parts.append(f"LIMIT {limit}")

        return " ".join(sql_parts), params