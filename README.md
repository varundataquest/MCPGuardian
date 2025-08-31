# 🛡️ AgentAgentGo: MCPGuard

**The world's first dual-mode MCP security platform: Web app for humans + MCP server for AI assistants.**

AgentAgentGo: MCPGuard automatically discovers MCP servers from public registries, analyzes their security posture, and provides both a beautiful web interface for human users and a comprehensive MCP server for AI assistants to programmatically discover, analyze, and get security insights about MCP servers.

**🚀 [Deploy to Render](https://render.com)** | **🌐 [Live Demo](https://mcpguardian-ui.onrender.com)** | **🤖 [MCP Server](https://mcpguardian-mcp.onrender.com/mcp)**

## ✨ Key Features

### 🌐 Web Interface (For Humans)
- 🔍 **Smart Discovery**: Crawls major MCP registries (Glama, mcp.so) with respect for robots.txt
- 🔒 **Security Scoring**: Transparent, explainable security scores based on metadata analysis
- 🚀 **Fast Search**: Full-text search with intelligent filtering and sorting
- 📊 **Rich Details**: Project info, hosting details, GitHub metrics, and deployment guidance
- 🎨 **Clean UI**: Responsive interface with color-coded security badges
- ⚡ **Real-time Updates**: Live crawl progress and instant search results
- ⚡ **Immediate Score Badges**: Scores are included in search responses to avoid per-card API calls and delays

### 🤖 MCP Server (For AI Assistants)
- 🌐 **HTTP Transport**: Streamable HTTP at `http://localhost:8016/mcp` (local) or `https://your-app.onrender.com/mcp` (production)
- 🔍 **`search_mcp_servers`**: Search and discover servers with security analysis
- 📋 **`get_server_details`**: Comprehensive server information and metadata
- 🛡️ **`analyze_server_security`**: Security breakdown with recommendations
- 🎯 **`recommend_servers`**: AI-curated recommendations based on use case
- 🔧 **`analyze_custom_server`**: Real-time analysis of any MCP server URL
- ⭐ **`list_popular_servers`**: GitHub stars-based popularity rankings
- 🔐 **`find_secure_servers`**: High-security server filtering
- 🚀 **`start_server_discovery`**: Trigger background server discovery
- 📊 **Security-First**: Every tool includes security scores and risk analysis

Note: When calling the MCP server over HTTP, clients must set `Accept: application/json` and also accept `text/event-stream` for streaming responses.

## 🚀 Quick Start

### 🌩️ **Production Deployment** (Recommended)

Deploy instantly to [Render](https://render.com) with our pre-configured blueprint:

1. **Fork this repository** to your GitHub
2. **Connect to Render** and deploy using `render.yaml`
3. **Set environment variables** in Render dashboard:
   ```bash
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE_KEY=your_service_key
   GEMINI_API_KEY=your_gemini_key (optional)
   GITHUB_TOKEN=your_github_token (optional)
   ADMIN_ACCESS_TOKEN=your_secure_token
   ```
4. **Access your deployment**:
   - 🌐 Web UI: `https://mcpguardian-ui.onrender.com`
   - 🤖 MCP Server: `https://mcpguardian-mcp.onrender.com/mcp`
   - 🔧 API: `https://mcpguardian-api.onrender.com`

See [`render-config.md`](render-config.md) for detailed deployment instructions.

### 💻 **Local Development**

1. **Clone and Setup**
```bash
git clone <your-repo-url>
cd AgentAgentGo-MCPGuard
```

2. **Set Up Database** (One-time)
   - Create a [Supabase](https://supabase.com) project
   - Run the SQL in `backend/db/schema.sql` in your Supabase SQL editor
   - Copy `backend/.env.example` to `backend/.env` and fill in your values

3. **Choose Your Development Mode**

#### 🔥 **Hybrid Mode** (Recommended) - Web UI + MCP Server
```bash
# Start web interface + MCP server for AI assistants
./scripts/overall_startup.sh

# Access both:
# 🌐 Web UI: http://localhost:3000
# 🤖 MCP Server: http://localhost:8016/mcp (Streamable HTTP)
# 🔧 REST API: http://localhost:8015
```

#### 🌐 **Web-Only Mode** - Just the Web Interface  
```bash
# Start web interface only (backend + UI)
./scripts/start_web_only.sh

# Access: http://localhost:3000
```

#### 🤖 **MCP-Only Mode** - Just the MCP Server
```bash
# Start MCP server only for AI assistants
./scripts/start_mcp_only.sh

# Connect your AI assistant to:
# 🤖 MCP Server: http://localhost:8016/mcp (Streamable HTTP)
```

### 4. Usage Examples

#### For Humans (Web Interface):
- **Search & Browse**: http://localhost:3000
- **Server Details**: Click any server for project info, security analysis, and deployment guides  
- **Admin Panel**: http://localhost:3000/admin (requires token setup)

#### For AI Assistants (MCP Protocol):

**🔌 Connection Details:**
- **Protocol**: MCP over Streamable HTTP
- **URL**: `http://localhost:8016/mcp`
- **Transport Type**: `streamable-http`

**🛠️ Connect with MCP Inspector:**
```json
{
  "url": "http://localhost:8016/mcp",
  "transportType": "streamable-http"
}
```

**📝 Example Tool Usage:**
```python
# Example AI assistant usage:
servers = await search_mcp_servers("github file operations", limit=5, sort_by="security_score")
analysis = await analyze_server_security(servers[0]["id"])
recommendations = await recommend_servers("code analysis", min_security_score=0.8)
```

---

## 🎯 How It Works

### Discovery Pipeline
1. **🕷️ Crawl**: Discovers servers from Glama.ai and mcp.so registries
2. **✨ Enrich**: Extracts metadata, finds mcp.json files, fetches GitHub info
3. **🔒 Score**: Analyzes security posture using transparent criteria
4. **💾 Store**: Saves servers and their security scores to the database with full-text search indexing

### Security Scoring
MCP Guardian uses a **transparent, explainable scoring system**:

- **🏆 Baseline (70 points)**: Credit for being discoverable
- **🔧 Runtime Safety**: Limited attack surface, read-only operations  
- **📋 Repository Health**: License, security docs, maintenance
- **🚀 Release Activity**: Recent updates and active development
- **🔗 Trust Signals**: HTTPS, security headers, proper hosting
- **🏢 Reputation**: Publisher/company reputation analysis

### Color-Coded Badges
- 🟢 **Green (75+)**: High confidence, well-maintained
- 🟡 **Yellow (70-75)**: Good baseline, some improvements possible  
- 🔴 **Red (<70)**: Caution advised, security gaps identified

## 🔧 Alternative Setup Methods

### Manual Setup
```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload --port 8015

# UI (new terminal)
cd ui && npm ci
NEXT_PUBLIC_API_BASE=http://localhost:8015 npm run dev
```

### Docker Compose
```bash
docker compose up --build
# Services available at localhost:3000 (UI) and localhost:8015 (API)
```

### Stop Services
```bash
./scripts/overall_shutdown.sh  # Graceful shutdown
# Or force stop: pkill -f uvicorn; pkill -f "next dev"
```

---

## 🤖 MCP Server Reference

### Available MCP Tools

AgentAgentGo: MCPGuard provides **10 comprehensive MCP tools** for AI assistants:

#### 🔍 **Discovery & Search**
- **`search_mcp_servers(query, limit, sort_by)`**
  - Search servers by query, tags, or use case
  - Sort by: `"relevance"`, `"security_score"`, `"recent"`, `"github_stars"`
  - Returns: Server list with security scores and metadata

- **`get_server_details(server_id)`**
  - Get comprehensive information for a specific server
  - Returns: Full server metadata, GitHub info, security analysis

- **`list_popular_servers(limit)`**
  - Get popular servers sorted by GitHub stars
  - Returns: Top servers with popularity metrics

- **`get_servers_by_registry(registry, limit)`**
  - Get servers from specific registry (`"glama"`, `"mcpso"`, `"pulsemcp"`)
  - Returns: Registry-specific server listings

#### 🛡️ **Security Analysis**
- **`analyze_server_security(server_id)`**
  - Get detailed security analysis for a server
  - Returns: Score breakdown, recommendations, risk factors

- **`find_secure_servers(min_security_score, limit)`**
  - Find servers meeting minimum security requirements
  - Returns: High-security servers with detailed analysis

- **`analyze_custom_server(url)`**
  - Analyze any MCP server URL on-demand
  - Returns: Real-time security assessment and connectivity check

#### 🎯 **AI-Powered Recommendations**
- **`recommend_servers(use_case, min_security_score, limit)`**
  - Get AI-curated server recommendations for specific use cases
  - Examples: `"file operations"`, `"github integration"`, `"web scraping"`
  - Returns: Ranked recommendations with reasoning and security scores

#### 🚀 **Discovery Management**
- **`start_server_discovery(max_glama_servers, max_mcpso_servers)`**
  - Trigger background discovery of new servers
  - Returns: Crawl session ID and status

- **`get_discovery_status()`**
  - Check status of active discovery crawls
  - Returns: Current crawl progress and information

### Usage Examples

#### Basic Server Search
```python
# Search for file-related servers with good security
servers = await search_mcp_servers(
    query="file system operations",
    limit=10,
    sort_by="security_score"
)
```

#### Get Security Analysis
```python
# Analyze a specific server's security
analysis = await analyze_server_security("server-123")
print(f"Security Score: {analysis['security_score']}")
print(f"Recommendations: {analysis['recommendations']}")
```

#### Smart Recommendations
```python
# Get AI-curated recommendations for a specific use case
recommendations = await recommend_servers(
    use_case="GitHub repository analysis",
    min_security_score=0.8,
    limit=5
)

for rec in recommendations:
    print(f"{rec['server']['name']}: {rec['recommendation']['reasoning']}")
```

#### Real-time Analysis
```python
# Analyze any MCP server URL on-demand
result = await analyze_custom_server("https://github.com/user/mcp-server")
print(f"Status: {result['status']}")
print(f"Security Analysis: {result.get('security_analysis', 'N/A')}")
```

---

## 📡 REST API Reference

### Search & Browse
- `GET /health` - Service health check (used by Render)
- `GET /search?q=<query>&limit=20&offset=0&sort=rank|stars|recent|score`
- `GET /servers?limit=20&offset=0` - List all servers
- `GET /servers/{id}` - Get server details with latest security score

### Server Details  
- `GET /servers/{id}/score` - Get latest security score breakdown

### Response Format
```json
{
  "items": [
    {
      "id": 123,
      "name": "GitHub MCP Server", 
      "registry": "glama",
      "description": "...",
      "homepage_url": "...",
      "latest_score": { "score_overall": 85.2 }
    }
  ],
  "total": 1247  // Total count across all pages
}
```

## 🛠️ Troubleshooting

### Service Issues
```bash
# Port conflicts
lsof -i :8015 && lsof -ti :8015 | xargs kill -9
./scripts/overall_startup.sh

# Connection problems
curl http://localhost:8015/search?q=test
curl http://localhost:3000  # Should show UI

# View logs
tail -f /tmp/uvicorn8015.log /tmp/next3000.log
```

### Common Problems
- **"No results"**: Backend not connected - check `curl http://localhost:8015/search?q=`
- **Port in use**: Kill processes with `./scripts/overall_shutdown.sh`  
- **Database empty**: Run a crawl from admin panel or check Supabase setup

---

## 🔐 Admin Panel (Restricted Access)

> **Note**: Admin functionality is protected and only accessible to authorized users.

### Setting Up Admin Access

1. **Configure Environment Variables**:
   ```bash
   # backend/.env
   ADMIN_ACCESS_TOKEN=your-secret-admin-token-here
   
   # ui/.env.local  
   NEXT_PUBLIC_API_BASE=http://localhost:8015
   NEXT_PUBLIC_ADMIN_ACCESS_TOKEN=your-secret-admin-token-here
   ```

2. **Access Admin Panel**: http://localhost:3000/admin (or :3001 if using alternate port)
   - Without token: Shows "Access Denied"
   - With token: Full admin interface

### Admin Features

#### 🕷️ Crawl Management
- **Start Crawl**: Configure registry limits (e.g., 50 Glama + 100 mcp.so servers)
- **Real-time Progress**: Live updates showing servers collected per registry
- **Stop Crawl**: Immediate cancellation of running crawls
- **Collection Progress**: `Glama: 45/50, mcp.so: 78/100, Total: 123/150`

#### 📊 Advanced Options
- **Registry Caps**: Set per-registry limits for targeted crawling
- **Concurrency Controls**: Adjust crawl, enrichment, and scoring parallelism  
- **Persistence**: Saves servers and security scores to the database (immediate per-registry server upserts, plus batched score inserts every `PERSIST_BATCH_SIZE`, and a final flush at end)
- **Backfill**: Run post-crawl enhancement for existing servers

#### 🔧 Debug Tools
- **Test API**: Verify backend connectivity from admin interface
- **Live Logs**: Stream real-time crawl progress and system events
- **Status Monitoring**: Check active crawls and system health

### Admin API Endpoints
```bash
# Start crawl (requires X-Admin-Token header)
curl -X POST -H "X-Admin-Token: your-token" \
  "http://localhost:8015/admin/crawl/start?max_items_glama=50&max_items_mcpso=100"

# Check status  
curl -H "X-Admin-Token: your-token" \
  "http://localhost:8015/admin/crawl/status"

# Stop crawl
curl -X POST -H "X-Admin-Token: your-token" \
  "http://localhost:8015/admin/crawl/stop"
```

### Production Deployment
For **Render** or other hosting:
- Set `ADMIN_ACCESS_TOKEN` in platform environment variables
- Public users see main UI only
- Admin access works from your laptop with proper token configuration

---

## ⚙️ Environment Configuration

MCPGuardian uses environment variables for configuration, keeping sensitive information secure and enabling easy deployment across different platforms.

### Required Environment Variables

#### **For Production (Render Dashboard)**
Set these as environment variables in your Render service settings:

```bash
# Database (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Authentication (Required)
ADMIN_ACCESS_TOKEN=your-secure-admin-token-here

# AI Services (Optional - for enhanced search)
GEMINI_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_token

# Registry Configuration (Pre-configured)
REGISTRY_1_NAME=primary_registry
REGISTRY_1_DISPLAY_NAME=Primary Source
REGISTRY_1_URL=https://glama.ai/mcp/servers
REGISTRY_1_ENABLED=true

REGISTRY_2_NAME=secondary_registry
REGISTRY_2_DISPLAY_NAME=Secondary Source  
REGISTRY_2_URL=https://mcp.so/servers
REGISTRY_2_ENABLED=true
```

#### **For Local Development (.env files)**
Create `backend/.env` and `ui/.env.local`:

```bash
# backend/.env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key  
GEMINI_API_KEY=your_gemini_key (optional)
GITHUB_TOKEN=your_github_token (optional)
ADMIN_ACCESS_TOKEN=dev-admin-token-12345

# Ports (auto-configured)
BACKEND_PORT=8015
MCP_SERVER_PORT=8016  
UI_PORT=3000
```

```bash
# ui/.env.local
NEXT_PUBLIC_API_BASE=http://localhost:8015
NEXT_PUBLIC_ADMIN_ACCESS_TOKEN=dev-admin-token-12345
```

### Registry Configuration Details

- **Registry Names**: Use generic names like `primary_registry`, `secondary_registry` to hide actual sources
- **Display Names**: Human-readable names shown in the UI
- **URLs**: Private registry endpoints (kept out of public code)
- **Enabled**: Toggle registries on/off without code changes
- **Environment Aware**: Automatically uses `RENDER_EXTERNAL_URL` in production

## 🚨 Troubleshooting

### Admin/Crawl Issues

#### Problem: "Crawl starts but shows no progress"
**Symptoms:**
- Crawl appears to start but no log messages appear
- Admin page shows "Starting crawl..." but nothing happens
- API Debug shows "Admin Token: Missing" (red)

**Root Cause:** Missing environment variables for authentication

**Solution:**
1. **Stop all services:**
   ```bash
   # Kill backend processes
   pkill -f "uvicorn app.main:app"
   
   # Kill frontend processes  
   lsof -ti:3000 | xargs kill -9  # or port 3001
   ```

2. **Start backend (environment already configured):**
   ```bash
   cd backend
   source ../.venv/bin/activate
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8015 --reload
   ```
   
   **Note**: The `.env` file now includes both original configuration (Supabase, OpenAI, etc.) and new registry abstraction settings.

3. **Start frontend with matching token:**
   ```bash
   cd ui
   NEXT_PUBLIC_ADMIN_ACCESS_TOKEN="your-secret-token" npm run dev
   # If port 3000 busy: npm run dev -- -p 3001
   ```

#### Problem: "Address already in use" errors
**Symptoms:**
- `EADDRINUSE: address already in use :::8015` (backend)
- `EADDRINUSE: address already in use :::3000` (frontend)

**Solution:**
```bash
# Find and kill processes using the ports
lsof -ti:8015 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Or use alternative ports
npm run dev -- -p 3001  # Frontend on 3001
```

#### Problem: "Invalid or missing admin token" 
**Symptoms:**
- API returns 401/403 errors
- Admin endpoints return authentication errors
- Crawl API calls fail

**Solution:**
Ensure **both** backend and frontend use the **same token**:
```bash
# Backend needs this env var:
ADMIN_ACCESS_TOKEN="your-secret-token"

# Frontend needs this env var: 
NEXT_PUBLIC_ADMIN_ACCESS_TOKEN="your-secret-token"
```

### Verification Steps

1. **Check API Debug section** in Admin panel:
   ```
   ✅ Admin Token: Present (green)
   ✅ Health: ok (green)  
   ```

2. **Test admin endpoint manually:**
   ```bash
   curl -H "X-Admin-Token: your-token" http://localhost:8015/admin/crawl/status
   # Should return: {"active":false,"crawl_id":null}
   ```

3. **Check browser console** for EventSource connection logs:
   ```
   ✅ EventSource connected
   🚀 Starting crawl with URL: ...  
   📡 Start crawl response: 200 OK
   ```

### Debug Mode
For detailed troubleshooting, the admin interface now includes:
- Console logging of all API requests/responses
- EventSource connection status
- Real-time error messages in activity log
- Admin token presence verification

### Current Running Services
If you followed the troubleshooting steps above, your services should be running on:
- **Backend API**: http://localhost:8015 (with admin token: `dev-admin-token-12345`)
- **Frontend UI**: http://localhost:3001 (with matching admin token)
- **Admin Panel**: http://localhost:3001/admin

**Quick Status Check:**
```bash
# Test backend
curl -H "X-Admin-Token: dev-admin-token-12345" http://localhost:8015/admin/crawl/status

# Test frontend  
curl -s http://localhost:3001 | grep -o "<title>.*</title>"
```

---

## 🧠 Technical Details

### Dual-Mode Architecture

#### 🌐 **Web Stack** (Human Interface)
- **Backend**: FastAPI + Uvicorn (port 8015), REST API endpoints
- **Frontend**: Next.js 14 with App Router, Tailwind CSS, SSE for real-time updates
- **Database**: Supabase/PostgreSQL with full-text search indexing
- **Real-time**: Server-Sent Events for live crawl progress

#### 🤖 **MCP Server** (AI Assistant Interface)  
- **Protocol**: Model Context Protocol (MCP) over Streamable HTTP transport
- **Endpoint**: `http://localhost:8016/mcp` (port 8016)
- **Framework**: FastMCP 2.0 with 10+ specialized tools
- **Architecture**: Shared core engine with web stack for consistency
- **Threading**: Isolated event loops to prevent conflicts in hybrid mode

#### 🔄 **Shared Core Engine**
- **Discovery**: Playwright for JavaScript-heavy sites, respectful rate limiting  
- **Security**: Metadata-only analysis, no code execution, transparent scoring
- **Enrichment**: GitHub API integration, mcp.json parsing, repository analysis
- **Storage**: Unified database layer with consistent scoring across both modes

### Development

#### Testing & Scripts
```bash
# Run tests
PYTHONPATH=backend pytest

# Manual pipeline run  
PYTHONPATH=backend python backend/scripts/smoke_pipeline.py

# Test MCP server standalone
cd backend && PYTHONPATH=. python mcp_server.py

# Database schema
# Apply backend/db/schema.sql to your Supabase project
```

#### Development Modes
```bash
# Test different startup modes during development:

# 1. Full hybrid mode (Web + MCP)
./scripts/overall_startup.sh

# 2. Web development only  
./scripts/start_web_only.sh

# 3. MCP server development only
./scripts/start_mcp_only.sh

# Stop everything
./scripts/overall_shutdown.sh
```

#### Key Files
- `backend/mcp_server.py` - MCP server with 10 tools for AI assistants
- `backend/app/core_engine.py` - Shared business logic for both modes
- `backend/app/main.py` - FastAPI web server  
- `ui/app/page.tsx` - Main search interface
- `ui/app/admin/page.tsx` - Admin dashboard

### Resources
- **MCP Registries**: [Glama.ai](https://glama.ai), [mcp.so](https://mcp.so)
- **Documentation**: `backend/docs/ARCHITECTURE.md`  
- **MCP Specification**: [Model Context Protocol](https://modelcontextprotocol.io)
- **FastMCP Framework**: [FastMCP Documentation](https://gofastmcp.com)
- **AI Assistant Integration**: Connect your AI assistant to the MCP server for programmatic access

---

## 📋 Advanced Configuration

### Custom Registry Setup

To add your own MCP registry sources:

```bash
# Add up to 9 registries in backend/.env
REGISTRY_3_NAME=custom_registry
REGISTRY_3_DISPLAY_NAME=My Custom Registry
REGISTRY_3_URL=https://my-registry.com/api/servers
REGISTRY_3_ENABLED=true
```

### Performance Tuning

```bash
# Adjust crawling behavior
CRAWL_MAX_CONCURRENCY=10          # Increase for faster crawling
CRAWL_RATE_LIMIT_PER_HOST=1       # Decrease for gentler crawling
CRAWL_MAX_PAGES_GLAMA=20          # More comprehensive discovery
```

### Security Hardening

For production deployments:

```bash
# Use strong admin tokens
ADMIN_ACCESS_TOKEN=$(openssl rand -hex 32)

# Restrict GitHub token scopes to minimum needed
# Only grant: public_repo, read:org (if needed)

# Use read-only database connections where possible
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Submit a pull request with clear description

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
