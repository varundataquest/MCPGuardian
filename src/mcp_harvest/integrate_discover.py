from __future__ import annotations

import json
import glob
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from mcp_harvest.storage.io import read_servers_csv, write_servers_csv, DATA_DIR
from mcp_harvest.normalize import server_to_csv_row
from mcp_harvest.models import Server
from mcp_harvest.reputation import compute_reputation


def load_discover_results() -> List[Dict[str, Any]]:
    """Load all discover results from JSONL files."""
    discover_files = glob.glob(str(DATA_DIR / "discover_*.jsonl"))
    all_results = []
    
    for file_path in discover_files:
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        result = json.loads(line)
                        all_results.append(result)
                    except json.JSONDecodeError:
                        continue
    
    return all_results


def convert_discover_to_server(discover_item: Dict[str, Any]) -> Server:
    """Convert a discover result to a Server object."""
    # Extract basic information
    name = discover_item.get('name', '')
    description = discover_item.get('description', '')
    repo_url = discover_item.get('repo_url', '')
    homepage = discover_item.get('homepage')
    
    # Generate a unique server_id from the name and repo
    server_id = f"discovered-{discover_item.get('id', name.lower().replace('/', '-'))}"
    
    # Extract signals for reputation scoring
    signals = discover_item.get('signals', {})
    stars = signals.get('stars', 0)
    days_since_push = signals.get('days_since_push', 365)
    license_info = signals.get('license')
    
    # Determine runtime based on repo URL patterns
    runtime = "unknown"
    if repo_url:
        if "python" in repo_url.lower() or "py" in repo_url.lower():
            runtime = "python"
        elif "node" in repo_url.lower() or "js" in repo_url.lower() or "ts" in repo_url.lower():
            runtime = "node"
        elif "docker" in repo_url.lower():
            runtime = "docker-image"
    
    # Create Server object
    server = Server(
        registry="discovered",
        server_id=server_id,
        display_name=name,
        description=description or f"MCP server for {name}",
        runtime=runtime,
        install=f"# Install from {repo_url}" if repo_url else "# Manual installation required",
        source_repo=repo_url,
        homepage=homepage,
        license=license_info,
        maintainer=None,
        auth_required="unknown",
        env_vars=[],
        tools=[],
        transports=["stdio"],  # Default assumption
        registries_seen_in=["discovered"],
        last_seen_iso=pd.Timestamp.now().isoformat(),
        first_seen_iso=pd.Timestamp.now().isoformat(),
        fingerprint_sha256="",  # Will be computed by the system
        reputation_score=compute_reputation(
            registries_seen_in=["discovered"],
            curated_docker=False,
            supply_chain_flags={},
            env_vars=[],
            github_stats={"stars": stars, "days_since_push": days_since_push} if stars > 0 else None,
            recency_days=30,
        ),
        tags=[name.lower().replace('-', ' ').replace('_', ' ')],
        notes=f"Discovered via search. Score: {discover_item.get('score', 0)}. {', '.join(discover_item.get('reasons', []))}"
    )
    
    return server


def integrate_discovered_servers() -> int:
    """Integrate discovered servers into the main servers.csv dataset."""
    # Load existing servers
    existing_df = read_servers_csv()
    existing_ids = set(existing_df['server_id'].astype(str))
    
    # Load discover results
    discover_results = load_discover_results()
    
    # Convert to Server objects
    new_servers = []
    for result in discover_results:
        try:
            server = convert_discover_to_server(result)
            # Only add if not already in the dataset
            if server.server_id not in existing_ids:
                new_servers.append(server)
        except Exception as e:
            print(f"Error converting discover result: {e}")
            continue
    
    if not new_servers:
        print("No new servers to integrate")
        return 0
    
    # Convert to CSV rows
    new_rows = []
    for server in new_servers:
        try:
            row = server_to_csv_row(server)
            new_rows.append(row)
        except Exception as e:
            print(f"Error converting server to CSV row: {e}")
            continue
    
    # Add to existing dataset
    if new_rows:
        all_rows = existing_df.to_dict('records') + new_rows
        write_servers_csv(all_rows)
        print(f"Integrated {len(new_rows)} discovered servers into the dataset")
        return len(new_rows)
    
    return 0


def main():
    """Main function to run the integration."""
    count = integrate_discovered_servers()
    print(f"Integration complete. Added {count} new servers.")


if __name__ == "__main__":
    main() 