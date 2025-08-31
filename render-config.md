# 🚀 Render Deployment Guide for MCPGuardian

## Quick Deployment Options

### Option 1: Multi-Service (Recommended)
Deploy as separate services for better scaling and isolation:

1. **Backend API Service** (FastAPI)
2. **MCP Server Service** (FastMCP) 
3. **Frontend Service** (Next.js)

### Option 2: Single Service
Deploy everything in one Docker container (simpler but less scalable).

## 📋 Step-by-Step Deployment

### 1. Connect Repository to Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Blueprint" 
3. Connect your GitHub repository
4. Render will detect the `render.yaml` file automatically

### 2. Configure Environment Variables

In Render dashboard, set these **sensitive** environment variables:

#### **Backend API Service**
```bash
# Database (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...your-key
SUPABASE_ANON_KEY=eyJhbGci...your-anon-key

# AI Services (Optional)
GEMINI_API_KEY=AIzaSy...your-gemini-key
GITHUB_TOKEN=ghp_...your-github-token

# Admin Access
ADMIN_ACCESS_TOKEN=your-secure-admin-token
```

#### **MCP Server Service**
```bash
# Same database config as above
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...your-key
GEMINI_API_KEY=AIzaSy...your-gemini-key
GITHUB_TOKEN=ghp_...your-github-token
```

#### **Frontend Service**
```bash
NEXT_PUBLIC_ADMIN_ACCESS_TOKEN=your-secure-admin-token
NEXT_PUBLIC_API_BASE=https://mcpguardian-api.onrender.com
```

### 3. URLs After Deployment

Your services will be available at:

- **Frontend**: `https://mcpguardian-ui.onrender.com`
- **Backend API**: `https://mcpguardian-api.onrender.com`  
- **MCP Server**: `https://mcpguardian-mcp.onrender.com/mcp`

### 4. Connect AI Assistants

#### **Cursor Configuration**
```json
// .cursor/mcp.json
{
  "mcpServers": {
    "mcpguardian": {
      "url": "https://mcpguardian-mcp.onrender.com/mcp"
    }
  }
}
```

#### **MCP Inspector**
```bash
# Test your deployment
npx @modelcontextprotocol/inspector@latest https://mcpguardian-mcp.onrender.com/mcp
```

### 5. Custom Domain (Optional)

1. Add your custom domain in Render dashboard
2. Update environment variables:
   - `API_BASE_URL=https://api.yourdomain.com`
   - `NEXT_PUBLIC_API_BASE=https://api.yourdomain.com`

## 🔧 Manual Deployment (Alternative)

If you prefer manual setup without `render.yaml`:

### Backend API Service
```yaml
Type: Web Service
Runtime: Python 3
Build Command: cd backend && pip install -r requirements.txt
Start Command: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### MCP Server Service  
```yaml
Type: Web Service
Runtime: Python 3
Build Command: cd backend && pip install -r requirements.txt  
Start Command: cd backend && python3 mcp_server.py --transport streamable-http --host 0.0.0.0 --port $PORT --path /mcp
```

### Frontend Service
```yaml
Type: Web Service
Runtime: Node
Build Command: cd ui && npm ci && npm run build
Start Command: cd ui && npm start
```

## 🎯 Production URLs

After deployment, update your documentation with:

```bash
# Production MCP Server
https://mcpguardian-mcp.onrender.com/mcp

# Production Web App  
https://mcpguardian-ui.onrender.com

# Production API
https://mcpguardian-api.onrender.com
```

## 🔒 Security Notes

1. **Never commit API keys** - Use Render dashboard environment variables
2. **Use strong admin tokens** in production
3. **Enable HTTPS only** (Render provides this automatically)
4. **Consider adding OAuth** for MCP server if needed

## 🚀 Benefits of Render Deployment

✅ **Native Docker Support** - Your existing setup works as-is  
✅ **Persistent Services** - MCP server runs continuously  
✅ **Auto-scaling** - Handles traffic spikes automatically  
✅ **Free SSL** - HTTPS enabled by default  
✅ **Easy Environment Management** - Secure secret handling  
✅ **Git-based Deployment** - Auto-deploy on git push  
✅ **Health Checks** - Automatic service monitoring  

Your MCPGuardian will be production-ready on Render! 🎉
