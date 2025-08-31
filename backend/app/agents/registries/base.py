"""
Abstract base class for all registry crawlers.
This provides a unified interface for different registry implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Awaitable

from ...config.registry_config import RegistryConfig


class BaseRegistry(ABC):
    """Abstract base class for all registry crawlers"""
    
    def __init__(self, config: RegistryConfig):
        self.config = config
        self.base_url = config.url
        self.registry_name = config.name
        self.display_name = config.display_name
    
    @abstractmethod
    async def crawl(
        self, 
        max_pages: int,
        rate_limit_per_host: float,
        user_agent: str,
        progress_cb: Optional[Callable[[Dict], Awaitable[None]]] = None,
        max_items: Optional[int] = None
    ) -> List[Dict]:
        """
        Crawl this registry and return server data
        
        Args:
            max_pages: Maximum pages to crawl
            rate_limit_per_host: Rate limit per host in seconds
            user_agent: User agent string to use
            progress_cb: Optional callback for progress updates
            max_items: Optional maximum number of items to return
            
        Returns:
            List of server dictionaries with standardized format:
            {
                "name": str,
                "slug": str, 
                "homepage_url": str,
                "repo_url": Optional[str],
                "description": Optional[str],
                "tags": Optional[List[str]],
                "registry": str  # The generic registry name
            }
        """
        pass

