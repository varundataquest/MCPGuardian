import re
from datetime import datetime, timezone
from typing import List

from ..models import ServerCandidate
from ..util import stable_id

SDK_TS_PAT = re.compile(r'@modelcontextprotocol/sdk', re.I)
SDK_PY_PAT = re.compile(r'\bfrom mcp\.server\.fastmcp import FastMCP\b|\b@mcp\.tool', re.I)
TRANS_PAT = re.compile(r'\b(stdio|sse|/sse|/mcp|streamable http)\b', re.I)
AUTH_PAT = re.compile(r'\b(api key|oauth|okta|bearer|basic auth)\b', re.I)
DANGER_PAT = re.compile(r'\b(chmod|curl|bash|powershell|exec|/etc/passwd|rm -rf)\b', re.I)


def normalize_candidate(raw: dict) -> ServerCandidate:
    name = raw.get("title") or raw.get("name") or raw.get("repo_name") or ""
    homepage = raw.get("homepage")
    repo = raw.get("repo_url") or raw.get("url")
    text = " ".join([
        raw.get("description") or "",
        raw.get("readme") or "",
        raw.get("snippet") or "",
    ])
    sdk = "typescript" if SDK_TS_PAT.search(text) else ("python" if SDK_PY_PAT.search(text) else "unknown")
    # Canonicalize transports to allowed literals
    raw_transports = [t.strip().lower() for t in TRANS_PAT.findall(text)]
    mapped: List[str] = []
    for t in raw_transports:
        if t in ("stdio",):
            mapped.append("stdio")
        elif t in ("sse", "/sse"):
            mapped.append("sse")
        elif t in ("/mcp", "streamable http", "http"):
            mapped.append("http")
    transports = sorted(set(mapped))
    auth = sorted(set(x.strip() for x in AUTH_PAT.findall(text)))
    risk_flags = ["danger_terms"] if DANGER_PAT.search(text) else []
    sid = raw.get("id") or stable_id((repo or homepage or name or "unknown"))
    signals = raw.get("signals") or raw.get("extra") or {}
    # Derive days_since_push if a timestamp is available
    pushed_at = signals.get("pushed_at")
    if pushed_at and not signals.get("days_since_push"):
        try:
            ts = str(pushed_at).replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            signals["days_since_push"] = max(0, int((now - dt).total_seconds() // 86400))
        except Exception:
            pass
    return ServerCandidate(
        id=sid,
        name=name.strip() or (repo or "unknown"),
        description=raw.get("description", ""),
        repo_url=repo,
        homepage=homepage,
        manifest_url=raw.get("manifest_url"),
        sdk=sdk,
        transports=transports,
        auth=auth,
        tools=raw.get("tools", []),
        registries=raw.get("registries", []),
        signals=signals,
        risk_flags=risk_flags,
        provenance=raw.get("provenance", []),
        score=0.0,
        reasons=[],
    )

