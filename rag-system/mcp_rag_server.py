"""
MCP (Model Context Protocol) Server for Agent-Native RAG System.

This module exposes all RAG functionality through standardized MCP interfaces,
enabling AI agents to orchestrate document ingestion, search, and synthesis.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# MCP imports
from mcp.server import Server
from mcp.types import Resource, Tool

# Local RAG components
from rag_core import MojoChromaRAG
from document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGMCPServer:
    """
    Agent-native MCP server exposing RAG functionality for AI orchestration.
    
    This server implements the OPTIMAL_RAG_IMPLEMENTATION_PLAN.md architecture
    by providing standardized interfaces for:
    - Document ingestion and processing
    - Vector similarity search 
    - Multi-agent task orchestration
    - System monitoring and status
    """
    
    def __init__(self):
        """Initialize the MCP RAG server."""
        self.server = Server("rag-server")
        
        # Initialize RAG components
        self.rag_system = MojoChromaRAG()
        self.document_processor = DocumentProcessor()
        
        # Setup MCP tools and resources
        self.setup_tools()
        self.setup_resources()
        
        logger.info("RAG MCP Server initialized - Ready for agent orchestration")
    
    def setup_tools(self):
        """Setup MCP tools for AI agent consumption."""
        
        @self.server.call_tool()
        async def ingest_document(file_path: str, **kwargs) -> str:
            """
            Ingest a document into the RAG system (Agent Tool).
            
            Args:
                file_path: Path to document file (.txt, .pdf, .doc, .csv, .xls)
                
            Returns:
                JSON string with ingestion results
            """
            try:
                # Process document using local processors (zero cost)
                processing_result = self.document_processor.process_document(file_path)
                
                if processing_result["status"] != "success":
                    return json.dumps({
                        "status": "error",
                        "message": f"Document processing failed: {processing_result.get('error', 'Unknown error')}",
                        "file_path": file_path
                    })
                
                # Add processed chunks to vector database
                documents = []
                for chunk in processing_result["chunks"]:
                    documents.append({
                        "text": chunk["text"],
                        "metadata": chunk["metadata"],
                        "id": f"{Path(file_path).stem}_chunk_{chunk['metadata']['chunk_index']}"
                    })
                
                # Store in ChromaDB (local, zero cost)
                storage_result = self.rag_system.add_documents(documents)
                
                return json.dumps({
                    "status": "success",
                    "message": f"Successfully ingested {processing_result['total_chunks']} chunks",
                    "file_path": file_path,
                    "file_type": processing_result["file_type"],
                    "chunks_processed": processing_result["total_chunks"],
                    "total_documents_in_system": storage_result["total_documents"],
                    "processing_method": processing_result.get("processing_method", "standard")
                })
                
            except Exception as e:
                logger.error(f"Document ingestion failed: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Ingestion failed: {str(e)}",
                    "file_path": file_path
                })
        
        @self.server.call_tool()
        async def search_documents(query: str, max_results: int = 5, **kwargs) -> str:
            """
            Search documents using semantic similarity (Agent Tool).
            
            Args:
                query: Search query text
                max_results: Maximum number of results to return
                
            Returns:
                JSON string with search results
            """
            try:
                search_results = self.rag_system.search_similar(query, max_results)
                
                return json.dumps({
                    "status": "success",
                    "query": query,
                    "results_found": len(search_results["results"]),
                    "results": search_results["results"]
                })
                
            except Exception as e:
                logger.error(f"Document search failed: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Search failed: {str(e)}",
                    "query": query
                })
        
        @self.server.call_tool()
        async def query_rag(query: str, max_context_docs: int = 5, **kwargs) -> str:
            """
            Complete RAG pipeline: search + generate response (Agent Tool).
            
            Args:
                query: User question
                max_context_docs: Number of documents for context
                
            Returns:
                JSON string with RAG response
            """
            try:
                rag_result = self.rag_system.query_rag(query, max_context_docs)
                
                return json.dumps({
                    "status": rag_result["status"],
                    "query": query,
                    "answer": rag_result["answer"],
                    "model_used": rag_result["model_used"],
                    "sources_used": len(rag_result["sources"]),
                    "sources": rag_result["sources"][:3],  # Limit sources for brevity
                    "confidence": "high" if rag_result["status"] == "success" else "low"
                })
                
            except Exception as e:
                logger.error(f"RAG query failed: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"RAG query failed: {str(e)}",
                    "query": query
                })
        
        @self.server.call_tool()
        async def orchestrate_multi_step_research(research_topic: str, perspectives: List[str] = None, **kwargs) -> str:
            """
            Orchestrate complex multi-step research using RAG (Agent Tool).
            
            Args:
                research_topic: Topic to research
                perspectives: List of perspectives to analyze from
                
            Returns:
                JSON string with comprehensive research results
            """
            try:
                if perspectives is None:
                    perspectives = ["technical", "business", "implementation"]
                
                research_results = []
                
                for perspective in perspectives:
                    # Generate perspective-specific query
                    perspective_query = f"Analyze {research_topic} from a {perspective} perspective"
                    
                    # Get RAG response for this perspective
                    rag_result = self.rag_system.query_rag(perspective_query, max_results=3)
                    
                    research_results.append({
                        "perspective": perspective,
                        "analysis": rag_result["answer"],
                        "sources_count": len(rag_result["sources"]),
                        "confidence": "high" if rag_result["status"] == "success" else "low"
                    })
                
                # Generate synthesis prompt for final analysis
                synthesis_prompt = f"Synthesize research on {research_topic} from multiple perspectives: {', '.join(perspectives)}"
                synthesis_result = self.rag_system.query_rag(synthesis_prompt, max_results=8)
                
                return json.dumps({
                    "status": "success",
                    "research_topic": research_topic,
                    "perspectives_analyzed": len(perspectives),
                    "perspective_results": research_results,
                    "synthesis": synthesis_result["answer"],
                    "total_sources_consulted": sum(r["sources_count"] for r in research_results)
                })
                
            except Exception as e:
                logger.error(f"Multi-step research failed: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Research orchestration failed: {str(e)}",
                    "research_topic": research_topic
                })
        
        @self.server.call_tool()
        async def get_system_status(**kwargs) -> str:
            """
            Get RAG system status and health metrics (Agent Tool).
            
            Returns:
                JSON string with system status
            """
            try:
                status = self.rag_system.get_system_status()
                
                # Add MCP server specific status
                status["mcp_server"] = {
                    "status": "healthy",
                    "tools_available": 5,
                    "agent_ready": True
                }
                
                return json.dumps(status)
                
            except Exception as e:
                logger.error(f"Status check failed: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Status check failed: {str(e)}"
                })
        
        @self.server.call_tool()
        async def analyze_document_collection(**kwargs) -> str:
            """
            Analyze the current document collection for insights (Agent Tool).
            
            Returns:
                JSON string with collection analysis
            """
            try:
                # Get system status for document count
                status = self.rag_system.get_system_status()
                document_count = status["vector_database"]["document_count"]
                
                if document_count == 0:
                    return json.dumps({
                        "status": "success",
                        "message": "No documents in collection yet",
                        "document_count": 0,
                        "recommendations": [
                            "Use 'ingest_document' tool to add documents",
                            "Supported formats: .txt, .pdf, .doc, .csv, .xls"
                        ]
                    })
                
                # Perform analysis queries
                analysis_queries = [
                    "What types of documents are in this collection?",
                    "What are the main topics covered?",
                    "What insights can be derived from the data?"
                ]
                
                analyses = []
                for query in analysis_queries:
                    result = self.rag_system.query_rag(query, max_results=5)
                    if result["status"] == "success":
                        analyses.append({
                            "question": query,
                            "analysis": result["answer"],
                            "sources_used": len(result["sources"])
                        })
                
                return json.dumps({
                    "status": "success",
                    "document_count": document_count,
                    "collection_analyses": analyses,
                    "summary": f"Analyzed collection of {document_count} documents with {len(analyses)} perspectives"
                })
                
            except Exception as e:
                logger.error(f"Collection analysis failed: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Collection analysis failed: {str(e)}"
                })
    
    def setup_resources(self):
        """Setup MCP resources for AI agent consumption."""
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available document resources."""
            try:
                status = self.rag_system.get_system_status()
                document_count = status["vector_database"]["document_count"]
                
                resources = [
                    Resource(
                        uri="rag://system/status",
                        name="RAG System Status",
                        description=f"Current system status with {document_count} documents"
                    ),
                    Resource(
                        uri="rag://documents/collection", 
                        name="Document Collection",
                        description=f"Vector database containing {document_count} processed documents"
                    ),
                    Resource(
                        uri="rag://models/local",
                        name="Local Models",
                        description="Local Ollama models for zero-cost inference"
                    )
                ]
                
                return resources
                
            except Exception as e:
                logger.error(f"Resource listing failed: {e}")
                return []
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource content."""
            try:
                if uri == "rag://system/status":
                    status = self.rag_system.get_system_status()
                    return json.dumps(status, indent=2)
                
                elif uri == "rag://documents/collection":
                    # Provide collection overview
                    status = self.rag_system.get_system_status()
                    return json.dumps({
                        "collection_type": "ChromaDB with DuckDB backend",
                        "document_count": status["vector_database"]["document_count"],
                        "cost": "$0/month (local only)",
                        "capabilities": [
                            "Semantic similarity search",
                            "Multi-format document ingestion",
                            "Real-time query processing"
                        ]
                    }, indent=2)
                
                elif uri == "rag://models/local":
                    status = self.rag_system.get_system_status()
                    return json.dumps({
                        "llm_models": status["llm"],
                        "embedding_model": "all-MiniLM-L6-v2 (local)",
                        "cost": "$0 (no API fees)"
                    }, indent=2)
                
                else:
                    return json.dumps({"error": f"Unknown resource URI: {uri}"})
                    
            except Exception as e:
                logger.error(f"Resource reading failed: {e}")
                return json.dumps({"error": f"Resource reading failed: {str(e)}"})
    
    async def run(self, transport_type: str = "stdio"):
        """Run the MCP server."""
        if transport_type == "stdio":
            from mcp.server.stdio import stdio_server
            logger.info("Starting RAG MCP Server with stdio transport")
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")


async def main():
    """Main function to run the RAG MCP server."""
    server = RAGMCPServer()
    
    logger.info("RAG MCP Server starting...")
    logger.info("Available tools:")
    logger.info("- ingest_document: Process and add documents to RAG system")
    logger.info("- search_documents: Semantic similarity search")
    logger.info("- query_rag: Complete RAG pipeline with response generation")
    logger.info("- orchestrate_multi_step_research: Complex multi-perspective analysis")
    logger.info("- get_system_status: System health and metrics")
    logger.info("- analyze_document_collection: Collection insights and recommendations")
    
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())