"""
Data models for career-monster skill.

Pydantic models for positions, candidates, assessments, and related entities.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class PositionType(str, Enum):
    """Types of academic positions."""
    ASSISTANT_PROFESSOR = "Assistant Professor (Tenure-Track)"
    ASSOCIATE_PROFESSOR = "Associate Professor"
    POSTDOC = "Postdoctoral Fellow"
    RESEARCH_SCIENTIST = "Research Scientist"
    LECTURER = "Lecturer"
    OTHER = "Other"


class CareerField(str, Enum):
    """Career fields supported."""
    POLITICAL_SCIENCE = "Political Science"
    ECONOMICS = "Economics"
    COMPUTER_SCIENCE = "Computer Science"
    SOCIOLOGY = "Sociology"
    LAW = "Law"
    OTHER = "Other"


class Publication(BaseModel):
    """Academic publication."""
    title: str
    authors: List[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    citations: Optional[int] = 0
    url: Optional[str] = None
    is_peer_reviewed: bool = True


class Award(BaseModel):
    """Academic award or honor."""
    name: str
    organization: str
    year: int
    description: Optional[str] = None


class HiringPosition(BaseModel):
    """A hiring position being analyzed."""
    id: Optional[str] = None
    institution: str
    department: str
    position_title: str = Field(default=PositionType.ASSISTANT_PROFESSOR)
    field_specialty: str = Field(default=CareerField.POLITICAL_SCIENCE)
    hire_date: str  # YYYY-MM-DD format
    job_posting_url: Optional[str] = None
    department_research_areas: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None

    class Config:
        use_enum_values = True


class Candidate(BaseModel):
    """A candidate who was hired."""
    id: Optional[str] = None
    position_id: Optional[str] = None
    name: str
    current_position: Optional[str] = None
    phd_institution: str
    phd_year: int
    phd_advisor: Optional[str] = None

    # Dissertation
    dissertation_title: str
    dissertation_url: Optional[str] = None
    dissertation_keywords: List[str] = Field(default_factory=list)
    dissertation_abstract: str = ""

    # Publications
    publications: List[Publication] = Field(default_factory=list)
    publications_count: int = 0

    # Network
    co_authors: List[str] = Field(default_factory=list)

    # Metrics
    awards: List[Award] = Field(default_factory=list)
    citations_count: int = 0
    h_index: Optional[int] = None

    # Metadata
    created_at: Optional[str] = None

    def model_post_init(self, __context):
        """Calculate derived fields."""
        if not self.publications_count and self.publications:
            self.publications_count = len(self.publications)
        if not self.co_authors and self.publications:
            # Extract unique co-authors
            coauthors = set()
            for pub in self.publications:
                coauthors.update(pub.authors)
            # Remove self
            coauthors.discard(self.name)
            self.co_authors = list(coauthors)


class AlignmentScore(BaseModel):
    """Alignment between candidate and position."""
    topic_alignment: float = Field(ge=0, le=10, description="Dissertation topic match (0-10)")
    network_overlap: float = Field(ge=0, le=10, description="Co-author network match (0-10)")
    methodology_match: float = Field(ge=0, le=10, description="Research methods match (0-10)")
    publication_strength: float = Field(ge=0, le=10, description="Publication quality (0-10)")
    overall_score: float = Field(ge=0, le=10, description="Weighted average (0-10)")

    def calculate_overall(self, weights: Optional[Dict[str, float]] = None):
        """Calculate weighted overall score."""
        if weights is None:
            weights = {
                "topic": 0.35,
                "network": 0.20,
                "methodology": 0.20,
                "publications": 0.25
            }

        self.overall_score = (
            self.topic_alignment * weights["topic"] +
            self.network_overlap * weights["network"] +
            self.methodology_match * weights["methodology"] +
            self.publication_strength * weights["publications"]
        )
        return self.overall_score


class NetworkAnalysis(BaseModel):
    """Co-authorship network analysis."""
    total_collaborators: int = 0
    star_collaborators: List[str] = Field(default_factory=list, description="Highly cited co-authors")
    institutional_diversity: int = 0
    betweenness_score: Optional[float] = None
    network_quality_score: float = Field(ge=0, le=10, default=5.0)


class ConfidenceScore(BaseModel):
    """Confidence in analysis quality."""
    overall: float = Field(ge=0, le=1, description="Overall confidence (0-1)")
    data_quality: float = Field(ge=0, le=1, description="Completeness of data")
    analysis_robustness: float = Field(ge=0, le=1, description="Strength of patterns")

    def explanation(self) -> str:
        """Human-readable confidence explanation."""
        if self.overall > 0.8:
            return "HIGH CONFIDENCE: Complete data, robust patterns observed"
        elif self.overall > 0.5:
            return "MEDIUM CONFIDENCE: Partial data, suggestive patterns"
        else:
            return "LOW CONFIDENCE: Limited data, speculative analysis"

    def calculate_overall(self):
        """Calculate overall confidence from components."""
        self.overall = (self.data_quality + self.analysis_robustness) / 2
        return self.overall


class HiringAssessment(BaseModel):
    """Complete assessment of a hire."""
    id: Optional[str] = None
    candidate_id: str
    position_id: str

    # Scoring
    alignment_score: AlignmentScore
    network_analysis: NetworkAnalysis
    confidence_score: ConfidenceScore

    # Narratives (4 perspectives)
    optimistic_narrative: str = ""
    pessimistic_narrative: str = ""
    pragmatic_narrative: str = ""
    speculative_narrative: str = ""

    # Key insights
    key_success_factors: List[str] = Field(default_factory=list)
    potential_red_flags: List[str] = Field(default_factory=list)

    # Metadata
    created_at: Optional[str] = None

    def add_disclaimer(self, narrative: str) -> str:
        """Add methodological disclaimer to narrative."""
        disclaimer = (
            "\n\n---\n\n"
            "**METHODOLOGICAL NOTE**: This assessment identifies patterns and correlations "
            "in hiring data. Correlation does not imply causation. Actual hiring decisions "
            "involve factors not captured in public data, including: interviews, teaching "
            "demonstrations, departmental politics, funding availability, and strategic "
            "positioning. Use these insights as one input among many for career planning."
        )
        return narrative + disclaimer

    def get_all_narratives_with_disclaimers(self) -> Dict[str, str]:
        """Get all narratives with disclaimers added."""
        return {
            "optimistic": self.add_disclaimer(self.optimistic_narrative),
            "pessimistic": self.add_disclaimer(self.pessimistic_narrative),
            "pragmatic": self.add_disclaimer(self.pragmatic_narrative),
            "speculative": self.add_disclaimer(self.speculative_narrative)
        }


class UserProfile(BaseModel):
    """User's own profile for comparison."""
    name: Optional[str] = "User"
    phd_institution: str
    phd_year: int
    phd_advisor: Optional[str] = None
    dissertation_topic: str
    dissertation_keywords: List[str] = Field(default_factory=list)
    publications_count: int = 0
    citations_count: int = 0
    co_authors: List[str] = Field(default_factory=list)
    target_field: str = CareerField.POLITICAL_SCIENCE
    target_position_type: str = PositionType.ASSISTANT_PROFESSOR

    class Config:
        use_enum_values = True


class GapAnalysis(BaseModel):
    """Comparison between user and successful candidates."""
    user_profile: UserProfile
    avg_successful_candidate: Dict[str, float]
    gaps: Dict[str, float]  # Negative = user behind, positive = user ahead
    recommendations: List[str] = Field(default_factory=list)
    estimated_timeline: Optional[str] = None
