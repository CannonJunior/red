"""
Full-Text Search Index Implementation

Provides fast text search capabilities with ranking, highlighting,
and advanced search features using built-in FTS capabilities.
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
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

class FTSIndex(IndexInterface):
    """
    SQLite FTS5-based full-text search index.

    Features:
    - Fast text search with BM25 ranking
    - Phrase search and proximity queries
    - Search term highlighting
    - Multi-workspace support
    - Stemming and stop word filtering
    """

    def __init__(self, index_name: str, data_path: str, config: Dict[str, Any]):
        super().__init__(index_name, data_path, config)

        self.connection = None
        self.db_path = self.data_path / f"{index_name}_fts.db"
        self.initialized_workspaces = set()

        # Configuration
        self.enable_stemming = config.get('enable_stemming', True)
        self.remove_diacritics = config.get('remove_diacritics', True)
        self.max_results = config.get('max_results', 100)
        self.highlight_tags = config.get('highlight_tags', ['<mark>', '</mark>'])

    async def initialize(self) -> bool:
        """Initialize SQLite FTS5 connection and create base schema."""
        try:
            # Create data directory
            self.data_path.mkdir(parents=True, exist_ok=True)

            # Connect to SQLite
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row  # Enable column access by name

            # Check FTS5 availability
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA compile_options")
            compile_options = [row[0] for row in cursor.fetchall()]

            if not any('FTS5' in option for option in compile_options):
                self.logger.error("SQLite FTS5 not available")
                return False

            self.logger.info(f"SQLite FTS5 index initialized at {self.db_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite FTS5: {e}")
            return False

    async def shutdown(self):
        """Gracefully shutdown the FTS index."""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
                self.initialized_workspaces.clear()
                self.logger.info("FTS index shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during FTS index shutdown: {e}")

    async def insert(self, documents: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Insert documents into the FTS index."""
        if not self.connection:
            raise RuntimeError("FTS index not initialized")

        workspace = self._validate_workspace(workspace)
        prepared_docs = self._prepare_documents(documents)

        if not prepared_docs:
            return {"status": "error", "message": "No valid documents to insert"}

        start_time = datetime.now()

        try:
            # Ensure workspace table exists
            await self._ensure_workspace_table(workspace)

            # Prepare insert data
            table_name = self._get_table_name(workspace)
            cursor = self.connection.cursor()

            insert_sql = f"""
                INSERT INTO {table_name}
                (id, title, content, author, tags, metadata, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            insert_data = []
            for doc in prepared_docs:
                row = (
                    doc['id'],
                    doc.get('title', ''),
                    self._extract_searchable_content(doc),
                    doc.get('author', ''),
                    self._format_tags(doc.get('tags', [])),
                    json.dumps(self._extract_metadata(doc)),
                    doc.get('_indexed_at', datetime.now().isoformat())
                )
                insert_data.append(row)

            cursor.executemany(insert_sql, insert_data)
            self.connection.commit()

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            self.logger.info(f"Inserted {len(prepared_docs)} documents into FTS index")

            return {
                "status": "success",
                "documents_inserted": len(prepared_docs),
                "execution_time": execution_time,
                "workspace": workspace
            }

        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"FTS insert failed: {e}")
            return {"status": "error", "message": str(e)}

    async def update(self, document_updates: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Update existing documents in the FTS index."""
        if not self.connection:
            raise RuntimeError("FTS index not initialized")

        workspace = self._validate_workspace(workspace)
        start_time = datetime.now()

        try:
            await self._ensure_workspace_table(workspace)
            table_name = self._get_table_name(workspace)
            cursor = self.connection.cursor()
            updated_count = 0

            for update in document_updates:
                if 'id' not in update:
                    self.logger.warning("Skipping update without document ID")
                    continue

                # Check if document exists
                cursor.execute(f"SELECT id FROM {table_name} WHERE id = ?", (update['id'],))
                if not cursor.fetchone():
                    self.logger.warning(f"Document {update['id']} not found for update")
                    continue

                # Update document
                update_sql = f"""
                    UPDATE {table_name}
                    SET title = ?, content = ?, author = ?, tags = ?, metadata = ?
                    WHERE id = ?
                """

                update_data = (
                    update.get('title', ''),
                    self._extract_searchable_content(update),
                    update.get('author', ''),
                    self._format_tags(update.get('tags', [])),
                    json.dumps(self._extract_metadata(update)),
                    update['id']
                )

                cursor.execute(update_sql, update_data)
                if cursor.rowcount > 0:
                    updated_count += 1

            self.connection.commit()

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            return {
                "status": "success",
                "documents_updated": updated_count,
                "execution_time": execution_time
            }

        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"FTS update failed: {e}")
            return {"status": "error", "message": str(e)}

    async def delete(self, document_ids: List[str], workspace: str = "default") -> Dict[str, Any]:
        """Delete documents from the FTS index."""
        if not self.connection:
            raise RuntimeError("FTS index not initialized")

        workspace = self._validate_workspace(workspace)
        start_time = datetime.now()

        try:
            await self._ensure_workspace_table(workspace)
            table_name = self._get_table_name(workspace)
            cursor = self.connection.cursor()

            # Create placeholders for IN clause
            placeholders = ', '.join(['?' for _ in document_ids])
            delete_sql = f"DELETE FROM {table_name} WHERE id IN ({placeholders})"

            cursor.execute(delete_sql, document_ids)
            deleted_count = cursor.rowcount
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
            self.logger.error(f"FTS delete failed: {e}")
            return {"status": "error", "message": str(e)}

    async def query(self, query_params: Dict[str, Any], workspace: str = "default") -> QueryResult:
        """Execute full-text search query."""
        if not self.connection:
            raise RuntimeError("FTS index not initialized")

        workspace = self._validate_workspace(workspace)
        start_time = datetime.now()

        try:
            await self._ensure_workspace_table(workspace)
            table_name = self._get_table_name(workspace)

            # Extract query parameters
            search_text = query_params.get('query', query_params.get('text', ''))
            limit = query_params.get('limit', self.max_results)
            enable_highlighting = query_params.get('highlight', True)
            search_fields = query_params.get('fields', ['content', 'title'])

            if not search_text:
                raise ValueError("Search text required for FTS query")

            # Build FTS query
            fts_query = self._build_fts_query(search_text, search_fields)

            # Build SQL query
            select_fields = [
                "id", "title", "author", "tags", "metadata", "indexed_at"
            ]

            if enable_highlighting:
                # Add highlighted content
                highlight_sql = f"highlight({table_name}, 2, '{self.highlight_tags[0]}', '{self.highlight_tags[1]}') as highlighted_content"
                select_fields.append(highlight_sql)
                select_fields.append(f"bm25({table_name}) as relevance_score")
            else:
                select_fields.append("content")
                select_fields.append(f"bm25({table_name}) as relevance_score")

            sql = f"""
                SELECT {', '.join(select_fields)}
                FROM {table_name}
                WHERE {table_name} MATCH ?
                ORDER BY bm25({table_name})
                LIMIT ?
            """

            cursor = self.connection.cursor()
            cursor.execute(sql, (fts_query, limit))
            rows = cursor.fetchall()

            # Format results
            documents = []
            confidence_scores = []

            for row in rows:
                doc = dict(row)

                # Parse JSON fields
                if 'metadata' in doc and doc['metadata']:
                    try:
                        doc['metadata'] = json.loads(doc['metadata'])
                    except Exception:
                        doc['metadata'] = {}

                if 'tags' in doc and doc['tags']:
                    try:
                        doc['tags'] = doc['tags'].split(',')
                    except Exception:
                        doc['tags'] = []

                # Convert BM25 score to confidence (0-1)
                bm25_score = doc.get('relevance_score', 0)
                confidence = self._bm25_to_confidence(bm25_score)
                confidence_scores.append(confidence)

                documents.append(doc)

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            return QueryResult(
                documents=documents,
                metadata={
                    "fts_query": fts_query,
                    "search_fields": search_fields,
                    "highlighting_enabled": enable_highlighting,
                    "workspace": workspace
                },
                total_found=len(documents),
                execution_time=execution_time,
                index_used=self.index_name,
                confidence_scores=confidence_scores
            )

        except Exception as e:
            self.logger.error(f"FTS query failed: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check FTS index health."""
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

            # Check FTS5 extension
            cursor.execute("PRAGMA compile_options")
            compile_options = [row[0] for row in cursor.fetchall()]
            if any('FTS5' in option for option in compile_options):
                health_data["checks"]["fts5_extension"] = "available"
            else:
                health_data["checks"]["fts5_extension"] = "unavailable"

            # Check database file
            if self.db_path.exists():
                size_mb = self.db_path.stat().st_size / (1024 * 1024)
                health_data["checks"]["database_file"] = f"healthy ({size_mb:.1f}MB)"
            else:
                health_data["checks"]["database_file"] = "missing"

            # Check workspaces
            health_data["checks"]["workspaces"] = f"{len(self.initialized_workspaces)} initialized"

            # Overall status
            if (health_data["checks"]["sqlite_connection"] == "healthy" and
                health_data["checks"]["fts5_extension"] == "available"):
                health_data["status"] = "healthy"

        except Exception as e:
            health_data["checks"]["error"] = str(e)

        return health_data

    def get_capabilities(self) -> Set[IndexCapabilities]:
        """Return supported capabilities."""
        return {
            IndexCapabilities.FULL_TEXT_SEARCH,
            IndexCapabilities.FUZZY_MATCHING,
            IndexCapabilities.EXACT_MATCH
        }

    async def optimize(self) -> Dict[str, Any]:
        """Optimize FTS index performance."""
        try:
            optimization_results = {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "optimizations": []
            }

            if not self.connection:
                return {"status": "failed", "error": "Database not connected"}

            cursor = self.connection.cursor()

            # Optimize each workspace table
            for workspace in self.initialized_workspaces:
                table_name = self._get_table_name(workspace)

                try:
                    # Run FTS5 optimize
                    cursor.execute(f"INSERT INTO {table_name}({table_name}) VALUES('optimize')")
                    optimization_results["optimizations"].append({
                        "workspace": workspace,
                        "action": "fts_optimize_completed"
                    })

                    # Analyze table
                    cursor.execute(f"ANALYZE {table_name}")
                    optimization_results["optimizations"].append({
                        "workspace": workspace,
                        "action": "table_analyzed"
                    })

                except Exception as e:
                    optimization_results["optimizations"].append({
                        "workspace": workspace,
                        "action": "optimization_failed",
                        "error": str(e)
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
        """Get comprehensive FTS index statistics."""
        try:
            total_documents = 0

            if self.connection:
                cursor = self.connection.cursor()

                # Count documents across all workspaces
                for workspace in self.initialized_workspaces:
                    try:
                        table_name = self._get_table_name(workspace)
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
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
            self.logger.error(f"Failed to get FTS index stats: {e}")
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
        """Ensure workspace FTS table exists."""
        if workspace in self.initialized_workspaces:
            return

        table_name = self._get_table_name(workspace)

        # Build FTS5 options
        fts_options = []
        if self.enable_stemming:
            fts_options.append("tokenize='porter'")
        # Note: remove_diacritics is not available in all SQLite FTS5 builds
        # if self.remove_diacritics:
        #     fts_options.append("remove_diacritics=1")

        options_str = ", " + ", ".join(fts_options) if fts_options else ""

        # Create FTS5 virtual table
        create_sql = f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {table_name} USING fts5(
                id UNINDEXED,
                title,
                content,
                author,
                tags,
                metadata UNINDEXED,
                indexed_at UNINDEXED{options_str}
            )
        """

        cursor = self.connection.cursor()
        cursor.execute(create_sql)
        self.connection.commit()

        self.initialized_workspaces.add(workspace)

    def _get_table_name(self, workspace: str) -> str:
        """Get FTS table name for workspace."""
        return f"fts_{workspace.replace('-', '_')}"

    def _extract_searchable_content(self, document: Dict[str, Any]) -> str:
        """Extract searchable content from document."""
        content_fields = ['content', 'text', 'description', 'summary', 'body']

        parts = []
        for field in content_fields:
            if field in document and document[field]:
                parts.append(str(document[field]))

        return ' '.join(parts) if parts else ''

    def _format_tags(self, tags: Any) -> str:
        """Format tags for FTS storage."""
        if isinstance(tags, list):
            return ','.join(str(tag) for tag in tags)
        elif isinstance(tags, str):
            return tags
        return ''

    def _extract_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for storage."""
        excluded_fields = {'id', 'title', 'content', 'text', 'author', 'tags'}
        return {k: v for k, v in document.items()
                if k not in excluded_fields and not k.startswith('_')}

    def _build_fts_query(self, search_text: str, search_fields: List[str]) -> str:
        """Build FTS5 query from search text and fields."""
        # Clean and prepare search text
        search_text = search_text.strip()

        # Handle phrase searches (quoted text)
        if search_text.startswith('"') and search_text.endswith('"'):
            return search_text

        # Handle proximity searches (NEAR operator)
        if ' NEAR ' in search_text.upper():
            return search_text

        # Split into terms and build query
        terms = re.findall(r'\w+', search_text.lower())

        if not terms:
            return search_text

        # Build field-specific query if specified
        if search_fields and len(search_fields) < 3:  # Optimize for specific fields
            field_queries = []
            for field in search_fields:
                if field in ['title', 'content', 'author', 'tags']:
                    field_queries.append(f"{field}: {' '.join(terms)}")

            if field_queries:
                return ' OR '.join(field_queries)

        # Default: search all terms
        return ' '.join(terms)

    def _bm25_to_confidence(self, bm25_score: float) -> float:
        """Convert BM25 score to confidence score (0-1)."""
        # BM25 scores are typically negative (lower is better)
        # Convert to positive confidence score
        if bm25_score >= 0:
            return 0.1  # Very low confidence for positive scores

        # Normalize negative BM25 score to 0-1 range
        # Typical BM25 scores range from 0 to -20+
        normalized = min(abs(bm25_score) / 20.0, 1.0)
        return normalized