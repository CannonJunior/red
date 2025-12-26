"""
Career-Monster: Analyze highly selective career positions.

This package provides tools for analyzing competitive hiring patterns,
with initial focus on PhD → tenure-track academic positions.
"""

__version__ = "1.0.0"
__author__ = "RED Project"

from .data_models import (
    HiringPosition,
    Candidate,
    Publication,
    Award,
    AlignmentScore,
    NetworkAnalysis,
    HiringAssessment,
    ConfidenceScore
)

from .alignment_scorer import AlignmentScorer
from .narrative_generator import NarrativeGenerator
from .database import CareerDatabase

__all__ = [
    "HiringPosition",
    "Candidate",
    "Publication",
    "Award",
    "AlignmentScore",
    "NetworkAnalysis",
    "HiringAssessment",
    "ConfidenceScore",
    "AlignmentScorer",
    "NarrativeGenerator",
    "CareerDatabase",
]
