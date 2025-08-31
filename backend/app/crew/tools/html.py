from __future__ import annotations

from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from urllib.parse import urljoin


def extract_mcp_fields(html: str, base_url: str) -> Dict:
    """Extract description, tags, tools, prompts, and any linked mcp.json.

    Uses resilient, multi-strategy selectors to tolerate layout changes.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Description strategies: meta description, og:description, twitter:description, first paragraph
    description: Optional[str] = None
    meta_candidates = [
        ("meta", {"name": "description"}),
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "twitter:description"}),
    ]
    for tag, attrs in meta_candidates:
        el = soup.find(tag, attrs=attrs)
        if el and el.get("content"):
            description = el.get("content").strip()
            break
    if not description:
        p = soup.find("p")
        if p:
            txt = p.get_text(" ", strip=True)
            description = txt[:500] if txt else None

    # Tags: common classes and data attributes
    tags: List[str] = []
    for sel in [
        ".tag",
        "[data-tag]",
        "a[href*='tag']",
        "[class*='chip']",
    ]:
        for el in soup.select(sel):
            text = el.get_text(" ", strip=True)
            if text and text.lower() not in [t.lower() for t in tags]:
                tags.append(text)

    # Tools/Prompts: heuristic sections
    def collect_list_under_heading(heading_keywords: List[str]) -> List[str]:
        out: List[str] = []
        for hsel in ["h1", "h2", "h3", "h4", "strong"]:
            for h in soup.select(hsel):
                text = h.get_text(" ", strip=True).lower()
                if any(k in text for k in heading_keywords):
                    # Find nearest list after heading
                    ul = h.find_next(["ul", "ol"])
                    if ul:
                        for li in ul.find_all("li"):
                            t = li.get_text(" ", strip=True)
                            if t:
                                out.append(t)
        return out

    tools = collect_list_under_heading(["tool", "tools"])
    prompts = collect_list_under_heading(["prompt", "prompts"]) 

    # Discover mcp.json links in page
    mcp_json_url: Optional[str] = None
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        if "/.well-known/mcp.json" in href:
            mcp_json_url = urljoin(base_url, href)
            break

    # Try to discover a GitHub repository link (owner/repo)
    repo_url: Optional[str] = None
    for a in soup.select("a[href*='github.com/']"):
        href = a.get("href")
        if not href:
            continue
        abs_url = urljoin(base_url, href)
        try:
            # only accept links of the form github.com/{owner}/{repo}
            from urllib.parse import urlparse

            p = urlparse(abs_url)
            if "github.com" in (p.netloc or ""):
                parts = (p.path or "").strip("/").split("/")
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]
                    if owner and repo and repo not in {"issues", "pulls", "actions", "topics"}:
                        repo_url = f"https://github.com/{owner}/{repo}"
                        break
        except Exception:
            continue

    return {
        "description": description,
        "tags": tags,
        "tools": tools,
        "prompts": prompts,
        "mcp_json_url": mcp_json_url,
        "repo_url": repo_url,
    }


