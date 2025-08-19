# MCP Guardian 🛡️

**AI-powered security-first MCP server discovery and connection system**

A modern web application that discovers, analyzes, and securely connects you to the best MCP servers for your needs with comprehensive server discovery from multiple sources and intelligent database caching for optimal performance.

## 🎯 Overview

MCP Guardian is a sophisticated web application that:

1. **Discovers** relevant MCP servers from GitHub, MCP registry, and community sources
2. **Caches** discoveries in SQLite database for instant subsequent queries
3. **Analyzes** each server's capabilities and security posture
4. **Scores** servers based on a comprehensive security rubric (0-100)
5. **Ranks** and returns the most secure MCP servers for your task
6. **Connects** your agent directly to the recommended servers with ready-to-run code for multiple frameworks

## 🏗️ Architecture

```
Web Interface (Vue.js + Tailwind CSS)
           ↓
    FastAPI Backend
           ↓
    Enhanced Discovery Engine
           ↓
    SQLite Database Cache
           ↓
    Multiple Sources:
    - GitHub Repositories
    - MCP Registry
    - Community Servers
    - Enhanced Mock Database
```

### Features

- **Multi-Source Discovery**: GitHub, MCP registry, community servers
- **Intelligent Caching**: SQLite database for instant query responses
- **Smart Filtering**: Relevance-based server selection
- **Security Scoring**: Transparent security evaluation
- **Framework Support**: LangChain, AutoGen, LangGraph, Custom
- **Modern Web UI**: Interactive Vue.js interface with real-time updates
- **Performance Optimized**: Cached discoveries return instantly

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Modern web browser

### 1. Clone and Setup

```bash
git clone https://github.com/varundataquest/MCPGuardian.git
cd MCPGuardian
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or using pip directly
pip install fastapi uvicorn jinja2 requests
```

### 3. Seed the Database (Optional but Recommended)

```bash
# Seed with initial server data for better performance
python seed_database.py
```

### 4. Run the Web Application

```bash
# Start the web application
python run_web_app.py
```

### 5. Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Database Stats**: http://localhost:8000/api/stats

## 🌐 Web Application Features

### **Server Discovery with Caching**
- Enter your prompt (e.g., "Agent that can handle file operations")
- Get relevant MCP servers from multiple sources
- **Instant responses** for repeated queries via database caching
- View security scores and recommendations
- See server capabilities and authentication methods

### **Code Generation**
- Choose your preferred framework (LangChain, AutoGen, LangGraph, Custom)
- Get ready-to-run agent code
- Download complete setup instructions
- Receive environment configuration templates

### **Enhanced Discovery Sources**
- **GitHub Repositories**: Real MCP servers from GitHub
- **MCP Registry**: Official MCP registry and documentation
- **Community Servers**: Curated community-contributed servers
- **Enhanced Database**: 20+ servers across multiple categories

## 📊 Server Categories

### **File Operations**
- Google Drive, AWS S3, Dropbox, OneDrive
- File upload, download, sharing, collaboration

### **Email & Communication**
- Gmail, Outlook, SendGrid, Slack
- Email management, messaging, team collaboration

### **Database**
- PostgreSQL, MySQL, MongoDB
- Database operations, query execution, data management

### **Search & Analytics**
- Elasticsearch, Algolia
- Search operations, analytics, indexing

### **AI/ML**
- OpenAI, Anthropic Claude
- Text generation, AI chat, analysis

### **Productivity**
- Notion, GitHub, Jira, Calendar, Sheets
- Document management, project management, scheduling

## 🔧 API Endpoints

### **Discover Servers**
```bash
POST /api/discover
{
  "prompt": "Agent that can handle file operations",
  "max_servers": 10
}
```

### **Connect to Server**
```bash
POST /api/connect
{
  "prompt": "Agent that can handle file operations",
  "server_name": "google-drive-mcp-server",
  "framework": "langchain"
}
```

### **Health Check**
```bash
GET /api/health
```

### **Database Statistics**
```bash
GET /api/stats
```

### **Seed Database**
```bash
POST /api/seed
```

## 🗄️ Database Features

### **Intelligent Caching**
- **SQLite Database**: Lightweight, file-based storage
- **Discovery Cache**: Caches query results for 24 hours
- **Server Storage**: Persistent storage of all discovered servers
- **Performance**: Instant responses for cached queries

### **Database Statistics**
- Total servers stored
- Servers by source distribution
- Active cache entries
- Average security scores

### **Cache Management**
- Automatic cache expiration
- Cleanup of expired entries
- Efficient indexing for fast queries

## 🛠️ Framework Support

### **LangChain**
Traditional agent framework with tool-based interactions

### **AutoGen**
Multi-agent conversation framework for complex workflows

### **LangGraph**
Stateful workflow framework with graph-based execution

### **Custom**
Simple direct server connections for basic use cases

## 📁 Project Structure

```
📦 MCP Guardian (19 files)
├── 🌐 Web Application Core
│   ├── src/mcp_multiagent_selector/web_app.py     # Main FastAPI app
│   ├── src/mcp_multiagent_selector/database.py    # Database and caching
│   ├── run_web_app.py                             # Launcher script
│   ├── seed_database.py                           # Database seeding
│   ├── templates/index.html                       # Vue.js frontend
│   └── static/style.css                           # Enhanced CSS
├── Connector Agents
│   ├── connector_agent_direct.py                  # Enhanced connector
│   └── downloadable_connector_agent.py            # Standalone generator
├── 📚 Documentation
│   ├── README.md                                  # Main documentation
│   ├── WEB_APP_README.md                          # Web app guide
│   ├── DOWNLOADABLE_CONNECTOR_AGENT_README.md     # Connector guide
│   └── ARCHITECTURE.md                            # System architecture
├── ⚙️ Configuration
│   ├── pyproject.toml                             # Project config
│   ├── requirements.txt                           # Dependencies
│   ├── poetry.lock                                # Lock file
│   ├── env.example                                # Environment template
│   └── .gitignore                                 # File exclusions
└── 🔧 Development
    └── .pre-commit-config.yaml                    # Code quality
```

## 🔒 Security Features

### **Security Scoring Rubric**
- **Hash Pinning**: Certificate pinning for secure connections
- **SBOM/AIBOM**: Software bill of materials
- **Rate Limiting**: Protection against abuse
- **Observability**: Comprehensive logging and monitoring
- **Authentication**: OAuth2, API key, username/password support

### **Transparent Scoring**
- Clear breakdown of security scores
- Recommendation levels (EXCELLENT, GOOD, FAIR, POOR)
- Activity-based scoring from GitHub metrics

## 🚀 Usage Examples

### **1. Discover File Operation Servers**
```bash
curl -X POST http://localhost:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Agent that can handle file operations", "max_servers": 5}'
```

### **2. Generate LangChain Agent**
```bash
curl -X POST http://localhost:8000/api/connect \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Agent that can handle file operations", "server_name": "google-drive-mcp-server", "framework": "langchain"}'
```

### **3. Check Database Statistics**
```bash
curl http://localhost:8000/api/stats
```

### **4. Use Standalone Connector Agent**
```bash
python downloadable_connector_agent.py
```

## 📈 Performance

### **Discovery Capabilities**
- **Multiple Sources**: 4 discovery sources
- **Server Categories**: 6 major categories
- **Total Servers**: 20+ servers available
- **Framework Support**: 4 frameworks supported

### **Caching Performance**
- **First Query**: 2-3 seconds (fresh discovery)
- **Cached Queries**: < 100ms (instant response)
- **Cache Duration**: 24 hours
- **Database Size**: Lightweight SQLite storage

### **Response Times**
- **Discovery (Cached)**: < 100ms
- **Discovery (Fresh)**: < 3 seconds
- **Code Generation**: < 1 second
- **Web Interface**: Real-time updates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Model Context Protocol (MCP) community
- FastAPI and Vue.js communities
- All contributors and users

---

**MCP Guardian** - Making MCP server discovery and connection secure, simple, intelligent, and fast! 🚀✨



