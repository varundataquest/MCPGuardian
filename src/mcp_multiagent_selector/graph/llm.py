"""LLM abstraction layer for the multi-agent system."""

import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from ..config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def summarize(self, candidate: Dict[str, Any], user_task: str) -> Dict[str, Any]:
        """Summarize a candidate server for the given user task."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self):
        import openai
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def summarize(self, candidate: Dict[str, Any], user_task: str) -> Dict[str, Any]:
        """Summarize a candidate using OpenAI."""
        prompt = f"""
        Analyze this MCP server candidate for the user task: "{user_task}"
        
        Candidate: {json.dumps(candidate, indent=2)}
        
        Provide a JSON response with the following fields:
        - summary: A concise summary of the server's capabilities
        - doc_quality: Integer 0-10 rating of documentation quality
        - maintainer_activity: Integer 0-10 rating of maintainer activity
        - auth_model: String describing authentication model
        - hash_pinning: Boolean indicating if hash pinning is used
        - sbom: Boolean indicating if SBOM/AI-BOM is available
        - risk_notes: String with any security risks or concerns
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            # Fallback to heuristic summary
            return self._heuristic_summary(candidate, user_task)
    
    def _heuristic_summary(self, candidate: Dict[str, Any], user_task: str) -> Dict[str, Any]:
        """Fallback heuristic summary when LLM fails."""
        name = candidate.get("name", "Unknown")
        endpoint = candidate.get("endpoint", "")
        
        return {
            "summary": f"MCP server '{name}' available at {endpoint}",
            "doc_quality": 5,
            "maintainer_activity": 5,
            "auth_model": "unknown",
            "hash_pinning": False,
            "sbom": False,
            "risk_notes": "Limited information available"
        }


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider."""
    
    def __init__(self):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    async def summarize(self, candidate: Dict[str, Any], user_task: str) -> Dict[str, Any]:
        """Summarize a candidate using Anthropic."""
        prompt = f"""
        Analyze this MCP server candidate for the user task: "{user_task}"
        
        Candidate: {json.dumps(candidate, indent=2)}
        
        Provide a JSON response with the following fields:
        - summary: A concise summary of the server's capabilities
        - doc_quality: Integer 0-10 rating of documentation quality
        - maintainer_activity: Integer 0-10 rating of maintainer activity
        - auth_model: String describing authentication model
        - hash_pinning: Boolean indicating if hash pinning is used
        - sbom: Boolean indicating if SBOM/AI-BOM is available
        - risk_notes: String with any security risks or concerns
        """
        
        try:
            response = await self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            return json.loads(content)
        except Exception as e:
            # Fallback to heuristic summary
            return self._heuristic_summary(candidate, user_task)
    
    def _heuristic_summary(self, candidate: Dict[str, Any], user_task: str) -> Dict[str, Any]:
        """Fallback heuristic summary when LLM fails."""
        name = candidate.get("name", "Unknown")
        endpoint = candidate.get("endpoint", "")
        
        return {
            "summary": f"MCP server '{name}' available at {endpoint}",
            "doc_quality": 5,
            "maintainer_activity": 5,
            "auth_model": "unknown",
            "hash_pinning": False,
            "sbom": False,
            "risk_notes": "Limited information available"
        }


class HeuristicProvider(LLMProvider):
    """Heuristic provider when no LLM credentials are available."""
    
    async def summarize(self, candidate: Dict[str, Any], user_task: str) -> Dict[str, Any]:
        """Generate heuristic summary."""
        name = candidate.get("name", "Unknown")
        endpoint = candidate.get("endpoint", "")
        docs = candidate.get("docs_snippets", [])
        
        # Simple heuristics
        doc_quality = min(10, len(docs) * 2)  # More docs = higher quality
        maintainer_activity = 5  # Default middle score
        
        # Check for common auth patterns
        auth_model = "unknown"
        if any("api_key" in doc.lower() for doc in docs):
            auth_model = "api_key"
        elif any("oauth" in doc.lower() for doc in docs):
            auth_model = "oauth"
        elif any("https" in doc.lower() for doc in docs):
            auth_model = "https"
        
        # Check for security indicators
        hash_pinning = any("hash" in doc.lower() or "digest" in doc.lower() for doc in docs)
        sbom = any("sbom" in doc.lower() or "bom" in doc.lower() for doc in docs)
        
        return {
            "summary": f"MCP server '{name}' available at {endpoint}. Found {len(docs)} documentation snippets.",
            "doc_quality": doc_quality,
            "maintainer_activity": maintainer_activity,
            "auth_model": auth_model,
            "hash_pinning": hash_pinning,
            "sbom": sbom,
            "risk_notes": "Heuristic analysis - limited information available"
        }


def get_llm_provider() -> LLMProvider:
    """Get the appropriate LLM provider based on configuration."""
    if not settings.has_llm_credentials:
        return HeuristicProvider()
    
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAIProvider()
    elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider()
    else:
        return HeuristicProvider()


# Global LLM instance
llm = get_llm_provider() 