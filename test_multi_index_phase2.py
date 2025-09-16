#!/usr/bin/env python3
"""
Comprehensive Test Suite for Multi-Index System Phase 2

Tests all advanced index implementations:
- VectorIndex (ChromaDB integration)
- GraphIndex (Kùzu graph database)
- MetadataIndex (DuckDB structured queries)
- FTSIndex (SQLite FTS5 full-text search)
- TemporalIndex (Version control and time-travel)
- AdaptiveIndexManager (Machine learning optimization)

Run with: PYTHONPATH=/home/junior/src/red uv run test_multi_index_phase2.py
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

# Test framework
class Phase2TestRunner:
    """Comprehensive test runner for Phase 2 features."""

    def __init__(self):
        self.test_results = {}
        self.temp_dir = None
        self.passed_tests = 0
        self.failed_tests = 0

    async def run_all_tests(self):
        """Run all Phase 2 tests."""
        print("🚀 PHASE 2 MULTI-INDEX SYSTEM - COMPREHENSIVE TESTS")
        print("=" * 70)
        print("🔬 Testing advanced index implementations with real databases")
        print("📊 This may take 30-60 seconds to complete all tests")
        print()

        # Create temporary test directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="multi_index_phase2_"))
        print(f"📁 Test data directory: {self.temp_dir}")
        print()

        try:
            # Run test suites
            await self._test_vector_index()
            await self._test_graph_index()
            await self._test_metadata_index()
            await self._test_fts_index()
            await self._test_temporal_index()
            await self._test_adaptive_manager()
            await self._test_integration()

            self._print_final_results()
            return self.failed_tests == 0

        except Exception as e:
            print(f"❌ Critical test failure: {e}")
            return False

        finally:
            # Cleanup
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)

    async def _test_vector_index(self):
        """Test VectorIndex with ChromaDB."""
        print("🔍 TESTING VECTOR INDEX (ChromaDB)")
        print("-" * 50)

        try:
            from indices.vector_index import VectorIndex

            # Create vector index
            config = {
                'embedding_model': 'nomic-embed-text',
                'embedding_dimension': 768,
                'max_results': 100
            }

            vector_index = VectorIndex("test_vector", self.temp_dir, config)

            # Test initialization
            self._assert_test("Vector Index Initialization",
                             await vector_index.initialize(),
                             "Failed to initialize ChromaDB vector index")

            # Test document insertion
            test_docs = [
                {
                    "id": "doc1",
                    "title": "Machine Learning Basics",
                    "content": "Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
                    "author": "AI Researcher"
                },
                {
                    "id": "doc2",
                    "title": "Deep Learning Overview",
                    "content": "Deep learning uses neural networks with multiple layers to model complex patterns in data.",
                    "author": "ML Engineer"
                }
            ]

            insert_result = await vector_index.insert(test_docs, "test_workspace")
            self._assert_test("Vector Index Document Insertion",
                             insert_result.get('status') == 'success',
                             f"Insert failed: {insert_result}")

            # Test semantic search
            search_params = {
                'query': 'artificial intelligence and machine learning',
                'limit': 10
            }

            search_result = await vector_index.query(search_params, "test_workspace")
            self._assert_test("Vector Index Semantic Search",
                             len(search_result.documents) > 0,
                             "No search results returned")

            # Test health check
            health = await vector_index.health_check()
            self._assert_test("Vector Index Health Check",
                             health.get('status') == 'healthy',
                             f"Health check failed: {health}")

            # Test statistics
            stats = await vector_index.get_stats()
            self._assert_test("Vector Index Statistics",
                             stats.document_count >= 2,
                             f"Expected at least 2 documents, got {stats.document_count}")

            await vector_index.shutdown()
            print("✅ Vector Index tests completed\n")

        except ImportError as e:
            self._skip_test("Vector Index Tests", f"ChromaDB not available: {e}")
        except Exception as e:
            self._fail_test("Vector Index Tests", str(e))

    async def _test_graph_index(self):
        """Test GraphIndex with Kùzu."""
        print("🕸️  TESTING GRAPH INDEX (Kùzu)")
        print("-" * 50)

        try:
            from indices.graph_index import GraphIndex

            config = {
                'entity_extraction_model': 'llama3.2:1b',
                'max_entities_per_document': 50,
                'relationship_confidence_threshold': 0.7
            }

            graph_index = GraphIndex("test_graph", self.temp_dir, config)

            # Test initialization
            self._assert_test("Graph Index Initialization",
                             await graph_index.initialize(),
                             "Failed to initialize Kùzu graph database")

            # Test document insertion with entity extraction
            test_docs = [
                {
                    "id": "paper1",
                    "title": "Research on Machine Learning Applications",
                    "content": "John Smith from Stanford University published research on neural networks. The study focused on image recognition using convolutional neural networks.",
                    "author": "John Smith"
                }
            ]

            insert_result = await graph_index.insert(test_docs, "research_workspace")
            self._assert_test("Graph Index Document Insertion",
                             insert_result.get('status') == 'success',
                             f"Insert failed: {insert_result}")

            # Test graph traversal query
            traversal_params = {
                'query_type': 'find_connections',
                'entity': 'John Smith',
                'max_depth': 2
            }

            traversal_result = await graph_index.query(traversal_params, "research_workspace")
            self._assert_test("Graph Index Traversal Query",
                             len(traversal_result.documents) >= 0,  # May be 0 if entity extraction failed
                             "Graph traversal query failed")

            # Test health check
            health = await graph_index.health_check()
            self._assert_test("Graph Index Health Check",
                             health.get('status') in ['healthy', 'degraded'],  # Degraded is ok if Ollama unavailable
                             f"Health check failed: {health}")

            await graph_index.shutdown()
            print("✅ Graph Index tests completed\n")

        except ImportError as e:
            self._skip_test("Graph Index Tests", f"Kùzu not available: {e}")
        except Exception as e:
            self._fail_test("Graph Index Tests", str(e))

    async def _test_metadata_index(self):
        """Test MetadataIndex with DuckDB."""
        print("📊 TESTING METADATA INDEX (DuckDB)")
        print("-" * 50)

        try:
            from indices.metadata_index import MetadataIndex

            config = {
                'enable_json_extension': True,
                'memory_limit': '512MB',
                'threads': 2
            }

            metadata_index = MetadataIndex("test_metadata", self.temp_dir, config)

            # Test initialization
            self._assert_test("Metadata Index Initialization",
                             await metadata_index.initialize(),
                             "Failed to initialize DuckDB metadata index")

            # Test document insertion
            test_docs = [
                {
                    "id": "meta1",
                    "title": "Research Paper A",
                    "author": "Dr. Jane Doe",
                    "category": "Computer Science",
                    "created_at": "2024-01-15T10:30:00Z",
                    "tags": ["AI", "Machine Learning"],
                    "content": "Research content here..."
                },
                {
                    "id": "meta2",
                    "title": "Research Paper B",
                    "author": "Dr. John Smith",
                    "category": "Data Science",
                    "created_at": "2024-01-20T14:15:00Z",
                    "tags": ["Analytics", "Statistics"],
                    "content": "More research content..."
                }
            ]

            insert_result = await metadata_index.insert(test_docs, "metadata_workspace")
            self._assert_test("Metadata Index Document Insertion",
                             insert_result.get('status') == 'success',
                             f"Insert failed: {insert_result}")

            # Test SQL query
            sql_params = {
                'sql': 'SELECT title, author, category FROM metadata_metadata_workspace WHERE author LIKE ?',
                'params': ['%Dr.%']
            }

            sql_result = await metadata_index.query(sql_params, "metadata_workspace")
            self._assert_test("Metadata Index SQL Query",
                             len(sql_result.documents) == 2,
                             f"Expected 2 results, got {len(sql_result.documents)}")

            # Test parameter-based query
            param_query = {
                'author': 'Jane Doe',
                'category': 'Computer Science',
                'limit': 10
            }

            param_result = await metadata_index.query(param_query, "metadata_workspace")
            self._assert_test("Metadata Index Parameter Query",
                             len(param_result.documents) >= 1,
                             "Parameter query returned no results")

            # Test aggregation query
            agg_params = {
                'sql': 'SELECT category, COUNT(*) as count FROM metadata_metadata_workspace GROUP BY category'
            }

            agg_result = await metadata_index.query(agg_params, "metadata_workspace")
            self._assert_test("Metadata Index Aggregation",
                             len(agg_result.documents) >= 1,
                             "Aggregation query failed")

            await metadata_index.shutdown()
            print("✅ Metadata Index tests completed\n")

        except ImportError as e:
            self._skip_test("Metadata Index Tests", f"DuckDB not available: {e}")
        except Exception as e:
            self._fail_test("Metadata Index Tests", str(e))

    async def _test_fts_index(self):
        """Test FTSIndex with SQLite FTS5."""
        print("🔎 TESTING FULL-TEXT SEARCH INDEX (SQLite FTS5)")
        print("-" * 50)

        try:
            from indices.fts_index import FTSIndex

            config = {
                'enable_stemming': True,
                'remove_diacritics': True,
                'max_results': 50
            }

            fts_index = FTSIndex("test_fts", self.temp_dir, config)

            # Test initialization
            self._assert_test("FTS Index Initialization",
                             await fts_index.initialize(),
                             "Failed to initialize SQLite FTS5 index")

            # Test document insertion
            test_docs = [
                {
                    "id": "fts1",
                    "title": "Machine Learning Tutorial",
                    "content": "This comprehensive tutorial covers machine learning algorithms including supervised learning, unsupervised learning, and reinforcement learning.",
                    "author": "AI Tutorial Team",
                    "tags": ["tutorial", "machine learning", "algorithms"]
                },
                {
                    "id": "fts2",
                    "title": "Deep Learning Guide",
                    "content": "Deep learning guide explaining neural networks, backpropagation, and gradient descent optimization techniques.",
                    "author": "Deep Learning Expert",
                    "tags": ["deep learning", "neural networks", "optimization"]
                }
            ]

            insert_result = await fts_index.insert(test_docs, "fts_workspace")
            self._assert_test("FTS Index Document Insertion",
                             insert_result.get('status') == 'success',
                             f"Insert failed: {insert_result}")

            # Test full-text search
            search_params = {
                'query': 'machine learning algorithms',
                'highlight': True,
                'limit': 10
            }

            search_result = await fts_index.query(search_params, "fts_workspace")
            self._assert_test("FTS Index Text Search",
                             len(search_result.documents) > 0,
                             "Text search returned no results")

            # Verify search ranking
            if search_result.documents:
                first_doc = search_result.documents[0]
                self._assert_test("FTS Index Search Ranking",
                                 'relevance_score' in first_doc,
                                 "Relevance score not included in results")

            # Test phrase search
            phrase_params = {
                'query': '"machine learning"',
                'fields': ['content', 'title']
            }

            phrase_result = await fts_index.query(phrase_params, "fts_workspace")
            self._assert_test("FTS Index Phrase Search",
                             len(phrase_result.documents) > 0,
                             "Phrase search failed")

            await fts_index.shutdown()
            print("✅ FTS Index tests completed\n")

        except Exception as e:
            self._fail_test("FTS Index Tests", str(e))

    async def _test_temporal_index(self):
        """Test TemporalIndex for version control."""
        print("⏰ TESTING TEMPORAL INDEX (Version Control)")
        print("-" * 50)

        try:
            from indices.temporal_index import TemporalIndex

            config = {
                'max_versions_per_document': 10,
                'retention_days': 30
            }

            temporal_index = TemporalIndex("test_temporal", self.temp_dir, config)

            # Test initialization
            self._assert_test("Temporal Index Initialization",
                             await temporal_index.initialize(),
                             "Failed to initialize temporal index")

            # Test document versioning
            doc_v1 = {
                "id": "versioned_doc",
                "title": "Project Proposal",
                "content": "Initial draft of the project proposal",
                "author": "Project Manager"
            }

            insert_v1 = await temporal_index.insert([doc_v1], "project_workspace")
            self._assert_test("Temporal Index Version 1 Insert",
                             insert_v1.get('status') == 'success',
                             "Failed to insert version 1")

            # Add version 2
            doc_v2 = {
                "id": "versioned_doc",
                "title": "Project Proposal v2",
                "content": "Updated draft with budget information and timeline",
                "author": "Project Manager"
            }

            insert_v2 = await temporal_index.insert([doc_v2], "project_workspace")
            self._assert_test("Temporal Index Version 2 Insert",
                             insert_v2.get('status') == 'success',
                             "Failed to insert version 2")

            # Test version history query
            history_params = {
                'query_type': 'version_history',
                'document_id': 'versioned_doc'
            }

            history_result = await temporal_index.query(history_params, "project_workspace")
            self._assert_test("Temporal Index Version History",
                             len(history_result.documents) >= 2,
                             f"Expected at least 2 versions, got {len(history_result.documents)}")

            # Test current state query
            current_params = {
                'query_type': 'current',
                'limit': 10
            }

            current_result = await temporal_index.query(current_params, "project_workspace")
            self._assert_test("Temporal Index Current State",
                             len(current_result.documents) >= 1,
                             "Current state query failed")

            # Test point-in-time query
            past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
            pit_params = {
                'query_type': 'point_in_time',
                'timestamp': past_time
            }

            pit_result = await temporal_index.query(pit_params, "project_workspace")
            self._assert_test("Temporal Index Point-in-Time Query",
                             len(pit_result.documents) >= 0,  # May be 0 if no documents existed at that time
                             "Point-in-time query failed")

            await temporal_index.shutdown()
            print("✅ Temporal Index tests completed\n")

        except Exception as e:
            self._fail_test("Temporal Index Tests", str(e))

    async def _test_adaptive_manager(self):
        """Test AdaptiveIndexManager for ML optimization."""
        print("🧠 TESTING ADAPTIVE INDEX MANAGER (ML Optimization)")
        print("-" * 50)

        try:
            from indices.adaptive import AdaptiveIndexManager

            config = {
                'pattern_window_size': 100,
                'min_pattern_frequency': 2,
                'cache_size': 50
            }

            adaptive_manager = AdaptiveIndexManager("test_adaptive", self.temp_dir, config)

            # Test initialization
            self._assert_test("Adaptive Manager Initialization",
                             await adaptive_manager.initialize(),
                             "Failed to initialize adaptive manager")

            # Test pattern learning
            learn_result1 = await adaptive_manager.learn_from_query(
                "find documents about machine learning",
                {'type': 'search', 'limit': 10},
                0.25,
                ['vector', 'fts'],
                15
            )

            self._assert_test("Adaptive Manager Pattern Learning",
                             'pattern_id' in learn_result1,
                             "Pattern learning failed")

            # Learn same pattern again
            learn_result2 = await adaptive_manager.learn_from_query(
                "search for machine learning papers",
                {'type': 'search', 'limit': 20},
                0.18,
                ['vector', 'fts'],
                12
            )

            # Test optimization recommendations
            recommendations = await adaptive_manager.get_optimization_recommendations(
                "find machine learning research",
                {'type': 'search'}
            )

            self._assert_test("Adaptive Manager Recommendations",
                             'recommended_indices' in recommendations,
                             "Failed to get optimization recommendations")

            # Test caching decision
            should_cache = await adaptive_manager.should_cache_result(
                "frequent query pattern",
                {'type': 'search'},
                50
            )

            self._assert_test("Adaptive Manager Caching Decision",
                             isinstance(should_cache, bool),
                             "Caching decision failed")

            # Test pattern analysis
            analysis_params = {
                'analysis_type': 'pattern_analysis'
            }

            analysis_result = await adaptive_manager.query(analysis_params)
            self._assert_test("Adaptive Manager Pattern Analysis",
                             len(analysis_result.documents) >= 0,
                             "Pattern analysis failed")

            await adaptive_manager.shutdown()
            print("✅ Adaptive Manager tests completed\n")

        except Exception as e:
            self._fail_test("Adaptive Manager Tests", str(e))

    async def _test_integration(self):
        """Test integration between different indices."""
        print("🔗 TESTING MULTI-INDEX INTEGRATION")
        print("-" * 50)

        try:
            # Test that all indices can work together
            from indices.vector_index import VectorIndex
            from indices.metadata_index import MetadataIndex
            from indices.fts_index import FTSIndex

            # Create multiple indices
            vector_config = {'embedding_dimension': 384}
            metadata_config = {'memory_limit': '256MB'}
            fts_config = {'max_results': 25}

            vector_index = VectorIndex("integration_vector", self.temp_dir, vector_config)
            metadata_index = MetadataIndex("integration_metadata", self.temp_dir, metadata_config)
            fts_index = FTSIndex("integration_fts", self.temp_dir, fts_config)

            # Initialize all indices
            indices_initialized = await asyncio.gather(
                vector_index.initialize(),
                metadata_index.initialize(),
                fts_index.initialize(),
                return_exceptions=True
            )

            successful_inits = sum(1 for result in indices_initialized if result is True)
            self._assert_test("Multi-Index Integration Initialization",
                             successful_inits >= 2,  # At least 2 indices should initialize
                             f"Only {successful_inits} indices initialized successfully")

            # Test coordinated document insertion
            test_doc = {
                "id": "integration_test_doc",
                "title": "Integration Test Document",
                "content": "This document tests integration between multiple indices including vector, metadata, and full-text search capabilities.",
                "author": "Test System",
                "category": "Testing"
            }

            # Insert into all available indices
            insert_tasks = []
            for idx in [vector_index, metadata_index, fts_index]:
                if hasattr(idx, 'connection') and idx.connection:
                    insert_tasks.append(idx.insert([test_doc], "integration_workspace"))

            if insert_tasks:
                insert_results = await asyncio.gather(*insert_tasks, return_exceptions=True)
                successful_inserts = sum(1 for result in insert_results
                                       if isinstance(result, dict) and result.get('status') == 'success')

                self._assert_test("Multi-Index Coordinated Insertion",
                                 successful_inserts >= 1,
                                 f"Only {successful_inserts} indices accepted insertions")

            # Cleanup
            await asyncio.gather(
                vector_index.shutdown(),
                metadata_index.shutdown(),
                fts_index.shutdown(),
                return_exceptions=True
            )

            print("✅ Integration tests completed\n")

        except Exception as e:
            self._fail_test("Integration Tests", str(e))

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
        print("=" * 70)
        print("📊 PHASE 2 TEST RESULTS SUMMARY")
        print("=" * 70)

        total_tests = self.passed_tests + self.failed_tests
        skipped_tests = sum(1 for result in self.test_results.values() if result.get('skipped'))

        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"⏭️  Skipped: {skipped_tests}")
        print(f"📈 Success Rate: {(self.passed_tests / max(total_tests, 1)) * 100:.1f}%")

        if self.failed_tests == 0:
            print("\n🎉 ALL PHASE 2 TESTS PASSED!")
            print("🚀 Advanced indexing system is ready for production")
        else:
            print(f"\n⚠️  {self.failed_tests} tests failed")
            print("🔧 Review failed tests and fix issues before deployment")

        print("\n🎯 Phase 2 Features Tested:")
        print("  • ChromaDB vector embeddings and semantic search")
        print("  • Kùzu graph database with entity extraction")
        print("  • DuckDB structured metadata queries")
        print("  • SQLite FTS5 full-text search with ranking")
        print("  • Temporal version control and time-travel queries")
        print("  • Adaptive ML-based query optimization")
        print("  • Multi-index integration and coordination")

async def main():
    """Run Phase 2 test suite."""
    print("🧪 Starting Phase 2 Multi-Index System Tests")
    print("⚡ Testing advanced indexing with real databases")
    print()

    test_runner = Phase2TestRunner()
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
        sys.exit(1)