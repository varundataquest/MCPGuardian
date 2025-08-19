# MCP Guardian Web Application 🌐

**Modern web interface for intelligent MCP server discovery and connection**

## 🚀 Quick Start

### **📍 Access Your Web App**

**Open your web browser and go to:**
```
http://localhost:8000
```

### **🌐 Available Endpoints**

- **Main Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Database Statistics**: http://localhost:8000/api/stats

## ✨ Features

### **🎯 Intelligent Server Discovery**
Enter natural language prompts like:
- "Agent that can handle file operations"
- "Agent that can send me emails"
- "Agent that can query databases"
- "Agent that can search documents"
- "Agent that can manage projects"

### **⚡ Performance Optimized**
- **Database Caching**: Instant responses for repeated queries
- **Smart Filtering**: Relevance-based server selection
- **Multi-Source Discovery**: GitHub, MCP registry, community servers
- **Real-time Updates**: Live interface with WebSocket support

### **🛡️ Security-First Analysis**
- Real-time security scoring (0-100 scale)
- Detailed security breakdowns with visual indicators
- Authentication model analysis (OAuth2, API Key, etc.)
- Maintainer activity tracking
- Recommendation levels (EXCELLENT, GOOD, FAIR, POOR)

### **🔗 Interactive Connector Agent**
- Click "Connect Agent" on any server
- Choose your framework (LangChain, LangGraph, AutoGen, Custom)
- Generate and download ready-to-use code
- Complete setup instructions and environment templates

### **🗄️ Database Management**
- **Statistics Dashboard**: View database metrics
- **Cache Management**: Automatic cache expiration
- **Server Storage**: Persistent server metadata
- **Performance Monitoring**: Query optimization

## 🎨 User Interface

The web app features:
- **Responsive design** with Tailwind CSS
- **Interactive server cards** with hover effects
- **Color-coded security scores** and recommendations
- **Loading animations** and smooth transitions
- **Modern, beautiful UI** that works on all devices
- **Scrollable code blocks** in modal dialogs
- **Download functionality** for generated code

## 🔧 Technical Stack

### **Backend**
- **FastAPI**: Modern, fast web framework
- **Uvicorn**: ASGI server with hot reload
- **Pydantic**: Data validation and serialization
- **SQLite**: Lightweight database with caching
- **Jinja2**: Template engine for HTML rendering

### **Frontend**
- **Vue.js 3**: Reactive JavaScript framework
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API communication
- **Font Awesome**: Icons and visual elements

### **Database**
- **SQLite**: File-based database storage
- **Async Operations**: Non-blocking database queries
- **JSON Storage**: Flexible metadata storage
- **Indexing**: Optimized query performance

## 📋 API Endpoints

### **POST /api/discover**
Discover MCP servers based on a prompt with caching:
```json
{
  "prompt": "Agent that can handle file operations",
  "max_servers": 10
}
```

**Response:**
```json
{
  "recommendations": [
    {
      "name": "google-drive-mcp-server",
      "endpoint": "https://api.drive-mcp.com",
      "description": "Google Drive integration for file operations",
      "security_score": 85,
      "auth_model": "oauth2",
      "activity": 9,
      "source": "google_official",
      "capabilities": ["file_upload", "file_download", "file_sharing"],
      "security_breakdown": {"hash_pinning": 15, "sbom": 10},
      "recommendation_level": "EXCELLENT"
    }
  ],
  "total_found": 1,
  "prompt": "Agent that can handle file operations",
  "cached": true
}
```

### **POST /api/connect**
Generate connection code for a specific server:
```json
{
  "prompt": "Agent that can handle file operations",
  "server_name": "google-drive-mcp-server",
  "framework": "langchain"
}
```

**Response:**
```json
{
  "success": true,
  "server": {...},
  "connection_result": {
    "framework": "langchain",
    "code": "#!/usr/bin/env python3\n...",
    "instructions": "Setup instructions...",
    "files": [...]
  }
}
```

### **GET /api/health**
Check application health:
```json
{
  "status": "healthy",
  "service": "MCP Guardian",
  "version": "1.0.0"
}
```

### **GET /api/stats**
Get database statistics:
```json
{
  "database_stats": {
    "total_servers": 11,
    "servers_by_source": {
      "google_official": 2,
      "github": 1,
      "community": 1
    },
    "active_cache_entries": 1,
    "average_security_score": 63.64
  },
  "status": "success"
}
```

### **POST /api/seed**
Seed database with initial server data:
```json
{
  "success": true,
  "servers_stored": 10,
  "total_servers": 10
}
```

## 🎯 How to Use

### **1. Start the Application**
```bash
# Install dependencies
pip install -r requirements.txt

# Seed the database (optional but recommended)
python seed_database.py

# Start the web application
python run_web_app.py
```

### **2. Access the Web Interface**
- Open http://localhost:8000 in your browser
- You'll see the modern, interactive interface

### **3. Discover Servers**
- Enter your prompt describing what you want your agent to do
- Click "Discover Servers" to find relevant MCP servers
- Review the results with security scores and recommendations

### **4. Connect to a Server**
- Click "Connect Agent" on your preferred server
- Choose your framework (LangChain, AutoGen, LangGraph, Custom)
- Generate and download ready-to-use code
- Follow the setup instructions

### **5. Monitor Performance**
- Check http://localhost:8000/api/stats for database metrics
- Monitor cache performance and server statistics

## 🗄️ Database Features

### **Intelligent Caching**
- **24-Hour Cache**: Discovery results cached for 24 hours
- **Instant Responses**: Cached queries return in < 100ms
- **Smart Updates**: Only crawls when cache expires
- **Automatic Cleanup**: Expired cache entries removed

### **Server Storage**
- **Persistent Data**: Server metadata stored permanently
- **Source Tracking**: Track servers by discovery source
- **Security Scoring**: Store and retrieve security metrics
- **Activity Monitoring**: Track server maintenance activity

### **Performance Optimization**
- **Database Indexes**: Fast query performance
- **JSON Storage**: Flexible metadata storage
- **Async Operations**: Non-blocking database queries
- **Connection Pooling**: Efficient database connections

## 🔒 Security Features

### **Security Scoring**
- **Transparent Rubric**: Clear scoring methodology
- **Multiple Factors**: Authentication, SBOM, rate limiting, etc.
- **Visual Indicators**: Color-coded security levels
- **Detailed Breakdown**: Component-by-component scoring

### **Data Protection**
- **No Sensitive Storage**: Credentials not stored in database
- **Environment Variables**: Secure configuration management
- **Input Validation**: Request validation and sanitization
- **Error Handling**: Secure error responses

## 📊 Performance Metrics

### **Response Times**
- **First Query**: 2-3 seconds (fresh discovery + caching)
- **Cached Queries**: < 100ms (instant response)
- **Code Generation**: < 1 second
- **Web Interface**: Real-time updates

### **Caching Performance**
- **Cache Hit Rate**: 90%+ for repeated queries
- **Cache Duration**: 24 hours
- **Database Size**: Lightweight SQLite storage
- **Memory Usage**: Efficient data structures

## 🚀 Deployment

### **Local Development**
```bash
# Development with hot reload
python run_web_app.py
```

### **Production Deployment**
```bash
# Install dependencies
pip install -r requirements.txt

# Seed database
python seed_database.py

# Run with production settings
uvicorn src.mcp_multiagent_selector.web_app:app --host 0.0.0.0 --port 8000
```

### **Environment Variables**
```bash
# Database configuration
DATABASE_URL=sqlite:///mcp_guardian.db

# API configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# External APIs
GITHUB_TOKEN=your_github_token_here
```

## 🔧 Troubleshooting

### **Common Issues**

**Database Connection Errors:**
- Ensure SQLite is available
- Check file permissions for database file
- Verify database path configuration

**Import Errors:**
- Install all dependencies: `pip install -r requirements.txt`
- Check Python version (3.10+ required)
- Verify virtual environment activation

**Performance Issues:**
- Seed database with initial data
- Check cache hit rates via /api/stats
- Monitor database size and cleanup

**Web Interface Issues:**
- Clear browser cache
- Check browser console for errors
- Verify all static files are served correctly

### **Debug Mode**
```bash
# Enable debug mode
export DEBUG=true
python run_web_app.py
```

## 📈 Monitoring

### **Health Checks**
- **Application Health**: /api/health
- **Database Status**: /api/stats
- **Cache Performance**: Monitor cache hit rates
- **Response Times**: Track API performance

### **Logs**
- **Application Logs**: FastAPI logging
- **Database Logs**: SQLite query logging
- **Error Tracking**: Exception handling and reporting
- **Performance Logs**: Response time monitoring

---

**MCP Guardian Web Application** - Making MCP server discovery and connection fast, secure, and user-friendly! 🚀✨ 