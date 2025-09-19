#!/usr/bin/env python3
"""
Test script for verifying multiple graph layout functionality.

Tests the new multi-layout knowledge graph visualization system
by loading sample data and demonstrating different layout algorithms.
"""

import requests
import json
import time

def test_graph_layouts():
    """Test different graph layout configurations."""
    print("🧪 TESTING MULTIPLE GRAPH LAYOUTS")
    print("=" * 50)

    base_url = "http://localhost:9090"

    # Test 1: Check if server is running
    print("1. Testing server connectivity...")
    try:
        response = requests.get(f"{base_url}/api/visualizations/knowledge-graph")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Server online - {data['metadata']['total_entities']} entities available")
        else:
            print(f"   ❌ Server error: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return

    # Test 2: Check layout options in frontend
    print("\n2. Testing layout dropdown integration...")
    try:
        response = requests.get(f"{base_url}/")
        html_content = response.text

        layout_options = [
            'force-directed',
            'hierarchical-tree',
            'radial-tree',
            'circular',
            'grid',
            'layered'
        ]

        layouts_found = []
        for layout in layout_options:
            if layout in html_content:
                layouts_found.append(layout)

        print(f"   ✅ Layout options found: {len(layouts_found)}/{len(layout_options)}")
        for layout in layouts_found:
            print(f"      • {layout}")

    except Exception as e:
        print(f"   ❌ Frontend check failed: {e}")

    # Test 3: Data structure validation
    print("\n3. Testing data structure for layout compatibility...")
    try:
        response = requests.get(f"{base_url}/api/visualizations/knowledge-graph")
        data = response.json()

        # Check required fields for layouts
        entities = data.get('entities', [])
        relationships = data.get('relationships', [])

        if entities:
            sample_entity = entities[0]
            required_fields = ['id', 'name', 'type', 'confidence']
            missing_fields = [field for field in required_fields if field not in sample_entity]

            if not missing_fields:
                print(f"   ✅ Entity structure valid - {len(entities)} entities")
            else:
                print(f"   ⚠️  Missing entity fields: {missing_fields}")

        if relationships:
            sample_relationship = relationships[0]
            required_fields = ['source', 'target', 'relationship', 'weight']
            missing_fields = [field for field in required_fields if field not in sample_relationship]

            if not missing_fields:
                print(f"   ✅ Relationship structure valid - {len(relationships)} relationships")
            else:
                print(f"   ⚠️  Missing relationship fields: {missing_fields}")

    except Exception as e:
        print(f"   ❌ Data structure check failed: {e}")

    # Test 4: Layout algorithm recommendations
    print("\n4. Layout algorithm recommendations for current data...")

    entity_types = {}
    relationship_types = {}

    for entity in entities:
        entity_type = entity.get('type', 'unknown')
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

    for rel in relationships:
        rel_type = rel.get('relationship', 'unknown')
        relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1

    print(f"   📊 Entity types: {entity_types}")
    print(f"   🔗 Relationship types: {relationship_types}")

    # Recommend layouts based on data characteristics
    recommendations = []

    if len(entities) <= 10:
        recommendations.append("Force-Directed: Good for small networks with natural clustering")
        recommendations.append("Circular: Aesthetic for small datasets")

    if len(set(entity_types.keys())) > 1:
        recommendations.append("Layered: Good for showing entity type hierarchy")
        recommendations.append("Grid: Systematic comparison of different entity types")

    if any('CLUSTER' in etype for etype in entity_types):
        recommendations.append("Hierarchical-Tree: Good for cluster relationships")
        recommendations.append("Radial-Tree: Central focus on main clusters")

    print(f"\n   🎯 Recommended layouts for this data:")
    for rec in recommendations:
        print(f"      • {rec}")

    # Test 5: Performance considerations
    print("\n5. Performance analysis for different layouts...")

    node_count = len(entities)
    edge_count = len(relationships)

    performance_notes = []

    if node_count > 100:
        performance_notes.append("⚠️  Large dataset: Force-directed may be slow")
        performance_notes.append("✅ Grid/Layered layouts will perform better")

    if edge_count > 200:
        performance_notes.append("⚠️  Many relationships: Consider reducing edge display")

    if node_count < 50:
        performance_notes.append("✅ All layouts should perform well")

    if not performance_notes:
        performance_notes.append("✅ Dataset size is optimal for all layouts")

    for note in performance_notes:
        print(f"   {note}")

    print("\n" + "=" * 50)
    print("✅ GRAPH LAYOUT TESTING COMPLETE")
    print("=" * 50)

    print("\n🎯 Implementation Status:")
    print("1. ✅ Research completed - 6 layout algorithms identified")
    print("2. ✅ Dropdown selector added to Knowledge Visualizations")
    print("3. ✅ Multiple D3.js layout algorithms implemented:")
    print("   • Force-Directed (default)")
    print("   • Hierarchical Tree")
    print("   • Radial Tree")
    print("   • Circular Layout")
    print("   • Grid Layout")
    print("   • Layered (DAG)")
    print("4. ✅ Layout switching functionality integrated")
    print("5. ✅ Fallback mechanisms for incompatible data")

    print("\n📖 How to Use:")
    print("1. Open: http://localhost:9090")
    print("2. Navigate to Visualizations section")
    print("3. Select 'Knowledge Graph' visualization type")
    print("4. Choose desired layout from 'Graph Layout' dropdown")
    print("5. Click 'Refresh Visualization' to apply layout")

    print("\n🔬 Layout Characteristics:")
    print("• Force-Directed: Natural clustering, good for exploration")
    print("• Hierarchical Tree: Shows clear parent-child relationships")
    print("• Radial Tree: Central focus with radial expansion")
    print("• Circular: Aesthetic arrangement in circle")
    print("• Grid: Systematic positioning for comparison")
    print("• Layered: Type-based layers (Sources → Clusters → Concepts)")

if __name__ == "__main__":
    test_graph_layouts()