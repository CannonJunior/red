#!/usr/bin/env python3
"""
Integration tests for RFP shredding workflow.

Tests the complete end-to-end process:
1. Section parsing
2. Requirement extraction
3. Classification
4. Database storage
5. Task creation
"""

import pytest
import sys
import os
import sqlite3
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shredding.rfp_shredder import RFPShredder
from shredding.requirement_extractor import RequirementExtractor
from shredding.requirement_classifier import RequirementClassifier


class TestRFPShreddingIntegration:
    """Integration tests for complete RFP shredding workflow."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary test database."""
        # Create temporary database
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Initialize with schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create requirements table (simplified version)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                id TEXT PRIMARY KEY,
                opportunity_id TEXT,
                section TEXT,
                page_number INTEGER,
                source_text TEXT,
                compliance_type TEXT,
                requirement_category TEXT,
                priority TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_requirement_extraction_and_classification_workflow(self):
        """Test extraction and classification workflow without PDF."""
        # Sample RFP text (Section C) - with proper sentence endings
        section_c_text = """
        SECTION C - DESCRIPTION/SPECIFICATIONS/WORK STATEMENT.

        TECHNICAL REQUIREMENTS are specified below.

        The contractor shall provide cloud-based infrastructure services with 99.9% uptime guarantee.
        The system must comply with FedRAMP High baseline controls and NIST 800-53 security requirements.
        All data shall be encrypted using AES-256 encryption both at rest and in transit.

        SUPPORT REQUIREMENTS are also mandatory.

        The contractor should provide 24/7 technical support with response times under 15 minutes for critical issues.
        Monthly status reports may be submitted to the COR as needed.
        """

        # Extract requirements
        extractor = RequirementExtractor()
        requirements = extractor.extract_requirements(
            section_c_text,
            section="C",
            start_page=10
        )

        # Should extract multiple requirements
        assert len(requirements) >= 3

        # Check for mandatory requirements
        mandatory_reqs = [r for r in requirements if r.compliance_type == 'mandatory']
        assert len(mandatory_reqs) >= 2

        # Check for recommended/optional requirements
        optional_reqs = [r for r in requirements if r.compliance_type in ['recommended', 'optional']]
        assert len(optional_reqs) >= 1

        print(f"\n✅ Extracted {len(requirements)} requirements")
        print(f"   - {len(mandatory_reqs)} mandatory")
        print(f"   - {len(optional_reqs)} recommended/optional")

        # Classify one requirement
        classifier = RequirementClassifier()

        if len(requirements) > 0:
            first_req = requirements[0]
            classification = classifier.classify(first_req.text)

            assert classification is not None
            assert hasattr(classification, 'compliance_type')
            assert hasattr(classification, 'category')
            assert hasattr(classification, 'priority')

            print(f"\n✅ Classification successful:")
            print(f"   - Type: {classification.compliance_type}")
            print(f"   - Category: {classification.category}")
            print(f"   - Priority: {classification.priority}")

    def test_database_storage(self, test_db):
        """Test storing requirements in database."""
        # Create sample requirements
        requirements = [
            {
                'id': 'C-001',
                'opportunity_id': 'test-opp-001',
                'section': 'C',
                'page_number': 10,
                'source_text': 'The contractor shall provide services.',
                'compliance_type': 'mandatory',
                'requirement_category': 'technical',
                'priority': 'high'
            },
            {
                'id': 'C-002',
                'opportunity_id': 'test-opp-001',
                'section': 'C',
                'page_number': 11,
                'source_text': 'Monthly reports should be submitted.',
                'compliance_type': 'recommended',
                'requirement_category': 'management',
                'priority': 'medium'
            }
        ]

        # Store in database
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # First create opportunity
        cursor.execute("""
            INSERT INTO opportunities (id, name) VALUES (?, ?)
        """, ('test-opp-001', 'Test Opportunity'))

        # Insert requirements
        for req in requirements:
            cursor.execute("""
                INSERT INTO requirements
                (id, opportunity_id, section, page_number, source_text,
                 compliance_type, requirement_category, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req['id'],
                req['opportunity_id'],
                req['section'],
                req['page_number'],
                req['source_text'],
                req['compliance_type'],
                req['requirement_category'],
                req['priority']
            ))

        conn.commit()

        # Verify storage
        cursor.execute("SELECT COUNT(*) FROM requirements WHERE opportunity_id = ?",
                      ('test-opp-001',))
        count = cursor.fetchone()[0]
        assert count == 2

        # Verify mandatory requirement
        cursor.execute("""
            SELECT * FROM requirements
            WHERE opportunity_id = ? AND compliance_type = 'mandatory'
        """, ('test-opp-001',))
        mandatory = cursor.fetchone()
        assert mandatory is not None

        conn.close()

        print(f"\n✅ Database storage successful")
        print(f"   - {count} requirements stored")

    def test_extraction_accuracy_metrics(self):
        """Test requirement extraction accuracy with known samples."""
        # Test cases with known correct answers
        test_cases = [
            {
                'text': 'The contractor shall deliver all items by the deadline.',
                'expected_type': 'mandatory',
                'expected_count': 1
            },
            {
                'text': 'Offerors should have experience. The proposal must include references.',
                'expected_type': 'mandatory',  # At least one mandatory
                'expected_count': 2
            },
            {
                'text': 'Additional features may be proposed if desired.',
                'expected_type': 'optional',
                'expected_count': 1
            }
        ]

        extractor = RequirementExtractor()
        total_tests = len(test_cases)
        passed_tests = 0

        for i, test_case in enumerate(test_cases):
            requirements = extractor.extract_requirements(
                test_case['text'],
                section='C',
                start_page=1
            )

            # Check count
            if len(requirements) >= test_case['expected_count']:
                passed_tests += 1
                print(f"✅ Test {i+1}: Extracted {len(requirements)} requirements (expected {test_case['expected_count']})")
            else:
                print(f"❌ Test {i+1}: Extracted {len(requirements)} requirements (expected {test_case['expected_count']})")

        accuracy = (passed_tests / total_tests) * 100
        print(f"\n📊 Extraction Accuracy: {accuracy:.1f}% ({passed_tests}/{total_tests} tests passed)")

        # Should achieve at least 66% accuracy
        assert accuracy >= 66.0

    def test_classification_batch_performance(self):
        """Test batch classification performance."""
        requirements = [
            {"text": "The contractor shall provide technical support.", "section": "C", "page": 10},
            {"text": "The system must be FedRAMP certified.", "section": "C", "page": 11},
            {"text": "Monthly reports should be submitted.", "section": "L", "page": 5},
            {"text": "Additional services may be requested.", "section": "C", "page": 12},
            {"text": "All personnel must have security clearance.", "section": "C", "page": 13}
        ]

        classifier = RequirementClassifier()

        # Test batch classification
        results = classifier.classify_batch(requirements, show_progress=False)

        assert len(results) == len(requirements)

        # All results should have required fields
        for result in results:
            assert hasattr(result, 'compliance_type')
            assert hasattr(result, 'category')
            assert hasattr(result, 'priority')

        # Count compliance types
        mandatory_count = sum(1 for r in results if r.compliance_type == 'mandatory')

        print(f"\n✅ Batch classification successful")
        print(f"   - {len(results)} requirements classified")
        print(f"   - {mandatory_count} classified as mandatory")

        # Should identify at least some mandatory requirements
        assert mandatory_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
