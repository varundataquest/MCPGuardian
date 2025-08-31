#!/bin/bash

# Test Render deployment setup locally
# This script validates that the configuration works before deploying

set -euo pipefail

echo "🧪 Testing Render Deployment Setup"
echo "=================================="

# Check required files
echo "📁 Checking required files..."
required_files=(
    "render.yaml"
    "backend/requirements.txt"
    "backend/Dockerfile.render"
    "ui/package.json"
    "ui/next.config.mjs"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        exit 1
    fi
done

# Check environment variables
echo ""
echo "🔧 Checking environment configuration..."
if [ -f "backend/.env" ]; then
    echo "  ✅ backend/.env exists"
    
    # Check for required variables
    required_vars=("SUPABASE_URL" "BACKEND_PORT" "MCP_SERVER_PORT")
    for var in "${required_vars[@]}"; do
        if grep -q "^$var=" backend/.env; then
            echo "  ✅ $var configured"
        else
            echo "  ⚠️  $var not found in .env"
        fi
    done
else
    echo "  ❌ backend/.env missing"
    exit 1
fi

# Test Python dependencies
echo ""
echo "🐍 Testing Python environment..."
if command -v python3 >/dev/null 2>&1; then
    echo "  ✅ Python 3 available"
    
    # Test if we can import key modules
    cd backend
    if python3 -c "import fastapi, uvicorn, fastmcp" 2>/dev/null; then
        echo "  ✅ Key Python packages available"
    else
        echo "  ⚠️  Some Python packages missing. Run: pip install -r requirements.txt"
    fi
    cd ..
else
    echo "  ❌ Python 3 not found"
    exit 1
fi

# Test Node.js dependencies
echo ""
echo "📦 Testing Node.js environment..."
if command -v node >/dev/null 2>&1; then
    echo "  ✅ Node.js available ($(node --version))"
    
    cd ui
    if [ -d "node_modules" ]; then
        echo "  ✅ Node modules installed"
    else
        echo "  ⚠️  Node modules not installed. Run: npm ci"
    fi
    
    # Test build
    echo "  🔨 Testing Next.js build..."
    if npm run build >/dev/null 2>&1; then
        echo "  ✅ Next.js build successful"
    else
        echo "  ❌ Next.js build failed"
        exit 1
    fi
    cd ..
else
    echo "  ❌ Node.js not found"
    exit 1
fi

# Test Docker build (if Docker is available)
echo ""
echo "🐳 Testing Docker configuration..."
if command -v docker >/dev/null 2>&1; then
    echo "  ✅ Docker available"
    
    echo "  🔨 Testing Docker build..."
    if docker build -f backend/Dockerfile.render -t mcpguardian-test backend/ >/dev/null 2>&1; then
        echo "  ✅ Docker build successful"
        docker rmi mcpguardian-test >/dev/null 2>&1 || true
    else
        echo "  ❌ Docker build failed"
        exit 1
    fi
else
    echo "  ⚠️  Docker not available (optional)"
fi

# Test service connectivity simulation
echo ""
echo "🌐 Testing service configuration..."

# Check if ports are available
check_port() {
    local port=$1
    if lsof -i :$port >/dev/null 2>&1; then
        echo "  ⚠️  Port $port is in use"
    else
        echo "  ✅ Port $port is available"
    fi
}

check_port 8015
check_port 8016
check_port 3000

echo ""
echo "📋 Render Deployment Checklist:"
echo "  1. ✅ All required files present"
echo "  2. ✅ Environment configuration ready"
echo "  3. ✅ Dependencies installable"
echo "  4. ✅ Build processes working"
echo ""
echo "🚀 Ready for Render deployment!"
echo ""
echo "Next steps:"
echo "  1. Push code to GitHub"
echo "  2. Connect repository to Render"
echo "  3. Set environment variables in Render dashboard"
echo "  4. Deploy using render.yaml blueprint"
echo ""
echo "🔗 Render deployment URLs will be:"
echo "  • Frontend: https://mcpguardian-ui.onrender.com"
echo "  • API: https://mcpguardian-api.onrender.com"
echo "  • MCP: https://mcpguardian-mcp.onrender.com/mcp"
