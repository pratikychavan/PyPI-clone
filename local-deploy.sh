#!/bin/bash

# Local deployment script without Docker Hub dependencies

echo "🚀 Setting up PyPI Clone locally..."

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Install with: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "🔧 Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Create packages directory
mkdir -p packages

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  ./venv/bin/python server.py"
echo ""
echo "Or run in background:"
echo "  nohup ./venv/bin/python server.py > pypi.log 2>&1 &"
