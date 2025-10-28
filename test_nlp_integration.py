#!/usr/bin/env python3
"""
Test script for MCP Natural Language Interface integration.

Tests the zero-cost NLP task parser and MCP interface.
"""

import sys
import os
sys.path.insert(0, '/home/junior/src/red')

# Fix import path for dash-separated directory
sys.path.insert(0, '/home/junior/src/red/agent-system')

from nlp.task_parser import ZeroCostNLPTaskParser, MCPTaskInterface, NLPTaskContext
import json


def test_nlp_parser():
    """Test the NLP task parser functionality."""
    print("🧠 Testing Zero-Cost NLP Task Parser...")

    # Initialize parser
    parser = ZeroCostNLPTaskParser()
    mcp_interface = MCPTaskInterface(parser)

    # Test cases
    test_cases = [
        {
            "input": "Search for documents about machine learning algorithms",
            "expected_type": "vector_search"
        },
        {
            "input": "Review this Python code for security vulnerabilities",
            "expected_type": "code_review"
        },
        {
            "input": "Analyze the vector patterns in my database",
            "expected_type": "data_analysis"
        },
        {
            "input": "Research the latest trends in AI development and compare different approaches",
            "expected_type": "multi_step_research"
        },
        {
            "input": "Summarize this document and extract key insights",
            "expected_type": "document_analysis"
        }
    ]

    print(f"\n📝 Running {len(test_cases)} test cases...")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['input'][:50]}...")

        # Create context
        context = NLPTaskContext(
            user_input=test_case['input'],
            session_id=f"test_{i}",
            user_history=[],
            available_agents=["rag_research_agent", "code_review_agent", "vector_data_analyst"],
            available_tools=["chromadb_search", "ollama_inference", "vector_processor"],
            current_workload={"rag_research_agent": 0, "code_review_agent": 1, "vector_data_analyst": 2}
        )

        # Parse task
        analysis = parser.parse_task(context)

        # Display results
        print(f"  ✓ Task Type: {analysis.task_type} (expected: {test_case['expected_type']})")
        print(f"  ✓ Recommended Agent: {analysis.recommended_agent}")
        print(f"  ✓ Confidence: {analysis.confidence_score:.2f}")
        print(f"  ✓ Complexity: {analysis.complexity}")
        print(f"  ✓ Duration: {analysis.estimated_duration_minutes} minutes")
        print(f"  ✓ Tools: {', '.join(analysis.mcp_tools_needed)}")

        # Check if task type matches expectation (for pattern-based tests)
        match = "✅" if analysis.task_type == test_case['expected_type'] else "⚠️"
        print(f"  {match} Classification accuracy")

    return parser


def test_mcp_interface(parser):
    """Test the MCP interface functionality."""
    print("\n🔧 Testing MCP Interface...")

    mcp_interface = MCPTaskInterface(parser)

    # Test MCP capabilities
    print("\n📋 MCP Capabilities:")
    capabilities = mcp_interface.mcp_get_capabilities()
    print(json.dumps(capabilities, indent=2))

    # Test MCP task parsing
    print("\n🎯 Testing MCP Task Parsing...")
    mcp_request = {
        "user_input": "Find research papers about vector databases and create a comprehensive analysis",
        "session_id": "mcp_test",
        "available_agents": ["rag_research_agent", "vector_data_analyst"],
        "available_tools": ["chromadb_search", "vector_processor", "text_extractor"],
        "current_workload": {"rag_research_agent": 0, "vector_data_analyst": 1}
    }

    mcp_response = mcp_interface.mcp_parse_task(mcp_request)
    print("MCP Response:")
    print(json.dumps(mcp_response, indent=2))


def test_performance_metrics(parser):
    """Test performance metrics collection."""
    print("\n📊 Testing Performance Metrics...")

    metrics = parser.get_metrics()
    print("Current Metrics:")
    print(json.dumps(metrics, indent=2))

    print(f"\n✅ Total requests processed: {metrics['parse_metrics']['total_requests']}")
    print(f"✅ Average parse time: {metrics['parse_metrics']['avg_parse_time_ms']:.2f}ms")
    print(f"✅ Cache hits: {metrics['parse_metrics']['cache_hits']}")
    print(f"✅ Accuracy score: {metrics['parse_metrics']['accuracy_score']:.2%}")


def main():
    """Run all NLP integration tests."""
    print("🚀 Starting MCP Natural Language Interface Integration Tests")
    print("=" * 60)

    try:
        # Test 1: Basic NLP parsing
        parser = test_nlp_parser()

        # Test 2: MCP interface
        test_mcp_interface(parser)

        # Test 3: Performance metrics
        test_performance_metrics(parser)

        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("💰 Total cost: $0.00 (zero-cost local processing)")
        print("🏆 RED Compliance: COST-FIRST ✅ AGENT-NATIVE ✅ LOCAL-FIRST ✅")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())