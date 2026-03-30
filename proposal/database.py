"""
Proposal Database — SQLite schema and query layer.

All proposal data lives in opportunities.db alongside the existing
opportunities and tasks tables. This module handles:
- Schema migration (safe, additive-only)
- CRUD operations for proposals, meetings, hotwash events
- JSON serialization of complex fields
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from proposal.models import (
    BidNoBidAssessment,
    HotwashEvent,
    Proposal,
    ProposalMeeting,
)


# Reason: DB path resolved relative to project root, configurable via env
DEFAULT_DB_PATH = Path(__file__).parent.parent / "opportunities.db"


@contextmanager
def get_conn(db_path: Path = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for SQLite connections with row_factory set.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        sqlite3.Connection: Open connection with Row factory.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema Migration
# ---------------------------------------------------------------------------

PROPOSALS_DDL = """
CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT,
    solicitation_number TEXT,
    title TEXT NOT NULL,
    agency TEXT DEFAULT '',
    contracting_office TEXT DEFAULT '',
    naics_code TEXT DEFAULT '',
    naics_description TEXT DEFAULT '',
    set_aside_type TEXT DEFAULT 'unknown',
    contract_type TEXT DEFAULT 'other',
    estimated_value REAL DEFAULT 0.0,
    is_recompete INTEGER DEFAULT 0,
    incumbent TEXT DEFAULT '',
    source TEXT DEFAULT '',
    rfp_release_date TEXT,
    questions_due_date TEXT,
    proposal_due_date TEXT,
    award_date TEXT,
    period_of_performance TEXT DEFAULT '',
    pipeline_stage TEXT DEFAULT 'identified',
    bid_decision TEXT DEFAULT 'pending',
    bid_decision_date TEXT,
    bid_decision_rationale TEXT DEFAULT '',
    pwin_score REAL,
    capture_manager TEXT DEFAULT '',
    proposal_manager TEXT DEFAULT '',
    volume_leads TEXT DEFAULT '[]',
    team_members TEXT DEFAULT '[]',
    teaming_partners TEXT DEFAULT '[]',
    key_personnel TEXT DEFAULT '[]',
    relevant_past_performance TEXT DEFAULT '[]',
    color_teams TEXT DEFAULT '{}',
    submission_method TEXT DEFAULT '',
    crm_opportunity_id TEXT DEFAULT '',
    sharepoint_folder_url TEXT DEFAULT '',
    sharepoint_site_id TEXT DEFAULT '',
    confluence_space_key TEXT DEFAULT '',
    shred_analysis_id TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL
);
"""

PROPOSAL_MEETINGS_DDL = """
CREATE TABLE IF NOT EXISTS proposal_meetings (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    meeting_type TEXT DEFAULT 'other',
    title TEXT NOT NULL,
    scheduled_date TEXT,
    actual_date TEXT,
    attendees TEXT DEFAULT '[]',
    agenda TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    action_items TEXT DEFAULT '[]',
    confluence_page_id TEXT DEFAULT '',
    confluence_page_url TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
);
"""

HOTWASH_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS hotwash_events (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    facilitator TEXT DEFAULT '',
    event_date TEXT,
    attendees TEXT DEFAULT '[]',
    what_went_well TEXT DEFAULT '[]',
    what_to_improve TEXT DEFAULT '[]',
    lessons_learned TEXT DEFAULT '[]',
    action_items TEXT DEFAULT '[]',
    process_score INTEGER,
    debrief_requested INTEGER DEFAULT 0,
    debrief_notes TEXT DEFAULT '',
    confluence_page_id TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
);
"""

BID_NO_BID_DDL = """
CREATE TABLE IF NOT EXISTS bid_no_bid_assessments (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    assessor TEXT DEFAULT '',
    assessment_date TEXT NOT NULL,
    criteria TEXT DEFAULT '[]',
    win_themes TEXT DEFAULT '[]',
    discriminators TEXT DEFAULT '[]',
    risks TEXT DEFAULT '[]',
    mitigations TEXT DEFAULT '[]',
    weighted_score REAL,
    recommendation TEXT DEFAULT 'pending',
    recommendation_rationale TEXT DEFAULT '',
    final_decision TEXT DEFAULT 'pending',
    decision_made_by TEXT DEFAULT '',
    decision_date TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
);
"""

INDEXES_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_proposals_stage ON proposals(pipeline_stage)",
    "CREATE INDEX IF NOT EXISTS idx_proposals_due ON proposals(proposal_due_date)",
    "CREATE INDEX IF NOT EXISTS idx_proposals_solicitation ON proposals(solicitation_number)",
    "CREATE INDEX IF NOT EXISTS idx_meetings_proposal ON proposal_meetings(proposal_id, scheduled_date)",
    "CREATE INDEX IF NOT EXISTS idx_hotwash_proposal ON hotwash_events(proposal_id)",
    "CREATE INDEX IF NOT EXISTS idx_bnb_proposal ON bid_no_bid_assessments(proposal_id)",
]


def run_migration(db_path: Path = DEFAULT_DB_PATH) -> None:
    """
    Apply schema migrations (safe, additive-only).

    Args:
        db_path: Path to the SQLite database file.
    """
    with get_conn(db_path) as conn:
        conn.execute(PROPOSALS_DDL)
        conn.execute(PROPOSAL_MEETINGS_DDL)
        conn.execute(HOTWASH_EVENTS_DDL)
        conn.execute(BID_NO_BID_DDL)
        for idx_ddl in INDEXES_DDL:
            conn.execute(idx_ddl)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> str:
    """Serialize a Pydantic model or dict to JSON string."""
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump())
    return json.dumps(obj)


def _list_serial(items: List[Any]) -> str:
    """Serialize a list of Pydantic models or dicts to JSON string."""
    result = []
    for item in items:
        if hasattr(item, "model_dump"):
            result.append(item.model_dump())
        else:
            result.append(item)
    return json.dumps(result)


def _row_to_proposal(row: sqlite3.Row) -> Proposal:
    """
    Deserialize a SQLite row into a Proposal model.

    Args:
        row: SQLite Row object from proposals table.

    Returns:
        Proposal: Populated Proposal instance.
    """
    data = dict(row)
    # Deserialize JSON fields
    json_fields = [
        "volume_leads", "team_members", "teaming_partners",
        "key_personnel", "relevant_past_performance",
        "color_teams", "tags",
    ]
    for field in json_fields:
        if data.get(field):
            try:
                data[field] = json.loads(data[field])
            except (json.JSONDecodeError, TypeError):
                data[field] = [] if field != "color_teams" else {}

    data["is_recompete"] = bool(data.get("is_recompete", 0))
    return Proposal(**data)


def _row_to_meeting(row: sqlite3.Row) -> ProposalMeeting:
    """Deserialize a SQLite row into a ProposalMeeting model."""
    data = dict(row)
    for field in ["attendees", "action_items"]:
        if data.get(field):
            try:
                data[field] = json.loads(data[field])
            except (json.JSONDecodeError, TypeError):
                data[field] = []
    return ProposalMeeting(**data)


def _row_to_hotwash(row: sqlite3.Row) -> HotwashEvent:
    """Deserialize a SQLite row into a HotwashEvent model."""
    data = dict(row)
    for field in ["attendees", "what_went_well", "what_to_improve",
                  "lessons_learned", "action_items"]:
        if data.get(field):
            try:
                data[field] = json.loads(data[field])
            except (json.JSONDecodeError, TypeError):
                data[field] = []
    data["debrief_requested"] = bool(data.get("debrief_requested", 0))
    return HotwashEvent(**data)


# ---------------------------------------------------------------------------
# Proposal CRUD
# ---------------------------------------------------------------------------

def create_proposal(proposal: Proposal, db_path: Path = DEFAULT_DB_PATH) -> Proposal:
    """
    Persist a new proposal record.

    Args:
        proposal: Populated Proposal instance with a unique id.
        db_path: Path to the SQLite database file.

    Returns:
        Proposal: The saved proposal (unchanged).

    Raises:
        sqlite3.IntegrityError: If solicitation_number already exists.
    """
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO proposals (
                id, opportunity_id, solicitation_number, title, agency,
                contracting_office, naics_code, naics_description,
                set_aside_type, contract_type, estimated_value, is_recompete,
                incumbent, source, rfp_release_date, questions_due_date,
                proposal_due_date, award_date, period_of_performance,
                pipeline_stage, bid_decision, bid_decision_date,
                bid_decision_rationale, pwin_score, capture_manager,
                proposal_manager, volume_leads, team_members, teaming_partners,
                key_personnel, relevant_past_performance, color_teams,
                submission_method, crm_opportunity_id, sharepoint_folder_url,
                sharepoint_site_id, confluence_space_key, shred_analysis_id,
                notes, tags, created_at, updated_at
            ) VALUES (
                :id, :opportunity_id, :solicitation_number, :title, :agency,
                :contracting_office, :naics_code, :naics_description,
                :set_aside_type, :contract_type, :estimated_value, :is_recompete,
                :incumbent, :source, :rfp_release_date, :questions_due_date,
                :proposal_due_date, :award_date, :period_of_performance,
                :pipeline_stage, :bid_decision, :bid_decision_date,
                :bid_decision_rationale, :pwin_score, :capture_manager,
                :proposal_manager, :volume_leads, :team_members, :teaming_partners,
                :key_personnel, :relevant_past_performance, :color_teams,
                :submission_method, :crm_opportunity_id, :sharepoint_folder_url,
                :sharepoint_site_id, :confluence_space_key, :shred_analysis_id,
                :notes, :tags, :created_at, :updated_at
            )
        """, {
            **proposal.model_dump(),
            "set_aside_type": proposal.set_aside_type.value,
            "contract_type": proposal.contract_type.value,
            "pipeline_stage": proposal.pipeline_stage.value,
            "bid_decision": proposal.bid_decision.value,
            "is_recompete": int(proposal.is_recompete),
            "volume_leads": _list_serial(proposal.volume_leads),
            "team_members": _list_serial(proposal.team_members),
            "teaming_partners": _list_serial(proposal.teaming_partners),
            "key_personnel": _list_serial(proposal.key_personnel),
            "relevant_past_performance": _list_serial(proposal.relevant_past_performance),
            "color_teams": _serialize(proposal.color_teams),
            "tags": _list_serial(proposal.tags),
        })
    return proposal


def get_proposal(proposal_id: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[Proposal]:
    """
    Retrieve a proposal by ID.

    Args:
        proposal_id: The proposal UUID.
        db_path: Path to the SQLite database file.

    Returns:
        Proposal or None if not found.
    """
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
        ).fetchone()
    return _row_to_proposal(row) if row else None


def get_proposal_by_solicitation(
    solicitation_number: str, db_path: Path = DEFAULT_DB_PATH
) -> Optional[Proposal]:
    """
    Retrieve a proposal by solicitation number.

    Args:
        solicitation_number: Solicitation number (e.g., FA8612-26-R-0001).
        db_path: Path to the SQLite database file.

    Returns:
        Proposal or None if not found.
    """
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM proposals WHERE solicitation_number = ?",
            (solicitation_number,),
        ).fetchone()
    return _row_to_proposal(row) if row else None


def list_proposals(
    stage: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Proposal]:
    """
    List proposals, optionally filtered by pipeline stage.

    Args:
        stage: Optional PipelineStage value to filter by.
        db_path: Path to the SQLite database file.

    Returns:
        List[Proposal]: Ordered by proposal_due_date ascending.
    """
    with get_conn(db_path) as conn:
        if stage:
            rows = conn.execute(
                "SELECT * FROM proposals WHERE pipeline_stage = ? "
                "ORDER BY proposal_due_date ASC",
                (stage,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM proposals ORDER BY proposal_due_date ASC"
            ).fetchall()
    return [_row_to_proposal(r) for r in rows]


def update_proposal(
    proposal_id: str,
    updates: Dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Proposal]:
    """
    Patch specific fields of an existing proposal.

    Args:
        proposal_id: Proposal UUID to update.
        updates: Dict of field → new value pairs.
        db_path: Path to the SQLite database file.

    Returns:
        Updated Proposal or None if not found.
    """
    from datetime import datetime

    existing = get_proposal(proposal_id, db_path)
    if not existing:
        return None

    # Merge updates into the existing model then re-save changed fields
    updates["updated_at"] = datetime.now().isoformat()

    # JSON-encode any list/dict fields present in updates
    json_map = {
        "volume_leads": list,
        "team_members": list,
        "teaming_partners": list,
        "key_personnel": list,
        "relevant_past_performance": list,
        "tags": list,
        "color_teams": dict,
    }
    for field, _ in json_map.items():
        if field in updates:
            updates[field] = json.dumps(
                [i.model_dump() if hasattr(i, "model_dump") else i
                 for i in updates[field]]
                if isinstance(updates[field], list)
                else (updates[field].model_dump() if hasattr(updates[field], "model_dump")
                      else updates[field])
            )

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [proposal_id]

    with get_conn(db_path) as conn:
        conn.execute(
            f"UPDATE proposals SET {set_clause} WHERE id = ?", values
        )

    return get_proposal(proposal_id, db_path)


def delete_proposal(proposal_id: str, db_path: Path = DEFAULT_DB_PATH) -> bool:
    """
    Delete a proposal and all related records (cascade).

    Args:
        proposal_id: Proposal UUID to delete.
        db_path: Path to the SQLite database file.

    Returns:
        bool: True if deleted, False if not found.
    """
    with get_conn(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM proposals WHERE id = ?", (proposal_id,)
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Meeting CRUD
# ---------------------------------------------------------------------------

def create_meeting(
    meeting: ProposalMeeting, db_path: Path = DEFAULT_DB_PATH
) -> ProposalMeeting:
    """Persist a new proposal meeting."""
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO proposal_meetings (
                id, proposal_id, meeting_type, title, scheduled_date,
                actual_date, attendees, agenda, notes, action_items,
                confluence_page_id, confluence_page_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            meeting.id, meeting.proposal_id, meeting.meeting_type.value,
            meeting.title, meeting.scheduled_date, meeting.actual_date,
            _list_serial(meeting.attendees), meeting.agenda, meeting.notes,
            _list_serial(meeting.action_items), meeting.confluence_page_id,
            meeting.confluence_page_url, meeting.created_at, meeting.updated_at,
        ))
    return meeting


def list_meetings(
    proposal_id: str, db_path: Path = DEFAULT_DB_PATH
) -> List[ProposalMeeting]:
    """List all meetings for a proposal."""
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM proposal_meetings WHERE proposal_id = ? "
            "ORDER BY scheduled_date ASC",
            (proposal_id,),
        ).fetchall()
    return [_row_to_meeting(r) for r in rows]


def update_meeting(
    meeting_id: str, updates: Dict[str, Any], db_path: Path = DEFAULT_DB_PATH
) -> Optional[ProposalMeeting]:
    """Patch fields on an existing meeting."""
    from datetime import datetime
    updates["updated_at"] = datetime.now().isoformat()
    for field in ["attendees", "action_items"]:
        if field in updates:
            updates[field] = json.dumps(updates[field])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [meeting_id]
    with get_conn(db_path) as conn:
        conn.execute(
            f"UPDATE proposal_meetings SET {set_clause} WHERE id = ?", values
        )
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM proposal_meetings WHERE id = ?", (meeting_id,)
        ).fetchone()
    return _row_to_meeting(row) if row else None


# ---------------------------------------------------------------------------
# Hotwash CRUD
# ---------------------------------------------------------------------------

def create_hotwash(
    hotwash: HotwashEvent, db_path: Path = DEFAULT_DB_PATH
) -> HotwashEvent:
    """Persist a new hotwash event."""
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO hotwash_events (
                id, proposal_id, outcome, facilitator, event_date,
                attendees, what_went_well, what_to_improve, lessons_learned,
                action_items, process_score, debrief_requested, debrief_notes,
                confluence_page_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hotwash.id, hotwash.proposal_id, hotwash.outcome.value,
            hotwash.facilitator, hotwash.event_date,
            _list_serial(hotwash.attendees),
            _list_serial(hotwash.what_went_well),
            _list_serial(hotwash.what_to_improve),
            _list_serial(hotwash.lessons_learned),
            _list_serial(hotwash.action_items),
            hotwash.process_score, int(hotwash.debrief_requested),
            hotwash.debrief_notes, hotwash.confluence_page_id,
            hotwash.created_at,
        ))
    return hotwash


def get_hotwash(proposal_id: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[HotwashEvent]:
    """Get the hotwash event for a proposal."""
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM hotwash_events WHERE proposal_id = ?", (proposal_id,)
        ).fetchone()
    return _row_to_hotwash(row) if row else None


# ---------------------------------------------------------------------------
# Bid/No-Bid CRUD
# ---------------------------------------------------------------------------

def save_bid_no_bid(
    assessment: BidNoBidAssessment, db_path: Path = DEFAULT_DB_PATH
) -> BidNoBidAssessment:
    """Persist or replace a B/NB assessment for a proposal."""
    with get_conn(db_path) as conn:
        conn.execute(
            "DELETE FROM bid_no_bid_assessments WHERE proposal_id = ?",
            (assessment.proposal_id,),
        )
        conn.execute("""
            INSERT INTO bid_no_bid_assessments (
                id, proposal_id, assessor, assessment_date,
                criteria, win_themes, discriminators, risks, mitigations,
                weighted_score, recommendation, recommendation_rationale,
                final_decision, decision_made_by, decision_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"bnb_{assessment.proposal_id}", assessment.proposal_id,
            assessment.assessor, assessment.assessment_date,
            _list_serial(assessment.criteria),
            _list_serial(assessment.win_themes),
            _list_serial(assessment.discriminators),
            _list_serial(assessment.risks),
            _list_serial(assessment.mitigations),
            assessment.weighted_score(),
            assessment.recommendation.value,
            assessment.recommendation_rationale,
            assessment.final_decision.value,
            assessment.decision_made_by,
            assessment.decision_date,
            assessment.assessment_date,
        ))
    return assessment


def get_bid_no_bid(
    proposal_id: str, db_path: Path = DEFAULT_DB_PATH
) -> Optional[BidNoBidAssessment]:
    """Retrieve the B/NB assessment for a proposal."""
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM bid_no_bid_assessments WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    for field in ["criteria", "win_themes", "discriminators", "risks", "mitigations"]:
        if data.get(field):
            try:
                data[field] = json.loads(data[field])
            except (json.JSONDecodeError, TypeError):
                data[field] = []
    return BidNoBidAssessment(**data)
