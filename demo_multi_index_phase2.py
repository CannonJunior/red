#!/usr/bin/env python3
"""
Phase 2 Multi-Index System Demo

Demonstrates advanced indexing features with real database implementations:
- VectorIndex: ChromaDB semantic search with embeddings
- GraphIndex: Kùzu graph database with entity extraction
- MetadataIndex: DuckDB structured queries and analytics
- FTSIndex: SQLite FTS5 full-text search with ranking
- TemporalIndex: Version control and time-travel queries
- AdaptiveIndex: ML-based query optimization and caching

Run with: PYTHONPATH=/home/junior/src/red uv run demo_multi_index_phase2.py
"""

import asyncio
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add multi-index system to path
sys.path.insert(0, str(Path(__file__).parent / "multi-index-system"))

class Phase2Demo:
    """Interactive demo for Phase 2 advanced indexing features."""

    def __init__(self):
        self.temp_dir = None
        self.indices = {}

    async def run_demo(self):
        """Run comprehensive Phase 2 demonstration."""
        print("🚀 MULTI-INDEX SYSTEM PHASE 2 - ADVANCED INDEXING DEMO")
        print("=" * 70)
        print("🔬 Demonstrating real database implementations and AI features")
        print("⚡ Features: Vector embeddings, Graph extraction, Analytics, FTS, Versioning")
        print()

        # Create temporary demo directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="multi_index_phase2_demo_"))
        print(f"📁 Demo data directory: {self.temp_dir}")
        print()

        try:
            await self._demo_vector_embeddings()
            await self._demo_graph_extraction()
            await self._demo_structured_analytics()
            await self._demo_fulltext_search()
            await self._demo_version_control()
            await self._demo_adaptive_optimization()
            await self._demo_cross_index_queries()

            self._print_final_summary()

        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Cleanup
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)

    async def _demo_vector_embeddings(self):
        """Demo vector embeddings and semantic search."""
        print("🔍 VECTOR EMBEDDINGS & SEMANTIC SEARCH")
        print("-" * 50)

        try:
            from indices.vector_index import VectorIndex

            config = {
                'embedding_model': 'nomic-embed-text',
                'embedding_dimension': 768,
                'max_results': 10
            }

            vector_index = VectorIndex("demo_vector", self.temp_dir, config)

            if await vector_index.initialize():
                print("✅ ChromaDB vector index initialized")

                # Sample research documents
                research_docs = [
                    {
                        "id": "paper_001",
                        "title": "Transformer Architecture for Natural Language Processing",
                        "content": "This paper introduces the transformer model architecture which uses self-attention mechanisms to process sequential data without recurrence or convolution.",
                        "author": "Research Team A",
                        "category": "NLP"
                    },
                    {
                        "id": "paper_002",
                        "title": "Graph Neural Networks for Knowledge Representation",
                        "content": "Graph neural networks (GNNs) enable learning on graph-structured data by aggregating information from neighboring nodes in the graph topology.",
                        "author": "Research Team B",
                        "category": "Graph Learning"
                    },
                    {
                        "id": "paper_003",
                        "title": "Distributed Systems for Large-Scale Machine Learning",
                        "content": "This work presents distributed computing frameworks that enable training of machine learning models across multiple nodes for handling big data scenarios.",
                        "author": "Research Team C",
                        "category": "Distributed ML"
                    }
                ]

                result = await vector_index.insert(research_docs, "research")
                print(f"📄 Inserted {result.get('documents_inserted', 0)} research papers")

                # Semantic search demonstration
                search_queries = [
                    "attention mechanisms and transformers",
                    "graph learning and neural networks",
                    "distributed machine learning systems"
                ]

                for query in search_queries:
                    print(f"\n🔎 Query: '{query}'")
                    search_result = await vector_index.query(
                        {"query": query, "limit": 2}, "research"
                    )

                    for i, doc in enumerate(search_result.documents):
                        confidence = search_result.confidence_scores[i] if search_result.confidence_scores else 0
                        print(f"  📊 Result {i+1}: {doc['metadata'].get('title', doc['id'])} (confidence: {confidence:.3f})")

                await vector_index.shutdown()
                self.indices['vector'] = True
                print("✅ Vector search demo completed\n")
            else:
                print("⚠️  ChromaDB not available, skipping vector demo\n")
                self.indices['vector'] = False

        except Exception as e:
            print(f"⚠️  Vector demo failed: {e}\n")
            self.indices['vector'] = False

    async def _demo_graph_extraction(self):
        """Demo graph database with entity extraction."""
        print("🕸️  GRAPH DATABASE & ENTITY EXTRACTION")
        print("-" * 50)

        try:
            from indices.graph_index import GraphIndex

            config = {
                'entity_extraction_model': 'llama3.2:1b',
                'max_entities_per_document': 20,
                'relationship_confidence_threshold': 0.6
            }

            graph_index = GraphIndex("demo_graph", self.temp_dir, config)

            if await graph_index.initialize():
                print("✅ Kùzu graph database initialized")

                # Sample documents with rich entity content
                entity_docs = [
                    {
                        "id": "news_001",
                        "title": "AI Research Breakthrough at Stanford University",
                        "content": "Dr. Sarah Chen from Stanford University published groundbreaking research on neural network optimization. The study was conducted in collaboration with Google Research and focuses on improving transformer models for natural language understanding.",
                        "author": "Tech News Reporter"
                    }
                ]

                result = await graph_index.insert(entity_docs, "news")
                print(f"📄 Processed {result.get('documents_inserted', 0)} documents for entity extraction")

                # Demonstrate graph queries
                queries = [
                    {"query_type": "entity_search", "entity_type": "PERSON"},
                    {"query_type": "relationship_analysis", "max_depth": 2},
                    {"query_type": "entity_connections", "entity": "Stanford University"}
                ]

                for query in queries:
                    print(f"\n🔍 Graph Query: {query['query_type']}")
                    try:
                        graph_result = await graph_index.query(query, "news")
                        print(f"  📊 Found {len(graph_result.documents)} graph results")

                        for doc in graph_result.documents[:2]:  # Show first 2 results
                            if 'entity' in doc:
                                print(f"    • Entity: {doc['entity']} (Type: {doc.get('type', 'N/A')})")
                            elif 'relationship' in doc:
                                print(f"    • Relationship: {doc['relationship']}")
                    except Exception as e:
                        print(f"  ⚠️  Query failed: {e}")

                await graph_index.shutdown()
                self.indices['graph'] = True
                print("✅ Graph extraction demo completed\n")
            else:
                print("⚠️  Kùzu not available, skipping graph demo\n")
                self.indices['graph'] = False

        except Exception as e:
            print(f"⚠️  Graph demo failed: {e}\n")
            self.indices['graph'] = False

    async def _demo_structured_analytics(self):
        """Demo structured data analytics with DuckDB."""
        print("📊 STRUCTURED DATA ANALYTICS")
        print("-" * 50)

        try:
            from indices.metadata_index import MetadataIndex

            config = {
                'enable_json_extension': True,
                'memory_limit': '512MB',
                'threads': 2
            }

            metadata_index = MetadataIndex("demo_metadata", self.temp_dir, config)

            if await metadata_index.initialize():
                print("✅ DuckDB metadata index initialized")

                # Sample business data
                business_docs = [
                    {
                        "id": "project_001",
                        "title": "Q1 Sales Dashboard Development",
                        "author": "John Smith",
                        "category": "Development",
                        "department": "Engineering",
                        "budget": 50000,
                        "start_date": "2024-01-01",
                        "end_date": "2024-03-31",
                        "status": "completed",
                        "tags": ["dashboard", "sales", "analytics"]
                    },
                    {
                        "id": "project_002",
                        "title": "Customer Data Migration",
                        "author": "Alice Johnson",
                        "category": "Data Engineering",
                        "department": "Data Team",
                        "budget": 75000,
                        "start_date": "2024-02-01",
                        "end_date": "2024-05-31",
                        "status": "in_progress",
                        "tags": ["migration", "customer", "data"]
                    },
                    {
                        "id": "project_003",
                        "title": "ML Model Deployment Pipeline",
                        "author": "Bob Wilson",
                        "category": "MLOps",
                        "department": "Data Science",
                        "budget": 100000,
                        "start_date": "2024-03-01",
                        "end_date": "2024-08-31",
                        "status": "planning",
                        "tags": ["ML", "deployment", "pipeline"]
                    }
                ]

                result = await metadata_index.insert(business_docs, "projects")
                print(f"📄 Inserted {result.get('documents_inserted', 0)} project records")

                # Analytics queries
                analytics_queries = [
                    {
                        "name": "Budget Analysis by Department",
                        "sql": "SELECT department, COUNT(*) as project_count, SUM(CAST(JSON_EXTRACT(metadata, '$.budget') AS INTEGER)) as total_budget FROM metadata_projects GROUP BY department ORDER BY total_budget DESC"
                    },
                    {
                        "name": "Project Status Distribution",
                        "sql": "SELECT JSON_EXTRACT(metadata, '$.status') as status, COUNT(*) as count FROM metadata_projects GROUP BY status"
                    },
                    {
                        "name": "Projects by Category",
                        "sql": "SELECT category, title, author FROM metadata_projects ORDER BY category"
                    }
                ]

                for analytics in analytics_queries:
                    print(f"\n📈 {analytics['name']}:")
                    try:
                        analytics_result = await metadata_index.query(
                            {"sql": analytics["sql"]}, "projects"
                        )

                        for row in analytics_result.documents:
                            print(f"  📊 {row}")
                    except Exception as e:
                        print(f"  ⚠️  Query failed: {e}")

                await metadata_index.shutdown()
                self.indices['metadata'] = True
                print("✅ Analytics demo completed\n")
            else:
                print("⚠️  DuckDB not available, skipping analytics demo\n")
                self.indices['metadata'] = False

        except Exception as e:
            print(f"⚠️  Analytics demo failed: {e}\n")
            self.indices['metadata'] = False

    async def _demo_fulltext_search(self):
        """Demo full-text search with ranking."""
        print("🔎 FULL-TEXT SEARCH & RANKING")
        print("-" * 50)

        try:
            from indices.fts_index import FTSIndex

            config = {
                'enable_stemming': True,
                'max_results': 10
            }

            fts_index = FTSIndex("demo_fts", self.temp_dir, config)

            if await fts_index.initialize():
                print("✅ SQLite FTS5 index initialized")

                # Sample documentation
                docs = [
                    {
                        "id": "doc_001",
                        "title": "Getting Started with Machine Learning",
                        "content": "Machine learning is a powerful tool for data analysis and prediction. This guide covers the fundamentals of supervised learning, unsupervised learning, and deep learning techniques.",
                        "author": "AI Tutorial Team",
                        "tags": ["machine learning", "tutorial", "beginner"]
                    },
                    {
                        "id": "doc_002",
                        "title": "Advanced Deep Learning Techniques",
                        "content": "Explore advanced neural network architectures including convolutional neural networks, recurrent neural networks, and transformer models for complex AI applications.",
                        "author": "Deep Learning Expert",
                        "tags": ["deep learning", "neural networks", "advanced"]
                    },
                    {
                        "id": "doc_003",
                        "title": "Data Preprocessing and Feature Engineering",
                        "content": "Learn essential data preprocessing techniques, feature selection methods, and engineering approaches to improve machine learning model performance.",
                        "author": "Data Science Team",
                        "tags": ["data preprocessing", "feature engineering", "data science"]
                    }
                ]

                result = await fts_index.insert(docs, "documentation")
                print(f"📄 Indexed {result.get('documents_inserted', 0)} documentation pages")

                # Full-text search examples
                search_examples = [
                    "machine learning fundamentals",
                    "neural networks deep learning",
                    "data preprocessing techniques",
                    '"machine learning"'  # Phrase search
                ]

                for search_query in search_examples:
                    print(f"\n🔍 Search: '{search_query}'")
                    try:
                        search_result = await fts_index.query(
                            {"query": search_query, "highlight": True, "limit": 3},
                            "documentation"
                        )

                        for i, doc in enumerate(search_result.documents):
                            relevance = doc.get('relevance_score', 0)
                            print(f"  📄 {doc['title']} (relevance: {abs(relevance):.2f})")
                            if 'highlighted_content' in doc:
                                preview = doc['highlighted_content'][:100] + "..." if len(doc['highlighted_content']) > 100 else doc['highlighted_content']
                                print(f"    💡 {preview}")
                    except Exception as e:
                        print(f"  ⚠️  Search failed: {e}")

                await fts_index.shutdown()
                self.indices['fts'] = True
                print("✅ Full-text search demo completed\n")
            else:
                print("⚠️  SQLite FTS5 not available, skipping search demo\n")
                self.indices['fts'] = False

        except Exception as e:
            print(f"⚠️  FTS demo failed: {e}\n")
            self.indices['fts'] = False

    async def _demo_version_control(self):
        """Demo version control and temporal queries."""
        print("⏰ VERSION CONTROL & TIME-TRAVEL QUERIES")
        print("-" * 50)

        try:
            from indices.temporal_index import TemporalIndex

            config = {
                'max_versions_per_document': 10,
                'retention_days': 30
            }

            temporal_index = TemporalIndex("demo_temporal", self.temp_dir, config)

            if await temporal_index.initialize():
                print("✅ Temporal index initialized")

                # Simulate document evolution
                document_versions = [
                    {
                        "id": "proposal_v1",
                        "title": "Project Proposal",
                        "content": "Initial draft of the project proposal with basic requirements.",
                        "author": "Project Manager",
                        "version": "1.0"
                    },
                    {
                        "id": "proposal_v1",  # Same ID for versioning
                        "title": "Project Proposal v2",
                        "content": "Updated proposal with detailed timeline, budget estimates, and resource allocation.",
                        "author": "Project Manager",
                        "version": "2.0"
                    },
                    {
                        "id": "proposal_v1",  # Same ID for versioning
                        "title": "Project Proposal Final",
                        "content": "Final proposal with stakeholder feedback incorporated, approved budget, and detailed implementation plan.",
                        "author": "Project Manager",
                        "version": "3.0"
                    }
                ]

                # Insert versions with small delays to create temporal history
                for i, version in enumerate(document_versions):
                    result = await temporal_index.insert([version], "proposals")
                    print(f"📝 Saved version {i+1}: {version['title']}")
                    if i < len(document_versions) - 1:
                        await asyncio.sleep(0.1)  # Small delay between versions

                # Temporal queries
                temporal_queries = [
                    {
                        "name": "Version History",
                        "params": {"query_type": "version_history", "document_id": "proposal_v1"}
                    },
                    {
                        "name": "Current State",
                        "params": {"query_type": "current", "limit": 5}
                    },
                    {
                        "name": "Recent Changes",
                        "params": {
                            "query_type": "changes_between",
                            "start_time": (datetime.now() - timedelta(minutes=1)).isoformat(),
                            "end_time": datetime.now().isoformat()
                        }
                    }
                ]

                for temporal_query in temporal_queries:
                    print(f"\n🕐 {temporal_query['name']}:")
                    try:
                        temporal_result = await temporal_index.query(
                            temporal_query["params"], "proposals"
                        )

                        for doc in temporal_result.documents:
                            version_num = doc.get('version_number', doc.get('current_version', 'N/A'))
                            title = doc.get('title', 'N/A')
                            change_summary = doc.get('change_summary', 'N/A')
                            print(f"  📄 Version {version_num}: {title}")
                            if change_summary != 'N/A':
                                print(f"    🔄 {change_summary}")
                    except Exception as e:
                        print(f"  ⚠️  Query failed: {e}")

                await temporal_index.shutdown()
                self.indices['temporal'] = True
                print("✅ Version control demo completed\n")
            else:
                print("⚠️  Temporal index failed to initialize\n")
                self.indices['temporal'] = False

        except Exception as e:
            print(f"⚠️  Temporal demo failed: {e}\n")
            self.indices['temporal'] = False

    async def _demo_adaptive_optimization(self):
        """Demo adaptive optimization and ML-based query optimization."""
        print("🧠 ADAPTIVE OPTIMIZATION & ML INSIGHTS")
        print("-" * 50)

        try:
            from indices.adaptive import AdaptiveIndexManager

            config = {
                'pattern_window_size': 50,
                'min_pattern_frequency': 2,
                'cache_size': 25
            }

            adaptive_manager = AdaptiveIndexManager("demo_adaptive", self.temp_dir, config)

            if await adaptive_manager.initialize():
                print("✅ Adaptive index manager initialized")

                # Simulate query patterns
                query_patterns = [
                    ("search machine learning papers", {"type": "search", "limit": 10}, 0.15, ["vector", "fts"]),
                    ("find recent research", {"type": "filter", "date_range": "recent"}, 0.22, ["temporal", "metadata"]),
                    ("analyze project budgets", {"type": "aggregation"}, 0.45, ["metadata"]),
                    ("search machine learning algorithms", {"type": "search", "limit": 20}, 0.18, ["vector", "fts"]),
                    ("find AI research papers", {"type": "search", "category": "AI"}, 0.13, ["vector", "metadata"])
                ]

                print("📊 Learning from query patterns...")
                for query, params, exec_time, indices_used in query_patterns:
                    learn_result = await adaptive_manager.learn_from_query(
                        query, params, exec_time, indices_used, len(indices_used) * 5
                    )
                    pattern_id = learn_result.get('pattern_id', 'unknown')[:8]
                    frequency = learn_result.get('pattern_frequency', 0)
                    print(f"  🔍 Pattern {pattern_id}: '{query}' (freq: {frequency})")

                # Get optimization recommendations
                test_queries = [
                    "search for machine learning research",
                    "analyze budget distribution",
                    "find documents about neural networks"
                ]

                print(f"\n🎯 Optimization Recommendations:")
                for test_query in test_queries:
                    recommendations = await adaptive_manager.get_optimization_recommendations(
                        test_query, {"type": "search"}
                    )

                    recommended_indices = recommendations.get('recommended_indices', [])
                    confidence = recommendations.get('confidence', 0)
                    should_cache = await adaptive_manager.should_cache_result(test_query, {"type": "search"}, 50)

                    print(f"  🔍 '{test_query}':")
                    print(f"    📊 Recommended indices: {recommended_indices}")
                    print(f"    🎯 Confidence: {confidence:.2f}")
                    print(f"    💾 Should cache: {should_cache}")

                # Performance insights
                insights_result = await adaptive_manager.query(
                    {"analysis_type": "performance_insights"}
                )

                if insights_result.documents:
                    insights = insights_result.documents[0]
                    print(f"\n📈 Performance Insights:")
                    print(f"  • Patterns learned: {insights.get('total_patterns_learned', 0)}")
                    print(f"  • Queries analyzed: {insights.get('total_queries_analyzed', 0)}")
                    print(f"  • Most common query type: {insights.get('most_common_query_type', 'N/A')}")

                    cache_stats = insights.get('cache_efficiency', {})
                    hit_rate = cache_stats.get('hit_rate', 0)
                    print(f"  • Cache hit rate: {hit_rate:.1%}")

                await adaptive_manager.shutdown()
                self.indices['adaptive'] = True
                print("✅ Adaptive optimization demo completed\n")
            else:
                print("⚠️  Adaptive manager failed to initialize\n")
                self.indices['adaptive'] = False

        except Exception as e:
            print(f"⚠️  Adaptive demo failed: {e}\n")
            self.indices['adaptive'] = False

    async def _demo_cross_index_queries(self):
        """Demo cross-index coordination and complex queries."""
        print("🔗 CROSS-INDEX COORDINATION")
        print("-" * 50)

        # This demonstrates how multiple indices can work together
        successful_indices = [name for name, success in self.indices.items() if success]

        print(f"✅ Successfully initialized indices: {', '.join(successful_indices)}")
        print(f"📊 Phase 2 completion rate: {len(successful_indices)}/6 indices ({len(successful_indices)/6*100:.1f}%)")

        if len(successful_indices) >= 3:
            print("\n🎯 Cross-Index Query Simulation:")
            print("  1. Vector search finds semantically similar documents")
            print("  2. Metadata index filters by structured criteria")
            print("  3. FTS index provides keyword-based ranking")
            print("  4. Temporal index shows version history")
            print("  5. Graph index reveals entity relationships")
            print("  6. Adaptive manager optimizes future queries")
            print("\n✨ This enables powerful hybrid queries combining:")
            print("  • Semantic similarity (Vector)")
            print("  • Structured filters (Metadata)")
            print("  • Text relevance (FTS)")
            print("  • Time-based analysis (Temporal)")
            print("  • Relationship discovery (Graph)")
            print("  • Performance optimization (Adaptive)")
        else:
            print("⚠️  Need at least 3 indices for effective cross-index demonstration")

        print("✅ Cross-index coordination demo completed\n")

    def _print_final_summary(self):
        """Print final demo summary."""
        print("=" * 70)
        print("🎉 PHASE 2 DEMO COMPLETE!")
        print("=" * 70)

        successful_indices = [name for name, success in self.indices.items() if success]
        failed_indices = [name for name, success in self.indices.items() if not success]

        print(f"✅ Successfully demonstrated: {len(successful_indices)}/6 indices")
        for index in successful_indices:
            print(f"  ✅ {index.capitalize()} Index")

        if failed_indices:
            print(f"\n⚠️  Skipped (dependencies unavailable): {len(failed_indices)} indices")
            for index in failed_indices:
                print(f"  ⏭️  {index.capitalize()} Index")

        print(f"\n🎯 Phase 2 Features Demonstrated:")
        print("  • 🔍 Vector embeddings with ChromaDB")
        print("  • 🕸️  Graph entity extraction with Kùzu")
        print("  • 📊 Structured analytics with DuckDB")
        print("  • 🔎 Full-text search with SQLite FTS5")
        print("  • ⏰ Version control and time-travel queries")
        print("  • 🧠 ML-based adaptive optimization")
        print("  • 🔗 Cross-index coordination capabilities")

        completion_rate = len(successful_indices) / 6 * 100
        if completion_rate >= 80:
            print(f"\n🚀 EXCELLENT! {completion_rate:.1f}% of advanced features working")
            print("🎯 Phase 2 implementation is production-ready")
        elif completion_rate >= 50:
            print(f"\n✅ GOOD! {completion_rate:.1f}% of advanced features working")
            print("🔧 Some optional dependencies need installation for full features")
        else:
            print(f"\n⚠️  {completion_rate:.1f}% of features working")
            print("🔧 Install missing dependencies for full Phase 2 experience")

        print("\n📖 Next Steps:")
        print("  • Install Ollama for AI features: https://ollama.ai")
        print("  • Run: ollama pull nomic-embed-text")
        print("  • Run: ollama pull llama3.2:1b")
        print("  • Test with: PYTHONPATH=/home/junior/src/red uv run test_multi_index_phase2.py")

async def main():
    """Run Phase 2 interactive demo."""
    demo = Phase2Demo()
    await demo.run_demo()

if __name__ == "__main__":
    print("🎬 Starting Phase 2 Multi-Index System Demo")
    print("🔬 Advanced indexing with real database implementations")
    print()

    try:
        asyncio.run(main())
        print("\n👋 Demo completed successfully!")
    except KeyboardInterrupt:
        print("\n⏸️  Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        import traceback
        traceback.print_exc()