#!/usr/bin/env python3
"""
MCP Registry Crawler Agent

This agent searches through all available MCP registries to find servers
relevant to a user's prompt and compiles a comprehensive list for the security agent.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..schemas import Candidate
from ..crawl.registries import RegistryCrawler
from ..crawl.web import WebCrawler
from ..crawl.extract import extract_capabilities, extract_auth_model, extract_maintainer_activity
from ..graph.llm import get_llm_provider

logger = logging.getLogger(__name__)

@dataclass
class RegistrySearchResult:
    """Result from searching a single registry."""
    registry_url: str
    servers_found: List[Dict[str, Any]]
    error: Optional[str] = None
    search_time: Optional[float] = None

@dataclass
class CrawlerAgentState:
    """State for the registry crawler agent."""
    user_prompt: str
    max_candidates: int
    discovered_servers: List[Candidate]
    registry_results: List[RegistrySearchResult]
    search_metadata: Dict[str, Any]

class SmitheryAPIClient:
    """Client for interacting with the Smithery API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.smithery.dev"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def search_servers(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for MCP servers using Smithery API."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/v1/search",
                    headers=self.headers,
                    json={
                        "query": query,
                        "limit": limit,
                        "type": "mcp_server"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract servers from Smithery response
                servers = []
                for item in data.get("results", []):
                    server = {
                        "name": item.get("name", ""),
                        "description": item.get("description", ""),
                        "endpoint": item.get("endpoint", ""),
                        "source": "smithery",
                        "metadata": {
                            "smithery_id": item.get("id"),
                            "tags": item.get("tags", []),
                            "rating": item.get("rating"),
                            "downloads": item.get("downloads"),
                            "last_updated": item.get("updated_at"),
                            "author": item.get("author"),
                            "repository": item.get("repository")
                        }
                    }
                    servers.append(server)
                
                logger.info(f"Smithery API found {len(servers)} servers for query: {query}")
                return servers
                
        except Exception as e:
            logger.error(f"Error searching Smithery API: {e}")
            return []
    
    async def get_server_details(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific server."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.base_url}/v1/servers/{server_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error getting server details from Smithery: {e}")
            return None

class MCPRegistryCrawlerAgent:
    """
    Agent that crawls MCP registries to find relevant servers.
    
    This agent:
    1. Searches through all configured MCP registries
    2. Uses Smithery API for enhanced server discovery
    3. Filters servers based on relevance to user prompt
    4. Extracts metadata and capabilities
    5. Compiles a ranked list of candidates
    """
    
    def __init__(self, smithery_api_key: Optional[str] = None):
        self.registry_crawler = RegistryCrawler()
        self.web_crawler = WebCrawler()
        self.llm_provider = get_llm_provider()
        
        # Initialize Smithery API client
        self.smithery_client = None
        if smithery_api_key:
            self.smithery_client = SmitheryAPIClient(smithery_api_key)
        
        # Known MCP registries
        self.default_registries = [
            "https://registry.mcp.dev/index.json",
            "https://mcp-registry.vercel.app/api/servers",
            "https://raw.githubusercontent.com/modelcontextprotocol/registry/main/servers.json",
            "https://api.github.com/repos/modelcontextprotocol/registry/contents/servers",
        ]
        
        # Registry-specific adapters
        self.registry_adapters = {
            "mcp.dev": self._parse_mcp_dev_registry,
            "mcp-registry.vercel.app": self._parse_vercel_registry,
            "github.com": self._parse_github_registry,
            "raw.githubusercontent.com": self._parse_raw_github_registry,
        }
    
    async def run(self, user_prompt: str, max_candidates: int = 50) -> List[Candidate]:
        """
        Main entry point for the registry crawler agent.
        
        Args:
            user_prompt: The user's natural language request
            max_candidates: Maximum number of candidates to return
            
        Returns:
            List of Candidate objects ranked by relevance
        """
        logger.info(f"Starting registry crawl for prompt: {user_prompt[:100]}...")
        
        # Initialize state
        state = CrawlerAgentState(
            user_prompt=user_prompt,
            max_candidates=max_candidates,
            discovered_servers=[],
            registry_results=[],
            search_metadata={
                "start_time": datetime.now().isoformat(),
                "total_registries_searched": 0,
                "total_servers_found": 0,
                "relevant_servers_found": 0,
                "smithery_enabled": self.smithery_client is not None
            }
        )
        
        # Step 1: Get registry URLs to search
        registry_urls = await self._get_registry_urls()
        
        # Step 2: Search each registry concurrently
        registry_results = await self._search_registries_concurrent(registry_urls, user_prompt)
        state.registry_results = registry_results
        
        # Step 3: Search Smithery API if available
        smithery_results = []
        if self.smithery_client:
            smithery_results = await self._search_smithery(user_prompt, max_candidates)
        
        # Step 4: Extract and normalize server data
        all_servers = await self._extract_servers_from_results(registry_results)
        
        # Add Smithery results
        if smithery_results:
            all_servers.extend(smithery_results)
        
        # Step 5: Filter and rank by relevance
        relevant_servers = await self._filter_by_relevance(all_servers, user_prompt)
        
        # Step 6: Enrich with additional metadata
        enriched_servers = await self._enrich_server_metadata(relevant_servers)
        
        # Step 7: Convert to Candidate objects
        candidates = await self._convert_to_candidates(enriched_servers)
        
        # Step 8: Rank and limit results
        final_candidates = self._rank_and_limit_candidates(candidates, max_candidates)
        
        # Update state
        state.discovered_servers = final_candidates
        state.search_metadata.update({
            "end_time": datetime.now().isoformat(),
            "total_registries_searched": len(registry_urls) + (1 if self.smithery_client else 0),
            "total_servers_found": sum(len(r.servers_found) for r in registry_results) + len(smithery_results),
            "relevant_servers_found": len(final_candidates),
            "smithery_servers_found": len(smithery_results)
        })
        
        logger.info(f"Registry crawl completed. Found {len(final_candidates)} relevant servers.")
        return final_candidates
    
    async def _search_smithery(self, user_prompt: str, max_candidates: int) -> List[Dict[str, Any]]:
        """Search for servers using Smithery API."""
        if not self.smithery_client:
            return []
        
        try:
            logger.info("Searching Smithery API for MCP servers...")
            
            # Create search query from user prompt
            search_query = self._create_smithery_query(user_prompt)
            
            # Search Smithery
            smithery_servers = await self.smithery_client.search_servers(
                query=search_query,
                limit=max_candidates
            )
            
            # Filter by relevance
            relevant_servers = []
            for server in smithery_servers:
                if self._is_relevant_server(server, user_prompt):
                    relevant_servers.append(server)
            
            logger.info(f"Smithery API found {len(relevant_servers)} relevant servers")
            return relevant_servers
            
        except Exception as e:
            logger.error(f"Error searching Smithery API: {e}")
            return []
    
    def _create_smithery_query(self, user_prompt: str) -> str:
        """Create an optimized search query for Smithery API."""
        # Extract key terms from user prompt
        keywords = self._extract_keywords(user_prompt.lower())
        
        # Create a focused search query
        if keywords:
            query_terms = list(keywords)[:3]  # Use top 3 keywords
            base_query = " ".join(query_terms)
        else:
            # Fallback to general MCP server search
            base_query = "MCP server"
        
        # Add context about MCP
        query = f"{base_query} MCP server model context protocol"
        
        return query
    
    async def _get_registry_urls(self) -> List[str]:
        """Get list of registry URLs to search."""
        urls = []
        
        # Add configured registries
        if settings.registry_urls_list:
            urls.extend(settings.registry_urls_list)
        
        # Add default registries if none configured
        if not urls:
            urls.extend(self.default_registries)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        logger.info(f"Will search {len(unique_urls)} registries: {unique_urls}")
        return unique_urls
    
    async def _search_registries_concurrent(self, registry_urls: List[str], user_prompt: str) -> List[RegistrySearchResult]:
        """Search all registries concurrently."""
        tasks = []
        for url in registry_urls:
            task = self._search_single_registry(url, user_prompt)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        registry_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                registry_results.append(RegistrySearchResult(
                    registry_url=registry_urls[i],
                    servers_found=[],
                    error=str(result)
                ))
            else:
                registry_results.append(result)
        
        return registry_results
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _search_single_registry(self, registry_url: str, user_prompt: str) -> RegistrySearchResult:
        """Search a single registry for relevant servers."""
        start_time = datetime.now()
        
        try:
            logger.info(f"Searching registry: {registry_url}")
            
            # Determine adapter based on URL
            adapter = self._get_registry_adapter(registry_url)
            
            # Fetch registry data
            async with httpx.AsyncClient(timeout=settings.crawl_timeout_secs) as client:
                response = await client.get(registry_url)
                response.raise_for_status()
                registry_data = response.json()
            
            # Parse using appropriate adapter
            servers = await adapter(registry_data, user_prompt)
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Found {len(servers)} servers in {registry_url}")
            
            return RegistrySearchResult(
                registry_url=registry_url,
                servers_found=servers,
                search_time=search_time
            )
            
        except Exception as e:
            logger.error(f"Error searching registry {registry_url}: {e}")
            return RegistrySearchResult(
                registry_url=registry_url,
                servers_found=[],
                error=str(e)
            )
    
    def _get_registry_adapter(self, url: str):
        """Get the appropriate adapter for a registry URL."""
        for domain, adapter in self.registry_adapters.items():
            if domain in url:
                return adapter
        return self._parse_generic_registry
    
    async def _parse_mcp_dev_registry(self, data: Dict[str, Any], user_prompt: str) -> List[Dict[str, Any]]:
        """Parse mcp.dev registry format."""
        servers = []
        
        if isinstance(data, dict) and "servers" in data:
            for server in data["servers"]:
                if self._is_relevant_server(server, user_prompt):
                    servers.append({
                        "name": server.get("name", ""),
                        "description": server.get("description", ""),
                        "endpoint": server.get("endpoint", ""),
                        "source": "mcp.dev",
                        "metadata": server
                    })
        
        return servers
    
    async def _parse_vercel_registry(self, data: Dict[str, Any], user_prompt: str) -> List[Dict[str, Any]]:
        """Parse Vercel MCP registry format."""
        servers = []
        
        if isinstance(data, list):
            for server in data:
                if self._is_relevant_server(server, user_prompt):
                    servers.append({
                        "name": server.get("name", ""),
                        "description": server.get("description", ""),
                        "endpoint": server.get("endpoint", ""),
                        "source": "vercel",
                        "metadata": server
                    })
        
        return servers
    
    async def _parse_github_registry(self, data: Dict[str, Any], user_prompt: str) -> List[Dict[str, Any]]:
        """Parse GitHub API registry format."""
        servers = []
        
        if isinstance(data, list):
            for item in data:
                if item.get("type") == "file" and item.get("name", "").endswith(".json"):
                    # Fetch individual server file
                    server_data = await self._fetch_github_file(item["download_url"])
                    if server_data and self._is_relevant_server(server_data, user_prompt):
                        servers.append({
                            "name": server_data.get("name", ""),
                            "description": server_data.get("description", ""),
                            "endpoint": server_data.get("endpoint", ""),
                            "source": "github",
                            "metadata": server_data
                        })
        
        return servers
    
    async def _parse_raw_github_registry(self, data: Dict[str, Any], user_prompt: str) -> List[Dict[str, Any]]:
        """Parse raw GitHub registry format."""
        return await self._parse_mcp_dev_registry(data, user_prompt)
    
    async def _parse_generic_registry(self, data: Dict[str, Any], user_prompt: str) -> List[Dict[str, Any]]:
        """Parse generic registry format."""
        servers = []
        
        # Try different common formats
        if isinstance(data, list):
            # List of servers
            for server in data:
                if self._is_relevant_server(server, user_prompt):
                    servers.append({
                        "name": server.get("name", ""),
                        "description": server.get("description", ""),
                        "endpoint": server.get("endpoint", ""),
                        "source": "generic",
                        "metadata": server
                    })
        elif isinstance(data, dict):
            # Object with servers array
            if "servers" in data:
                return await self._parse_mcp_dev_registry(data, user_prompt)
            else:
                # Single server object
                if self._is_relevant_server(data, user_prompt):
                    servers.append({
                        "name": data.get("name", ""),
                        "description": data.get("description", ""),
                        "endpoint": data.get("endpoint", ""),
                        "source": "generic",
                        "metadata": data
                    })
        
        return servers
    
    async def _fetch_github_file(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch a file from GitHub."""
        try:
            async with httpx.AsyncClient(timeout=settings.crawl_timeout_secs) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch GitHub file {url}: {e}")
            return None
    
    def _is_relevant_server(self, server: Dict[str, Any], user_prompt: str) -> bool:
        """Check if a server is relevant to the user prompt."""
        # Basic relevance check based on name and description
        name = server.get("name", "").lower()
        description = server.get("description", "").lower()
        
        # Extract keywords from user prompt
        prompt_keywords = self._extract_keywords(user_prompt.lower())
        
        # Check for keyword matches
        for keyword in prompt_keywords:
            if keyword in name or keyword in description:
                return True
        
        return False
    
    def _extract_keywords(self, prompt: str) -> Set[str]:
        """Extract relevant keywords from user prompt."""
        # Common MCP server keywords
        common_keywords = {
            "calendar", "email", "database", "file", "web", "scraping", "notification",
            "weather", "news", "search", "translate", "image", "video", "audio",
            "code", "git", "github", "document", "pdf", "spreadsheet", "chat",
            "messaging", "social", "api", "http", "rest", "graphql", "storage",
            "cloud", "aws", "azure", "gcp", "docker", "kubernetes", "monitoring",
            "logging", "analytics", "ml", "ai", "model", "embedding", "vector"
        }
        
        # Extract words from prompt
        words = set(prompt.split())
        
        # Return intersection with common keywords
        return words.intersection(common_keywords)
    
    async def _extract_servers_from_results(self, registry_results: List[RegistrySearchResult]) -> List[Dict[str, Any]]:
        """Extract and normalize server data from registry results."""
        all_servers = []
        
        for result in registry_results:
            if result.error:
                logger.warning(f"Skipping registry {result.registry_url} due to error: {result.error}")
                continue
            
            for server in result.servers_found:
                # Normalize server data
                normalized_server = {
                    "name": server.get("name", ""),
                    "description": server.get("description", ""),
                    "endpoint": server.get("endpoint", ""),
                    "source": server.get("source", "unknown"),
                    "metadata": server.get("metadata", {}),
                    "registry_url": result.registry_url
                }
                
                # Remove duplicates based on endpoint
                if not any(s["endpoint"] == normalized_server["endpoint"] for s in all_servers):
                    all_servers.append(normalized_server)
        
        logger.info(f"Extracted {len(all_servers)} unique servers from registries")
        return all_servers
    
    async def _filter_by_relevance(self, servers: List[Dict[str, Any]], user_prompt: str) -> List[Dict[str, Any]]:
        """Filter servers by relevance to user prompt using LLM."""
        if not servers:
            return []
        
        relevant_servers = []
        
        for server in servers:
            # Create a relevance check prompt
            relevance_prompt = f"""
            User Request: {user_prompt}
            
            MCP Server:
            - Name: {server['name']}
            - Description: {server['description']}
            - Endpoint: {server['endpoint']}
            
            Is this MCP server relevant to the user's request? Consider:
            1. Does it provide capabilities that would help with the user's task?
            2. Is it a good fit for the described use case?
            3. Would it be useful for the user's goals?
            
            Respond with only "YES" or "NO".
            """
            
            try:
                response = await self.llm_provider.summarize(relevance_prompt, "")
                is_relevant = "YES" in response.upper()
                
                if is_relevant:
                    relevant_servers.append(server)
                    
            except Exception as e:
                logger.warning(f"Failed to check relevance for {server['name']}: {e}")
                # Fallback to basic keyword matching
                if self._is_relevant_server(server, user_prompt):
                    relevant_servers.append(server)
        
        logger.info(f"Filtered to {len(relevant_servers)} relevant servers")
        return relevant_servers
    
    async def _enrich_server_metadata(self, servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich server metadata with additional information."""
        enriched_servers = []
        
        for server in servers:
            enriched_server = server.copy()
            
            # Extract capabilities from description
            description = server.get("description", "")
            enriched_server["capabilities"] = extract_capabilities(description)
            
            # Extract auth model
            enriched_server["auth_model"] = extract_auth_model(description)
            
            # Extract maintainer activity (if available in metadata)
            metadata = server.get("metadata", {})
            enriched_server["maintainer_activity"] = extract_maintainer_activity(metadata)
            
            # Add discovery timestamp
            enriched_server["discovered_at"] = datetime.now().isoformat()
            
            enriched_servers.append(enriched_server)
        
        return enriched_servers
    
    async def _convert_to_candidates(self, servers: List[Dict[str, Any]]) -> List[Candidate]:
        """Convert server data to Candidate objects."""
        candidates = []
        
        for server in servers:
            candidate = Candidate(
                name=server["name"],
                endpoint=server["endpoint"],
                registry_meta=server["metadata"],
                docs_snippets=[server["description"]],
                signals={
                    "capabilities": server.get("capabilities", []),
                    "auth_model": server.get("auth_model", ""),
                    "maintainer_activity": server.get("maintainer_activity", 0),
                    "source": server["source"],
                    "discovered_at": server["discovered_at"]
                }
            )
            candidates.append(candidate)
        
        return candidates
    
    def _rank_and_limit_candidates(self, candidates: List[Candidate], max_candidates: int) -> List[Candidate]:
        """Rank candidates by relevance and limit results."""
        # Simple ranking based on maintainer activity and description length
        def rank_score(candidate: Candidate) -> float:
            score = 0.0
            
            # Higher maintainer activity = better
            score += candidate.signals.get("maintainer_activity", 0) * 0.1
            
            # Longer description = more detailed = potentially better
            description_length = sum(len(snippet) for snippet in candidate.docs_snippets)
            score += min(description_length / 1000, 1.0) * 0.5
            
            # Prefer servers with more capabilities
            capabilities = candidate.signals.get("capabilities", [])
            score += len(capabilities) * 0.2
            
            # Bonus for Smithery servers (they're curated)
            if candidate.signals.get("source") == "smithery":
                score += 0.3
            
            return score
        
        # Sort by rank score (descending)
        ranked_candidates = sorted(candidates, key=rank_score, reverse=True)
        
        # Limit to max_candidates
        return ranked_candidates[:max_candidates]

# Convenience function for easy integration
async def run_registry_crawler_agent(user_prompt: str, max_candidates: int = 50, smithery_api_key: Optional[str] = None) -> List[Candidate]:
    """Run the registry crawler agent."""
    agent = MCPRegistryCrawlerAgent(smithery_api_key=smithery_api_key)
    return await agent.run(user_prompt, max_candidates) 