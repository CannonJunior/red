#!/usr/bin/env python3
"""
Interactive Demo Script for Multi-Index System Phase 1

This script provides an interactive way to test and explore all Phase 1 features.
Run with: PYTHONPATH=/home/junior/src/red uv run demo_multi_index.py
"""

import asyncio
import sys
from pathlib import Path

# Add multi-index system to path
sys.path.insert(0, str(Path(__file__).parent / "multi-index-system"))

async def demo_query_router():
    """Demo the Smart Query Router with different query types."""
    print("\n" + "="*60)
    print("🧠 SMART QUERY ROUTER DEMO")
    print("="*60)

    from core.query_router import SmartQueryRouter, QueryContext

    router = SmartQueryRouter()

    # Test different types of queries
    test_queries = [
        "What is artificial intelligence?",
        "How are users connected to projects in the system?",
        "Count all documents in the database",
        "Find files containing 'machine learning'",
        "Show me changes from last week",
        "Analyze the relationship between departments and projects over time"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Query {i}: '{query}'")

        context = QueryContext(
            user_id="demo_user",
            workspace="demo",
            response_time_preference="balanced"
        )

        decision = await router.route_query(query, context)

        print(f"   ✓ Intent: {decision.intent.value}")
        print(f"   ✓ Primary Index: {decision.primary_index}")
        print(f"   ✓ Secondary Indices: {decision.secondary_indices}")
        print(f"   ✓ Confidence: {decision.confidence:.2f}")
        print(f"   ✓ Estimated Time: {decision.estimated_time:.3f}s")
        print(f"   ✓ Reasoning: {decision.reasoning}")

async def demo_coordinator():
    """Demo the Multi-Index Coordinator with transactions."""
    print("\n" + "="*60)
    print("⚙️  MULTI-INDEX COORDINATOR DEMO")
    print("="*60)

    from core.coordinator import MultiIndexCoordinator, OperationType

    coordinator = MultiIndexCoordinator()

    # Create sample operations
    operations = []

    # Simulate ingesting a document across multiple indices
    document_data = {
        "id": "demo_doc_001",
        "title": "AI and Machine Learning Overview",
        "content": "Artificial intelligence and machine learning are transforming technology...",
        "author": "Demo User",
        "tags": ["AI", "ML", "technology"],
        "created_at": "2024-01-15T10:30:00Z"
    }

    print(f"\n📄 Creating operations for document: {document_data['title']}")

    # Vector index operation
    vector_op = coordinator.create_index_operation(
        index_name="vector",
        operation_type=OperationType.INSERT,
        data={
            "id": document_data["id"],
            "text": f"{document_data['title']} {document_data['content']}",
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]  # Simulated embedding
        }
    )
    operations.append(vector_op)

    # Metadata index operation
    metadata_op = coordinator.create_index_operation(
        index_name="metadata",
        operation_type=OperationType.INSERT,
        data={
            "id": document_data["id"],
            "title": document_data["title"],
            "author": document_data["author"],
            "created_at": document_data["created_at"],
            "tags": document_data["tags"]
        }
    )
    operations.append(metadata_op)

    # FTS index operation
    fts_op = coordinator.create_index_operation(
        index_name="fts",
        operation_type=OperationType.INSERT,
        data={
            "id": document_data["id"],
            "searchable_text": f"{document_data['title']} {document_data['content']} {' '.join(document_data['tags'])}"
        }
    )
    operations.append(fts_op)

    print(f"   ✓ Created {len(operations)} operations across indices")

    # Execute coordinated transaction
    print(f"\n🔄 Executing coordinated transaction...")
    transaction = await coordinator.coordinate_operation(
        operations=operations,
        workspace="demo"
    )

    print(f"   ✓ Transaction ID: {transaction.transaction_id}")
    print(f"   ✓ Status: {transaction.status.value}")
    print(f"   ✓ Operations Count: {len(transaction.operations)}")
    print(f"   ✓ Created At: {transaction.created_at}")

    # Show coordinator stats
    stats = coordinator.get_coordinator_stats()
    print(f"\n📊 Coordinator Statistics:")
    print(f"   ✓ Active Transactions: {stats['active_transactions']}")
    print(f"   ✓ Total Operations: {stats['performance_stats']['total_operations']}")
    print(f"   ✓ Successful Operations: {stats['performance_stats']['successful_operations']}")

async def demo_health_monitor():
    """Demo the Health Monitoring System."""
    print("\n" + "="*60)
    print("🏥 HEALTH MONITORING DEMO")
    print("="*60)

    from core.monitoring import HealthMonitor

    monitor = HealthMonitor(check_interval=1.0)

    print("🔄 Starting health monitoring (will run for 5 seconds)...")
    monitor.start_monitoring()

    # Let it run and collect data
    await asyncio.sleep(5)

    # Get health status
    overall_health = monitor.get_overall_health()
    print(f"\n📊 Overall System Health: {overall_health['status'].upper()}")

    for component, status in overall_health.get('components', {}).items():
        print(f"   ✓ {component.capitalize()}: {status}")

    # Get performance data
    performance = monitor.get_performance_summary()
    print(f"\n⚡ Performance Profiles:")
    for component, profile in performance.items():
        print(f"   ✓ {component.capitalize()}:")
        print(f"     - Avg Response Time: {profile['avg_response_time']:.3f}s")
        print(f"     - Success Rate: {profile['success_rate']:.1%}")
        print(f"     - Throughput: {profile['throughput']:.1f} ops/sec")

    # Get metrics summary
    metrics = monitor.get_metrics_summary()
    print(f"\n📈 Metrics Collection:")
    print(f"   ✓ Total Metrics: {metrics['total_metrics']}")
    print(f"   ✓ Data Points: {metrics['total_data_points']}")
    print(f"   ✓ Health Checks: {metrics['health_checks_performed']}")

    monitor.stop_monitoring()
    print("   ✓ Health monitoring stopped")

async def demo_conflict_resolution():
    """Demo the Conflict Resolution System."""
    print("\n" + "="*60)
    print("⚔️  CONFLICT RESOLUTION DEMO")
    print("="*60)

    from core.conflict_resolution import ConflictResolver

    resolver = ConflictResolver()

    print(f"🔧 Conflict Resolver initialized with node: {resolver.node_id}")

    # Simulate concurrent edits by different users
    print(f"\n📝 Simulating concurrent document edits...")

    # User 1 updates document
    op1 = resolver.track_operation(
        operation_id="edit_001",
        user_id="alice",
        workspace="demo",
        document_id="shared_doc_123",
        operation_type="update",
        operation_data={
            "title": "Project Proposal v2.1",
            "section_1": "Updated introduction by Alice",
            "last_modified": "2024-01-15T10:30:00Z"
        }
    )

    print(f"   ✓ User Alice: {op1.operation_id} at {op1.timestamp}")
    print(f"     Vector Clock: {op1.vector_clock.to_dict()}")

    # User 2 updates same document (simulate concurrent edit)
    op2 = resolver.track_operation(
        operation_id="edit_002",
        user_id="bob",
        workspace="demo",
        document_id="shared_doc_123",
        operation_type="update",
        operation_data={
            "title": "Project Proposal v2.2",
            "section_2": "New analysis section by Bob",
            "last_modified": "2024-01-15T10:31:00Z"
        }
    )

    print(f"   ✓ User Bob: {op2.operation_id} at {op2.timestamp}")
    print(f"     Vector Clock: {op2.vector_clock.to_dict()}")

    # Check for conflicts
    print(f"\n🔍 Detecting conflicts...")
    conflict = await resolver.detect_conflicts(op2, {
        "title": "Project Proposal v2.2",
        "section_2": "New analysis section by Bob",
        "last_modified": "2024-01-15T10:31:00Z"
    })

    if conflict:
        print(f"   ⚠️  Conflict detected: {conflict.conflict_id}")
        print(f"     Type: {conflict.conflict_type.value}")
        print(f"     Operations: {len(conflict.conflicting_operations)}")

        # Resolve the conflict
        print(f"\n🔧 Resolving conflict...")
        resolution = await resolver.resolve_conflict(conflict)
        print(f"   ✓ Resolution Status: {resolution['status']}")
        print(f"   ✓ Strategy Used: {resolution.get('strategy', 'N/A')}")

        if 'resolved_data' in resolution:
            print(f"   ✓ Merged Result: {resolution['resolved_data']}")
    else:
        print("   ✓ No conflicts detected")

    # Show conflict summary
    summary = resolver.get_conflict_summary()
    print(f"\n📊 Conflict Resolution Summary:")
    print(f"   ✓ Total Operations Tracked: {summary['total_operations_tracked']}")
    print(f"   ✓ Active Conflicts: {summary['active_conflicts']}")
    print(f"   ✓ Resolved Conflicts: {summary['resolved_conflicts']}")

async def demo_integration():
    """Demo the Integration Layer (simplified)."""
    print("\n" + "="*60)
    print("🔗 INTEGRATION LAYER DEMO")
    print("="*60)

    print("🏗️  Initializing multi-index system...")

    # Show what a full integration would look like
    print("   ✓ Query Router: AI-powered intent recognition")
    print("   ✓ Coordinator: Multi-index transaction management")
    print("   ✓ Health Monitor: Real-time system monitoring")
    print("   ✓ Conflict Resolver: Concurrent operation handling")
    print("   ✓ Configuration: Zero-cost local deployment")

    print(f"\n🎯 System Architecture:")
    print("   📊 Query → Router → Index Selection → Coordinator → Execution")
    print("   🔄 Data → Conflict Check → Transaction → Multi-Index Update")
    print("   🏥 System → Health Monitor → Metrics → Alerts")

    print(f"\n✨ Key Capabilities Demonstrated:")
    print("   • AI-powered query understanding and routing")
    print("   • ACID-like transactions across multiple data stores")
    print("   • Real-time health monitoring with performance tracking")
    print("   • Conflict-free concurrent operations with vector clocks")
    print("   • Zero-cost local deployment with fallback mechanisms")

async def run_full_demo():
    """Run the complete demo of all Phase 1 features."""
    print("🚀 MULTI-INDEX SYSTEM PHASE 1 - INTERACTIVE DEMO")
    print("📅 Live demonstration of all implemented features")
    print("⏱️  This demo will take approximately 30 seconds")

    try:
        await demo_query_router()
        await demo_coordinator()
        await demo_health_monitor()
        await demo_conflict_resolution()
        await demo_integration()

        print("\n" + "="*60)
        print("🎉 DEMO COMPLETE!")
        print("="*60)
        print("✅ All Phase 1 components demonstrated successfully")
        print("🔧 Ready for Phase 2: Advanced Indexing Implementation")
        print("📖 See PHASE1_SUMMARY.md for detailed technical information")

        return True

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🎯 PHASE 1 MULTI-INDEX SYSTEM - LIVE DEMO")
    print("=" * 70)

    success = asyncio.run(run_full_demo())
    exit(0 if success else 1)