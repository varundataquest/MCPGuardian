#!/bin/bash

echo "🚀 MCP Registry Harvester - GitHub Push Script"
echo "=============================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please initialize git first."
    exit 1
fi

# Check if we have commits
if ! git log --oneline -1 > /dev/null 2>&1; then
    echo "❌ No commits found. Please commit your changes first."
    exit 1
fi

echo "✅ Git repository is ready!"
echo ""

echo "📋 Next steps:"
echo "1. Go to https://github.com/new"
echo "2. Create a new repository (e.g., 'mcp-registry-harvester')"
echo "3. Make it Public or Private as you prefer"
echo "4. DO NOT initialize with README, .gitignore, or license"
echo "5. Copy the repository URL"
echo ""

read -p "Enter your GitHub repository URL (e.g., https://github.com/username/mcp-registry-harvester): " repo_url

if [ -z "$repo_url" ]; then
    echo "❌ No repository URL provided. Exiting."
    exit 1
fi

echo ""
echo "🔗 Adding remote origin..."
git remote add origin "$repo_url"

echo "📤 Pushing to GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "✅ Successfully pushed to GitHub!"
echo "🌐 Your repository is now available at: $repo_url"
echo ""
echo "🎉 You can now:"
echo "   • Deploy using Railway: ./deploy.sh"
echo "   • Share your repository with others"
echo "   • Set up GitHub Actions for CI/CD"
echo "   • Clone on other machines" 