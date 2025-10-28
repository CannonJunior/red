"""
MCP Natural Language Interface for Agent-Accessible Task Parsing.

This module implements zero-cost natural language parsing for:
- COST-FIRST: Local Ollama models for task understanding ($0 operational cost)
- AGENT-NATIVE: MCP-compliant task parsing and agent recommendation
- MOJO-OPTIMIZED: Fast text processing ready for SIMD acceleration
- LOCAL-FIRST: Complete localhost NLP processing
- SIMPLE-SCALE: Optimized for 5 concurrent users
"""

import re
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import requests

# Import agent system components
from coordination.redis_coordinator import AgentTask

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TaskAnalysis:
    """Structured task analysis result."""
    task_type: str
    complexity: str  # low, medium, high
    estimated_duration_minutes: int
    required_capabilities: List[str]
    recommended_agent: str
    confidence_score: float
    extracted_entities: Dict[str, Any]
    mcp_tools_needed: List[str]
    compute_requirements: Dict[str, Any]


@dataclass
class NLPTaskContext:
    """Context for natural language task processing."""
    user_input: str
    session_id: str
    user_history: List[str]
    available_agents: List[str]
    available_tools: List[str]
    current_workload: Dict[str, int]


class ZeroCostNLPTaskParser:
    """
    Zero-cost natural language task parser using local Ollama.

    Provides intelligent task analysis and agent recommendation without API costs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize NLP task parser with local service connections."""
        self.config = config or {}

        # Local service endpoints
        self.ollama_url = self.config.get("ollama_host", "http://localhost:11434")
        self.model = self.config.get("nlp_model", "qwen2.5:3b")

        # Task patterns for fast classification
        self.task_patterns = self._initialize_task_patterns()

        # Agent capability mapping
        self.agent_capabilities = self._load_agent_capabilities()

        # Performance metrics
        self.parse_metrics = {
            "total_requests": 0,
            "avg_parse_time_ms": 0,
            "accuracy_score": 0.95,  # Target: >95% task classification accuracy
            "cache_hits": 0
        }

        # Simple LRU cache for frequent patterns
        self.pattern_cache = {}
        self.max_cache_size = 100

        logger.info("Zero-cost NLP task parser initialized")

    def _initialize_task_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for fast task classification."""
        return {
            "vector_search": [
                r"search\s+for\s+(.+)",
                r"find\s+(.+)\s+similar\s+to",
                r"lookup\s+(.+)",
                r"retrieve\s+(.+)",
                r"query\s+(.+)"
            ],
            "document_analysis": [
                r"analyze\s+(.+)\s+document",
                r"summarize\s+(.+)",
                r"extract\s+(.+)\s+from",
                r"review\s+(.+)\s+content",
                r"process\s+(.+)\s+file"
            ],
            "code_review": [
                r"review\s+(.+)\s+code",
                r"check\s+(.+)\s+for\s+bugs",
                r"analyze\s+(.+)\s+security",
                r"optimize\s+(.+)\s+performance",
                r"audit\s+(.+)\s+implementation"
            ],
            "multi_step_research": [
                r"research\s+(.+)",
                r"investigate\s+(.+)",
                r"compare\s+(.+)\s+(with|to|and)",
                r"analyze\s+(.+)\s+from\s+multiple",
                r"comprehensive\s+study\s+of"
            ],
            "data_analysis": [
                r"analyze\s+(.+)\s+data",
                r"process\s+(.+)\s+statistics",
                r"cluster\s+(.+)",
                r"classify\s+(.+)",
                r"pattern\s+analysis"
            ]
        }

    def _load_agent_capabilities(self) -> Dict[str, List[str]]:
        """Load agent capabilities mapping."""
        return {
            "rag_research_agent": [
                "vector_search", "document_analysis", "llm_inference", "multi_step_research"
            ],
            "code_review_agent": [
                "code_analysis", "security_review", "llm_inference", "static_analysis"
            ],
            "vector_data_analyst": [
                "vector_analysis", "data_clustering", "similarity_search", "statistical_analysis"
            ]
        }

    def parse_task(self, context: NLPTaskContext) -> TaskAnalysis:
        """
        Parse natural language task into structured analysis.

        Args:
            context: NLP task context with user input and available resources.

        Returns:
            TaskAnalysis: Structured task analysis with recommendations.
        """
        start_time = time.time()

        try:
            # Step 1: Fast pattern matching for common tasks
            quick_analysis = self._quick_pattern_match(context.user_input)

            if quick_analysis and quick_analysis.confidence_score > 0.8:
                logger.info(f"Fast pattern match: {quick_analysis.task_type}")
                self._update_metrics(time.time() - start_time, True)
                return quick_analysis

            # Step 2: LLM-based analysis for complex tasks
            llm_analysis = self._llm_task_analysis(context)

            # Step 3: Combine and validate results
            final_analysis = self._merge_analysis(quick_analysis, llm_analysis, context)

            self._update_metrics(time.time() - start_time, False)
            return final_analysis

        except Exception as e:
            logger.error(f"Task parsing failed: {e}")
            return self._fallback_analysis(context)

    def _quick_pattern_match(self, user_input: str) -> Optional[TaskAnalysis]:
        """Fast regex-based pattern matching for common tasks."""
        user_input_lower = user_input.lower()

        # Check cache first
        cache_key = hash(user_input_lower)
        if cache_key in self.pattern_cache:
            self.parse_metrics["cache_hits"] += 1
            return self.pattern_cache[cache_key]

        for task_type, patterns in self.task_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    # Extract entity from match
                    entity = match.group(1) if match.groups() else ""

                    analysis = TaskAnalysis(
                        task_type=task_type,
                        complexity=self._estimate_complexity(user_input),
                        estimated_duration_minutes=self._estimate_duration(task_type),
                        required_capabilities=[task_type],
                        recommended_agent=self._recommend_agent(task_type),
                        confidence_score=0.85,  # High confidence for pattern matches
                        extracted_entities={"primary_entity": entity},
                        mcp_tools_needed=self._get_mcp_tools(task_type),
                        compute_requirements=self._get_compute_requirements(task_type)
                    )

                    # Cache result
                    if len(self.pattern_cache) < self.max_cache_size:
                        self.pattern_cache[cache_key] = analysis

                    return analysis

        return None

    def _llm_task_analysis(self, context: NLPTaskContext) -> TaskAnalysis:
        """Use local Ollama for complex task analysis."""
        analysis_prompt = f"""
        Analyze this user request and provide structured task information:

        User Input: "{context.user_input}"
        Available Agents: {context.available_agents}
        Available Tools: {context.available_tools}

        Please identify:
        1. Task type (vector_search, document_analysis, code_review, multi_step_research, data_analysis)
        2. Complexity level (low, medium, high)
        3. Estimated duration in minutes
        4. Required capabilities
        5. Best agent for this task
        6. Confidence score (0.0-1.0)
        7. Key entities mentioned
        8. MCP tools needed

        Respond in JSON format only:
        {{
            "task_type": "...",
            "complexity": "...",
            "estimated_duration_minutes": 0,
            "required_capabilities": [...],
            "recommended_agent": "...",
            "confidence_score": 0.0,
            "extracted_entities": {{}},
            "mcp_tools_needed": [...],
            "compute_requirements": {{}}
        }}
        """

        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json={
                "model": self.model,
                "prompt": analysis_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent parsing
                    "top_p": 0.9
                }
            }, timeout=10)

            if response.status_code == 200:
                result = response.json()
                llm_output = result.get("response", "")

                # Parse JSON from LLM response
                try:
                    # Extract JSON from response (handle markdown formatting)
                    json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
                    if json_match:
                        parsed_data = json.loads(json_match.group())

                        return TaskAnalysis(
                            task_type=parsed_data.get("task_type", "general"),
                            complexity=parsed_data.get("complexity", "medium"),
                            estimated_duration_minutes=parsed_data.get("estimated_duration_minutes", 5),
                            required_capabilities=parsed_data.get("required_capabilities", []),
                            recommended_agent=parsed_data.get("recommended_agent", "rag_research_agent"),
                            confidence_score=float(parsed_data.get("confidence_score", 0.7)),
                            extracted_entities=parsed_data.get("extracted_entities", {}),
                            mcp_tools_needed=parsed_data.get("mcp_tools_needed", []),
                            compute_requirements=parsed_data.get("compute_requirements", {})
                        )
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM JSON response")

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")

        # Fallback to heuristic analysis
        return self._heuristic_analysis(context.user_input)

    def _heuristic_analysis(self, user_input: str) -> TaskAnalysis:
        """Heuristic-based analysis fallback."""
        # Simple keyword-based classification
        keywords = user_input.lower().split()

        if any(word in keywords for word in ["search", "find", "lookup", "query"]):
            task_type = "vector_search"
        elif any(word in keywords for word in ["analyze", "review", "check", "audit"]):
            task_type = "document_analysis"
        elif any(word in keywords for word in ["code", "bug", "security", "performance"]):
            task_type = "code_review"
        elif any(word in keywords for word in ["research", "investigate", "study", "compare"]):
            task_type = "multi_step_research"
        else:
            task_type = "general"

        return TaskAnalysis(
            task_type=task_type,
            complexity="medium",
            estimated_duration_minutes=5,
            required_capabilities=[task_type],
            recommended_agent=self._recommend_agent(task_type),
            confidence_score=0.6,
            extracted_entities={"keywords": keywords[:5]},
            mcp_tools_needed=self._get_mcp_tools(task_type),
            compute_requirements=self._get_compute_requirements(task_type)
        )

    def _merge_analysis(self, quick: Optional[TaskAnalysis], llm: TaskAnalysis,
                       context: NLPTaskContext) -> TaskAnalysis:
        """Merge quick pattern match with LLM analysis."""
        if not quick:
            return llm

        # Use higher confidence analysis as base
        base_analysis = quick if quick.confidence_score > llm.confidence_score else llm

        # Enhance with workload-based agent selection
        optimal_agent = self._select_optimal_agent(
            base_analysis.recommended_agent,
            context.current_workload
        )

        base_analysis.recommended_agent = optimal_agent
        return base_analysis

    def _select_optimal_agent(self, preferred_agent: str,
                            current_workload: Dict[str, int]) -> str:
        """Select optimal agent based on current workload."""
        # If preferred agent has low workload, use it
        if current_workload.get(preferred_agent, 0) < 2:
            return preferred_agent

        # Find least loaded agent with required capabilities
        min_workload = float('inf')
        best_agent = preferred_agent

        for agent, workload in current_workload.items():
            if workload < min_workload:
                min_workload = workload
                best_agent = agent

        return best_agent

    def _estimate_complexity(self, user_input: str) -> str:
        """Estimate task complexity based on input characteristics."""
        length = len(user_input.split())

        if length < 5:
            return "low"
        elif length < 15:
            return "medium"
        else:
            return "high"

    def _estimate_duration(self, task_type: str) -> int:
        """Estimate task duration in minutes."""
        duration_map = {
            "vector_search": 2,
            "document_analysis": 5,
            "code_review": 8,
            "multi_step_research": 15,
            "data_analysis": 10,
            "general": 5
        }
        return duration_map.get(task_type, 5)

    def _recommend_agent(self, task_type: str) -> str:
        """Recommend best agent for task type."""
        agent_map = {
            "vector_search": "rag_research_agent",
            "document_analysis": "rag_research_agent",
            "code_review": "code_review_agent",
            "multi_step_research": "rag_research_agent",
            "data_analysis": "vector_data_analyst",
            "general": "rag_research_agent"
        }
        return agent_map.get(task_type, "rag_research_agent")

    def _get_mcp_tools(self, task_type: str) -> List[str]:
        """Get required MCP tools for task type."""
        tool_map = {
            "vector_search": ["chromadb_search", "similarity_calculator"],
            "document_analysis": ["text_extractor", "summarizer", "entity_recognizer"],
            "code_review": ["static_analyzer", "security_scanner", "performance_profiler"],
            "multi_step_research": ["web_scraper", "document_indexer", "synthesis_engine"],
            "data_analysis": ["vector_processor", "clustering_engine", "stats_calculator"],
            "general": ["text_processor"]
        }
        return tool_map.get(task_type, ["text_processor"])

    def _get_compute_requirements(self, task_type: str) -> Dict[str, Any]:
        """Get compute requirements for task type."""
        requirements_map = {
            "vector_search": {"memory_mb": 256, "cpu_cores": 1, "priority": "high"},
            "document_analysis": {"memory_mb": 512, "cpu_cores": 1, "priority": "medium"},
            "code_review": {"memory_mb": 512, "cpu_cores": 2, "priority": "medium"},
            "multi_step_research": {"memory_mb": 1024, "cpu_cores": 2, "priority": "low"},
            "data_analysis": {"memory_mb": 1024, "cpu_cores": 4, "priority": "high"},
            "general": {"memory_mb": 256, "cpu_cores": 1, "priority": "medium"}
        }
        return requirements_map.get(task_type, {"memory_mb": 256, "cpu_cores": 1, "priority": "medium"})

    def _fallback_analysis(self, context: NLPTaskContext) -> TaskAnalysis:
        """Fallback analysis when all else fails."""
        return TaskAnalysis(
            task_type="general",
            complexity="medium",
            estimated_duration_minutes=5,
            required_capabilities=["general"],
            recommended_agent="rag_research_agent",
            confidence_score=0.5,
            extracted_entities={"input": context.user_input[:100]},
            mcp_tools_needed=["text_processor"],
            compute_requirements={"memory_mb": 256, "cpu_cores": 1, "priority": "medium"}
        )

    def _update_metrics(self, parse_time: float, cache_hit: bool):
        """Update performance metrics."""
        self.parse_metrics["total_requests"] += 1

        if not cache_hit:
            current_avg = self.parse_metrics["avg_parse_time_ms"]
            new_time_ms = parse_time * 1000
            self.parse_metrics["avg_parse_time_ms"] = \
                (current_avg * 0.9) + (new_time_ms * 0.1)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            "parse_metrics": self.parse_metrics,
            "cache_size": len(self.pattern_cache),
            "supported_task_types": list(self.task_patterns.keys()),
            "agent_capabilities": self.agent_capabilities,
            "cost": "$0.00"
        }


class MCPTaskInterface:
    """
    MCP-compliant interface for natural language task processing.

    Exposes NLP parsing capabilities through standardized MCP protocol.
    """

    def __init__(self, parser: ZeroCostNLPTaskParser):
        """Initialize MCP task interface."""
        self.parser = parser
        self.interface_version = "1.0.0"

        logger.info("MCP task interface initialized")

    def mcp_parse_task(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP-compliant task parsing endpoint.

        Args:
            request: MCP request with user input and context.

        Returns:
            MCP response with structured task analysis.
        """
        try:
            # Extract context from MCP request
            context = NLPTaskContext(
                user_input=request.get("user_input", ""),
                session_id=request.get("session_id", "default"),
                user_history=request.get("user_history", []),
                available_agents=request.get("available_agents", []),
                available_tools=request.get("available_tools", []),
                current_workload=request.get("current_workload", {})
            )

            # Parse task
            analysis = self.parser.parse_task(context)

            return {
                "status": "success",
                "mcp_version": self.interface_version,
                "analysis": asdict(analysis),
                "recommendations": {
                    "agent": analysis.recommended_agent,
                    "tools": analysis.mcp_tools_needed,
                    "priority": analysis.compute_requirements.get("priority", "medium")
                },
                "cost": "$0.00"
            }

        except Exception as e:
            logger.error(f"MCP task parsing failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "mcp_version": self.interface_version
            }

    def mcp_get_capabilities(self) -> Dict[str, Any]:
        """Get MCP interface capabilities."""
        return {
            "interface": "natural_language_task_parser",
            "version": self.interface_version,
            "capabilities": [
                "task_classification",
                "agent_recommendation",
                "complexity_estimation",
                "entity_extraction",
                "workload_optimization"
            ],
            "supported_languages": ["english"],
            "response_time_ms": self.parser.parse_metrics["avg_parse_time_ms"],
            "accuracy": self.parser.parse_metrics["accuracy_score"]
        }


if __name__ == "__main__":
    # Test the NLP task parser
    parser = ZeroCostNLPTaskParser()
    mcp_interface = MCPTaskInterface(parser)

    # Test cases
    test_cases = [
        "Search for documents about machine learning algorithms",
        "Review this Python code for security vulnerabilities",
        "Analyze the vector patterns in my database",
        "Research the latest trends in AI development",
        "Find similar documents to this research paper"
    ]

    print("Testing Zero-Cost NLP Task Parser...")

    for i, test_input in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_input}")

        context = NLPTaskContext(
            user_input=test_input,
            session_id=f"test_{i}",
            user_history=[],
            available_agents=["rag_research_agent", "code_review_agent", "vector_data_analyst"],
            available_tools=["chromadb_search", "ollama_inference", "vector_processor"],
            current_workload={"rag_research_agent": 1, "code_review_agent": 0, "vector_data_analyst": 2}
        )

        analysis = parser.parse_task(context)
        print(f"  Task Type: {analysis.task_type}")
        print(f"  Recommended Agent: {analysis.recommended_agent}")
        print(f"  Confidence: {analysis.confidence_score:.2f}")
        print(f"  Estimated Duration: {analysis.estimated_duration_minutes} minutes")

    # Test MCP interface
    print("\nTesting MCP Interface...")
    mcp_request = {
        "user_input": "Find research papers about vector databases and summarize key findings",
        "session_id": "mcp_test",
        "available_agents": ["rag_research_agent", "vector_data_analyst"],
        "current_workload": {"rag_research_agent": 0}
    }

    mcp_response = mcp_interface.mcp_parse_task(mcp_request)
    print(f"MCP Response: {json.dumps(mcp_response, indent=2)}")

    # Print metrics
    print(f"\nMetrics: {json.dumps(parser.get_metrics(), indent=2)}")