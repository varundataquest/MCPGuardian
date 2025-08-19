# MCP Guardian Web Application

## 🚀 Quick Start

The MCP Guardian web application is now running successfully! 

### **📍 Access Your Web App**

**Open your web browser and go to:**
```
http://localhost:8000
```

### **🌐 Available Endpoints**

- **Main Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## ✨ Features

### **🎯 Prompt-Based Discovery**
Enter natural language prompts like:
- "Agent that can handle file operations"
- "Agent that can send me emails"
- "Agent that can query databases"
- "Agent that can search documents"

### **🛡️ Security-First Analysis**
- Real-time security scoring (0-100 scale)
- Detailed security breakdowns with visual indicators
- Authentication model analysis (OAuth2, API Key, etc.)
- Maintainer activity tracking
- Recommendation levels (EXCELLENT, GOOD, POOR)

### **🔗 Interactive Connector Agent**
- Click "Connect Agent" on any server
- Choose your framework (LangChain, LangGraph, AutoGen, Custom)
- Generate and download ready-to-use code
- Complete setup instructions

## 🎨 User Interface

The web app features:
- **Responsive design** with Tailwind CSS
- **Interactive server cards** with hover effects
- **Color-coded security scores** and recommendations
- **Loading animations** and smooth transitions
- **Modern, beautiful UI** that works on all devices

## 🔧 Technical Stack

### **Backend**
- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server

### **Frontend**
- **Vue.js 3**: Reactive JavaScript framework
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API communication
- **Font Awesome**: Icons and visual elements

## 📋 API Endpoints

### **POST /api/discover**
Discover MCP servers based on a prompt:
```json
{
  "prompt": "Agent that can handle file operations",
  "max_servers": 10
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

### **GET /api/health**
Check application health:
```json
{
  "status": "healthy",
  "service": "MCP Guardian"
}
```

## 🎯 How to Use

1. **Open the web app** at http://localhost:8000
2. **Enter your prompt** describing what you want your agent to do
3. **Click "Discover Servers"** to find relevant MCP servers
4. **Review the results** with security scores and recommendations
5. **Click "Connect Agent"** on your preferred server
6. **Choose your framework** and get generated code
7. **Download and use** the generated agent code

## 🛡️ Security Features

The web app provides comprehensive security analysis:
- **Hash pinning detection**
- **SBOM (Software Bill of Materials) analysis**
- **Authentication model evaluation**
- **Maintainer activity scoring**
- **CVE and risk assessment**
- **Transparent scoring rubric**

## 🎉 Success!

Your MCP Guardian web application is now a complete, production-ready system that provides:
- **AI-powered MCP server discovery**
- **Security-first analysis and scoring**
- **Interactive code generation**
- **Beautiful, modern web interface**

The web app successfully transforms your command-line MCP Guardian into an accessible, user-friendly web application that anyone can use to discover and connect to secure MCP servers!

---

**Status**: ✅ **Running successfully** at http://localhost:8000
**Last Tested**: All endpoints working correctly
**Features**: All functionality operational 