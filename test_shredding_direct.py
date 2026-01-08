#!/usr/bin/env python3
"""
Direct test of shredding tools to verify end-to-end functionality.
"""

from agent_system.shredding_tools import shred_rfp, get_opportunity_status

# Test the shred_rfp tool directly
print("=" * 60)
print("Testing RFP Shredding Tool")
print("=" * 60)

result = shred_rfp(
    file_path="data/JADC2/FA8612-21-S-C001.txt",
    rfp_number="FA8612-21-S-C001-TEST",
    opportunity_name="JADC2 Cloud Services Test",
    due_date="2025-02-15",
    agency="Air Force",
    create_tasks=True,
    auto_assign=False
)

print("\n" + "=" * 60)
print("SHREDDING RESULT")
print("=" * 60)

if result['status'] == 'success':
    print(f"✅ Status: {result['status']}")
    print(f"📋 Opportunity ID: {result['opportunity_id']}")
    print(f"📊 Total Requirements: {result['total_requirements']}")
    print(f"  - Mandatory: {result['mandatory_count']}")
    print(f"  - Recommended: {result['recommended_count']}")
    print(f"  - Optional: {result['optional_count']}")
    print(f"📝 Tasks Created: {result['tasks_created']}")
    print(f"📄 Compliance Matrix: {result['matrix_file']}")
    print(f"\n📑 Sections Found:")
    for section, details in result['sections'].items():
        print(f"  Section {section}: {details['title']}")
        print(f"    Pages: {details.get('start_page')} - {details.get('end_page')}")

    # Test get_opportunity_status
    print("\n" + "=" * 60)
    print("TESTING OPPORTUNITY STATUS")
    print("=" * 60)

    status = get_opportunity_status(result['opportunity_id'])
    print(f"\n✅ Opportunity: {status['opportunity']['title']}")
    print(f"📊 Requirements: {status['requirements']['total']} total")
    print(f"  - Mandatory: {status['requirements']['mandatory']}")
    print(f"  - Compliant: {status['requirements']['compliant']}")
    print(f"  - Not Started: {status['requirements']['not_started']}")
    print(f"  - Completion Rate: {status['requirements']['completion_rate']}%")
    print(f"\n📋 Tasks: {status['tasks']['total']} total")
    print(f"  - Completed: {status['tasks']['completed']}")
    print(f"  - In Progress: {status['tasks']['in_progress']}")
    print(f"  - Pending: {status['tasks']['pending']}")

else:
    print(f"❌ Status: {result['status']}")
    print(f"Error: {result.get('error', 'Unknown error')}")
