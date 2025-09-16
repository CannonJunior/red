"""
Knowledge Graph Builder for Vector Data

Creates proper knowledge graphs from vector embeddings and content chunks,
extracting semantic concepts and relationships based on vector similarity.
"""

import numpy as np
from typing import Dict, List, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)


class VectorKnowledgeGraphBuilder:
    """
    Builds knowledge graphs from vector embeddings and content chunks.

    Extracts:
    - Semantic concepts from text content
    - Content clusters based on vector similarity
    - Relationships between concepts and chunks
    """

    def __init__(self):
        self.similarity_threshold = 0.7
        self.concept_min_frequency = 2

    def build_knowledge_graph_from_vectors(self, chunks_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a knowledge graph from vector chunks data.

        Args:
            chunks_data: Dictionary containing chunks, embeddings, and metadata

        Returns:
            Knowledge graph with entities and relationships
        """
        chunks = chunks_data.get('chunks', [])

        if not chunks:
            return {
                "entities": [],
                "relationships": [],
                "metadata": {
                    "total_entities": 0,
                    "total_relationships": 0,
                    "message": "No vector chunks available for knowledge graph creation",
                    "data_source": "Vector Embeddings"
                }
            }

        try:
            # Extract semantic concepts from content
            concepts = self._extract_semantic_concepts(chunks)

            # Create content cluster entities based on vector similarity
            clusters = self._create_content_clusters(chunks)

            # Create document source entities
            sources = self._create_source_entities(chunks)

            # Combine all entities
            all_entities = concepts + clusters + sources

            # Create relationships
            relationships = self._create_relationships(chunks, concepts, clusters, sources)

            return {
                "entities": all_entities,
                "relationships": relationships,
                "metadata": {
                    "total_entities": len(all_entities),
                    "total_relationships": len(relationships),
                    "concept_count": len(concepts),
                    "cluster_count": len(clusters),
                    "source_count": len(sources),
                    "chunk_count": len(chunks),
                    "data_source": "Vector Embeddings + Semantic Analysis",
                    "extraction_method": "vector_similarity + concept_extraction"
                }
            }

        except Exception as e:
            logger.error(f"Knowledge graph building failed: {e}")
            return {
                "entities": [],
                "relationships": [],
                "metadata": {
                    "total_entities": 0,
                    "total_relationships": 0,
                    "error": f"Knowledge graph building failed: {e}",
                    "data_source": "Vector Embeddings"
                }
            }

    def _extract_semantic_concepts(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract semantic concepts from chunk content."""
        concepts = []
        all_text = " ".join(chunk.get('text', '') for chunk in chunks)

        # Extract key terms using simple NLP techniques
        # Remove common stop words and extract meaningful terms
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', all_text)  # Capitalized phrases
        words.extend(re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', all_text))  # snake_case terms
        words.extend(re.findall(r'\b[A-Z]{2,}\b', all_text))  # Acronyms

        # Count frequency and filter
        word_counts = Counter(words)

        concept_id = 0
        for word, count in word_counts.items():
            if count >= self.concept_min_frequency and len(word) > 2:
                concepts.append({
                    "id": f"concept_{concept_id}",
                    "name": word,
                    "type": "CONCEPT",
                    "confidence": min(count / len(chunks), 1.0),  # Normalized frequency
                    "frequency": count,
                    "metadata": {
                        "extraction_method": "frequency_analysis",
                        "term_type": self._classify_term(word)
                    }
                })
                concept_id += 1

        # Sort by confidence and take top concepts
        concepts.sort(key=lambda x: x['confidence'], reverse=True)
        return concepts[:20]  # Limit to top 20 concepts

    def _classify_term(self, term: str) -> str:
        """Classify extracted terms by type."""
        if term.isupper() and len(term) >= 2:
            return "acronym"
        elif '_' in term:
            return "technical_term"
        elif term[0].isupper():
            return "proper_noun"
        else:
            return "general_term"

    def _create_content_clusters(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create content clusters based on vector similarity."""
        if len(chunks) < 2:
            return []

        # Extract embeddings
        embeddings = []
        valid_chunks = []

        for chunk in chunks:
            embedding = chunk.get('embedding')
            if embedding is not None and len(embedding) > 0:
                embeddings.append(embedding)
                valid_chunks.append(chunk)

        if len(embeddings) < 2:
            return []

        try:
            embeddings_array = np.array(embeddings)

            # Determine optimal number of clusters (max 5, min 2)
            n_clusters = min(max(len(embeddings) // 3, 2), 5)

            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(embeddings_array)

            # Create cluster entities
            clusters = []
            for cluster_id in range(n_clusters):
                cluster_chunks = [chunk for i, chunk in enumerate(valid_chunks) if cluster_labels[i] == cluster_id]

                if cluster_chunks:
                    # Generate cluster name from content
                    cluster_name = self._generate_cluster_name(cluster_chunks)

                    clusters.append({
                        "id": f"cluster_{cluster_id}",
                        "name": cluster_name,
                        "type": "CONTENT_CLUSTER",
                        "confidence": len(cluster_chunks) / len(valid_chunks),
                        "metadata": {
                            "chunk_count": len(cluster_chunks),
                            "cluster_method": "kmeans",
                            "representative_sources": list(set(chunk.get('source', 'unknown') for chunk in cluster_chunks))[:3]
                        }
                    })

            return clusters

        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return []

    def _generate_cluster_name(self, cluster_chunks: List[Dict[str, Any]]) -> str:
        """Generate a descriptive name for a cluster based on its content."""
        # Combine text from all chunks in cluster
        cluster_text = " ".join(chunk.get('text', '') for chunk in cluster_chunks)

        # Extract key terms
        words = re.findall(r'\b[A-Za-z]+\b', cluster_text.lower())
        word_counts = Counter(words)

        # Get most common meaningful words
        common_words = [word for word, count in word_counts.most_common(5)
                       if len(word) > 3 and word not in {'this', 'that', 'with', 'from', 'they', 'have', 'will', 'been', 'were'}]

        if common_words:
            return f"Cluster: {', '.join(common_words[:2])}"
        else:
            return f"Content Cluster ({len(cluster_chunks)} chunks)"

    def _create_source_entities(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create entities representing document sources."""
        sources = {}

        for chunk in chunks:
            source = chunk.get('source', 'unknown')
            if source not in sources:
                # Extract filename
                import os
                filename = os.path.basename(source) if source != 'unknown' else 'Unknown Document'

                sources[source] = {
                    "id": f"source_{len(sources)}",
                    "name": filename,
                    "type": "DOCUMENT_SOURCE",
                    "confidence": 1.0,
                    "metadata": {
                        "source_path": source,
                        "file_type": chunk.get('file_type', 'unknown'),
                        "chunk_count": 0
                    }
                }

            sources[source]["metadata"]["chunk_count"] += 1

        return list(sources.values())

    def _create_relationships(self, chunks: List[Dict[str, Any]], concepts: List[Dict[str, Any]],
                            clusters: List[Dict[str, Any]], sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create relationships between entities."""
        relationships = []

        # Create concept-to-chunk relationships
        for concept in concepts:
            concept_name = concept['name'].lower()
            for chunk in chunks:
                chunk_text = chunk.get('text', '').lower()
                if concept_name in chunk_text:
                    # Find the source for this chunk
                    chunk_source = chunk.get('source', 'unknown')
                    source_entity = next((s for s in sources if s['metadata']['source_path'] == chunk_source), None)

                    if source_entity:
                        relationships.append({
                            "source": concept['id'],
                            "target": source_entity['id'],
                            "relationship": "MENTIONED_IN",
                            "weight": concept['confidence'] * 0.8,
                            "metadata": {
                                "relationship_type": "concept_to_document",
                                "chunk_id": chunk.get('id', 'unknown')
                            }
                        })

        # Create cluster-to-source relationships
        if len(chunks) >= 2:
            try:
                embeddings = [chunk.get('embedding') for chunk in chunks if chunk.get('embedding') is not None]
                if len(embeddings) >= 2:
                    embeddings_array = np.array(embeddings)
                    n_clusters = min(len(clusters), len(embeddings))

                    if n_clusters > 0:
                        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                        cluster_labels = kmeans.fit_predict(embeddings_array)

                        for i, chunk in enumerate(chunks):
                            if i < len(cluster_labels) and chunk.get('embedding') is not None:
                                cluster_id = cluster_labels[i]
                                if cluster_id < len(clusters):
                                    chunk_source = chunk.get('source', 'unknown')
                                    source_entity = next((s for s in sources if s['metadata']['source_path'] == chunk_source), None)

                                    if source_entity:
                                        relationships.append({
                                            "source": clusters[cluster_id]['id'],
                                            "target": source_entity['id'],
                                            "relationship": "CONTAINS_CONTENT_FROM",
                                            "weight": 0.7,
                                            "metadata": {
                                                "relationship_type": "cluster_to_document",
                                                "chunk_id": chunk.get('id', 'unknown')
                                            }
                                        })
            except Exception as e:
                logger.error(f"Failed to create cluster relationships: {e}")

        # Create concept-to-concept relationships based on co-occurrence
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                # Check if concepts co-occur in the same chunks
                co_occurrence_count = 0
                for chunk in chunks:
                    chunk_text = chunk.get('text', '').lower()
                    if concept1['name'].lower() in chunk_text and concept2['name'].lower() in chunk_text:
                        co_occurrence_count += 1

                if co_occurrence_count >= 1:
                    relationships.append({
                        "source": concept1['id'],
                        "target": concept2['id'],
                        "relationship": "CO_OCCURS_WITH",
                        "weight": min(co_occurrence_count / len(chunks), 1.0),
                        "metadata": {
                            "relationship_type": "concept_to_concept",
                            "co_occurrence_count": co_occurrence_count
                        }
                    })

        return relationships