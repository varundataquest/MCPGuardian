from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl

Transport = Literal["stdio", "sse", "http"]
Sdk = Literal["typescript", "python", "other", "unknown"]


class SourceHit(BaseModel):
    source: str
    url: HttpUrl
    title: Optional[str] = None
    snippet: Optional[str] = None
    extra: Dict = {}


class ServerCandidate(BaseModel):
    id: str
    name: str
    description: str = ""
    repo_url: Optional[HttpUrl] = None
    homepage: Optional[HttpUrl] = None
    manifest_url: Optional[HttpUrl] = None
    sdk: Sdk = "unknown"
    transports: List[Transport] = []
    auth: List[str] = []
    tools: List[str] = []
    categories: List[str] = []
    registries: List[str] = []
    signals: Dict = {}
    query_features: Dict = {}
    risk_flags: List[str] = []
    score: float = 0.0
    reasons: List[str] = []
    provenance: List[SourceHit] = []

