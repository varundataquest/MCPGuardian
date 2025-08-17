from __future__ import annotations

import asyncio
import json
import os
from typing import List, Optional
import time
import webbrowser
import uvicorn
from dotenv import load_dotenv

import typer
from rich.console import Console
from rich.table import Table

from mcp_harvest.normalize import server_to_csv_row
from mcp_harvest.storage.io import append_deltas, ensure_data_files, read_servers_csv, write_servers_csv
from mcp_harvest.storage.manifest import update_fingerprint_and_delta
from mcp_harvest.crawl.mcp_get import MCPGetCrawler
from mcp_harvest.crawl.docker_registry import DockerRegistryCrawler
from mcp_harvest.crawl.smithery import SmitheryCrawler
from mcp_harvest.crawl.opentools import OpenToolsCrawler
from mcp_harvest.crawl.mcp_servers_dir import MCPServersDirCrawler
from mcp_harvest.crawl.github_search import GithubSearchCrawler
from mcp_harvest.reputation import compute_reputation
from mcp_harvest.query import search
from mcp_harvest.ranking import rank_servers
from mcp_harvest.features import kmeans_clusters, plot_clusters
from harvest.discovery.run import discover as run_discover
from harvest.recommend.run import recommend as run_recommend
from harvest.discovery.model import train_from_jsonl
from mcp_harvest.integrate_discover import integrate_discovered_servers


load_dotenv()
app = typer.Typer(help="MCP registry harvester")
console = Console()


async def _run_crawlers(crawlers: List[object], include_set: Optional[set[str]], exclude_set: set[str]) -> List[object]:
    tasks = []
    for crawler in crawlers:
        if include_set is not None and crawler.name not in include_set:
            continue
        if crawler.name in exclude_set:
            continue
        tasks.append(crawler.run())
    results = await asyncio.gather(*tasks)
    all_servers = []
    for servers in results:
        all_servers.extend(servers)
    return all_servers


@app.command()
def crawl(include: Optional[str] = typer.Option(None, help="Comma-separated registry names"), exclude: Optional[str] = typer.Option(None, help="Comma-separated registry names"), fixtures_dir: Optional[str] = typer.Option(None, help="Path to synthetic fixtures for deterministic runs")) -> None:
    os.environ["CRAWL_INCLUDE"] = include or os.environ.get("CRAWL_INCLUDE", "")
    os.environ["CRAWL_EXCLUDE"] = exclude or os.environ.get("CRAWL_EXCLUDE", "")
    if fixtures_dir:
        os.environ["MCP_FIXTURES_DIR"] = fixtures_dir
    ensure_data_files()

    include_set = set((os.environ.get("CRAWL_INCLUDE") or "").split(",")) if os.environ.get("CRAWL_INCLUDE") else None
    exclude_set = set((os.environ.get("CRAWL_EXCLUDE") or "").split(",")) if os.environ.get("CRAWL_EXCLUDE") else set()

    crawlers = [
        MCPGetCrawler(),
        DockerRegistryCrawler(),
        SmitheryCrawler(),
        OpenToolsCrawler(),
        MCPServersDirCrawler(),
        GithubSearchCrawler(),
    ]

    all_servers = asyncio.run(_run_crawlers(crawlers, include_set, exclude_set))

    rows = []
    deltas = []
    for server in all_servers:
        # fingerprint + delta
        fp, delta_obj = update_fingerprint_and_delta(server.server_id, server.registry, server.model_dump())
        server.fingerprint_sha256 = fp.sha256
        # reputation
        server.reputation_score = compute_reputation(
            registries_seen_in=server.registries_seen_in,
            curated_docker="curated" in (server.notes or ""),
            supply_chain_flags={},
            env_vars=[ev.model_dump() for ev in server.env_vars],
            github_stats=None,
            recency_days=30,
        )
        row = server_to_csv_row(server)
        rows.append(row)
        if delta_obj is not None:
            deltas.append(delta_obj.model_dump())

    if rows:
        write_servers_csv(rows)
    if deltas:
        append_deltas(deltas)
    console.print(f"Crawled {len(rows)} servers from {len(crawlers)} sources")


@app.command()
def query(q: str, top: int = 5, require_runtime: Optional[str] = None) -> None:
    df = read_servers_csv()
    if df.empty:
        console.print("No data in servers.csv yet. Run crawl first.")
        raise typer.Exit(code=1)
    records = rank_servers(df, q, top=top, runtime=require_runtime)
    console.print(json.dumps(records, ensure_ascii=False))


@app.command()
def discover(q: str = typer.Option(..., help="Keyword to discover MCP servers / tools"), limit: int = typer.Option(120, help="Max candidates to collect"), top: int = typer.Option(20, help="Top results to print")) -> None:
    """Discover best MCP servers/tools for a keyword using web + registry sources."""
    results = asyncio.run(run_discover(q, limit))
    console.print(json.dumps(results[:top], ensure_ascii=False))


@app.command()
def recommend(desc: str = typer.Option(..., help="Free-text agent description"), top: int = typer.Option(10, help="Top recommendations")) -> None:
    resp = run_recommend(desc, top_k=top)
    console.print(json.dumps(resp, ensure_ascii=False))


@app.command()
def train_discover_model(glob_pattern: str = typer.Option("data/discover_*.jsonl", help="Path glob of discover jsonl files")) -> None:
    path = train_from_jsonl(glob_pattern)
    console.print(json.dumps({"model": path}))


@app.command()
def explain(server_id: str) -> None:
    df = read_servers_csv()
    row = df[df["server_id"] == server_id]
    if row.empty:
        console.print(f"Server {server_id} not found")
        raise typer.Exit(code=1)
    record = row.iloc[0].to_dict()
    table = Table(title=f"{record.get('display_name') or record.get('server_id')}")
    for key in ["runtime", "install", "auth_required", "transports", "registries_seen_in", "source_repo", "homepage"]:
        table.add_row(key, str(record.get(key, "")))
    console.print(table)


@app.command()
def clusters(k: int = 12, plot: Optional[str] = typer.Option(None, help="Path to save PNG plot")) -> None:
    df = read_servers_csv()
    if df.empty:
        console.print("No data in servers.csv yet.")
        raise typer.Exit(code=1)
    result = kmeans_clusters(df, k=k)
    labels = result["labels"]
    console.print(json.dumps(result))
    if plot:
        plot_clusters(df, labels, plot)
        console.print(f"Saved cluster plot to {plot}")


@app.command()
def integrate_discover() -> None:
    """Integrate discovered MCP servers from JSONL files into the main dataset."""
    count = integrate_discovered_servers()
    console.print(f"Integration complete. Added {count} new servers to the dataset.")


@app.command()
def devserver(
    fixtures_dir: Optional[str] = typer.Option(None, help="Path to fixtures; defaults to ./fixtures if present"),
    include: Optional[str] = typer.Option(None, help="Registries to include"),
    exclude: Optional[str] = typer.Option(None, help="Registries to exclude"),
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Enable auto-reload (experimental when launched programmatically)"),
    open_browser: bool = typer.Option(True, help="Open browser to the UI"),
) -> None:
    # Default fixtures directory if not provided
    if fixtures_dir is None and os.path.isdir("fixtures"):
        fixtures_dir = os.path.abspath("fixtures")
    # Preload data
    crawl(include=include, exclude=exclude, fixtures_dir=fixtures_dir)
    # Integrate discovered servers
    integrate_discovered_servers()
    url = f"http://{host}:{port}/"
    if open_browser:
        # Small delay to allow server to start
        typer.echo(f"Opening {url} in your browser…")
        # Will open shortly after we start the server
        def _open():
            time.sleep(0.8)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        import threading

        threading.Thread(target=_open, daemon=True).start()
    # Start server (blocking)
    uvicorn.run("mcp_harvest.api:app", host=host, port=port, reload=reload, log_level="warning")


