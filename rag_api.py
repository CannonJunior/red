"""
RAG API Integration for the existing web application.

This module integrates the RAG system with the existing server.py application,
adding document processing and semantic search capabilities.
"""

import json
import logging
from typing import Dict, Any
from pathlib import Path
import sys
import os

# Add rag-system to Python path
rag_system_path = Path(__file__).parent / "rag-system"
sys.path.append(str(rag_system_path))

try:
    from rag_core import MojoChromaRAG
    from document_processor import DocumentProcessor
    RAG_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("RAG system imported successfully")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"RAG system not available: {e}")
    RAG_AVAILABLE = False


class RAGService:
    """
    RAG service integration for the web application.
    
    Provides document processing and semantic search capabilities
    with zero-cost, local-first architecture.
    """
    
    def __init__(self):
        """Initialize RAG service if available."""
        self.available = RAG_AVAILABLE
        
        if self.available:
            try:
                self.rag_system = MojoChromaRAG(persist_directory="./web_rag_data")
                self.document_processor = DocumentProcessor()
                logger.info("RAG service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RAG service: {e}")
                self.available = False
        else:
            self.rag_system = None
            self.document_processor = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get RAG system status."""
        if not self.available:
            return {
                "status": "unavailable",
                "message": "RAG system not initialized",
                "features": []
            }
        
        try:
            status = self.rag_system.get_system_status()
            status["integration"] = "web_app"
            status["api_available"] = True
            return status
        except Exception as e:
            return {
                "status": "error",
                "message": f"Status check failed: {e}",
                "features": []
            }
    
    def ingest_document(self, file_path: str) -> Dict[str, Any]:
        """
        Process and ingest a document into the RAG system.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Processing result dictionary
        """
        if not self.available:
            return {
                "status": "error",
                "message": "RAG system not available"
            }
        
        try:
            # Process document
            processing_result = self.document_processor.process_document(file_path)
            
            if processing_result["status"] != "success":
                return processing_result
            
            # Add to vector database
            documents = []
            for chunk in processing_result["chunks"]:
                documents.append({
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                    "id": f"{Path(file_path).stem}_chunk_{chunk['metadata']['chunk_index']}"
                })
            
            storage_result = self.rag_system.add_documents(documents)
            
            return {
                "status": "success",
                "message": f"Successfully processed {processing_result['total_chunks']} chunks",
                "file_path": file_path,
                "file_type": processing_result["file_type"],
                "chunks_processed": processing_result["total_chunks"],
                "total_documents": storage_result["total_documents"]
            }
            
        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")
            return {
                "status": "error",
                "message": f"Document ingestion failed: {e}"
            }
    
    def search_documents(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search documents using semantic similarity.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            Search results dictionary
        """
        if not self.available:
            return {
                "status": "error",
                "message": "RAG system not available",
                "results": []
            }
        
        try:
            results = self.rag_system.search_similar(query, max_results)
            return {
                "status": "success",
                "query": query,
                "results": results["results"],
                "total_found": results["total_found"]
            }
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return {
                "status": "error",
                "message": f"Search failed: {e}",
                "results": []
            }
    
    def query_rag(self, query: str, max_context: int = 5) -> Dict[str, Any]:
        """
        Complete RAG query with response generation.
        
        Args:
            query: User question
            max_context: Maximum context documents
            
        Returns:
            RAG response dictionary
        """
        if not self.available:
            return {
                "status": "error",
                "message": "RAG system not available",
                "answer": "RAG system is not available. Please ensure all dependencies are installed."
            }
        
        try:
            result = self.rag_system.query_rag(query, max_context)
            return {
                "status": result["status"],
                "query": query,
                "answer": result["answer"],
                "sources": result["sources"][:3],  # Limit sources for web display
                "model_used": result["model_used"]
            }
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "status": "error",
                "message": f"RAG query failed: {e}",
                "answer": f"Sorry, I encountered an error: {e}"
            }
    
    def get_documents(self) -> Dict[str, Any]:
        """
        Get metadata for all ingested documents.
        
        Returns:
            Documents metadata dictionary
        """
        if not self.available:
            return {
                "status": "error",
                "message": "RAG system not available",
                "documents": []
            }
        
        try:
            documents = self.rag_system.get_documents_metadata()
            return {
                "status": "success",
                "documents": documents,
                "total": len(documents)
            }
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return {
                "status": "error",
                "message": f"Failed to get documents: {e}",
                "documents": []
            }
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get RAG system analytics.
        
        Returns:
            Analytics dictionary
        """
        if not self.available:
            return {
                "status": "error",
                "message": "RAG system not available",
                "document_count": 0,
                "chunk_count": 0,
                "query_count": 0
            }
        
        try:
            status = self.rag_system.get_system_status()
            documents = self.rag_system.get_documents_metadata()
            
            # Calculate total chunks
            total_chunks = sum(doc.get('chunks', 0) for doc in documents)
            
            return {
                "status": "success",
                "document_count": len(documents),  # Use actual document count, not chunk count
                "chunk_count": total_chunks,
                "query_count": getattr(self.rag_system, 'query_count', 0)  # Placeholder for now
            }
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {
                "status": "error",
                "message": f"Failed to get analytics: {e}",
                "document_count": 0,
                "chunk_count": 0,
                "query_count": 0
            }

    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """
        Delete a document from the RAG system.
        
        Args:
            document_id: The unique identifier for the document to delete
            
        Returns:
            Deletion result dictionary
        """
        if not self.available:
            return {
                "status": "error",
                "message": "RAG system not available",
                "document_id": document_id
            }
        
        try:
            # Call the delete_document method from the RAG core system
            result = self.rag_system.delete_document(document_id)
            
            if result.get("success", False):
                return {
                    "status": "success",
                    "message": result.get("message", f"Document {document_id} deleted successfully"),
                    "document_id": document_id,
                    "timestamp": result.get("timestamp")
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", f"Failed to delete document {document_id}"),
                    "document_id": document_id
                }
                
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to delete document: {e}",
                "document_id": document_id
            }


# Global RAG service instance
rag_service = RAGService()


def handle_rag_status_request():
    """Handle RAG status API request."""
    return rag_service.get_status()


def handle_rag_search_request(query: str, max_results: int = 5):
    """Handle RAG search API request."""
    return rag_service.search_documents(query, max_results)


def handle_rag_query_request(query: str, max_context: int = 5):
    """Handle RAG query API request."""
    return rag_service.query_rag(query, max_context)


def handle_rag_ingest_request(file_path: str):
    """Handle RAG document ingestion request."""
    return rag_service.ingest_document(file_path)


def handle_rag_documents_request():
    """Handle RAG documents listing request."""
    return rag_service.get_documents()


def handle_rag_analytics_request():
    """Handle RAG analytics request."""
    return rag_service.get_analytics()


def handle_rag_document_delete_request(document_id: str):
    """Handle RAG document deletion request."""
    return rag_service.delete_document(document_id)


# Test functionality
if __name__ == "__main__":
    # Test RAG service
    print("Testing RAG Service...")
    
    status = rag_service.get_status()
    print(f"Status: {json.dumps(status, indent=2)}")
    
    if status["status"] != "error":
        # Test search
        search_result = rag_service.search_documents("What is Mojo?")
        print(f"Search Result: {json.dumps(search_result, indent=2)}")
        
        # Test RAG query
        rag_result = rag_service.query_rag("Explain the RAG system architecture")
        print(f"RAG Result: {json.dumps(rag_result, indent=2)}")