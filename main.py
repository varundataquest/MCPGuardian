#!/usr/bin/env python3
"""Main entry point for the MCP Multi-Agent Selector."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_multiagent_selector.mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main()) 