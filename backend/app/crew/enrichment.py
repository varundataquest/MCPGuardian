from __future__ import annotations

from typing import Dict, Optional
import os

import httpx

from .tools.html import extract_mcp_fields
from .tools.github import fetch_github_repo_metadata, parse_github_repo_from_url
from app.llm.gemini import get_optional_client
from app.llm.prompts import build_enrichment_prompt

# Run-level budget for enrichment LLM calls (to avoid overuse when quota is low)
_ENRICHMENT_LLM_CALLS: int = 0
try:
    _ENRICHMENT_LLM_BUDGET: int = int(os.getenv("ENRICHMENT_LLM_BUDGET", "16"))
except Exception:
    _ENRICHMENT_LLM_BUDGET = 16


async def discover_mcp_json(base_url: str, client: httpx.AsyncClient) -> Optional[Dict]:
    # Try direct fetch of .well-known/mcp.json
    candidates = ["/.well-known/mcp.json", "/.well-known/MCP.json"]
    for path in candidates:
        try:
            r = await client.get(httpx.URL(base_url).copy_with(path=path, query=None))
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return None

async def _enrich_from_npm(homepage_url: str, client: httpx.AsyncClient) -> Dict:
    try:
        u = httpx.URL(homepage_url)
        if u.host not in {"www.npmjs.com", "npmjs.com"}:
            return {}
        parts = [p for p in (u.path or "").split("/") if p]
        if len(parts) < 2 or parts[0] != "package":
            return {}
        pkg = "/".join(parts[1:])
        reg_url = f"https://registry.npmjs.org/{pkg}"
        r = await client.get(reg_url)
        if r.status_code != 200:
            return {}
        data = r.json()
        out: Dict = {}
        repo = ((data.get("repository") or {}).get("url") or "")
        if isinstance(repo, str) and repo:
            repo = repo.replace("git+", "").replace(".git", "")
            out["repo_url"] = repo
        hp = data.get("homepage")
        if not out.get("repo_url") and isinstance(hp, str) and "github.com" in hp:
            out["repo_url"] = hp
        if data.get("description"):
            out["description"] = data.get("description")
        if isinstance(data.get("keywords"), list):
            out["tags"] = [str(k) for k in data.get("keywords") if k]
        return out
    except Exception:
        return {}


async def enrich_server_candidate(candidate: Dict) -> Dict:
    """Fetch page(s) and merge enrichment fields.

    candidate keys: registry, name, slug, homepage_url, repo_url?, description?, tags?
    """
    headers = {"User-Agent": "MCPGuardianBot/0.1"}
    out = dict(candidate)
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(connect=2.0, read=6.0, write=6.0, pool=6.0)) as c:
        # Fetch homepage for HTML metadata
        try:
            resp = await c.get(candidate["homepage_url"]) 
            if resp.status_code == 200:
                fields = extract_mcp_fields(resp.text, candidate["homepage_url"])
                for k in ["description", "tags", "tools", "prompts"]:
                    if fields.get(k):
                        if k == "tags":
                            # merge unique
                            merged = list({*(out.get("tags") or []), *fields["tags"]})
                            out["tags"] = merged
                        else:
                            out[k] = fields[k]
                # Pick up repo_url from page if missing
                if not out.get("repo_url") and fields.get("repo_url"):
                    out["repo_url"] = fields.get("repo_url")
                # NPM registry enrichment
                npm_bits = await _enrich_from_npm(candidate["homepage_url"], c)
                if npm_bits:
                    if npm_bits.get("repo_url") and not out.get("repo_url"):
                        out["repo_url"] = npm_bits["repo_url"]
                    if npm_bits.get("description") and not out.get("description"):
                        out["description"] = npm_bits["description"]
                    if npm_bits.get("tags"):
                        out["tags"] = list({*(out.get("tags") or []), *npm_bits["tags"]})

                # Fetch well-known or linked mcp.json
                mcp_json = None
                mcp_link = fields.get("mcp_json_url")
                if mcp_link:
                    try:
                        r = await c.get(mcp_link)
                        if r.status_code == 200:
                            mcp_json = r.json()
                    except Exception:
                        pass
                if mcp_json is None:
                    mj = await discover_mcp_json(candidate["homepage_url"], c)
                    if mj:
                        mcp_json = mj
                        out["mcp_json_url"] = str(httpx.URL(candidate["homepage_url"]).copy_with(path="/.well-known/mcp.json", query=None))
                if mcp_json:
                    out["mcp_json"] = mcp_json
                    if mcp_link:
                        out["mcp_json_url"] = mcp_link
        except Exception:
            pass

        # Hosting / connectivity / headers
        try:
            base = httpx.URL(candidate["homepage_url"]) 
            root = base.copy_with(path="/", query=None, fragment=None)
            # HEAD first; fallback to GET
            hr = await c.head(root)
            if hr.status_code >= 400:
                hr = await c.get(root)
            hdrs = {k.lower(): v for k, v in hr.headers.items()}
            https_ok = str(candidate["homepage_url"]).startswith("https://")
            hsts = "strict-transport-security" in hdrs
            sec_headers = [
                "content-security-policy",
                "x-content-type-options",
                "x-frame-options",
                "referrer-policy",
                "permissions-policy",
            ]
            headers_good = sum(1 for k in sec_headers if k in hdrs) >= 2
            st = await c.get(root.copy_with(path="/.well-known/security.txt"))
            security_txt = st.status_code == 200 and (st.text or "").strip() != ""
            out["hosting"] = {
                "host_domain": base.host,
                "public_mcp_json": bool(out.get("mcp_json")),
                "mcp_json_url": out.get("mcp_json_url"),
                "https": https_ok,
                "hsts": hsts,
                "security_txt": security_txt,
                "security_headers_good": headers_good,
            }
            out["connectivity"] = {
                "publicly_connectable": bool(out.get("mcp_json")),
                "hint": "Public .well-known/mcp.json discovered" if out.get("mcp_json") else "No public .well-known/mcp.json found",
            }
        except Exception:
            pass

        # GitHub enrichment if repo_url present
        repo_url = out.get("repo_url")
        repo_full = parse_github_repo_from_url(repo_url) if repo_url else None
        if repo_full:
            meta = await fetch_github_repo_metadata(repo_full)
            if meta:
                out["github"] = meta
    # Project visibility
    out["project_visibility"] = "open_source" if (out.get("repo_url")) else "closed_source"

    # Deployment hints
    try:
        topics = [str(t).lower() for t in ((out.get("github") or {}).get("topics") or [])]
        tags = [str(t).lower() for t in (out.get("tags") or [])]
        keys = set(topics + tags)
        hints = []
        if any(k in keys for k in ["docker", "container"]):
            hints.append("Docker")
        if any(k in keys for k in ["npm", "node", "typescript", "javascript"]):
            hints.append("npm/Node.js")
        if any(k in keys for k in ["pypi", "python", "pip"]):
            hints.append("pip/PyPI")
        if "go" in keys:
            hints.append("Go")
        if any(k in keys for k in ["homebrew", "brew"]):
            hints.append("Homebrew")
        readme_url = None
        if out.get("repo_url") and "github.com" in out.get("repo_url"):
            readme_url = out.get("repo_url").rstrip("/") + "#readme"
        out["deployment"] = {
            "hints": hints,
            "readme_url": readme_url,
        }
    except Exception:
        pass

    # Optional LLM augmentation (single call combines normalization + risk flags)
    try:
        enable_llm = str(os.getenv("GEMINI_ENABLE_ENRICHMENT", "1")).lower() in {"1", "true", "yes"}
        client = get_optional_client() if enable_llm else None
        def _needs_llm(o: Dict) -> bool:
            # Looser heuristic: enrich when ANY critical gap exists
            desc = (o.get("description") or "").strip()
            tags = o.get("tags") or []
            tools = o.get("tools") or []
            prompts = o.get("prompts") or []
            # Gaps
            if not desc or len(desc) < 60:
                return True
            if len(tags) < 2:
                return True
            if not tools and not prompts:
                return True
            if not o.get("mcp_json"):
                return True
            # Closed-source with no repo metadata
            if (o.get("project_visibility") == "closed_source") and (not o.get("repo_url")):
                return True
            return False

        global _ENRICHMENT_LLM_CALLS, _ENRICHMENT_LLM_BUDGET
        allowed = _ENRICHMENT_LLM_CALLS < _ENRICHMENT_LLM_BUDGET
        if client and allowed and _needs_llm(out):
            # Build a compact summary for the model from fields we have
            summary_lines = []
            if out.get("description"):
                summary_lines.append(f"Description: {out['description']}")
            if out.get("tags"):
                summary_lines.append(f"Tags: {', '.join(out.get('tags') or [])}")
            if out.get("tools"):
                summary_lines.append(f"Tools: {', '.join([t if isinstance(t,str) else (t.get('name') or '') for t in (out.get('tools') or [])])}")
            if out.get("prompts"):
                summary_lines.append(f"Prompts: {', '.join([p if isinstance(p,str) else (p.get('name') or '') for p in (out.get('prompts') or [])])}")
            if out.get("mcp_json"):
                summary_lines.append("mcp.json present: true")
            summary = "\n".join(summary_lines)[:4000]

            enriched = await client.generate_json(build_enrichment_prompt(summary), category="enrichment")
            if isinstance(enriched, dict):
                _ENRICHMENT_LLM_CALLS += 1
                if enriched.get("description") and not out.get("description"):
                    out["description"] = enriched.get("description")
                if isinstance(enriched.get("tags"), list):
                    merged = list({*(out.get("tags") or []), *[str(x) for x in enriched.get("tags") if x]})
                    out["tags"] = merged
                if isinstance(enriched.get("tools"), list) and enriched.get("tools"):
                    out["tools"] = enriched.get("tools")
                if isinstance(enriched.get("prompts"), list) and enriched.get("prompts"):
                    out["prompts"] = enriched.get("prompts")
                if isinstance(enriched.get("resources"), list) and enriched.get("resources"):
                    out["resources"] = enriched.get("resources")
                if isinstance(enriched.get("risk_flags"), dict):
                    out.setdefault("llm_flags", {}).update(enriched.get("risk_flags"))
    except Exception:
        pass

    return out


