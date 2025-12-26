"""
Narrative Generator: Create multi-perspective assessments using Ollama.

Generates optimistic, pessimistic, pragmatic, and speculative narratives
for each hiring case.
"""

import requests
import json
import logging
from typing import Dict, Optional
from .data_models import (
    Candidate,
    HiringPosition,
    AlignmentScore,
    NetworkAnalysis,
    HiringAssessment
)

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """Generate multi-perspective hiring assessments."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b"
    ):
        """
        Initialize narrative generator.

        Args:
            ollama_url: URL of Ollama server
            model: Model to use for generation
        """
        self.ollama_url = ollama_url
        self.model = model

    def generate_assessment(
        self,
        candidate: Candidate,
        position: HiringPosition,
        alignment: AlignmentScore,
        network: NetworkAnalysis,
        verbosity: str = "standard"
    ) -> HiringAssessment:
        """
        Generate complete hiring assessment with all perspectives.

        Args:
            candidate: The hired candidate
            position: The position
            alignment: Alignment scores
            network: Network analysis
            verbosity: Level of detail (brief, standard, detailed)

        Returns:
            Complete HiringAssessment
        """
        logger.info(f"Generating assessment for {candidate.name} → {position.institution}")

        # Generate each perspective
        optimistic = self._generate_optimistic(
            candidate, position, alignment, network, verbosity
        )
        pessimistic = self._generate_pessimistic(
            candidate, position, alignment, network, verbosity
        )
        pragmatic = self._generate_pragmatic(
            candidate, position, alignment, network, verbosity
        )
        speculative = self._generate_speculative(
            candidate, position, alignment, network, verbosity
        )

        # Extract key factors
        success_factors = self._extract_success_factors(
            candidate, position, alignment, network
        )
        red_flags = self._extract_red_flags(
            candidate, position, alignment, network
        )

        # Create assessment
        assessment = HiringAssessment(
            candidate_id=candidate.id or candidate.name,
            position_id=position.id or f"{position.institution}_{position.hire_date}",
            alignment_score=alignment,
            network_analysis=network,
            confidence_score=None,  # Will be set by caller
            optimistic_narrative=optimistic,
            pessimistic_narrative=pessimistic,
            pragmatic_narrative=pragmatic,
            speculative_narrative=speculative,
            key_success_factors=success_factors,
            potential_red_flags=red_flags
        )

        return assessment

    def _generate_optimistic(
        self,
        candidate: Candidate,
        position: HiringPosition,
        alignment: AlignmentScore,
        network: NetworkAnalysis,
        verbosity: str
    ) -> str:
        """Generate optimistic perspective."""

        context = self._build_context(candidate, position, alignment, network)

        prompt = f"""You are analyzing an academic hiring case from an OPTIMISTIC perspective.

{context}

Write an optimistic assessment explaining why this hire makes perfect sense.
Focus on:
- Exceptional strengths and qualifications
- Perfect timing and market conditions
- Strategic advantages they bring to the department
- How they exceeded requirements
- Their future potential and trajectory

{self._get_verbosity_instruction(verbosity)}

Write the optimistic assessment:"""

        response = self._call_ollama(prompt)
        return response

    def _generate_pessimistic(
        self,
        candidate: Candidate,
        position: HiringPosition,
        alignment: AlignmentScore,
        network: NetworkAnalysis,
        verbosity: str
    ) -> str:
        """Generate pessimistic/critical perspective."""

        context = self._build_context(candidate, position, alignment, network)

        prompt = f"""You are analyzing an academic hiring case from a CRITICAL/SKEPTICAL perspective.

{context}

Write a critical assessment examining potential weaknesses in this hire.
Focus on:
- Potential gaps or limitations in qualifications
- Competitive disadvantages they may have overcome
- Market conditions that may have worked against them
- Risks the department took with this hire
- Alternative explanations beyond pure merit

{self._get_verbosity_instruction(verbosity)}

Write the critical assessment:"""

        response = self._call_ollama(prompt)
        return response

    def _generate_pragmatic(
        self,
        candidate: Candidate,
        position: HiringPosition,
        alignment: AlignmentScore,
        network: NetworkAnalysis,
        verbosity: str
    ) -> str:
        """Generate balanced, pragmatic perspective."""

        context = self._build_context(candidate, position, alignment, network)

        prompt = f"""You are analyzing an academic hiring case from a BALANCED, PRAGMATIC perspective.

{context}

Write a realistic assessment that weighs both strengths and weaknesses.
Focus on:
- Both strengths AND weaknesses (balanced view)
- Clear evidence versus speculation
- Market realities and constraints
- Probable decision-making factors
- Reproducible success elements for others to learn from

{self._get_verbosity_instruction(verbosity)}

Write the pragmatic assessment:"""

        response = self._call_ollama(prompt)
        return response

    def _generate_speculative(
        self,
        candidate: Candidate,
        position: HiringPosition,
        alignment: AlignmentScore,
        network: NetworkAnalysis,
        verbosity: str
    ) -> str:
        """Generate speculative perspective (hidden factors)."""

        context = self._build_context(candidate, position, alignment, network)

        prompt = f"""You are analyzing an academic hiring case from a SPECULATIVE perspective, considering non-obvious factors.

{context}

Write a speculative assessment exploring hidden or non-obvious factors.
Focus on:
- Personal connections and professional networks
- Timing and strategic positioning in the market
- Possible department politics or strategic needs
- Funding, grant implications, or financial factors
- Diversity initiatives or strategic hiring priorities
- Factors not visible in public record

{self._get_verbosity_instruction(verbosity)}

Write the speculative assessment:"""

        response = self._call_ollama(prompt)
        return response

    def _build_context(
        self,
        candidate: Candidate,
        position: HiringPosition,
        alignment: AlignmentScore,
        network: NetworkAnalysis
    ) -> str:
        """Build context summary for LLM."""

        context = f"""HIRING CASE:

**Position:**
- Institution: {position.institution}
- Department: {position.department}
- Position: {position.position_title}
- Field: {position.field_specialty}
- Hire Date: {position.hire_date}

**Candidate:**
- Name: {candidate.name}
- PhD Institution: {candidate.phd_institution} ({candidate.phd_year})
- PhD Advisor: {candidate.phd_advisor or 'Not specified'}
- Dissertation: "{candidate.dissertation_title}"
- Publications: {candidate.publications_count} peer-reviewed papers
- Citations: {candidate.citations_count}
- Co-authors: {len(candidate.co_authors)} collaborators
- Awards: {len(candidate.awards)} ({', '.join([a.name for a in candidate.awards[:3]]) if candidate.awards else 'None listed'})

**Dissertation Keywords:**
{', '.join(candidate.dissertation_keywords) if candidate.dissertation_keywords else 'Not available'}

**Department Research Areas:**
{', '.join(position.department_research_areas) if position.department_research_areas else 'Not specified'}

**Alignment Scores (0-10 scale):**
- Topic Alignment: {alignment.topic_alignment:.1f}/10
- Network Overlap: {alignment.network_overlap:.1f}/10
- Methodology Match: {alignment.methodology_match:.1f}/10
- Publication Strength: {alignment.publication_strength:.1f}/10
- Overall Alignment: {alignment.overall_score:.1f}/10

**Network Analysis:**
- Total Collaborators: {network.total_collaborators}
- Network Quality: {network.network_quality_score:.1f}/10
"""
        return context

    def _get_verbosity_instruction(self, verbosity: str) -> str:
        """Get instructions based on verbosity level."""
        if verbosity == "brief":
            return "Write 1-2 concise paragraphs."
        elif verbosity == "detailed":
            return "Write a comprehensive analysis of 1-2 pages (4-6 substantial paragraphs)."
        elif verbosity == "comprehensive":
            return "Write an in-depth analysis of 3+ pages (8-10 paragraphs with detailed evidence)."
        else:  # standard
            return "Write 3-5 well-developed paragraphs."

    def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama API to generate text.

        Args:
            prompt: The prompt to send

        Returns:
            Generated text
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 800  # Max tokens for standard verbosity
                    }
                },
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return f"[Error generating narrative: HTTP {response.status_code}]"

        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return "[Error: Request timed out. Ollama may be overloaded.]"
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return f"[Error generating narrative: {str(e)}]"

    def _extract_success_factors(
        self,
        candidate: Candidate,
        position: HiringPosition,
        alignment: AlignmentScore,
        network: NetworkAnalysis
    ) -> list:
        """Extract key success factors from the data."""

        factors = []

        # High topic alignment
        if alignment.topic_alignment >= 8.0:
            factors.append(
                f"Excellent topic alignment ({alignment.topic_alignment:.1f}/10) "
                f"between dissertation and department research"
            )

        # Strong publications
        if candidate.publications_count >= 5:
            factors.append(
                f"Strong publication record ({candidate.publications_count} papers)"
            )

        if candidate.citations_count >= 100:
            factors.append(
                f"High citation impact ({candidate.citations_count} citations)"
            )

        # Prestigious PhD
        top_schools = [
            'Harvard', 'Princeton', 'Stanford', 'MIT', 'Yale', 'Berkeley',
            'Michigan', 'Columbia', 'Duke', 'Chicago'
        ]
        if any(school in candidate.phd_institution for school in top_schools):
            factors.append(
                f"PhD from top-tier institution ({candidate.phd_institution})"
            )

        # Awards
        if candidate.awards:
            factors.append(
                f"Dissertation/research awards ({len(candidate.awards)} awards)"
            )

        # Strong network
        if network.total_collaborators >= 7:
            factors.append(
                f"Well-developed co-authorship network ({network.total_collaborators} collaborators)"
            )

        # If no factors, add generic ones
        if not factors:
            factors.append("Meets basic qualifications for position")
            if alignment.overall_score >= 6.0:
                factors.append("Moderate overall alignment with position needs")

        return factors[:5]  # Top 5 factors

    def _extract_red_flags(
        self,
        candidate: Candidate,
        position: HiringPosition,
        alignment: AlignmentScore,
        network: NetworkAnalysis
    ) -> list:
        """Extract potential concerns from the data."""

        red_flags = []

        # Low topic alignment
        if alignment.topic_alignment < 5.0:
            red_flags.append(
                f"Weak topic alignment ({alignment.topic_alignment:.1f}/10) "
                f"may indicate pivot or niche specialty"
            )

        # Few publications
        if candidate.publications_count < 2:
            red_flags.append(
                f"Limited publication record ({candidate.publications_count} papers)"
            )

        # Low citations
        if candidate.citations_count < 20 and candidate.phd_year < 2020:
            red_flags.append(
                "Low citation count relative to time since PhD"
            )

        # Small network
        if network.total_collaborators < 3:
            red_flags.append(
                "Limited co-authorship network may indicate isolation"
            )

        # Recent PhD with high expectations
        years_since_phd = 2024 - candidate.phd_year
        if years_since_phd < 2 and candidate.publications_count >= 5:
            # This is actually good, not a red flag
            pass

        # Return empty list if no red flags (most hires should be good!)
        return red_flags[:3]  # Top 3 concerns
