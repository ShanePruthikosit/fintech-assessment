#!/bin/bash

# SimuVest Demo Startup Script
# This script starts the backend server for the demo

echo "🚀 Starting SimuVest Demo..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create data directory
mkdir -p /home/claude/simuvest/data

# Install dependencies
echo "📦 Installing Python dependencies..."
cd /home/claude/simuvest/backend
pip install --break-system-packages -q -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Start the backend
echo "🔧 Starting FastAPI backend on port 8000..."
echo "📊 API Documentation: http://localhost:8000/docs"
echo "🌐 Frontend: Open frontend/index.html in your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 main.py
