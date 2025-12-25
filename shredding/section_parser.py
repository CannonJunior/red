"""
Section Parser for Government RFPs

Extracts and identifies sections from FAR-format RFPs (Sections A-M),
with focus on Section C (Technical), Section L (Instructions), and
Section M (Evaluation Criteria).
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_system.document_processor import DocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SectionParser:
    """
    Parse RFP documents to identify and extract sections.

    Handles Federal Acquisition Regulation (FAR) uniform contract format
    sections A through M, with special handling for critical sections.
    """

    # Section header patterns (in priority order)
    SECTION_PATTERNS = [
        # Standard formats
        r'^SECTION\s+([A-M])[:\s\-]',
        r'^SEC\.\s+([A-M])[:\s\-]',
        r'^PART\s+([IVX]+)[:\s\-]',  # Roman numerals
        r'^([A-M])\.\s+[A-Z]',        # "C. DESCRIPTION"

        # With descriptions
        r'^SECTION\s+([A-M])\s*[-:]\s*(.+)',
        r'^PART\s+([A-M])\s*[-:]\s*(.+)',

        # Numbered sections
        r'^([A-M])-\d+',               # "C-1"
    ]

    # Known section names for validation
    SECTION_NAMES = {
        'A': ['Solicitation/Contract Form', 'Solicitation Form'],
        'B': ['Supplies or Services', 'Supplies/Services'],
        'C': ['Description/Specifications', 'Statement of Work', 'SOW',
              'Statement of Objectives', 'SOO', 'Technical Requirements'],
        'L': ['Instructions', 'Instructions to Offerors',
              'Instructions, Conditions, and Notices to Offerors'],
        'M': ['Evaluation Factors', 'Evaluation Criteria',
              'Evaluation Factors for Award'],
    }

    def __init__(self):
        """Initialize section parser."""
        self.doc_processor = DocumentProcessor()
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.SECTION_PATTERNS
        ]

    def extract_sections(
        self,
        file_path: str,
        section_ranges: Optional[Dict[str, Dict[str, int]]] = None
    ) -> Dict[str, Dict]:
        """
        Extract all sections from RFP document.

        Args:
            file_path: Path to RFP PDF file
            section_ranges: Optional manual section page ranges
                           {'C': {'start_page': 10, 'end_page': 45}, ...}

        Returns:
            Dictionary of sections with metadata:
            {
                'C': {
                    'title': 'Statement of Work',
                    'start_page': 10,
                    'end_page': 45,
                    'text': '...',
                    'chunks': [...]
                },
                ...
            }
        """
        logger.info(f"Extracting sections from: {file_path}")

        # Process document
        doc_result = self.doc_processor.process_document(file_path)

        if doc_result['status'] == 'error':
            logger.error(f"Document processing failed: {doc_result['error']}")
            return {}

        # Get full text
        full_text = self._combine_chunks(doc_result['chunks'])

        # Detect sections
        if section_ranges:
            sections = self._extract_by_ranges(
                file_path, section_ranges, doc_result
            )
        else:
            sections = self._detect_sections(full_text, doc_result)

        logger.info(f"Found sections: {list(sections.keys())}")
        return sections

    def extract_section(
        self,
        file_path: str,
        section: str,
        start_page: Optional[int] = None,
        end_page: Optional[int] = None
    ) -> Dict:
        """
        Extract a specific section from RFP.

        Args:
            file_path: Path to RFP PDF
            section: Section letter (A-M)
            start_page: Optional manual start page
            end_page: Optional manual end page

        Returns:
            Section dictionary with text and metadata
        """
        section = section.upper()

        if start_page and end_page:
            # Manual page range
            return self._extract_section_by_pages(
                file_path, section, start_page, end_page
            )

        # Auto-detect
        sections = self.extract_sections(file_path)

        if section in sections:
            return sections[section]
        else:
            logger.warning(f"Section {section} not found in document")
            return {}

    def _detect_sections(
        self,
        full_text: str,
        doc_result: Dict
    ) -> Dict[str, Dict]:
        """
        Detect sections using pattern matching.

        Args:
            full_text: Complete document text
            doc_result: Document processing result

        Returns:
            Dictionary of detected sections
        """
        sections = {}
        lines = full_text.split('\n')

        current_section = None
        section_start_line = 0

        for line_num, line in enumerate(lines):
            # Try each pattern
            for pattern in self.compiled_patterns:
                match = pattern.search(line)

                if match:
                    section_letter = match.group(1)

                    # Convert Roman numerals if needed
                    if section_letter in ['I', 'II', 'III', 'IV', 'V']:
                        section_letter = self._roman_to_letter(section_letter)

                    # Validate it's a real section
                    if section_letter not in self.SECTION_NAMES:
                        continue

                    # Save previous section
                    if current_section:
                        sections[current_section] = {
                            'title': self._extract_section_title(
                                lines[section_start_line]
                            ),
                            'start_line': section_start_line,
                            'end_line': line_num - 1,
                            'text': '\n'.join(lines[section_start_line:line_num])
                        }

                    # Start new section
                    current_section = section_letter
                    section_start_line = line_num
                    logger.info(f"Found Section {section_letter} at line {line_num}")
                    break

        # Save last section
        if current_section:
            sections[current_section] = {
                'title': self._extract_section_title(lines[section_start_line]),
                'start_line': section_start_line,
                'end_line': len(lines) - 1,
                'text': '\n'.join(lines[section_start_line:])
            }

        # Enhance with page numbers
        self._add_page_numbers(sections, doc_result)

        return sections

    def _extract_by_ranges(
        self,
        file_path: str,
        section_ranges: Dict[str, Dict[str, int]],
        doc_result: Dict
    ) -> Dict[str, Dict]:
        """
        Extract sections using manual page ranges.

        Args:
            file_path: Path to PDF
            section_ranges: Page ranges per section
            doc_result: Document processing result

        Returns:
            Dictionary of sections
        """
        sections = {}

        for section, page_range in section_ranges.items():
            start_page = page_range['start_page']
            end_page = page_range['end_page']

            # Extract text from page range
            text = self._extract_page_range(
                doc_result['chunks'],
                start_page,
                end_page
            )

            sections[section] = {
                'title': self.SECTION_NAMES.get(section, ['Unknown'])[0],
                'start_page': start_page,
                'end_page': end_page,
                'text': text,
                'page_count': end_page - start_page + 1
            }

        return sections

    def _extract_section_by_pages(
        self,
        file_path: str,
        section: str,
        start_page: int,
        end_page: int
    ) -> Dict:
        """Extract section by page numbers."""
        doc_result = self.doc_processor.process_document(file_path)

        if doc_result['status'] == 'error':
            return {}

        text = self._extract_page_range(
            doc_result['chunks'],
            start_page,
            end_page
        )

        return {
            'section': section,
            'title': self.SECTION_NAMES.get(section, ['Unknown'])[0],
            'start_page': start_page,
            'end_page': end_page,
            'text': text,
            'page_count': end_page - start_page + 1
        }

    def _combine_chunks(self, chunks: List[Dict]) -> str:
        """Combine document chunks into full text."""
        return '\n'.join([chunk['text'] for chunk in chunks])

    def _extract_page_range(
        self,
        chunks: List[Dict],
        start_page: int,
        end_page: int
    ) -> str:
        """Extract text from specific page range."""
        text_parts = []

        for chunk in chunks:
            # Check if chunk has page metadata
            if 'metadata' in chunk and 'page' in chunk['metadata']:
                page = chunk['metadata']['page']
                if start_page <= page <= end_page:
                    text_parts.append(chunk['text'])

        return '\n'.join(text_parts)

    def _extract_section_title(self, header_line: str) -> str:
        """Extract clean section title from header."""
        # Remove section identifier
        for pattern in self.compiled_patterns:
            header_line = pattern.sub('', header_line)

        # Clean up
        title = header_line.strip()
        title = re.sub(r'^[-:\s]+', '', title)
        title = re.sub(r'[-:\s]+$', '', title)

        return title

    def _add_page_numbers(self, sections: Dict, doc_result: Dict):
        """Add page number metadata to sections."""
        # This requires page mapping from Docling
        # For now, estimate based on line numbers
        total_lines = sum(len(chunk['text'].split('\n'))
                         for chunk in doc_result['chunks'])

        for section_data in sections.values():
            start_line = section_data['start_line']
            end_line = section_data['end_line']

            # Estimate pages (assuming 50 lines per page)
            section_data['estimated_start_page'] = start_line // 50
            section_data['estimated_end_page'] = end_line // 50

    def _roman_to_letter(self, roman: str) -> str:
        """Convert Roman numeral to section letter."""
        roman_map = {
            'I': 'A', 'II': 'B', 'III': 'C', 'IV': 'D',
            'V': 'E', 'VI': 'F', 'VII': 'G', 'VIII': 'H'
        }
        return roman_map.get(roman, roman)

    def validate_sections(self, sections: Dict[str, Dict]) -> Dict[str, bool]:
        """
        Validate that critical sections were found.

        Args:
            sections: Dictionary of extracted sections

        Returns:
            Validation results for critical sections
        """
        validation = {
            'has_section_c': 'C' in sections,
            'has_section_l': 'L' in sections,
            'has_section_m': 'M' in sections,
            'is_complete': all([
                'C' in sections,
                'L' in sections,
                'M' in sections
            ])
        }

        if not validation['is_complete']:
            logger.warning(
                f"Missing critical sections. Found: {list(sections.keys())}"
            )

        return validation
