"""
Kùzu Graph Database Index Implementation

This module provides graph-based indexing using Kùzu for relationship modeling,
entity extraction, and graph traversal queries. Supports zero-cost local deployment
with high-performance graph operations.
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime
import hashlib

import kuzu

# Import existing components
import sys
from pathlib import Path as PathLib
sys.path.append(str(PathLib(__file__).parent.parent.parent))
from ollama_config import ollama_config

from .base import IndexInterface, IndexCapabilities, QueryResult, IndexStats, IndexNotInitializedError

logger = logging.getLogger(__name__)

class GraphIndex(IndexInterface):
    """
    Kùzu-based graph database for entity relationships and graph traversal.

    Features:
    - Automatic entity extraction from documents
    - Relationship modeling and storage
    - Graph traversal queries (BFS, DFS, shortest path)
    - Zero-cost local deployment
    - Integration with existing multi-index system
    """

    def __init__(self, index_name: str, data_path: str, config: Dict[str, Any]):
        """Initialize the Kùzu graph index."""
        super().__init__(index_name, data_path, config)

        self.db_path = Path(data_path) / "kuzu_db"
        self.db: Optional[kuzu.Database] = None
        self.connection: Optional[kuzu.Connection] = None

        # Entity extraction configuration
        self.entity_extraction_model = config.get('entity_model', 'qwen2.5:3b')
        self.max_entities_per_doc = config.get('max_entities', 50)
        self.min_entity_confidence = config.get('min_confidence', 0.7)

        # Graph schema
        self.entity_types = {
            'Document', 'Person', 'Organization', 'Location', 'Concept', 'Event', 'Product'
        }
        self.relationship_types = {
            'CONTAINS', 'MENTIONS', 'RELATED_TO', 'LOCATED_IN', 'WORKS_FOR',
            'PART_OF', 'DESCRIBES', 'REFERENCES', 'CREATED_BY', 'OCCURRED_IN'
        }

        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize Kùzu database and create schema."""
        try:
            # Create parent directory but not the database path itself
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove if exists as directory (Kùzu expects file path)
            if self.db_path.exists() and self.db_path.is_dir():
                import shutil
                shutil.rmtree(self.db_path)

            # Initialize Kùzu database
            self.db = kuzu.Database(str(self.db_path))
            self.connection = kuzu.Connection(self.db)

            # Create graph schema
            await self._create_schema()

            self.initialized = True
            self.logger.info(f"Kùzu graph database initialized at {self.db_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Kùzu database: {e}")
            return False

    async def shutdown(self):
        """Shutdown Kùzu database connections."""
        try:
            if self.connection:
                self.connection.close()
            if self.db:
                self.db.close()
            self.initialized = False
            self.logger.info("Kùzu graph database shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during Kùzu shutdown: {e}")

    async def _create_schema(self):
        """Create node and relationship tables in Kùzu."""
        try:
            # Create node table for entities
            entity_schema = """
            CREATE NODE TABLE IF NOT EXISTS Entity(
                id STRING PRIMARY KEY,
                name STRING,
                type STRING,
                workspace STRING,
                confidence DOUBLE,
                properties MAP(STRING, STRING),
                created_at TIMESTAMP,
                document_id STRING
            )
            """
            self.connection.execute(entity_schema)

            # Create node table for documents
            document_schema = """
            CREATE NODE TABLE IF NOT EXISTS Document(
                id STRING PRIMARY KEY,
                title STRING,
                content STRING,
                workspace STRING,
                created_at TIMESTAMP,
                metadata MAP(STRING, STRING)
            )
            """
            self.connection.execute(document_schema)

            # Create relationship table
            relationship_schema = """
            CREATE REL TABLE IF NOT EXISTS Relationship(
                FROM Entity TO Entity,
                type STRING,
                confidence DOUBLE,
                workspace STRING,
                properties MAP(STRING, STRING),
                created_at TIMESTAMP
            )
            """
            self.connection.execute(relationship_schema)

            # Create document-entity relationship
            contains_schema = """
            CREATE REL TABLE IF NOT EXISTS Contains(
                FROM Document TO Entity,
                position INTEGER,
                context STRING,
                created_at TIMESTAMP
            )
            """
            self.connection.execute(contains_schema)

            self.logger.info("Kùzu graph schema created successfully")

        except Exception as e:
            self.logger.error(f"Failed to create Kùzu schema: {e}")
            raise

    async def insert(self, documents: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Insert documents and extract entities/relationships."""
        if not self.initialized:
            raise IndexNotInitializedError("Graph index not initialized")

        workspace = self._validate_workspace(workspace)
        prepared_docs = self._prepare_documents(documents)

        start_time = datetime.now()
        entities_created = 0
        relationships_created = 0
        documents_processed = 0

        try:
            for doc in prepared_docs:
                # Insert document node
                await self._insert_document_node(doc, workspace)

                # Extract entities from document
                entities = await self._extract_entities(doc)

                # Insert entity nodes and relationships
                doc_entities = []
                for entity in entities:
                    entity_id = await self._insert_entity_node(entity, doc['id'], workspace)
                    if entity_id:
                        doc_entities.append(entity_id)
                        entities_created += 1

                # Create relationships between entities in the same document
                relationships = await self._create_entity_relationships(doc_entities, doc, workspace)
                relationships_created += len(relationships)

                # Link document to entities
                await self._link_document_entities(doc['id'], doc_entities, workspace)

                documents_processed += 1

            execution_time = (datetime.now() - start_time).total_seconds()
            self._track_query_performance(execution_time)

            return {
                'status': 'success',
                'documents_processed': documents_processed,
                'entities_created': entities_created,
                'relationships_created': relationships_created,
                'execution_time': execution_time,
                'workspace': workspace
            }

        except Exception as e:
            self.logger.error(f"Graph insertion failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'documents_processed': documents_processed
            }

    async def _extract_entities(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities from document using local LLM."""
        try:
            text = document.get('content', '') or document.get('text', '')
            if not text:
                return []

            # Construct entity extraction prompt
            prompt = f"""Extract named entities from the following text. Return a JSON list of entities with this format:
[{{"name": "entity name", "type": "Person|Organization|Location|Concept|Event|Product", "confidence": 0.0-1.0}}]

Only extract clear, unambiguous entities. Types:
- Person: People's names
- Organization: Companies, institutions, groups
- Location: Places, cities, countries
- Concept: Ideas, technologies, methods
- Event: Specific events, meetings, incidents
- Product: Products, services, tools

Text: {text[:1000]}

JSON:"""

            messages = [{"role": "user", "content": prompt}]
            result = ollama_config.chat_response(self.entity_extraction_model, messages)

            if result['success']:
                response_text = result['data']['message']['content'].strip()

                # Extract JSON from response
                try:
                    # Find JSON array in response
                    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                    if json_match:
                        entities_json = json_match.group(0)
                        entities = json.loads(entities_json)

                        # Filter by confidence
                        filtered_entities = [
                            entity for entity in entities
                            if isinstance(entity, dict) and
                               entity.get('confidence', 0) >= self.min_entity_confidence and
                               entity.get('name') and entity.get('type')
                        ]

                        return filtered_entities[:self.max_entities_per_doc]

                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse entities JSON: {e}")

            return []

        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            return []

    async def _insert_document_node(self, document: Dict[str, Any], workspace: str):
        """Insert document as a node in the graph."""
        query = """
        CREATE (d:Document {
            id: $id,
            title: $title,
            content: $content,
            workspace: $workspace,
            created_at: $created_at,
            metadata: $metadata
        })
        """

        metadata_map = {k: str(v) for k, v in document.get('metadata', {}).items()}

        params = {
            'id': document['id'],
            'title': document.get('title', ''),
            'content': document.get('content', document.get('text', ''))[:1000],  # Truncate long content
            'workspace': workspace,
            'created_at': document.get('_indexed_at', datetime.now().isoformat()),
            'metadata': metadata_map
        }

        self.connection.execute(query, params)

    async def _insert_entity_node(self, entity: Dict[str, Any], document_id: str, workspace: str) -> Optional[str]:
        """Insert entity as a node in the graph."""
        try:
            entity_id = f"{workspace}_{entity['type']}_{hashlib.md5(entity['name'].encode()).hexdigest()[:8]}"

            query = """
            MERGE (e:Entity {id: $id})
            ON CREATE SET
                e.name = $name,
                e.type = $type,
                e.workspace = $workspace,
                e.confidence = $confidence,
                e.created_at = $created_at,
                e.document_id = $document_id
            ON MATCH SET
                e.confidence = CASE WHEN $confidence > e.confidence THEN $confidence ELSE e.confidence END
            """

            params = {
                'id': entity_id,
                'name': entity['name'],
                'type': entity['type'],
                'workspace': workspace,
                'confidence': entity.get('confidence', 0.8),
                'created_at': datetime.now().isoformat(),
                'document_id': document_id
            }

            self.connection.execute(query, params)
            return entity_id

        except Exception as e:
            self.logger.error(f"Failed to insert entity {entity.get('name', 'unknown')}: {e}")
            return None

    async def _create_entity_relationships(self, entity_ids: List[str], document: Dict[str, Any], workspace: str) -> List[str]:
        """Create relationships between entities in the same document."""
        relationships = []

        try:
            # Create relationships between entities that appear in the same document
            for i, entity1_id in enumerate(entity_ids):
                for entity2_id in entity_ids[i+1:]:
                    relationship_id = f"rel_{entity1_id}_{entity2_id}"

                    query = """
                    MATCH (e1:Entity {id: $entity1_id}), (e2:Entity {id: $entity2_id})
                    MERGE (e1)-[r:Relationship]->(e2)
                    ON CREATE SET
                        r.type = $rel_type,
                        r.confidence = $confidence,
                        r.workspace = $workspace,
                        r.created_at = $created_at
                    """

                    params = {
                        'entity1_id': entity1_id,
                        'entity2_id': entity2_id,
                        'rel_type': 'RELATED_TO',  # Default relationship type
                        'confidence': 0.6,  # Default confidence for co-occurrence
                        'workspace': workspace,
                        'created_at': datetime.now().isoformat()
                    }

                    self.connection.execute(query, params)
                    relationships.append(relationship_id)

        except Exception as e:
            self.logger.error(f"Failed to create entity relationships: {e}")

        return relationships

    async def _link_document_entities(self, document_id: str, entity_ids: List[str], workspace: str):
        """Link document to its extracted entities."""
        try:
            for i, entity_id in enumerate(entity_ids):
                query = """
                MATCH (d:Document {id: $doc_id}), (e:Entity {id: $entity_id})
                MERGE (d)-[c:Contains]->(e)
                ON CREATE SET
                    c.position = $position,
                    c.created_at = $created_at
                """

                params = {
                    'doc_id': document_id,
                    'entity_id': entity_id,
                    'position': i,
                    'created_at': datetime.now().isoformat()
                }

                self.connection.execute(query, params)

        except Exception as e:
            self.logger.error(f"Failed to link document entities: {e}")

    async def update(self, document_updates: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Update documents in the graph (re-extract entities)."""
        # For simplicity, we'll delete and re-insert
        doc_ids = [doc['id'] for doc in document_updates if 'id' in doc]
        await self.delete(doc_ids, workspace)
        return await self.insert(document_updates, workspace)

    async def delete(self, document_ids: List[str], workspace: str = "default") -> Dict[str, Any]:
        """Delete documents and their entities from the graph."""
        if not self.initialized:
            raise IndexNotInitializedError("Graph index not initialized")

        workspace = self._validate_workspace(workspace)
        deleted_docs = 0
        deleted_entities = 0

        try:
            for doc_id in document_ids:
                # Delete document and its relationships
                delete_query = """
                MATCH (d:Document {id: $doc_id, workspace: $workspace})
                OPTIONAL MATCH (d)-[:Contains]->(e:Entity)
                DETACH DELETE d, e
                """

                result = self.connection.execute(delete_query, {
                    'doc_id': doc_id,
                    'workspace': workspace
                })

                deleted_docs += 1

            return {
                'status': 'success',
                'deleted_documents': deleted_docs,
                'workspace': workspace
            }

        except Exception as e:
            self.logger.error(f"Graph deletion failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'deleted_documents': deleted_docs
            }

    async def query(self, query_params: Dict[str, Any], workspace: str = "default") -> QueryResult:
        """Execute graph queries (entity search, relationship traversal)."""
        if not self.initialized:
            raise IndexNotInitializedError("Graph index not initialized")

        start_time = datetime.now()
        workspace = self._validate_workspace(workspace)

        try:
            query_type = query_params.get('type', 'entity_search')

            if query_type == 'entity_search':
                return await self._entity_search_query(query_params, workspace, start_time)
            elif query_type == 'relationship_traversal':
                return await self._relationship_traversal_query(query_params, workspace, start_time)
            elif query_type == 'path_finding':
                return await self._path_finding_query(query_params, workspace, start_time)
            else:
                raise ValueError(f"Unsupported query type: {query_type}")

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Graph query failed: {e}")
            return QueryResult(
                documents=[],
                metadata={'error': str(e)},
                total_found=0,
                execution_time=execution_time,
                index_used=self.index_name
            )

    async def _entity_search_query(self, query_params: Dict[str, Any], workspace: str, start_time: datetime) -> QueryResult:
        """Search for entities by name or type."""
        entity_name = query_params.get('entity_name', '')
        entity_type = query_params.get('entity_type', '')
        limit = query_params.get('limit', 10)

        query = """
        MATCH (e:Entity)
        WHERE e.workspace = $workspace
        """

        params = {'workspace': workspace}

        if entity_name:
            query += " AND e.name CONTAINS $entity_name"
            params['entity_name'] = entity_name

        if entity_type:
            query += " AND e.type = $entity_type"
            params['entity_type'] = entity_type

        query += f" RETURN e LIMIT {limit}"

        result = self.connection.execute(query, params)
        entities = result.get_as_df().to_dict('records') if result else []

        execution_time = (datetime.now() - start_time).total_seconds()
        self._track_query_performance(execution_time)

        return QueryResult(
            documents=entities,
            metadata={'query_type': 'entity_search', 'workspace': workspace},
            total_found=len(entities),
            execution_time=execution_time,
            index_used=self.index_name
        )

    async def _relationship_traversal_query(self, query_params: Dict[str, Any], workspace: str, start_time: datetime) -> QueryResult:
        """Traverse relationships from a starting entity."""
        start_entity = query_params.get('start_entity', '')
        max_depth = query_params.get('max_depth', 3)
        relationship_type = query_params.get('relationship_type', '')

        query = f"""
        MATCH path = (start:Entity {{name: $start_entity, workspace: $workspace}})
        -[r:Relationship*1..{max_depth}]->(end:Entity)
        """

        params = {
            'start_entity': start_entity,
            'workspace': workspace
        }

        if relationship_type:
            query = query.replace('r:Relationship', f'r:Relationship {{type: $rel_type}}')
            params['rel_type'] = relationship_type

        query += " RETURN path"

        result = self.connection.execute(query, params)
        paths = result.get_as_df().to_dict('records') if result else []

        execution_time = (datetime.now() - start_time).total_seconds()
        self._track_query_performance(execution_time)

        return QueryResult(
            documents=paths,
            metadata={'query_type': 'relationship_traversal', 'workspace': workspace},
            total_found=len(paths),
            execution_time=execution_time,
            index_used=self.index_name
        )

    async def _path_finding_query(self, query_params: Dict[str, Any], workspace: str, start_time: datetime) -> QueryResult:
        """Find shortest path between two entities."""
        start_entity = query_params.get('start_entity', '')
        end_entity = query_params.get('end_entity', '')

        query = """
        MATCH path = shortestPath(
            (start:Entity {name: $start_entity, workspace: $workspace})
            -[*]->
            (end:Entity {name: $end_entity, workspace: $workspace})
        )
        RETURN path
        """

        params = {
            'start_entity': start_entity,
            'end_entity': end_entity,
            'workspace': workspace
        }

        result = self.connection.execute(query, params)
        paths = result.get_as_df().to_dict('records') if result else []

        execution_time = (datetime.now() - start_time).total_seconds()
        self._track_query_performance(execution_time)

        return QueryResult(
            documents=paths,
            metadata={'query_type': 'path_finding', 'workspace': workspace},
            total_found=len(paths),
            execution_time=execution_time,
            index_used=self.index_name
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check Kùzu database health."""
        try:
            if not self.initialized or not self.connection:
                return {
                    'status': 'unhealthy',
                    'message': 'Database not initialized',
                    'metrics': {}
                }

            # Test query
            result = self.connection.execute("MATCH (n) RETURN count(n) as node_count")
            node_count = result.get_as_df().iloc[0]['node_count'] if result else 0

            return {
                'status': 'healthy',
                'message': 'Kùzu database operational',
                'metrics': {
                    'node_count': node_count,
                    'avg_query_time': self.get_avg_query_time(),
                    'total_queries': self.query_count
                }
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Health check failed: {e}',
                'metrics': {}
            }

    def get_capabilities(self) -> Set[IndexCapabilities]:
        """Get graph index capabilities."""
        return {
            IndexCapabilities.GRAPH_TRAVERSAL,
            IndexCapabilities.EXACT_MATCH,
            IndexCapabilities.FUZZY_MATCHING
        }

    async def optimize(self) -> Dict[str, Any]:
        """Optimize graph database (rebuild indices, clean up orphaned nodes)."""
        try:
            # Remove orphaned entities (not connected to any document)
            cleanup_query = """
            MATCH (e:Entity)
            WHERE NOT (e)<-[:Contains]-(:Document)
            DETACH DELETE e
            """
            self.connection.execute(cleanup_query)

            return {
                'status': 'success',
                'message': 'Graph optimization completed',
                'optimizations': ['removed_orphaned_entities']
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Optimization failed: {e}'
            }

    async def get_stats(self) -> IndexStats:
        """Get comprehensive graph statistics."""
        try:
            # Count nodes and relationships
            node_result = self.connection.execute("MATCH (n) RETURN count(n) as count")
            node_count = node_result.get_as_df().iloc[0]['count'] if node_result else 0

            rel_result = self.connection.execute("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.get_as_df().iloc[0]['count'] if rel_result else 0

            # Estimate storage size (approximation)
            storage_size = (node_count + rel_count) * 1024  # Rough estimate

            return IndexStats(
                document_count=node_count,
                storage_size_bytes=storage_size,
                avg_query_time=self.get_avg_query_time(),
                total_queries=self.query_count,
                last_updated=datetime.now(),
                health_status='healthy' if self.initialized else 'unhealthy',
                capabilities=self.get_capabilities()
            )

        except Exception as e:
            self.logger.error(f"Failed to get graph stats: {e}")
            return IndexStats(
                document_count=0,
                storage_size_bytes=0,
                avg_query_time=0.0,
                total_queries=self.query_count,
                last_updated=datetime.now(),
                health_status='unhealthy',
                capabilities=self.get_capabilities()
            )