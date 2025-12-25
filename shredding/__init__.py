"""
RFP Shredding Module

Provides automated RFP (Request for Proposal) analysis and requirement extraction
for government solicitations.
"""

from .section_parser import SectionParser
from .requirement_extractor import RequirementExtractor
from .requirement_classifier import RequirementClassifier
from .rfp_shredder import RFPShredder

__all__ = [
    'SectionParser',
    'RequirementExtractor',
    'RequirementClassifier',
    'RFPShredder'
]

__version__ = '1.0.0'
