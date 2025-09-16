#!/usr/bin/env python3
"""
Multi-Index System CLI - Interactive Command Line Interface

Simple CLI to test individual Phase 1 features interactively.
Usage: PYTHONPATH=/home/junior/src/red uv run multi_index_cli.py
"""

import asyncio
import sys
from pathlib import Path

# Add multi-index system to path
sys.path.insert(0, str(Path(__file__).parent / "multi-index-system"))

async def cli_query_router():
    """Interactive query router testing."""
    from core.query_router import SmartQueryRouter, QueryContext

    router = SmartQueryRouter()

    print("🧠 QUERY ROUTER - Test your own queries!")
    print("Enter queries to see how they get routed (type 'quit' to exit)")

    while True:
        query = input("\n💬 Enter query: ").strip()
        if query.lower() in ['quit', 'exit', 'q']:
            break

        if not query:
            continue

        context = QueryContext(workspace="interactive")
        decision = await router.route_query(query, context)

        print(f"   🎯 Intent: {decision.intent.value}")
        print(f"   📍 Primary Index: {decision.primary_index}")
        print(f"   📋 Secondary: {decision.secondary_indices}")
        print(f"   📊 Confidence: {decision.confidence:.2f}")
        print(f"   💭 Reasoning: {decision.reasoning}")

def cli_health_status():
    """Show current system health."""
    from core.monitoring import HealthMonitor

    print("🏥 HEALTH STATUS")
    monitor = HealthMonitor(check_interval=0.1)
    monitor.start_monitoring()

    import time
    time.sleep(1)  # Let it collect some data

    health = monitor.get_overall_health()

    print(f"   Overall Status: {health['status'].upper()}")
    for component, status in health.get('components', {}).items():
        emoji = "✅" if status == "healthy" else "⚠️"
        print(f"   {emoji} {component.title()}: {status}")

    monitor.stop_monitoring()

async def cli_coordinator_test():
    """Test coordinator with sample data."""
    from core.coordinator import MultiIndexCoordinator, OperationType

    print("⚙️  COORDINATOR TEST")
    coordinator = MultiIndexCoordinator()

    # Create test operation
    operation = coordinator.create_index_operation(
        index_name="vector",
        operation_type=OperationType.INSERT,
        data={"id": "cli_test", "content": "CLI test document"}
    )

    transaction = await coordinator.coordinate_operation([operation])

    print(f"   Transaction: {transaction.transaction_id}")
    print(f"   Status: {transaction.status.value}")
    print(f"   Operations: {len(transaction.operations)}")

def cli_config_info():
    """Show configuration information."""
    from config.settings import get_config

    print("⚙️  CONFIGURATION")
    config = get_config()

    print(f"   Data Directory: {config.base_data_dir}")
    print(f"   Enabled Indices: {list(config.get_enabled_indices().keys())}")
    print(f"   Query Timeout: {config.query_timeout_seconds}s")
    print(f"   Health Interval: {config.health_check_interval}s")

async def main_menu():
    """Main CLI menu."""
    print("🚀 MULTI-INDEX SYSTEM CLI")
    print("=" * 40)

    while True:
        print("\nChoose an option:")
        print("1. 🧠 Test Query Router (interactive)")
        print("2. 🏥 Show Health Status")
        print("3. ⚙️  Test Coordinator")
        print("4. 📋 Show Configuration")
        print("5. 🎯 Run Full Demo")
        print("6. 🧪 Run All Tests")
        print("0. 🚪 Exit")

        choice = input("\nEnter choice (0-6): ").strip()

        try:
            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                await cli_query_router()
            elif choice == "2":
                cli_health_status()
            elif choice == "3":
                await cli_coordinator_test()
            elif choice == "4":
                cli_config_info()
            elif choice == "5":
                print("🎬 Running full demo...")
                import subprocess
                subprocess.run([
                    "uv", "run", "demo_multi_index.py"
                ], env={"PYTHONPATH": "/home/junior/src/red"})
            elif choice == "6":
                print("🧪 Running all tests...")
                import subprocess
                subprocess.run([
                    "uv", "run", "test_multi_index_phase1.py"
                ], env={"PYTHONPATH": "/home/junior/src/red"})
            else:
                print("❌ Invalid choice. Please enter 0-6.")

        except KeyboardInterrupt:
            print("\n⏸️  Interrupted. Returning to menu...")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n👋 Exiting CLI...")
        sys.exit(0)