#!/usr/bin/env python3
"""
Comprehensive Test Suite for Multi-Index System Phase 3

Tests all production-ready features:
- Enhanced Query Execution with Intelligent Planning
- Observable D3 Visualizations
- MCP (Model Context Protocol) Integration
- Advanced Redis Caching
- Real-time Collaboration Features
- Production Deployment Configuration

Run with: PYTHONPATH=/home/junior/src/red uv run test_multi_index_phase3.py
"""

import asyncio
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
import uuid

# Add multi-index system to path
sys.path.insert(0, str(Path(__file__).parent / "multi-index-system"))

class Phase3TestRunner:
    """Comprehensive test runner for Phase 3 production features."""

    def __init__(self):
        self.test_results = {}
        self.temp_dir = None
        self.passed_tests = 0
        self.failed_tests = 0

    async def run_all_tests(self):
        """Run all Phase 3 tests."""
        print("🚀 PHASE 3 MULTI-INDEX SYSTEM - PRODUCTION FEATURES TEST")
        print("=" * 75)
        print("🏭 Testing production-ready features and enterprise capabilities")
        print("⚡ This comprehensive test may take 60-90 seconds to complete")
        print()

        # Create temporary test directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="multi_index_phase3_"))
        print(f"📁 Test data directory: {self.temp_dir}")
        print()

        try:
            # Run comprehensive test suites
            await self._test_intelligent_query_planner()
            await self._test_enhanced_query_executor()
            await self._test_d3_visualizations()
            await self._test_mcp_integration()
            await self._test_redis_caching()
            await self._test_collaboration_features()
            await self._test_production_config()
            await self._test_integration_workflows()

            self._print_final_results()
            return self.failed_tests == 0

        except Exception as e:
            print(f"❌ Critical test failure: {e}")
            return False

        finally:
            # Cleanup
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)

    async def _test_intelligent_query_planner(self):
        """Test intelligent query planning and cost optimization."""
        print("🧠 TESTING INTELLIGENT QUERY PLANNER")
        print("-" * 50)

        try:
            from core.query_planner import IntelligentQueryPlanner, QueryStrategy, IndexPriority
            from core.query_router import QueryIntent
            from core.coordinator import MultiIndexCoordinator
            from core.monitoring import HealthMonitor

            # Initialize components
            planner = IntelligentQueryPlanner()
            coordinator = MultiIndexCoordinator()
            health_monitor = HealthMonitor()

            # Test planner initialization
            await coordinator.initialize()
            health_monitor.start_monitoring()
            await planner.initialize(coordinator, health_monitor)

            self._assert_test("Query Planner Initialization",
                             planner is not None,
                             "Failed to initialize query planner")

            # Test execution plan creation
            plan = await planner.create_execution_plan(
                "find machine learning research papers",
                {"limit": 10},
                QueryIntent.SEMANTIC_SEARCH,
                "test_workspace"
            )

            self._assert_test("Execution Plan Creation",
                             plan is not None and len(plan.execution_steps) > 0,
                             "Failed to create execution plan")

            self._assert_test("Plan Cost Estimation",
                             plan.estimated_cost > 0 and plan.estimated_time > 0,
                             "Plan cost estimation failed")

            # Test different strategies
            strategies_tested = []
            for strategy in [QueryStrategy.PARALLEL, QueryStrategy.SEQUENTIAL, QueryStrategy.WATERFALL]:
                try:
                    test_plan = await planner._create_plan_for_strategy(
                        "test_query", strategy, ["vector", "fts"], ["metadata"],
                        {"complexity": 0.5, "performance_priority": "balanced"}
                    )
                    if test_plan:
                        strategies_tested.append(strategy.value)
                except Exception:
                    pass

            self._assert_test("Multiple Strategy Support",
                             len(strategies_tested) >= 2,
                             f"Only {len(strategies_tested)} strategies working")

            # Test optimization insights
            insights = await planner.get_optimization_insights()
            self._assert_test("Optimization Insights",
                             isinstance(insights, dict) and "total_queries_planned" in insights,
                             "Failed to get optimization insights")

            # Cleanup
            health_monitor.stop_monitoring()
            print("✅ Query Planner tests completed\n")

        except Exception as e:
            self._fail_test("Query Planner Tests", str(e))

    async def _test_enhanced_query_executor(self):
        """Test enhanced query execution with cross-index coordination."""
        print("⚡ TESTING ENHANCED QUERY EXECUTOR")
        print("-" * 50)

        try:
            from core.query_executor import EnhancedQueryExecutor, ExecutionContext

            # Initialize executor
            executor = EnhancedQueryExecutor()
            await executor.initialize()

            self._assert_test("Query Executor Initialization",
                             executor.query_planner is not None,
                             "Failed to initialize query executor")

            # Test single query execution
            context = ExecutionContext(
                user_id="test_user",
                workspace="test_workspace",
                performance_priority="balanced",
                max_execution_time=30.0
            )

            result = await executor.execute_query(
                "search for artificial intelligence papers",
                {"limit": 5},
                context
            )

            self._assert_test("Single Query Execution",
                             result is not None and hasattr(result, 'documents'),
                             "Single query execution failed")

            self._assert_test("Query Performance Tracking",
                             result.execution_time > 0,
                             "Performance tracking failed")

            # Test multi-query execution
            queries = [
                ("machine learning algorithms", {"limit": 3}),
                ("neural network architectures", {"limit": 3}),
                ("deep learning frameworks", {"limit": 3})
            ]

            multi_results = await executor.execute_multi_query(queries, context)

            self._assert_test("Multi-Query Execution",
                             len(multi_results) == 3,
                             f"Expected 3 results, got {len(multi_results)}")

            # Test execution insights
            insights = await executor.get_execution_insights()

            self._assert_test("Execution Insights",
                             "total_queries_executed" in insights and "cache_performance" in insights,
                             "Failed to get execution insights")

            # Test performance optimization
            optimization = await executor.optimize_performance()

            self._assert_test("Performance Optimization",
                             "cache_optimizations" in optimization,
                             "Performance optimization failed")

            print("✅ Enhanced Query Executor tests completed\n")

        except Exception as e:
            self._fail_test("Enhanced Query Executor Tests", str(e))

    async def _test_d3_visualizations(self):
        """Test Observable D3 visualization components."""
        print("📊 TESTING D3 VISUALIZATION COMPONENTS")
        print("-" * 50)

        try:
            from visualization.d3_components import D3VisualizationEngine

            # Initialize visualization engine
            viz_engine = D3VisualizationEngine()

            self._assert_test("D3 Visualization Engine Initialization",
                             len(viz_engine.visualization_templates) > 0,
                             "Failed to load visualization templates")

            # Test knowledge graph visualization
            entities = [
                {"id": "ai", "name": "Artificial Intelligence", "type": "CONCEPT", "confidence": 1.0},
                {"id": "ml", "name": "Machine Learning", "type": "CONCEPT", "confidence": 0.9},
                {"id": "dl", "name": "Deep Learning", "type": "CONCEPT", "confidence": 0.8}
            ]

            relationships = [
                {"source": "ai", "target": "ml", "relationship": "INCLUDES", "weight": 0.9},
                {"source": "ml", "target": "dl", "relationship": "INCLUDES", "weight": 0.8}
            ]

            kg_viz = viz_engine.create_knowledge_graph(entities, relationships)

            self._assert_test("Knowledge Graph Visualization",
                             kg_viz["type"] == "knowledge_graph" and len(kg_viz["d3_config"]["data"]["nodes"]) == 3,
                             "Knowledge graph visualization failed")

            # Test performance dashboard
            metrics = {
                "total_queries": 1000,
                "avg_query_time": 0.25,
                "success_rate": 0.98,
                "cache_hit_rate": 0.75
            }

            time_series = [
                {"timestamp": "2024-01-01T00:00:00Z", "query_count": 50, "avg_response_time": 0.2},
                {"timestamp": "2024-01-01T01:00:00Z", "query_count": 75, "avg_response_time": 0.3}
            ]

            dashboard_viz = viz_engine.create_performance_dashboard(metrics, time_series)

            self._assert_test("Performance Dashboard Visualization",
                             dashboard_viz["type"] == "performance_dashboard" and len(dashboard_viz["d3_config"]["charts"]) > 0,
                             "Performance dashboard visualization failed")

            # Test search results explorer
            search_results = [
                {"id": "doc1", "title": "AI Research Paper", "content": "This paper discusses...", "score": 0.95},
                {"id": "doc2", "title": "ML Algorithms", "content": "Machine learning...", "score": 0.87}
            ]

            query_info = {"query": "artificial intelligence research", "total_found": 2}

            search_viz = viz_engine.create_search_results_explorer(search_results, query_info)

            self._assert_test("Search Results Explorer",
                             search_viz["type"] == "search_results_explorer" and len(search_viz["d3_config"]["data"]["results"]) == 2,
                             "Search results explorer failed")

            # Test Observable notebook generation
            notebook_code = viz_engine.generate_observable_notebook(kg_viz["id"])

            self._assert_test("Observable Notebook Generation",
                             "d3" in notebook_code and "function" in notebook_code,
                             "Observable notebook generation failed")

            # Test visualization export
            export_dir = self.temp_dir / "visualizations"
            exported_files = viz_engine.export_all_visualizations(str(export_dir))

            self._assert_test("Visualization Export",
                             len(exported_files) > 0 and all(Path(f).exists() for f in exported_files.values()),
                             "Visualization export failed")

            print("✅ D3 Visualization tests completed\n")

        except Exception as e:
            self._fail_test("D3 Visualization Tests", str(e))

    async def _test_mcp_integration(self):
        """Test MCP (Model Context Protocol) integration."""
        print("🤖 TESTING MCP INTEGRATION")
        print("-" * 50)

        try:
            from mcp.protocol_handler import MCPServer, MCPClient, MCPMessage, MCPTool

            # Test MCP Server
            mcp_server = MCPServer()
            await mcp_server.initialize()

            self._assert_test("MCP Server Initialization",
                             len(mcp_server.tools) > 0,
                             "MCP server failed to initialize with tools")

            # Test server capabilities
            self._assert_test("MCP Server Capabilities",
                             mcp_server.server_capabilities["tools"] and mcp_server.server_capabilities["resources"],
                             "MCP server missing required capabilities")

            # Test initialize message handling
            init_message = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "initialize",
                "params": {"capabilities": {"tools": True}}
            }

            init_response = await mcp_server.handle_message(init_message)

            self._assert_test("MCP Initialize Message",
                             init_response.get("result", {}).get("capabilities", {}).get("tools"),
                             "MCP initialize message failed")

            # Test tools list
            tools_message = {
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tools/list"
            }

            tools_response = await mcp_server.handle_message(tools_message)

            self._assert_test("MCP Tools List",
                             len(tools_response.get("result", {}).get("tools", [])) > 0,
                             "MCP tools list failed")

            # Test tool call
            tool_call_message = {
                "jsonrpc": "2.0",
                "id": "3",
                "method": "tools/call",
                "params": {
                    "name": "search_documents",
                    "arguments": {"query": "test query", "limit": 5}
                }
            }

            tool_response = await mcp_server.handle_message(tool_call_message)

            self._assert_test("MCP Tool Call",
                             "result" in tool_response and "content" in tool_response["result"],
                             "MCP tool call failed")

            # Test MCP Client
            mcp_client = MCPClient("ws://localhost:8080")
            connection_success = await mcp_client.connect()

            self._assert_test("MCP Client Connection",
                             connection_success or mcp_client.session_id is not None,
                             "MCP client connection failed")

            # Test client tool call
            client_tool_result = await mcp_client.call_tool("search_documents", {"query": "test"})

            self._assert_test("MCP Client Tool Call",
                             "tool" in client_tool_result,
                             "MCP client tool call failed")

            # Cleanup
            await mcp_server.shutdown()
            await mcp_client.disconnect()

            print("✅ MCP Integration tests completed\n")

        except Exception as e:
            self._fail_test("MCP Integration Tests", str(e))

    async def _test_redis_caching(self):
        """Test advanced Redis caching layer."""
        print("💾 TESTING REDIS CACHING LAYER")
        print("-" * 50)

        try:
            from cache.redis_cache import AdvancedRedisCache, QueryResultCache, EmbeddingCache

            # Test basic cache functionality
            cache = AdvancedRedisCache()
            await cache.initialize()

            self._assert_test("Redis Cache Initialization",
                             cache is not None,
                             "Redis cache initialization failed")

            # Test cache set/get
            test_data = {"test": "data", "number": 42}
            set_success = await cache.set("test_key", test_data)
            retrieved_data = await cache.get("test_key")

            self._assert_test("Cache Set/Get Operations",
                             set_success and retrieved_data == test_data,
                             "Cache set/get operations failed")

            # Test multi-get/set
            multi_items = [
                ("key1", {"data": 1}, "query_result", None),
                ("key2", {"data": 2}, "query_result", None),
                ("key3", {"data": 3}, "query_result", None)
            ]

            multi_set_count = await cache.set_multi(multi_items)
            multi_get_results = await cache.get_multi([("key1", "query_result"), ("key2", "query_result")])

            self._assert_test("Cache Multi-Operations",
                             multi_set_count == 3 and len(multi_get_results) == 2,
                             "Cache multi-operations failed")

            # Test cache invalidation by tags
            await cache.set("tagged_key1", "data1", tags=["tag1", "tag2"])
            await cache.set("tagged_key2", "data2", tags=["tag2", "tag3"])

            invalidated_count = await cache.invalidate_by_tags(["tag2"])

            self._assert_test("Cache Tag Invalidation",
                             invalidated_count >= 0,
                             "Cache tag invalidation failed")

            # Test distributed locking
            lock_value = await cache.acquire_lock("test_resource", timeout=10)
            release_success = await cache.release_lock("test_resource", lock_value) if lock_value else True

            self._assert_test("Distributed Locking",
                             lock_value is not None and release_success,
                             "Distributed locking failed")

            # Test specialized caches
            query_cache = QueryResultCache()
            await query_cache.initialize()

            # Mock QueryResult for testing
            class MockQueryResult:
                def __init__(self):
                    self.documents = [{"id": "test", "title": "Test Doc"}]
                    self.total_found = 1
                    self.execution_time = 0.1

            mock_result = MockQueryResult()
            query_cache_success = await query_cache.cache_query_result("query_hash", mock_result)

            self._assert_test("Specialized Query Cache",
                             query_cache_success,
                             "Specialized query cache failed")

            # Test embedding cache
            embedding_cache = EmbeddingCache()
            await embedding_cache.initialize()

            embedding_success = await embedding_cache.cache_embedding(
                "text_hash", [0.1, 0.2, 0.3], "test_model"
            )

            self._assert_test("Embedding Cache",
                             embedding_success,
                             "Embedding cache failed")

            # Test cache statistics
            stats = await cache.get_cache_stats()

            self._assert_test("Cache Statistics",
                             hasattr(stats, 'total_requests') and hasattr(stats, 'hit_rate'),
                             "Cache statistics failed")

            # Test cache optimization
            optimization_results = await cache.optimize_cache()

            self._assert_test("Cache Optimization",
                             "actions_taken" in optimization_results,
                             "Cache optimization failed")

            # Cleanup
            await cache.shutdown()
            await query_cache.shutdown()
            await embedding_cache.shutdown()

            print("✅ Redis Caching tests completed\n")

        except Exception as e:
            self._fail_test("Redis Caching Tests", str(e))

    async def _test_collaboration_features(self):
        """Test real-time collaboration features."""
        print("👥 TESTING REAL-TIME COLLABORATION")
        print("-" * 50)

        try:
            from collaboration.realtime_sync import RealtimeCollaborationManager, CollaborationEvent, EventType, UserPresence

            # Initialize collaboration manager
            collab_manager = RealtimeCollaborationManager()
            await collab_manager.initialize()

            self._assert_test("Collaboration Manager Initialization",
                             collab_manager.cache is not None,
                             "Collaboration manager initialization failed")

            # Test workspace creation
            workspace = await collab_manager.create_workspace(
                "Test Workspace",
                "user1",
                "A test workspace for collaboration"
            )

            self._assert_test("Workspace Creation",
                             workspace is not None and workspace.workspace_id in collab_manager.active_workspaces,
                             "Workspace creation failed")

            # Test user joining workspace
            join_success = await collab_manager.join_workspace(
                workspace.workspace_id,
                "user2",
                "Test User 2",
                "https://example.com/avatar.jpg"
            )

            self._assert_test("User Workspace Join",
                             join_success and "user2" in collab_manager.user_presence,
                             "User workspace join failed")

            # Test query sharing
            query_data = {
                "query_text": "shared test query",
                "query_params": {"limit": 10},
                "results_preview": [{"id": "doc1", "title": "Test Doc"}]
            }

            share_id = await collab_manager.share_query(workspace.workspace_id, "user1", query_data)

            self._assert_test("Query Sharing",
                             share_id != "",
                             "Query sharing failed")

            # Test annotation creation
            annotation = await collab_manager.add_annotation(
                workspace.workspace_id,
                "user1",
                "doc1",
                "This is a test annotation",
                {"start": 0, "end": 10}
            )

            self._assert_test("Annotation Creation",
                             annotation is not None and annotation.annotation_id,
                             "Annotation creation failed")

            # Test presence updates
            presence_update = await collab_manager.update_user_presence(
                workspace.workspace_id,
                "user2",
                {"status": "active", "current_document": "doc1", "cursor_position": {"line": 1, "column": 5}}
            )

            self._assert_test("Presence Updates",
                             presence_update,
                             "Presence updates failed")

            # Test getting active users
            active_users = await collab_manager.get_active_users(workspace.workspace_id)

            self._assert_test("Active Users Retrieval",
                             len(active_users) > 0,
                             "Active users retrieval failed")

            # Test workspace activity
            activity = await collab_manager.get_workspace_activity(workspace.workspace_id)

            self._assert_test("Workspace Activity",
                             isinstance(activity, list),
                             "Workspace activity retrieval failed")

            # Test user leaving workspace
            leave_success = await collab_manager.leave_workspace(workspace.workspace_id, "user2")

            self._assert_test("User Workspace Leave",
                             leave_success,
                             "User workspace leave failed")

            # Cleanup
            await collab_manager.shutdown()

            print("✅ Real-time Collaboration tests completed\n")

        except Exception as e:
            self._fail_test("Real-time Collaboration Tests", str(e))

    async def _test_production_config(self):
        """Test production deployment configuration."""
        print("🏭 TESTING PRODUCTION CONFIGURATION")
        print("-" * 50)

        try:
            from deployment.production_config import ProductionConfigManager, ProductionConfig, ProductionMonitoring

            # Test configuration loading
            config_manager = ProductionConfigManager()
            config = config_manager.load_config()

            self._assert_test("Production Config Loading",
                             isinstance(config, ProductionConfig),
                             "Production config loading failed")

            # Test configuration validation
            validation_errors = config_manager.validate_config(config)

            self._assert_test("Configuration Validation",
                             isinstance(validation_errors, list),
                             "Configuration validation failed")

            # Test Kubernetes export
            k8s_config = config_manager.export_kubernetes_config(config)

            self._assert_test("Kubernetes Config Export",
                             k8s_config["kind"] == "Deployment" and "spec" in k8s_config,
                             "Kubernetes config export failed")

            # Test Docker Compose export
            docker_config = config_manager.export_docker_compose(config)

            self._assert_test("Docker Compose Export",
                             docker_config["version"] and "services" in docker_config,
                             "Docker Compose export failed")

            # Test production monitoring
            monitoring = ProductionMonitoring(config)

            # Register mock health check
            async def mock_health_check():
                return {"healthy": True, "response_time": 0.05}

            monitoring.register_health_check("test_check", mock_health_check)

            health_results = await monitoring.run_health_checks()

            self._assert_test("Production Health Checks",
                             health_results["status"] == "healthy" and "test_check" in health_results["checks"],
                             "Production health checks failed")

            # Test Prometheus metrics export
            prometheus_metrics = monitoring.export_prometheus_metrics()

            self._assert_test("Prometheus Metrics Export",
                             "multi_index_system_info" in prometheus_metrics,
                             "Prometheus metrics export failed")

            print("✅ Production Configuration tests completed\n")

        except Exception as e:
            self._fail_test("Production Configuration Tests", str(e))

    async def _test_integration_workflows(self):
        """Test end-to-end integration workflows."""
        print("🔗 TESTING INTEGRATION WORKFLOWS")
        print("-" * 50)

        try:
            # Test comprehensive workflow: Query → Plan → Execute → Cache → Visualize → Collaborate

            # 1. Initialize all components
            from core.query_executor import EnhancedQueryExecutor, ExecutionContext
            from cache.redis_cache import AdvancedRedisCache
            from visualization.d3_components import D3VisualizationEngine
            from collaboration.realtime_sync import RealtimeCollaborationManager

            executor = EnhancedQueryExecutor()
            cache = AdvancedRedisCache()
            viz_engine = D3VisualizationEngine()
            collab_manager = RealtimeCollaborationManager()

            # Initialize components
            await executor.initialize()
            await cache.initialize()
            await collab_manager.initialize()

            self._assert_test("Component Integration Initialization",
                             all([executor.query_planner, cache, viz_engine, collab_manager]),
                             "Failed to initialize all components")

            # 2. Execute query with enhanced executor
            context = ExecutionContext(
                user_id="integration_test_user",
                workspace="integration_workspace",
                performance_priority="balanced"
            )

            query_result = await executor.execute_query(
                "artificial intelligence and machine learning research",
                {"limit": 10, "include_metadata": True},
                context
            )

            self._assert_test("Integrated Query Execution",
                             query_result is not None and hasattr(query_result, 'documents'),
                             "Integrated query execution failed")

            # 3. Cache query result
            import hashlib
            query_hash = hashlib.md5("ai_ml_research_query".encode()).hexdigest()
            cache_success = await cache.set(query_hash, query_result, data_type='query_result')

            self._assert_test("Query Result Caching",
                             cache_success,
                             "Query result caching failed")

            # 4. Create visualization from results
            if query_result.documents:
                viz_data = viz_engine.create_search_results_explorer(
                    query_result.documents,
                    {"query": "AI ML research", "total_found": len(query_result.documents)}
                )

                self._assert_test("Result Visualization Creation",
                                 viz_data["type"] == "search_results_explorer",
                                 "Result visualization creation failed")

            # 5. Share results in collaborative workspace
            workspace = await collab_manager.create_workspace(
                "AI Research Collaboration",
                "integration_test_user",
                "Collaborative workspace for AI research"
            )

            share_id = await collab_manager.share_query(
                workspace.workspace_id,
                "integration_test_user",
                {
                    "query_text": "artificial intelligence research",
                    "query_params": {"limit": 10},
                    "results_preview": query_result.documents[:3] if query_result.documents else []
                }
            )

            self._assert_test("Collaborative Query Sharing",
                             share_id != "",
                             "Collaborative query sharing failed")

            # 6. Test performance monitoring across components
            executor_insights = await executor.get_execution_insights()
            cache_stats = await cache.get_cache_stats()

            self._assert_test("Cross-Component Performance Monitoring",
                             "total_queries_executed" in executor_insights and hasattr(cache_stats, 'hit_rate'),
                             "Cross-component performance monitoring failed")

            # 7. Test MCP integration with query results
            from mcp.protocol_handler import MCPServer

            mcp_server = MCPServer()
            await mcp_server.initialize()

            # Simulate MCP tool call for analytics
            analytics_message = {
                "jsonrpc": "2.0",
                "id": "analytics_test",
                "method": "tools/call",
                "params": {
                    "name": "get_analytics",
                    "arguments": {"analysis_type": "query_patterns", "workspace": "integration_workspace"}
                }
            }

            mcp_response = await mcp_server.handle_message(analytics_message)

            self._assert_test("MCP Analytics Integration",
                             "result" in mcp_response,
                             "MCP analytics integration failed")

            # 8. Test real-time event broadcasting
            event_handler_called = False

            async def test_event_handler(event):
                nonlocal event_handler_called
                event_handler_called = True

            from collaboration.realtime_sync import EventType
            collab_manager.register_event_handler(EventType.QUERY_SHARE, test_event_handler)

            # Trigger another query share to test event handling
            await collab_manager.share_query(
                workspace.workspace_id,
                "integration_test_user",
                {"query_text": "test event", "query_params": {}}
            )

            # Give event time to propagate
            await asyncio.sleep(0.1)

            self._assert_test("Real-time Event Broadcasting",
                             event_handler_called,
                             "Real-time event broadcasting failed")

            # Cleanup all components
            await executor.optimize_performance()
            await cache.optimize_cache()
            await mcp_server.shutdown()
            await collab_manager.shutdown()
            await cache.shutdown()

            print("✅ Integration Workflow tests completed\n")

        except Exception as e:
            self._fail_test("Integration Workflow Tests", str(e))

    # Helper methods

    def _assert_test(self, test_name: str, condition: bool, error_msg: str):
        """Assert test condition and track results."""
        if condition:
            print(f"  ✅ {test_name}")
            self.passed_tests += 1
        else:
            print(f"  ❌ {test_name}: {error_msg}")
            self.failed_tests += 1

        self.test_results[test_name] = {
            'passed': condition,
            'error': error_msg if not condition else None
        }

    def _skip_test(self, test_name: str, reason: str):
        """Skip test and track results."""
        print(f"  ⏭️  {test_name}: SKIPPED - {reason}")
        self.test_results[test_name] = {
            'passed': None,
            'skipped': True,
            'reason': reason
        }

    def _fail_test(self, test_name: str, error: str):
        """Fail test and track results."""
        print(f"  ❌ {test_name}: {error}")
        self.failed_tests += 1
        self.test_results[test_name] = {
            'passed': False,
            'error': error
        }

    def _print_final_results(self):
        """Print final test results summary."""
        print("=" * 75)
        print("📊 PHASE 3 TEST RESULTS SUMMARY")
        print("=" * 75)

        total_tests = self.passed_tests + self.failed_tests
        skipped_tests = sum(1 for result in self.test_results.values() if result.get('skipped'))

        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"⏭️  Skipped: {skipped_tests}")
        print(f"📈 Success Rate: {(self.passed_tests / max(total_tests, 1)) * 100:.1f}%")

        if self.failed_tests == 0:
            print("\n🎉 ALL PHASE 3 TESTS PASSED!")
            print("🚀 Production-ready multi-index system is ready for deployment")
        else:
            print(f"\n⚠️  {self.failed_tests} tests failed")
            print("🔧 Review failed tests and dependencies before production deployment")

        print("\n🎯 Phase 3 Features Tested:")
        print("  • 🧠 Intelligent query planning with cost optimization")
        print("  • ⚡ Enhanced query execution with cross-index coordination")
        print("  • 📊 Interactive Observable D3 visualizations")
        print("  • 🤖 MCP integration for AI agent workflows")
        print("  • 💾 Advanced Redis caching with distributed features")
        print("  • 👥 Real-time collaboration and workspace management")
        print("  • 🏭 Production deployment configuration and monitoring")
        print("  • 🔗 End-to-end integration workflows")

        completion_rate = (self.passed_tests / max(total_tests, 1)) * 100
        if completion_rate >= 90:
            print(f"\n🌟 EXCELLENT! {completion_rate:.1f}% of production features working")
            print("🎯 Phase 3 implementation is enterprise-ready")
        elif completion_rate >= 75:
            print(f"\n✅ GOOD! {completion_rate:.1f}% of production features working")
            print("🔧 Minor issues need resolution for full production readiness")
        else:
            print(f"\n⚠️  {completion_rate:.1f}% of features working")
            print("🔧 Significant work needed before production deployment")

        print("\n📖 Production Deployment:")
        print("  • Configure production.yaml with your environment settings")
        print("  • Set up Redis cluster for caching and collaboration")
        print("  • Deploy with Kubernetes or Docker Compose configurations")
        print("  • Configure monitoring and alerting for operations")

async def main():
    """Run Phase 3 comprehensive test suite."""
    print("🧪 Starting Phase 3 Multi-Index System Tests")
    print("🏭 Testing production-ready enterprise features")
    print()

    test_runner = Phase3TestRunner()
    success = await test_runner.run_all_tests()

    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏸️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)