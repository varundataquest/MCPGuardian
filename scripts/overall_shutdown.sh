#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Stopping AgentAgentGo: MCPGuard services..."

# Graceful shutdown first
pkill -f 'uvicorn app.main:app' >/dev/null 2>&1 || true
pkill -f 'next dev' >/dev/null 2>&1 || true
pkill -f 'mcp_server.py' >/dev/null 2>&1 || true
sleep 2

# Force cleanup if processes persist
if lsof -i :8015 >/dev/null 2>&1; then
    echo "🔨 Force-stopping backend processes on port 8015..."
    lsof -ti :8015 | xargs kill -9 2>/dev/null || true
fi

if lsof -i :3000 >/dev/null 2>&1; then
    echo "🔨 Force-stopping UI processes on port 3000..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
fi

# Clean up log files
rm -f /tmp/uvicorn8015.log /tmp/next3000.log /tmp/mcp_server.log 2>/dev/null || true

echo "✅ Stopped backend, UI, and MCP servers."

