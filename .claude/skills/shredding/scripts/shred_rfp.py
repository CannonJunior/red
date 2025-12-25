#!/usr/bin/env python3
"""
RFP Shredding Script

Automated RFP shredding with requirement extraction, classification,
and compliance matrix generation.

Usage:
    python shred_rfp.py <rfp_file.pdf> --rfp-number FA8732-25-R-0001 \
        --name "IT Support Services" --due-date 2025-03-15 \
        --create-tasks --auto-assign

Example:
    python shred_rfp.py rfp_12345.pdf \
        --rfp-number FA8732-25-R-0001 \
        --name "IT Support Services" \
        --due-date 2025-03-15 \
        --agency "Air Force" \
        --naics 541512 \
        --set-aside "Small Business" \
        --create-tasks \
        --auto-assign \
        --output-dir ./matrices
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shredding.rfp_shredder import RFPShredder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Shred RFP and generate compliance matrix',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Required arguments
    parser.add_argument(
        'file_path',
        help='Path to RFP PDF file'
    )

    parser.add_argument(
        '--rfp-number',
        required=True,
        help='RFP/solicitation number (e.g., FA8732-25-R-0001)'
    )

    parser.add_argument(
        '--name',
        required=True,
        help='Opportunity name (e.g., "IT Support Services")'
    )

    parser.add_argument(
        '--due-date',
        required=True,
        help='Proposal due date in YYYY-MM-DD format'
    )

    # Optional arguments
    parser.add_argument(
        '--agency',
        help='Issuing agency (e.g., "Air Force")'
    )

    parser.add_argument(
        '--naics',
        help='NAICS code (e.g., 541512)'
    )

    parser.add_argument(
        '--set-aside',
        help='Set-aside type (e.g., "Small Business", "8(a)")'
    )

    parser.add_argument(
        '--create-tasks',
        action='store_true',
        help='Create tasks for each requirement'
    )

    parser.add_argument(
        '--auto-assign',
        action='store_true',
        help='Auto-assign tasks to team members/agents'
    )

    parser.add_argument(
        '--output-dir',
        help='Output directory for compliance matrix (default: current dir)'
    )

    parser.add_argument(
        '--db-path',
        default='opportunities.db',
        help='Path to SQLite database (default: opportunities.db)'
    )

    parser.add_argument(
        '--ollama-url',
        default='http://localhost:11434',
        help='Ollama server URL (default: http://localhost:11434)'
    )

    parser.add_argument(
        '--model',
        default='qwen2.5:3b',
        help='Ollama model to use (default: qwen2.5:3b)'
    )

    args = parser.parse_args()

    # Validate file exists
    if not Path(args.file_path).exists():
        logger.error(f"File not found: {args.file_path}")
        sys.exit(1)

    # Initialize shredder
    logger.info("Initializing RFP Shredder...")
    shredder = RFPShredder(
        db_path=args.db_path,
        ollama_url=args.ollama_url,
        ollama_model=args.model
    )

    # Shred RFP
    logger.info(f"Starting shredding: {args.rfp_number}")
    logger.info(f"File: {args.file_path}")
    logger.info(f"Due date: {args.due_date}")

    result = shredder.shred_rfp(
        file_path=args.file_path,
        rfp_number=args.rfp_number,
        opportunity_name=args.name,
        due_date=args.due_date,
        agency=args.agency,
        naics_code=args.naics,
        set_aside=args.set_aside,
        create_tasks=args.create_tasks,
        auto_assign=args.auto_assign,
        output_dir=args.output_dir
    )

    # Display results
    if result['status'] == 'success':
        print("\n" + "="*60)
        print("✅ RFP SHREDDING COMPLETE")
        print("="*60)
        print(f"\nOpportunity ID: {result['opportunity_id']}")
        print(f"\nRequirements Extracted:")
        print(f"  Total:       {result['total_requirements']}")
        print(f"  Mandatory:   {result['mandatory_count']}")
        print(f"  Recommended: {result['recommended_count']}")
        print(f"  Optional:    {result['optional_count']}")

        if args.create_tasks:
            print(f"\nTasks Created: {result['tasks_created']}")

        print(f"\nCompliance Matrix: {result['matrix_file']}")

        print(f"\nSections Found:")
        for section, data in result['sections'].items():
            print(f"  Section {section}: {data['title']}")
            if data.get('start_page'):
                print(f"    Pages: {data['start_page']}-{data['end_page']}")

        print("\n" + "="*60)

        # Show status
        status = shredder.get_opportunity_status(result['opportunity_id'])
        print(f"\nCompliance Rate: {status['requirements']['completion_rate']}%")
        print(f"Not Started: {status['requirements']['not_started']}")

        print("\nNext steps:")
        print("  1. Review compliance matrix")
        print("  2. Assign requirements to team members")
        print("  3. Start addressing requirements")
        print("  4. Update compliance status as you progress")

        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ RFP SHREDDING FAILED")
        print("="*60)
        print(f"\nError: {result['error']}")
        print("\nPlease check:")
        print("  - PDF file is readable")
        print("  - Ollama is running (ollama serve)")
        print("  - Database migrations have been run")
        print("  - Network connectivity to Ollama")
        sys.exit(1)


if __name__ == "__main__":
    main()
