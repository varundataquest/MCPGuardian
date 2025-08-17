from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


RegistryName = Literal["smithery", "opentools", "docker", "mcp-get", "mcp-servers", "discovered"]
RuntimeName = Literal["python", "node", "go", "docker-image", "other", "unknown"]
AuthMethod = Literal["none", "api_key", "oauth", "other", "unknown"]
TransportName = Literal["stdio", "sse", "streamableHttp", "unknown"]


class Tool(BaseModel):
    name: str
    description: Optional[str] = None


class EnvVar(BaseModel):
    name: str
    required: bool = False
    description: Optional[str] = None


class Server(BaseModel):
    registry: RegistryName
    server_id: str = Field(..., description="Stable slug or upstream id")
    display_name: Optional[str] = None
    description: Optional[str] = None
    runtime: RuntimeName = "unknown"
    install: Optional[str] = None
    source_repo: Optional[HttpUrl | str] = None
    homepage: Optional[HttpUrl | str] = None
    license: Optional[str] = None
    maintainer: Optional[str] = None
    auth_required: AuthMethod = "unknown"
    env_vars: List[EnvVar] = Field(default_factory=list)
    tools: List[Tool] = Field(default_factory=list)
    transports: List[TransportName] = Field(default_factory=list)
    registries_seen_in: List[RegistryName] = Field(default_factory=list)
    last_seen_iso: Optional[str] = None
    first_seen_iso: Optional[str] = None
    fingerprint_sha256: Optional[str] = None
    reputation_score: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class Fingerprint(BaseModel):
    server_id: str
    registry: RegistryName
    sha256: str
    manifest: dict
    computed_at: datetime


class Delta(BaseModel):
    timestamp: datetime
    server_id: str
    registry: RegistryName
    old_sha: Optional[str]
    new_sha: str
    changed_keys: List[str] = Field(default_factory=list)


# Canonical CSV schema
CSV_COLUMNS: List[str] = [
    "registry",
    "server_id",
    "display_name",
    "description",
    "runtime",
    "install",
    "source_repo",
    "homepage",
    "license",
    "maintainer",
    "auth_required",
    "env_vars",
    "tools",
    "transports",
    "registries_seen_in",
    "last_seen_iso",
    "first_seen_iso",
    "fingerprint_sha256",
    "reputation_score",
    "tags",
    "notes",
]


