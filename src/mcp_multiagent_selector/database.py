#!/usr/bin/env python3
"""
MCP Guardian Database Module
Handles caching and storage of MCP server discoveries
"""

import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MCPDatabase:
    """Database for caching MCP server discoveries"""
    
    def __init__(self, db_path: str = "mcp_guardian.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create servers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS servers (
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
                )
            ''')
            
            # Create discovery_cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discovery_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    max_servers INTEGER DEFAULT 10,
                    results TEXT,  -- JSON array of server names
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_servers_name ON servers(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_servers_source ON servers(source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_prompt ON discovery_cache(prompt)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON discovery_cache(expires_at)')
            
            conn.commit()
    
    async def store_server(self, server_data: Dict[str, Any]) -> bool:
        """Store a server in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Prepare data
                capabilities_json = json.dumps(server_data.get('capabilities', []))
                security_json = json.dumps(server_data.get('security', {}))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO servers 
                    (name, endpoint, description, source, auth_model, activity, 
                     capabilities, security_data, security_score, recommendation_level, 
                     updated_at, last_crawled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    server_data['name'],
                    server_data['endpoint'],
                    server_data.get('description', ''),
                    server_data['source'],
                    server_data.get('auth_model', 'api_key'),
                    server_data.get('activity', 5),
                    capabilities_json,
                    security_json,
                    server_data.get('security_score', 0),
                    server_data.get('recommendation_level', 'FAIR'),
                    datetime.now(),
                    datetime.now()
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing server {server_data.get('name', 'unknown')}: {e}")
            return False
    
    async def store_servers_batch(self, servers: List[Dict[str, Any]]) -> int:
        """Store multiple servers in batch"""
        success_count = 0
        for server in servers:
            if await self.store_server(server):
                success_count += 1
        return success_count
    
    async def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a server by name"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, endpoint, description, source, auth_model, activity,
                           capabilities, security_data, security_score, recommendation_level,
                           created_at, updated_at, last_crawled
                    FROM servers WHERE name = ?
                ''', (name,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'name': row[0],
                        'endpoint': row[1],
                        'description': row[2],
                        'source': row[3],
                        'auth_model': row[4],
                        'activity': row[5],
                        'capabilities': json.loads(row[6]) if row[6] else [],
                        'security': json.loads(row[7]) if row[7] else {},
                        'security_score': row[8],
                        'recommendation_level': row[9],
                        'created_at': row[10],
                        'updated_at': row[11],
                        'last_crawled': row[12]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting server {name}: {e}")
            return None
    
    async def search_servers(self, prompt: str, max_servers: int = 10) -> List[Dict[str, Any]]:
        """Search servers based on prompt relevance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Simple keyword-based search
                keywords = prompt.lower().split()
                conditions = []
                params = []
                
                for keyword in keywords:
                    conditions.append('''
                        (LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(capabilities) LIKE ?)
                    ''')
                    params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
                
                where_clause = ' OR '.join(conditions) if conditions else '1=1'
                
                cursor.execute(f'''
                    SELECT name, endpoint, description, source, auth_model, activity,
                           capabilities, security_data, security_score, recommendation_level
                    FROM servers 
                    WHERE {where_clause}
                    ORDER BY security_score DESC, activity DESC
                    LIMIT ?
                ''', params + [max_servers])
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'name': row[0],
                        'endpoint': row[1],
                        'description': row[2],
                        'source': row[3],
                        'auth_model': row[4],
                        'activity': row[5],
                        'capabilities': json.loads(row[6]) if row[6] else [],
                        'security': json.loads(row[7]) if row[7] else {},
                        'security_score': row[8],
                        'recommendation_level': row[9]
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching servers: {e}")
            return []
    
    async def get_all_servers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all servers with optional limit"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, endpoint, description, source, auth_model, activity,
                           capabilities, security_data, security_score, recommendation_level
                    FROM servers 
                    ORDER BY security_score DESC, activity DESC
                    LIMIT ?
                ''', (limit,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'name': row[0],
                        'endpoint': row[1],
                        'description': row[2],
                        'source': row[3],
                        'auth_model': row[4],
                        'activity': row[5],
                        'capabilities': json.loads(row[6]) if row[6] else [],
                        'security': json.loads(row[7]) if row[7] else {},
                        'security_score': row[8],
                        'recommendation_level': row[9]
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting all servers: {e}")
            return []
    
    async def cache_discovery_result(self, prompt: str, max_servers: int, 
                                   server_names: List[str], cache_duration_hours: int = 24) -> bool:
        """Cache a discovery result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                expires_at = datetime.now() + timedelta(hours=cache_duration_hours)
                results_json = json.dumps(server_names)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO discovery_cache 
                    (prompt, max_servers, results, expires_at)
                    VALUES (?, ?, ?, ?)
                ''', (prompt, max_servers, results_json, expires_at))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error caching discovery result: {e}")
            return False
    
    async def get_cached_discovery(self, prompt: str, max_servers: int) -> Optional[List[str]]:
        """Get cached discovery result if still valid"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT results FROM discovery_cache 
                    WHERE prompt = ? AND max_servers = ? AND expires_at > ?
                ''', (prompt, max_servers, datetime.now()))
                
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
                
        except Exception as e:
            logger.error(f"Error getting cached discovery: {e}")
            return None
    
    async def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM discovery_cache WHERE expires_at <= ?', (datetime.now(),))
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            return 0
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count servers
                cursor.execute('SELECT COUNT(*) FROM servers')
                total_servers = cursor.fetchone()[0]
                
                # Count by source
                cursor.execute('SELECT source, COUNT(*) FROM servers GROUP BY source')
                servers_by_source = dict(cursor.fetchall())
                
                # Count cache entries
                cursor.execute('SELECT COUNT(*) FROM discovery_cache WHERE expires_at > ?', (datetime.now(),))
                active_cache_entries = cursor.fetchone()[0]
                
                # Average security score
                cursor.execute('SELECT AVG(security_score) FROM servers')
                avg_security_score = cursor.fetchone()[0] or 0
                
                return {
                    'total_servers': total_servers,
                    'servers_by_source': servers_by_source,
                    'active_cache_entries': active_cache_entries,
                    'average_security_score': round(avg_security_score, 2)
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    async def seed_database(self, servers: List[Dict[str, Any]]) -> int:
        """Seed the database with initial server data"""
        logger.info(f"Seeding database with {len(servers)} servers")
        return await self.store_servers_batch(servers)

# Global database instance
db = MCPDatabase() 