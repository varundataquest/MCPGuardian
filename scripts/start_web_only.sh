#!/bin/bash

# Start only the web stack (FastAPI + Next.js UI)
# This is the original functionality

echo "🌐 Starting AgentAgentGo: MCPGuard (Web Only Mode)"

# Check if we're in the right directory
if [ ! -f "scripts/start_web_only.sh" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$UI_PID" ]; then
        kill $UI_PID 2>/dev/null || true
    fi
    exit
}
trap cleanup INT TERM

# Stop existing services
./scripts/overall_shutdown.sh >/dev/null 2>&1 || true
sleep 1

# Start backend
echo "🚀 Starting backend server..."
cd backend
export NEXT_PUBLIC_API_BASE=http://localhost:8015
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8015 --reload > /tmp/uvicorn8015.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8015/servers >/dev/null 2>&1; then
        echo "✅ Backend is responding"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start after 30 seconds"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Start UI
echo "🎨 Starting UI..."
cd ui
export NEXT_PUBLIC_API_BASE=http://localhost:8015
npm run dev > /tmp/next3000.log 2>&1 &
UI_PID=$!
cd ..

# Wait for UI to start
echo "⏳ Waiting for UI to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "✅ UI is responding"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ UI failed to start after 30 seconds"
        kill $BACKEND_PID $UI_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

echo ""
echo "🎉 Web services are running:"
echo "   UI:        http://localhost:3000"
echo "   Admin:     http://localhost:3000/admin"
echo "   Backend:   http://localhost:8015"
echo ""
echo "📊 Test connectivity:"
echo "   curl http://localhost:8015/servers"
echo ""
echo "📝 View logs:"
echo "   tail -f /tmp/uvicorn8015.log /tmp/next3000.log"
echo ""
echo "🛑 Press Ctrl+C to stop all services"

# Wait for user interrupt
wait
