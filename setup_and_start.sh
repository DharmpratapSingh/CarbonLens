#!/bin/bash
# ClimateGPT Setup and Startup Helper Script
# ==========================================

set -e

echo "🌍 ClimateGPT Setup and Startup Helper"
echo "======================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Creating template .env file..."
    echo "⚠️  You MUST edit .env and set OPENAI_API_KEY=your_username:your_password"
    echo ""
    exit 1
fi

# Load environment variables
echo "📋 Loading environment variables from .env..."
export $(cat .env | grep -v '^#' | grep -v '^\s*$' | xargs)

# Validate required environment variables
echo "🔍 Validating environment configuration..."

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" == "your_username:your_password" ]; then
    echo "❌ OPENAI_API_KEY is not set or is still the template value!"
    echo "📝 Please edit .env and set OPENAI_API_KEY=your_username:your_password"
    echo "   Get your credentials from: https://erasmus.ai"
    exit 1
fi

if [[ ! "$OPENAI_API_KEY" == *":"* ]]; then
    echo "❌ OPENAI_API_KEY must be in format 'username:password'"
    echo "   Current value does not contain ':' separator"
    exit 1
fi

echo "✅ OPENAI_API_KEY is set correctly"
echo "✅ OPENAI_BASE_URL: ${OPENAI_BASE_URL:-https://erasmus.ai/models/climategpt_8b_test/v1}"
echo "✅ MCP_URL: ${MCP_URL:-http://127.0.0.1:8010}"
echo ""

# Check Python dependencies
echo "🔍 Checking Python dependencies..."
python -c "
import sys
try:
    import streamlit
    import requests
    import fastapi
    import pandas
    import altair
    print('✅ All required Python packages are installed')
except ImportError as e:
    print(f'❌ Missing Python package: {e}')
    print('Run: pip install streamlit requests fastapi pandas altair python-dotenv uvicorn')
    sys.exit(1)
" || exit 1

echo ""

# Check if services are already running
if curl -s http://localhost:8010/health > /dev/null 2>&1; then
    echo "⚠️  MCP Bridge already running on port 8010"
    echo "   Use 'pkill -f mcp_http_bridge' to stop it first"
    exit 1
fi

if lsof -ti:8501 > /dev/null 2>&1; then
    echo "⚠️  Streamlit already running on port 8501"
    echo "   Use 'pkill -f streamlit' to stop it first"
    exit 1
fi

# Clear Python cache
echo "🧹 Clearing Python cache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "🚀 Starting ClimateGPT Application..."
echo "======================================"
echo ""

# Start MCP HTTP Bridge (wraps mcp_server_stdio.py)
echo "📡 Starting MCP Bridge Server on port 8010..."
python mcp_http_bridge.py > logs/mcp_bridge.log 2>&1 &
MCP_PID=$!
echo "   PID: $MCP_PID"

# Wait for MCP Server to initialize
echo "⏳ Waiting for MCP Bridge to initialize..."
sleep 3

# Check if MCP Bridge is healthy
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8010/health > /dev/null 2>&1; then
        echo "✅ MCP Bridge started successfully (using TRUE MCP protocol)"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   Retry $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ MCP Bridge failed to start"
    echo "   Check logs/mcp_bridge.log for details"
    kill $MCP_PID 2>/dev/null || true
    exit 1
fi

echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Streamlit App
echo "🌐 Starting Streamlit App on port 8501..."
echo "   Log file: logs/streamlit.log"
streamlit run enhanced_climategpt_with_personas.py > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "   PID: $STREAMLIT_PID"

echo ""
echo "✅ ClimateGPT Application Started Successfully!"
echo "=============================================="
echo ""
echo "📊 Services:"
echo "   - MCP Bridge:    http://localhost:8010/health"
echo "   - Streamlit UI:  http://localhost:8501"
echo ""
echo "📝 Process IDs:"
echo "   - MCP Bridge: $MCP_PID"
echo "   - Streamlit:  $STREAMLIT_PID"
echo ""
echo "📋 Logs:"
echo "   - MCP Bridge: logs/mcp_bridge.log"
echo "   - Streamlit:  logs/streamlit.log"
echo ""
echo "🛑 To stop:"
echo "   pkill -f mcp_http_bridge"
echo "   pkill -f streamlit"
echo ""
echo "🌍 Open http://localhost:8501 in your browser to use ClimateGPT!"
echo ""

# Cleanup on Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $MCP_PID $STREAMLIT_PID 2>/dev/null; echo '✅ Stopped'; exit 0" SIGINT SIGTERM

# Keep script running to maintain services
echo "💡 Press Ctrl+C to stop all services"
wait
