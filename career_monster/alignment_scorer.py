"""
Alignment Scorer: Calculate how well a candidate matches a position.

Uses keyword matching, co-author overlap, and publication metrics to score alignment.
"""

import re
from typing import List, Set
from .data_models import (
    Candidate,
    HiringPosition,
    AlignmentScore,
    NetworkAnalysis,
    ConfidenceScore
)


class AlignmentScorer:
    """Calculate alignment between candidates and positions."""

    def __init__(self):
        """Initialize alignment scorer."""
        # Common stopwords for academic text
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }

    def calculate_alignment(
        self,
        candidate: Candidate,
        position: HiringPosition
    ) -> AlignmentScore:
        """
        Calculate comprehensive alignment score.

        Args:
            candidate: The hired candidate
            position: The position they were hired for

        Returns:
            AlignmentScore with all metrics
        """
        # Calculate individual scores
        topic_score = self._calculate_topic_alignment(candidate, position)
        network_score = self._calculate_network_overlap(candidate, position)
        method_score = self._calculate_methodology_match(candidate, position)
        pub_score = self._calculate_publication_strength(candidate)

        # Create alignment score
        alignment = AlignmentScore(
            topic_alignment=topic_score,
            network_overlap=network_score,
            methodology_match=method_score,
            publication_strength=pub_score,
            overall_score=0.0  # Will be calculated
        )

        # Calculate weighted overall score
        alignment.calculate_overall()

        return alignment

    def _calculate_topic_alignment(
        self,
        candidate: Candidate,
        position: HiringPosition
    ) -> float:
        """
        Calculate topic alignment using keyword matching.

        Args:
            candidate: Candidate with dissertation keywords
            position: Position with department research areas

        Returns:
            Score from 0-10
        """
        if not candidate.dissertation_keywords or not position.department_research_areas:
            # Insufficient data - return neutral score
            return 5.0

        # Extract and clean keywords
        candidate_keywords = self._extract_keywords(
            candidate.dissertation_keywords + [candidate.dissertation_title]
        )
        dept_keywords = self._extract_keywords(
            position.department_research_areas + [position.field_specialty]
        )

        # Calculate overlap
        if not candidate_keywords or not dept_keywords:
            return 5.0

        intersection = candidate_keywords & dept_keywords
        union = candidate_keywords | dept_keywords

        # Jaccard similarity
        jaccard = len(intersection) / len(union) if union else 0

        # Calculate semantic overlap (simple keyword matching)
        overlap_count = 0
        for c_keyword in candidate_keywords:
            for d_keyword in dept_keywords:
                if self._keywords_similar(c_keyword, d_keyword):
                    overlap_count += 1

        # Normalize to 0-10 scale
        # Strong overlap = 8-10, moderate = 5-7, weak = 2-4, none = 0-1
        if overlap_count >= 5:
            score = 9.0
        elif overlap_count >= 3:
            score = 7.5
        elif overlap_count >= 1:
            score = 5.5
        elif jaccard > 0.1:
            score = 4.0
        else:
            score = 2.0

        return min(10.0, score)

    def _calculate_network_overlap(
        self,
        candidate: Candidate,
        position: HiringPosition
    ) -> float:
        """
        Calculate co-author network overlap.

        In Phase 1, we don't have department faculty co-author data,
        so we score based on network size and diversity.

        Args:
            candidate: Candidate with co-authors list
            position: Position (for future use)

        Returns:
            Score from 0-10
        """
        if not candidate.co_authors:
            return 3.0  # Low score for no collaborations

        # Score based on number of unique collaborators
        num_collaborators = len(candidate.co_authors)

        if num_collaborators >= 10:
            score = 9.0
        elif num_collaborators >= 7:
            score = 7.5
        elif num_collaborators >= 5:
            score = 6.0
        elif num_collaborators >= 3:
            score = 4.5
        else:
            score = 3.0

        return score

    def _calculate_methodology_match(
        self,
        candidate: Candidate,
        position: HiringPosition
    ) -> float:
        """
        Calculate methodology alignment.

        Looks for methodological keywords in dissertation vs position.

        Args:
            candidate: Candidate with dissertation info
            position: Position with field specialty

        Returns:
            Score from 0-10
        """
        # Common methodological keywords by approach
        quantitative_methods = {
            'regression', 'statistical', 'quantitative', 'econometric',
            'survey', 'experiment', 'data', 'model', 'analysis'
        }
        qualitative_methods = {
            'qualitative', 'interview', 'ethnography', 'case study',
            'archival', 'historical', 'discourse', 'narrative'
        }
        formal_methods = {
            'game theory', 'formal', 'mathematical', 'rational choice',
            'theorem', 'proof', 'model'
        }

        # Extract methods from dissertation
        diss_text = (
            candidate.dissertation_title + " " +
            candidate.dissertation_abstract + " " +
            " ".join(candidate.dissertation_keywords)
        ).lower()

        # Check which methods are present
        has_quant = any(method in diss_text for method in quantitative_methods)
        has_qual = any(method in diss_text for method in qualitative_methods)
        has_formal = any(method in diss_text for method in formal_methods)

        # Check field expectations
        field_lower = position.field_specialty.lower()

        # Default: moderate score for having clear methodology
        score = 6.0

        # Boost for multi-method approaches
        methods_count = sum([has_quant, has_qual, has_formal])
        if methods_count >= 2:
            score = 8.0
        elif methods_count >= 1:
            score = 7.0

        # Boost for formal methods in appropriate fields
        if has_formal and 'formal' in field_lower:
            score = min(10.0, score + 2.0)

        return score

    def _calculate_publication_strength(self, candidate: Candidate) -> float:
        """
        Calculate publication strength score.

        Based on number of publications and citations.

        Args:
            candidate: Candidate with publication data

        Returns:
            Score from 0-10
        """
        pub_count = candidate.publications_count
        citations = candidate.citations_count

        # Base score on publication count
        if pub_count == 0:
            pub_score = 1.0
        elif pub_count >= 8:
            pub_score = 10.0
        elif pub_count >= 5:
            pub_score = 8.5
        elif pub_count >= 3:
            pub_score = 7.0
        elif pub_count >= 2:
            pub_score = 5.5
        else:  # 1 publication
            pub_score = 4.0

        # Adjust based on citations (if available)
        if citations > 0:
            if citations >= 500:
                pub_score = min(10.0, pub_score + 2.0)
            elif citations >= 200:
                pub_score = min(10.0, pub_score + 1.5)
            elif citations >= 100:
                pub_score = min(10.0, pub_score + 1.0)
            elif citations >= 50:
                pub_score = min(10.0, pub_score + 0.5)

        return pub_score

    def analyze_network(self, candidate: Candidate) -> NetworkAnalysis:
        """
        Analyze co-authorship network.

        In Phase 1, basic analysis only.

        Args:
            candidate: Candidate to analyze

        Returns:
            NetworkAnalysis with metrics
        """
        # Count collaborators
        total_collaborators = len(candidate.co_authors)

        # Identify star collaborators (placeholder - would need citation data)
        star_collaborators = []
        # In future: check if any co-authors are highly cited

        # Estimate institutional diversity (placeholder)
        # In future: extract institutions from co-author affiliations
        institutional_diversity = min(5, total_collaborators // 2)

        # Calculate network quality score
        if total_collaborators >= 10:
            quality = 9.0
        elif total_collaborators >= 5:
            quality = 7.0
        elif total_collaborators >= 3:
            quality = 5.0
        else:
            quality = 3.0

        return NetworkAnalysis(
            total_collaborators=total_collaborators,
            star_collaborators=star_collaborators,
            institutional_diversity=institutional_diversity,
            network_quality_score=quality
        )

    def calculate_confidence(
        self,
        candidate: Candidate,
        position: HiringPosition
    ) -> ConfidenceScore:
        """
        Calculate confidence in analysis.

        Based on data completeness.

        Args:
            candidate: Candidate data
            position: Position data

        Returns:
            ConfidenceScore
        """
        # Check data completeness
        data_points = 0
        total_possible = 10

        if candidate.dissertation_abstract:
            data_points += 2
        if candidate.dissertation_keywords:
            data_points += 1
        if candidate.publications:
            data_points += 2
        if candidate.co_authors:
            data_points += 1
        if candidate.awards:
            data_points += 1
        if candidate.citations_count > 0:
            data_points += 1
        if position.department_research_areas:
            data_points += 2

        data_quality = data_points / total_possible

        # Analysis robustness based on data richness
        if data_quality > 0.7:
            robustness = 0.8
        elif data_quality > 0.5:
            robustness = 0.6
        else:
            robustness = 0.4

        confidence = ConfidenceScore(
            overall=0.0,
            data_quality=data_quality,
            analysis_robustness=robustness
        )
        confidence.calculate_overall()

        return confidence

    def _extract_keywords(self, text_list: List[str]) -> Set[str]:
        """
        Extract meaningful keywords from text.

        Args:
            text_list: List of text strings

        Returns:
            Set of cleaned keywords
        """
        keywords = set()

        for text in text_list:
            if not text:
                continue

            # Clean and split
            text_lower = text.lower()
            # Remove punctuation except hyphens
            text_clean = re.sub(r'[^\w\s-]', ' ', text_lower)

            # Split and filter
            words = text_clean.split()
            for word in words:
                # Remove stopwords and short words
                if len(word) > 3 and word not in self.stopwords:
                    keywords.add(word)

        return keywords

    def _keywords_similar(self, keyword1: str, keyword2: str) -> bool:
        """
        Check if two keywords are similar.

        Simple substring matching for Phase 1.

        Args:
            keyword1: First keyword
            keyword2: Second keyword

        Returns:
            True if similar
        """
        # Exact match
        if keyword1 == keyword2:
            return True

        # Substring match (one contains the other)
        if keyword1 in keyword2 or keyword2 in keyword1:
            return True

        # Stemming-like match (simple suffix removal)
        stem1 = keyword1.rstrip('s').rstrip('ing').rstrip('ed')
        stem2 = keyword2.rstrip('s').rstrip('ing').rstrip('ed')

        if stem1 == stem2:
            return True

        return False
