#!/bin/bash

# Start only the MCP server
# Provides MCP protocol access for AI assistants

echo "🤖 Starting AgentAgentGo: MCPGuard (MCP Server Only)"

# Check if we're in the right directory
if [ ! -f "scripts/start_mcp_only.sh" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Load environment variables from .env (safely handle special characters)
if [ -f "backend/.env" ]; then
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        # Remove any quotes from the value and export
        value=$(echo "$value" | sed 's/^["\'\'']*//;s/["\'\'']*$//')
        export "$key=$value"
    done < backend/.env
fi

# Set default port if not defined
MCP_SERVER_PORT=${MCP_SERVER_PORT:-8016}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping MCP server..."
    if [ ! -z "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null || true
    fi
    exit
}
trap cleanup INT TERM

# Stop any existing services
./scripts/overall_shutdown.sh >/dev/null 2>&1 || true
sleep 1

# Check environment variables
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env file not found"
    echo "   Please create backend/.env with required environment variables:"
    echo "   SUPABASE_URL=your_supabase_url"
    echo "   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key"
    exit 1
fi

# Install fastmcp if not present
echo "📦 Checking dependencies..."
cd backend
if ! python3 -c "import fastmcp" 2>/dev/null; then
    echo "⚠️  fastmcp not found, installing..."
    pip3 install fastmcp>=0.2.0
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install fastmcp"
        exit 1
    fi
    echo "✅ fastmcp installed successfully"
fi

# Start MCP server with HTTP transport
echo "🤖 Starting MCP server with HTTP transport..."
python3 mcp_server.py --transport streamable-http --host 127.0.0.1 --port $MCP_SERVER_PORT --path /mcp > /tmp/mcp_server.log 2>&1 &
MCP_PID=$!

# Wait a moment for the server to start
sleep 3

# Check if the process is still running
if ! kill -0 $MCP_PID 2>/dev/null; then
    echo "❌ MCP server failed to start. Check logs:"
    cat /tmp/mcp_server.log
    exit 1
fi

echo "✅ MCP server started (PID $MCP_PID)"
cd ..

echo ""
echo "🎉 MCP server is running:"
echo "   Protocol:  Model Context Protocol (MCP)"
echo "   Transport: Streamable HTTP"
echo "   URL:       http://127.0.0.1:$MCP_SERVER_PORT/mcp"
echo "   Tools:     10+ AI tools for server discovery and security analysis"
echo ""
echo "🔧 Available MCP Tools:"
echo "   • search_mcp_servers        - Search and discover servers"
echo "   • get_server_details        - Get comprehensive server info"
echo "   • analyze_server_security   - Security analysis and scoring"
echo "   • recommend_servers         - AI-curated recommendations"
echo "   • analyze_custom_server     - Analyze any server URL"
echo "   • list_popular_servers      - Popular servers by GitHub stars"
echo "   • find_secure_servers       - High-security servers"
echo "   • start_server_discovery    - Discover new servers"
echo ""
echo "🤖 Connect your AI assistant to this MCP server to access these tools."
echo ""
echo "📝 View logs:"
echo "   tail -f /tmp/mcp_server.log"
echo ""
echo "🛑 Press Ctrl+C to stop the MCP server"

# Wait for user interrupt
wait $MCP_PID
