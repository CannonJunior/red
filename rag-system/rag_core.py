"""
Core RAG system implementation with ChromaDB and local Ollama integration.

This module provides the foundation for agent-native RAG functionality following
the OPTIMAL_RAG_IMPLEMENTATION_PLAN.md architecture.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

import chromadb
from chromadb.config import Settings
import ollama
import redis
from sentence_transformers import SentenceTransformer

# Import parent directory for ollama_config
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from ollama_config import ollama_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MojoChromaRAG:
    """
    Zero-cost, locally-running RAG system optimized for 5 users.
    Agent-native architecture with MCP interfaces.
    """
    
    def __init__(self, persist_directory: str = "./rag_data"):
        """
        Initialize the RAG system with local components.
        
        Args:
            persist_directory: Local directory for vector database persistence
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        
        # Initialize ChromaDB with DuckDB backend for better performance
        self.client = chromadb.Client(Settings(
            persist_directory=str(self.persist_directory),
            anonymized_telemetry=False,  # Privacy-first
            allow_reset=True
        ))
        
        # Initialize collections
        self.collection = self._get_or_create_collection("documents")
        
        # Initialize embedding model (local, no API costs)
        logger.info("Loading local embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize Ollama client (local LLM, zero API costs)
        # Keep backward compatibility with existing ollama.Client() for internal methods
        self.ollama_client = ollama.Client()
        
        # Use robust configuration for external-facing methods
        self.robust_ollama_config = ollama_config
        
        # Dynamically select the best available model
        self.default_model = self._get_best_available_model()
        
        # Initialize Redis for event streaming (lightweight vs Kafka)
        try:
            self.redis_client = redis.Redis(
                host='localhost', 
                port=6379, 
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis for event streaming")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis not available: {e}. Event streaming disabled.")
            self.redis_client = None
    
    def _get_best_available_model(self):
        """
        Dynamically select the best available model from Ollama.
        
        Priority order:
        1. qwen2.5:3b (preferred - fast and efficient)
        2. llama3.1:8b or similar llama models
        3. Any other available model
        4. Fallback to "qwen2.5:3b" with warning
        """
        preferred_models = [
            "qwen2.5:3b",
            "qwen2.5:1.5b", 
            "qwen2.5:7b",
            "llama3.1:8b",
            "llama3.1:7b", 
            "llama3:8b",
            "llama3:7b",
            "llama2:7b",
            "mistral:7b",
            "gemma:7b"
        ]
        
        try:
            # Get available models using robust configuration
            connection_test = self.robust_ollama_config.test_connection()
            
            if connection_test['connected'] and connection_test['models']:
                available_models = connection_test['models']
                logger.info(f"Available Ollama models: {available_models}")
                
                # Try to find preferred models in order
                for preferred in preferred_models:
                    if preferred in available_models:
                        logger.info(f"Selected model: {preferred}")
                        return preferred
                
                # If no preferred model found, use the first available
                first_model = available_models[0]
                logger.info(f"No preferred model found, using first available: {first_model}")
                return first_model
            else:
                logger.warning(f"Cannot connect to Ollama: {connection_test.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
        
        # Fallback to default with warning
        fallback_model = "qwen2.5:3b"
        logger.warning(f"Could not detect available models, falling back to: {fallback_model}")
        logger.warning("Please ensure Ollama is running and has models installed")
        return fallback_model
    
    def _get_or_create_collection(self, name: str, workspace: str = 'default'):
        """Get or create a ChromaDB collection for a specific workspace."""
        collection_name = f"{workspace}_{name}" if workspace != 'default' else name
        try:
            return self.client.get_collection(name=collection_name)
        except (ValueError, Exception):
            # Collection doesn't exist, create it
            return self.client.create_collection(
                name=collection_name,
                metadata={
                    "description": f"Agent-native RAG document collection for workspace: {workspace}",
                    "workspace": workspace
                }
            )
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using local model.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()
    
    def add_documents(self, documents: List[Dict[str, Any]], workspace: str = 'default') -> Dict[str, Any]:
        """
        Add documents to the vector database (Agent-accessible via MCP).
        
        Args:
            documents: List of document dictionaries with 'text', 'metadata', etc.
            workspace: Workspace/Knowledge Base identifier
            
        Returns:
            Status dictionary for agent consumption
        """
        texts = []
        metadatas = []
        ids = []
        
        for i, doc in enumerate(documents):
            doc_id = doc.get('id', f"doc_{i}_{len(texts)}")
            texts.append(doc['text'])
            metadatas.append(doc.get('metadata', {}))
            ids.append(doc_id)
        
        # Generate embeddings locally (zero cost)
        embeddings = self.embed_texts(texts)
        
        # Get workspace-specific collection
        collection = self._get_or_create_collection("documents", workspace)
        
        # Add to ChromaDB
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        # Emit event for agent orchestration
        if self.redis_client:
            self._emit_event("documents_added", {
                "count": len(documents),
                "collection": "documents"
            })
        
        return {
            "status": "success",
            "documents_added": len(documents),
            "total_documents": collection.count(),
            "workspace": workspace
        }
    
    def search_similar(self, query: str, n_results: int = 5, workspace: str = 'default') -> Dict[str, Any]:
        """
        Perform semantic similarity search (Agent-accessible via MCP).
        
        Args:
            query: Search query text
            n_results: Number of results to return
            workspace: Workspace/Knowledge Base identifier
            
        Returns:
            Search results formatted for agent consumption
        """
        # Generate query embedding locally
        query_embedding = self.embed_texts([query])[0]
        
        # Get workspace-specific collection
        collection = self._get_or_create_collection("documents", workspace)
        
        # Search ChromaDB (optimized for sub-10ms latency)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results for agent consumption
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                "document": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "similarity_score": 1.0 - results['distances'][0][i],  # Convert distance to similarity
                "rank": i + 1
            })
        
        # Debug: Log search results
        logger.info(f"🔍 Search Debug - Query: '{query}' found {len(formatted_results)} results")
        if formatted_results:
            logger.info(f"🔍 Search Debug - First result metadata: {formatted_results[0].get('metadata', {})}")
        else:
            logger.warning(f"🔍 Search Debug - No results found for query: '{query}'")
            
        return {
            "query": query,
            "results": formatted_results,
            "total_found": len(formatted_results)
        }
    
    def generate_response(self, query: str, context_docs: List[str]) -> Dict[str, Any]:
        """
        Generate response using local Ollama model with retrieved context.
        
        Args:
            query: User query
            context_docs: Retrieved document texts for context
            
        Returns:
            Generated response with metadata
        """
        # Build context-aware prompt without numbered document references
        context = "\\n\\n".join(context_docs)

        prompt = f"""Answer the following question using only the information provided in the context below. Do not reference document numbers or make up information not present in the context.

Context:
{context}

Question: {query}

Answer based solely on the provided context:"""

        try:
            # Use robust Ollama configuration for chat response
            logger.debug(f"Generating response using robust Ollama config with model: {self.default_model}")
            messages = [{"role": "user", "content": prompt}]
            result = self.robust_ollama_config.chat_response(self.default_model, messages)
            
            if result['success']:
                response_content = result['data']['message']['content']
                return {
                    "query": query,
                    "response": response_content,
                    "model_used": self.default_model,
                    "context_docs_count": len(context_docs),
                    "status": "success",
                    "connection_attempt": result['attempt']
                }
            else:
                logger.error(f"Robust Ollama request failed: {result['error']}")
                return {
                    "query": query,
                    "response": f"Error: Unable to generate response after {result['attempt']} attempts. {result['error']}",
                    "error": result['error'],
                    "status": "error",
                    "connection_attempt": result['attempt']
                }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "query": query,
                "response": f"Error: Unexpected error during response generation. Please ensure Ollama is running with model '{self.default_model}'.",
                "error": str(e),
                "status": "error"
            }
    
    def query_rag(self, query: str, n_results: int = 5, workspace: str = 'default') -> Dict[str, Any]:
        """
        Complete RAG pipeline: search + generate (Agent-accessible via MCP).
        
        Args:
            query: User question
            n_results: Number of documents to retrieve for context
            workspace: Workspace/Knowledge Base identifier
            
        Returns:
            Complete RAG response with sources
        """
        # Step 1: Semantic search
        search_results = self.search_similar(query, n_results, workspace)
        
        # Step 2: Extract context documents
        context_docs = [result["document"] for result in search_results["results"]]
        
        # Step 3: Generate response with context
        generation_result = self.generate_response(query, context_docs)
        
        # Step 4: Combine results
        return {
            "query": query,
            "answer": generation_result["response"],
            "sources": search_results["results"],
            "model_used": generation_result.get("model_used", self.default_model),
            "retrieval_count": len(context_docs),
            "status": generation_result["status"]
        }
    
    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """Emit event to Redis Streams for agent orchestration."""
        if not self.redis_client:
            return
            
        event = {
            'event_type': event_type,
            'timestamp': str(datetime.now()),
            'payload': json.dumps(payload),
            'source': 'rag_system'
        }
        
        try:
            self.redis_client.xadd(f'rag_events:{event_type}', event)
        except Exception as e:
            logger.warning(f"Failed to emit event: {e}")
    
    def get_documents_metadata(self, workspace: str = 'default') -> List[Dict[str, Any]]:
        """Get metadata for all ingested documents in a specific workspace."""
        try:
            # Get workspace-specific collection
            collection = self._get_or_create_collection("documents", workspace)
            # Get all documents from ChromaDB
            results = collection.get()
            
            documents = []
            processed_sources = set()
            
            for i, metadata in enumerate(results.get('metadatas', [])):
                if metadata and 'source' in metadata:
                    source_path = metadata['source']
                    
                    # Skip if we've already processed this source file
                    if source_path in processed_sources:
                        continue
                    processed_sources.add(source_path)
                    
                    # Extract filename from path
                    import os
                    filename = os.path.basename(source_path)
                    
                    # Count chunks for this document
                    chunk_count = sum(1 for m in results.get('metadatas', []) 
                                    if m and m.get('source') == source_path)
                    
                    # Determine file type
                    file_ext = os.path.splitext(filename)[1].lower()
                    file_type = {
                        '.csv': 'CSV',
                        '.txt': 'Text',
                        '.pdf': 'PDF',
                        '.docx': 'Word Document',
                        '.md': 'Markdown'
                    }.get(file_ext, 'Unknown')
                    
                    # Try to get file size (this is approximate)
                    try:
                        file_size = os.path.getsize(source_path) if os.path.exists(source_path) else None
                    except:
                        file_size = None
                    
                    doc_info = {
                        'id': f"doc_{len(documents)}",
                        'name': filename,
                        'type': file_type,
                        'size': file_size,
                        'chunks': chunk_count,
                        'uploadDate': metadata.get('ingestion_date', datetime.now().isoformat()),
                        'status': 'processed',
                        'source_path': source_path
                    }
                    
                    documents.append(doc_info)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error getting documents metadata: {e}")
            return []

    def delete_document(self, document_id: str, workspace: str = 'default') -> Dict[str, Any]:
        """
        Delete a document from the vector database.
        
        Args:
            document_id: The unique identifier for the document to delete (e.g., "doc_0", "doc_1")
            workspace: Workspace/Knowledge Base identifier
            
        Returns:
            Dictionary with deletion status and details
        """
        try:
            logger.info(f"Attempting to delete document: {document_id} from workspace: {workspace}")
            
            # First, get the list of documents to find the source path for this document ID
            documents = self.get_documents_metadata(workspace)
            
            # Find the document that matches this ID
            target_document = None
            for doc in documents:
                if doc['id'] == document_id:
                    target_document = doc
                    break
            
            if not target_document:
                return {
                    "success": False,
                    "error": f"Document with ID '{document_id}' not found",
                    "document_id": document_id
                }
            
            # Get the source path for this document
            source_path = target_document['source_path']
            logger.info(f"Found document {document_id} with source path: {source_path}")
            
            # Get workspace-specific collection
            collection = self._get_or_create_collection("documents", workspace)
            
            # Now find all chunk IDs that belong to this source path
            all_data = collection.get()
            all_ids = all_data.get('ids', [])
            all_metadatas = all_data.get('metadatas', [])
            
            matching_ids = []
            
            for i, chunk_id in enumerate(all_ids):
                metadata = all_metadatas[i] if i < len(all_metadatas) else {}
                
                # Match based on source path in metadata
                if metadata and metadata.get('source') == source_path:
                    matching_ids.append(chunk_id)
            
            logger.info(f"Found {len(matching_ids)} matching chunk IDs for document '{document_id}' (source: {source_path}): {matching_ids}")
            
            if not matching_ids:
                return {
                    "success": False,
                    "error": f"No chunks found for document '{document_id}' with source path '{source_path}'",
                    "document_id": document_id
                }
            
            # Delete all matching chunks from workspace-specific collection
            collection.delete(ids=matching_ids)
            
            # Log the deletion event
            deleted_count = len(matching_ids)
            logger.info(f"Deleted document '{document_id}' ({deleted_count} chunks): {matching_ids}")
            
            # Emit event if Redis is available
            if self.redis_client:
                try:
                    event_data = {
                        "event_type": "document_deleted",
                        "document_id": document_id,
                        "chunks_deleted": deleted_count,
                        "chunk_ids": matching_ids,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.redis_client.xadd("rag_events", event_data)
                except Exception as e:
                    logger.warning(f"Failed to emit deletion event: {e}")
            
            return {
                "success": True,
                "message": f"Document '{document_id}' deleted successfully ({deleted_count} chunks)",
                "document_id": document_id,
                "chunks_deleted": deleted_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return {
                "success": False,
                "error": f"Delete operation failed: {str(e)}",
                "document_id": document_id
            }

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status for monitoring (Agent-accessible via MCP)."""
        status = {
            "vector_database": {
                "type": "ChromaDB",
                "backend": "DuckDB",
                "document_count": self.collection.count(),
                "status": "healthy"
            },
            "llm": {
                "type": "Ollama",
                "model": self.default_model,
                "status": "unknown"  # Will be checked
            },
            "event_streaming": {
                "type": "Redis Streams",
                "status": "available" if self.redis_client else "unavailable"
            },
            "cost": "$0/month",
            "architecture": "local-first"
        }
        
        # Check Ollama status using robust configuration
        try:
            # Use robust connection test
            connection_test = self.robust_ollama_config.test_connection()
            if connection_test['connected']:
                status["llm"]["status"] = "healthy"
                status["llm"]["available_models"] = connection_test.get('models', [])
                status["llm"]["response_time"] = connection_test.get('response_time')
                status["llm"]["config"] = self.robust_ollama_config.get_config_info()
            else:
                status["llm"]["status"] = "unavailable"
                status["llm"]["error"] = connection_test.get('error', 'Connection failed')
                status["llm"]["config"] = self.robust_ollama_config.get_config_info()
        except Exception as e:
            status["llm"]["status"] = "error"
            status["llm"]["error"] = str(e)
        
        return status


# Example usage and testing
if __name__ == "__main__":
    # Initialize RAG system
    rag = MojoChromaRAG()
    
    # Test system status
    status = rag.get_system_status()
    print("System Status:")
    print(json.dumps(status, indent=2))
    
    # Test document addition
    sample_docs = [
        {
            "text": "Mojo is a programming language designed for high-performance AI applications.",
            "metadata": {"source": "mojo_intro", "type": "definition"}
        },
        {
            "text": "ChromaDB is an open-source vector database designed for AI applications.",
            "metadata": {"source": "chromadb_intro", "type": "definition"}
        }
    ]
    
    result = rag.add_documents(sample_docs)
    print("\\nDocument Addition Result:")
    print(json.dumps(result, indent=2))
    
    # Test RAG query
    query_result = rag.query_rag("What is Mojo?")
    print("\\nRAG Query Result:")
    print(json.dumps(query_result, indent=2))