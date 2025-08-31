from __future__ import annotations

import os
from typing import Dict, Optional

import httpx


def parse_github_repo_from_url(url: str) -> Optional[str]:
    # Accept https://github.com/{owner}/{repo}[...]
    if "github.com" not in url:
        return None
    try:
        parts = httpx.URL(url).path.strip("/").split("/")
    except Exception:
        return None
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    # Trim .git
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{owner}/{repo}"


async def fetch_github_repo_metadata(repo_full_name: str) -> Optional[Dict]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo_full_name}"
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(30)) as c:
        r = await c.get(url)
        if r.status_code != 200:
            return None
        data = r.json()
        topics = []
        # separate call for topics for classic API
        tr = await c.get(url + "/topics", headers={**headers, "Accept": "application/vnd.github.mercy-preview+json"})
        if tr.status_code == 200:
            topics = tr.json().get("names", [])
        return {
            "license": (data.get("license") or {}).get("spdx_id"),
            "stargazers_count": data.get("stargazers_count"),
            "forks_count": data.get("forks_count"),
            "open_issues_count": data.get("open_issues_count"),
            "pushed_at": data.get("pushed_at"),
            "topics": topics,
        }


