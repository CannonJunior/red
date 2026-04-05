"""Proposal, Bid-No-Bid, and Hotwash list tracking data layer.

Tables (in search_system.db alongside capture tables):
  proposal_items  — one row per opportunity that enters 04-In Progress
  bnb_items       — one row per opportunity that enters 03-Bid Decision
  hotwash_items   — one row per opportunity that enters 06/07/08/09 stages

All tables are auto-populated by the opportunity stage-change trigger
in server/routes/opportunities.py, and are also directly writable via
the tracking HTTP API.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

try:
    from server.db_pool import get_db as _get_db
    _USE_POOL = True
except ImportError:
    _USE_POOL = False

_DEFAULT_DB = "search_system.db"


class TrackingManager:
    """CRUD manager for proposal_items and bnb_items tracking tables."""

    def __init__(self, db_path: str = _DEFAULT_DB):
        self.db_path = db_path
        self._init_database()

    # -------------------------------------------------------------------------
    # Connection
    # -------------------------------------------------------------------------

    def _connect(self):
        if _USE_POOL:
            return _get_db(self.db_path)

        @contextmanager
        def _plain():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        return _plain()

    def _init_database(self):
        """Create proposal_items, bnb_items, and hotwash_items tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS proposal_items (
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL UNIQUE,
                opportunity_name TEXT NOT NULL,
                created_date TEXT,
                goldenrod_date TEXT,
                submission_date TEXT,
                proposal_price REAL,
                contract_type TEXT,
                agreement_type TEXT,
                submitted INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_proposal_items_opp
                ON proposal_items(opportunity_id);

            CREATE TABLE IF NOT EXISTS bnb_items (
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL UNIQUE,
                opportunity_name TEXT NOT NULL,
                decision TEXT DEFAULT 'pending',
                rationale TEXT,
                score REAL,
                decision_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bnb_items_opp
                ON bnb_items(opportunity_id);

            CREATE TABLE IF NOT EXISTS hotwash_items (
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL UNIQUE,
                opportunity_name TEXT NOT NULL,
                trigger_stage TEXT,
                conducted_date TEXT,
                participants TEXT,
                outcome_summary TEXT,
                lessons_learned TEXT,
                action_items TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_hotwash_items_opp
                ON hotwash_items(opportunity_id);
        """)
        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # Proposal Items
    # -------------------------------------------------------------------------

    def list_proposal_items(self) -> Dict:
        """Return all proposal list items ordered by created_at desc."""
        try:
            with self._connect() as conn:
                rows = conn.cursor().execute(
                    "SELECT * FROM proposal_items ORDER BY created_at DESC"
                ).fetchall()
            return {'status': 'success', 'items': [self._pld(r) for r in rows]}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_proposal_item(self, data: Dict) -> Dict:
        """Create a proposal list item (manual creation)."""
        try:
            pid, now = str(uuid.uuid4()), datetime.now().isoformat()
            opp_id = data.get('opportunity_id', '')
            with self._connect() as conn:
                conn.cursor().execute(
                    """INSERT INTO proposal_items
                       (id, opportunity_id, opportunity_name, created_date,
                        goldenrod_date, submission_date, proposal_price,
                        contract_type, agreement_type, submitted, notes,
                        created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pid, opp_id, data.get('opportunity_name', ''),
                     data.get('created_date', now[:10]),
                     data.get('goldenrod_date', ''),
                     data.get('submission_date', ''),
                     data.get('proposal_price'),
                     data.get('contract_type', ''),
                     data.get('agreement_type', ''),
                     int(data.get('submitted', False)),
                     data.get('notes', ''),
                     now, now))
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM proposal_items WHERE id=?", (pid,)
                ).fetchone()
            return {'status': 'success', 'item': self._pld(row)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_proposal_item(self, item_id: str, data: Dict) -> Dict:
        """Update fields on a proposal list item."""
        try:
            now = datetime.now().isoformat()
            sets, vals = [], []
            for f in ['opportunity_name', 'created_date', 'goldenrod_date',
                      'submission_date', 'proposal_price', 'contract_type',
                      'agreement_type', 'notes']:
                if f in data:
                    sets.append(f"{f}=?")
                    vals.append(data[f])
            if 'submitted' in data:
                sets.append("submitted=?")
                vals.append(int(data['submitted']))
            sets.append("updated_at=?")
            vals.extend([now, item_id])
            with self._connect() as conn:
                conn.cursor().execute(
                    f"UPDATE proposal_items SET {','.join(sets)} WHERE id=?", vals)
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM proposal_items WHERE id=?", (item_id,)
                ).fetchone()
            return {'status': 'success', 'item': self._pld(row) if row else None}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_proposal_item(self, item_id: str) -> Dict:
        """Delete a proposal list item."""
        try:
            with self._connect() as conn:
                conn.cursor().execute(
                    "DELETE FROM proposal_items WHERE id=?", (item_id,))
                conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def ensure_proposal_item(self, opportunity_id: str, opportunity_name: str) -> Dict:
        """Create a proposal item for this opportunity if one doesn't exist yet."""
        try:
            with self._connect() as conn:
                exists = conn.cursor().execute(
                    "SELECT id FROM proposal_items WHERE opportunity_id=?",
                    (opportunity_id,)).fetchone()
            if exists:
                return {'status': 'exists'}
            return self.create_proposal_item({
                'opportunity_id': opportunity_id,
                'opportunity_name': opportunity_name,
                'created_date': datetime.now().date().isoformat(),
            })
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _pld(self, r) -> Dict:
        return {
            'id': r['id'],
            'opportunity_id': r['opportunity_id'],
            'opportunity_name': r['opportunity_name'] or '',
            'created_date': r['created_date'] or '',
            'goldenrod_date': r['goldenrod_date'] or '',
            'submission_date': r['submission_date'] or '',
            'proposal_price': r['proposal_price'],
            'contract_type': r['contract_type'] or '',
            'agreement_type': r['agreement_type'] or '',
            'submitted': bool(r['submitted']),
            'notes': r['notes'] or '',
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
        }

    # -------------------------------------------------------------------------
    # BNB Items
    # -------------------------------------------------------------------------

    def list_bnb_items(self) -> Dict:
        """Return all BNB list items ordered by created_at desc."""
        try:
            with self._connect() as conn:
                rows = conn.cursor().execute(
                    "SELECT * FROM bnb_items ORDER BY created_at DESC"
                ).fetchall()
            return {'status': 'success', 'items': [self._bnbd(r) for r in rows]}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_bnb_item(self, data: Dict) -> Dict:
        """Create a BNB list item (manual creation)."""
        try:
            bid, now = str(uuid.uuid4()), datetime.now().isoformat()
            opp_id = data.get('opportunity_id', '')
            with self._connect() as conn:
                conn.cursor().execute(
                    """INSERT INTO bnb_items
                       (id, opportunity_id, opportunity_name, decision,
                        rationale, score, decision_date, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (bid, opp_id, data.get('opportunity_name', ''),
                     data.get('decision', 'pending'),
                     data.get('rationale', ''),
                     data.get('score'),
                     data.get('decision_date', ''),
                     now, now))
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM bnb_items WHERE id=?", (bid,)
                ).fetchone()
            return {'status': 'success', 'item': self._bnbd(row)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_bnb_item(self, item_id: str, data: Dict) -> Dict:
        """Update fields on a BNB list item."""
        try:
            now = datetime.now().isoformat()
            sets, vals = [], []
            for f in ['opportunity_name', 'decision', 'rationale', 'score', 'decision_date']:
                if f in data:
                    sets.append(f"{f}=?")
                    vals.append(data[f])
            sets.append("updated_at=?")
            vals.extend([now, item_id])
            with self._connect() as conn:
                conn.cursor().execute(
                    f"UPDATE bnb_items SET {','.join(sets)} WHERE id=?", vals)
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM bnb_items WHERE id=?", (item_id,)
                ).fetchone()
            return {'status': 'success', 'item': self._bnbd(row) if row else None}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_bnb_item(self, item_id: str) -> Dict:
        """Delete a BNB list item."""
        try:
            with self._connect() as conn:
                conn.cursor().execute(
                    "DELETE FROM bnb_items WHERE id=?", (item_id,))
                conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def ensure_bnb_item(self, opportunity_id: str, opportunity_name: str) -> Dict:
        """Create a BNB item for this opportunity if one doesn't exist yet."""
        try:
            with self._connect() as conn:
                exists = conn.cursor().execute(
                    "SELECT id FROM bnb_items WHERE opportunity_id=?",
                    (opportunity_id,)).fetchone()
            if exists:
                return {'status': 'exists'}
            return self.create_bnb_item({
                'opportunity_id': opportunity_id,
                'opportunity_name': opportunity_name,
            })
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _bnbd(self, r) -> Dict:
        return {
            'id': r['id'],
            'opportunity_id': r['opportunity_id'],
            'opportunity_name': r['opportunity_name'] or '',
            'decision': r['decision'] or 'pending',
            'rationale': r['rationale'] or '',
            'score': r['score'],
            'decision_date': r['decision_date'] or '',
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
        }


    # -------------------------------------------------------------------------
    # Hotwash Items
    # -------------------------------------------------------------------------

    def list_hotwash_items(self) -> Dict:
        """Return all hotwash items ordered by created_at desc."""
        try:
            with self._connect() as conn:
                rows = conn.cursor().execute(
                    "SELECT * FROM hotwash_items ORDER BY created_at DESC"
                ).fetchall()
            return {'status': 'success', 'items': [self._hwd(r) for r in rows]}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_hotwash_item(self, data: Dict) -> Dict:
        """Create a hotwash item (manual or auto-triggered)."""
        try:
            hid, now = str(uuid.uuid4()), datetime.now().isoformat()
            opp_id = data.get('opportunity_id', '')
            with self._connect() as conn:
                conn.cursor().execute(
                    """INSERT INTO hotwash_items
                       (id, opportunity_id, opportunity_name, trigger_stage,
                        conducted_date, participants, outcome_summary,
                        lessons_learned, action_items, notes,
                        created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (hid, opp_id, data.get('opportunity_name', ''),
                     data.get('trigger_stage', ''),
                     data.get('conducted_date', ''),
                     data.get('participants', ''),
                     data.get('outcome_summary', ''),
                     data.get('lessons_learned', ''),
                     data.get('action_items', ''),
                     data.get('notes', ''),
                     now, now))
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM hotwash_items WHERE id=?", (hid,)
                ).fetchone()
            return {'status': 'success', 'item': self._hwd(row)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_hotwash_item(self, item_id: str, data: Dict) -> Dict:
        """Update fields on a hotwash item."""
        try:
            now = datetime.now().isoformat()
            sets, vals = [], []
            for f in ['opportunity_name', 'trigger_stage', 'conducted_date',
                      'participants', 'outcome_summary', 'lessons_learned',
                      'action_items', 'notes']:
                if f in data:
                    sets.append(f"{f}=?")
                    vals.append(data[f])
            sets.append("updated_at=?")
            vals.extend([now, item_id])
            with self._connect() as conn:
                conn.cursor().execute(
                    f"UPDATE hotwash_items SET {','.join(sets)} WHERE id=?", vals)
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM hotwash_items WHERE id=?", (item_id,)
                ).fetchone()
            return {'status': 'success', 'item': self._hwd(row) if row else None}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_hotwash_item(self, item_id: str) -> Dict:
        """Delete a hotwash item."""
        try:
            with self._connect() as conn:
                conn.cursor().execute(
                    "DELETE FROM hotwash_items WHERE id=?", (item_id,))
                conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def ensure_hotwash_item(self, opportunity_id: str, opportunity_name: str,
                             trigger_stage: str = '') -> Dict:
        """Create a hotwash item for this opportunity if one doesn't exist yet."""
        try:
            with self._connect() as conn:
                exists = conn.cursor().execute(
                    "SELECT id FROM hotwash_items WHERE opportunity_id=?",
                    (opportunity_id,)).fetchone()
            if exists:
                return {'status': 'exists'}
            return self.create_hotwash_item({
                'opportunity_id': opportunity_id,
                'opportunity_name': opportunity_name,
                'trigger_stage': trigger_stage,
            })
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _hwd(self, r) -> Dict:
        """Serialize a hotwash_items row."""
        return {
            'id': r['id'],
            'opportunity_id': r['opportunity_id'],
            'opportunity_name': r['opportunity_name'] or '',
            'trigger_stage': r['trigger_stage'] or '',
            'conducted_date': r['conducted_date'] or '',
            'participants': r['participants'] or '',
            'outcome_summary': r['outcome_summary'] or '',
            'lessons_learned': r['lessons_learned'] or '',
            'action_items': r['action_items'] or '',
            'notes': r['notes'] or '',
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
        }


# -------------------------------------------------------------------------
# Global singleton
# -------------------------------------------------------------------------

_tracking_manager: Optional[TrackingManager] = None


def get_tracking_manager() -> TrackingManager:
    """Get or create the global TrackingManager singleton."""
    global _tracking_manager
    if _tracking_manager is None:
        _tracking_manager = TrackingManager()
    return _tracking_manager
