"""Test script for TODO API Phase 4 - MCP Integration.

This test suite validates the MCP tool integration by simulating
MCP tool calls through the TODO manager and verifying results.

Tests:
- MCP tool: create_todo (natural language)
- MCP tool: create_todo (structured)
- MCP tool: list_todos (with filters)
- MCP tool: get_todo
- MCP tool: update_todo
- MCP tool: complete_todo
- MCP tool: delete_todo
- MCP tool: create_list
- MCP tool: share_list
- MCP tool: parse_todo
"""

import json
import uuid
from datetime import datetime, timedelta

# Import TODO components directly
from todos import get_todo_manager
from todos.nlp_parser import parse_natural_language

print("\n" + "="*60)
print("TODO API Phase 4 - MCP Integration Test Suite")
print("="*60)
print("\nNote: Testing MCP tool functionality via direct manager calls")
print("(Simulating MCP tool invocations)")


def test_mcp_create_todo_natural_language():
    """Test MCP create_todo tool with natural language input."""
    print("\n" + "="*60)
    print("Test 1: MCP create_todo - Natural Language")
    print("="*60)

    manager = get_todo_manager()

    # Create test user
    username = f"mcp_test_{str(uuid.uuid4())[:8]}"
    user_result = manager.create_user(username, f"{username}@test.com", "MCP Test User")
    user_id = user_result['user']['id']
    print(f"\n✅ Created test user: {user_id[:8]}...")

    test_cases = [
        {
            "input": "Buy groceries tomorrow @high #personal",
            "expected_title": "Buy groceries",
            "expected_priority": "high",
            "expected_tags": ["personal"]
        },
        {
            "input": "Team meeting Friday 2pm @urgent #work",
            "expected_title": "Team meeting",
            "expected_priority": "urgent",
            "expected_tags": ["work"]
        },
        {
            "input": "Review code today !! #development #review",
            "expected_title": "Review code",
            "expected_priority": "urgent",
            "expected_tags": ["development", "review"]
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{test['input']}'")

        # Simulate MCP tool call
        try:
            # Parse natural language
            parsed = parse_natural_language(test['input'], user_id)

            # Create todo with parsed data
            result = manager.create_todo(
                user_id,
                parsed['title'],
                priority=parsed.get('priority', 'medium'),
                due_date=parsed.get('due_date'),
                due_time=parsed.get('due_time'),
                bucket=parsed.get('bucket', 'inbox'),
                tags=parsed.get('tags', [])
            )

            todo = result['todo']

            # Verify results
            checks_passed = True

            if test['expected_title'] in todo['title']:
                print(f"   ✅ Title: '{todo['title']}'")
            else:
                print(f"   ❌ Title: Expected to contain '{test['expected_title']}', got '{todo['title']}'")
                checks_passed = False

            if todo['priority'] == test['expected_priority']:
                print(f"   ✅ Priority: {todo['priority']}")
            else:
                print(f"   ❌ Priority: Expected {test['expected_priority']}, got {todo['priority']}")
                checks_passed = False

            if set(todo['tags']) == set(test['expected_tags']):
                print(f"   ✅ Tags: {todo['tags']}")
            else:
                print(f"   ❌ Tags: Expected {test['expected_tags']}, got {todo['tags']}")
                checks_passed = False

            if checks_passed:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Natural Language: {passed} passed, {failed} failed")
    return passed, failed


def test_mcp_list_todos_with_filters():
    """Test MCP list_todos tool with various filters."""
    print("\n" + "="*60)
    print("Test 2: MCP list_todos - Filtering")
    print("="*60)

    manager = get_todo_manager()

    # Create test user
    username = f"mcp_list_{str(uuid.uuid4())[:8]}"
    user_result = manager.create_user(username, f"{username}@test.com", "List Test User")
    user_id = user_result['user']['id']
    print(f"\n✅ Created test user: {user_id[:8]}...")

    # Create todos with different attributes
    print("\nCreating test todos...")
    manager.create_todo(user_id, "High priority task", priority="high", bucket="today")
    manager.create_todo(user_id, "Low priority task", priority="low", bucket="inbox")
    manager.create_todo(user_id, "Urgent task", priority="urgent", bucket="upcoming", tags=["work"])
    manager.create_todo(user_id, "Completed task", priority="medium", status="completed")
    print("✅ Created 4 test todos")

    test_filters = [
        {"filter": {"priority": "high"}, "expected_min": 1, "name": "High priority"},
        {"filter": {"bucket": "today"}, "expected_min": 1, "name": "Today bucket"},
        {"filter": {"status": "completed"}, "expected_min": 1, "name": "Completed status"},
        {"filter": {"priority": "urgent"}, "expected_min": 1, "name": "Urgent priority"},
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_filters, 1):
        print(f"\n{i}. Testing filter: {test['name']}")
        print(f"   Filter: {test['filter']}")

        try:
            # Simulate MCP tool call (filters as dict)
            result = manager.list_todos(user_id, filters=test['filter'])
            count = result['count']

            if count >= test['expected_min']:
                print(f"   ✅ Found {count} todo(s)")
                passed += 1
            else:
                print(f"   ❌ Expected at least {test['expected_min']}, found {count}")
                failed += 1

        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"List Filtering: {passed} passed, {failed} failed")
    return passed, failed


def test_mcp_crud_operations():
    """Test MCP CRUD operations: get, update, complete, delete."""
    print("\n" + "="*60)
    print("Test 3: MCP CRUD Operations")
    print("="*60)

    manager = get_todo_manager()

    # Create test user
    username = f"mcp_crud_{str(uuid.uuid4())[:8]}"
    user_result = manager.create_user(username, f"{username}@test.com", "CRUD Test User")
    user_id = user_result['user']['id']
    print(f"\n✅ Created test user: {user_id[:8]}...")

    # Create a test todo
    todo_result = manager.create_todo(user_id, "Test todo for CRUD", priority="medium")
    todo_id = todo_result['todo']['id']
    print(f"✅ Created test todo: {todo_id[:8]}...")

    passed = 0
    failed = 0

    # Test 1: get_todo
    print("\n1. Testing get_todo...")
    try:
        result = manager.get_todo(todo_id)
        # get_todo returns the dict directly, not wrapped
        if result and result.get('title') == "Test todo for CRUD":
            print("   ✅ Retrieved todo successfully")
            passed += 1
        else:
            print(f"   ❌ Wrong todo retrieved")
            failed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed += 1

    # Test 2: update_todo
    print("\n2. Testing update_todo...")
    try:
        manager.update_todo(todo_id, user_id, {"title": "Updated todo", "priority": "high"})
        result = manager.get_todo(todo_id)
        if result.get('title') == "Updated todo" and result.get('priority') == "high":
            print("   ✅ Updated todo successfully")
            passed += 1
        else:
            print(f"   ❌ Update failed")
            failed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed += 1

    # Test 3: complete_todo
    print("\n3. Testing complete_todo...")
    try:
        manager.complete_todo(todo_id, user_id)
        result = manager.get_todo(todo_id)
        if result.get('status') == "completed":
            print("   ✅ Completed todo successfully")
            passed += 1
        else:
            print(f"   ❌ Completion failed")
            failed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed += 1

    # Test 4: delete_todo
    print("\n4. Testing delete_todo...")
    try:
        manager.delete_todo(todo_id, user_id)
        # Try to get deleted todo - should return None
        result = manager.get_todo(todo_id)
        if result is None:
            print("   ✅ Deleted todo successfully")
            passed += 1
        else:
            print(f"   ❌ Todo still exists after deletion")
            failed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed += 1

    print(f"\n{'='*60}")
    print(f"CRUD Operations: {passed} passed, {failed} failed")
    return passed, failed


def test_mcp_list_operations():
    """Test MCP list operations: create_list, share_list."""
    print("\n" + "="*60)
    print("Test 4: MCP List Operations")
    print("="*60)

    manager = get_todo_manager()

    # Create test users
    user1_name = f"mcp_list1_{str(uuid.uuid4())[:8]}"
    user1_result = manager.create_user(user1_name, f"{user1_name}@test.com", "List User 1")
    user1_id = user1_result['user']['id']

    user2_name = f"mcp_list2_{str(uuid.uuid4())[:8]}"
    user2_result = manager.create_user(user2_name, f"{user2_name}@test.com", "List User 2")
    user2_id = user2_result['user']['id']

    print(f"\n✅ Created test users: {user1_id[:8]}... and {user2_id[:8]}...")

    passed = 0
    failed = 0

    # Test 1: create_list
    print("\n1. Testing create_list...")
    try:
        result = manager.create_list(
            user1_id,
            "Team Project",
            description="Shared project tasks",
            color="#10B981"
        )
        list_id = result['list']['id']
        if result['list']['name'] == "Team Project":
            print(f"   ✅ Created list: Team Project ({list_id[:8]}...)")
            passed += 1
        else:
            print(f"   ❌ List creation failed")
            failed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed += 1
        return passed, failed

    # Test 2: share_list
    print("\n2. Testing share_list...")
    try:
        result = manager.share_list(list_id, user2_id, "edit")
        # Verify sharing
        shares_result = manager.get_list_shares(list_id)
        if shares_result['count'] >= 1:
            print(f"   ✅ Shared list with user (edit permission)")
            passed += 1
        else:
            print(f"   ❌ List sharing failed")
            failed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed += 1

    # Test 3: Get shared lists
    print("\n3. Testing get shared lists...")
    try:
        result = manager.get_shared_lists(user2_id)
        if result['count'] >= 1:
            print(f"   ✅ User can see shared list")
            passed += 1
        else:
            print(f"   ❌ Shared list not visible")
            failed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed += 1

    print(f"\n{'='*60}")
    print(f"List Operations: {passed} passed, {failed} failed")
    return passed, failed


def test_mcp_parse_todo():
    """Test MCP parse_todo tool."""
    print("\n" + "="*60)
    print("Test 5: MCP parse_todo Tool")
    print("="*60)

    test_cases = [
        {
            "input": "Submit report by Friday 3pm @high #work #finance",
            "expected_title": "Submit report",
            "expected_priority": "high",
            "expected_tags": ["work", "finance"]
        },
        {
            "input": "Call mom tomorrow @low #personal",
            "expected_title": "Call mom",
            "expected_priority": "low"
        },
        {
            "input": "Team standup today 9am #team",
            "expected_title": "Team standup",
            "expected_bucket": "today"
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{test['input']}'")

        try:
            # Simulate MCP parse_todo tool call
            parsed = parse_natural_language(test['input'])

            checks_passed = True

            if 'expected_title' in test:
                if test['expected_title'] in parsed['title']:
                    print(f"   ✅ Title: '{parsed['title']}'")
                else:
                    print(f"   ❌ Title: Expected to contain '{test['expected_title']}', got '{parsed['title']}'")
                    checks_passed = False

            if 'expected_priority' in test:
                if parsed['priority'] == test['expected_priority']:
                    print(f"   ✅ Priority: {parsed['priority']}")
                else:
                    print(f"   ❌ Priority: Expected {test['expected_priority']}, got {parsed['priority']}")
                    checks_passed = False

            if 'expected_tags' in test:
                if set(parsed['tags']) == set(test['expected_tags']):
                    print(f"   ✅ Tags: {parsed['tags']}")
                else:
                    print(f"   ❌ Tags: Expected {test['expected_tags']}, got {parsed['tags']}")
                    checks_passed = False

            if 'expected_bucket' in test:
                if parsed['bucket'] == test['expected_bucket']:
                    print(f"   ✅ Bucket: {parsed['bucket']}")
                else:
                    print(f"   ❌ Bucket: Expected {test['expected_bucket']}, got {parsed['bucket']}")
                    checks_passed = False

            if checks_passed:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Parse Tool: {passed} passed, {failed} failed")
    return passed, failed


if __name__ == "__main__":
    try:
        total_passed = 0
        total_failed = 0

        # Run all test suites
        p, f = test_mcp_create_todo_natural_language()
        total_passed += p
        total_failed += f

        p, f = test_mcp_list_todos_with_filters()
        total_passed += p
        total_failed += f

        p, f = test_mcp_crud_operations()
        total_passed += p
        total_failed += f

        p, f = test_mcp_list_operations()
        total_passed += p
        total_failed += f

        p, f = test_mcp_parse_todo()
        total_passed += p
        total_failed += f

        # Final summary
        print("\n" + "="*60)
        print("PHASE 4 MCP INTEGRATION TEST SUMMARY")
        print("="*60)
        print(f"Total Tests Passed: {total_passed}")
        print(f"Total Tests Failed: {total_failed}")
        print(f"Success Rate: {(total_passed/(total_passed+total_failed)*100):.1f}%")
        print("="*60)

        if total_failed == 0:
            print("\n✅ All Phase 4 MCP tests passed!")
            print("\nMCP Tools Verified:")
            print("  ✅ create_todo (natural language & structured)")
            print("  ✅ list_todos (with filtering)")
            print("  ✅ get_todo")
            print("  ✅ update_todo")
            print("  ✅ complete_todo")
            print("  ✅ delete_todo")
            print("  ✅ create_list")
            print("  ✅ share_list")
            print("  ✅ parse_todo")
            print("\nTotal: 9 MCP tools ready for chat integration")
        else:
            print(f"\n⚠️  {total_failed} test(s) failed. Review output above.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
