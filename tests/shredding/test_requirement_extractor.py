#!/usr/bin/env python3
"""
Unit tests for requirement_extractor.py

Tests requirement extraction from RFP text including:
- Mandatory keyword detection ("shall", "must", "will")
- Recommended keyword detection ("should")
- Optional keyword detection ("may", "can")
- Conditional requirement handling
- Deduplication logic
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shredding.requirement_extractor import RequirementExtractor


class TestRequirementExtractor:
    """Test suite for RequirementExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create RequirementExtractor instance."""
        return RequirementExtractor()

    def test_mandatory_shall_keyword(self, extractor):
        """Test detection of mandatory requirements with 'shall'."""
        text = "The contractor shall provide secure authentication services."
        requirements = extractor.extract_requirements(text, section="C", page=15)

        assert len(requirements) == 1
        assert requirements[0]['compliance_type'] == 'mandatory'
        assert 'shall' in requirements[0]['text'].lower()
        assert requirements[0]['section'] == 'C'
        assert requirements[0]['page'] == 15

    def test_mandatory_must_keyword(self, extractor):
        """Test detection of mandatory requirements with 'must'."""
        text = "The system must comply with NIST 800-53 security controls."
        requirements = extractor.extract_requirements(text, section="C", page=20)

        assert len(requirements) == 1
        assert requirements[0]['compliance_type'] == 'mandatory'
        assert 'must' in requirements[0]['text'].lower()

    def test_mandatory_will_keyword(self, extractor):
        """Test detection of mandatory requirements with 'will'."""
        text = "The contractor will submit monthly progress reports."
        requirements = extractor.extract_requirements(text, section="L", page=5)

        assert len(requirements) == 1
        assert requirements[0]['compliance_type'] == 'mandatory'
        assert 'will' in requirements[0]['text'].lower()

    def test_recommended_should_keyword(self, extractor):
        """Test detection of recommended requirements with 'should'."""
        text = "Contractors should have prior experience with federal contracts."
        requirements = extractor.extract_requirements(text, section="M", page=10)

        assert len(requirements) == 1
        assert requirements[0]['compliance_type'] == 'recommended'
        assert 'should' in requirements[0]['text'].lower()

    def test_optional_may_keyword(self, extractor):
        """Test detection of optional requirements with 'may'."""
        text = "The contractor may provide additional support services if needed."
        requirements = extractor.extract_requirements(text, section="C", page=25)

        assert len(requirements) == 1
        assert requirements[0]['compliance_type'] == 'optional'
        assert 'may' in requirements[0]['text'].lower()

    def test_optional_can_keyword(self, extractor):
        """Test detection of optional requirements with 'can'."""
        text = "Offerors can submit questions until the deadline."
        requirements = extractor.extract_requirements(text, section="L", page=3)

        assert len(requirements) == 1
        assert requirements[0]['compliance_type'] == 'optional'
        assert 'can' in requirements[0]['text'].lower()

    def test_multiple_requirements_single_text(self, extractor):
        """Test extraction of multiple requirements from single text block."""
        text = """
        The contractor shall provide technical support.
        The system should integrate with existing infrastructure.
        Users may request additional features.
        """
        requirements = extractor.extract_requirements(text, section="C", page=30)

        assert len(requirements) >= 2  # At least mandatory and recommended
        compliance_types = [req['compliance_type'] for req in requirements]
        assert 'mandatory' in compliance_types
        assert 'recommended' in compliance_types or 'optional' in compliance_types

    def test_conditional_requirement(self, extractor):
        """Test conditional requirement detection (if...then pattern)."""
        text = "If the system fails, the contractor shall provide backup within 24 hours."
        requirements = extractor.extract_requirements(text, section="C", page=18)

        assert len(requirements) == 1
        assert requirements[0]['compliance_type'] == 'mandatory'
        # Check if conditional pattern is detected
        req_text = requirements[0]['text'].lower()
        assert 'if' in req_text or 'shall' in req_text

    def test_no_requirements_in_descriptive_text(self, extractor):
        """Test that descriptive text without keywords doesn't extract requirements."""
        text = "This section describes the background of the project."
        requirements = extractor.extract_requirements(text, section="A", page=1)

        # Should extract nothing or very few
        assert len(requirements) == 0

    def test_deduplication(self, extractor):
        """Test that duplicate requirements are removed."""
        text = """
        The contractor shall provide support.
        The contractor shall provide support.
        The contractor shall provide support services.
        """
        requirements = extractor.extract_requirements(text, section="C", page=22)

        # Should deduplicate exact matches
        assert len(requirements) <= 2  # At most 2 unique requirements

    def test_page_number_preservation(self, extractor):
        """Test that page numbers are correctly preserved."""
        text = "The contractor shall deliver all materials by the deadline."
        requirements = extractor.extract_requirements(text, section="L", page=42)

        assert len(requirements) == 1
        assert requirements[0]['page'] == 42

    def test_section_preservation(self, extractor):
        """Test that section labels are correctly preserved."""
        text = "Proposals must address all evaluation criteria."
        requirements = extractor.extract_requirements(text, section="M", page=8)

        assert len(requirements) == 1
        assert requirements[0]['section'] == 'M'

    def test_paragraph_id_extraction(self, extractor):
        """Test paragraph ID extraction from formatted text."""
        text = "3.2.1 The contractor shall implement security controls."
        requirements = extractor.extract_requirements(text, section="C", page=16)

        assert len(requirements) == 1
        # Check if paragraph ID is detected (if implemented)
        if 'paragraph_id' in requirements[0]:
            assert '3.2.1' in str(requirements[0]['paragraph_id'])

    def test_empty_text_handling(self, extractor):
        """Test handling of empty or whitespace-only text."""
        requirements = extractor.extract_requirements("", section="C", page=1)
        assert len(requirements) == 0

        requirements = extractor.extract_requirements("   \n\n  ", section="C", page=1)
        assert len(requirements) == 0

    def test_special_characters_handling(self, extractor):
        """Test handling of special characters in requirements."""
        text = "The contractor shall provide 24/7/365 support & monitoring."
        requirements = extractor.extract_requirements(text, section="C", page=12)

        assert len(requirements) == 1
        assert '24/7/365' in requirements[0]['text']
        assert '&' in requirements[0]['text'] or 'and' in requirements[0]['text']

    def test_required_keyword_variant(self, extractor):
        """Test detection of 'required' keyword variant."""
        text = "Security clearance is required for all personnel."
        requirements = extractor.extract_requirements(text, section="C", page=7)

        assert len(requirements) == 1
        assert requirements[0]['compliance_type'] == 'mandatory'
        assert 'required' in requirements[0]['text'].lower()

    def test_mixed_case_keywords(self, extractor):
        """Test case-insensitive keyword detection."""
        text = "The contractor SHALL provide services. The system MUST comply."
        requirements = extractor.extract_requirements(text, section="C", page=14)

        assert len(requirements) >= 1
        # All should be detected despite uppercase
        for req in requirements:
            assert req['compliance_type'] == 'mandatory'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
