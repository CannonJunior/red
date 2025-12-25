"""
Requirement Extractor for RFP Shredding

Extracts individual requirements from RFP sections using compliance
keywords and NLP techniques.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """Individual RFP requirement."""
    id: str
    section: str
    text: str
    page_number: Optional[int] = None
    paragraph_id: Optional[str] = None
    compliance_type: str = 'unknown'  # mandatory, recommended, optional
    keywords: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class RequirementExtractor:
    """
    Extract requirements from RFP sections.

    Uses compliance keywords to identify sentences that represent
    requirements that must be addressed in the proposal.
    """

    # Compliance keywords (in priority order)
    MANDATORY_KEYWORDS = [
        r'\bshall\b',
        r'\bmust\b',
        r'\bwill\b',
        r'\brequired\b',
        r'\bmandatory\b',
        r'\b(is|are)\s+required\b'
    ]

    RECOMMENDED_KEYWORDS = [
        r'\bshould\b',
        r'\bencouraged\b',
        r'\brecommended\b',
        r'\bpreferred\b'
    ]

    OPTIONAL_KEYWORDS = [
        r'\bmay\b',
        r'\bcan\b',
        r'\bcould\b',
        r'\boptional\b',
        r'\bat\s+(?:the\s+)?offeror(?:\'s)?\s+discretion\b'
    ]

    # Negative patterns (don't extract these as requirements)
    NEGATIVE_PATTERNS = [
        r'^\s*\d+[\.\)]\s*$',  # Just numbers
        r'^\s*[A-Z]\.\s*$',     # Just letters
        r'^\s*page\s+\d+',      # Page markers
        r'^\s*table\s+',        # Table headers
        r'^\s*figure\s+',       # Figure captions
    ]

    # Conditional patterns
    CONDITIONAL_PATTERNS = [
        r'\bif\b.+\b(shall|must|will|should)\b',
        r'\bwhen\b.+\b(shall|must|will|should)\b',
        r'\bin\s+the\s+event\b.+\b(shall|must|will|should)\b'
    ]

    def __init__(self):
        """Initialize requirement extractor."""
        # Compile regex patterns
        self.mandatory_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.MANDATORY_KEYWORDS
        ]
        self.recommended_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.RECOMMENDED_KEYWORDS
        ]
        self.optional_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.OPTIONAL_KEYWORDS
        ]
        self.negative_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.NEGATIVE_PATTERNS
        ]
        self.conditional_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.CONDITIONAL_PATTERNS
        ]

    def extract_requirements(
        self,
        text: str,
        section: str = 'C',
        start_page: Optional[int] = None
    ) -> List[Requirement]:
        """
        Extract requirements from section text.

        Args:
            text: Section text
            section: Section identifier (C, L, M, etc.)
            start_page: Optional starting page number

        Returns:
            List of extracted requirements
        """
        logger.info(f"Extracting requirements from Section {section}")

        # First try to split by numbered paragraphs
        paragraphs = self._split_by_paragraph_numbers(text)

        if paragraphs:
            logger.info(f"Processing {len(paragraphs)} numbered paragraphs")
            requirements = self._extract_from_numbered_paragraphs(paragraphs, section, start_page)
        else:
            # Fallback to sentence-based extraction
            logger.info("No numbered paragraphs found, using sentence-based extraction")
            sentences = self._split_sentences(text)
            logger.info(f"Processing {len(sentences)} sentences")
            requirements = self._extract_from_sentences(sentences, section, start_page)

        return requirements

    def _extract_from_numbered_paragraphs(
        self,
        paragraphs: List[Dict],
        section: str,
        start_page: Optional[int]
    ) -> List[Requirement]:
        """
        Extract requirements from numbered paragraphs.

        Args:
            paragraphs: List of paragraph dicts with 'number', 'text', 'level'
            section: Section identifier
            start_page: Optional starting page number

        Returns:
            List of requirements
        """
        requirements = []
        req_counter = 1

        for para in paragraphs:
            para_text = para['text'].strip()
            para_number = para['number']

            # Skip empty paragraphs or headers
            if not para_text or len(para_text.split()) < 3:
                continue

            # Skip section headers (e.g., "3.1 TECHNICAL REQUIREMENTS")
            if para_text.isupper() and len(para_text.split()) < 10:
                continue

            # Check for compliance keywords
            compliance_type, keywords = self._classify_sentence(para_text)

            if compliance_type != 'unknown':
                # Extract requirement
                req = Requirement(
                    id=f"{section}-{req_counter:03d}",
                    section=section,
                    text=para_text,
                    compliance_type=compliance_type,
                    keywords=keywords,
                    paragraph_id=para_number
                )

                # Estimate page number
                if start_page:
                    req.page_number = start_page

                requirements.append(req)
                req_counter += 1

        return requirements

    def _extract_from_sentences(
        self,
        sentences: List[str],
        section: str,
        start_page: Optional[int]
    ) -> List[Requirement]:
        """
        Extract requirements from sentences (fallback method).

        Args:
            sentences: List of sentences
            section: Section identifier
            start_page: Optional starting page number

        Returns:
            List of requirements
        """
        requirements = []
        req_counter = 1

        for sent_idx, sentence in enumerate(sentences):
            # Skip if matches negative patterns
            if self._is_negative(sentence):
                continue

            # Check for compliance keywords
            compliance_type, keywords = self._classify_sentence(sentence)

            if compliance_type != 'unknown':
                # Extract requirement
                req = Requirement(
                    id=f"{section}-{req_counter:03d}",
                    section=section,
                    text=sentence.strip(),
                    compliance_type=compliance_type,
                    keywords=keywords,
                    paragraph_id=self._extract_paragraph_id(sentence)
                )

                # Estimate page number
                if start_page:
                    # Roughly estimate page (50 sentences per page)
                    req.page_number = start_page + (sent_idx // 50)

                requirements.append(req)
                req_counter += 1

        logger.info(f"Extracted {len(requirements)} requirements from Section {section}")

        # Log breakdown
        mandatory = sum(1 for r in requirements if r.compliance_type == 'mandatory')
        recommended = sum(1 for r in requirements if r.compliance_type == 'recommended')
        optional = sum(1 for r in requirements if r.compliance_type == 'optional')

        logger.info(f"  Mandatory: {mandatory}")
        logger.info(f"  Recommended: {recommended}")
        logger.info(f"  Optional: {optional}")

        return requirements

    def _split_by_paragraph_numbers(self, text: str) -> List[Dict]:
        """
        Split text by numbered paragraphs (e.g., 3.1.1, 3.2, 4.1.2).

        Handles hierarchical numbering commonly found in government RFPs.

        Args:
            text: Section text

        Returns:
            List of dicts with 'number', 'text', 'level' keys
            Empty list if no numbered paragraphs found
        """
        paragraphs = []

        # Pattern to match paragraph numbers: 1.2.3, 3.1, 4.2.1.1, etc.
        # Matches at start of line or after newline
        para_pattern = re.compile(
            r'^(\d+(?:\.\d+)*)\s+(.+?)(?=^\d+(?:\.\d+)+\s+|\Z)',
            re.MULTILINE | re.DOTALL
        )

        matches = para_pattern.findall(text)

        if not matches:
            # Try alternative pattern for paragraphs with more whitespace
            para_pattern = re.compile(
                r'(?:^|\n)(\d+(?:\.\d+)+)\s+(.+?)(?=\n\d+(?:\.\d+)+\s+|\Z)',
                re.DOTALL
            )
            matches = para_pattern.findall(text)

        for match in matches:
            para_number = match[0].strip()
            para_text = match[1].strip()

            # Calculate hierarchy level (number of dots + 1)
            level = para_number.count('.') + 1

            # Only include paragraphs at leaf level (typically 3+ levels: 3.1.1)
            # or paragraphs with substantial text
            if level >= 2 and len(para_text.split()) >= 5:
                paragraphs.append({
                    'number': para_number,
                    'text': para_text,
                    'level': level
                })

        return paragraphs

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Uses simple sentence splitting with special handling for
        common government document patterns.
        """
        # Replace common abbreviations to avoid false splits
        text = re.sub(r'\bU\.S\.', 'US', text)
        text = re.sub(r'\bU\.K\.', 'UK', text)
        text = re.sub(r'\be\.g\.', 'eg', text)
        text = re.sub(r'\bi\.e\.', 'ie', text)
        text = re.sub(r'\bvs\.', 'vs', text)
        text = re.sub(r'\bFig\.', 'Fig', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Filter out very short sentences (likely fragments)
        sentences = [s for s in sentences if len(s.split()) >= 5]

        return sentences

    def _classify_sentence(self, sentence: str) -> Tuple[str, List[str]]:
        """
        Classify sentence compliance type.

        Args:
            sentence: Sentence text

        Returns:
            Tuple of (compliance_type, keywords_found)
        """
        keywords_found = []

        # Check for mandatory keywords
        for pattern in self.mandatory_patterns:
            if pattern.search(sentence):
                keywords_found.append(pattern.pattern.strip(r'\b'))

        if keywords_found:
            # Check if it's conditional
            for cond_pattern in self.conditional_patterns:
                if cond_pattern.search(sentence):
                    keywords_found.append('conditional')
                    break

            return ('mandatory', keywords_found)

        # Check for recommended keywords
        for pattern in self.recommended_patterns:
            if pattern.search(sentence):
                keywords_found.append(pattern.pattern.strip(r'\b'))

        if keywords_found:
            return ('recommended', keywords_found)

        # Check for optional keywords
        for pattern in self.optional_patterns:
            if pattern.search(sentence):
                keywords_found.append(pattern.pattern.strip(r'\b'))

        if keywords_found:
            return ('optional', keywords_found)

        return ('unknown', [])

    def _is_negative(self, sentence: str) -> bool:
        """Check if sentence matches negative patterns."""
        for pattern in self.negative_patterns:
            if pattern.match(sentence):
                return True

        # Also skip very short sentences
        if len(sentence.strip()) < 20:
            return True

        return False

    def _extract_paragraph_id(self, sentence: str) -> Optional[str]:
        """
        Extract paragraph ID if present.

        Examples: "3.2.1", "4.1", "C.2.3"
        """
        # Look for paragraph numbering at start of sentence
        match = re.match(r'^([A-Z]?\d+(?:\.\d+)+)', sentence)

        if match:
            return match.group(1)

        return None

    def deduplicate_requirements(
        self,
        requirements: List[Requirement]
    ) -> List[Requirement]:
        """
        Remove duplicate requirements.

        Sometimes the same requirement appears in multiple locations
        (e.g., both Section C and Section L).

        Args:
            requirements: List of requirements

        Returns:
            Deduplicated list
        """
        seen_texts = set()
        unique_reqs = []

        for req in requirements:
            # Normalize text for comparison
            normalized = req.text.lower().strip()

            # Remove extra whitespace
            normalized = re.sub(r'\s+', ' ', normalized)

            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_reqs.append(req)
            else:
                logger.debug(f"Duplicate requirement skipped: {req.id}")

        logger.info(f"Deduplicated: {len(requirements)} → {len(unique_reqs)} requirements")

        return unique_reqs

    def filter_by_section(
        self,
        requirements: List[Requirement],
        sections: List[str]
    ) -> List[Requirement]:
        """
        Filter requirements by section.

        Args:
            requirements: List of requirements
            sections: List of section letters to include

        Returns:
            Filtered list
        """
        filtered = [r for r in requirements if r.section in sections]

        logger.info(
            f"Filtered to sections {sections}: "
            f"{len(requirements)} → {len(filtered)}"
        )

        return filtered

    def to_dict_list(self, requirements: List[Requirement]) -> List[Dict]:
        """Convert requirements to list of dictionaries."""
        return [
            {
                'id': req.id,
                'section': req.section,
                'text': req.text,
                'page_number': req.page_number,
                'paragraph_id': req.paragraph_id,
                'compliance_type': req.compliance_type,
                'keywords': req.keywords
            }
            for req in requirements
        ]
