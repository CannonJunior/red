"""Test script for TODO API Phase 3 - Natural Language Processing.

This test suite validates the NLP parser's ability to extract:
- Dates (today, tomorrow, weekdays, relative days, ISO dates)
- Times (3pm, 12:00, 3:00 pm, etc.)
- Priority markers (@high, @urgent, !, !!)
- Tags (#tag, #work, etc.)
- Bucket determination
- Title extraction and cleanup
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:9090/api/todos"


def get_next_weekday_date(weekday_name):
    """Calculate the next occurrence of a weekday."""
    weekdays = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    target_weekday = weekdays[weekday_name.lower()]
    today = datetime.now()
    current_weekday = today.weekday()
    days_ahead = target_weekday - current_weekday
    if days_ahead <= 0:
        days_ahead += 7
    next_date = today + timedelta(days=days_ahead)
    return next_date.strftime('%Y-%m-%d')


def test_nlp_date_extraction():
    """Test date extraction from natural language."""
    print("\n" + "="*60)
    print("Phase 3 NLP Test - Date Extraction")
    print("="*60)

    test_cases = [
        {
            "input": "Call mom today",
            "expected_date": datetime.now().strftime('%Y-%m-%d'),
            "expected_title": "Call mom",
            "name": "Today"
        },
        {
            "input": "Submit report tomorrow",
            "expected_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            "expected_title": "Submit report",
            "name": "Tomorrow"
        },
        {
            "input": "Team meeting next week",
            "expected_date": (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d'),
            "expected_title": "Team meeting",
            "name": "Next week"
        },
        {
            "input": "Review PR in 3 days",
            "expected_date": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
            "expected_title": "Review PR",
            "name": "In 3 days"
        },
        {
            "input": "Doctor appointment on Friday",
            "expected_date": get_next_weekday_date("Friday"),
            "expected_title": "Doctor appointment",
            "name": "Weekday (Friday)"
        },
        {
            "input": "Task scheduled for 2025-12-25",
            "expected_date": "2025-12-25",
            "expected_title": "Task scheduled for",
            "name": "ISO date"
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['name']}")
        print(f"   Input: '{test['input']}'")

        response = requests.post(f"{BASE_URL}/parse", json={
            "input": test['input']
        }).json()

        if response['status'] == 'success':
            parsed = response['parsed']
            if parsed['due_date'] == test['expected_date']:
                print(f"   ✅ Date: {parsed['due_date']}")
                passed += 1
            else:
                print(f"   ❌ Date: Expected {test['expected_date']}, got {parsed['due_date']}")
                failed += 1

            if test['expected_title'] in parsed['title']:
                print(f"   ✅ Title: '{parsed['title']}'")
            else:
                print(f"   ⚠️  Title: '{parsed['title']}' (expected to contain '{test['expected_title']}')")
        else:
            print(f"   ❌ Error: {response.get('message')}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Date Extraction: {passed} passed, {failed} failed")
    return passed, failed


def test_nlp_time_extraction():
    """Test time extraction from natural language."""
    print("\n" + "="*60)
    print("Phase 3 NLP Test - Time Extraction")
    print("="*60)

    test_cases = [
        {
            "input": "Meeting at 3pm",
            "expected_time": "15:00",
            "name": "Simple PM time"
        },
        {
            "input": "Breakfast at 8am",
            "expected_time": "08:00",
            "name": "Simple AM time"
        },
        {
            "input": "Call at 2:30 pm",
            "expected_time": "14:30",
            "name": "Time with minutes PM"
        },
        {
            "input": "Standup at 9:15 am",
            "expected_time": "09:15",
            "name": "Time with minutes AM"
        },
        {
            "input": "Deadline 11:59 pm",
            "expected_time": "23:59",
            "name": "Late night time"
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['name']}")
        print(f"   Input: '{test['input']}'")

        response = requests.post(f"{BASE_URL}/parse", json={
            "input": test['input']
        }).json()

        if response['status'] == 'success':
            parsed = response['parsed']
            if parsed['due_time'] == test['expected_time']:
                print(f"   ✅ Time: {parsed['due_time']}")
                passed += 1
            else:
                print(f"   ❌ Time: Expected {test['expected_time']}, got {parsed['due_time']}")
                failed += 1
        else:
            print(f"   ❌ Error: {response.get('message')}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Time Extraction: {passed} passed, {failed} failed")
    return passed, failed


def test_nlp_priority_extraction():
    """Test priority marker extraction from natural language."""
    print("\n" + "="*60)
    print("Phase 3 NLP Test - Priority Extraction")
    print("="*60)

    test_cases = [
        {"input": "Important task @high", "expected": "high", "name": "@high marker"},
        {"input": "Critical bug @urgent", "expected": "urgent", "name": "@urgent marker"},
        {"input": "Simple task @low", "expected": "low", "name": "@low marker"},
        {"input": "Normal task @medium", "expected": "medium", "name": "@medium marker"},
        {"input": "Emergency fix !!", "expected": "urgent", "name": "!! marker"},
        {"input": "Priority task !", "expected": "high", "name": "! marker"},
        {"input": "Regular task", "expected": "medium", "name": "No marker (default)"}
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['name']}")
        print(f"   Input: '{test['input']}'")

        response = requests.post(f"{BASE_URL}/parse", json={
            "input": test['input']
        }).json()

        if response['status'] == 'success':
            parsed = response['parsed']
            if parsed['priority'] == test['expected']:
                print(f"   ✅ Priority: {parsed['priority']}")
                passed += 1
            else:
                print(f"   ❌ Priority: Expected {test['expected']}, got {parsed['priority']}")
                failed += 1
        else:
            print(f"   ❌ Error: {response.get('message')}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Priority Extraction: {passed} passed, {failed} failed")
    return passed, failed


def test_nlp_tag_extraction():
    """Test tag extraction from natural language."""
    print("\n" + "="*60)
    print("Phase 3 NLP Test - Tag Extraction")
    print("="*60)

    test_cases = [
        {"input": "Buy groceries #personal", "expected": ["personal"], "name": "Single tag"},
        {"input": "Fix bug #work #urgent", "expected": ["work", "urgent"], "name": "Multiple tags"},
        {"input": "Project update #team #sprint1 #review", "expected": ["team", "sprint1", "review"], "name": "Three tags"},
        {"input": "Simple task", "expected": [], "name": "No tags"}
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['name']}")
        print(f"   Input: '{test['input']}'")

        response = requests.post(f"{BASE_URL}/parse", json={
            "input": test['input']
        }).json()

        if response['status'] == 'success':
            parsed = response['parsed']
            if set(parsed['tags']) == set(test['expected']):
                print(f"   ✅ Tags: {parsed['tags']}")
                passed += 1
            else:
                print(f"   ❌ Tags: Expected {test['expected']}, got {parsed['tags']}")
                failed += 1
        else:
            print(f"   ❌ Error: {response.get('message')}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Tag Extraction: {passed} passed, {failed} failed")
    return passed, failed


def test_nlp_complex_parsing():
    """Test complex inputs with multiple features."""
    print("\n" + "="*60)
    print("Phase 3 NLP Test - Complex Parsing")
    print("="*60)

    test_cases = [
        {
            "input": "Submit quarterly report by Friday 3pm @high #work #finance",
            "expected": {
                "title_contains": "Submit quarterly report",
                "priority": "high",
                "tags": ["work", "finance"],
                "has_date": True,
                "has_time": True,
                "time": "15:00"
            },
            "name": "Full featured input"
        },
        {
            "input": "Call mom tomorrow @low #personal",
            "expected": {
                "title_contains": "Call mom",
                "priority": "low",
                "tags": ["personal"],
                "has_date": True,
                "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            },
            "name": "Date + priority + tag"
        },
        {
            "input": "Team standup today 9am #team",
            "expected": {
                "title_contains": "Team standup",
                "tags": ["team"],
                "has_date": True,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "has_time": True,
                "time": "09:00",
                "bucket": "today"
            },
            "name": "Today + time + tag + bucket"
        }
    ]

    passed = 0
    failed = 0
    total_checks = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['name']}")
        print(f"   Input: '{test['input']}'")

        response = requests.post(f"{BASE_URL}/parse", json={
            "input": test['input']
        }).json()

        if response['status'] == 'success':
            parsed = response['parsed']
            test_passed = True

            # Check title
            if 'title_contains' in test['expected']:
                if test['expected']['title_contains'] in parsed['title']:
                    print(f"   ✅ Title: '{parsed['title']}'")
                else:
                    print(f"   ❌ Title: Expected to contain '{test['expected']['title_contains']}', got '{parsed['title']}'")
                    test_passed = False
                total_checks += 1

            # Check priority
            if 'priority' in test['expected']:
                if parsed['priority'] == test['expected']['priority']:
                    print(f"   ✅ Priority: {parsed['priority']}")
                else:
                    print(f"   ❌ Priority: Expected {test['expected']['priority']}, got {parsed['priority']}")
                    test_passed = False
                total_checks += 1

            # Check tags
            if 'tags' in test['expected']:
                if set(parsed['tags']) == set(test['expected']['tags']):
                    print(f"   ✅ Tags: {parsed['tags']}")
                else:
                    print(f"   ❌ Tags: Expected {test['expected']['tags']}, got {parsed['tags']}")
                    test_passed = False
                total_checks += 1

            # Check date
            if 'has_date' in test['expected'] and test['expected']['has_date']:
                if parsed['due_date']:
                    if 'date' in test['expected']:
                        if parsed['due_date'] == test['expected']['date']:
                            print(f"   ✅ Date: {parsed['due_date']}")
                        else:
                            print(f"   ❌ Date: Expected {test['expected']['date']}, got {parsed['due_date']}")
                            test_passed = False
                    else:
                        print(f"   ✅ Date: {parsed['due_date']}")
                else:
                    print(f"   ❌ Date: Expected date but got None")
                    test_passed = False
                total_checks += 1

            # Check time
            if 'has_time' in test['expected'] and test['expected']['has_time']:
                if parsed['due_time']:
                    if 'time' in test['expected']:
                        if parsed['due_time'] == test['expected']['time']:
                            print(f"   ✅ Time: {parsed['due_time']}")
                        else:
                            print(f"   ❌ Time: Expected {test['expected']['time']}, got {parsed['due_time']}")
                            test_passed = False
                    else:
                        print(f"   ✅ Time: {parsed['due_time']}")
                else:
                    print(f"   ❌ Time: Expected time but got None")
                    test_passed = False
                total_checks += 1

            # Check bucket
            if 'bucket' in test['expected']:
                if parsed['bucket'] == test['expected']['bucket']:
                    print(f"   ✅ Bucket: {parsed['bucket']}")
                else:
                    print(f"   ❌ Bucket: Expected {test['expected']['bucket']}, got {parsed['bucket']}")
                    test_passed = False
                total_checks += 1

            if test_passed:
                passed += 1
            else:
                failed += 1

        else:
            print(f"   ❌ Error: {response.get('message')}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Complex Parsing: {passed}/{len(test_cases)} tests passed")
    return passed, failed


def test_nlp_todo_creation():
    """Test creating todos using natural language input."""
    print("\n" + "="*60)
    print("Phase 3 NLP Test - Todo Creation with NLP")
    print("="*60)

    # Create a test user
    print("\n1. Creating test user...")
    import uuid
    username = f"nlp_test_{str(uuid.uuid4())[:8]}"
    user_response = requests.post(f"{BASE_URL}/users", json={
        "username": username,
        "email": f"{username}@test.com",
        "display_name": "NLP Test User"
    }).json()

    if user_response['status'] != 'success':
        print(f"❌ Failed to create user: {user_response.get('message')}")
        return 0, 1

    user_id = user_response['user']['id']
    print(f"✅ User created: {user_id[:8]}...")

    # Test creating todos with NLP
    test_cases = [
        {
            "input": "Buy groceries tomorrow @high #personal",
            "name": "Simple NLP todo"
        },
        {
            "input": "Team meeting Friday 2pm @urgent #work",
            "name": "Date + time + priority + tag"
        },
        {
            "input": "Review code today !! #development #review",
            "name": "Today + !! priority + multiple tags"
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i+1}. Creating: {test['name']}")
        print(f"   Input: '{test['input']}'")

        response = requests.post(BASE_URL, json={
            "user_id": user_id,
            "input": test['input']
        }).json()

        if response['status'] == 'success':
            todo = response['todo']
            print(f"   ✅ Created: '{todo['title']}'")
            print(f"      - Priority: {todo['priority']}")
            print(f"      - Tags: {todo['tags']}")
            print(f"      - Due date: {todo.get('due_date', 'None')}")
            print(f"      - Due time: {todo.get('due_time', 'None')}")
            print(f"      - Bucket: {todo['bucket']}")
            passed += 1
        else:
            print(f"   ❌ Failed: {response.get('message')}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Todo Creation: {passed} passed, {failed} failed")
    return passed, failed


if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("TODO API Phase 3 - NLP Test Suite")
        print("="*60)

        total_passed = 0
        total_failed = 0

        # Run all test suites
        p, f = test_nlp_date_extraction()
        total_passed += p
        total_failed += f

        p, f = test_nlp_time_extraction()
        total_passed += p
        total_failed += f

        p, f = test_nlp_priority_extraction()
        total_passed += p
        total_failed += f

        p, f = test_nlp_tag_extraction()
        total_passed += p
        total_failed += f

        p, f = test_nlp_complex_parsing()
        total_passed += p
        total_failed += f

        p, f = test_nlp_todo_creation()
        total_passed += p
        total_failed += f

        # Final summary
        print("\n" + "="*60)
        print("PHASE 3 NLP TEST SUMMARY")
        print("="*60)
        print(f"Total Tests Passed: {total_passed}")
        print(f"Total Tests Failed: {total_failed}")
        print(f"Success Rate: {(total_passed/(total_passed+total_failed)*100):.1f}%")
        print("="*60)

        if total_failed == 0:
            print("\n✅ All Phase 3 NLP tests passed!")
        else:
            print(f"\n⚠️  {total_failed} test(s) failed. Review output above.")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("Make sure the server is running on http://localhost:9090")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
