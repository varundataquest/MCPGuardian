#!/usr/bin/env python3
"""
Database Seeding Script for MCP Guardian
Seeds the database with initial MCP server data
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_multiagent_selector.database import db

async def main():
    """Seed the database with initial server data"""
    print("🌱 Seeding MCP Guardian Database...")
    
    # Initial server data
    initial_servers = [
        {
            "name": "google-drive-mcp-server",
            "endpoint": "https://api.drive-mcp.com",
            "description": "Google Drive integration for file operations with OAuth2 authentication",
            "source": "google_official",
            "auth_model": "oauth2",
            "activity": 9,
            "capabilities": ["file_upload", "file_download", "file_sharing", "collaboration"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 85,
            "recommendation_level": "EXCELLENT"
        },
        {
            "name": "aws-s3-mcp-server",
            "endpoint": "https://api.s3-mcp.com",
            "description": "AWS S3 file storage operations with API key authentication",
            "source": "aws_official",
            "auth_model": "api_key",
            "activity": 9,
            "capabilities": ["file_storage", "file_retrieval", "versioning", "backup"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 80,
            "recommendation_level": "EXCELLENT"
        },
        {
            "name": "gmail-mcp-server",
            "endpoint": "https://api.gmail-mcp.com",
            "description": "Gmail API integration for sending and receiving emails with OAuth2 authentication",
            "source": "google_official",
            "auth_model": "oauth2",
            "activity": 9,
            "capabilities": ["send_email", "receive_email", "manage_labels", "search"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 85,
            "recommendation_level": "EXCELLENT"
        },
        {
            "name": "openai-mcp-server",
            "endpoint": "https://api.openai-mcp.com",
            "description": "OpenAI integration for text generation and analysis",
            "source": "openai_official",
            "auth_model": "api_key",
            "activity": 9,
            "capabilities": ["text_generation", "code_generation", "analysis", "translation"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 80,
            "recommendation_level": "EXCELLENT"
        },
        {
            "name": "anthropic-mcp-server",
            "endpoint": "https://api.anthropic-mcp.com",
            "description": "Anthropic Claude integration for AI conversations and reasoning",
            "source": "anthropic_official",
            "auth_model": "api_key",
            "activity": 8,
            "capabilities": ["ai_chat", "reasoning", "analysis", "content_generation"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 75,
            "recommendation_level": "GOOD"
        },
        {
            "name": "postgres-mcp-server",
            "endpoint": "https://api.postgres-mcp.com",
            "description": "PostgreSQL database operations with connection pooling and security",
            "source": "postgres_official",
            "auth_model": "username_password",
            "activity": 8,
            "capabilities": ["query_execution", "schema_management", "backup", "monitoring"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 75,
            "recommendation_level": "GOOD"
        },
        {
            "name": "notion-mcp-server",
            "endpoint": "https://api.notion-mcp.com",
            "description": "Notion workspace integration for document management",
            "source": "notion_official",
            "auth_model": "oauth2",
            "activity": 7,
            "capabilities": ["document_management", "database", "collaboration"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 70,
            "recommendation_level": "GOOD"
        },
        {
            "name": "slack-mcp-server",
            "endpoint": "https://api.slack-mcp.com",
            "description": "Slack workspace integration for messaging and collaboration",
            "source": "slack_official",
            "auth_model": "oauth2",
            "activity": 7,
            "capabilities": ["messaging", "file_sharing", "team_collaboration"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 70,
            "recommendation_level": "GOOD"
        },
        {
            "name": "github-mcp-server",
            "endpoint": "https://api.github-mcp.com",
            "description": "GitHub repository integration for code management",
            "source": "github_official",
            "auth_model": "oauth2",
            "activity": 8,
            "capabilities": ["code_management", "version_control", "collaboration"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 75,
            "recommendation_level": "GOOD"
        },
        {
            "name": "elasticsearch-mcp-server",
            "endpoint": "https://api.elasticsearch-mcp.com",
            "description": "Elasticsearch integration for advanced search and analytics",
            "source": "elastic_official",
            "auth_model": "api_key",
            "activity": 8,
            "capabilities": ["search", "analytics", "indexing", "aggregation"],
            "security": {"hash_pinning": True, "sbom": True, "rate_limiting": True, "observability": True},
            "security_score": 75,
            "recommendation_level": "GOOD"
        }
    ]
    
    # Store servers in database
    stored_count = await db.store_servers_batch(initial_servers)
    
    print(f"✅ Successfully stored {stored_count} servers in database")
    
    # Get database stats
    stats = await db.get_database_stats()
    print(f"📊 Database Stats:")
    print(f"   Total servers: {stats.get('total_servers', 0)}")
    print(f"   Servers by source: {stats.get('servers_by_source', {})}")
    print(f"   Average security score: {stats.get('average_security_score', 0)}")
    
    print("🎉 Database seeding complete!")

if __name__ == "__main__":
    asyncio.run(main()) 