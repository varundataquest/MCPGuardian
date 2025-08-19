#!/usr/bin/env python3
"""
MCP Guardian Web Application
A modern web interface for discovering and connecting to MCP servers
"""

import asyncio
import json
import os
import sys
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

# Import connector agent
from connector_agent_direct import ConnectorAgent

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

# Mock data for different types of servers
MOCK_SERVERS = {
    "file operations": [
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
        }
    ],
    "email": [
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
            "name": "sendgrid-mcp-server",
            "endpoint": "https://api.sendgrid-mcp.com",
            "description": "SendGrid email delivery service integration with API key authentication",
            "source": "sendgrid_official",
            "auth_model": "api_key",
            "activity": 7,
            "capabilities": ["send_email", "templates", "analytics", "bounce_handling"],
            "security": {"hash_pinning": False, "sbom": False, "rate_limiting": True, "observability": False}
        }
    ],
    "database": [
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
            "name": "mongodb-mcp-server",
            "endpoint": "https://api.mongodb-mcp.com",
            "description": "MongoDB NoSQL database operations with document management",
            "source": "mongodb_official",
            "auth_model": "api_key",
            "activity": 7,
            "capabilities": ["document_operations", "aggregation", "indexing", "replication"],
            "security": {"hash_pinning": True, "sbom": False, "rate_limiting": True, "observability": True}
        }
    ],
    "search": [
        {
            "name": "elasticsearch-mcp-server",
            "endpoint": "https://api.elasticsearch-mcp.com",
            "description": "Elasticsearch search and analytics with full-text search capabilities",
            "source": "elastic_official",
            "auth_model": "api_key",
            "activity": 8,
            "capabilities": ["full_text_search", "analytics", "aggregations", "monitoring"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True}
        }
    ]
}

def get_relevant_servers(prompt: str) -> List[Dict[str, Any]]:
    """Get relevant servers based on the prompt"""
    prompt_lower = prompt.lower()
    
    # Simple keyword matching
    if any(word in prompt_lower for word in ["file", "files", "upload", "download", "storage", "drive"]):
        return MOCK_SERVERS.get("file operations", [])
    elif any(word in prompt_lower for word in ["email", "mail", "send", "gmail", "outlook"]):
        return MOCK_SERVERS.get("email", [])
    elif any(word in prompt_lower for word in ["database", "db", "sql", "query", "postgres", "mongodb"]):
        return MOCK_SERVERS.get("database", [])
    elif any(word in prompt_lower for word in ["search", "elasticsearch", "query", "index"]):
        return MOCK_SERVERS.get("search", [])
    else:
        # Return a mix of servers for generic prompts
        all_servers = []
        for category in MOCK_SERVERS.values():
            all_servers.extend(category)
        return all_servers[:3]

async def analyze_servers(servers: List[Dict[str, Any]]) -> List[ServerRecommendation]:
    """Analyze servers and return recommendations"""
    recommendations = []
    
    for server in servers:
        # Create evidence for scoring
        evidence = {
            'hash_pinning': server['security'].get('hash_pinning', False),
            'auth_model': server['auth_model'],
            'maintainer_activity': server['activity'],
            'sbom': server['security'].get('sbom', False),
            'risk_notes': f"Server: {server['name']}, Auth: {server['auth_model']}, Activity: {server['activity']}/10"
        }
        
        score, breakdown = score_server_from_dict(evidence)
        
        # Determine recommendation level
        if score >= 70:
            recommendation_level = "EXCELLENT"
        elif score >= 50:
            recommendation_level = "GOOD"
        else:
            recommendation_level = "POOR"
        
        recommendation = ServerRecommendation(
            name=server['name'],
            endpoint=server['endpoint'],
            description=server['description'],
            security_score=score,
            auth_model=server['auth_model'],
            activity=server['activity'],
            source=server['source'],
            capabilities=server['capabilities'],
            security_breakdown=breakdown,
            recommendation_level=recommendation_level
        )
        
        recommendations.append(recommendation)
    
    # Sort by security score
    recommendations.sort(key=lambda x: x.security_score, reverse=True)
    return recommendations

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/discover")
async def discover_servers(request: PromptRequest):
    """Discover MCP servers based on prompt"""
    try:
        # Get relevant servers
        servers = get_relevant_servers(request.prompt)
        
        # Analyze servers
        recommendations = await analyze_servers(servers)
        
        return {
            "success": True,
            "prompt": request.prompt,
            "servers_found": len(recommendations),
            "recommendations": [rec.dict() for rec in recommendations[:request.max_servers]]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/connect")
async def connect_server(request: ConnectorRequest):
    """Generate connection code for a specific server"""
    try:
        # Find the server
        all_servers = []
        for category in MOCK_SERVERS.values():
            all_servers.extend(category)
        
        server_info = next((s for s in all_servers if s['name'] == request.server_name), None)
        
        if not server_info:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Use connector agent
        connector = ConnectorAgent()
        result = await connector.run(request.prompt, server_info)
        
        # Update framework in result
        result["framework"] = request.framework
        
        return {
            "success": True,
            "server": server_info,
            "framework": request.framework,
            "connection_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "MCP Guardian"}

if __name__ == "__main__":
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 