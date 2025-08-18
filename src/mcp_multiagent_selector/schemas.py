"""Pydantic schemas for the MCP Multi-Agent Selector."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Candidate(BaseModel):
    """A candidate MCP server discovered during crawling."""
    
    name: str
    endpoint: str
    registry_meta: Optional[Dict[str, Any]] = None
    docs_snippets: List[str] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)
    source: str = "unknown"


class EvidenceSummary(BaseModel):
    """Evidence summary for a server."""
    
    summary: str
    doc_quality: int = Field(ge=0, le=10)
    maintainer_activity: int = Field(ge=0, le=10)
    auth_model: str
    hash_pinning: bool = False
    sbom: bool = False
    risk_notes: Optional[str] = None


class SecurityScore(BaseModel):
    """Security score for a server."""
    
    score: int = Field(ge=0, le=100)
    rubric: Dict[str, Any]
    computed_at: datetime


class RankedServer(BaseModel):
    """A ranked MCP server result."""
    
    name: str
    endpoint: str
    score: int = Field(ge=0, le=100)
    summary: str
    rubric_breakdown: Dict[str, Any]
    source: str
    discovered_at: datetime


class PipelineInput(BaseModel):
    """Input for the selection pipeline."""
    
    user_task: str
    max_candidates: int = Field(default=50, ge=1, le=100)


class PipelineOutput(BaseModel):
    """Output from the selection pipeline."""
    
    ranked_servers: List[RankedServer]
    total_candidates: int
    run_id: int
    completed_at: datetime


class ConnectionInstructions(BaseModel):
    """Connection instructions for MCP servers."""
    
    servers: List[Dict[str, Any]]
    client_config: Dict[str, Any]
    capabilities: List[str]
    suggested_timeouts: Dict[str, int]
    auth_notes: List[str]
    retry_config: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "0.1.0" 