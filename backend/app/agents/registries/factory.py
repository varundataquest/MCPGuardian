"""
Registry factory that creates appropriate registry instances based on URL patterns.
This allows dynamic creation of registry crawlers without hardcoding specific types.
"""

from typing import Optional

from ...config.registry_config import RegistryConfig
from .base import BaseRegistry


class RegistryFactory:
    """Creates appropriate registry instances based on URL patterns"""
    
    @classmethod
    def create_registry(cls, config: RegistryConfig) -> BaseRegistry:
        """
        Auto-detect registry type from URL and create appropriate instance
        
        Args:
            config: Registry configuration
            
        Returns:
            Appropriate registry instance
            
        Raises:
            ValueError: If registry type cannot be determined from URL
        """
        url = config.url.lower()
        
        # Generic registry detection based on URL patterns
        if any(domain in url for domain in ["glama", "glama.ai"]):
            from .glama import GlamaRegistry
            return GlamaRegistry(config)
        elif any(domain in url for domain in ["mcp.so", "mcpso"]):
            from .mcpso import McpsoRegistry
            return McpsoRegistry(config) 
        elif any(domain in url for domain in ["pulsemcp", "pulsemcp.com"]):
            from .pulsemcp import PulsemcpRegistry
            return PulsemcpRegistry(config)
        else:
            # Default to McpsoRegistry for unknown domains (most generic)
            from .mcpso import McpsoRegistry
            return McpsoRegistry(config)
    
    @classmethod
    def get_supported_domain_patterns(cls) -> list[str]:
        """Get list of supported domain patterns"""
        return [
            "glama",
            "mcp.so", 
            "pulsemcp"
        ]
