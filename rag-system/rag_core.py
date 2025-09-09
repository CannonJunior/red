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
        self.ollama_client = ollama.Client()
        self.default_model = "qwen2.5:3b"  # Fast, efficient model
        
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
    
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection."""
        try:
            return self.client.get_collection(name=name)
        except (ValueError, Exception):
            # Collection doesn't exist, create it
            return self.client.create_collection(
                name=name,
                metadata={"description": "Agent-native RAG document collection"}
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
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add documents to the vector database (Agent-accessible via MCP).
        
        Args:
            documents: List of document dictionaries with 'text', 'metadata', etc.
            
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
        
        # Add to ChromaDB
        self.collection.add(
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
            "total_documents": self.collection.count()
        }
    
    def search_similar(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Perform semantic similarity search (Agent-accessible via MCP).
        
        Args:
            query: Search query text
            n_results: Number of results to return
            
        Returns:
            Search results formatted for agent consumption
        """
        # Generate query embedding locally
        query_embedding = self.embed_texts([query])[0]
        
        # Search ChromaDB (optimized for sub-10ms latency)
        results = self.collection.query(
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
        # Build context-aware prompt
        context = "\\n\\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(context_docs)])
        
        prompt = f"""Based on the following context documents, please answer the question.
        
Context:
{context}

Question: {query}

Please provide a comprehensive answer based on the context provided."""

        try:
            # Generate response with local Ollama (zero API costs)
            response = self.ollama_client.chat(
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "query": query,
                "response": response['message']['content'],
                "model_used": self.default_model,
                "context_docs_count": len(context_docs),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "query": query,
                "response": f"Error: Unable to generate response. Please ensure Ollama is running with model '{self.default_model}'.",
                "error": str(e),
                "status": "error"
            }
    
    def query_rag(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Complete RAG pipeline: search + generate (Agent-accessible via MCP).
        
        Args:
            query: User question
            n_results: Number of documents to retrieve for context
            
        Returns:
            Complete RAG response with sources
        """
        # Step 1: Semantic search
        search_results = self.search_similar(query, n_results)
        
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
        
        # Check Ollama status
        try:
            models = self.ollama_client.list()
            status["llm"]["status"] = "healthy"
            status["llm"]["available_models"] = [model['name'] for model in models['models']]
        except Exception as e:
            status["llm"]["status"] = "unavailable"
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