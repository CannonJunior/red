#!/usr/bin/env python3
"""
Test script to verify Ollama robustness improvements work with the web application.
"""

import json
import urllib.request
import urllib.error
import sys

def test_server_endpoint(url, description):
    """Test a server endpoint and print results."""
    print(f"\n🧪 Testing {description}")
    print(f"   URL: {url}")
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"   ✅ Success ({response.status})")
            
            # Print relevant information based on endpoint
            if 'models' in data:
                print(f"   📋 Models: {data['models']}")
                if 'connection_attempt' in data:
                    print(f"   🔄 Connection attempts: {data['connection_attempt']}")
            elif 'response' in data:
                print(f"   🤖 Response: {data['response'][:50]}...")
                if 'connection_attempt' in data:
                    print(f"   🔄 Connection attempts: {data['connection_attempt']}")
            elif 'status' in data:
                print(f"   📊 Status: {data['status']}")
                if 'llm' in data and 'response_time' in data['llm']:
                    print(f"   ⏱️  Response time: {data['llm']['response_time']}s")
            else:
                print(f"   📄 Response keys: {list(data.keys())}")
            
            return True
            
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error {e.code}: {e.reason}")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print(f"   🔍 Error details: {error_data}")
        except:
            pass
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_chat_endpoint(message="Hello, test message"):
    """Test the chat endpoint with a simple message."""
    print(f"\n🧪 Testing Chat Endpoint")
    print(f"   Message: {message}")
    
    url = "http://localhost:9090/api/chat"
    data = {
        "message": message,
        "model": "qwen2.5:3b"
    }
    
    try:
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"   ✅ Success ({response.status})")
            print(f"   🤖 Response: {result.get('response', 'No response')[:100]}...")
            
            if 'connection_attempt' in result:
                print(f"   🔄 Connection attempts: {result['connection_attempt']}")
            if 'rag_enabled' in result:
                print(f"   📚 RAG enabled: {result['rag_enabled']}")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run comprehensive robustness tests."""
    print("🚀 Testing Ollama Robustness Improvements")
    print("=" * 50)
    
    # Test individual endpoints
    endpoints = [
        ("http://localhost:9090/api/models", "Models API"),
        ("http://localhost:9090/api/rag/status", "RAG Status API"),
    ]
    
    success_count = 0
    total_tests = len(endpoints) + 1  # +1 for chat test
    
    # Test GET endpoints
    for url, description in endpoints:
        if test_server_endpoint(url, description):
            success_count += 1
    
    # Test chat endpoint (POST)
    if test_chat_endpoint():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {success_count}/{total_tests} passed")
    
    if success_count == total_tests:
        print("🎉 All Ollama robustness tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check server logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())