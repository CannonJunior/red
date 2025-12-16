"""Test script for TODO API endpoints."""

import requests
import json

BASE_URL = "http://localhost:9090/api/todos"


def test_create_user():
    """Test creating a user."""
    print("\n1. Creating user...")
    response = requests.post(f"{BASE_URL}/users", json={
        "username": "testuser",
        "email": "test@example.com",
        "display_name": "Test User"
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data.get('user', {}).get('id')


def test_create_list(user_id):
    """Test creating a todo list."""
    print("\n2. Creating todo list...")
    response = requests.post(f"{BASE_URL}/lists", json={
        "user_id": user_id,
        "name": "Work Tasks",
        "description": "Tasks for work projects",
        "color": "#3B82F6"
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data.get('list', {}).get('id')


def test_create_todo(user_id, list_id):
    """Test creating a todo."""
    print("\n3. Creating todo...")
    response = requests.post(BASE_URL, json={
        "user_id": user_id,
        "list_id": list_id,
        "title": "Complete project documentation",
        "description": "Write comprehensive docs for the TODO API",
        "priority": "high",
        "bucket": "today",
        "tags": ["work", "documentation"]
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data.get('todo', {}).get('id')


def test_list_todos(user_id):
    """Test listing todos."""
    print("\n4. Listing todos...")
    response = requests.get(BASE_URL, json={
        "user_id": user_id
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")


def test_create_tag(user_id):
    """Test creating a tag."""
    print("\n5. Creating tag...")
    response = requests.post(f"{BASE_URL}/tags", json={
        "user_id": user_id,
        "name": "urgent",
        "color": "#EF4444"
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")


def test_complete_todo(todo_id, user_id):
    """Test completing a todo."""
    print("\n6. Completing todo...")
    response = requests.post(f"{BASE_URL}/{todo_id}/complete", json={
        "user_id": user_id
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")


def test_get_today_todos(user_id):
    """Test getting today's todos."""
    print("\n7. Getting today's todos...")
    response = requests.get(f"{BASE_URL}/today", json={
        "user_id": user_id
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")


def main():
    """Run all tests."""
    print("="*50)
    print("TODO API Test Suite")
    print("="*50)

    try:
        # Test user creation
        user_id = test_create_user()
        if not user_id:
            print("❌ Failed to create user")
            return

        # Test list creation
        list_id = test_create_list(user_id)
        if not list_id:
            print("❌ Failed to create list")
            return

        # Test todo creation
        todo_id = test_create_todo(user_id, list_id)
        if not todo_id:
            print("❌ Failed to create todo")
            return

        # Test listing todos
        test_list_todos(user_id)

        # Test tag creation
        test_create_tag(user_id)

        # Test completing todo
        test_complete_todo(todo_id, user_id)

        # Test getting today's todos
        test_get_today_todos(user_id)

        print("\n" + "="*50)
        print("✅ All tests completed!")
        print("="*50)

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("Make sure the server is running on http://localhost:9090")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
