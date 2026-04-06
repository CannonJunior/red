"""Shipley Capture Process intelligence data layer.

Manages customer contacts, competitive intel, engagement activities,
win strategy, and price-to-win analysis per opportunity.
"""
import sqlite3
import uuid
import json
from datetime import datetime
from typing import Dict, Optional

try:
    from server.db_pool import get_db as _get_db
    _USE_POOL = True
except ImportError:
    _USE_POOL = False

from config.database import DEFAULT_DB


class CaptureManager:
    """CRUD manager for Shipley capture intelligence tables."""

    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        self._init_database()

    def _connect(self):
        if _USE_POOL:
            return _get_db(self.db_path)
        from contextlib import contextmanager

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
        """Create all capture tables and indexes."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS customer_contacts (
                id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL,
                name TEXT NOT NULL, title TEXT, org TEXT,
                role TEXT DEFAULT 'Influencer', hot_buttons TEXT,
                relationship_strength INTEGER DEFAULT 3,
                last_contact_date TEXT, notes TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_contacts_opp ON customer_contacts(opportunity_id);
            CREATE TABLE IF NOT EXISTS competitor_intel (
                id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL,
                company_name TEXT NOT NULL,
                is_incumbent INTEGER DEFAULT 0, likely_bid TEXT DEFAULT 'Maybe',
                strengths TEXT, weaknesses TEXT, likely_approach TEXT,
                estimated_price REAL, notes TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_competitor_opp ON competitor_intel(opportunity_id);
            CREATE TABLE IF NOT EXISTS engagement_activities (
                id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL,
                activity_date TEXT NOT NULL, activity_type TEXT DEFAULT 'Meeting',
                customer_attendees TEXT, our_attendees TEXT,
                topics_covered TEXT, intelligence_gathered TEXT,
                action_items TEXT, follow_up_required INTEGER DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_activity_opp
                ON engagement_activities(opportunity_id, activity_date);


            CREATE TABLE IF NOT EXISTS win_strategy (
                opportunity_id TEXT PRIMARY KEY,
                pwin_score REAL DEFAULT 0.0,
                win_themes TEXT, discriminators TEXT, ghosts TEXT,
                customer_hot_buttons_summary TEXT,
                gate_0_complete INTEGER DEFAULT 0, gate_1_complete INTEGER DEFAULT 0,
                gate_2_complete INTEGER DEFAULT 0, gate_3_complete INTEGER DEFAULT 0,
                gate_4_complete INTEGER DEFAULT 0, gate_5_complete INTEGER DEFAULT 0,
                gate_0_date TEXT, gate_1_date TEXT, gate_2_date TEXT,
                gate_3_date TEXT, gate_4_date TEXT, gate_5_date TEXT,
                notes TEXT, updated_at TEXT NOT NULL,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ptw_analysis (
                opportunity_id TEXT PRIMARY KEY,
                ptw_target REAL, our_estimated_cost REAL,
                fee_percent REAL DEFAULT 0.08, unanet_project_id TEXT,
                competitor_price_low REAL, competitor_price_high REAL,
                pricing_notes TEXT, updated_at TEXT NOT NULL,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        conn.close()

    # --- Customer Contacts ---
    def list_contacts(self, opportunity_id: str) -> Dict:
        """List all contacts for an opportunity."""
        try:
            with self._connect() as conn:
                rows = conn.cursor().execute(
                    "SELECT * FROM customer_contacts WHERE opportunity_id=? ORDER BY name",
                    (opportunity_id,)).fetchall()
            return {'status': 'success', 'contacts': [self._cd(r) for r in rows]}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_contact(self, opportunity_id: str, data: Dict) -> Dict:
        """Create a customer contact."""
        try:
            cid, now = str(uuid.uuid4()), datetime.now().isoformat()
            with self._connect() as conn:
                conn.cursor().execute("""
                    INSERT INTO customer_contacts
                    (id,opportunity_id,name,title,org,role,hot_buttons,
                     relationship_strength,last_contact_date,notes,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (cid, opportunity_id, data.get('name', 'Unknown'),
                     data.get('title', ''), data.get('org', ''),
                     data.get('role', 'Influencer'),
                     json.dumps(data.get('hot_buttons', [])),
                     int(data.get('relationship_strength', 3)),
                     data.get('last_contact_date', ''), data.get('notes', ''),
                     now, now))
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM customer_contacts WHERE id=?", (cid,)).fetchone()
            return {'status': 'success', 'contact': self._cd(row)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_contact(self, contact_id: str, data: Dict) -> Dict:
        """Update a customer contact."""
        try:
            now = datetime.now().isoformat()
            sets, vals = [], []
            for f in ['name', 'title', 'org', 'role', 'relationship_strength',
                      'last_contact_date', 'notes']:
                if f in data:
                    sets.append(f"{f}=?")
                    vals.append(data[f])
            if 'hot_buttons' in data:
                sets.append("hot_buttons=?")
                vals.append(json.dumps(data['hot_buttons']))
            sets.append("updated_at=?")
            vals.extend([now, contact_id])
            with self._connect() as conn:
                conn.cursor().execute(
                    f"UPDATE customer_contacts SET {','.join(sets)} WHERE id=?", vals)
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM customer_contacts WHERE id=?", (contact_id,)).fetchone()
            return {'status': 'success', 'contact': self._cd(row) if row else None}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_contact(self, contact_id: str) -> Dict:
        """Delete a customer contact."""
        try:
            with self._connect() as conn:
                conn.cursor().execute(
                    "DELETE FROM customer_contacts WHERE id=?", (contact_id,))
                conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    def _cd(self, r) -> Dict:
        return {'id': r['id'], 'opportunity_id': r['opportunity_id'],
                'name': r['name'], 'title': r['title'] or '',
                'org': r['org'] or '', 'role': r['role'] or 'Influencer',
                'hot_buttons': json.loads(r['hot_buttons']) if r['hot_buttons'] else [],
                'relationship_strength': r['relationship_strength'] or 3,
                'last_contact_date': r['last_contact_date'] or '',
                'notes': r['notes'] or '',
                'created_at': r['created_at'], 'updated_at': r['updated_at']}

    # --- Competitive Intelligence ---
    def list_competitors(self, opportunity_id: str) -> Dict:
        """List all competitors for an opportunity."""
        try:
            with self._connect() as conn:
                rows = conn.cursor().execute(
                    "SELECT * FROM competitor_intel WHERE opportunity_id=? ORDER BY company_name",
                    (opportunity_id,)).fetchall()
            return {'status': 'success', 'competitors': [self._cpd(r) for r in rows]}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_competitor(self, opportunity_id: str, data: Dict) -> Dict:
        """Create a competitor entry."""
        try:
            cid, now = str(uuid.uuid4()), datetime.now().isoformat()
            with self._connect() as conn:
                conn.cursor().execute("""
                    INSERT INTO competitor_intel
                    (id,opportunity_id,company_name,is_incumbent,likely_bid,
                     strengths,weaknesses,likely_approach,estimated_price,notes,
                     created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (cid, opportunity_id, data.get('company_name', 'Unknown'),
                     int(data.get('is_incumbent', False)),
                     data.get('likely_bid', 'Maybe'),
                     json.dumps(data.get('strengths', [])),
                     json.dumps(data.get('weaknesses', [])),
                     data.get('likely_approach', ''),
                     data.get('estimated_price'),
                     data.get('notes', ''), now, now))
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM competitor_intel WHERE id=?", (cid,)).fetchone()
            return {'status': 'success', 'competitor': self._cpd(row)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_competitor(self, competitor_id: str, data: Dict) -> Dict:
        """Update a competitor entry."""
        try:
            now = datetime.now().isoformat()
            sets, vals = [], []
            for f in ['company_name', 'is_incumbent', 'likely_bid',
                      'likely_approach', 'estimated_price', 'notes']:
                if f in data:
                    sets.append(f"{f}=?")
                    vals.append(int(data[f]) if f == 'is_incumbent' else data[f])
            for jf in ['strengths', 'weaknesses']:
                if jf in data:
                    sets.append(f"{jf}=?")
                    vals.append(json.dumps(data[jf]))
            sets.append("updated_at=?")
            vals.extend([now, competitor_id])
            with self._connect() as conn:
                conn.cursor().execute(
                    f"UPDATE competitor_intel SET {','.join(sets)} WHERE id=?", vals)
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM competitor_intel WHERE id=?", (competitor_id,)).fetchone()
            return {'status': 'success', 'competitor': self._cpd(row) if row else None}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_competitor(self, competitor_id: str) -> Dict:
        """Delete a competitor entry."""
        try:
            with self._connect() as conn:
                conn.cursor().execute(
                    "DELETE FROM competitor_intel WHERE id=?", (competitor_id,))
                conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    def _cpd(self, r) -> Dict:
        return {'id': r['id'], 'opportunity_id': r['opportunity_id'],
                'company_name': r['company_name'],
                'is_incumbent': bool(r['is_incumbent']),
                'likely_bid': r['likely_bid'] or 'Maybe',
                'strengths': json.loads(r['strengths']) if r['strengths'] else [],
                'weaknesses': json.loads(r['weaknesses']) if r['weaknesses'] else [],
                'likely_approach': r['likely_approach'] or '',
                'estimated_price': r['estimated_price'],
                'notes': r['notes'] or '',
                'created_at': r['created_at'], 'updated_at': r['updated_at']}

    # --- Engagement Activities ---
    def list_activities(self, opportunity_id: str) -> Dict:
        """List engagement activities, newest first."""
        try:
            with self._connect() as conn:
                rows = conn.cursor().execute(
                    """SELECT * FROM engagement_activities
                       WHERE opportunity_id=? ORDER BY activity_date DESC""",
                    (opportunity_id,)).fetchall()
            return {'status': 'success', 'activities': [self._ad(r) for r in rows]}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_activity(self, opportunity_id: str, data: Dict) -> Dict:
        """Log an engagement activity."""
        try:
            aid, now = str(uuid.uuid4()), datetime.now().isoformat()
            with self._connect() as conn:
                conn.cursor().execute("""
                    INSERT INTO engagement_activities
                    (id,opportunity_id,activity_date,activity_type,
                     customer_attendees,our_attendees,topics_covered,
                     intelligence_gathered,action_items,follow_up_required,
                     created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (aid, opportunity_id,
                     data.get('activity_date', now[:10]),
                     data.get('activity_type', 'Meeting'),
                     json.dumps(data.get('customer_attendees', [])),
                     json.dumps(data.get('our_attendees', [])),
                     data.get('topics_covered', ''),
                     data.get('intelligence_gathered', ''),
                     json.dumps(data.get('action_items', [])),
                     int(data.get('follow_up_required', False)),
                     now, now))
                conn.commit()
                row = conn.cursor().execute(
                    "SELECT * FROM engagement_activities WHERE id=?", (aid,)).fetchone()
            return {'status': 'success', 'activity': self._ad(row)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_activity(self, activity_id: str) -> Dict:
        """Delete an engagement activity."""
        try:
            with self._connect() as conn:
                conn.cursor().execute(
                    "DELETE FROM engagement_activities WHERE id=?", (activity_id,))
                conn.commit()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    def _ad(self, r) -> Dict:
        return {'id': r['id'], 'opportunity_id': r['opportunity_id'],
                'activity_date': r['activity_date'],
                'activity_type': r['activity_type'] or 'Meeting',
                'customer_attendees': json.loads(r['customer_attendees'])
                    if r['customer_attendees'] else [],
                'our_attendees': json.loads(r['our_attendees'])
                    if r['our_attendees'] else [],
                'topics_covered': r['topics_covered'] or '',
                'intelligence_gathered': r['intelligence_gathered'] or '',
                'action_items': json.loads(r['action_items']) if r['action_items'] else [],
                'follow_up_required': bool(r['follow_up_required']),
                'created_at': r['created_at'], 'updated_at': r['updated_at']}

    # --- Win Strategy ---
    def get_win_strategy(self, opportunity_id: str) -> Dict:
        """Get win strategy; returns defaults if no row exists yet."""
        try:
            with self._connect() as conn:
                row = conn.cursor().execute(
                    "SELECT * FROM win_strategy WHERE opportunity_id=?",
                    (opportunity_id,)).fetchone()
            ws = self._wsd(row) if row else self._ws_default(opportunity_id)
            return {'status': 'success', 'win_strategy': ws}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def upsert_win_strategy(self, opportunity_id: str, data: Dict) -> Dict:
        """Create or update win strategy for an opportunity."""
        try:
            now = datetime.now().isoformat()
            ws = self._ws_default(opportunity_id)
            existing = self.get_win_strategy(opportunity_id)
            if existing.get('status') == 'success':
                ws.update(existing['win_strategy'])
            ws.update({k: v for k, v in data.items() if k != 'opportunity_id'})
            with self._connect() as conn:
                conn.cursor().execute("""
                    INSERT INTO win_strategy (opportunity_id,pwin_score,win_themes,
                      discriminators,ghosts,customer_hot_buttons_summary,
                      gate_0_complete,gate_1_complete,gate_2_complete,
                      gate_3_complete,gate_4_complete,gate_5_complete,
                      gate_0_date,gate_1_date,gate_2_date,
                      gate_3_date,gate_4_date,gate_5_date,notes,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(opportunity_id) DO UPDATE SET
                      pwin_score=excluded.pwin_score,win_themes=excluded.win_themes,
                      discriminators=excluded.discriminators,ghosts=excluded.ghosts,
                      customer_hot_buttons_summary=excluded.customer_hot_buttons_summary,
                      gate_0_complete=excluded.gate_0_complete,
                      gate_1_complete=excluded.gate_1_complete,
                      gate_2_complete=excluded.gate_2_complete,
                      gate_3_complete=excluded.gate_3_complete,
                      gate_4_complete=excluded.gate_4_complete,
                      gate_5_complete=excluded.gate_5_complete,
                      gate_0_date=excluded.gate_0_date,gate_1_date=excluded.gate_1_date,
                      gate_2_date=excluded.gate_2_date,gate_3_date=excluded.gate_3_date,
                      gate_4_date=excluded.gate_4_date,gate_5_date=excluded.gate_5_date,
                      notes=excluded.notes,updated_at=excluded.updated_at""",
                    (opportunity_id, float(ws.get('pwin_score', 0)),
                     json.dumps(ws.get('win_themes', [])),
                     json.dumps(ws.get('discriminators', [])),
                     json.dumps(ws.get('ghosts', [])),
                     ws.get('customer_hot_buttons_summary', ''),
                     *[int(ws.get(f'gate_{i}_complete', False)) for i in range(6)],
                     *[ws.get(f'gate_{i}_date', '') for i in range(6)],
                     ws.get('notes', ''), now))
                conn.commit()
            return self.get_win_strategy(opportunity_id)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _wsd(self, r) -> Dict:
        return {'opportunity_id': r['opportunity_id'],
                'pwin_score': float(r['pwin_score'] or 0),
                'win_themes': json.loads(r['win_themes']) if r['win_themes'] else [],
                'discriminators': json.loads(r['discriminators']) if r['discriminators'] else [],
                'ghosts': json.loads(r['ghosts']) if r['ghosts'] else [],
                'customer_hot_buttons_summary': r['customer_hot_buttons_summary'] or '',
                **{f'gate_{i}_complete': bool(r[f'gate_{i}_complete']) for i in range(6)},
                **{f'gate_{i}_date': r[f'gate_{i}_date'] or '' for i in range(6)},
                'notes': r['notes'] or '', 'updated_at': r['updated_at']}

    def _ws_default(self, opp_id: str) -> Dict:
        return {'opportunity_id': opp_id, 'pwin_score': 0.0,
                'win_themes': [], 'discriminators': [], 'ghosts': [],
                'customer_hot_buttons_summary': '',
                **{f'gate_{i}_complete': False for i in range(6)},
                **{f'gate_{i}_date': '' for i in range(6)},
                'notes': '', 'updated_at': ''}

    # --- Price-to-Win ---
    def get_ptw(self, opportunity_id: str) -> Dict:
        """Get PTW analysis; returns defaults if no row exists yet."""
        try:
            with self._connect() as conn:
                row = conn.cursor().execute(
                    "SELECT * FROM ptw_analysis WHERE opportunity_id=?",
                    (opportunity_id,)).fetchone()
            ptw = self._ptwd(row) if row else self._ptw_default(opportunity_id)
            return {'status': 'success', 'ptw': ptw}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def upsert_ptw(self, opportunity_id: str, data: Dict) -> Dict:
        """Create or update PTW analysis."""
        try:
            now = datetime.now().isoformat()
            ptw = self._ptw_default(opportunity_id)
            existing = self.get_ptw(opportunity_id)
            if existing.get('status') == 'success':
                ptw.update(existing['ptw'])
            ptw.update({k: v for k, v in data.items()
                        if k not in ('opportunity_id', 'our_price', 'cost_gap')})
            with self._connect() as conn:
                conn.cursor().execute("""
                    INSERT INTO ptw_analysis
                    (opportunity_id,ptw_target,our_estimated_cost,fee_percent,
                     unanet_project_id,competitor_price_low,competitor_price_high,
                     pricing_notes,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(opportunity_id) DO UPDATE SET
                      ptw_target=excluded.ptw_target,
                      our_estimated_cost=excluded.our_estimated_cost,
                      fee_percent=excluded.fee_percent,
                      unanet_project_id=excluded.unanet_project_id,
                      competitor_price_low=excluded.competitor_price_low,
                      competitor_price_high=excluded.competitor_price_high,
                      pricing_notes=excluded.pricing_notes,
                      updated_at=excluded.updated_at""",
                    (opportunity_id, ptw.get('ptw_target'),
                     ptw.get('our_estimated_cost'),
                     float(ptw.get('fee_percent') or 0.08),
                     ptw.get('unanet_project_id', ''),
                     ptw.get('competitor_price_low'), ptw.get('competitor_price_high'),
                     ptw.get('pricing_notes', ''), now))
                conn.commit()
            return self.get_ptw(opportunity_id)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _ptwd(self, r) -> Dict:
        cost, fee = r['our_estimated_cost'], float(r['fee_percent'] or 0.08)
        target = r['ptw_target']
        our_price = round(cost * (1 + fee), 2) if cost is not None else None
        cost_gap = round(target - our_price, 2) if (
            target is not None and our_price is not None) else None
        return {'opportunity_id': r['opportunity_id'],
                'ptw_target': target, 'our_estimated_cost': cost,
                'fee_percent': fee, 'our_price': our_price, 'cost_gap': cost_gap,
                'unanet_project_id': r['unanet_project_id'] or '',
                'competitor_price_low': r['competitor_price_low'],
                'competitor_price_high': r['competitor_price_high'],
                'pricing_notes': r['pricing_notes'] or '',
                'updated_at': r['updated_at']}

    def _ptw_default(self, opp_id: str) -> Dict:
        return {'opportunity_id': opp_id, 'ptw_target': None,
                'our_estimated_cost': None, 'fee_percent': 0.08,
                'our_price': None, 'cost_gap': None, 'unanet_project_id': '',
                'competitor_price_low': None, 'competitor_price_high': None,
                'pricing_notes': '', 'updated_at': ''}


# Global singleton
_capture_manager: Optional[CaptureManager] = None


def get_capture_manager() -> CaptureManager:
    """Get or create the global CaptureManager singleton."""
    global _capture_manager
    if _capture_manager is None:
        _capture_manager = CaptureManager()
    return _capture_manager
