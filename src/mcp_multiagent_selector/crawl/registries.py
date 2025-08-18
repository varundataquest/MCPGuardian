"""MCP registry crawling functionality."""

import json
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..schemas import Candidate


class RegistryCrawler:
    """Crawler for MCP registries."""
    
    def __init__(self):
        self.timeout = settings.crawl_timeout_secs
        self.registry_urls = settings.registry_urls_list
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_registry_index(self, url: str) -> Dict[str, Any]:
        """Fetch a registry index with retry logic."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    
    async def crawl_registries(self) -> List[Candidate]:
        """Crawl all configured registries."""
        candidates = []
        
        for registry_url in self.registry_urls:
            try:
                index_data = await self.fetch_registry_index(registry_url)
                registry_candidates = self.parse_registry_index(index_data, registry_url)
                candidates.extend(registry_candidates)
            except Exception as e:
                print(f"Failed to crawl registry {registry_url}: {e}")
                continue
        
        return candidates
    
    def parse_registry_index(self, index_data: Dict[str, Any], registry_url: str) -> List[Candidate]:
        """Parse a registry index and extract candidates."""
        candidates = []
        
        # Handle different registry formats
        if isinstance(index_data, list):
            # List of servers
            for item in index_data:
                candidate = self.parse_server_item(item, registry_url)
                if candidate:
                    candidates.append(candidate)
        elif isinstance(index_data, dict):
            # Object with servers array
            servers = index_data.get("servers", [])
            if isinstance(servers, list):
                for item in servers:
                    candidate = self.parse_server_item(item, registry_url)
                    if candidate:
                        candidates.append(candidate)
        
        return candidates
    
    def parse_server_item(self, item: Dict[str, Any], registry_url: str) -> Optional[Candidate]:
        """Parse a single server item from registry."""
        try:
            name = item.get("name", "Unknown")
            endpoint = item.get("endpoint", "")
            
            if not endpoint:
                return None
            
            # Extract additional metadata
            registry_meta = {
                "registry_url": registry_url,
                "original_data": item
            }
            
            # Extract signals from metadata
            signals = {}
            if "description" in item:
                signals["description"] = item["description"]
            if "version" in item:
                signals["version"] = item["version"]
            if "maintainer" in item:
                signals["maintainer"] = item["maintainer"]
            
            return Candidate(
                name=name,
                endpoint=endpoint,
                registry_meta=registry_meta,
                signals=signals,
                source="registry"
            )
        except Exception as e:
            print(f"Failed to parse server item: {e}")
            return None


class MockRegistryCrawler(RegistryCrawler):
    """Mock crawler for testing and demo purposes."""
    
    async def crawl_registries(self) -> List[Candidate]:
        """Return mock candidates for testing."""
        return [
            Candidate(
                name="mock-calendar-server",
                endpoint="https://api.example.com/calendar",
                registry_meta={"registry_url": "mock", "original_data": {}},
                signals={"description": "Calendar management server", "version": "1.0.0"},
                source="mock_registry"
            ),
            Candidate(
                name="mock-webscraping-server",
                endpoint="https://api.example.com/scraper",
                registry_meta={"registry_url": "mock", "original_data": {}},
                signals={"description": "Web scraping and data extraction", "version": "2.1.0"},
                source="mock_registry"
            ),
            Candidate(
                name="mock-email-server",
                endpoint="https://api.example.com/email",
                registry_meta={"registry_url": "mock", "original_data": {}},
                signals={"description": "Email management and sending", "version": "1.5.0"},
                source="mock_registry"
            )
        ]


def get_registry_crawler() -> RegistryCrawler:
    """Get the appropriate registry crawler."""
    if not settings.registry_urls_list:
        return MockRegistryCrawler()
    return RegistryCrawler() 