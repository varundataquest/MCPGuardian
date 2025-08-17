#!/bin/bash

# MCP Registry Harvester Deployment Script

echo "🚀 MCP Registry Harvester Deployment Script"
echo "=========================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    exit 1
fi

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Check if logged in to Railway
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway:"
    railway login
fi

echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment complete!"
echo "🌐 Your app is available at:"
railway domain

echo ""
echo "📊 To view logs:"
echo "   railway logs"

echo ""
echo "🔧 To open the app:"
echo "   railway open" 