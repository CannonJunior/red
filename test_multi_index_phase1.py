"""
Simple test script for Phase 1 multi-index system components.

This script validates the core components work correctly.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add the multi-index-system to the path
sys.path.insert(0, str(Path(__file__).parent / "multi-index-system"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_functionality():
    """Test basic functionality of Phase 1 components."""
    print("🚀 Testing Phase 1 Multi-Index System")
    print("="*50)

    try:
        # Test 1: Configuration
        print("\\n1. Testing Configuration...")
        from config.settings import get_config

        config = get_config()
        print(f"✓ Configuration loaded successfully")
        print(f"  - Base directory: {config.base_data_dir}")
        print(f"  - Enabled indices: {list(config.get_enabled_indices().keys())}")

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

    try:
        # Test 2: Query Router Basic Functionality
        print("\\n2. Testing Query Router...")
        from core.query_router import SmartQueryRouter, QueryContext

        router = SmartQueryRouter()

        # Test pattern-based classification
        test_query = "What is machine learning?"
        context = QueryContext(workspace="test")

        decision = await router.route_query(test_query, context)

        print(f"✓ Query routing successful")
        print(f"  - Query: {test_query}")
        print(f"  - Intent: {decision.intent.value}")
        print(f"  - Primary Index: {decision.primary_index}")
        print(f"  - Confidence: {decision.confidence:.2f}")

    except Exception as e:
        print(f"✗ Query Router test failed: {e}")
        return False

    try:
        # Test 3: Multi-Index Coordinator
        print("\\n3. Testing Multi-Index Coordinator...")
        from core.coordinator import MultiIndexCoordinator, OperationType

        coordinator = MultiIndexCoordinator()

        # Create test operation
        operation = coordinator.create_index_operation(
            index_name="vector",
            operation_type=OperationType.INSERT,
            data={"id": "test_1", "content": "Test content"}
        )

        # Test coordination
        transaction = await coordinator.coordinate_operation([operation])

        print(f"✓ Coordination successful")
        print(f"  - Transaction ID: {transaction.transaction_id}")
        print(f"  - Status: {transaction.status.value}")
        print(f"  - Operations: {len(transaction.operations)}")

    except Exception as e:
        print(f"✗ Coordinator test failed: {e}")
        return False

    try:
        # Test 4: Health Monitor
        print("\\n4. Testing Health Monitor...")
        from core.monitoring import HealthMonitor

        monitor = HealthMonitor(check_interval=0.5)
        monitor.start_monitoring()

        # Wait for a health check
        await asyncio.sleep(1)

        health = monitor.get_overall_health()
        monitor.stop_monitoring()

        print(f"✓ Health monitoring successful")
        print(f"  - Overall status: {health['status']}")
        print(f"  - Components checked: {len(health.get('components', {}))}")

    except Exception as e:
        print(f"✗ Health Monitor test failed: {e}")
        return False

    try:
        # Test 5: Conflict Resolution
        print("\\n5. Testing Conflict Resolution...")
        from core.conflict_resolution import ConflictResolver

        resolver = ConflictResolver()

        # Track a test operation
        metadata = resolver.track_operation(
            operation_id="test_op_1",
            user_id="test_user",
            workspace="test",
            document_id="doc_1",
            operation_type="update",
            operation_data={"title": "Test Document"}
        )

        print(f"✓ Conflict resolution setup successful")
        print(f"  - Node ID: {resolver.node_id}")
        print(f"  - Operation tracked: {metadata.operation_id}")
        print(f"  - Vector clock: {metadata.vector_clock.to_dict()}")

    except Exception as e:
        print(f"✗ Conflict Resolution test failed: {e}")
        return False

    print("\\n" + "="*50)
    print("🎉 ALL BASIC TESTS PASSED!")
    print("Phase 1 multi-index system is working correctly.")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    if success:
        print("\\n✅ Phase 1 implementation ready for next phase!")
    else:
        print("\\n❌ Phase 1 needs fixes before proceeding.")

    exit(0 if success else 1)