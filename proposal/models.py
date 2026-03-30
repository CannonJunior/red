"""
GovCon Proposal Data Models.

Pydantic models for the full proposal lifecycle. All field defaults
are intentionally permissive — validation tightens at pipeline transitions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class PipelineStage(str, Enum):
    """
    Proposal pipeline stages — aligned to Unanet CRM stage codes.

    Mapping to Unanet (see unanet_mapping.json for authoritative reference):
        identified / qualifying  → 01-Qualification
        long_lead                → 02-Long Lead
        bid_decision             → 03-Bid Decision
        active                   → 04-In Progress
        submitted                → 05-Waiting/Review
        negotiating              → 06-In Negotiation
        awarded                  → 07-Closed Won
        lost                     → 08-Closed Lost
        no_bid                   → 09-Closed No Bid
        cancelled                → 20-Closed Other Reason
        contract_vehicle_won     → 98-Awarded-Contract Vehicle
        contract_vehicle_complete→ 99-Completed Contract Vehicle
    """
    IDENTIFIED = "identified"
    QUALIFYING = "qualifying"
    LONG_LEAD = "long_lead"           # 02-Long Lead: tracked early, no active RFP yet
    BID_DECISION = "bid_decision"
    ACTIVE = "active"
    SUBMITTED = "submitted"
    NEGOTIATING = "negotiating"       # 06-In Negotiation: post-submission award discussions
    AWARDED = "awarded"
    LOST = "lost"
    NO_BID = "no_bid"
    CANCELLED = "cancelled"
    CONTRACT_VEHICLE_WON = "contract_vehicle_won"         # 98: IDIQ/GWAC vehicle awarded
    CONTRACT_VEHICLE_COMPLETE = "contract_vehicle_complete"  # 99: vehicle fully executed


class BidDecision(str, Enum):
    """Bid/No-Bid decision options."""
    BID = "bid"
    NO_BID = "no_bid"
    CONDITIONAL = "conditional"
    PENDING = "pending"


class SetAsideType(str, Enum):
    """Federal small business set-aside types."""
    FULL_AND_OPEN = "full_and_open"
    SMALL_BUSINESS = "small_business"
    SDVOSB = "sdvosb"         # Service-Disabled Veteran-Owned
    VOSB = "vosb"              # Veteran-Owned
    WOSB = "wosb"              # Women-Owned
    EDWOSB = "edwosb"          # Economically Disadvantaged WOSB
    EIGHT_A = "8a"
    HUBZONE = "hubzone"
    UNKNOWN = "unknown"


class ContractType(str, Enum):
    """Federal contract types."""
    FFP = "ffp"                # Firm Fixed Price
    TM = "t_and_m"            # Time & Materials
    LH = "labor_hour"
    CPFF = "cpff"              # Cost Plus Fixed Fee
    CPAF = "cpaf"              # Cost Plus Award Fee
    CPIF = "cpif"              # Cost Plus Incentive Fee
    IDIQ = "idiq"              # Indefinite Delivery / Indefinite Quantity
    BPA = "bpa"                # Blanket Purchase Agreement
    GWAC = "gwac"              # Government-Wide Acquisition Contract
    OTHER = "other"


class MeetingType(str, Enum):
    """Proposal meeting types."""
    KICKOFF = "kickoff"
    PINK_TEAM = "pink_team"
    RED_TEAM = "red_team"
    GOLD_TEAM = "gold_team"
    ORALS_PREP = "orals_prep"
    WEEKLY_SYNC = "weekly_sync"
    MANAGEMENT_REVIEW = "management_review"
    HOTWASH = "hotwash"
    OTHER = "other"


class ProposalOutcome(str, Enum):
    """Final proposal outcome for hotwash."""
    WON = "won"
    LOST = "lost"
    NO_BID = "no_bid"
    CANCELLED = "cancelled"
    WITHDRAWN = "withdrawn"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class TeamMember(BaseModel):
    """Proposal team member assignment."""
    name: str
    role: str                         # e.g., "Volume Lead - Technical"
    organization: str = ""            # Prime or sub name
    is_subcontractor: bool = False
    contact_email: str = ""


class PastPerformance(BaseModel):
    """Past performance reference for proposal."""
    reference_id: str
    contract_number: str = ""
    title: str
    agency: str = ""
    value: float = 0.0
    period: str = ""                  # e.g., "2022-2025"
    relevance_score: float = 0.0      # 0.0-1.0 match to this opportunity
    description: str = ""


class ColorTeamSchedule(BaseModel):
    """Color team review schedule."""
    pink_team: Optional[str] = None   # ISO date
    red_team: Optional[str] = None
    gold_team: Optional[str] = None
    orals: Optional[str] = None


class ActionItem(BaseModel):
    """Meeting or review action item."""
    description: str
    owner: str
    due_date: str                     # ISO date
    status: str = "open"              # open, in_progress, complete


# ---------------------------------------------------------------------------
# Core proposal model
# ---------------------------------------------------------------------------

class Proposal(BaseModel):
    """
    Full GovCon proposal record.

    This is the central data model. All skills read/write through this model.
    Fields are designed to map to Unanet CRM, SharePoint metadata, and
    Confluence space properties.
    """
    id: str
    opportunity_id: Optional[str] = None    # FK to opportunities table

    # Solicitation identification
    solicitation_number: str = ""           # e.g., FA8612-26-R-0001
    title: str
    agency: str = ""                        # e.g., AFRL/RQ, DISA, Navy NAVFAC
    contracting_office: str = ""            # Full contracting office name
    naics_code: str = ""                    # Primary NAICS
    naics_description: str = ""

    # Competition parameters
    set_aside_type: SetAsideType = SetAsideType.UNKNOWN
    contract_type: ContractType = ContractType.OTHER
    estimated_value: float = 0.0            # Total estimated contract value
    is_recompete: bool = False
    incumbent: str = ""
    source: str = ""                        # SAM.gov, eBuy, PTAC, industry_day

    # Dates — all ISO format strings for SQLite compatibility
    rfp_release_date: Optional[str] = None
    questions_due_date: Optional[str] = None
    proposal_due_date: Optional[str] = None # CRITICAL — primary deadline
    award_date: Optional[str] = None
    period_of_performance: str = ""         # e.g., "24 months base + 2 x 12-mo OY"

    # Pipeline state
    pipeline_stage: PipelineStage = PipelineStage.IDENTIFIED
    bid_decision: BidDecision = BidDecision.PENDING
    bid_decision_date: Optional[str] = None
    bid_decision_rationale: str = ""
    pwin_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Team
    capture_manager: str = ""
    proposal_manager: str = ""
    volume_leads: List[str] = Field(default_factory=list)
    team_members: List[TeamMember] = Field(default_factory=list)
    teaming_partners: List[str] = Field(default_factory=list)
    key_personnel: List[str] = Field(default_factory=list)

    # Past performance
    relevant_past_performance: List[PastPerformance] = Field(default_factory=list)

    # Review schedule
    color_teams: ColorTeamSchedule = Field(default_factory=ColorTeamSchedule)
    submission_method: str = ""             # PIEE, email, hand-delivery, etc.

    # Integration IDs — set by crm-sync skill
    crm_opportunity_id: str = ""            # Unanet CRM ID
    sharepoint_folder_url: str = ""
    sharepoint_site_id: str = ""
    confluence_space_key: str = ""

    # Analysis references
    shred_analysis_id: str = ""             # ID from shredding skill output

    # Metadata
    notes: str = ""
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("pwin_score", mode="before")
    @classmethod
    def validate_pwin(cls, v: Any) -> Optional[float]:
        """Accept pwin as 0-100 percentage or 0.0-1.0 fraction."""
        if v is None:
            return None
        v = float(v)
        # Reason: Users often enter pwin as 0-100; normalize to 0.0-1.0
        if v > 1.0:
            return v / 100.0
        return v

    @property
    def fiscal_year(self) -> str:
        """Derive fiscal year from proposal_due_date or rfp_release_date."""
        date_str = self.proposal_due_date or self.rfp_release_date
        if not date_str:
            return "FY??"
        dt = datetime.fromisoformat(date_str[:10])
        # Federal FY: Oct 1 - Sep 30
        fy = dt.year + 1 if dt.month >= 10 else dt.year
        return f"FY{str(fy)[2:]}"

    @property
    def short_id(self) -> str:
        """Short solicitation identifier for folder/file naming."""
        return self.solicitation_number.replace("/", "-") or self.id[:8]

    def days_until_due(self) -> Optional[int]:
        """Days remaining until proposal due date."""
        if not self.proposal_due_date:
            return None
        due = datetime.fromisoformat(self.proposal_due_date)
        delta = due - datetime.now()
        return delta.days


# ---------------------------------------------------------------------------
# Meeting model
# ---------------------------------------------------------------------------

class ProposalMeeting(BaseModel):
    """Record of a proposal-related meeting."""
    id: str
    proposal_id: str
    meeting_type: MeetingType = MeetingType.OTHER
    title: str
    scheduled_date: Optional[str] = None
    actual_date: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    agenda: str = ""
    notes: str = ""
    action_items: List[ActionItem] = Field(default_factory=list)
    confluence_page_id: str = ""
    confluence_page_url: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Hotwash model
# ---------------------------------------------------------------------------

class HotwashEvent(BaseModel):
    """Post-proposal retrospective record."""
    id: str
    proposal_id: str
    outcome: ProposalOutcome
    facilitator: str = ""
    event_date: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    what_went_well: List[str] = Field(default_factory=list)
    what_to_improve: List[str] = Field(default_factory=list)
    lessons_learned: List[str] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    process_score: Optional[int] = Field(None, ge=1, le=10)
    debrief_requested: bool = False
    debrief_notes: str = ""
    confluence_page_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Bid/No-Bid scoring model
# ---------------------------------------------------------------------------

class BidNoBidCriterion(BaseModel):
    """Single criterion in the Shipley B/NB scoring matrix."""
    name: str
    weight: float = 1.0               # Relative weight (default equal-weight)
    score: Optional[float] = None     # 1-10 score
    notes: str = ""
    rationale: str = ""


class BidNoBidAssessment(BaseModel):
    """
    Shipley-based Bid/No-Bid assessment.

    Standard 8-factor weighted scoring used in GovCon best practice.
    Total weighted score determines recommendation:
        ≥70 → Bid  |  50-69 → Conditional  |  <50 → No-Bid
    """
    proposal_id: str
    assessor: str = ""
    assessment_date: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Core Shipley Go/No-Go factors
    criteria: List[BidNoBidCriterion] = Field(default_factory=lambda: [
        BidNoBidCriterion(name="Customer Knowledge", weight=1.5),
        BidNoBidCriterion(name="Competitive Position", weight=1.5),
        BidNoBidCriterion(name="Incumbent Advantage", weight=1.25),
        BidNoBidCriterion(name="Technical Capability Match", weight=1.5),
        BidNoBidCriterion(name="Past Performance Relevance", weight=1.25),
        BidNoBidCriterion(name="Team & Resource Availability", weight=1.0),
        BidNoBidCriterion(name="Price to Win Feasibility", weight=1.25),
        BidNoBidCriterion(name="Risk Assessment", weight=1.0),
    ])

    # Additional qualitative factors
    win_themes: List[str] = Field(default_factory=list)
    discriminators: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)

    # Decision
    recommendation: BidDecision = BidDecision.PENDING
    recommendation_rationale: str = ""
    final_decision: BidDecision = BidDecision.PENDING
    decision_made_by: str = ""
    decision_date: Optional[str] = None

    def weighted_score(self) -> float:
        """
        Calculate the weighted score (0-100 scale).

        Returns:
            float: Weighted average score normalized to 0-100.
        """
        scored = [c for c in self.criteria if c.score is not None]
        if not scored:
            return 0.0
        total_weight = sum(c.weight for c in scored)
        weighted_sum = sum(c.score * c.weight for c in scored)
        # Normalize from 0-10 scale to 0-100 scale
        return (weighted_sum / total_weight) * 10

    def auto_recommendation(self) -> BidDecision:
        """
        Derive recommendation from weighted score.

        Returns:
            BidDecision: BID if ≥70, CONDITIONAL if 50-70, NO_BID if <50.
        """
        score = self.weighted_score()
        if score >= 70:
            return BidDecision.BID
        elif score >= 50:
            return BidDecision.CONDITIONAL
        else:
            return BidDecision.NO_BID
