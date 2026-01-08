#!/usr/bin/env python3
"""
Database Migration: Add Tasks Table

Creates the tasks table for RFP shredding task management.

Usage:
    python migrations/002_add_tasks_table.py [--rollback]
"""

import sqlite3
import sys
import argparse
from pathlib import Path
from datetime import datetime


def get_db_path():
    """Get the path to the opportunities database."""
    return Path(__file__).parent.parent / "opportunities.db"


def upgrade():
    """Create tasks table and indexes."""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("📊 Running migration: Add tasks table")

    try:
        # Check if tasks table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='tasks'
        """)

        if cursor.fetchone():
            print("⚠️  Tasks table already exists. Checking schema...")

            # Check if it has the shredding-compatible columns
            cursor.execute("PRAGMA table_info(tasks)")
            columns = {col[1] for col in cursor.fetchall()}

            required_cols = {'id', 'opportunity_id', 'title', 'description',
                           'status', 'priority', 'due_date', 'assignee',
                           'metadata', 'created_at', 'updated_at'}

            if required_cols.issubset(columns):
                print("✅ Tasks table already has shredding-compatible schema")
                return True
            else:
                print("⚠️  Tasks table exists but missing columns:")
                print(f"  Missing: {required_cols - columns}")
                print("  Please manually migrate existing tasks or drop the table")
                return False

        # Create tasks table with shredding-compatible schema
        print("  Creating 'tasks' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                -- Identity
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL,

                -- Task Details
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',

                -- Scheduling
                due_date TIMESTAMP,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                completed_at TIMESTAMP,

                -- Assignment
                assignee TEXT,
                assignee_type TEXT,

                -- Progress
                progress INTEGER DEFAULT 0,

                -- Metadata
                metadata TEXT,
                tags TEXT,

                -- Timestamps
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for tasks
        print("  Creating indexes for 'tasks'...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_opportunity
            ON tasks(opportunity_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_priority
            ON tasks(priority)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_assignee
            ON tasks(assignee)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_due_date
            ON tasks(due_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_updated
            ON tasks(updated_at DESC)
        """)

        conn.commit()

        # Verify table created
        cursor.execute("PRAGMA table_info(tasks)")
        columns = cursor.fetchall()

        print(f"\n✅ Migration successful!")
        print(f"  'tasks' table created with {len(columns)} columns")

    except sqlite3.Error as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True


def downgrade():
    """Remove tasks table (rollback)."""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("🔄 Rolling back migration: Remove tasks table")

    try:
        # Drop indexes first
        print("  Dropping indexes...")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_opportunity")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_status")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_priority")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_assignee")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_due_date")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_updated")

        # Drop table
        print("  Dropping 'tasks' table...")
        cursor.execute("DROP TABLE IF EXISTS tasks")

        conn.commit()
        print(f"\n✅ Rollback successful!")

    except sqlite3.Error as e:
        print(f"\n❌ Rollback failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True


def verify_migration():
    """Verify migration was successful."""
    db_path = get_db_path()

    if not db_path.exists():
        print("❌ Database not found")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("\n🔍 Verifying migration...")

    try:
        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='tasks'
        """)

        if not cursor.fetchone():
            print("❌ 'tasks' table not found")
            return False

        # Check required columns exist
        cursor.execute("PRAGMA table_info(tasks)")
        columns = {col[1] for col in cursor.fetchall()}

        required_cols = {'id', 'opportunity_id', 'title', 'description',
                        'status', 'priority', 'due_date', 'assignee',
                        'metadata', 'created_at', 'updated_at'}

        if not required_cols.issubset(columns):
            print(f"❌ Missing required columns: {required_cols - columns}")
            return False

        # Check indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_tasks_%'
        """)
        indexes = cursor.fetchall()

        print(f"✅ Table verified: tasks")
        print(f"✅ Columns verified: {len(columns)} columns")
        print(f"✅ Indexes verified: {len(indexes)} indexes")

        # Test insert and delete
        test_id = "test_migration_verify_task"
        cursor.execute("""
            INSERT INTO tasks
            (id, opportunity_id, title, status)
            VALUES (?, ?, ?, ?)
        """, (test_id, test_id, "Test Task", "pending"))

        cursor.execute("DELETE FROM tasks WHERE id = ?", (test_id,))
        conn.commit()

        print("✅ Insert/Delete test passed")

    except sqlite3.Error as e:
        print(f"❌ Verification failed: {e}")
        return False
    finally:
        conn.close()

    return True


def main():
    """Run migration script."""
    parser = argparse.ArgumentParser(
        description='Database migration for tasks table'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback the migration (remove table)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migration was successful'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Tasks Table - Database Migration")
    print("=" * 60)
    print(f"Database: {get_db_path()}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60 + "\n")

    if args.verify:
        success = verify_migration()
        sys.exit(0 if success else 1)

    if args.rollback:
        success = downgrade()
    else:
        success = upgrade()

    if success:
        # Auto-verify after upgrade
        if not args.rollback:
            verify_migration()
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
