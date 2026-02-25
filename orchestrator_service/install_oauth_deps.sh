#!/bin/bash
echo "🔧 Installing OAuth testing dependencies..."

# Install Python dependencies
pip3 install fastapi==0.104.1
pip3 install httpx==0.25.1
pip3 install pytest==7.4.3
pip3 install pytest-asyncio==0.21.1
pip3 install pytest-httpx==0.27.0

echo "✅ Dependencies installed successfully!"
echo ""
echo "📋 To run OAuth tests:"
echo "   cd /home/node/.openclaw/workspace/projects/crmventas/orchestrator_service"
echo "   python3 test_meta_oauth.py"
echo ""
echo "📋 To run all marketing tests:"
echo "   python3 -m pytest tests/test_marketing_backend.py -v"