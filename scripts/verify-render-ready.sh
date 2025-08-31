#!/bin/bash

# Verify Render deployment readiness
# This script checks that all configurations are ready for Render

echo "🚀 Verifying Render Deployment Readiness..."
echo "==========================================="

# Check required files
echo "📋 Checking deployment files..."
required_files=(
    "render.yaml"
    "render-env-setup.md"
    "backend/requirements.txt"
    "backend/Dockerfile.render"
    "ui/package.json"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        exit 1
    fi
done

# Check render.yaml configuration
echo ""
echo "🔧 Checking render.yaml configuration..."
if grep -q "sync: false.*Set manually" render.yaml; then
    echo "  ✅ Environment variables set to manual configuration"
else
    echo "  ⚠️  Environment variables might need manual configuration"
fi

if grep -A1 "PYTHONPATH" render.yaml | grep -q "backend"; then
    echo "  ✅ Backend Python path configured"
else
    echo "  ❌ Backend Python path missing"
    exit 1
fi

# Check package.json port configuration
echo ""
echo "📦 Checking UI port configuration..."
if grep -q '\${PORT:-3000}' ui/package.json; then
    echo "  ✅ UI configured to use Render's PORT variable"
else
    echo "  ❌ UI not configured for Render PORT variable"
    exit 1
fi

# Check backend dependencies
echo ""
echo "🐍 Checking backend dependencies..."
required_deps=("fastapi" "uvicorn" "fastmcp" "supabase")
for dep in "${required_deps[@]}"; do
    if grep -q "$dep" backend/requirements.txt; then
        echo "  ✅ $dep dependency found"
    else
        echo "  ❌ $dep dependency missing"
        exit 1
    fi
done

# Check Next.js build configuration
echo ""
echo "⚙️ Checking Next.js configuration..."
if [ -f "ui/next.config.mjs" ]; then
    echo "  ✅ Next.js config exists"
else
    echo "  ⚠️  Next.js config missing (might use defaults)"
fi

echo ""
echo "🎉 Render Deployment Readiness: PASSED"
echo ""
echo "📋 Next steps for deployment:"
echo "1. Push code to GitHub repository"
echo "2. Connect repository to Render"
echo "3. Deploy using render.yaml blueprint"
echo "4. Set environment variables using render-env-setup.md"
echo "5. Test deployed services"
echo ""
echo "🌐 Expected service URLs:"
echo "  • Frontend: https://mcpguardian-ui.onrender.com"
echo "  • API: https://mcpguardian-api.onrender.com"  
echo "  • MCP: https://mcpguardian-mcp.onrender.com/mcp"
