#!/usr/bin/env python3
"""
Unit tests for requirement_classifier.py

Tests Ollama-based requirement classification including:
- Compliance type classification (mocked for determinism)
- Fallback keyword-based classification when Ollama is unavailable
- Entity extraction
- Batch classification
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shredding.requirement_classifier import RequirementClassifier, RequirementClassification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_ollama_response(payload: dict) -> MagicMock:
    """Return a mock requests.post response with given JSON payload."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"response": json.dumps(payload)}
    return resp


_MANDATORY_RESPONSE = {
    "compliance_type": "mandatory",
    "category": "technical",
    "priority": "high",
    "risk_level": "red",
    "keywords": ["security", "encryption", "data"],
    "implicit_requirements": ["encryption at rest", "key management"],
}

_RECOMMENDED_RESPONSE = {
    "compliance_type": "recommended",
    "category": "compliance",
    "priority": "medium",
    "risk_level": "yellow",
    "keywords": ["ISO 27001", "certification"],
    "implicit_requirements": ["current certification"],
}

_OPTIONAL_RESPONSE = {
    "compliance_type": "optional",
    "category": "deliverable",
    "priority": "low",
    "risk_level": "green",
    "keywords": ["additional", "references"],
    "implicit_requirements": [],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier():
    """Create RequirementClassifier with mocked init connection check."""
    with patch("shredding.requirement_classifier.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200,
                                          json=lambda: {"models": []})
        return RequirementClassifier(ollama_url="http://localhost:11434")


# ---------------------------------------------------------------------------
# TestRequirementClassifier
# ---------------------------------------------------------------------------

class TestRequirementClassifier:
    """Test suite for RequirementClassifier."""

    # --- classify(): mocked Ollama path ---

    def test_classify_returns_dataclass(self, classifier):
        """classify() returns a RequirementClassification dataclass."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The contractor shall provide support.")
        assert isinstance(result, RequirementClassification)

    def test_classify_has_all_fields(self, classifier):
        """All expected fields are present on the returned dataclass."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The system shall use AES-256.")
        assert hasattr(result, "compliance_type")
        assert hasattr(result, "category")
        assert hasattr(result, "priority")
        assert hasattr(result, "risk_level")
        assert hasattr(result, "keywords")
        assert hasattr(result, "implicit_requirements")
        assert hasattr(result, "extracted_entities")

    def test_mandatory_compliance_type(self, classifier):
        """Ollama response with mandatory is surfaced correctly."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The contractor must comply with regulations.")
        assert result.compliance_type == "mandatory"

    def test_recommended_compliance_type(self, classifier):
        """Ollama response with recommended is surfaced correctly."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_RECOMMENDED_RESPONSE)):
            result = classifier.classify("Contractors should have ISO 27001 certification.")
        assert result.compliance_type == "recommended"

    def test_optional_compliance_type(self, classifier):
        """Ollama response with optional is surfaced correctly."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_OPTIONAL_RESPONSE)):
            result = classifier.classify("Offerors may provide additional references.")
        assert result.compliance_type == "optional"

    def test_category_technical(self, classifier):
        """Category field is populated from Ollama response."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The system shall use AES-256.")
        assert result.category == "technical"

    def test_priority_high(self, classifier):
        """Priority field is populated from Ollama response."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The system shall maintain 99.99% uptime.")
        assert result.priority == "high"

    def test_keywords_list(self, classifier):
        """Keywords are returned as a list."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The system shall use AES-256 encryption.")
        assert isinstance(result.keywords, list)
        assert "security" in result.keywords

    def test_keywords_joinable(self, classifier):
        """Keywords list is joinable for downstream processing."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The system shall implement NIST 800-53 controls.")
        keyword_str = " ".join(result.keywords).lower()
        assert len(keyword_str) > 0

    def test_entity_extraction_returns_dict(self, classifier):
        """extracted_entities is always a dict."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The contractor shall comply with NIST 800-171.")
        assert isinstance(result.extracted_entities, dict)

    def test_entity_extraction_has_standard_keys(self, classifier):
        """extracted_entities contains expected sub-keys."""
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            result = classifier.classify("The system must comply with NIST 800-53.")
        assert "standards" in result.extracted_entities or "acronyms" in result.extracted_entities

    # --- classify(): fallback path (Ollama unavailable) ---

    def test_fallback_mandatory_on_shall(self, classifier):
        """Fallback classifies 'shall' as mandatory without Ollama."""
        with patch("shredding.requirement_classifier.requests.post",
                   side_effect=Exception("Connection refused")):
            result = classifier.classify("The contractor shall provide services.")
        assert result.compliance_type == "mandatory"

    def test_fallback_mandatory_on_must(self, classifier):
        """Fallback classifies 'must' as mandatory without Ollama."""
        with patch("shredding.requirement_classifier.requests.post",
                   side_effect=Exception("Connection refused")):
            result = classifier.classify("The system must comply with federal regulations.")
        assert result.compliance_type == "mandatory"

    def test_fallback_recommended_on_should(self, classifier):
        """Fallback classifies 'should' as recommended without Ollama."""
        with patch("shredding.requirement_classifier.requests.post",
                   side_effect=Exception("Connection refused")):
            result = classifier.classify("Contractors should have prior experience.")
        assert result.compliance_type == "recommended"

    def test_fallback_optional_on_may(self, classifier):
        """Fallback classifies 'may' as optional without Ollama."""
        with patch("shredding.requirement_classifier.requests.post",
                   side_effect=Exception("Connection refused")):
            result = classifier.classify("Offerors may provide additional references.")
        assert result.compliance_type == "optional"

    def test_fallback_returns_dataclass(self, classifier):
        """Fallback still returns RequirementClassification dataclass."""
        with patch("shredding.requirement_classifier.requests.post",
                   side_effect=Exception("down")):
            result = classifier.classify("The contractor shall provide support.")
        assert isinstance(result, RequirementClassification)

    # --- classify_batch() ---

    def test_batch_returns_same_count(self, classifier):
        """classify_batch returns one result per requirement."""
        requirements = [
            {"text": "The contractor shall provide technical support.", "section": "C"},
            {"text": "The system should integrate with infrastructure.", "section": "C"},
            {"text": "Additional services may be requested.", "section": "C"},
        ]
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            results = classifier.classify_batch(requirements, show_progress=False)
        assert len(results) == 3

    def test_batch_returns_dataclass_instances(self, classifier):
        """classify_batch results are RequirementClassification instances."""
        requirements = [
            {"text": "The contractor shall comply.", "section": "C"},
        ]
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            results = classifier.classify_batch(requirements, show_progress=False)
        assert all(isinstance(r, RequirementClassification) for r in results)

    def test_batch_has_compliance_type(self, classifier):
        """All batch results have compliance_type attribute."""
        requirements = [{"text": "The system shall support 10,000 users.", "section": "C"}]
        with patch("shredding.requirement_classifier.requests.post",
                   return_value=_mock_ollama_response(_MANDATORY_RESPONSE)):
            results = classifier.classify_batch(requirements, show_progress=False)
        assert all(hasattr(r, "compliance_type") for r in results)

    # --- edge cases ---

    def test_empty_text_does_not_crash(self, classifier):
        """Empty text returns a RequirementClassification without crashing."""
        with patch("shredding.requirement_classifier.requests.post",
                   side_effect=Exception("down")):
            result = classifier.classify("")
        assert result is not None
        assert hasattr(result, "compliance_type")

    def test_bad_json_from_ollama_falls_back(self, classifier):
        """If Ollama returns invalid JSON, fallback classification is used."""
        bad_resp = MagicMock()
        bad_resp.status_code = 200
        bad_resp.json.return_value = {"response": "NOT JSON AT ALL"}
        with patch("shredding.requirement_classifier.requests.post", return_value=bad_resp):
            result = classifier.classify("The contractor shall provide services.")
        assert isinstance(result, RequirementClassification)
        assert result.compliance_type == "mandatory"  # fallback via keyword


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
