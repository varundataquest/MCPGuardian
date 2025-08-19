# MCP Guardian Architecture 🏗️

**AI-powered security-first MCP server discovery and connection system**

## 🎯 System Overview

MCP Guardian is a modern web application that provides intelligent MCP server discovery, security analysis, and code generation. The system uses a sophisticated caching layer to ensure fast responses while maintaining comprehensive server discovery capabilities.

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Guardian System                          │
├─────────────────────────────────────────────────────────────────┤
│  🌐 Web Interface (Vue.js + Tailwind CSS)                      │
│  ├── Interactive server discovery                              │
│  ├── Real-time security scoring                                │
│  ├── Framework selection (LangChain, AutoGen, LangGraph)       │
│  └── Code generation and download                              │
├─────────────────────────────────────────────────────────────────┤
│  🚀 FastAPI Backend                                            │
│  ├── RESTful API endpoints                                     │
│  ├── WebSocket support for real-time updates                   │
│  ├── Request validation and error handling                     │
│  └── Static file serving                                       │
├─────────────────────────────────────────────────────────────────┤
│  🗄️ Database Layer (SQLite)                                    │
│  ├── Server storage and metadata                               │
│  ├── Discovery result caching                                  │
│  ├── Performance optimization                                   │
│  └── Automatic cache management                                │
├─────────────────────────────────────────────────────────────────┤
│  🔍 Discovery Engine                                           │
│  ├── Multi-source server discovery                             │
│  ├── Intelligent filtering and ranking                         │
│  ├── Security analysis and scoring                             │
│  └── Relevance-based selection                                 │
├─────────────────────────────────────────────────────────────────┤
│  🔗 External Sources                                           │
│  ├── GitHub repositories                                       │
│  ├── MCP registry                                              │
│  ├── Community servers                                         │
│  └── Enhanced mock database                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Component Architecture

### 🌐 Frontend Layer

**Technology Stack:**
- **Vue.js 3**: Reactive JavaScript framework
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API communication
- **Font Awesome**: Icons and visual elements

**Key Features:**
- Responsive design for all devices
- Real-time server discovery interface
- Interactive security score visualization
- Framework selection and code generation
- Downloadable agent code and instructions

### 🚀 Backend Layer

**Technology Stack:**
- **FastAPI**: Modern, fast web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation and serialization
- **Jinja2**: Template engine for HTML rendering

**API Endpoints:**
```
POST /api/discover     - Discover MCP servers with caching
POST /api/connect      - Generate connection code
GET  /api/health       - Health check
GET  /api/stats        - Database statistics
POST /api/seed         - Seed database with initial data
GET  /                 - Web interface
GET  /docs             - API documentation
WS   /ws               - WebSocket endpoint
```

### 🗄️ Database Layer

**Technology Stack:**
- **SQLite**: Lightweight, file-based database
- **Async SQLite**: Asynchronous database operations
- **JSON Storage**: Flexible data storage for server metadata

**Database Schema:**

```sql
-- Servers table
CREATE TABLE servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    endpoint TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL,
    auth_model TEXT,
    activity INTEGER DEFAULT 5,
    capabilities TEXT,  -- JSON array
    security_data TEXT, -- JSON object
    security_score INTEGER DEFAULT 0,
    recommendation_level TEXT DEFAULT 'FAIR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Discovery cache table
CREATE TABLE discovery_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,
    max_servers INTEGER DEFAULT 10,
    results TEXT,  -- JSON array of server names
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

**Database Features:**
- **Intelligent Caching**: 24-hour cache for discovery results
- **Performance Indexes**: Optimized queries for fast responses
- **Automatic Cleanup**: Expired cache entry removal
- **Statistics Tracking**: Comprehensive database metrics

### 🔍 Discovery Engine

**Multi-Source Discovery:**
1. **GitHub Repositories**: Real MCP servers from GitHub
2. **MCP Registry**: Official MCP registry and documentation
3. **Community Servers**: Curated community-contributed servers
4. **Enhanced Mock Database**: 20+ servers across categories

**Discovery Process:**
```
1. Check Cache → 2. Fresh Discovery → 3. Filter & Rank → 4. Store & Cache
```

**Server Categories:**
- **File Operations**: Google Drive, AWS S3, Dropbox, OneDrive
- **Email & Communication**: Gmail, Outlook, SendGrid, Slack
- **Database**: PostgreSQL, MySQL, MongoDB
- **Search & Analytics**: Elasticsearch, Algolia
- **AI/ML**: OpenAI, Anthropic Claude
- **Productivity**: Notion, GitHub, Jira, Calendar, Sheets

### 🔗 Connector Agent

**Framework Support:**
- **LangChain**: Traditional agent framework
- **AutoGen**: Multi-agent conversation framework
- **LangGraph**: Stateful workflow framework
- **Custom**: Simple direct server connections

**Code Generation:**
- Ready-to-run agent code
- Complete setup instructions
- Environment configuration templates
- Requirements and dependencies

## 🔒 Security Architecture

### Security Scoring Rubric

**Scoring Components (0-100 points):**
- **Authentication (25 points)**: OAuth2, API key, username/password
- **Hash Pinning (15 points)**: Certificate pinning for secure connections
- **SBOM/AIBOM (10 points)**: Software bill of materials
- **Rate Limiting (10 points)**: Protection against abuse
- **Observability (10 points)**: Comprehensive logging and monitoring
- **Update Cadence (10 points)**: Maintainer activity and updates
- **Documentation (10 points)**: Quality and completeness of docs
- **Community Trust (10 points)**: Community adoption and reviews

**Recommendation Levels:**
- **EXCELLENT (80-100)**: Highly secure, well-maintained
- **GOOD (60-79)**: Good security practices, active development
- **FAIR (40-59)**: Basic security, limited activity
- **POOR (0-39)**: Security concerns, inactive maintenance

### Security Features

**Data Protection:**
- No sensitive data storage in database
- Environment variable configuration
- Secure credential management
- Input validation and sanitization

**Network Security:**
- HTTPS enforcement
- Rate limiting and abuse protection
- Request validation and error handling
- Secure external API communication

## 📈 Performance Architecture

### Caching Strategy

**Multi-Level Caching:**
1. **Database Cache**: 24-hour discovery result caching
2. **Server Storage**: Persistent server metadata storage
3. **Query Optimization**: Indexed database queries
4. **Response Caching**: FastAPI response caching

**Performance Metrics:**
- **First Query**: 2-3 seconds (fresh discovery + caching)
- **Cached Queries**: < 100ms (instant response)
- **Database Size**: Lightweight SQLite storage
- **Cache Hit Rate**: 90%+ for repeated queries

### Scalability Considerations

**Horizontal Scaling:**
- Stateless FastAPI application
- Database can be migrated to PostgreSQL/MySQL
- Redis for distributed caching
- Load balancer support

**Vertical Scaling:**
- Async/await for concurrent requests
- Connection pooling for database
- Memory-efficient data structures
- Optimized query patterns

## 🔧 Development Architecture

### Project Structure

```
📦 MCP Guardian
├── 🌐 Web Application Core
│   ├── src/mcp_multiagent_selector/
│   │   ├── web_app.py          # Main FastAPI application
│   │   └── database.py         # Database and caching layer
│   ├── run_web_app.py          # Application launcher
│   ├── seed_database.py        # Database seeding script
│   ├── templates/index.html    # Vue.js frontend
│   └── static/style.css        # Enhanced styling
├── Connector Agents
│   ├── connector_agent_direct.py      # Enhanced connector
│   └── downloadable_connector_agent.py # Standalone generator
├── 📚 Documentation
│   ├── README.md                      # Main documentation
│   ├── ARCHITECTURE.md                # This file
│   ├── WEB_APP_README.md              # Web app guide
│   └── DOWNLOADABLE_CONNECTOR_AGENT_README.md
├── ⚙️ Configuration
│   ├── pyproject.toml                 # Project configuration
│   ├── requirements.txt               # Dependencies
│   ├── env.example                    # Environment template
│   └── .gitignore                     # File exclusions
└── 🔧 Development
    └── .pre-commit-config.yaml        # Code quality
```

### Development Workflow

**Local Development:**
1. Clone repository and install dependencies
2. Seed database with initial data
3. Run web application with hot reload
4. Access web interface and API documentation

**Testing Strategy:**
- Unit tests for core components
- Integration tests for API endpoints
- End-to-end tests for web interface
- Performance tests for caching

**Deployment:**
- Docker containerization support
- Environment-based configuration
- Health checks and monitoring
- Logging and error tracking

## 🚀 Deployment Architecture

### Production Setup

**Recommended Stack:**
- **Web Server**: Nginx reverse proxy
- **Application**: FastAPI with Uvicorn
- **Database**: SQLite (can be upgraded to PostgreSQL)
- **Caching**: Redis (optional for distributed caching)
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured logging with JSON format

**Environment Variables:**
```bash
# Database
DATABASE_URL=sqlite:///mcp_guardian.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# External APIs
GITHUB_TOKEN=your_github_token_here

# Security
SECRET_KEY=your_secret_key_here
CORS_ORIGINS=https://yourdomain.com
```

### Monitoring and Observability

**Health Checks:**
- Application health endpoint
- Database connectivity checks
- External API availability
- Cache performance metrics

**Metrics Collection:**
- Request/response times
- Cache hit/miss rates
- Database query performance
- Error rates and types

**Logging Strategy:**
- Structured JSON logging
- Request/response logging
- Error tracking and alerting
- Performance monitoring

## 🔮 Future Architecture

### Planned Enhancements

**Advanced Features:**
- **Machine Learning**: Intelligent server recommendations
- **Real-time Updates**: WebSocket-based live updates
- **Advanced Caching**: Redis-based distributed caching
- **API Rate Limiting**: Sophisticated rate limiting strategies

**Scalability Improvements:**
- **Microservices**: Service decomposition
- **Event-Driven**: Event sourcing and CQRS
- **GraphQL**: Flexible API querying
- **Real-time Analytics**: Live performance monitoring

**Security Enhancements:**
- **OAuth Integration**: User authentication
- **Role-Based Access**: Permission management
- **Audit Logging**: Comprehensive audit trails
- **Vulnerability Scanning**: Automated security checks

---

**MCP Guardian** - A modern, scalable, and secure architecture for MCP server discovery and connection! 🚀✨ 