#!/bin/bash

# Agentic UI Server Start Script
# Kills any process on port 9090 then starts the server

PORT=9090

echo "🔍 Checking for existing processes on port $PORT..."

# Find and kill any process using port 9090
PID=$(lsof -ti:$PORT 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "🛑 Found process $PID using port $PORT, killing it..."
    kill -9 $PID 2>/dev/null || true
    sleep 1
    
    # Double check
    PID_CHECK=$(lsof -ti:$PORT 2>/dev/null)
    if [ ! -z "$PID_CHECK" ]; then
        echo "⚠️  Warning: Process might still be running on port $PORT"
    else
        echo "✅ Port $PORT is now free"
    fi
else
    echo "✅ Port $PORT is available"
fi

echo ""
echo "🚀 Starting Agentic UI Server..."

# Try uv run first, fallback to python3
if command -v uv &> /dev/null; then
    echo "📦 Using uv run..."
    uv run server.py
else
    echo "🐍 uv not found, using python3..."
    python3 server.py
fi