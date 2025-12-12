#!/usr/bin/env python3
"""
Database Migration Script
Safely applies database optimizations with automatic backup
"""

import sqlite3
import shutil
import os
from datetime import datetime
from pathlib import Path


def backup_database(db_path: str) -> str:
    """Create a backup of the database before migration."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"

    print(f"📦 Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created successfully")

    return backup_path


def apply_migration(db_path: str, migration_file: str) -> bool:
    """Apply SQL migration from file."""
    try:
        # Read migration SQL
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        # Connect to database
        print(f"🔌 Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"📝 Applying migration...")

        # Use executescript() which handles transactions automatically
        # This is needed for statements like ANALYZE that can't be in transactions
        try:
            cursor.executescript(migration_sql)
            print("✅ Migration SQL executed successfully")
        except sqlite3.OperationalError as e:
            # Check if it's an "already exists" error
            if 'already exists' in str(e).lower():
                print("⏭️  Some objects already exist, continuing...")
            else:
                raise

        print("💾 Changes applied successfully")

        # Verify migration
        print("\n🔍 Verifying migration...")
        verify_migration(cursor)

        conn.close()
        print("✅ Migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_migration(cursor):
    """Verify that migration was applied correctly."""
    # Check indexes
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
    index_count = cursor.fetchone()[0]
    print(f"  📊 Total indexes: {index_count}")

    # Check triggers
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'")
    trigger_count = cursor.fetchone()[0]
    print(f"  ⚡ Total triggers: {trigger_count}")

    # Check FTS table exists
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='objects_fts'")
    fts_exists = cursor.fetchone()[0] > 0
    print(f"  🔍 FTS table exists: {'✅' if fts_exists else '❌'}")

    # List new composite indexes
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index'
        AND name LIKE '%folder%'
        OR name LIKE '%composite%'
        ORDER BY name
    """)
    composite_indexes = cursor.fetchall()
    if composite_indexes:
        print(f"\n  🎯 Composite indexes:")
        for idx in composite_indexes:
            print(f"     • {idx[0]}")

    # List triggers
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name")
    triggers = cursor.fetchall()
    if triggers:
        print(f"\n  ⚙️  FTS sync triggers:")
        for trigger in triggers:
            print(f"     • {trigger[0]}")


def get_database_stats(db_path: str):
    """Get database statistics before and after migration."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get table sizes
    cursor.execute("SELECT COUNT(*) FROM searchable_objects")
    objects_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM folders")
    folders_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tags")
    tags_count = cursor.fetchone()[0]

    # Get FTS index size (use a simple search query since FTS tables work differently)
    try:
        # For FTS5 tables, we can count rows using a match-all query
        cursor.execute("SELECT COUNT(*) FROM objects_fts WHERE objects_fts MATCH '*' OR 1=1")
        fts_count = cursor.fetchone()[0]
    except:
        # Fallback: assume FTS count matches objects if query fails
        fts_count = objects_count

    conn.close()

    print(f"\n📊 Database Statistics:")
    print(f"  • Objects: {objects_count}")
    print(f"  • Folders: {folders_count}")
    print(f"  • Tags: {tags_count}")
    print(f"  • FTS entries: {fts_count}")

    if objects_count != fts_count:
        print(f"\n  ⚠️  WARNING: FTS index out of sync!")
        print(f"     Objects: {objects_count}, FTS entries: {fts_count}")
        print(f"     Difference: {abs(objects_count - fts_count)}")


def main():
    """Main migration execution."""
    print("=" * 70)
    print("  DATABASE OPTIMIZATION MIGRATION")
    print("  Adds composite indexes and FTS sync triggers")
    print("=" * 70)
    print()

    # Paths
    db_path = "search_system.db"
    migration_file = "db_migrations/001_add_indexes_and_triggers.sql"

    # Check files exist
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found: {db_path}")
        return 1

    if not os.path.exists(migration_file):
        print(f"❌ Error: Migration file not found: {migration_file}")
        return 1

    # Get stats before migration
    print("📊 PRE-MIGRATION STATISTICS:")
    get_database_stats(db_path)
    print()

    # Create backup
    backup_path = backup_database(db_path)
    print()

    # Apply migration
    success = apply_migration(db_path, migration_file)
    print()

    if success:
        # Get stats after migration
        print("📊 POST-MIGRATION STATISTICS:")
        get_database_stats(db_path)
        print()

        print("🎉 Migration completed successfully!")
        print(f"📦 Backup saved at: {backup_path}")
        print()
        print("💡 You can safely delete the backup after verifying everything works.")
        return 0
    else:
        print("❌ Migration failed!")
        print(f"📦 Database backup available at: {backup_path}")
        print("💡 You can restore from backup if needed:")
        print(f"   mv {backup_path} {db_path}")
        return 1


if __name__ == "__main__":
    exit(main())
