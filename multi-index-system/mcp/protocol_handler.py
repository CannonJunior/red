"""
MCP (Model Context Protocol) Integration for Phase 3

Implements Model Context Protocol for seamless AI agent integration
with the multi-index system, enabling intelligent document analysis
and knowledge synthesis workflows.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

try:
    from ..config.settings import get_config
    from ..core.query_executor import EnhancedQueryExecutor, ExecutionContext
    from ..indices.adaptive import AdaptiveIndexManager
except ImportError:
    from config.settings import get_config
    from core.query_executor import EnhancedQueryExecutor, ExecutionContext
    from indices.adaptive import AdaptiveIndexManager

logger = logging.getLogger(__name__)

class MCPMessageType(Enum):
    """MCP message types for agent communication."""
    INITIALIZE = "initialize"
    CALL = "call"
    RESULT = "result"
    ERROR = "error"
    NOTIFICATION = "notification"
    PING = "ping"
    PONG = "pong"

class MCPResourceType(Enum):
    """Types of resources available through MCP."""
    DOCUMENT = "document"
    SEARCH_RESULTS = "search_results"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    ANALYTICS = "analytics"
    VISUALIZATION = "visualization"

@dataclass
class MCPMessage:
    """MCP protocol message structure."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

@dataclass
class MCPTool:
    """MCP tool definition for AI agents."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler: Optional[Callable] = None

@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str
    resource_type: MCPResourceType
    metadata: Dict[str, Any]

class MCPServer:
    """
    MCP server for AI agent integration.

    Provides tools and resources for:
    - Document search and retrieval
    - Knowledge graph exploration
    - Analytics and insights
    - Visualization generation
    - Real-time collaboration
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        self.session_id = str(uuid.uuid4())

        # Core components
        self.query_executor = None
        self.adaptive_manager = None

        # MCP state
        self.client_capabilities = {}
        self.server_capabilities = {
            "tools": True,
            "resources": True,
            "prompts": True,
            "logging": True
        }

        # Available tools and resources
        self.tools = {}
        self.resources = {}
        self.active_sessions = {}

        # Initialize tools
        self._register_tools()

    async def initialize(self):
        """Initialize MCP server with multi-index system."""
        try:
            # Initialize query executor
            self.query_executor = EnhancedQueryExecutor(self.config)
            await self.query_executor.initialize()

            # Initialize adaptive manager
            try:
                from pathlib import Path
                temp_path = Path("/tmp/mcp_adaptive")
                temp_path.mkdir(exist_ok=True)

                self.adaptive_manager = AdaptiveIndexManager(
                    "mcp_adaptive",
                    str(temp_path),
                    {"pattern_window_size": 100, "cache_size": 50}
                )
                await self.adaptive_manager.initialize()
            except Exception as e:
                logger.warning(f"Adaptive manager initialization failed: {e}")

            logger.info(f"MCP server initialized with session {self.session_id}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP message."""
        try:
            mcp_msg = MCPMessage(**message)

            if mcp_msg.method == "initialize":
                return await self._handle_initialize(mcp_msg)
            elif mcp_msg.method == "tools/list":
                return await self._handle_list_tools(mcp_msg)
            elif mcp_msg.method == "tools/call":
                return await self._handle_tool_call(mcp_msg)
            elif mcp_msg.method == "resources/list":
                return await self._handle_list_resources(mcp_msg)
            elif mcp_msg.method == "resources/read":
                return await self._handle_read_resource(mcp_msg)
            elif mcp_msg.method == "prompts/list":
                return await self._handle_list_prompts(mcp_msg)
            elif mcp_msg.method == "logging/setLevel":
                return await self._handle_set_log_level(mcp_msg)
            elif mcp_msg.method == "ping":
                return self._create_response(mcp_msg.id, "pong")
            else:
                return self._create_error_response(
                    mcp_msg.id, -32601, f"Method not found: {mcp_msg.method}"
                )

        except Exception as e:
            logger.error(f"Error handling MCP message: {e}")
            return self._create_error_response(
                message.get("id"), -32603, f"Internal error: {str(e)}"
            )

    def _register_tools(self):
        """Register available MCP tools."""

        # Document search tool
        self.tools["search_documents"] = MCPTool(
            name="search_documents",
            description="Search for documents using semantic, full-text, or structured queries",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "search_type": {
                        "type": "string",
                        "enum": ["semantic", "fulltext", "structured", "hybrid"],
                        "description": "Type of search to perform"
                    },
                    "limit": {"type": "integer", "default": 10, "description": "Maximum results"},
                    "workspace": {"type": "string", "default": "default", "description": "Workspace to search"}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "relevance": {"type": "number"},
                                "source": {"type": "string"}
                            }
                        }
                    },
                    "total_found": {"type": "integer"},
                    "execution_time": {"type": "number"}
                }
            },
            handler=self._handle_search_documents
        )

        # Knowledge graph exploration tool
        self.tools["explore_knowledge_graph"] = MCPTool(
            name="explore_knowledge_graph",
            description="Explore entity relationships and graph connections",
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity to explore"},
                    "max_depth": {"type": "integer", "default": 2, "description": "Maximum traversal depth"},
                    "relationship_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by relationship types"
                    },
                    "workspace": {"type": "string", "default": "default"}
                },
                "required": ["entity"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "entities": {"type": "array"},
                    "relationships": {"type": "array"},
                    "graph_metrics": {"type": "object"}
                }
            },
            handler=self._handle_explore_knowledge_graph
        )

        # Analytics tool
        self.tools["get_analytics"] = MCPTool(
            name="get_analytics",
            description="Get analytics and insights about documents and queries",
            input_schema={
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": ["document_stats", "query_patterns", "performance_metrics", "trend_analysis"],
                        "description": "Type of analysis to perform"
                    },
                    "time_range": {"type": "string", "description": "Time range for analysis"},
                    "workspace": {"type": "string", "default": "default"}
                },
                "required": ["analysis_type"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "analytics": {"type": "object"},
                    "visualizations": {"type": "array"},
                    "insights": {"type": "array"}
                }
            },
            handler=self._handle_get_analytics
        )

        # Document analysis tool
        self.tools["analyze_document"] = MCPTool(
            name="analyze_document",
            description="Perform deep analysis of a specific document",
            input_schema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Document ID to analyze"},
                    "analysis_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["entities", "topics", "sentiment", "summarization", "relationships"]
                        },
                        "description": "Types of analysis to perform"
                    },
                    "workspace": {"type": "string", "default": "default"}
                },
                "required": ["document_id"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "document": {"type": "object"},
                    "analysis_results": {"type": "object"},
                    "related_documents": {"type": "array"}
                }
            },
            handler=self._handle_analyze_document
        )

        # Recommendation tool
        self.tools["get_recommendations"] = MCPTool(
            name="get_recommendations",
            description="Get personalized recommendations based on user activity",
            input_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID for personalization"},
                    "recommendation_type": {
                        "type": "string",
                        "enum": ["similar_documents", "trending_topics", "research_suggestions"],
                        "description": "Type of recommendations"
                    },
                    "limit": {"type": "integer", "default": 5},
                    "workspace": {"type": "string", "default": "default"}
                },
                "required": ["user_id", "recommendation_type"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "recommendations": {"type": "array"},
                    "reasoning": {"type": "array"},
                    "confidence": {"type": "number"}
                }
            },
            handler=self._handle_get_recommendations
        )

    # MCP message handlers

    async def _handle_initialize(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle MCP initialization."""
        params = message.params or {}
        self.client_capabilities = params.get("capabilities", {})

        return self._create_response(message.id, {
            "protocolVersion": "2024-11-05",
            "capabilities": self.server_capabilities,
            "serverInfo": {
                "name": "multi-index-system",
                "version": "3.0.0",
                "description": "Multi-Index Knowledge Base System with AI Integration"
            }
        })

    async def _handle_list_tools(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle tools list request."""
        tools_list = []
        for tool_name, tool in self.tools.items():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })

        return self._create_response(message.id, {"tools": tools_list})

    async def _handle_tool_call(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle tool call request."""
        params = message.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return self._create_error_response(
                message.id, -32602, f"Tool not found: {tool_name}"
            )

        try:
            tool = self.tools[tool_name]
            if tool.handler:
                result = await tool.handler(arguments)
                return self._create_response(message.id, {"content": result})
            else:
                return self._create_error_response(
                    message.id, -32603, f"Tool handler not implemented: {tool_name}"
                )
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return self._create_error_response(
                message.id, -32603, f"Tool execution failed: {str(e)}"
            )

    async def _handle_list_resources(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle resources list request."""
        resources_list = []
        for uri, resource in self.resources.items():
            resources_list.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type
            })

        return self._create_response(message.id, {"resources": resources_list})

    async def _handle_read_resource(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle resource read request."""
        params = message.params or {}
        uri = params.get("uri")

        if uri not in self.resources:
            return self._create_error_response(
                message.id, -32602, f"Resource not found: {uri}"
            )

        try:
            resource = self.resources[uri]
            content = await self._read_resource_content(resource)

            return self._create_response(message.id, {
                "contents": [{
                    "uri": uri,
                    "mimeType": resource.mime_type,
                    "text": content
                }]
            })
        except Exception as e:
            return self._create_error_response(
                message.id, -32603, f"Failed to read resource: {str(e)}"
            )

    async def _handle_list_prompts(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle prompts list request."""
        prompts = [
            {
                "name": "document_analysis",
                "description": "Analyze a document for key insights",
                "arguments": [
                    {"name": "document_id", "description": "ID of document to analyze", "required": True}
                ]
            },
            {
                "name": "knowledge_synthesis",
                "description": "Synthesize knowledge from multiple sources",
                "arguments": [
                    {"name": "topic", "description": "Topic to synthesize", "required": True},
                    {"name": "sources", "description": "Source documents", "required": False}
                ]
            }
        ]

        return self._create_response(message.id, {"prompts": prompts})

    async def _handle_set_log_level(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle log level setting."""
        params = message.params or {}
        level = params.get("level", "INFO")

        # Set logging level
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logging.getLogger().setLevel(numeric_level)

        return self._create_response(message.id, {})

    # Tool handlers

    async def _handle_search_documents(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle document search tool."""
        query = arguments["query"]
        search_type = arguments.get("search_type", "hybrid")
        limit = arguments.get("limit", 10)
        workspace = arguments.get("workspace", "default")

        if not self.query_executor:
            raise RuntimeError("Query executor not initialized")

        # Create execution context
        context = ExecutionContext(
            user_id="mcp_agent",
            workspace=workspace,
            performance_priority="balanced"
        )

        # Execute search
        result = await self.query_executor.execute_query(
            query, {"limit": limit, "search_type": search_type}, context
        )

        # Format results for MCP
        formatted_results = []
        for doc in result.documents:
            formatted_results.append({
                "id": doc.get("id", ""),
                "title": doc.get("title", ""),
                "content": doc.get("content", "")[:500] + "...",  # Truncate content
                "relevance": doc.get("score", doc.get("relevance_score", 0)),
                "source": doc.get("source", "unknown"),
                "metadata": doc.get("metadata", {})
            })

        return [{
            "type": "text",
            "text": json.dumps({
                "results": formatted_results,
                "total_found": result.total_found,
                "execution_time": result.execution_time,
                "query_info": {
                    "original_query": query,
                    "search_type": search_type,
                    "workspace": workspace
                }
            }, indent=2)
        }]

    async def _handle_explore_knowledge_graph(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle knowledge graph exploration tool."""
        entity = arguments["entity"]
        max_depth = arguments.get("max_depth", 2)
        workspace = arguments.get("workspace", "default")

        # Mock knowledge graph exploration
        # In real implementation, this would query the graph index
        mock_response = {
            "entities": [
                {"id": entity, "name": entity, "type": "CONCEPT", "confidence": 1.0},
                {"id": f"{entity}_related_1", "name": f"Related to {entity}", "type": "CONCEPT", "confidence": 0.8}
            ],
            "relationships": [
                {
                    "source": entity,
                    "target": f"{entity}_related_1",
                    "relationship": "RELATED_TO",
                    "weight": 0.8
                }
            ],
            "graph_metrics": {
                "total_entities": 2,
                "total_relationships": 1,
                "max_depth_reached": 1
            }
        }

        return [{
            "type": "text",
            "text": json.dumps(mock_response, indent=2)
        }]

    async def _handle_get_analytics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle analytics tool."""
        analysis_type = arguments["analysis_type"]
        workspace = arguments.get("workspace", "default")

        if not self.query_executor:
            raise RuntimeError("Query executor not initialized")

        # Get execution insights
        insights = await self.query_executor.get_execution_insights()

        analytics_response = {
            "analysis_type": analysis_type,
            "workspace": workspace,
            "data": insights,
            "generated_at": datetime.now().isoformat()
        }

        return [{
            "type": "text",
            "text": json.dumps(analytics_response, indent=2)
        }]

    async def _handle_analyze_document(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle document analysis tool."""
        document_id = arguments["document_id"]
        analysis_types = arguments.get("analysis_types", ["entities", "topics"])
        workspace = arguments.get("workspace", "default")

        # Mock document analysis
        analysis_results = {
            "document_id": document_id,
            "analysis_results": {
                "entities": [
                    {"entity": "Sample Entity", "type": "PERSON", "confidence": 0.9}
                ] if "entities" in analysis_types else [],
                "topics": [
                    {"topic": "Sample Topic", "confidence": 0.8}
                ] if "topics" in analysis_types else [],
                "sentiment": {
                    "polarity": 0.1, "subjectivity": 0.5
                } if "sentiment" in analysis_types else None
            },
            "related_documents": []
        }

        return [{
            "type": "text",
            "text": json.dumps(analysis_results, indent=2)
        }]

    async def _handle_get_recommendations(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle recommendations tool."""
        user_id = arguments["user_id"]
        recommendation_type = arguments["recommendation_type"]
        limit = arguments.get("limit", 5)
        workspace = arguments.get("workspace", "default")

        # Get adaptive recommendations if available
        recommendations = []
        reasoning = []

        if self.adaptive_manager:
            try:
                # Get adaptive insights for recommendations
                insights = await self.adaptive_manager.query(
                    {"analysis_type": "pattern_analysis"}
                )

                if insights.documents:
                    patterns = insights.documents[:limit]
                    for pattern in patterns:
                        recommendations.append({
                            "type": "document_pattern",
                            "description": f"Based on query pattern: {pattern.get('query_type', 'unknown')}",
                            "confidence": pattern.get('frequency', 0) / 10.0  # Normalize
                        })
                        reasoning.append(f"Pattern frequency: {pattern.get('frequency', 0)}")

            except Exception as e:
                logger.warning(f"Failed to get adaptive recommendations: {e}")

        # Add fallback recommendations
        if not recommendations:
            recommendations = [
                {
                    "type": "trending",
                    "description": "Sample trending document",
                    "confidence": 0.7
                }
            ]
            reasoning = ["Based on general popularity"]

        response = {
            "recommendations": recommendations,
            "reasoning": reasoning,
            "confidence": sum(r.get('confidence', 0) for r in recommendations) / max(len(recommendations), 1),
            "user_id": user_id,
            "recommendation_type": recommendation_type
        }

        return [{
            "type": "text",
            "text": json.dumps(response, indent=2)
        }]

    # Helper methods

    def _create_response(self, message_id: Optional[str], result: Any) -> Dict[str, Any]:
        """Create MCP response message."""
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": result
        }

    def _create_error_response(self, message_id: Optional[str], code: int, message: str) -> Dict[str, Any]:
        """Create MCP error response."""
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    async def _read_resource_content(self, resource: MCPResource) -> str:
        """Read content for a resource."""
        # This would read actual resource content
        # For now, return mock content
        return json.dumps({
            "resource_type": resource.resource_type.value,
            "name": resource.name,
            "description": resource.description,
            "metadata": resource.metadata,
            "content": "Mock resource content"
        }, indent=2)

    def register_resource(self, resource: MCPResource):
        """Register a new resource."""
        self.resources[resource.uri] = resource

    def unregister_resource(self, uri: str):
        """Unregister a resource."""
        if uri in self.resources:
            del self.resources[uri]

    async def shutdown(self):
        """Shutdown MCP server."""
        try:
            if self.query_executor:
                # Query executor shutdown would be handled by its own cleanup
                pass

            if self.adaptive_manager:
                await self.adaptive_manager.shutdown()

            logger.info("MCP server shutdown complete")

        except Exception as e:
            logger.error(f"Error during MCP server shutdown: {e}")

class MCPClient:
    """
    MCP client for connecting to external AI services.

    Enables the multi-index system to act as an MCP client
    to integrate with AI agents and language models.
    """

    def __init__(self, server_url: str, config: Optional[Dict[str, Any]] = None):
        self.server_url = server_url
        self.config = config or {}
        self.session_id = None
        self.server_capabilities = {}

    async def connect(self) -> bool:
        """Connect to MCP server."""
        try:
            # Send initialize message
            init_message = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {"listChanged": True},
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name": "multi-index-system-client",
                        "version": "3.0.0"
                    }
                }
            }

            # In real implementation, this would use WebSocket or HTTP
            # For now, just simulate successful connection
            self.session_id = str(uuid.uuid4())
            self.server_capabilities = {
                "tools": True,
                "resources": True,
                "prompts": True
            }

            logger.info(f"Connected to MCP server at {self.server_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        if not self.session_id:
            raise RuntimeError("Not connected to MCP server")

        message = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # In real implementation, this would send the message
        # For now, return mock response
        return {
            "tool": tool_name,
            "arguments": arguments,
            "result": "Mock tool response",
            "executed_at": datetime.now().isoformat()
        }

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources on the server."""
        if not self.session_id:
            raise RuntimeError("Not connected to MCP server")

        # Mock resource list
        return [
            {
                "uri": "document://sample",
                "name": "Sample Document",
                "description": "A sample document resource",
                "mimeType": "application/json"
            }
        ]

    async def disconnect(self):
        """Disconnect from MCP server."""
        if self.session_id:
            self.session_id = None
            self.server_capabilities = {}
            logger.info("Disconnected from MCP server")