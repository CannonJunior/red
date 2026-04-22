"""
opportunities_schema.py — SQLite schema creation for the opportunities module.

Call init_opportunities_schema(conn) once at startup to ensure all tables
and indexes exist. Designed to be idempotent (CREATE IF NOT EXISTS + safe
ALTER TABLE ADD COLUMN).
"""

import sqlite3


def init_opportunities_schema(conn: sqlite3.Connection) -> None:
    """
    Create opportunities, tasks, and task_history tables and indexes.

    Args:
        conn: Open sqlite3 connection. Caller is responsible for commit/close.
    """
    cursor = conn.cursor()

    # Create opportunities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            value REAL DEFAULT 0.0,
            tags TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Core indexes for fast status/date queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_opportunities_status
        ON opportunities(status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_opportunities_created
        ON opportunities(created_at DESC)
    """)

    # Create tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            assigned_to TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_opportunity
        ON tasks(opportunity_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_dates
        ON tasks(start_date, end_date)
    """)

    # Create task_history table for tracking edits
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            opportunity_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT,
            progress INTEGER,
            assigned_to TEXT,
            edited_by TEXT,
            edited_at TEXT NOT NULL,
            change_description TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_history_task
        ON task_history(task_id, edited_at DESC)
    """)

    # Additional performance indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_opportunities_priority
        ON opportunities(priority)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_status
        ON tasks(status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_assigned
        ON tasks(assigned_to)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_history_opportunity
        ON task_history(opportunity_id)
    """)

    # Add pipeline_stage column if it doesn't exist yet (migration)
    # Reason: ALTER TABLE must precede index creation on the column
    try:
        cursor.execute(
            "ALTER TABLE opportunities ADD COLUMN pipeline_stage TEXT DEFAULT 'identified'"
        )
    except Exception:
        pass  # Column already exists

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_opportunities_pipeline_stage
        ON opportunities(pipeline_stage)
    """)

    # Add CRM-sourced columns (idempotent ALTER TABLE ADD COLUMN)
    _new_cols = [
        "probability TEXT",
        "proposal_due_date TEXT",
        "opp_number TEXT",
        "is_iwa TEXT",
        "owning_org TEXT",
        "proposal_folder TEXT",
        "agency TEXT",
        "solicitation_link TEXT",
        "deal_type TEXT",
    ]
    for col_def in _new_cols:
        try:
            cursor.execute(f"ALTER TABLE opportunities ADD COLUMN {col_def}")
        except Exception:
            pass  # Column already exists

    conn.commit()
