#!/bin/bash

# PyPI Clone Startup Script

echo "🚀 Starting PyPI Clone Server"
echo "=============================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Make scripts executable
chmod +x cli.py
chmod +x server.py
chmod +x test_server.py

# Start server
echo "🌟 Starting PyPI Clone server..."
echo "📍 Server will be available at: http://localhost:8080"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

python3 server.py
