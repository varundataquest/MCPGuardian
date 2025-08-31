#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

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

# Set default ports if not defined
BACKEND_PORT=${BACKEND_PORT:-8015}
MCP_SERVER_PORT=${MCP_SERVER_PORT:-8016}
UI_PORT=${UI_PORT:-3000}

echo "🧹 Cleaning up old processes..."

# Kill old processes more thoroughly
pkill -f 'uvicorn app.main:app' >/dev/null 2>&1 || true
pkill -f 'next dev' >/dev/null 2>&1 || true

# Check for port conflicts and resolve them
if lsof -i :$BACKEND_PORT >/dev/null 2>&1; then
    echo "⚠️  Port $BACKEND_PORT in use, attempting to free it..."
    lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    sleep 1
fi

if lsof -i :$UI_PORT >/dev/null 2>&1; then
    echo "⚠️  Port $UI_PORT in use, attempting to free it..."  
    lsof -ti :$UI_PORT | xargs kill -9 2>/dev/null || true
    sleep 1
fi

sleep 0.5

# Backend
echo "🐍 Setting up Python environment..."
if [ ! -d .venv ]; then
  # Check Python version - FastMCP requires Python 3.10+
  PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
  PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
  PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
  
  if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; then
    echo "⚠️  Warning: Python 3.10+ required for FastMCP (found $PYTHON_VERSION)"
    echo "   Attempting to use python3.10..."
    if command -v python3.10 >/dev/null 2>&1; then
      python3.10 -m venv .venv
      echo "✅ Using python3.10"
    elif command -v python3.11 >/dev/null 2>&1; then
      python3.11 -m venv .venv
      echo "✅ Using python3.11"
    elif command -v python3.12 >/dev/null 2>&1; then
      python3.12 -m venv .venv
      echo "✅ Using python3.12"
    else
      echo "❌ Error: No Python 3.10+ found. Please install Python 3.10 or higher."
      echo "   brew install python@3.10"
      exit 1
    fi
  else
    python3 -m venv .venv
    echo "✅ Using python3 ($PYTHON_VERSION)"
  fi
fi
source .venv/bin/activate
echo "📦 Installing dependencies..."
pip install -r backend/requirements.txt >/dev/null 2>&1 || {
  echo "❌ Failed to install dependencies. Check backend/requirements.txt"
  exit 1
}
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --port $BACKEND_PORT >/tmp/uvicorn$BACKEND_PORT.log 2>&1 &
BACK_PID=$!

echo "🚀 Backend started (PID $BACK_PID) -> http://localhost:$BACKEND_PORT"

# Wait for backend to be ready
echo "⏳ Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/admin/crawl/status >/dev/null 2>&1; then
        echo "✅ Backend is responding"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start (timeout after 30s)"
        echo "Check logs: tail -f /tmp/uvicorn$BACKEND_PORT.log"
        exit 1
    fi
done

# UI
echo "🎨 Starting UI..."
cd ui

# Check Node.js availability and fix common issues
if ! command -v node >/dev/null 2>&1; then
  echo "❌ Error: Node.js not found. Please install Node.js:"
  echo "   brew install node@20"
  exit 1
fi

# Check for Node.js ICU4C issues (common on macOS)
if ! node --version >/dev/null 2>&1; then
  echo "⚠️  Node.js has library issues. Trying Node@20..."
  if command -v /opt/homebrew/opt/node@20/bin/node >/dev/null 2>&1; then
    export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
    echo "✅ Using Node@20 to fix library issues"
  else
    echo "❌ Error: Node.js library issues detected. Install Node@20:"
    echo "   brew install node@20"
    exit 1
  fi
fi

NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
echo "🟢 Using Node.js $NODE_VERSION"

# Install dependencies with better error handling
echo "📦 Installing UI dependencies..."
if command -v pnpm >/dev/null 2>&1; then
  pnpm install --silent >/dev/null 2>&1 || {
    echo "⚠️  pnpm install failed, trying npm..."
    npm install --silent >/dev/null 2>&1 || {
      echo "❌ UI dependencies installation failed"
      echo "   Try manually: cd ui && npm install"
    }
  }
  NEXT_PUBLIC_API_BASE=http://localhost:$BACKEND_PORT pnpm dev --port $UI_PORT >/tmp/next$UI_PORT.log 2>&1 &
else
  npm install --silent >/dev/null 2>&1 || {
    echo "❌ UI dependencies installation failed"
    echo "   Try manually: cd ui && npm install"
  }
  NEXT_PUBLIC_API_BASE=http://localhost:$BACKEND_PORT npm run dev -- --port $UI_PORT >/tmp/next$UI_PORT.log 2>&1 &
fi
UI_PID=$!

echo "🎨 UI started (PID $UI_PID) -> http://localhost:$UI_PORT"

# Wait for UI to be ready
echo "⏳ Waiting for UI to start..."
for i in {1..20}; do
    if curl -s http://localhost:$UI_PORT >/dev/null 2>&1; then
        echo "✅ UI is responding"
        break
    fi
    sleep 1
done

# MCP Server
echo "🤖 Starting MCP server..."
cd "$ROOT_DIR"

# Check if fastmcp is installed and install from GitHub if needed
if ! .venv/bin/python -c "import fastmcp" 2>/dev/null; then
    echo "📦 Installing FastMCP from GitHub (requires Python 3.10+)..."
    .venv/bin/pip install git+https://github.com/jlowin/fastmcp.git >/dev/null 2>&1 || {
        echo "❌ Failed to install FastMCP. This usually means Python < 3.10"
        echo "   FastMCP requires Python 3.10+. Current: $(.venv/bin/python --version)"
        echo "   Please install Python 3.10+ and restart"
        exit 1
    }
    echo "✅ FastMCP installed successfully"
fi

# Start MCP server using threading approach to avoid event loop conflicts  
cd "$ROOT_DIR/backend"

# Create a simple MCP server runner script
cat > /tmp/run_mcp_server.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
import subprocess

# Add the backend directory to the path  
sys.path.insert(0, os.getcwd())

def main():
    try:
        print('🤖 Starting MCP server with HTTP transport...', flush=True)
        # Use subprocess to run with HTTP transport arguments
        result = subprocess.run([
            sys.executable, 'mcp_server.py', 
            '--transport', 'streamable-http',
            '--host', '127.0.0.1',
            '--port', os.environ.get('MCP_SERVER_PORT', '8016'), 
            '--path', '/mcp'
        ], cwd=os.getcwd())
        sys.exit(result.returncode)
    except Exception:
        # Silent fail - don't print errors as stdout might be closed
        sys.exit(1)

if __name__ == '__main__':
    main()
EOF

PYTHONPATH=. "$ROOT_DIR/.venv/bin/python" /tmp/run_mcp_server.py >/tmp/mcp_server.log 2>&1 &
MCP_PID=$!

# Give MCP server a moment to start
sleep 3

if kill -0 $MCP_PID 2>/dev/null; then
    echo "🤖 MCP server started (PID $MCP_PID) -> http://127.0.0.1:$MCP_SERVER_PORT/mcp"
    MCP_STATUS="✅ Running (HTTP)"
else
    echo "⚠️  MCP server failed to start (check /tmp/mcp_server.log)"
    MCP_STATUS="❌ Failed" 
fi

cd "$ROOT_DIR"

echo ""
echo "🎉 Services are running:"
echo "   Backend:     http://localhost:$BACKEND_PORT"
echo "   UI:          http://localhost:$UI_PORT"
echo "   Admin:       http://localhost:$UI_PORT/admin"
echo "   MCP Server:  $MCP_STATUS"
echo ""
echo "🤖 MCP Tools Available:"
echo "   • search_mcp_servers        • recommend_servers"
echo "   • get_server_details        • analyze_custom_server"
echo "   • analyze_server_security   • find_secure_servers"
echo "   • list_popular_servers      • start_server_discovery"
echo ""
echo "📊 Test connectivity:"
echo "   curl http://localhost:$BACKEND_PORT/admin/crawl/status"
echo ""
echo "🎯 Usage Modes:"
echo "   🌐 Browser:     Open http://localhost:$UI_PORT"
echo "   🤖 MCP Client:  Connect to http://127.0.0.1:$MCP_SERVER_PORT/mcp"
echo "   🔧 API:         Direct REST API at http://localhost:$BACKEND_PORT"
echo ""
echo "📝 View logs:"
echo "   tail -f /tmp/uvicorn$BACKEND_PORT.log /tmp/next$UI_PORT.log /tmp/mcp_server.log"
echo ""
echo "🔧 Troubleshooting:"
echo "   • UI issues: Check Node.js version (need 18+) and try 'cd ui && npm install'"
echo "   • Backend issues: Ensure Python 3.10+ and Supabase credentials in backend/.env"
echo "   • Port conflicts: Run './scripts/overall_shutdown.sh' first"
echo "   • FastMCP issues: Requires Python 3.10+, install with 'brew install python@3.10'"
