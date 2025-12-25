#!/usr/bin/env python3
"""
Unit tests for requirement_classifier.py

Tests Ollama-based requirement classification including:
- Compliance type classification
- Category classification (technical, management, cost, etc.)
- Priority assignment
- Keyword extraction
- Fallback behavior when Ollama unavailable
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shredding.requirement_classifier import RequirementClassifier


class TestRequirementClassifier:
    """Test suite for RequirementClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create RequirementClassifier instance."""
        return RequirementClassifier(ollama_url="http://localhost:11434")

    def test_technical_requirement_classification(self, classifier):
        """Test classification of technical requirements."""
        text = "The system shall use AES-256 encryption for data at rest."

        result = classifier.classify(text)

        assert result is not None
        assert 'category' in result
        # Should classify as technical
        assert result['category'] in ['technical', 'compliance']
        assert 'compliance_type' in result
        assert result['compliance_type'] == 'mandatory'

    def test_management_requirement_classification(self, classifier):
        """Test classification of management requirements."""
        text = "The contractor shall submit monthly status reports to the COR."

        result = classifier.classify(text)

        assert result is not None
        assert 'category' in result
        # Should classify as management or deliverable
        assert result['category'] in ['management', 'deliverable']

    def test_cost_requirement_classification(self, classifier):
        """Test classification of cost/pricing requirements."""
        text = "Offerors shall provide fixed-price proposals with cost breakdowns."

        result = classifier.classify(text)

        assert result is not None
        assert 'category' in result
        # Should classify as cost or compliance
        assert result['category'] in ['cost', 'compliance', 'deliverable']

    def test_mandatory_compliance_type(self, classifier):
        """Test detection of mandatory compliance type."""
        text = "The contractor must comply with all federal regulations."

        result = classifier.classify(text)

        assert result is not None
        assert result['compliance_type'] == 'mandatory'

    def test_recommended_compliance_type(self, classifier):
        """Test detection of recommended compliance type."""
        text = "Contractors should have ISO 27001 certification."

        result = classifier.classify(text)

        assert result is not None
        assert result['compliance_type'] in ['recommended', 'optional']

    def test_optional_compliance_type(self, classifier):
        """Test detection of optional compliance type."""
        text = "Offerors may provide additional references."

        result = classifier.classify(text)

        assert result is not None
        assert result['compliance_type'] == 'optional'

    def test_priority_assignment(self, classifier):
        """Test priority level assignment."""
        high_priority_text = "The system shall maintain 99.99% uptime for critical operations."

        result = classifier.classify(high_priority_text)

        assert result is not None
        assert 'priority' in result
        assert result['priority'] in ['high', 'medium', 'low']

    def test_keyword_extraction(self, classifier):
        """Test extraction of key terms from requirements."""
        text = "The contractor shall implement NIST 800-53 security controls with multi-factor authentication."

        result = classifier.classify(text)

        assert result is not None
        assert 'keywords' in result
        # Should extract important keywords
        keywords_str = ' '.join(result['keywords']).lower()
        # At least some relevant keywords should be present
        assert any(term in keywords_str for term in ['nist', 'security', 'authentication', 'mfa'])

    def test_batch_classification(self, classifier):
        """Test batch classification of multiple requirements."""
        requirements = [
            "The contractor shall provide technical support.",
            "Monthly reports should be submitted.",
            "Additional services may be requested."
        ]

        results = classifier.classify_batch(requirements)

        assert len(results) == len(requirements)
        assert all('compliance_type' in r for r in results)
        assert all('category' in r for r in results)

    @patch('shredding.requirement_classifier.requests.post')
    def test_fallback_when_ollama_unavailable(self, mock_post, classifier):
        """Test fallback to keyword-based classification when Ollama is down."""
        # Simulate Ollama being unavailable
        mock_post.side_effect = Exception("Connection refused")

        text = "The contractor shall provide services."

        result = classifier.classify(text)

        # Should still return a result using fallback logic
        assert result is not None
        assert 'compliance_type' in result
        assert result['compliance_type'] == 'mandatory'  # Based on "shall"

    def test_empty_text_handling(self, classifier):
        """Test handling of empty text."""
        result = classifier.classify("")

        # Should handle gracefully
        assert result is not None
        assert 'compliance_type' in result

    def test_very_long_text_handling(self, classifier):
        """Test handling of very long requirement text."""
        # Create a long but valid requirement
        text = "The contractor shall " + "provide services and support " * 50

        result = classifier.classify(text)

        assert result is not None
        assert 'compliance_type' in result
        assert result['compliance_type'] == 'mandatory'

    def test_special_standards_detection(self, classifier):
        """Test detection of industry standards (NIST, ISO, FIPS)."""
        text = "The system shall comply with NIST 800-171 and ISO 27001 standards."

        result = classifier.classify(text)

        assert result is not None
        if 'entities' in result:
            entities_str = str(result['entities']).lower()
            assert 'nist' in entities_str or 'iso' in entities_str

    def test_acronym_handling(self, classifier):
        """Test proper handling of acronyms."""
        text = "The contractor shall implement MFA, SSO, and RBAC for the IAM system."

        result = classifier.classify(text)

        assert result is not None
        # Should handle acronyms without errors
        assert 'category' in result

    def test_conditional_requirement_classification(self, classifier):
        """Test classification of conditional requirements."""
        text = "If the system is unavailable, the contractor shall activate backup within 4 hours."

        result = classifier.classify(text)

        assert result is not None
        assert result['compliance_type'] == 'mandatory'
        # May have conditional indicator in keywords
        if 'keywords' in result:
            keywords_lower = [k.lower() for k in result['keywords']]
            # Might detect conditional nature

    def test_numeric_requirement_handling(self, classifier):
        """Test handling of requirements with numeric specifications."""
        text = "The system shall support 10,000 concurrent users with <100ms latency."

        result = classifier.classify(text)

        assert result is not None
        assert result['compliance_type'] == 'mandatory'
        assert 'category' in result

    def test_classification_consistency(self, classifier):
        """Test that same requirement classifies consistently."""
        text = "The contractor shall provide 24/7 technical support."

        result1 = classifier.classify(text)
        result2 = classifier.classify(text)

        # Should be consistent (allowing for minor variations in LLM output)
        assert result1['compliance_type'] == result2['compliance_type']
        # Category might vary slightly, but should be in same domain


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
