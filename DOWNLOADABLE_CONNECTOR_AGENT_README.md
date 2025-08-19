# MCP Guardian Connector Agent - Downloadable Version

## 🚀 Overview

This is a **standalone, downloadable version** of the MCP Guardian connector agent that generates production-ready code for connecting to MCP (Model Context Protocol) servers.

## 📁 What You Get

When you run the downloadable connector agent, it generates these files:

### 1. **Agent Code** (`google_drive_mcp_server_agent.py`)
- Complete, runnable LangChain agent code
- Ready-to-use Python script
- Includes all necessary imports and dependencies
- Interactive command-line interface

### 2. **Setup Instructions** (`google_drive_mcp_server_setup_instructions.md`)
- Step-by-step installation guide
- Environment variable configuration
- Security best practices
- Usage instructions

### 3. **Requirements** (`google_drive_mcp_server_requirements.txt`)
- Python package dependencies
- Version specifications for compatibility
- Ready for `pip install -r requirements.txt`

### 4. **Environment Template** (`google_drive_mcp_server_env_template.txt`)
- Template for environment variables
- API key configuration
- Authentication setup
- Copy to `.env` and fill in your credentials

## 🛠️ How to Use

### Step 1: Generate the Files
```bash
python downloadable_connector_agent.py
```

### Step 2: Install Dependencies
```bash
pip install -r google_drive_mcp_server_requirements.txt
```

### Step 3: Set Up Environment Variables
```bash
# Copy the template
cp google_drive_mcp_server_env_template.txt .env

# Edit .env with your actual credentials
nano .env
```

### Step 4: Run the Agent
```bash
python google_drive_mcp_server_agent.py
```

## 🔧 Features

### ✅ **Complete Code Generation**
- LangChain agent implementation
- MCP server integration
- Tool creation and management
- Error handling and logging

### ✅ **Multiple Authentication Models**
- OAuth2 support
- API key authentication
- Username/password authentication
- Secure credential management

### ✅ **Smart Capability Detection**
- Automatically detects server capabilities
- Generates appropriate tool descriptions
- Customizes agent behavior based on task

### ✅ **Production Ready**
- Proper error handling
- Connection management
- Resource cleanup
- Security best practices

## 📋 Example Generated Code

The generated agent includes:

```python
class GoogleDriveMcpServerAgent:
    """Agent for google-drive-mcp-server operations"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.session = None
        self.agent_executor = None
    
    async def connect_to_server(self):
        """Connect to the MCP server"""
        # Connection logic here
    
    async def run(self, user_input: str) -> str:
        """Run the agent with user input"""
        # Agent execution logic here
```

## 🔐 Security Features

### **Environment Variables**
- All credentials stored in `.env` file
- No hardcoded secrets in code
- Secure credential management

### **Authentication Support**
- OAuth2 for enterprise applications
- API key authentication
- Username/password for legacy systems

### **Best Practices**
- Input validation
- Error handling
- Secure connection management
- Resource cleanup

## 🎯 Use Cases

### **File Operations**
- Upload/download files
- File sharing and collaboration
- Document management
- Cloud storage integration

### **Email Management**
- Send/receive emails
- Email automation
- Contact management
- Calendar integration

### **Database Operations**
- Query databases
- Data manipulation
- Schema management
- Backup and restore

### **Search Operations**
- Web search
- Document search
- Index management
- Content discovery

## 🚀 Quick Start

1. **Download the connector agent:**
   ```bash
   # The file is already in your project
   python downloadable_connector_agent.py
   ```

2. **Install dependencies:**
   ```bash
   pip install -r google_drive_mcp_server_requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp google_drive_mcp_server_env_template.txt .env
   # Edit .env with your credentials
   ```

4. **Run the agent:**
   ```bash
   python google_drive_mcp_server_agent.py
   ```

5. **Interact with the agent:**
   ```
   🤖 You: Upload a file to Google Drive
   📤 Agent: I'll help you upload a file to Google Drive...
   ```

## 🔗 Integration with Web App

This downloadable version works alongside the **MCP Guardian Web Application**:

- **Web App**: Discover and analyze MCP servers
- **Connector Agent**: Generate runnable code for selected servers
- **Downloadable Files**: Standalone, production-ready agents

### **Web App Features:**
- Server discovery and recommendation
- Security analysis and scoring
- Interactive code generation
- Real-time connector agent

### **Downloadable Features:**
- Standalone agent code
- Complete setup instructions
- Configuration templates
- Production deployment ready

## 📚 Documentation

### **Generated Files:**
- `google_drive_mcp_server_agent.py` - Main agent code
- `google_drive_mcp_server_setup_instructions.md` - Setup guide
- `google_drive_mcp_server_requirements.txt` - Dependencies
- `google_drive_mcp_server_env_template.txt` - Environment template

### **Key Components:**
- **ConnectorAgent Class**: Main code generation logic
- **LangChain Integration**: Agent framework integration
- **MCP Protocol**: Server communication
- **Authentication**: Secure credential management

## 🎉 Benefits

### **For Developers:**
- ✅ **Zero Configuration**: Generated code works out of the box
- ✅ **Production Ready**: Includes error handling and security
- ✅ **Framework Agnostic**: Supports multiple agent frameworks
- ✅ **Customizable**: Easy to modify and extend

### **For Organizations:**
- ✅ **Security First**: Built-in security best practices
- ✅ **Scalable**: Designed for production deployment
- ✅ **Maintainable**: Clean, well-documented code
- ✅ **Compliant**: Follows industry standards

## 🔄 Updates and Maintenance

The connector agent is designed to be:
- **Self-contained**: No external dependencies for code generation
- **Version controlled**: Track changes to generated code
- **Updatable**: Easy to regenerate with new features
- **Backward compatible**: Maintains compatibility with existing deployments

## 📞 Support

For issues or questions:
1. Check the generated setup instructions
2. Review the code comments
3. Test with simple queries first
4. Enable verbose logging for debugging

## 🎯 Next Steps

1. **Run the connector agent** to generate your files
2. **Install dependencies** and configure environment
3. **Test the agent** with simple queries
4. **Customize** the code for your specific needs
5. **Deploy** to production environment

---

**Generated by MCP Guardian - AI-powered security-first MCP server discovery** 🛡️✨ 