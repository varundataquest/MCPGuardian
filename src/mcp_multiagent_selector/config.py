"""Configuration management for the MCP Multi-Agent Selector."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/mcp"
    
    # LLM Configuration
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    
    # Crawling Configuration
    crawl_timeout_secs: int = 20
    registries_urls: str = ""
    max_candidates: int = 50
    
    # MCP Server Configuration
    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 8080
    
    # Smithery API Configuration
    smithery_api_key: Optional[str] = None
    
    # Optional Features
    use_playwright: bool = False
    enable_fastapi_health: bool = True
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    
    @property
    def registry_urls_list(self) -> List[str]:
        """Get registry URLs as a list."""
        if not self.registries_urls:
            return []
        return [url.strip() for url in self.registries_urls.split(",") if url.strip()]
    
    @property
    def has_llm_credentials(self) -> bool:
        """Check if we have LLM credentials configured."""
        if self.llm_provider == "openai" and self.openai_api_key:
            return True
        elif self.llm_provider == "anthropic" and self.anthropic_api_key:
            return True
        elif self.llm_provider == "azure_openai" and self.azure_openai_api_key:
            return True
        return False
    
    @property
    def has_smithery_credentials(self) -> bool:
        """Check if Smithery API key is configured."""
        return bool(self.smithery_api_key)
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 