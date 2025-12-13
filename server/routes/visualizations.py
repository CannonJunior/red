"""Visualization route handlers for knowledge graphs, dashboards, etc."""

from datetime import datetime
from debug_logger import debug_log
from server_decorators import require_system

try:
    from rag_api import handle_rag_analytics_request, handle_rag_search_request, handle_rag_vector_chunks_request
    from knowledge_graph_builder import VectorKnowledgeGraphBuilder
    KNOWLEDGE_GRAPH_AVAILABLE = True
except ImportError:
    KNOWLEDGE_GRAPH_AVAILABLE = False


def handle_knowledge_graph_api(handler):
    """Handle knowledge graph visualization API requests using vector embeddings."""
    try:
        if not KNOWLEDGE_GRAPH_AVAILABLE:
            handler.send_json_response({
                'error': 'RAG system or Knowledge Graph Builder not available',
                'entities': [],
                'relationships': []
            }, 503)
            return

        # Get vector chunks with embeddings from ChromaDB
        chunks_result = handle_rag_vector_chunks_request()

        if chunks_result.get('status') != 'success':
            handler.send_json_response({
                "entities": [],
                "relationships": [],
                "metadata": {
                    "total_entities": 0,
                    "total_relationships": 0,
                    "message": "No vector chunks available. Upload documents to create knowledge graph.",
                    "generated_at": datetime.now().isoformat()
                }
            })
            return

        # Build knowledge graph from vector data
        graph_builder = VectorKnowledgeGraphBuilder()
        graph_data = graph_builder.build_knowledge_graph_from_vectors(chunks_result)

        # Add timestamp to metadata
        graph_data["metadata"]["generated_at"] = datetime.now().isoformat()

        entity_count = len(graph_data.get("entities", []))
        relationship_count = len(graph_data.get("relationships", []))
        chunk_count = chunks_result.get('total_chunks', 0)

        debug_log(f"Vector-based knowledge graph: {entity_count} entities, {relationship_count} relationships from {chunk_count} vector chunks", "📊")
        handler.send_json_response(graph_data)

    except Exception as e:
        print(f"❌ Knowledge graph API error: {e}")
        handler.send_json_response({'error': f'Knowledge graph failed: {str(e)}'}, 500)


def handle_performance_dashboard_api(handler):
    """Handle performance dashboard API requests using real analytics data."""
    try:
        # Get real analytics from RAG system
        analytics_result = handle_rag_analytics_request()

        # Extract real metrics
        document_count = analytics_result.get('document_count', 0)
        chunk_count = analytics_result.get('chunk_count', 0)

        # Generate realistic metrics based on actual data
        metrics = {
            "total_documents": document_count,
            "total_chunks": chunk_count,
            "avg_chunks_per_doc": chunk_count / max(document_count, 1),
            "system_health": "healthy" if document_count > 0 else "no_data",
            "data_source": "ChromaDB",
            "embedding_model": "all-MiniLM-L6-v2",
            "last_updated": datetime.now().isoformat()
        }

        # Generate basic time series data (since we don't track query history yet)
        time_series = [
            {
                "timestamp": datetime.now().isoformat(),
                "document_count": document_count,
                "chunk_count": chunk_count,
                "system_status": "operational"
            }
        ]

        # Recommendations based on actual state
        recommendations = []
        if document_count == 0:
            recommendations.append("Upload documents to start using the knowledge base")
        elif document_count < 5:
            recommendations.append("Consider adding more documents for better search results")
        else:
            recommendations.append("Knowledge base is well-populated and ready for queries")

        if chunk_count > 0:
            recommendations.append(f"Vector database contains {chunk_count} searchable chunks")

        dashboard_data = {
            "metrics": metrics,
            "time_series": time_series,
            "alerts": [],
            "recommendations": recommendations,
            "data_source": "Real ChromaDB analytics"
        }

        debug_log(f"Performance dashboard: {document_count} docs, {chunk_count} chunks", "📈")
        handler.send_json_response(dashboard_data)

    except Exception as e:
        print(f"❌ Performance dashboard API error: {e}")
        handler.send_json_response({'error': f'Performance dashboard failed: {str(e)}'}, 500)


def handle_search_results_api(handler):
    """Handle search results explorer API requests using real RAG search."""
    try:
        # Perform a real search using the RAG system
        sample_query = "knowledge documents content"
        search_result = handle_rag_search_request(sample_query, max_results=5)

        if search_result.get('status') != 'success':
            handler.send_json_response({
                "search_results": [],
                "query_info": {
                    "query": sample_query,
                    "total_found": 0,
                    "execution_time": 0,
                    "message": "No documents available for search. Upload documents first."
                },
                "data_source": "Real RAG search"
            })
            return

        # Format real search results
        search_results = []
        results = search_result.get('results', [])

        for i, result in enumerate(results):
            # Extract meaningful title from document content or metadata
            content = result.get('document', '')
            metadata = result.get('metadata', {})

            # Try to create a meaningful title
            title = metadata.get('file_name', f"Document {i+1}")
            if not title and content:
                # Use first line as title if available
                first_line = content.split('\n')[0].strip()
                title = first_line[:50] + "..." if len(first_line) > 50 else first_line

            search_results.append({
                "id": f"search_result_{i}",
                "title": title,
                "content": content[:200] + "..." if len(content) > 200 else content,
                "score": result.get('similarity_score', 0),
                "source": metadata.get('source', 'Unknown source'),
                "metadata": {
                    "file_type": metadata.get('file_type', 'unknown'),
                    "chunk_index": metadata.get('chunk_index', 0),
                    "chunk_type": metadata.get('chunk_type', 'content')
                }
            })

        explorer_data = {
            "search_results": search_results,
            "query_info": {
                "query": sample_query,
                "total_found": len(search_results),
                "execution_time": search_result.get('execution_time', 0),
                "strategy": "semantic_search",
                "data_source": "ChromaDB"
            },
            "filters": {
                "available_types": list(set(r["metadata"]["file_type"] for r in search_results)),
                "available_chunks": list(set(r["metadata"]["chunk_type"] for r in search_results))
            },
            "data_source": "Real RAG search"
        }

        debug_log(f"Search explorer: {len(search_results)} real results from ChromaDB", "🔍")
        handler.send_json_response(explorer_data)

    except Exception as e:
        print(f"❌ Search results API error: {e}")
        handler.send_json_response({'error': f'Search results failed: {str(e)}'}, 500)
