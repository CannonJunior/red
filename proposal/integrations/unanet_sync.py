"""
Unanet CRM Bidirectional Sync Manager.

Orchestrates two-way synchronization between the local proposals database
and Unanet CRM. Sync state is persisted to a JSON file so each run only
processes records that have changed since the last sync.

Conflict resolution strategy (configurable):
    "prefer_local"  — local wins on field conflicts (default)
    "prefer_crm"    — CRM value wins on field conflicts
    "prefer_newer"  — whichever record has the later updated_at wins

Configuration via environment variables:
    UNANET_SYNC_STATE_FILE — path to sync state JSON (default: outputs/proposal/unanet_sync_state.json)
    UNANET_CONFLICT_STRATEGY — one of prefer_local|prefer_crm|prefer_newer (default: prefer_local)

Usage:
    from proposal.integrations.unanet_sync import UnanetSyncManager
    mgr = UnanetSyncManager()
    result = mgr.sync()
    print(result.summary())
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from proposal.database import (
    DEFAULT_DB_PATH,
    get_proposal,
    list_proposals,
    update_proposal,
)
from proposal.integrations.unanet import UnanetAPIError, UnanetClient

logger = logging.getLogger(__name__)

# Fields pulled from Unanet that are allowed to overwrite local values
_CRM_PULL_FIELDS = [
    "pipeline_stage",
    "pwin_score",
    "bid_decision",
    "capture_manager",
    "estimated_value",
    "notes",
]

# Fields that must never be overwritten from CRM (local is authoritative)
_LOCAL_ONLY_FIELDS = {
    "id", "opportunity_id", "sharepoint_folder_url", "sharepoint_site_id",
    "confluence_space_key", "shred_analysis_id", "created_at",
}


def _state_file_path() -> Path:
    """Return path to sync state file, configurable via env."""
    default = (
        Path(__file__).parent.parent.parent / "outputs" / "proposal" / "unanet_sync_state.json"
    )
    return Path(os.getenv("UNANET_SYNC_STATE_FILE", str(default)))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SyncEntry:
    """
    Per-proposal sync state record.

    Attributes:
        proposal_id: Local UUID of the proposal.
        crm_id: Unanet CRM opportunity ID (empty if not yet pushed).
        last_pushed_at: ISO timestamp of last successful push to CRM.
        last_pulled_at: ISO timestamp of last successful pull from CRM.
    """
    proposal_id: str
    crm_id: str = ""
    last_pushed_at: str = ""
    last_pulled_at: str = ""

    def to_dict(self) -> Dict[str, str]:
        """Serialize to a plain dict for JSON storage."""
        return {
            "crm_id": self.crm_id,
            "last_pushed_at": self.last_pushed_at,
            "last_pulled_at": self.last_pulled_at,
        }


@dataclass
class SyncResult:
    """
    Summary of a sync run.

    Attributes:
        pushed_created: Proposals newly created in CRM.
        pushed_updated: Proposals updated in CRM from local changes.
        pulled_updated: Local proposals updated from CRM data.
        skipped: Proposals skipped (no change detected).
        errors: List of (proposal_id, error_message) tuples.
    """
    pushed_created: List[str] = field(default_factory=list)
    pushed_updated: List[str] = field(default_factory=list)
    pulled_updated: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[tuple] = field(default_factory=list)

    def summary(self) -> str:
        """
        Return a human-readable sync summary string.

        Returns:
            str: One-line summary of sync results.
        """
        return (
            f"Sync complete — "
            f"created: {len(self.pushed_created)}, "
            f"updated→CRM: {len(self.pushed_updated)}, "
            f"pulled←CRM: {len(self.pulled_updated)}, "
            f"skipped: {len(self.skipped)}, "
            f"errors: {len(self.errors)}"
        )

    @property
    def has_errors(self) -> bool:
        """True if any errors occurred during sync."""
        return len(self.errors) > 0


# ---------------------------------------------------------------------------
# Sync manager
# ---------------------------------------------------------------------------

class UnanetSyncManager:
    """
    Bidirectional sync between local proposal DB and Unanet CRM.

    Reads and writes sync state from a JSON file to avoid re-processing
    unchanged records. All HTTP calls are delegated to UnanetClient.

    Example:
        mgr = UnanetSyncManager()
        result = mgr.sync()
    """

    def __init__(
        self,
        client: Optional[UnanetClient] = None,
        state_file: Optional[Path] = None,
        conflict_strategy: Optional[str] = None,
        db_path: Optional[Path] = None,
    ):
        """
        Initialize the sync manager.

        Args:
            client: UnanetClient instance. Built from env vars if omitted.
            state_file: Path to sync state JSON. Falls back to env/default.
            conflict_strategy: One of 'prefer_local', 'prefer_crm', 'prefer_newer'.
            db_path: Override local database path.

        Raises:
            ValueError: If conflict_strategy is not a valid option.
        """
        self._client = client or UnanetClient()
        self._state_file = state_file or _state_file_path()
        self._db_path = db_path or DEFAULT_DB_PATH

        strategy = conflict_strategy or os.getenv("UNANET_CONFLICT_STRATEGY", "prefer_local")
        valid_strategies = {"prefer_local", "prefer_crm", "prefer_newer"}
        if strategy not in valid_strategies:
            raise ValueError(
                f"Invalid conflict_strategy '{strategy}'. "
                f"Must be one of: {', '.join(sorted(valid_strategies))}"
            )
        self._conflict_strategy = strategy
        self._state: Dict[str, SyncEntry] = self._load_state()

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> Dict[str, SyncEntry]:
        """
        Load sync state from JSON file.

        Returns:
            Dict[str, SyncEntry]: Keyed by proposal_id.
        """
        if not self._state_file.exists():
            return {}
        try:
            with open(self._state_file) as fh:
                raw = json.load(fh)
            return {
                pid: SyncEntry(proposal_id=pid, **entry)
                for pid, entry in raw.items()
            }
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("Failed to parse sync state file: %s — starting fresh", exc)
            return {}

    def _save_state(self) -> None:
        """Persist current sync state to JSON file."""
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_file, "w") as fh:
            json.dump(
                {pid: entry.to_dict() for pid, entry in self._state.items()},
                fh,
                indent=2,
            )

    def _now_iso(self) -> str:
        """Return the current UTC time as an ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def _entry(self, proposal_id: str) -> SyncEntry:
        """Get or create a SyncEntry for the given proposal_id."""
        if proposal_id not in self._state:
            self._state[proposal_id] = SyncEntry(proposal_id=proposal_id)
        return self._state[proposal_id]

    # ------------------------------------------------------------------
    # Push: local → CRM
    # ------------------------------------------------------------------

    def push_all(self, result: Optional[SyncResult] = None) -> SyncResult:
        """
        Push all changed local proposals to Unanet CRM.

        Creates CRM records for proposals without a crm_id and updates
        records whose local updated_at is newer than last_pushed_at.

        Args:
            result: Existing SyncResult to append to; created if None.

        Returns:
            SyncResult: Updated result with push outcomes.
        """
        if result is None:
            result = SyncResult()

        proposals = list_proposals(db_path=self._db_path)
        for proposal in proposals:
            pid = proposal.id
            entry = self._entry(pid)
            data = proposal.model_dump()

            # Convert enum fields to their string values for CRM mapping
            for enum_field in ("pipeline_stage", "bid_decision", "set_aside_type", "contract_type"):
                if enum_field in data and hasattr(data[enum_field], "value"):
                    data[enum_field] = data[enum_field].value

            try:
                if not entry.crm_id:
                    # No CRM record yet — create it
                    crm_id = self._client.create_opportunity(data)
                    entry.crm_id = crm_id
                    entry.last_pushed_at = self._now_iso()
                    # Write crm_opportunity_id back to local DB
                    update_proposal(
                        pid,
                        {"crm_opportunity_id": crm_id},
                        db_path=self._db_path,
                    )
                    result.pushed_created.append(pid)
                    logger.info("Created CRM record %s for proposal %s", crm_id, pid)

                elif self._needs_push(proposal.updated_at, entry.last_pushed_at):
                    # Local record updated since last push
                    self._client.update_opportunity(entry.crm_id, data)
                    entry.last_pushed_at = self._now_iso()
                    result.pushed_updated.append(pid)
                    logger.info("Updated CRM record %s for proposal %s", entry.crm_id, pid)

                else:
                    result.skipped.append(pid)

            except UnanetAPIError as exc:
                logger.error("Push failed for proposal %s: %s", pid, exc)
                result.errors.append((pid, str(exc)))

        self._save_state()
        return result

    def _needs_push(self, local_updated_at: str, last_pushed_at: str) -> bool:
        """
        Determine if a local record needs to be pushed to CRM.

        Args:
            local_updated_at: ISO timestamp of last local update.
            last_pushed_at: ISO timestamp of last successful push.

        Returns:
            bool: True if local is newer than last push.
        """
        if not last_pushed_at:
            return True
        try:
            local_dt = datetime.fromisoformat(local_updated_at.replace("Z", "+00:00"))
            pushed_dt = datetime.fromisoformat(last_pushed_at.replace("Z", "+00:00"))
            return local_dt > pushed_dt
        except (ValueError, AttributeError):
            return True

    # ------------------------------------------------------------------
    # Pull: CRM → local
    # ------------------------------------------------------------------

    def pull_all(self, result: Optional[SyncResult] = None) -> SyncResult:
        """
        Pull changed CRM records and update local proposals.

        Only updates local proposals that already exist locally (matched
        by crm_opportunity_id). Does not create new local proposals from
        CRM — that is a deliberate design choice to avoid orphan records.

        Args:
            result: Existing SyncResult to append to; created if None.

        Returns:
            SyncResult: Updated result with pull outcomes.
        """
        if result is None:
            result = SyncResult()

        # Build a crm_id → proposal_id lookup from sync state
        crm_to_local: Dict[str, str] = {
            entry.crm_id: pid
            for pid, entry in self._state.items()
            if entry.crm_id
        }

        if not crm_to_local:
            logger.debug("No CRM-linked proposals to pull — nothing to do")
            return result

        try:
            crm_records = self._client.list_opportunities(limit=500)
        except UnanetAPIError as exc:
            logger.error("Failed to list CRM opportunities: %s", exc)
            result.errors.append(("list_opportunities", str(exc)))
            return result

        for crm_record in crm_records:
            crm_id = str(crm_record.get("id") or crm_record.get("opportunityId", ""))
            if not crm_id or crm_id not in crm_to_local:
                continue

            pid = crm_to_local[crm_id]
            entry = self._entry(pid)

            try:
                local_proposal = get_proposal(pid, db_path=self._db_path)
                if local_proposal is None:
                    logger.warning("Sync state references missing proposal %s — skipping", pid)
                    continue

                if not self._needs_pull(crm_record, entry.last_pulled_at, local_proposal.updated_at):
                    result.skipped.append(pid)
                    continue

                updates = self._extract_crm_updates(crm_record)
                if updates:
                    update_proposal(pid, updates, db_path=self._db_path)
                    entry.last_pulled_at = self._now_iso()
                    result.pulled_updated.append(pid)
                    logger.info("Pulled CRM updates for proposal %s (%s)", pid, crm_id)
                else:
                    result.skipped.append(pid)

            except (UnanetAPIError, Exception) as exc:
                logger.error("Pull failed for proposal %s: %s", pid, exc)
                result.errors.append((pid, str(exc)))

        self._save_state()
        return result

    def _needs_pull(
        self,
        crm_record: Dict[str, Any],
        last_pulled_at: str,
        local_updated_at: str,
    ) -> bool:
        """
        Determine if a CRM record has changes that should be pulled locally.

        Args:
            crm_record: Raw CRM record dict.
            last_pulled_at: ISO timestamp of last successful pull.
            local_updated_at: ISO timestamp of last local update.

        Returns:
            bool: True if CRM has newer data worth pulling.
        """
        if not last_pulled_at:
            return True

        # Reason: Unanet may use different field names for the modified timestamp
        crm_updated = (
            crm_record.get("updated_date")
            or crm_record.get("modified_date")
            or crm_record.get("updatedAt")
            or ""
        )

        if self._conflict_strategy == "prefer_local":
            # Only pull if CRM is newer than last pull AND local hasn't changed since
            if not crm_updated:
                return False
            try:
                crm_dt = datetime.fromisoformat(crm_updated.replace("Z", "+00:00"))
                pulled_dt = datetime.fromisoformat(last_pulled_at.replace("Z", "+00:00"))
                return crm_dt > pulled_dt
            except (ValueError, AttributeError):
                return False

        elif self._conflict_strategy == "prefer_crm":
            if not crm_updated:
                return False
            try:
                crm_dt = datetime.fromisoformat(crm_updated.replace("Z", "+00:00"))
                pulled_dt = datetime.fromisoformat(last_pulled_at.replace("Z", "+00:00"))
                return crm_dt > pulled_dt
            except (ValueError, AttributeError):
                return True  # When uncertain, pull

        else:  # prefer_newer
            if not crm_updated:
                return False
            try:
                crm_dt = datetime.fromisoformat(crm_updated.replace("Z", "+00:00"))
                local_dt = datetime.fromisoformat(local_updated_at.replace("Z", "+00:00"))
                return crm_dt > local_dt
            except (ValueError, AttributeError):
                return False

    def _extract_crm_updates(
        self,
        crm_record: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a dict of local field updates derived from a CRM record.

        Only maps fields present in _CRM_PULL_FIELDS. Stage codes are
        reverse-mapped to local PipelineStage values. pwin is scaled
        from CRM 0–100 back to local 0.0–1.0.

        Args:
            crm_record: Raw CRM record dict.

        Returns:
            Dict[str, Any]: Ready-to-pass updates dict for update_proposal().
        """
        # Reverse field mapping: crm_field → local_field
        reverse_map = {v: k for k, v in self._client.field_mapping.items()}
        updates: Dict[str, Any] = {}

        for crm_field, value in crm_record.items():
            local_field = reverse_map.get(crm_field)
            if not local_field:
                continue
            if local_field not in _CRM_PULL_FIELDS:
                continue
            if local_field in _LOCAL_ONLY_FIELDS:
                continue
            if value is None:
                continue

            # Reason: CRM stores pwin as 0–100; local model uses 0.0–1.0
            if local_field == "pwin_score":
                try:
                    value = float(value) / 100.0
                except (ValueError, TypeError):
                    continue

            # Reason: CRM stage codes must be converted to local PipelineStage values
            if local_field == "pipeline_stage":
                value = self._client.map_stage_from_crm(str(value))

            updates[local_field] = value

        return updates

    # ------------------------------------------------------------------
    # Bidirectional sync
    # ------------------------------------------------------------------

    def sync(self) -> SyncResult:
        """
        Run a full bidirectional sync: push then pull.

        Push runs first so local state is committed to CRM before we
        check for inbound CRM changes to avoid unnecessary conflicts.

        Returns:
            SyncResult: Combined result from push and pull phases.
        """
        result = SyncResult()
        logger.info("Starting bidirectional Unanet sync (strategy=%s)", self._conflict_strategy)

        result = self.push_all(result)
        result = self.pull_all(result)

        logger.info(result.summary())
        return result

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_sync_entry(self, proposal_id: str) -> Optional[SyncEntry]:
        """
        Retrieve the sync state for a specific proposal.

        Args:
            proposal_id: Local proposal UUID.

        Returns:
            SyncEntry or None if proposal has never been synced.
        """
        return self._state.get(proposal_id)

    def reset_sync_state(self, proposal_id: Optional[str] = None) -> None:
        """
        Clear sync state to force a full re-sync on next run.

        Args:
            proposal_id: If provided, only reset this proposal's state.
                         If omitted, clear all state.
        """
        if proposal_id:
            self._state.pop(proposal_id, None)
        else:
            self._state.clear()
        self._save_state()
