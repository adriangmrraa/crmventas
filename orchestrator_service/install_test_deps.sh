#!/bin/bash
# Install minimal dependencies for testing

echo "🔧 Installing minimal test dependencies..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv --without-pip
    source venv/bin/activate
    
    # Install pip manually
    curl -sS https://bootstrap.pypa.io/get-pip.py | python
else
    source venv/bin/activate
fi

echo "📥 Installing FastAPI and dependencies..."
pip install fastapi==0.104.1
pip install uvicorn==0.24.0
pip install pydantic==2.5.0
pip install httpx==0.25.1
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1

echo "✅ Dependencies installed!"
echo ""
echo "To activate virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests:"
echo "  python test_endpoints_quick.py"