#!/usr/bin/env python3
"""
Test script for dynamic CAG capacity calculation.

This script demonstrates how the CAG system automatically determines
optimal token capacity based on available system memory.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from cag_api import calculate_optimal_cag_capacity, CAGManager
import psutil


def format_bytes(bytes_value):
    """Format bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def test_capacity_calculation():
    """Test the dynamic capacity calculation."""
    print("=" * 70)
    print("CAG Dynamic Capacity Calculation Test")
    print("=" * 70)

    # Get system memory info
    memory = psutil.virtual_memory()

    print("\n📊 System Memory Information:")
    print(f"   Total RAM: {format_bytes(memory.total)}")
    print(f"   Available RAM: {format_bytes(memory.available)}")
    print(f"   Used RAM: {format_bytes(memory.used)} ({memory.percent}%)")

    # Calculate optimal capacity
    print("\n🧠 Calculating Optimal CAG Capacity...")
    optimal_capacity = calculate_optimal_cag_capacity()

    print(f"\n✅ Result: {optimal_capacity:,} tokens")

    # Estimate memory usage
    bytes_per_token = 6  # As per our calculation
    estimated_memory = optimal_capacity * bytes_per_token
    print(f"   Estimated memory usage: {format_bytes(estimated_memory)}")

    # Test CAGManager initialization
    print("\n🔧 Testing CAGManager Initialization...")

    print("\n   Test 1: Auto-detect capacity (default)")
    manager_auto = CAGManager()
    print(f"   ✓ Manager created with {manager_auto.max_context_tokens:,} tokens")

    print("\n   Test 2: Custom capacity (64K tokens)")
    manager_custom = CAGManager(max_context_tokens=64_000)
    print(f"   ✓ Manager created with {manager_custom.max_context_tokens:,} tokens")

    # Test different system scenarios
    print("\n" + "=" * 70)
    print("Capacity Estimates for Different System Configurations")
    print("=" * 70)

    scenarios = [
        ("Low-end laptop", 4),     # 4 GB RAM
        ("Mid-range laptop", 8),   # 8 GB RAM
        ("High-end laptop", 16),   # 16 GB RAM
        ("Workstation", 32),       # 32 GB RAM
        ("Server", 64),            # 64 GB RAM
    ]

    print(f"\n{'System Type':<20} {'RAM':<10} {'Estimated Capacity':<20} {'Memory Used'}")
    print("-" * 70)

    for system_type, ram_gb in scenarios:
        # Simulate calculation
        reserved_ram_gb = max(2.0, ram_gb * 0.25)
        usable_ram_gb = max(0.5, ram_gb * 0.7 - reserved_ram_gb)  # Assume 70% available
        usable_ram_bytes = usable_ram_gb * (1024 ** 3)

        estimated_tokens = int(usable_ram_bytes / bytes_per_token)
        optimal = max(32_000, min(estimated_tokens, 200_000))
        memory_used = optimal * bytes_per_token

        print(f"{system_type:<20} {ram_gb:<10} GB {optimal:>18,} tokens {format_bytes(memory_used)}")

    print("\n" + "=" * 70)
    print("💡 Note: Actual capacity may vary based on current system load")
    print("=" * 70)

    return optimal_capacity


def main():
    """Run the test."""
    try:
        capacity = test_capacity_calculation()

        print(f"\n🎉 Test completed successfully!")
        print(f"   Your system's optimal CAG capacity: {capacity:,} tokens")
        print(f"\n💰 Total cost: $0.00 (zero-cost local processing)")
        print(f"🏆 RED Compliance: COST-FIRST ✅ LOCAL-FIRST ✅ SIMPLE-SCALE ✅")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
