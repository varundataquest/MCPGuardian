"""
Registry configuration loader that reads from environment variables.
This allows hiding actual registry URLs and names from the public codebase.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Continue without dotenv if not installed


@dataclass 
class RegistryConfig:
    """Configuration for a single registry"""
    name: str              # internal name (registry_1)  
    display_name: str      # UI display name (Primary Source)
    url: str               # crawling endpoint URL
    enabled: bool = True   # whether to include in crawls


class RegistryManager:
    """Loads registry configurations from environment variables"""
    
    def __init__(self):
        self.registries: Dict[str, RegistryConfig] = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """Load all REGISTRY_*_* environment variables"""
        for i in range(1, 10):  # Support up to 9 registries
            name_key = f"REGISTRY_{i}_NAME"
            url_key = f"REGISTRY_{i}_URL"
            
            name = os.getenv(name_key)
            url = os.getenv(url_key)
            
            if not name or not url:
                continue
                
            registry_key = f"registry_{i}"
            self.registries[registry_key] = RegistryConfig(
                name=name,
                display_name=os.getenv(f"REGISTRY_{i}_DISPLAY_NAME", f"Registry {i}"),
                url=url,
                enabled=os.getenv(f"REGISTRY_{i}_ENABLED", "true").lower() == "true"
            )
    
    def get_enabled_registries(self) -> List[RegistryConfig]:
        """Get all enabled registries"""
        return [r for r in self.registries.values() if r.enabled]
    
    def get_registry_by_key(self, registry_key: str) -> Optional[RegistryConfig]:
        """Get registry by key (registry_1, registry_2, etc.)"""
        return self.registries.get(registry_key)
    
    def get_registry_by_legacy_name(self, legacy_name: str) -> Optional[RegistryConfig]:
        """Map old names to new registry configs for backward compatibility"""
        legacy_mapping = {
            "glama": "registry_1",
            "mcpso": "registry_2", 
            "mcp.so": "registry_2",
            "pulsemcp": "registry_3"
        }
        registry_key = legacy_mapping.get(legacy_name)
        return self.registries.get(registry_key) if registry_key else None
    
    def get_all_registries(self) -> Dict[str, RegistryConfig]:
        """Get all registries (enabled and disabled)"""
        return self.registries.copy()
    
    def get_legacy_name_mapping(self) -> Dict[str, str]:
        """Get mapping from legacy names to current registry keys"""
        return {
            "glama": "registry_1",
            "mcpso": "registry_2", 
            "mcp.so": "registry_2",
            "pulsemcp": "registry_3"
        }


# Global registry manager instance
registry_manager = RegistryManager()
