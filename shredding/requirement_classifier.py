"""
Requirement Classifier using Ollama

Classifies RFP requirements using local Ollama LLM for:
- Category (technical, management, cost, deliverable)
- Priority (high, medium, low)
- Risk level (red, yellow, green)
- Entity extraction (dates, standards, agencies)
"""

import json
import logging
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RequirementClassification:
    """Classification result for a requirement."""
    compliance_type: str  # mandatory, recommended, optional
    category: str         # technical, management, cost, deliverable, compliance
    priority: str         # high, medium, low
    risk_level: str       # red, yellow, green
    keywords: List[str]
    implicit_requirements: List[str]
    extracted_entities: Dict[str, List[str]]


class RequirementClassifier:
    """
    Classify requirements using Ollama LLM.

    Uses prompt engineering to extract structured classification
    from requirement text.
    """

    CLASSIFICATION_PROMPT = """You are an expert at analyzing government RFP requirements.

Analyze this requirement from a government solicitation:

"{requirement_text}"

Source: Section {section}, Page {page}

Provide a structured classification with these fields:

1. **compliance_type**: Is this mandatory, recommended, or optional?
   - "mandatory" = MUST comply (contains "shall", "must", "will", "required")
   - "recommended" = SHOULD comply (contains "should", "encouraged")
   - "optional" = MAY comply (contains "may", "can", "could")

2. **category**: What type of requirement is this?
   - "technical" = Technical specifications, performance, security
   - "management" = Management approach, processes, organization
   - "cost" = Pricing, cost structure, payment terms
   - "deliverable" = Documents, reports, products to deliver
   - "compliance" = Certifications, registrations, legal requirements

3. **priority**: How critical is this requirement to proposal success?
   - "high" = Critical, likely scored heavily, differentiator
   - "medium" = Important but not show-stopper
   - "low" = Nice-to-have, minor scoring factor

4. **risk_level**: What's the risk of non-compliance?
   - "red" = High risk - could eliminate proposal
   - "yellow" = Medium risk - could lose points
   - "green" = Low risk - minor impact

5. **keywords**: Extract 3-5 most important keywords from the requirement

6. **implicit_requirements**: What unstated requirements are implied by this statement?

Respond ONLY with valid JSON matching this exact structure:
{{
  "compliance_type": "mandatory|recommended|optional",
  "category": "technical|management|cost|deliverable|compliance",
  "priority": "high|medium|low",
  "risk_level": "red|yellow|green",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "implicit_requirements": ["implied requirement 1", "implied requirement 2"]
}}
"""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b",
        batch_size: int = 1
    ):
        """
        Initialize classifier.

        Args:
            ollama_url: URL of Ollama server
            model: Model to use for classification
            batch_size: Number of requirements to classify in one call
        """
        self.ollama_url = ollama_url
        self.model = model
        self.batch_size = batch_size

        # Test connection
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                logger.info(f"Connected to Ollama. Available models: {len(models)}")
            else:
                logger.warning(f"Ollama connection issue: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")

    def classify(
        self,
        requirement_text: str,
        section: str = "C",
        page: Optional[int] = None
    ) -> RequirementClassification:
        """
        Classify a single requirement.

        Args:
            requirement_text: The requirement text
            section: Section letter (C, L, M)
            page: Page number

        Returns:
            RequirementClassification object
        """
        # Build prompt
        prompt = self.CLASSIFICATION_PROMPT.format(
            requirement_text=requirement_text,
            section=section,
            page=page or "Unknown"
        )

        # Call Ollama
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')

                # Parse JSON response
                try:
                    classification_data = json.loads(generated_text)

                    # Create classification object
                    return RequirementClassification(
                        compliance_type=classification_data.get('compliance_type', 'unknown'),
                        category=classification_data.get('category', 'unknown'),
                        priority=classification_data.get('priority', 'medium'),
                        risk_level=classification_data.get('risk_level', 'yellow'),
                        keywords=classification_data.get('keywords', []),
                        implicit_requirements=classification_data.get('implicit_requirements', []),
                        extracted_entities=self._extract_entities(requirement_text)
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Ollama response as JSON: {e}")
                    logger.error(f"Response was: {generated_text[:200]}")

                    # Return fallback classification
                    return self._fallback_classification(requirement_text)

            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return self._fallback_classification(requirement_text)

        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return self._fallback_classification(requirement_text)

        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return self._fallback_classification(requirement_text)

    def classify_batch(
        self,
        requirements: List[Dict],
        show_progress: bool = True
    ) -> List[RequirementClassification]:
        """
        Classify multiple requirements.

        Args:
            requirements: List of requirement dicts with 'text', 'section', 'page'
            show_progress: Show progress logging

        Returns:
            List of RequirementClassification objects
        """
        classifications = []
        total = len(requirements)

        for idx, req in enumerate(requirements):
            if show_progress and (idx % 10 == 0 or idx == total - 1):
                logger.info(f"Classifying requirements: {idx + 1}/{total}")

            classification = self.classify(
                requirement_text=req.get('text', ''),
                section=req.get('section', 'C'),
                page=req.get('page_number')
            )

            classifications.append(classification)

        return classifications

    def _fallback_classification(
        self,
        requirement_text: str
    ) -> RequirementClassification:
        """
        Fallback classification using keyword matching.

        Used when Ollama call fails.
        """
        text_lower = requirement_text.lower()

        # Determine compliance type
        if any(kw in text_lower for kw in ['shall', 'must', 'will', 'required']):
            compliance_type = 'mandatory'
        elif any(kw in text_lower for kw in ['should', 'recommended']):
            compliance_type = 'recommended'
        elif any(kw in text_lower for kw in ['may', 'can', 'optional']):
            compliance_type = 'optional'
        else:
            compliance_type = 'unknown'

        # Determine category (simple keyword matching)
        if any(kw in text_lower for kw in ['system', 'software', 'hardware', 'technical', 'security']):
            category = 'technical'
        elif any(kw in text_lower for kw in ['manage', 'process', 'organization', 'personnel']):
            category = 'management'
        elif any(kw in text_lower for kw in ['cost', 'price', 'payment', 'invoice']):
            category = 'cost'
        elif any(kw in text_lower for kw in ['deliver', 'report', 'document', 'submission']):
            category = 'deliverable'
        elif any(kw in text_lower for kw in ['comply', 'certif', 'regulation', 'standard']):
            category = 'compliance'
        else:
            category = 'technical'  # Default

        # Simple priority (all mandatory = high, recommended = medium, optional = low)
        priority = 'high' if compliance_type == 'mandatory' else 'medium'

        # Simple risk
        risk_level = 'yellow' if compliance_type == 'mandatory' else 'green'

        return RequirementClassification(
            compliance_type=compliance_type,
            category=category,
            priority=priority,
            risk_level=risk_level,
            keywords=self._extract_simple_keywords(requirement_text),
            implicit_requirements=[],
            extracted_entities=self._extract_entities(requirement_text)
        )

    def _extract_simple_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords using simple frequency analysis."""
        import re
        from collections import Counter

        # Remove common words
        stopwords = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
            'I', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you',
            'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they',
            'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one',
            'all', 'would', 'there', 'their', 'shall', 'must', 'may'
        }

        # Tokenize
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())

        # Filter stopwords
        words = [w for w in words if w not in stopwords]

        # Get most common
        counter = Counter(words)
        keywords = [word for word, count in counter.most_common(max_keywords)]

        return keywords

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities using regex patterns.

        Extracts:
        - Dates
        - Standards (NIST, ISO, etc.)
        - Acronyms
        """
        import re

        entities = {
            'dates': [],
            'standards': [],
            'acronyms': []
        }

        # Extract dates (simple patterns)
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
            r'\d{4}-\d{2}-\d{2}',         # YYYY-MM-DD
            r'[A-Z][a-z]+\s+\d{1,2},\s+\d{4}'  # Month DD, YYYY
        ]
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text))

        # Extract standards
        standard_pattern = r'\b(NIST|ISO|IEEE|FIPS|MIL-STD|DoD|FAR|DFARS)\s*[\d\-\.]+\b'
        entities['standards'] = re.findall(standard_pattern, text, re.IGNORECASE)

        # Extract acronyms (all caps words 2-6 chars)
        acronym_pattern = r'\b[A-Z]{2,6}\b'
        entities['acronyms'] = re.findall(acronym_pattern, text)

        # Deduplicate
        for key in entities:
            entities[key] = list(set(entities[key]))

        return entities

    def to_dict(self, classification: RequirementClassification) -> Dict:
        """Convert classification to dictionary."""
        return asdict(classification)
