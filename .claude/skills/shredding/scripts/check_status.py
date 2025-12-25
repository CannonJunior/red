#!/usr/bin/env python3
"""
Check RFP Shredding Status

View the status of a shredded RFP opportunity, including:
- Requirements breakdown
- Compliance status
- Task progress

Usage:
    python check_status.py <opportunity_id>

Example:
    python check_status.py 12345678-1234-1234-1234-123456789abc
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shredding.rfp_shredder import RFPShredder

logging.basicConfig(level=logging.WARNING)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check RFP shredding status'
    )

    parser.add_argument(
        'opportunity_id',
        help='Opportunity ID to check'
    )

    parser.add_argument(
        '--db-path',
        default='opportunities.db',
        help='Path to SQLite database (default: opportunities.db)'
    )

    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed requirement breakdown'
    )

    args = parser.parse_args()

    # Initialize shredder
    shredder = RFPShredder(db_path=args.db_path)

    # Get status
    status = shredder.get_opportunity_status(args.opportunity_id)

    if 'error' in status:
        print(f"❌ Error: {status['error']}")
        sys.exit(1)

    # Display status
    print("\n" + "="*60)
    print("RFP SHREDDING STATUS")
    print("="*60)

    opp = status['opportunity']
    print(f"\nOpportunity: {opp['title']}")
    print(f"ID: {opp['id']}")
    print(f"Status: {opp['status'].upper()}")
    print(f"Due Date: {opp['due_date']}")

    if opp['metadata']:
        meta = opp['metadata']
        if 'rfp_number' in meta:
            print(f"RFP Number: {meta['rfp_number']}")
        if 'sections' in meta:
            print(f"Sections: {', '.join(meta['sections'])}")

    # Requirements
    req = status['requirements']
    print(f"\n{'Requirements':<20} {'Count':<10} {'%':>10}")
    print("-" * 40)
    print(f"{'Total':<20} {req['total']:<10}")
    print(f"{'Mandatory':<20} {req['mandatory']:<10}")
    print()
    print(f"{'Fully Compliant':<20} {req['compliant']:<10} {req['compliant']/req['total']*100:>9.1f}%")
    print(f"{'Partially Compliant':<20} {req['partial']:<10} {req['partial']/req['total']*100:>9.1f}%")
    print(f"{'Non-Compliant':<20} {req['non_compliant']:<10} {req['non_compliant']/req['total']*100:>9.1f}%")
    print(f"{'Not Started':<20} {req['not_started']:<10} {req['not_started']/req['total']*100:>9.1f}%")
    print()
    print(f"{'Completion Rate':<20} {'':<10} {req['completion_rate']:>9.1f}%")

    # Tasks
    if status['tasks']['total'] > 0:
        tasks = status['tasks']
        print(f"\n{'Tasks':<20} {'Count':<10} {'%':>10}")
        print("-" * 40)
        print(f"{'Total':<20} {tasks['total']:<10}")
        print(f"{'Completed':<20} {tasks['completed']:<10} {tasks['completed']/tasks['total']*100:>9.1f}%")
        print(f"{'In Progress':<20} {tasks['in_progress']:<10} {tasks['in_progress']/tasks['total']*100:>9.1f}%")
        print(f"{'Pending':<20} {tasks['pending']:<10} {tasks['pending']/tasks['total']*100:>9.1f}%")

    # Detailed breakdown
    if args.detailed:
        import sqlite3
        import json

        conn = sqlite3.connect(args.db_path)
        cursor = conn.cursor()

        # Get requirements by category
        cursor.execute("""
            SELECT
                requirement_category,
                COUNT(*) as count,
                SUM(CASE WHEN compliance_status = 'fully_compliant' THEN 1 ELSE 0 END) as compliant
            FROM requirements
            WHERE opportunity_id = ?
            GROUP BY requirement_category
            ORDER BY count DESC
        """, (args.opportunity_id,))

        categories = cursor.fetchall()

        print(f"\n{'Category Breakdown':<20} {'Total':<10} {'Compliant':>10}")
        print("-" * 40)
        for cat, count, compliant in categories:
            print(f"{cat or 'unknown':<20} {count:<10} {compliant:>10}")

        # Get requirements by priority
        cursor.execute("""
            SELECT
                priority,
                COUNT(*) as count
            FROM requirements
            WHERE opportunity_id = ?
            GROUP BY priority
            ORDER BY
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END
        """, (args.opportunity_id,))

        priorities = cursor.fetchall()

        print(f"\n{'Priority Breakdown':<20} {'Count':>10}")
        print("-" * 40)
        for priority, count in priorities:
            print(f"{priority or 'unknown':<20} {count:>10}")

        conn.close()

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
