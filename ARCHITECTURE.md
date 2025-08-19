# MCP Multi-Agent Selector - System Architecture

## 🏗️ Overview

The MCP Multi-Agent Selector is a sophisticated system that orchestrates a LangGraph multi-agent workflow to discover, analyze, and rank MCP (Model Context Protocol) servers based on security criteria. It provides both an MCP server interface and a connector agent for seamless integration.

## 🎯 Core Purpose

Given a natural language task (e.g., "deploy web apps with one-click"), the system:
1. **Discovers** relevant MCP servers from multiple registries
2. **Analyzes** each server's security posture using a transparent rubric
3. **Ranks** servers by security score (0-100)
4. **Connects** users' agents to the best MCP servers

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Multi-Agent Selector                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │   User Input    │    │   MCP Server    │    │   Connector Agent       │  │
│  │                 │    │   Interface     │    │                         │  │
│  │ • Natural       │───▶│ • run_selection │───▶│ • Interactive Setup     │  │
│  │   Language      │    │   _pipeline     │    │ • Code Generation       │  │
│  │ • Task Desc     │    │ • get_results   │    │ • Framework Support     │  │
│  │                 │    │ • connect_agent │    │ • Ready-to-Run Agent    │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                        LangGraph Workflow                              │  │
│  │                                                                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │  │   Manager   │─▶│   Crawler   │─▶│   Writer    │─▶│  Security   │    │  │
│  │  │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │    │  │
│  │  │             │  │             │  │             │  │             │    │  │
│  │  │ • Task      │  │ • Registry  │  │ • Evidence  │  │ • Scoring   │    │  │
│  │  │   Analysis  │  │   Crawling  │  │   Writing   │  │ • Rubric    │    │  │
│  │  │ • Planning  │  │ • Web       │  │ • Database  │  │ • Ranking   │    │  │
│  │  │             │  │   Crawling  │  │   Storage   │  │             │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │  │
│  │                                    │                                    │  │
│  │                                    ▼                                    │  │
│  │                            ┌─────────────┐                              │  │
│  │                            │  Finalizer  │                              │  │
│  │                            │   Agent     │                              │  │
│  │                            │             │                              │  │
│  │                            │ • Results   │                              │  │
│  │                            │ • Ranking   │                              │  │
│  │                            │ • Summary   │                              │  │
│  │                            └─────────────┘                              │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                           Data Layer                                   │  │
│  │                                                                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │  │   Servers   │  │  Evidence   │  │   Scores    │  │    Runs     │    │  │
│  │  │             │  │             │  │             │  │             │    │  │
│  │  │ • MCP       │  │ • Security  │  │ • Security  │  │ • Pipeline  │    │  │
│  │  │   Servers   │  │   Evidence  │  │   Scores    │  │   History   │    │  │
│  │  │ • Metadata  │  │ • Analysis  │  │ • Rubric    │  │ • Results   │    │  │
│  │  │ • Endpoints │  │ • Docs      │  │ • Rankings  │  │ • Status    │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                        External Services                               │  │
│  │                                                                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │  │   LLM APIs  │  │   MCP       │  │   Web       │  │   Smithery  │    │  │
│  │  │             │  │  Registries │  │   Crawlers  │  │     API     │    │  │
│  │  │ • OpenAI    │  │             │  │             │  │             │    │  │
│  │  │ • Anthropic │  │ • mcp.dev   │  │ • httpx     │  │ • Curated   │    │  │
│  │  │ • Azure     │  │ • GitHub    │  │ • Playwright│  │   Servers   │    │  │
│  │  │             │  │ • Vercel    │  │ • Beautiful │  │ • Enhanced  │    │  │
│  │  └─────────────┘  └─────────────┘  │   Soup      │  │   Discovery │    │  │
│  │                                    └─────────────┘  └─────────────┘    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔧 Component Details

### 1. **MCP Server Interface** (`src/mcp_multiagent_selector/mcp_server/`)
- **Purpose**: Exposes the system as an MCP server
- **Tools**:
  - `run_selection_pipeline`: Main pipeline execution
  - `get_last_results`: Retrieve historical results
  - `connect_agent_instructions`: Get connection instructions
  - `health`: Health check endpoint
- **Protocol**: MCP (Model Context Protocol) over stdio

### 2. **LangGraph Workflow** (`src/mcp_multiagent_selector/graph/`)
- **Manager Agent**: Analyzes user task, plans discovery strategy
- **Crawler Agent**: Searches MCP registries and web for relevant servers
- **Writer Agent**: Extracts evidence, writes to database
- **Security Agent**: Scores servers using security rubric
- **Finalizer Agent**: Ranks results, generates summary

### 3. **Data Models** (`src/mcp_multiagent_selector/models.py`)
- **Server**: MCP server metadata and endpoints
- **Evidence**: Security evidence and analysis
- **Score**: Security scores with detailed rubric
- **Run**: Pipeline execution history

### 4. **Security Scoring** (`src/mcp_multiagent_selector/security/`)
- **Transparent Rubric**: 0-100 point system
- **Categories**:
  - Signature/attestation (+25)
  - HTTPS/mTLS (+15)
  - Hash pinning (+15)
  - Update cadence (+10)
  - Least-privilege docs (+10)
  - SBOM/AI-BOM (+10)
  - Rate limiting (+5)
  - Observability (+5)
  - CVE penalties (-30 max)

### 5. **Crawling System** (`src/mcp_multiagent_selector/crawl/`)
- **Registry Crawler**: Fetches from MCP registries
- **Web Crawler**: Extracts documentation using httpx/Playwright
- **Extraction**: Heuristic metadata extraction
- **Smithery Integration**: Enhanced discovery via Smithery API

### 6. **Connector Agent** (`connector_agent_direct.py`)
- **Interactive Setup**: Guides users through configuration
- **Framework Support**: LangChain, LangGraph, AutoGen, Custom
- **Code Generation**: Creates ready-to-run agent code
- **File Generation**: Complete project setup

## 🔄 Data Flow

### 1. **Pipeline Execution**
```
User Task → MCP Server → LangGraph Workflow → Database → Results
```

### 2. **Agent Connection**
```
User Requirements → Connector Agent → Generated Agent → MCP Server Integration
```

### 3. **Security Analysis**
```
Server Discovery → Evidence Collection → Security Scoring → Ranking → Results
```

## 🗄️ Database Schema

### Tables
- **`servers`**: MCP server information
- **`evidence`**: Security evidence and analysis
- **`scores`**: Security scores with rubric breakdown
- **`runs`**: Pipeline execution history

### Relationships
- Server → Evidence (1:1)
- Server → Scores (1:many)
- Run → Results (1:1)

## 🚀 Deployment Architecture

### Docker Compose Services
- **`db`**: PostgreSQL 16 database
- **`server`**: MCP Multi-Agent Selector application

### Environment Configuration
- Database connection
- LLM API keys (OpenAI, Anthropic, Azure)
- Smithery API integration
- Crawling settings
- MCP server configuration

## 🔌 Integration Points

### 1. **LLM Providers**
- OpenAI GPT-4
- Anthropic Claude
- Azure OpenAI
- Fallback heuristics

### 2. **MCP Registries**
- mcp.dev
- GitHub repositories
- Vercel deployments
- Custom registries

### 3. **External APIs**
- Smithery API (enhanced discovery)
- Web crawling (documentation extraction)

### 4. **Agent Frameworks**
- LangChain
- LangGraph
- AutoGen
- Custom implementations

## 🛡️ Security Features

### 1. **Transparent Scoring**
- Open-source rubric
- Detailed breakdown
- Reproducible results

### 2. **Evidence Collection**
- Documentation analysis
- Security indicator extraction
- Risk assessment

### 3. **Authentication**
- OAuth support
- API key management
- Secure credential handling

## 📊 Monitoring & Observability

### 1. **Health Checks**
- Database connectivity
- External API status
- Pipeline execution status

### 2. **Logging**
- Structured logging
- Error tracking
- Performance metrics

### 3. **Metrics**
- Pipeline execution time
- Server discovery rates
- Security score distributions

## 🔧 Development & Testing

### 1. **Testing Strategy**
- Unit tests for each component
- Integration tests for workflows
- End-to-end pipeline tests
- Connector agent tests

### 2. **Development Tools**
- Poetry for dependency management
- Alembic for database migrations
- Pre-commit hooks for code quality
- Docker for consistent environments

### 3. **CI/CD**
- Automated testing
- Code quality checks
- Docker image building
- Deployment automation

## 🎯 Key Benefits

1. **Automated Discovery**: Finds relevant MCP servers automatically
2. **Security-First**: Transparent security scoring and ranking
3. **Framework Agnostic**: Supports multiple agent frameworks
4. **Ready-to-Use**: Generates complete, runnable agent code
5. **Extensible**: Modular architecture for easy extension
6. **Production Ready**: Comprehensive testing and monitoring

## 🚀 Future Enhancements

1. **Additional Registries**: Support for more MCP registries
2. **Enhanced Scoring**: Machine learning-based security scoring
3. **Real-time Updates**: Live security monitoring
4. **Multi-language Support**: Support for non-Python agents
5. **Advanced Analytics**: Detailed usage and performance analytics
6. **Community Features**: User ratings and reviews 