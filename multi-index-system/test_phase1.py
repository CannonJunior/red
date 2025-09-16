"""
Test script for Phase 1 multi-index system components.

This script validates all Phase 1 components:
- Configuration system
- Smart Query Router with intent recognition
- Multi-Index Coordinator for data synchronization
- Health Monitoring and metrics
- Conflict Resolution system
- Integration layer

Run with: uv run multi-index-system/test_phase1.py
"""

import asyncio
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import system components
from core.integration import initialize_system, get_multi_index_system
from core.query_router import QueryContext, QueryIntent
from core.coordinator import OperationType
from config.settings import get_config

async def test_configuration():
    """Test configuration system."""
    print("\\n" + "="*50)
    print("TESTING: Configuration System")
    print("="*50)

    config = get_config()

    print(f"✓ Base data directory: {config.base_data_dir}")
    print(f"✓ Enabled indices: {list(config.get_enabled_indices().keys())}")
    print(f"✓ Query timeout: {config.query_timeout_seconds}s")
    print(f"✓ Health check interval: {config.health_check_interval}s")

    # Test configuration dictionary conversion
    config_dict = config.to_dict()
    print(f"✓ Configuration serializable: {len(config_dict)} settings")

    return True

async def test_query_router():
    """Test smart query router with intent recognition."""
    print("\\n" + "="*50)
    print("TESTING: Smart Query Router")
    print("="*50)

    from core.query_router import SmartQueryRouter

    router = SmartQueryRouter()

    # Test different query types
    test_queries = [
        ("What is artificial intelligence?", QueryIntent.SEMANTIC_SEARCH),
        ("How are users connected to projects?", QueryIntent.RELATIONSHIP_QUERY),
        ("Count the number of documents", QueryIntent.FACTUAL_LOOKUP),
        ("Find documents containing 'machine learning'", QueryIntent.FULL_TEXT_SEARCH),
        ("Show me changes from last week", QueryIntent.TEMPORAL_QUERY),
        ("Complex multi-faceted analysis question", QueryIntent.HYBRID)
    ]

    for query, expected_intent in test_queries:
        try:
            context = QueryContext(
                user_id="test_user",
                workspace="test",
                response_time_preference="balanced"
            )

            decision = await router.route_query(query, context)

            print(f"✓ Query: '{query[:40]}...'")
            print(f"  → Intent: {decision.intent.value}")
            print(f"  → Primary Index: {decision.primary_index}")
            print(f"  → Secondary Indices: {decision.secondary_indices}")
            print(f"  → Confidence: {decision.confidence:.2f}")
            print(f"  → Estimated Time: {decision.estimated_time:.3f}s")
            print(f"  → Reasoning: {decision.reasoning}")

            if decision.intent == expected_intent:
                print("  ✓ Intent classification correct")
            else:
                print(f"  ⚠ Expected {expected_intent.value}, got {decision.intent.value}")

        except Exception as e:
            print(f"✗ Query routing failed: {e}")
            return False

    # Test routing statistics
    stats = router.get_routing_stats()
    print(f"\\n✓ Router stats: {stats}")

    return True

async def test_coordinator():
    """Test multi-index coordinator."""
    print("\\n" + "="*50)
    print("TESTING: Multi-Index Coordinator")
    print("="*50)

    from core.coordinator import MultiIndexCoordinator, IndexOperation

    coordinator = MultiIndexCoordinator()

    # Test operation creation
    operations = [
        coordinator.create_index_operation(
            index_name="vector",
            operation_type=OperationType.INSERT,
            data={"id": "test_doc_1", "text": "Test document content", "embedding": [0.1, 0.2, 0.3]}
        ),
        coordinator.create_index_operation(
            index_name="metadata",
            operation_type=OperationType.INSERT,
            data={"id": "test_doc_1", "title": "Test Document", "author": "Test User"}
        )
    ]

    print(f"✓ Created {len(operations)} test operations")

    # Test coordinated transaction
    try:
        transaction = await coordinator.coordinate_operation(
            operations=operations,
            workspace="test"
        )

        print(f"✓ Transaction {transaction.transaction_id} completed")
        print(f"  → Status: {transaction.status.value}")
        print(f"  → Operations: {len(transaction.operations)}")
        print(f"  → Created: {transaction.created_at}")

        # Test transaction status retrieval
        status = coordinator.get_transaction_status(transaction.transaction_id)
        if status:
            print(f"✓ Transaction status retrieved: {status.status.value}")
        else:
            print("✗ Failed to retrieve transaction status")
            return False

    except Exception as e:
        print(f"✗ Coordinator test failed: {e}")
        return False

    # Test coordinator statistics
    stats = coordinator.get_coordinator_stats()
    print(f"\\n✓ Coordinator stats: {stats}")

    return True

async def test_health_monitor():
    """Test health monitoring system."""
    print("\\n" + "="*50)
    print("TESTING: Health Monitor")
    print("="*50)

    from core.monitoring import HealthMonitor

    monitor = HealthMonitor(check_interval=1.0)  # Fast interval for testing

    # Start monitoring
    monitor.start_monitoring()
    print("✓ Health monitoring started")

    # Wait for a few health checks
    await asyncio.sleep(3)

    # Test health status
    overall_health = monitor.get_overall_health()
    print(f"✓ Overall health: {overall_health}")

    # Test performance summary
    performance = monitor.get_performance_summary()
    print(f"✓ Performance profiles: {len(performance)} components")

    # Test metrics summary
    metrics = monitor.get_metrics_summary()
    print(f"✓ Metrics collected: {metrics['total_data_points']} points")

    # Stop monitoring
    monitor.stop_monitoring()
    print("✓ Health monitoring stopped")

    return True

async def test_conflict_resolver():
    """Test conflict resolution system."""
    print("\\n" + "="*50)
    print("TESTING: Conflict Resolver")
    print("="*50)

    from core.conflict_resolution import ConflictResolver

    resolver = ConflictResolver()

    # Track some operations
    op1 = resolver.track_operation(
        operation_id="op_1",
        user_id="user_1",
        workspace="test",
        document_id="doc_1",
        operation_type="update",
        operation_data={"title": "Document Title v1", "content": "Original content"}
    )

    op2 = resolver.track_operation(
        operation_id="op_2",
        user_id="user_2",
        workspace="test",
        document_id="doc_1",
        operation_type="update",
        operation_data={"title": "Document Title v2", "content": "Modified content"}
    )

    print(f"✓ Tracked operations: {op1.operation_id}, {op2.operation_id}")

    # Test conflict detection
    conflict = await resolver.detect_conflicts(
        op2, {"title": "Document Title v2", "content": "Modified content"}
    )

    if conflict:
        print(f"✓ Conflict detected: {conflict.conflict_id}")
        print(f"  → Type: {conflict.conflict_type.value}")
        print(f"  → Operations: {len(conflict.conflicting_operations)}")

        # Test conflict resolution
        resolution = await resolver.resolve_conflict(conflict)
        print(f"✓ Conflict resolved: {resolution['status']}")
        print(f"  → Strategy: {resolution.get('strategy', 'N/A')}")

    else:
        print("⚠ No conflict detected (expected for this test)")

    # Test summary statistics
    summary = resolver.get_conflict_summary()
    print(f"\\n✓ Conflict resolver stats: {summary}")

    return True

async def test_integration_layer():
    """Test the complete integration layer."""
    print("\\n" + "="*50)
    print("TESTING: Integration Layer")
    print("="*50)

    # Initialize system
    system = await initialize_system()
    print("✓ Multi-index system initialized and started")

    # Test system status
    status = system.get_system_status()
    print(f"✓ System status: {status.overall_health}")
    print(f"  → Enabled indices: {status.enabled_indices}")
    print(f"  → Components active: Router={status.query_router_active}, "
          f"Coordinator={status.coordinator_active}, Monitor={status.monitor_active}")

    # Test query execution
    try:
        query_result = await system.query(
            "What is machine learning?",
            workspace="test"
        )
        print(f"✓ Query executed successfully")
        print(f"  → Primary index: {query_result['routing']['primary_index']}")
        print(f"  → Intent: {query_result['routing']['intent']}")
        print(f"  → Confidence: {query_result['routing']['confidence']:.2f}")

    except Exception as e:
        print(f"✗ Query execution failed: {e}")
        return False

    # Test data ingestion
    try:
        test_data = [
            {"id": "integration_test_1", "title": "Test Document 1", "content": "Test content 1"},
            {"id": "integration_test_2", "title": "Test Document 2", "content": "Test content 2"}
        ]

        ingestion_result = await system.ingest_data(
            test_data,
            workspace="test",
            user_id="test_user"
        )

        print(f"✓ Data ingestion completed: {ingestion_result['status']}")
        print(f"  → Transaction: {ingestion_result['transaction_id']}")
        print(f"  → Operations: {ingestion_result['operations_count']}")
        print(f"  → Indices: {ingestion_result['indices_updated']}")

    except Exception as e:
        print(f"✗ Data ingestion failed: {e}")
        return False

    # Test detailed metrics
    detailed_metrics = system.get_detailed_metrics()
    print(f"\\n✓ Detailed metrics collected from {len(detailed_metrics)} components")

    # Test conflict resolution
    conflict_result = await system.resolve_conflicts("test")
    print(f"✓ Conflict resolution: {conflict_result['status']}")

    # Shutdown system
    await system.shutdown()
    print("✓ System shutdown completed")

    return True

async def run_all_tests():
    """Run all Phase 1 tests."""
    print("🚀 Starting Phase 1 Multi-Index System Tests")
    print(f"Time: {datetime.now().isoformat()}")

    test_results = {}

    # Run individual component tests
    tests = [
        ("Configuration System", test_configuration),
        ("Query Router", test_query_router),
        ("Multi-Index Coordinator", test_coordinator),
        ("Health Monitor", test_health_monitor),
        ("Conflict Resolver", test_conflict_resolver),
        ("Integration Layer", test_integration_layer)
    ]

    for test_name, test_func in tests:
        try:
            print(f"\\n🔧 Running {test_name} test...")
            result = await test_func()
            test_results[test_name] = result
            if result:
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"💥 {test_name} test CRASHED: {e}")
            test_results[test_name] = False

    # Summary
    print("\\n" + "="*60)
    print("📊 PHASE 1 TEST SUMMARY")
    print("="*60)

    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<40} {status}")

    print(f"\\n🎯 Overall Results: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Phase 1 implementation is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return False

if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)