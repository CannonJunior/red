#!/usr/bin/env python3
"""
Database Migration: Add Shredding Tables

Creates the requirements and rfp_metadata tables for the RFP shredding skill.

Usage:
    python migrations/001_add_shredding_tables.py [--rollback]
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
    """Create shredding tables and indexes."""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Creating new database...")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("📊 Running migration: Add shredding tables")

    try:
        # Create requirements table
        print("  Creating 'requirements' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                -- Identity
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL,
                task_id TEXT,

                -- Source Information
                section TEXT NOT NULL,
                page_number INTEGER,
                paragraph_id TEXT,
                source_text TEXT NOT NULL,

                -- Classification (from Ollama)
                compliance_type TEXT NOT NULL,
                requirement_category TEXT,
                priority TEXT DEFAULT 'medium',
                risk_level TEXT DEFAULT 'green',

                -- Compliance Tracking
                compliance_status TEXT DEFAULT 'not_started',
                proposal_section TEXT,
                proposal_page INTEGER,

                -- Assignment
                assignee_id TEXT,
                assignee_type TEXT,
                assignee_name TEXT,

                -- Metadata
                keywords TEXT,
                dependencies TEXT,
                notes TEXT,
                extracted_entities TEXT,

                -- Timestamps
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                due_date TIMESTAMP,
                completed_at TIMESTAMP,

                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
            )
        """)

        # Create indexes for requirements
        print("  Creating indexes for 'requirements'...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requirements_opportunity
            ON requirements(opportunity_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requirements_section
            ON requirements(section)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requirements_compliance
            ON requirements(compliance_status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requirements_assignee
            ON requirements(assignee_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requirements_priority
            ON requirements(priority)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requirements_updated
            ON requirements(updated_at DESC)
        """)

        # Create rfp_metadata table
        print("  Creating 'rfp_metadata' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfp_metadata (
                -- Identity
                id TEXT PRIMARY KEY,
                opportunity_id TEXT NOT NULL UNIQUE,

                -- RFP Identification
                rfp_number TEXT,
                rfp_title TEXT NOT NULL,
                issuing_agency TEXT,
                office_name TEXT,
                naics_code TEXT,
                naics_description TEXT,
                set_aside TEXT,
                contract_type TEXT,

                -- Dates
                posted_date TIMESTAMP,
                response_due_date TIMESTAMP,
                questions_due_date TIMESTAMP,
                estimated_award_date TIMESTAMP,

                -- Document Information
                file_path TEXT NOT NULL,
                file_name TEXT,
                file_size_bytes INTEGER,
                page_count INTEGER,
                sections_found TEXT,

                -- Processing Metadata
                shredded_at TIMESTAMP,
                shredded_by TEXT,
                processing_time_seconds REAL,
                total_requirements INTEGER DEFAULT 0,
                mandatory_requirements INTEGER DEFAULT 0,
                optional_requirements INTEGER DEFAULT 0,

                -- Source
                source_url TEXT,
                source_system TEXT DEFAULT 'sam.gov',
                sam_opportunity_id TEXT,

                -- Status
                shredding_status TEXT DEFAULT 'pending',
                error_message TEXT,

                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for rfp_metadata
        print("  Creating indexes for 'rfp_metadata'...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rfp_metadata_rfp_number
            ON rfp_metadata(rfp_number)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rfp_metadata_due_date
            ON rfp_metadata(response_due_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rfp_metadata_status
            ON rfp_metadata(shredding_status)
        """)

        conn.commit()

        # Verify tables created
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('requirements', 'rfp_metadata')
        """)
        tables = cursor.fetchall()

        print(f"\n✅ Migration successful!")
        print(f"  Tables created: {[t[0] for t in tables]}")

        # Display schema info
        cursor.execute("PRAGMA table_info(requirements)")
        req_columns = cursor.fetchall()
        print(f"  'requirements' table: {len(req_columns)} columns")

        cursor.execute("PRAGMA table_info(rfp_metadata)")
        meta_columns = cursor.fetchall()
        print(f"  'rfp_metadata' table: {len(meta_columns)} columns")

    except sqlite3.Error as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True


def downgrade():
    """Remove shredding tables (rollback)."""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("🔄 Rolling back migration: Remove shredding tables")

    try:
        # Drop indexes first
        print("  Dropping indexes...")
        cursor.execute("DROP INDEX IF EXISTS idx_requirements_opportunity")
        cursor.execute("DROP INDEX IF EXISTS idx_requirements_section")
        cursor.execute("DROP INDEX IF EXISTS idx_requirements_compliance")
        cursor.execute("DROP INDEX IF EXISTS idx_requirements_assignee")
        cursor.execute("DROP INDEX IF EXISTS idx_requirements_priority")
        cursor.execute("DROP INDEX IF EXISTS idx_requirements_updated")
        cursor.execute("DROP INDEX IF EXISTS idx_rfp_metadata_rfp_number")
        cursor.execute("DROP INDEX IF EXISTS idx_rfp_metadata_due_date")
        cursor.execute("DROP INDEX IF EXISTS idx_rfp_metadata_status")

        # Drop tables
        print("  Dropping 'requirements' table...")
        cursor.execute("DROP TABLE IF EXISTS requirements")

        print("  Dropping 'rfp_metadata' table...")
        cursor.execute("DROP TABLE IF EXISTS rfp_metadata")

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
        # Check tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('requirements', 'rfp_metadata')
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if 'requirements' not in tables:
            print("❌ 'requirements' table not found")
            return False

        if 'rfp_metadata' not in tables:
            print("❌ 'rfp_metadata' table not found")
            return False

        # Check indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_requirements_%'
        """)
        req_indexes = cursor.fetchall()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_rfp_metadata_%'
        """)
        meta_indexes = cursor.fetchall()

        print(f"✅ Tables verified: {tables}")
        print(f"✅ Indexes verified: {len(req_indexes)} for requirements, {len(meta_indexes)} for rfp_metadata")

        # Test insert and delete
        test_id = "test_migration_verify"
        cursor.execute("""
            INSERT INTO rfp_metadata
            (id, opportunity_id, rfp_title, file_path)
            VALUES (?, ?, ?, ?)
        """, (test_id, test_id, "Test", "/test"))

        cursor.execute("DELETE FROM rfp_metadata WHERE id = ?", (test_id,))
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
        description='Database migration for RFP shredding tables'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback the migration (remove tables)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migration was successful'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("RFP Shredding Skill - Database Migration")
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
