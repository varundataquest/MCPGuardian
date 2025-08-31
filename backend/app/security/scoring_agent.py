from __future__ import annotations

import datetime as dt
import os
from typing import Dict, Optional, Tuple
import logging
import asyncio

import httpx
import yaml
from app.llm.gemini import get_optional_client
from app.llm.prompts import build_reputation_prompt


def _load_rubric() -> Dict:
    path = os.path.join(os.path.dirname(__file__), "rubric.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
logger = logging.getLogger(__name__)

# In-process cache to avoid repeated LLM calls for the same publisher/host pair per run
_REPUTATION_CACHE: Dict[Tuple[Optional[str], Optional[str]], Tuple[float, list]] = {}
_REPUTATION_LLM_CALLS: int = 0
try:
    _REPUTATION_LLM_BUDGET: int = int(os.getenv("REPUTATION_LLM_BUDGET", "20"))
except Exception:
    _REPUTATION_LLM_BUDGET = 20


def get_rubric_weights() -> Dict[str, float]:
    """Expose rubric weights for UI/API consumers."""
    data = _load_rubric()
    return data.get("weights", {})


async def _repo_has_file(repo_full: str, path: str, headers: Dict[str, str]) -> bool:
    url = f"https://api.github.com/repos/{repo_full}/contents/{path}"
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(connect=2.0, read=6.0, write=6.0, pool=6.0)) as c:
            r = await c.get(url)
            return r.status_code == 200
    except Exception:
        return False


async def _fetch_releases(repo_full: str, headers: Dict[str, str]) -> Optional[Dict]:
    url = f"https://api.github.com/repos/{repo_full}/releases"
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(connect=2.0, read=6.0, write=6.0, pool=6.0)) as c:
            r = await c.get(url)
            if r.status_code != 200:
                return None
            releases = r.json()
            if not isinstance(releases, list) or not releases:
                return {"count": 0, "latest_published_at": None}
            latest = releases[0].get("published_at")
            return {"count": len(releases), "latest_published_at": latest}
    except Exception:
        return None


def _homepage_root(url: str) -> Optional[httpx.URL]:
    try:
        u = httpx.URL(url)
        return u.copy_with(path="/", query=None, fragment=None)
    except Exception:
        return None


async def _head_homepage(url: str) -> Tuple[bool, bool, bool]:
    """Return (https_ok, hsts, headers_good)."""
    https_ok = str(url).startswith("https://")
    hsts = False
    headers_good = False
    root = _homepage_root(url)
    if not root:
        return https_ok, hsts, headers_good
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(connect=2.0, read=6.0, write=6.0, pool=6.0)) as c:
            r = await c.head(root, headers={"User-Agent": "MCPGuardianBot/0.1"})
            if r.status_code >= 400:
                r = await c.get(root, headers={"User-Agent": "MCPGuardianBot/0.1"})
            h = {k.lower(): v for k, v in r.headers.items()}
            hsts = "strict-transport-security" in h
            sec_headers = [
                "content-security-policy",
                "x-content-type-options",
                "x-frame-options",
                "referrer-policy",
                "permissions-policy",
            ]
            present = sum(1 for k in sec_headers if k in h)
            headers_good = present >= 2
    except Exception:
        pass
    return https_ok, hsts, headers_good


async def _check_security_txt(url: str) -> bool:
    root = _homepage_root(url)
    if not root:
        return False
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(connect=2.0, read=6.0, write=6.0, pool=6.0)) as c:
            r = await c.get(root.copy_with(path="/.well-known/security.txt"))
            return r.status_code == 200 and (r.text or "").strip() != ""
    except Exception:
        return False


async def _score_release_cadence(rubric: Dict, repo_full: Optional[str]) -> float:
    w = rubric["weights"]["release_cadence"]
    if not repo_full:
        return 0.0
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    meta = await _fetch_releases(repo_full, headers)
    if not meta:
        return 0.0
    conf = rubric["release_cadence"]
    points = 0.0
    # recent release
    latest = meta.get("latest_published_at")
    if latest:
        try:
            latest_dt = dt.datetime.fromisoformat(latest.replace("Z", "+00:00"))
            delta = dt.datetime.now(dt.timezone.utc) - latest_dt
            if delta.days <= conf["recent_days_threshold"]:
                points += conf["points_recent_release_days"]
        except Exception:
            pass
    # count
    count = meta.get("count") or 0
    if count >= conf["count_min_releases"]:
        points += conf["points_release_count"]
    return min(points, w)


async def _score_ci_presence(rubric: Dict, repo_full: Optional[str]) -> float:
    w = rubric["weights"]["ci_presence"]
    if not repo_full:
        return 0.0
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # Check workflows directory
    url = f"https://api.github.com/repos/{repo_full}/contents/.github/workflows"
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(connect=2.0, read=6.0, write=6.0, pool=6.0)) as c:
            r = await c.get(url)
            if r.status_code == 200 and isinstance(r.json(), list):
                return rubric["ci_presence"]["points"]
    except Exception:
        return 0.0
    return 0.0


def _extract_runtime_signals(enriched: Dict) -> Dict[str, bool]:
    schema = enriched.get("mcp_json") or {}
    description = (enriched.get("description") or "")

    # Aggregate as much textual context as possible
    parts = [json_dump_safe(schema), description]
    for key in ("tools", "prompts", "resources", "tags"):
        val = enriched.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.extend([str(item.get(k) or "") for k in ("name", "description", "title", "summary")])
        elif isinstance(val, str):
            parts.append(val)
    # Include any LLM flags text if present
    if isinstance(enriched.get("llm_flags"), dict):
        try:
            import json as _json
            parts.append(_json.dumps(enriched.get("llm_flags")))
        except Exception:
            pass

    txt = ("\n".join([p for p in parts if p]) or "").lower()

    # Expanded keyword sets
    shell_keywords = [
        "exec", "execute", "shell", "subprocess", "spawn", "system(", "command", "bash", "sh -c", "powershell"
    ]
    fs_keywords = [
        "writefile", "write_file", "file.write", "fs.write", "fs.writefile", "appendfile", "save file", "save",
        "upload", "mv ", "rename", "unlink", "delete", "rm ", "rmdir", "mkdir", "chmod", "chown"
    ]
    net_keywords = [
        "http://", "https://", "request", "requests", "axios", "fetch", "network", "socket",
        "websocket", "ws://", "wss://", "tcp", "grpc"
    ]
    allowlist_keywords = [
        "allowlist", "whitelist", "allowed_domains", "allowed_hosts", "allowed_origins", "scope", "scopes",
        "permissions", "capabilities", "restricted"
    ]
    ratelimit_keywords = [
        "rate limit", "ratelimit", "rate-limit", "quota", "throttle", "backoff", "retry", "burst"
    ]
    timeout_keywords = [
        "timeout", "deadline", "abortcontroller", "abortsinal", "cancel after"
    ]
    auth_keywords = [
        "oauth", "oauth2", "api key", "api_key", "apikey", "bearer", "token", "auth", "client_secret", "client id"
    ]

    def any_in(keys):
        return any(k in txt for k in keys)

    # Structured scan of mcp_json for common fields
    def flatten(obj):
        try:
            import collections.abc as cabc
        except Exception:
            cabc = None
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield str(k).lower()
                for x in flatten(v):
                    yield x
        elif isinstance(obj, (list, tuple, set)):
            for it in obj:
                for x in flatten(it):
                    yield x
        elif isinstance(obj, (str, bytes)):
            try:
                yield str(obj).lower()
            except Exception:
                pass
        else:
            try:
                yield str(obj).lower()
            except Exception:
                pass
    flat_tokens = set()
    try:
        for t in flatten(schema):
            if t:
                flat_tokens.add(t)
    except Exception:
        pass

    shell_exec = any_in(shell_keywords) or any(any(kw in tok for kw in ["shell", "exec", "command"]) for tok in flat_tokens)
    fs_write = any_in(fs_keywords) or any(any(kw in tok for kw in ["write", "save", "chmod", "unlink"]) for tok in flat_tokens)
    net_egress = any_in(net_keywords) or any(any(kw in tok for kw in ["http://", "https://", "socket", "websocket", "grpc"]) for tok in flat_tokens)
    allowlist_present = any_in(allowlist_keywords) or any(any(kw in tok for kw in ["allowlist", "allowed", "scope", "scopes", "permissions"]) for tok in flat_tokens)
    rate_limits_present = any_in(ratelimit_keywords) or any("rate" in tok or "limit" in tok or "quota" in tok for tok in flat_tokens)
    timeouts_present = any_in(timeout_keywords) or any("timeout" in tok or "deadline" in tok for tok in flat_tokens)
    auth_present = any_in(auth_keywords) or any(any(kw in tok for kw in ["oauth", "apikey", "api key", "bearer", "token"]) for tok in flat_tokens)

    return {
        "shell_exec": shell_exec,
        "fs_write": fs_write,
        "net_egress": net_egress,
        "allowlist_present": allowlist_present,
        "rate_limits_present": rate_limits_present,
        "timeouts_present": timeouts_present,
        "auth_present": auth_present,
        "limited_surface": not (shell_exec or fs_write or net_egress),
        "read_only": ("read-only" in txt) or ("readonly" in txt),
    }


def _score_runtime_capabilities(rubric: Dict, enriched: Dict) -> float:
    w = float(rubric["weights"]["runtime_capabilities"])
    conf = rubric["runtime_capabilities"]
    points = float(conf["max_points"])
    sig = _extract_runtime_signals(enriched)

    if sig["shell_exec"] and not sig["allowlist_present"]:
        points -= float(conf["penalties"]["shell_unscoped"])
    if sig["fs_write"] and not sig["allowlist_present"]:
        points -= float(conf["penalties"]["filesystem_unscoped"])
    if sig["net_egress"] and not sig["allowlist_present"]:
        points -= float(conf["penalties"]["network_unscoped"])

    if sig["allowlist_present"]:
        points += float(conf["rewards"]["has_scopes"])
    if sig["auth_present"]:
        points += float(conf["rewards"]["has_auth"])
    if sig["rate_limits_present"]:
        points += float(conf["rewards"]["has_rate_limits"])
    if sig["timeouts_present"]:
        points += float(conf["rewards"]["has_timeouts"])

    points = max(0.0, min(points, float(conf["max_points"])))
    return (points / float(conf["max_points"])) * w


async def _score_repo_hygiene(rubric: Dict, repo_full: Optional[str], github_meta: Optional[Dict]) -> float:
    w = float(rubric["weights"]["repo_hygiene"])
    if not repo_full:
        return 0.0
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    points = 0.0
    conf = rubric["repo_hygiene"]
    if github_meta and github_meta.get("license"):
        points += float(conf["license_points"])
    if await _repo_has_file(repo_full, "SECURITY.md", headers):
        points += float(conf["security_md_points"])
    if await _repo_has_file(repo_full, "CODEOWNERS", headers) or await _repo_has_file(repo_full, ".github/CODEOWNERS", headers):
        points += float(conf["codeowners_points"])
    return min(points, w)


async def _score_trust_signals(rubric: Dict, homepage_url: Optional[str]) -> float:
    w = float(rubric["weights"]["trust_signals"])
    if not homepage_url:
        return 0.0
    https_ok, hsts, _ = await _head_homepage(homepage_url)
    sec_txt = await _check_security_txt(homepage_url)
    conf = rubric["trust_signals"]
    points = 0.0
    if https_ok:
        points += float(conf["https_points"])
    if hsts:
        points += float(conf["hsts_points"])
    if sec_txt:
        points += float(conf["security_txt_points"])
    return min(points, w)


async def _score_distribution_host(rubric: Dict, enriched: Dict) -> float:
    w = float(rubric["weights"]["distribution_host"])
    conf = rubric["distribution_host"]
    points = 0.0
    if enriched.get("mcp_json"):
        points += float(conf["mcp_json_points"])
    https_ok, hsts, headers_good = await _head_homepage(enriched.get("homepage_url", ""))
    if headers_good:
        points += float(conf["security_headers_points"])
    return min(points, w)


def json_dump_safe(obj: Dict) -> str:
    try:
        import json

        return json.dumps(obj)
    except Exception:
        return ""


def _format_reason(reason_id: str, delta: float, message: str, evidence: Optional[str] = None) -> Dict:
    out = {"id": reason_id, "delta": round(float(delta), 2), "message": message}
    if evidence:
        out["evidence"] = evidence
    return out


def _score_runtime_capabilities_with_reasons(rubric: Dict, enriched: Dict) -> Tuple[float, list]:
    w = float(rubric["weights"]["runtime_capabilities"])
    conf = rubric["runtime_capabilities"]
    # Start conservative: absence of evidence is not safety
    points = 0.0
    reasons: list = []
    sig = _extract_runtime_signals(enriched)

    if sig["shell_exec"] and not sig["allowlist_present"]:
        delta = -float(conf["penalties"]["shell_unscoped"])
        points += delta
        reasons.append(_format_reason("shell_unscoped", delta, "Shell execution detected without allowlist"))
    if sig["fs_write"] and not sig["allowlist_present"]:
        delta = -float(conf["penalties"]["filesystem_unscoped"])
        points += delta
        reasons.append(_format_reason("filesystem_unscoped", delta, "Filesystem write detected without allowlist"))
    if sig["net_egress"] and not sig["allowlist_present"]:
        delta = -float(conf["penalties"]["network_unscoped"])
        points += delta
        reasons.append(_format_reason("network_unscoped", delta, "Network egress detected without allowlist"))

    if sig["allowlist_present"]:
        delta = float(conf["rewards"]["has_scopes"])
        points += delta
        reasons.append(_format_reason("has_scopes", delta, "Allowlist / scopes present"))
    if sig["auth_present"]:
        delta = float(conf["rewards"]["has_auth"])
        points += delta
        reasons.append(_format_reason("has_auth", delta, "Authentication required for sensitive operations"))
    if sig["rate_limits_present"]:
        delta = float(conf["rewards"]["has_rate_limits"])
        points += delta
        reasons.append(_format_reason("has_rate_limits", delta, "Rate limits present"))
    if sig["timeouts_present"]:
        delta = float(conf["rewards"]["has_timeouts"])
        points += delta
        reasons.append(_format_reason("has_timeouts", delta, "Operation timeouts present"))

    # Small positive credit when surface appears read-only/limited
    if sig.get("limited_surface") or sig.get("read_only"):
        d = min(1.0, float(conf["max_points"]) * 0.05)
        points += d
        label = "read_only_surface" if sig.get("read_only") else "limited_surface"
        reasons.append(_format_reason(label, d, "Limited or read-only runtime surface inferred"))

    points = max(0.0, min(points, float(conf["max_points"])))
    return (points / float(conf["max_points"])) * w, reasons


async def _score_repo_hygiene_with_reasons(rubric: Dict, repo_full: Optional[str], github_meta: Optional[Dict]) -> Tuple[float, list]:
    w = float(rubric["weights"]["repo_hygiene"])
    if not repo_full:
        return 0.0, []
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    points = 0.0
    reasons: list = []
    conf = rubric["repo_hygiene"]
    if github_meta and github_meta.get("license"):
        delta = float(conf["license_points"])
        points += delta
        reasons.append(_format_reason("license", delta, f"License present ({github_meta.get('license')})"))
    else:
        # Attempt lightweight README check for LICENSE mention if API quota limited
        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(connect=2.0, read=6.0, write=6.0, pool=6.0)) as c:
                r = await c.get(f"https://raw.githubusercontent.com/{repo_full}/HEAD/README.md")
                if r.status_code == 200 and "license" in (r.text or "").lower():
                    delta = float(conf["license_points"]) / 2.0
                    points += delta
                    reasons.append(_format_reason("readme_license_hint", delta, "README mentions license"))
        except Exception:
            pass
    if await _repo_has_file(repo_full, "SECURITY.md", headers):
        delta = float(conf["security_md_points"])
        points += delta
        reasons.append(_format_reason("security_md", delta, "SECURITY.md present"))
    if await _repo_has_file(repo_full, "CODEOWNERS", headers) or await _repo_has_file(repo_full, ".github/CODEOWNERS", headers):
        delta = float(conf["codeowners_points"])
        points += delta
        reasons.append(_format_reason("codeowners", delta, "CODEOWNERS present"))
    return min(points, w), reasons


async def _score_release_cadence_with_reasons(rubric: Dict, repo_full: Optional[str], github_meta: Optional[Dict]) -> Tuple[float, list]:
    w = float(rubric["weights"]["release_cadence"])
    if not repo_full:
        return 0.0, []
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    meta = await _fetch_releases(repo_full, headers)
    if not meta:
        meta = {"count": 0, "latest_published_at": None}
    conf = rubric["release_cadence"]
    points = 0.0
    reasons: list = []
    latest = meta.get("latest_published_at")
    if latest:
        try:
            latest_dt = dt.datetime.fromisoformat(latest.replace("Z", "+00:00"))
            delta_days = (dt.datetime.now(dt.timezone.utc) - latest_dt).days
            if delta_days <= int(conf["recent_days_threshold"]):
                d = float(conf["points_recent_release_days"])
                points += d
                reasons.append(_format_reason("recent_release", d, f"Recent release {delta_days} days ago"))
        except Exception:
            pass
    count = int(meta.get("count") or 0)
    if count >= int(conf["count_min_releases"]):
        d = float(conf["points_release_count"])
        points += d
        reasons.append(_format_reason("release_count", d, f"{count} releases in history"))
    if count == 0 and (github_meta or {}).get("pushed_at"):
        try:
            latest_dt = dt.datetime.fromisoformat(str(github_meta.get("pushed_at")).replace("Z", "+00:00"))
            delta_days = (dt.datetime.now(dt.timezone.utc) - latest_dt).days
            if delta_days <= int(conf["recent_days_threshold"]):
                d = float(conf["points_recent_release_days"]) / 2.0
                points += d
                reasons.append(_format_reason("recent_activity", d, f"Recent push {delta_days} days ago"))
        except Exception:
            pass
    return min(points, w), reasons


async def _score_ci_presence_with_reasons(rubric: Dict, repo_full: Optional[str]) -> Tuple[float, list]:
    w = float(rubric["weights"]["ci_presence"])
    if not repo_full:
        return 0.0, []
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo_full}/contents/.github/workflows"
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(connect=2.0, read=6.0, write=6.0, pool=6.0)) as c:
            r = await c.get(url)
            if r.status_code == 200 and isinstance(r.json(), list):
                pts = float(rubric["ci_presence"]["points"])
                return pts, [_format_reason("ci_workflows", pts, "CI workflows detected in .github/workflows/")]
    except Exception:
        return 0.0, []
    return 0.0, []


def _is_generic_host(host: Optional[str]) -> bool:
    if not host:
        return False
    host_l = host.lower()
    generic = {"github.com", "github.io", "npmjs.com", "pypi.org", "readthedocs.io"}
    return any(host_l == h or host_l.endswith("." + h) for h in generic)


async def _score_trust_signals_with_reasons(rubric: Dict, homepage_url: Optional[str]) -> Tuple[float, list]:
    w = float(rubric["weights"]["trust_signals"])
    if not homepage_url:
        return 0.0, []
    https_ok, hsts, _ = await _head_homepage(homepage_url)
    sec_txt = await _check_security_txt(homepage_url)
    conf = rubric["trust_signals"]
    points = 0.0
    reasons: list = []
    host = None
    try:
        host = httpx.URL(homepage_url).host
    except Exception:
        pass
    generic = _is_generic_host(host)
    if https_ok:
        d = float(conf["https_points"])
        points += d
        reasons.append(_format_reason("https", d, "HTTPS enabled"))
    if hsts and not generic:
        d = float(conf["hsts_points"])
        points += d
        reasons.append(_format_reason("hsts", d, "HSTS header present"))
    if sec_txt and not generic:
        d = float(conf["security_txt_points"])
        points += d
        reasons.append(_format_reason("security_txt", d, ".well-known/security.txt present"))
    return min(points, w), reasons


async def _score_distribution_host_with_reasons(rubric: Dict, enriched: Dict) -> Tuple[float, list]:
    w = float(rubric["weights"]["distribution_host"])
    conf = rubric["distribution_host"]
    points = 0.0
    reasons: list = []
    if enriched.get("mcp_json"):
        d = float(conf["mcp_json_points"])
        points += d
        reasons.append(_format_reason("mcp_json", d, "Public MCP JSON discovered", (enriched.get("mcp_json_url") or enriched.get("homepage_url"))))
    https_ok, hsts, headers_good = await _head_homepage(enriched.get("homepage_url", ""))
    host = None
    try:
        host = httpx.URL(enriched.get("homepage_url", "")).host
    except Exception:
        pass
    if headers_good and not _is_generic_host(host):
        d = float(conf["security_headers_points"])
        points += d
        reasons.append(_format_reason("security_headers", d, "Security headers present (CSP/XCTO/XFO/Referrer/Permissions)"))
    return min(points, w), reasons


async def _score_reputation_with_reasons(rubric: Dict, enriched: Dict) -> Tuple[float, list]:
    w = float(rubric["weights"].get("reputation", 0))
    if w <= 0:
        return 0.0, []
    enable_llm = str(os.getenv("GEMINI_ENABLE_REPUTATION", "1")).lower() in {"1", "true", "yes"}
    client = get_optional_client() if enable_llm else None
    publisher = None
    # Try to infer publisher from repo URL host path
    repo_url = enriched.get("repo_url") or ""
    try:
        if "github.com" in repo_url:
            parts = httpx.URL(repo_url).path.strip("/").split("/")
            if len(parts) >= 1:
                publisher = parts[0]
    except Exception:
        publisher = None
    host = None
    try:
        host = httpx.URL(enriched.get("homepage_url") or "").host
    except Exception:
        host = None

    # If a precomputed reputation exists on the enriched object, use it directly
    pre = enriched.get("llm_reputation")
    if isinstance(pre, dict) and (pre.get("company_reputation") is not None):
        try:
            comp = float(pre.get("company_reputation"))
        except Exception:
            comp = 50.0
        base = max(0.0, min(100.0, comp))
        score = (base / 100.0) * w
        rationale = str(pre.get("rationale") or "LLM estimate")
        reasons = [_format_reason("company_reputation", round(score, 2), f"Company reputation: {int(base)} — {rationale}")]
        # Seed cache for publisher if available to reduce future calls
        try:
            _REPUTATION_CACHE[(publisher, None)] = (score, reasons)
        except Exception:
            pass
        return score, reasons
    # Helper fallback when LLM is not available or fails (company only)
    def fallback_company_only(p: Optional[str]) -> Tuple[float, str]:
        p_l = (p or "").lower()
        known_brands = {
            "aws": 90, "amazon": 90, "amazonwebservices": 90,
            "google": 88, "microsoft": 88, "meta": 78, "openai": 80,
            "nvidia": 85, "ibm": 80, "oracle": 78, "redhat": 80,
            "mozilla": 75, "apache": 82, "jetbrains": 78, "hashicorp": 80,
            "datadog": 78, "cloudflare": 82, "vercel": 75, "netlify": 72,
            "elastic": 78, "baidu": 72, "tencent": 75, "alibaba": 75,
        }
        comp = 50.0
        for k, v in known_brands.items():
            if p_l == k or p_l.startswith(k + "/"):
                comp = v; break
        rationale = "fallback"
        return comp, rationale

    # Cache check first (exact key), then fallback to publisher-only cache
    cache_key = (publisher, host)
    if cache_key in _REPUTATION_CACHE:
        return _REPUTATION_CACHE[cache_key]
    fallback_key = (publisher, None)
    if fallback_key in _REPUTATION_CACHE:
        return _REPUTATION_CACHE[fallback_key]

    prompt = build_reputation_prompt(publisher or "unknown", host or "unknown")
    rep = None
    # Gate LLM usage: skip when brand/host known or budget exhausted
    def _should_call_llm(pub: Optional[str], h: Optional[str]) -> bool:
        p_l = (pub or "").lower()
        h_l = (h or "").lower()
        known_brands = {
            "aws", "amazon", "amazonwebservices", "google", "microsoft", "meta", "openai",
            "nvidia", "ibm", "oracle", "redhat", "mozilla", "apache", "jetbrains", "hashicorp",
            "datadog", "cloudflare", "vercel", "netlify", "elastic", "baidu", "tencent", "alibaba",
        }
        known_hosts = {"github.com", "gitlab.com", "npmjs.com", "pypi.org", "readthedocs.io", "github.io"}
        if p_l in known_brands or h_l in known_hosts:
            return False
        global _REPUTATION_LLM_CALLS, _REPUTATION_LLM_BUDGET
        return _REPUTATION_LLM_CALLS < _REPUTATION_LLM_BUDGET

    call_llm = _should_call_llm(publisher, host)
    if client and call_llm:
        # Constrain concurrent reputation calls with a small semaphore
        if not hasattr(_score_reputation_with_reasons, "_sem"):
            setattr(_score_reputation_with_reasons, "_sem", asyncio.Semaphore(2))
        sem: asyncio.Semaphore = getattr(_score_reputation_with_reasons, "_sem")
        try:
            global _REPUTATION_LLM_CALLS
            _REPUTATION_LLM_CALLS += 1
            async with sem:
                rep = await client.generate_json(prompt, category="reputation")
        except Exception as exc:
            logger.warning("reputation: LLM call failed, using fallback: %s", exc)
            rep = None
    else:
        if not client:
            logger.warning("reputation: GEMINI_API_KEY not set or client unavailable; using fallback")
        elif not call_llm:
            logger.info("reputation: skipping LLM (known brand/host or budget exhausted)")
    if not isinstance(rep, dict):
        if rep is not None:
            try:
                preview = str(rep)
                if len(preview) > 160:
                    preview = preview[:160] + "..."
                logger.warning("reputation: invalid JSON from LLM; using fallback. preview=%s", preview)
            except Exception:
                logger.warning("reputation: invalid JSON from LLM; using fallback (unprintable response)")
        comp, rationale = fallback_company_only(publisher)
        score = (float(comp) / 100.0) * w
        reasons = [
            _format_reason("company_reputation", round(score, 2), f"Company reputation (fallback): {int(comp)}"),
        ]
        _REPUTATION_CACHE[cache_key] = (score, reasons)
        return _REPUTATION_CACHE[cache_key]
    comp = float(rep.get("company_reputation") or 50)
    logger.info("reputation: LLM JSON OK: company=%s", comp)
    # Scale to weight using company only
    base = max(0.0, min(100.0, comp))
    score = (base / 100.0) * w
    reasons = []
    rationale = str(rep.get("rationale") or "LLM estimate")
    reasons.append(_format_reason("company_reputation", round(score,2), f"Company reputation: {int(comp)} — {rationale}"))
    _REPUTATION_CACHE[cache_key] = (score, reasons)
    return _REPUTATION_CACHE[cache_key]


async def score_enriched_server(enriched: Dict) -> Dict:
    rubric = _load_rubric()

    # Repo
    repo_full = None
    repo_url = enriched.get("repo_url")
    if repo_url and "github.com" in repo_url:
        try:
            parts = httpx.URL(repo_url).path.strip("/").split("/")
            if len(parts) >= 2:
                repo_full = f"{parts[0]}/{parts[1].replace('.git','')}"
        except Exception:
            repo_full = None
    if not repo_full and enriched.get("homepage_url") and "github.com" in enriched.get("homepage_url"):
        try:
            parts = httpx.URL(enriched.get("homepage_url")).path.strip("/").split("/")
            if len(parts) >= 2:
                repo_full = f"{parts[0]}/{parts[1].replace('.git','')}"
        except Exception:
            repo_full = None

    # Baseline credit
    baseline = float(rubric.get("weights", {}).get("baseline", 0))
    baseline_reasons = []
    if baseline > 0 and enriched.get("homepage_url"):
        baseline_reasons.append(_format_reason("baseline", baseline, "Baseline credit for discoverable server"))

    runtime_capabilities, r_reasons = _score_runtime_capabilities_with_reasons(rubric, enriched)
    repo_hygiene, h_reasons = await _score_repo_hygiene_with_reasons(rubric, repo_full, enriched.get("github"))
    release_cadence, rel_reasons = await _score_release_cadence_with_reasons(rubric, repo_full, enriched.get("github"))
    ci_presence, ci_reasons = await _score_ci_presence_with_reasons(rubric, repo_full)
    trust_signals, t_reasons = await _score_trust_signals_with_reasons(rubric, enriched.get("homepage_url"))
    distribution_host, d_reasons = await _score_distribution_host_with_reasons(rubric, enriched)
    reputation, rep_reasons = await _score_reputation_with_reasons(rubric, enriched)

    weights = rubric["weights"]
    total = baseline + runtime_capabilities + repo_hygiene + release_cadence + ci_presence + trust_signals + distribution_host + reputation
    overall = max(0, min(100, round(total, 2)))

    # Apply caps
    caps = rubric.get("caps", {})
    cap_val = 100.0
    sig = _extract_runtime_signals(enriched)
    shell_cap_applied = False
    if sig.get("shell_exec") and not sig.get("allowlist_present") and "shell_no_allowlist" in caps:
        cap_val = min(cap_val, float(caps["shell_no_allowlist"]))
        shell_cap_applied = True
    if repo_full and (not (enriched.get("github") or {}).get("license")) and "no_license" in caps:
        cap_val = min(cap_val, float(caps["no_license"]))
    # Enforce baseline minimum first
    if baseline > 0:
        overall = max(overall, baseline)
    # Then apply critical caps that are allowed to drop below baseline
    if shell_cap_applied:
        overall = min(overall, float(caps.get("shell_no_allowlist", overall)))

    return {
        "overall": overall,
        "breakdown": {
            "runtime_capabilities": round(runtime_capabilities, 2),
            "repo_hygiene": round(repo_hygiene, 2),
            "release_cadence": round(release_cadence, 2),
            "ci_presence": round(ci_presence, 2),
            "trust_signals": round(trust_signals, 2),
            "distribution_host": round(distribution_host, 2),
            "reputation": round(reputation, 2),
        },
        "weights": weights,
        "details": {
            "baseline": baseline_reasons,
            "runtime_capabilities": r_reasons,
            "repo_hygiene": h_reasons,
            "release_cadence": rel_reasons,
            "ci_presence": ci_reasons,
            "trust_signals": t_reasons,
            "distribution_host": d_reasons,
            "reputation": rep_reasons,
        },
    }


