# MCP Multi-Agent Selector

An MCP server that orchestrates a multi-agent LangGraph workflow to find and rank MCP servers by security score.

## 🎯 Overview

The MCP Multi-Agent Selector is a sophisticated system that uses LangGraph to orchestrate multiple AI agents to:

1. **Crawl** MCP registries and web sources for candidate servers
2. **Analyze** each server's documentation and metadata
3. **Score** servers based on a comprehensive security rubric
4. **Rank** and return the best MCP servers for a given task
5. **Provide** connection instructions for integrating with the selected servers

## 🏗️ Architecture

```
Manager → Crawler → Writer → Security → Finalizer
   ↓        ↓        ↓        ↓         ↓
  Init   Discover  Persist   Score   Return Results
```

### Agents

- **ManagerAgent**: Orchestrates the workflow and tracks execution
- **CrawlerAgent**: Discovers MCP servers from registries and web sources
- **WriterAgent**: Analyzes documentation and persists evidence to PostgreSQL
- **SecurityAgent**: Scores servers using a transparent security rubric
- **FinalizerAgent**: Ranks results and returns the best servers

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (provided via Docker)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd mcp-multiagent-selector
cp env.example .env
# Edit .env with your configuration
```

### 2. Start the Services

```bash
# Start PostgreSQL and the MCP server
docker-compose up --build

# Or use the Makefile
make dev
```

### 3. Run Database Migrations

```bash
# The migrations run automatically on startup, but you can also run manually:
make migrate
```

### 4. Test the System

```bash
# Run tests
make test

# Seed with test data
python scripts/seed.py
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```bash
# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/mcp

# LLM Provider (choose one)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here

# Or use Anthropic
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Crawling Configuration
CRAWL_TIMEOUT_SECS=20
REGISTRIES_URLS=https://registry.1.example/index.json,https://registry.2.example/index.json
MAX_CANDIDATES=50

# MCP Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
```

## 🛠️ Usage

### MCP Tools

The server exposes four main tools:

#### 1. `run_selection_pipeline`

Run the complete pipeline to find and rank MCP servers.

```json
{
  "user_task": "I want to create an agent that can negotiate the best price for a gym membership",
  "max_candidates": 50
}
```

#### 2. `get_last_results`

Retrieve the last N results from the database.

```json
{
  "limit": 10
}
```

#### 3. `connect_agent_instructions`

Get connection instructions for the top-k ranked servers.

```json
{
  "top_k": 3
}
```

#### 4. `health`

Health check endpoint.

```json
{}
```

### Example Usage

```python
# Using the MCP client
from mcp import ClientSession, StdioServerParameters

async with ClientSession(StdioServerParameters(
    command="python", 
    args=["-m", "mcp_multiagent_selector.mcp_server.server"]
)) as session:
    # Run the pipeline
    result = await session.call_tool(
        "run_selection_pipeline",
        {
            "user_task": "Find servers for web scraping and data extraction",
            "max_candidates": 20
        }
    )
    print(result.content[0].text)
```

## 🔒 Security Scoring Rubric

The system uses a transparent scoring rubric (0-100 points):

- **Signature/Attestation** (+25): Code signing, attestation present
- **HTTPS/mTLS** (+15): Secure transport documented
- **Hash Pinning** (+15): Artifact digest references
- **Update Cadence** (+10): Recent commits/releases
- **Least Privilege** (+10): Tool scope clarity in docs
- **SBOM/AI-BOM** (+10): Dependency transparency
- **Rate Limiting** (+5): Abuse controls disclosed
- **Observability** (+5): Traceability docs
- **CVE Penalties** (-30): Known vulnerabilities

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test categories
pytest tests/test_scoring.py -v
pytest tests/test_extract.py -v
pytest tests/test_end_to_end.py -v

# Run with coverage
pytest --cov=src tests/
```

## 📊 Database Schema

### Tables

- **servers**: MCP server information
- **evidence**: Analysis and metadata for each server
- **scores**: Security scores with detailed breakdowns
- **runs**: Pipeline execution history

### Example Queries

```sql
-- Get top ranked servers
SELECT s.name, s.endpoint, sc.score, e.summary
FROM servers s
JOIN scores sc ON s.id = sc.server_id
JOIN evidence e ON s.id = e.server_id
ORDER BY sc.score DESC
LIMIT 10;

-- Get latest run results
SELECT r.user_task, r.result
FROM runs r
WHERE r.status = 'completed'
ORDER BY r.finished_at DESC
LIMIT 1;
```

## 🚀 Deployment

### Docker Compose (Recommended)

```bash
docker-compose up --build -d
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-selector
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-selector
  template:
    metadata:
      labels:
        app: mcp-selector
    spec:
      containers:
      - name: mcp-selector
        image: mcp-multiagent-selector:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          value: "postgresql+psycopg://user:pass@postgres:5432/mcp"
```

### Railway

```bash
# Deploy to Railway
railway up
```

## 🔧 Development

### Setup Development Environment

```bash
# Install dependencies
make install

# Format code
make format

# Lint code
make lint

# Type check
make type-check

# Run all checks
make check
```

### Adding New Registry Sources

1. Extend `RegistryCrawler` in `src/mcp_multiagent_selector/crawl/registries.py`
2. Add your registry URL to `REGISTRIES_URLS` in `.env`
3. Test with `make test`

### Adding New Security Metrics

1. Update the scoring rubric in `src/mcp_multiagent_selector/security/scoring.py`
2. Add extraction logic in `src/mcp_multiagent_selector/crawl/extract.py`
3. Update tests in `tests/test_scoring.py`

## 📈 Performance

- **Pipeline Execution**: ~30-60 seconds for 50 candidates
- **Database Queries**: <100ms for typical operations
- **Memory Usage**: ~200MB for typical workloads
- **Concurrent Requests**: Supports multiple concurrent pipeline executions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run `make check`
6. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: This README and inline code comments
- **Examples**: See `scripts/seed.py` for usage examples

## 🔮 Roadmap

- [ ] Support for more LLM providers (Azure OpenAI, local models)
- [ ] Advanced clustering and similarity analysis
- [ ] Real-time monitoring and alerting
- [ ] Integration with more MCP registries
- [ ] Web UI for pipeline monitoring
- [ ] Advanced caching and performance optimizations
- [ ] Support for custom scoring rubrics
- [ ] Integration with CI/CD pipelines for automated security scanning



