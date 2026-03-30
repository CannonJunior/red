"""
Proposal Workflow System — Core Library

GovCon proposal lifecycle management from opportunity identification
through contract award and hotwash retrospective.

Architecture: This library contains all business logic. Skills in
.claude/skills/ are thin wrappers that invoke these modules.

Pipeline Stages:
    identified → qualifying → bid_decision → active → submitted → awarded/lost/no_bid
"""

__version__ = "1.0.0"
