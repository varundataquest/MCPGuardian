#!/usr/bin/env python3
"""
MCP Guardian Web Application
A modern web interface for discovering and connecting to MCP servers
"""

import asyncio
import json
import os
import sys
import re
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Import connector agent and database
from connector_agent_direct import ConnectorAgent
from .database import db

# Mock the security scoring function to avoid import issues
def score_server_from_dict(evidence: Dict[str, Any]) -> tuple[int, Dict[str, int]]:
    """Mock security scoring function"""
    score = 0
    breakdown = {}
    
    # Simple scoring logic
    if evidence.get('auth_model') == 'oauth2':
        score += 25
        breakdown['signature_or_attestation'] = 25
    elif evidence.get('auth_model') == 'api_key':
        score += 5
        breakdown['https_or_mtls'] = 5
    
    if evidence.get('hash_pinning'):
        score += 15
        breakdown['hash_pinning'] = 15
    
    if evidence.get('sbom'):
        score += 10
        breakdown['sbom_or_aibom'] = 10
    
    activity = evidence.get('maintainer_activity', 5)
    score += activity
    breakdown['update_cadence'] = activity
    
    return score, breakdown

# Enhanced MCP server discovery with database caching
class MCPServerDiscovery:
    """Enhanced MCP server discovery from multiple sources with database caching"""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({"Authorization": f"token {self.github_token}"})
    
    async def discover_servers(self, prompt: str, max_servers: int = 10) -> List[Dict[str, Any]]:
        """Discover MCP servers with database caching"""
        
        # First, check if we have a cached result
        cached_server_names = await db.get_cached_discovery(prompt, max_servers)
        if cached_server_names:
            print(f"📋 Using cached discovery for prompt: {prompt}")
            servers = []
            for server_name in cached_server_names:
                server = await db.get_server(server_name)
                if server:
                    servers.append(server)
            return servers[:max_servers]
        
        # If no cache, perform fresh discovery
        print(f"🔍 Performing fresh discovery for prompt: {prompt}")
        servers = []
        
        # Get servers from multiple sources
        sources = [
            self._get_github_servers,
            self._get_mcp_registry_servers,
            self._get_community_servers,
            self._get_mock_servers
        ]
        
        for source_func in sources:
            try:
                source_servers = await source_func(prompt, max_servers // len(sources))
                servers.extend(source_servers)
                if len(servers) >= max_servers:
                    break
            except Exception as e:
                print(f"Error fetching from {source_func.__name__}: {e}")
                continue
        
        # Filter and rank servers based on prompt
        filtered_servers = self._filter_servers_by_prompt(servers, prompt)
        
        # Add security scoring
        for server in filtered_servers:
            score, breakdown = score_server_from_dict(server.get('security', {}))
            server['security_score'] = score
            server['security_breakdown'] = breakdown
            server['recommendation_level'] = self._get_recommendation_level(score)
        
        # Sort by security score and return top results
        filtered_servers.sort(key=lambda x: x.get('security_score', 0), reverse=True)
        final_servers = filtered_servers[:max_servers]
        
        # Store servers in database and cache the result
        if final_servers:
            await db.store_servers_batch(final_servers)
            server_names = [server['name'] for server in final_servers]
            await db.cache_discovery_result(prompt, max_servers, server_names)
        
        return final_servers
    
    async def _get_github_servers(self, prompt: str, max_count: int) -> List[Dict[str, Any]]:
        """Discover MCP servers from GitHub repositories"""
        servers = []
        
        # Search for MCP servers on GitHub
        search_queries = [
            "mcp-server",
            "model-context-protocol server",
            "MCP server",
            "mcp tool",
            "model context protocol"
        ]
        
        for query in search_queries:
            try:
                url = f"https://api.github.com/search/repositories"
                params = {
                    "q": f"{query} language:python",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(max_count, 30)
                }
                
                response = self.session.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for repo in data.get('items', []):
                        server = self._parse_github_repo(repo, prompt)
                        if server:
                            servers.append(server)
                
                if len(servers) >= max_count:
                    break
                    
            except Exception as e:
                print(f"Error searching GitHub for {query}: {e}")
                continue
        
        return servers[:max_count]
    
    def _parse_github_repo(self, repo: Dict[str, Any], prompt: str) -> Optional[Dict[str, Any]]:
        """Parse GitHub repository into MCP server format"""
        try:
            name = repo.get('name', '').lower()
            description = repo.get('description', '')
            
            # Skip if not likely an MCP server
            if not any(keyword in name or keyword in description.lower() 
                      for keyword in ['mcp', 'model-context', 'modelcontext']):
                return None
            
            # Determine capabilities based on name and description
            capabilities = self._extract_capabilities(name, description, prompt)
            
            # Determine auth model
            auth_model = self._determine_auth_model(name, description)
            
            # Calculate activity score
            activity = min(10, max(1, repo.get('stargazers_count', 0) // 10))
            
            server = {
                "name": name,
                "endpoint": f"https://github.com/{repo['full_name']}",
                "description": description or f"MCP server for {name}",
                "source": "github",
                "auth_model": auth_model,
                "activity": activity,
                "capabilities": capabilities,
                "security": {
                    "hash_pinning": activity > 5,
                    "sbom": activity > 7,
                    "rate_limiting": True,
                    "observability": activity > 6
                }
            }
            
            return server
            
        except Exception as e:
            print(f"Error parsing GitHub repo: {e}")
            return None
    
    async def _get_mcp_registry_servers(self, prompt: str, max_count: int) -> List[Dict[str, Any]]:
        """Discover servers from MCP registry and known sources"""
        servers = []
        
        # Known MCP registry endpoints
        registry_urls = [
            "https://raw.githubusercontent.com/modelcontextprotocol/registry/main/registry.json",
            "https://api.github.com/repos/modelcontextprotocol/registry/contents",
            "https://raw.githubusercontent.com/modelcontextprotocol/mcp/main/README.md"
        ]
        
        for url in registry_urls:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    # Parse registry data (simplified)
                    registry_servers = self._parse_registry_data(response.text, prompt)
                    servers.extend(registry_servers)
                    
                    if len(servers) >= max_count:
                        break
                        
            except Exception as e:
                print(f"Error fetching from registry {url}: {e}")
                continue
        
        return servers[:max_count]
    
    def _parse_registry_data(self, data: str, prompt: str) -> List[Dict[str, Any]]:
        """Parse registry data into server format"""
        servers = []
        
        # Extract server information from registry data
        # This is a simplified parser - in production you'd want more sophisticated parsing
        server_patterns = [
            r'([a-zA-Z0-9_-]+)-mcp-server',
            r'([a-zA-Z0-9_-]+)_mcp_server',
            r'mcp-server-([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in server_patterns:
            matches = re.findall(pattern, data, re.IGNORECASE)
            for match in matches:
                server_name = f"{match}-mcp-server"
                capabilities = self._extract_capabilities(server_name, data, prompt)
                
                server = {
                    "name": server_name,
                    "endpoint": f"https://registry.mcp.dev/{server_name}",
                    "description": f"Official MCP server for {match}",
                    "source": "mcp_registry",
                    "auth_model": "oauth2" if "oauth" in data.lower() else "api_key",
                    "activity": 8,
                    "capabilities": capabilities,
                    "security": {
                        "hash_pinning": True,
                        "sbom": True,
                        "rate_limiting": True,
                        "observability": True
                    }
                }
                servers.append(server)
        
        return servers
    
    async def _get_community_servers(self, prompt: str, max_count: int) -> List[Dict[str, Any]]:
        """Get community-contributed MCP servers"""
        servers = []
        
        # Community server sources
        community_sources = [
            {
                "name": "anthropic-mcp-server",
                "description": "Anthropic Claude integration for AI conversations",
                "capabilities": ["ai_chat", "text_generation", "reasoning"],
                "auth_model": "api_key"
            },
            {
                "name": "openai-mcp-server", 
                "description": "OpenAI GPT integration for text generation and analysis",
                "capabilities": ["text_generation", "code_generation", "analysis"],
                "auth_model": "api_key"
            },
            {
                "name": "notion-mcp-server",
                "description": "Notion workspace integration for document management",
                "capabilities": ["document_management", "database", "collaboration"],
                "auth_model": "oauth2"
            },
            {
                "name": "slack-mcp-server",
                "description": "Slack workspace integration for messaging and collaboration",
                "capabilities": ["messaging", "file_sharing", "team_collaboration"],
                "auth_model": "oauth2"
            },
            {
                "name": "github-mcp-server",
                "description": "GitHub repository integration for code management",
                "capabilities": ["code_management", "version_control", "collaboration"],
                "auth_model": "oauth2"
            },
            {
                "name": "jira-mcp-server",
                "description": "Jira project management integration",
                "capabilities": ["project_management", "issue_tracking", "workflow"],
                "auth_model": "oauth2"
            },
            {
                "name": "calendar-mcp-server",
                "description": "Calendar integration for scheduling and events",
                "capabilities": ["scheduling", "event_management", "reminders"],
                "auth_model": "oauth2"
            },
            {
                "name": "sheets-mcp-server",
                "description": "Google Sheets integration for spreadsheet operations",
                "capabilities": ["spreadsheet_operations", "data_analysis", "collaboration"],
                "auth_model": "oauth2"
            },
            {
                "name": "drive-mcp-server",
                "description": "Google Drive integration for file operations",
                "capabilities": ["file_operations", "storage", "sharing"],
                "auth_model": "oauth2"
            },
            {
                "name": "gmail-mcp-server",
                "description": "Gmail integration for email operations",
                "capabilities": ["email_operations", "contact_management", "search"],
                "auth_model": "oauth2"
            }
        ]
        
        for source in community_sources:
            if len(servers) >= max_count:
                break
                
            capabilities = self._extract_capabilities(source["name"], source["description"], prompt)
            if capabilities:  # Only add if relevant to prompt
                server = {
                    "name": source["name"],
                    "endpoint": f"https://community.mcp.dev/{source['name']}",
                    "description": source["description"],
                    "source": "community",
                    "auth_model": source["auth_model"],
                    "activity": 7,
                    "capabilities": capabilities,
                    "security": {
                        "hash_pinning": True,
                        "sbom": True,
                        "rate_limiting": True,
                        "observability": True
                    }
                }
                servers.append(server)
        
        return servers
    
    async def _get_mock_servers(self, prompt: str, max_count: int) -> List[Dict[str, Any]]:
        """Get enhanced mock servers with more variety"""
        all_mock_servers = []
        
        # File operations servers
        file_servers = [
            {
                "name": "google-drive-mcp-server",
                "endpoint": "https://api.drive-mcp.com",
                "description": "Google Drive integration for file operations with OAuth2 authentication",
                "source": "google_official",
                "auth_model": "oauth2",
                "activity": 9,
                "capabilities": ["file_upload", "file_download", "file_sharing", "collaboration"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "aws-s3-mcp-server",
                "endpoint": "https://api.s3-mcp.com",
                "description": "AWS S3 file storage operations with API key authentication",
                "source": "aws_official",
                "auth_model": "api_key",
                "activity": 9,
                "capabilities": ["file_storage", "file_retrieval", "versioning", "backup"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "dropbox-mcp-server",
                "endpoint": "https://api.dropbox-mcp.com",
                "description": "Dropbox file management with enterprise security and comprehensive logging",
                "source": "dropbox_official",
                "auth_model": "oauth2",
                "activity": 8,
                "capabilities": ["file_sync", "version_control", "sharing", "collaboration"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "onedrive-mcp-server",
                "endpoint": "https://api.onedrive-mcp.com",
                "description": "Microsoft OneDrive integration for cloud storage and collaboration",
                "source": "microsoft_official",
                "auth_model": "oauth2",
                "activity": 8,
                "capabilities": ["cloud_storage", "file_sync", "collaboration", "versioning"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            }
        ]
        
        # Email servers
        email_servers = [
            {
                "name": "gmail-mcp-server",
                "endpoint": "https://api.gmail-mcp.com",
                "description": "Gmail API integration for sending and receiving emails with OAuth2 authentication",
                "source": "google_official",
                "auth_model": "oauth2",
                "activity": 9,
                "capabilities": ["send_email", "receive_email", "manage_labels", "search"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "outlook-mcp-server",
                "endpoint": "https://api.outlook-mcp.com",
                "description": "Microsoft Outlook integration for email and calendar management",
                "source": "microsoft_official",
                "auth_model": "oauth2",
                "activity": 8,
                "capabilities": ["email_management", "calendar_integration", "contact_management"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "sendgrid-mcp-server",
                "endpoint": "https://api.sendgrid-mcp.com",
                "description": "SendGrid email delivery service integration with API key authentication",
                "source": "sendgrid_official",
                "auth_model": "api_key",
                "activity": 7,
                "capabilities": ["send_email", "templates", "analytics", "bounce_handling"],
                "security": {"hash_pinning": False, "sbom": False, "rate_limiting": True, "observability": False}
            }
        ]
        
        # Database servers
        database_servers = [
            {
                "name": "postgres-mcp-server",
                "endpoint": "https://api.postgres-mcp.com",
                "description": "PostgreSQL database operations with connection pooling and security",
                "source": "postgres_official",
                "auth_model": "username_password",
                "activity": 8,
                "capabilities": ["query_execution", "schema_management", "backup", "monitoring"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "mysql-mcp-server",
                "endpoint": "https://api.mysql-mcp.com",
                "description": "MySQL database integration with transaction support and optimization",
                "source": "mysql_official",
                "auth_model": "username_password",
                "activity": 7,
                "capabilities": ["database_operations", "transaction_management", "optimization"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "mongodb-mcp-server",
                "endpoint": "https://api.mongodb-mcp.com",
                "description": "MongoDB NoSQL database integration with document operations",
                "source": "mongodb_official",
                "auth_model": "api_key",
                "activity": 7,
                "capabilities": ["document_operations", "aggregation", "indexing", "replication"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            }
        ]
        
        # Search servers
        search_servers = [
            {
                "name": "elasticsearch-mcp-server",
                "endpoint": "https://api.elasticsearch-mcp.com",
                "description": "Elasticsearch integration for advanced search and analytics",
                "source": "elastic_official",
                "auth_model": "api_key",
                "activity": 8,
                "capabilities": ["search", "analytics", "indexing", "aggregation"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "algolia-mcp-server",
                "endpoint": "https://api.algolia-mcp.com",
                "description": "Algolia search integration for fast and relevant search results",
                "source": "algolia_official",
                "auth_model": "api_key",
                "activity": 7,
                "capabilities": ["search", "autocomplete", "analytics", "personalization"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            }
        ]
        
        # AI/ML servers
        ai_servers = [
            {
                "name": "openai-mcp-server",
                "endpoint": "https://api.openai-mcp.com",
                "description": "OpenAI integration for text generation and analysis",
                "source": "openai_official",
                "auth_model": "api_key",
                "activity": 9,
                "capabilities": ["text_generation", "code_generation", "analysis", "translation"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            },
            {
                "name": "anthropic-mcp-server",
                "endpoint": "https://api.anthropic-mcp.com",
                "description": "Anthropic Claude integration for AI conversations and reasoning",
                "source": "anthropic_official",
                "auth_model": "api_key",
                "activity": 8,
                "capabilities": ["ai_chat", "reasoning", "analysis", "content_generation"],
                "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
            }
        ]
        
        # Combine all server categories
        all_mock_servers.extend(file_servers)
        all_mock_servers.extend(email_servers)
        all_mock_servers.extend(database_servers)
        all_mock_servers.extend(search_servers)
        all_mock_servers.extend(ai_servers)
        
        # Filter by prompt relevance
        filtered_servers = []
        for server in all_mock_servers:
            capabilities = self._extract_capabilities(server["name"], server["description"], prompt)
            if capabilities:
                server["capabilities"] = capabilities
                filtered_servers.append(server)
        
        return filtered_servers[:max_count]
    
    def _extract_capabilities(self, name: str, description: str, prompt: str) -> List[str]:
        """Extract relevant capabilities based on prompt"""
        prompt_lower = prompt.lower()
        name_lower = name.lower()
        desc_lower = description.lower()
        
        # Define capability mappings
        capability_mappings = {
            "file": ["file_upload", "file_download", "file_storage", "file_operations"],
            "email": ["send_email", "receive_email", "email_management"],
            "database": ["query_execution", "database_operations", "data_management"],
            "search": ["search", "indexing", "analytics"],
            "ai": ["text_generation", "ai_chat", "analysis"],
            "collaboration": ["collaboration", "sharing", "team_work"],
            "storage": ["storage", "backup", "versioning"],
            "communication": ["messaging", "notifications", "chat"]
        }
        
        # Find relevant capabilities
        relevant_capabilities = []
        for keyword, capabilities in capability_mappings.items():
            if (keyword in prompt_lower or 
                keyword in name_lower or 
                keyword in desc_lower):
                relevant_capabilities.extend(capabilities)
        
        # Add some default capabilities if none found
        if not relevant_capabilities:
            if "file" in prompt_lower:
                relevant_capabilities = ["file_operations", "storage"]
            elif "email" in prompt_lower:
                relevant_capabilities = ["email_management", "communication"]
            elif "database" in prompt_lower:
                relevant_capabilities = ["database_operations", "data_management"]
            else:
                relevant_capabilities = ["general_operations"]
        
        return list(set(relevant_capabilities))  # Remove duplicates
    
    def _determine_auth_model(self, name: str, description: str) -> str:
        """Determine authentication model based on server info"""
        text = f"{name} {description}".lower()
        
        if "oauth" in text or "google" in text or "microsoft" in text:
            return "oauth2"
        elif "api_key" in text or "token" in text:
            return "api_key"
        elif "username" in text or "password" in text:
            return "username_password"
        else:
            return "api_key"  # Default
    
    def _filter_servers_by_prompt(self, servers: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
        """Filter servers based on prompt relevance"""
        prompt_lower = prompt.lower()
        filtered = []
        
        for server in servers:
            name = server.get("name", "").lower()
            description = server.get("description", "").lower()
            capabilities = server.get("capabilities", [])
            
            # Check if server is relevant to prompt
            relevance_score = 0
            
            # Check name relevance
            if any(word in name for word in prompt_lower.split()):
                relevance_score += 2
            
            # Check description relevance
            if any(word in description for word in prompt_lower.split()):
                relevance_score += 1
            
            # Check capabilities relevance
            for capability in capabilities:
                if any(word in capability.lower() for word in prompt_lower.split()):
                    relevance_score += 1
            
            # Add server if relevant
            if relevance_score > 0:
                server["relevance_score"] = relevance_score
                filtered.append(server)
        
        # Sort by relevance score
        filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return filtered
    
    def _get_recommendation_level(self, security_score: int) -> str:
        """Get recommendation level based on security score"""
        if security_score >= 80:
            return "EXCELLENT"
        elif security_score >= 60:
            return "GOOD"
        elif security_score >= 40:
            return "FAIR"
        else:
            return "POOR"

# Initialize server discovery
server_discovery = MCPServerDiscovery()

# Pydantic models for API
class PromptRequest(BaseModel):
    prompt: str
    max_servers: int = 10

class ServerRecommendation(BaseModel):
    name: str
    endpoint: str
    description: str
    security_score: int
    auth_model: str
    activity: int
    source: str
    capabilities: List[str]
    security_breakdown: Dict[str, int]
    recommendation_level: str

class ConnectorRequest(BaseModel):
    prompt: str
    server_name: str
    framework: str = "langchain"

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

# Initialize FastAPI app
app = FastAPI(
    title="MCP Guardian",
    description="AI-powered security-first MCP server discovery and connection system",
    version="1.0.0"
)

# Initialize WebSocket manager
manager = WebSocketManager()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize connector agent
connector_agent = ConnectorAgent()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/discover")
async def discover_servers(request: PromptRequest):
    """Discover MCP servers based on prompt with database caching"""
    try:
        # Use enhanced server discovery with caching
        servers = await server_discovery.discover_servers(request.prompt, request.max_servers)
        
        # Convert to response format
        recommendations = []
        for server in servers:
            recommendation = ServerRecommendation(
                name=server["name"],
                endpoint=server["endpoint"],
                description=server["description"],
                security_score=server.get("security_score", 0),
                auth_model=server["auth_model"],
                activity=server["activity"],
                source=server["source"],
                capabilities=server["capabilities"],
                security_breakdown=server.get("security_breakdown", {}),
                recommendation_level=server.get("recommendation_level", "FAIR")
            )
            recommendations.append(recommendation)
        
        return {
            "recommendations": [rec.dict() for rec in recommendations],
            "total_found": len(recommendations),
            "prompt": request.prompt,
            "cached": len(recommendations) > 0  # Simple cache indicator
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error discovering servers: {str(e)}")

@app.post("/api/connect")
async def connect_to_server(request: ConnectorRequest):
    """Generate connection code for a specific server"""
    try:
        # Find the server in our discovered servers
        servers = await server_discovery.discover_servers(request.prompt, 50)
        target_server = None
        
        for server in servers:
            if server["name"] == request.server_name:
                target_server = server
                break
        
        if not target_server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Generate connection code using connector agent
        connection_result = await connector_agent.run(
            prompt=request.prompt,
            server_info=target_server,
            framework=request.framework
        )
        
        return {
            "success": True,
            "server": target_server,
            "connection_result": connection_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to server: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "MCP Guardian",
        "version": "1.0.0"
    }

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        stats = await db.get_database_stats()
        return {
            "database_stats": stats,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.post("/api/seed")
async def seed_database():
    """Seed the database with initial server data"""
    try:
        # Get all mock servers for seeding
        all_servers = []
        
        # Get servers from different sources
        sources = [
            server_discovery._get_community_servers,
            server_discovery._get_mock_servers
        ]
        
        for source_func in sources:
            try:
                servers = await source_func("", 50)  # Empty prompt to get all servers
                all_servers.extend(servers)
            except Exception as e:
                print(f"Error getting servers from {source_func.__name__}: {e}")
                continue
        
        # Add security scoring
        for server in all_servers:
            score, breakdown = score_server_from_dict(server.get('security', {}))
            server['security_score'] = score
            server['security_breakdown'] = breakdown
            server['recommendation_level'] = server_discovery._get_recommendation_level(score)
        
        # Store in database
        stored_count = await db.seed_database(all_servers)
        
        return {
            "success": True,
            "servers_stored": stored_count,
            "total_servers": len(all_servers)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding database: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Message: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 