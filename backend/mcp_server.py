#!/usr/bin/env python3
"""
AgentAgentGo: MCPGuard - MCP Server

An MCP server that provides AI assistants with tools to discover, 
analyze, and get security insights about MCP servers.

Usage:
    python mcp_server.py

Environment Variables:
    SUPABASE_URL: Supabase project URL
    SUPABASE_SERVICE_ROLE_KEY: Supabase service role key
    GEMINI_API_KEY: Google Gemini API key (optional)
    GITHUB_TOKEN: GitHub API token (optional)
"""

import asyncio
import os
import sys
import threading
from typing import Dict, List, Optional, Any, Sequence
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from fastmcp import FastMCP
from app.core_engine import get_engine, ServerRecommendation, SecurityAnalysis


# Initialize MCP server with HTTP transport
import argparse

def create_mcp_server(transport="stdio", host="127.0.0.1", port=8000, path="/mcp"):
    """Create MCP server with specified transport"""
    # FastMCP handles transport in the run() method, not constructor
    mcp = FastMCP("AgentAgentGo-MCPGuard")
    
    if transport == "http" or transport == "streamable-http":
        # Return config for HTTP transport
        return mcp, host, port, path, "streamable-http"
    else:
        # Return config for STDIO transport
        return mcp, None, None, None, "stdio"

# Parse command line arguments for transport configuration
parser = argparse.ArgumentParser(description='AgentAgentGo MCP Server')
parser.add_argument('--transport', choices=['stdio', 'http', 'streamable-http'], 
                   default='stdio', help='Transport type (default: stdio)')
parser.add_argument('--host', default='127.0.0.1', help='Host for HTTP transport (default: 127.0.0.1)')
parser.add_argument('--port', type=int, default=8000, help='Port for HTTP transport (default: 8000)')
parser.add_argument('--path', default='/mcp', help='Path for HTTP transport (default: /mcp)')

# Try to parse args, but don't fail if running in imported mode
try:
    args = parser.parse_args()
    mcp, http_host, http_port, http_path, transport_type = create_mcp_server(args.transport, args.host, args.port, args.path)
except SystemExit:
    # If parsing fails (e.g., when imported), use default STDIO
    mcp, http_host, http_port, http_path, transport_type = create_mcp_server()

engine = get_engine()


@mcp.tool()
async def search_mcp_servers(
    query: str = "",
    limit: int = 20,
    sort_by: str = "relevance"
) -> List[Dict]:
    """
    Search and discover MCP servers with security analysis.
    
    Args:
        query: Search query (e.g., "github", "file operations", "security")
        limit: Maximum number of results to return (1-100)
        sort_by: Sort order - "relevance", "security_score", "recent", "github_stars"
    
    Returns:
        List of MCP servers with metadata, security scores, and descriptions
    """
    # Map sort_by parameter to internal sort keys
    sort_mapping = {
        "relevance": "rank",
        "security_score": "score", 
        "recent": "recent",
        "github_stars": "stars"
    }
    sort_key = sort_mapping.get(sort_by, "rank")
    
    result = await engine.search_servers(
        query=query,
        limit=min(limit, 100),
        offset=0,
        sort=sort_key
    )
    
    # Format results for MCP client
    formatted_results = []
    for server in result.items:
        formatted_server = {
            "id": server["id"],
            "name": server.get("name", "Unknown"),
            "description": server.get("description", "No description available"),
            "homepage_url": server.get("homepage_url"),
            "repo_url": server.get("repo_url"),
            "registry": server.get("registry", "unknown"),
            "tags": server.get("tags", []),
            "github_stars": server.get("github_stars", 0),
            "updated_at": server.get("updated_at"),
            "security_score": None
        }
        
        # Add security score if available
        if server.get("latest_score"):
            formatted_server["security_score"] = {
                "overall": server["latest_score"].get("score_overall"),
                "last_analyzed": server["latest_score"].get("created_at")
            }
        
        formatted_results.append(formatted_server)
    
    return formatted_results


@mcp.tool()
async def get_server_details(server_id: str) -> Optional[Dict]:
    """
    Get comprehensive details for a specific MCP server.
    
    Args:
        server_id: The unique ID of the MCP server
        
    Returns:
        Detailed server information including security analysis
    """
    server = await engine.get_server_details(server_id)
    
    if not server:
        return None
    
    return {
        "id": server["id"],
        "name": server.get("name", "Unknown"),
        "slug": server.get("slug"),
        "description": server.get("description", "No description available"),
        "homepage_url": server.get("homepage_url"),
        "repo_url": server.get("repo_url"),
        "registry": server.get("registry", "unknown"),
        "tags": server.get("tags", []),
        "github_stars": server.get("github_stars", 0),
        "created_at": server.get("created_at"),
        "updated_at": server.get("updated_at"),
        "metadata": server.get("metadata_json"),
        "security_score": server.get("latest_score")
    }


@mcp.tool()
async def analyze_server_security(server_id: str) -> Optional[Dict]:
    """
    Get comprehensive security analysis for an MCP server.
    
    Args:
        server_id: The unique ID of the MCP server
        
    Returns:
        Security analysis with score breakdown, recommendations, and risk factors
    """
    analysis = await engine.analyze_server_security(server_id)
    
    if not analysis:
        return None
    
    return {
        "server_id": analysis.server_id,
        "security_score": analysis.score_overall,
        "score_breakdown": analysis.breakdown,
        "recommendations": analysis.recommendations,
        "risk_factors": analysis.risk_factors,
        "analysis_summary": f"Security score: {analysis.score_overall:.2f}/1.0"
    }


@mcp.tool()
async def recommend_servers(
    use_case: str,
    min_security_score: float = 0.5,
    limit: int = 10
) -> List[Dict]:
    """
    Get AI-curated server recommendations based on your use case.
    
    Args:
        use_case: Describe what you need (e.g., "file operations", "github integration", "web scraping")
        min_security_score: Minimum security score required (0.0 to 1.0)
        limit: Maximum number of recommendations
        
    Returns:
        List of recommended servers with match reasoning and security scores
    """
    recommendations = await engine.recommend_servers(
        use_case=use_case,
        min_security_score=min_security_score,
        limit=limit
    )
    
    formatted_recommendations = []
    for rec in recommendations:
        server = rec.server
        formatted_rec = {
            "server": {
                "id": server["id"],
                "name": server.get("name", "Unknown"),
                "description": server.get("description", "No description available"),
                "homepage_url": server.get("homepage_url"),
                "repo_url": server.get("repo_url"),
                "registry": server.get("registry", "unknown"),
                "tags": server.get("tags", []),
                "github_stars": server.get("github_stars", 0)
            },
            "recommendation": {
                "security_score": rec.security_score,
                "match_score": rec.match_score,
                "reasoning": rec.reasoning,
                "overall_rating": (rec.match_score * 0.6 + rec.security_score * 0.4)
            }
        }
        formatted_recommendations.append(formatted_rec)
    
    return formatted_recommendations


@mcp.tool()
async def analyze_custom_server(url: str) -> Dict:
    """
    Analyze any MCP server URL on-demand, even if not in the database.
    
    Args:
        url: The homepage URL of the MCP server to analyze
        
    Returns:
        Analysis results including connectivity check and security assessment
    """
    result = await engine.analyze_custom_server(url)
    return result


@mcp.tool()
async def list_popular_servers(limit: int = 20) -> List[Dict]:
    """
    Get a list of popular MCP servers sorted by GitHub stars.
    
    Args:
        limit: Maximum number of servers to return
        
    Returns:
        List of popular servers with GitHub star counts and security scores
    """
    result = await engine.search_servers(
        query="",
        limit=limit,
        offset=0,
        sort="stars"
    )
    
    return [
        {
            "id": server["id"],
            "name": server.get("name", "Unknown"),
            "description": server.get("description", "No description available"),
            "homepage_url": server.get("homepage_url"),
            "repo_url": server.get("repo_url"),
            "github_stars": server.get("github_stars", 0),
            "registry": server.get("registry", "unknown"),
            "security_score": server.get("latest_score", {}).get("score_overall") if server.get("latest_score") else None
        }
        for server in result.items
    ]


@mcp.tool()
async def get_servers_by_registry(registry: str, limit: int = 50) -> List[Dict]:
    """
    Get MCP servers from a specific registry.
    
    Args:
        registry: Registry name (e.g., "glama", "mcpso", "pulsemcp")
        limit: Maximum number of servers to return
        
    Returns:
        List of servers from the specified registry
    """
    result = await engine.search_servers(
        query="",
        limit=limit,
        offset=0,
        sort="recent",
        registry_filter=[registry]
    )
    
    return [
        {
            "id": server["id"],
            "name": server.get("name", "Unknown"),
            "description": server.get("description", "No description available"),
            "homepage_url": server.get("homepage_url"),
            "repo_url": server.get("repo_url"),
            "tags": server.get("tags", []),
            "github_stars": server.get("github_stars", 0),
            "updated_at": server.get("updated_at"),
            "security_score": server.get("latest_score", {}).get("score_overall") if server.get("latest_score") else None
        }
        for server in result.items
    ]


@mcp.tool()
async def find_secure_servers(min_security_score: float = 0.8, limit: int = 20) -> List[Dict]:
    """
    Find MCP servers with high security scores.
    
    Args:
        min_security_score: Minimum security score threshold (0.0 to 1.0)
        limit: Maximum number of servers to return
        
    Returns:
        List of high-security servers with detailed security information
    """
    result = await engine.search_servers(
        query="",
        limit=limit * 2,  # Get more to filter
        offset=0,
        sort="score",
        min_security_score=min_security_score
    )
    
    secure_servers = []
    for server in result.items[:limit]:
        security_score = server.get("latest_score", {}).get("score_overall", 0) if server.get("latest_score") else 0
        if security_score >= min_security_score:
            secure_servers.append({
                "id": server["id"],
                "name": server.get("name", "Unknown"),
                "description": server.get("description", "No description available"),
                "homepage_url": server.get("homepage_url"),
                "repo_url": server.get("repo_url"),
                "registry": server.get("registry", "unknown"),
                "github_stars": server.get("github_stars", 0),
                "security_score": security_score,
                "security_breakdown": server.get("latest_score", {}).get("breakdown_json", {})
            })
    
    return secure_servers


@mcp.tool()
async def start_server_discovery(
    max_glama_servers: int = 100,
    max_mcpso_servers: int = 100
) -> Dict:
    """
    Start discovering new MCP servers from public registries.
    
    Args:
        max_glama_servers: Maximum servers to discover from Glama registry
        max_mcpso_servers: Maximum servers to discover from mcp.so registry
        
    Returns:
        Discovery session information with crawl ID
    """
    crawl_id = await engine.start_discovery_crawl(
        max_servers_glama=max_glama_servers,
        max_servers_mcpso=max_mcpso_servers
    )
    
    return {
        "crawl_id": crawl_id,
        "status": "started",
        "max_glama_servers": max_glama_servers,
        "max_mcpso_servers": max_mcpso_servers,
        "message": f"Discovery crawl {crawl_id} started. This may take several minutes."
    }


@mcp.tool()
async def get_discovery_status() -> Dict:
    """
    Get the status of any active server discovery crawl.
    
    Returns:
        Current discovery status and progress information
    """
    status = await engine.get_crawl_status()
    return status


def sync_main():
    """Synchronous main entry point for the MCP server"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("   Please set them in backend/.env file")
        sys.exit(1)
    
    print("🚀 Starting AgentAgentGo: MCPGuard MCP Server...")
    print("🛡️ Providing secure MCP server discovery and analysis tools")
    print("📊 Available tools: 10+ tools for AI assistants")


async def async_main():
    """Async main entry point for the MCP server"""
    sync_main()
    # Run the MCP server with transport configuration
    if transport_type == "streamable-http":
        print(f"🌐 Starting MCP server with HTTP transport at http://{http_host}:{http_port}{http_path}")
        # For FastMCP HTTP transport, use streamable-http with server config
        await mcp.run(transport="streamable-http", host=http_host, port=http_port, path=http_path)
    else:
        print("🤖 Starting MCP server with STDIO transport")
        await mcp.run()


def run_mcp_server():
    """Run the MCP server, handling existing event loops gracefully"""
    # Check if we're being imported vs run directly
    if __name__ != "__main__":
        # If imported (like in hybrid mode), run in separate thread
        print("🧵 Running MCP server in separate thread to avoid event loop conflicts...")
        thread = threading.Thread(target=_run_mcp_in_thread, daemon=True)
        thread.start()
        return thread
    else:
        # If run directly, try different approaches
        _run_mcp_direct()


def _run_mcp_in_thread():
    """Run MCP server in a separate thread with its own event loop"""
    try:
        # Create new event loop for this thread
        asyncio.set_event_loop(asyncio.new_event_loop())
        sync_main()
        # Use mcp.run() directly with transport configuration
        if transport_type == "streamable-http":
            mcp.run(transport="streamable-http", host=http_host, port=http_port, path=http_path)
        else:
            mcp.run()
    except Exception as e:
        # Don't print here as stdout might be closed in background mode
        pass


def _run_mcp_direct():
    """Run MCP server directly (for standalone usage)"""
    sync_main()
    
    # Check for existing event loop conflicts
    try:
        loop = asyncio.get_running_loop()
        print("⚠️  Event loop already running, cannot start MCP server directly")
        print("   This usually happens when importing modules that set up async infrastructure")
        print("   Try running the MCP server in isolation or use threading mode")
        sys.exit(1)
    except RuntimeError:
        # No running loop, we can proceed
        pass
    
    # Run the MCP server directly with transport configuration
    try:
        if transport_type == "streamable-http":
            print(f"🌐 Starting MCP server with HTTP transport at http://{http_host}:{http_port}{http_path}")
            mcp.run(transport="streamable-http", host=http_host, port=http_port, path=http_path)
        else:
            print("🤖 Starting MCP server with STDIO transport")
            mcp.run()
    except Exception as e:
        print(f"❌ MCP server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_mcp_server()
