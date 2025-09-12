#!/usr/bin/env python3
"""
Test script to debug RAG source count display issue.
This will help identify if the problem is in the backend or frontend.
"""

import json
import urllib.request
import urllib.error
import sys

def test_chat_with_rag(message="What is artificial intelligence?"):
    """Test chat endpoint and examine the response structure."""
    print(f"🧪 Testing Chat with RAG")
    print(f"   Message: {message}")
    
    url = "http://localhost:9090/api/chat"
    data = {
        "message": message,
        "model": "qwen2.5:3b"  # Will use dynamic selection
    }
    
    try:
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"   ✅ Success ({response.status})")
            
            # Print full response structure for debugging
            print(f"   📄 Full response structure:")
            for key, value in result.items():
                if key == 'response':
                    print(f"      {key}: {str(value)[:50]}...")
                else:
                    print(f"      {key}: {value}")
            
            # Specifically check RAG-related fields
            print(f"\n   🔍 RAG Analysis:")
            print(f"      rag_enabled: {result.get('rag_enabled', 'NOT_PRESENT')}")
            print(f"      sources_used: {result.get('sources_used', 'NOT_PRESENT')}")
            
            # Check if sources_used is the right type
            sources_used = result.get('sources_used')
            if sources_used is not None:
                print(f"      sources_used type: {type(sources_used)}")
                print(f"      sources_used > 0: {sources_used > 0}")
            
            return result
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    """Run RAG source count debugging tests."""
    print("🔍 Testing RAG Source Count Display")
    print("=" * 50)
    
    # Test with a question that should use RAG if documents are available
    result = test_chat_with_rag("What is artificial intelligence?")
    
    if result:
        print(f"\n📊 Summary:")
        rag_enabled = result.get('rag_enabled', False)
        sources_used = result.get('sources_used', 0)
        
        print(f"   RAG Enabled: {rag_enabled}")
        print(f"   Sources Used: {sources_used}")
        
        if rag_enabled and sources_used > 0:
            print(f"   🎉 RAG working correctly with {sources_used} sources")
        elif rag_enabled and sources_used == 0:
            print(f"   ⚠️  RAG enabled but no sources used")
        else:
            print(f"   📝 RAG not enabled or no documents available")
            
        # Test what the frontend would receive
        print(f"\n   🖥️  Frontend would display:")
        if rag_enabled:
            if sources_used > 0:
                print(f"      'RAG Enhanced • {sources_used} sources'")
            else:
                print(f"      'RAG Enhanced'")
        else:
            print(f"      No RAG indicator")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())