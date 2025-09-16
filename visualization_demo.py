#!/usr/bin/env python3
"""
Phase 3 Visualization Demo

Demonstrates how to access and use the Phase 3 visualization endpoints
from the multi-index system through the web application.
"""

import requests
import json
import webbrowser
import time
from pathlib import Path

def test_visualization_endpoints():
    """Test all Phase 3 visualization endpoints."""
    base_url = "http://localhost:9090"

    print("🎨 PHASE 3 VISUALIZATION DEMO")
    print("=" * 50)
    print("Testing visualization endpoints and data access\n")

    # Test knowledge graph endpoint
    print("📊 Testing Knowledge Graph API...")
    try:
        response = requests.get(f"{base_url}/api/visualizations/knowledge-graph")
        if response.status_code == 200:
            data = response.json()
            entities = data.get('entities', [])
            relationships = data.get('relationships', [])
            print(f"   ✅ Knowledge Graph: {len(entities)} entities, {len(relationships)} relationships")

            # Print sample entities
            for entity in entities[:3]:
                print(f"      - {entity['name']} ({entity['type']}, confidence: {entity['confidence']})")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test performance dashboard endpoint
    print("\n📈 Testing Performance Dashboard API...")
    try:
        response = requests.get(f"{base_url}/api/visualizations/performance")
        if response.status_code == 200:
            data = response.json()
            metrics = data.get('metrics', {})
            print(f"   ✅ Performance Dashboard: {metrics.get('total_queries')} queries")
            print(f"      - Avg response time: {metrics.get('avg_query_time')}s")
            print(f"      - Success rate: {metrics.get('success_rate', 0) * 100:.1f}%")
            print(f"      - Cache hit rate: {metrics.get('cache_hit_rate', 0) * 100:.1f}%")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test search results endpoint
    print("\n🔍 Testing Search Results Explorer API...")
    try:
        response = requests.get(f"{base_url}/api/visualizations/search-results")
        if response.status_code == 200:
            data = response.json()
            results = data.get('search_results', [])
            query_info = data.get('query_info', {})
            print(f"   ✅ Search Explorer: {len(results)} results")
            print(f"      - Query: '{query_info.get('query')}'")
            print(f"      - Execution time: {query_info.get('execution_time')}s")

            # Print sample results
            for result in results[:2]:
                print(f"      - {result['title']} (score: {result['score']})")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def open_visualizations():
    """Open visualization pages in browser."""
    base_url = "http://localhost:9090"

    print("\n🌐 Opening Visualization Pages...")

    # Check if visualizations.html exists
    viz_file = Path("visualizations.html")
    if viz_file.exists():
        print(f"   📄 Opening {base_url}/visualizations.html")
        try:
            webbrowser.open(f"{base_url}/visualizations.html")
            print("   ✅ Visualization page opened in browser")
        except Exception as e:
            print(f"   ❌ Failed to open browser: {e}")
    else:
        print("   ❌ visualizations.html not found")

    # Also provide main interface URL
    print(f"   📄 Main Interface: {base_url}")
    print("      - Go to the main interface and look for the 'Visualizations' section")

def demonstrate_integration():
    """Demonstrate Phase 3 integration with existing RAG system."""
    print("\n🔗 PHASE 3 INTEGRATION DEMONSTRATION")
    print("=" * 50)

    print("The Phase 3 visualization system integrates with:")
    print("✅ RAG System - Knowledge graph from document analysis")
    print("✅ Multi-Index System - Performance metrics from query execution")
    print("✅ Search System - Results exploration and relevance scoring")
    print("✅ D3 Visualizations - Interactive knowledge graphs and dashboards")
    print("✅ Real-time Updates - Live performance monitoring")

    print("\n📍 Access Points:")
    print("1. Direct API endpoints:")
    print("   - GET /api/visualizations/knowledge-graph")
    print("   - GET /api/visualizations/performance")
    print("   - GET /api/visualizations/search-results")

    print("\n2. Web Interface:")
    print("   - http://localhost:9090/visualizations.html")
    print("   - Interactive D3.js visualizations")
    print("   - Real-time data refresh")

    print("\n3. Integration with existing features:")
    print("   - RAG document analysis feeds knowledge graph")
    print("   - Query performance metrics update dashboard")
    print("   - Search results power exploration interface")

def main():
    """Run the complete visualization demo."""
    print("🚀 Starting Phase 3 Visualization Demo\n")

    # Test API endpoints
    test_visualization_endpoints()

    # Demonstrate integration
    demonstrate_integration()

    # Provide access instructions
    print("\n" + "=" * 50)
    print("📖 HOW TO ACCESS VISUALIZATIONS")
    print("=" * 50)

    print("\n🎯 Quick Access:")
    print("1. Open your browser and go to: http://localhost:9090")
    print("2. Navigate to the visualization section")
    print("3. Or directly access: http://localhost:9090/visualizations.html")

    print("\n🛠️ Development Access:")
    print("1. Use curl to test APIs:")
    print("   curl http://localhost:9090/api/visualizations/knowledge-graph")
    print("2. Integrate with your applications via REST API")
    print("3. Customize visualizations by modifying visualizations.html")

    print("\n📊 Visualization Types Available:")
    print("• Knowledge Graphs - Interactive network of concepts and relationships")
    print("• Performance Dashboards - Real-time system metrics and health")
    print("• Search Explorers - Document search results with relevance scoring")

    print("\n✨ Phase 3 Features Demonstrated:")
    print("• ✅ D3.js Interactive Visualizations")
    print("• ✅ RESTful API Endpoints")
    print("• ✅ Real-time Data Integration")
    print("• ✅ Multi-Index System Performance Monitoring")
    print("• ✅ Knowledge Graph Generation")

if __name__ == "__main__":
    main()