"""MCP server implementation."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from ..db import SessionLocal
from ..models import Server as DBServer, Run
from ..graph import run_pipeline
from ..config import settings


class MCPServer:
    """MCP server for the multi-agent selector."""
    
    def __init__(self):
        self.server = Server("mcp-multiagent-selector")
        self.setup_tools()
    
    def setup_tools(self):
        """Setup MCP tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="run_selection_pipeline",
                        description="Run the multi-agent pipeline to find and rank MCP servers for a given task",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "user_task": {
                                    "type": "string",
                                    "description": "Natural language description of the task"
                                },
                                "max_candidates": {
                                    "type": "integer",
                                    "description": "Maximum number of candidates to process",
                                    "default": 50
                                }
                            },
                            "required": ["user_task"]
                        }
                    ),
                    Tool(
                        name="get_last_results",
                        description="Get the last N results from the database",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of results to return",
                                    "default": 10
                                }
                            }
                        }
                    ),
                    Tool(
                        name="connect_agent_instructions",
                        description="Get connection instructions for the top-k ranked servers",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "top_k": {
                                    "type": "integer",
                                    "description": "Number of top servers to include",
                                    "default": 3
                                }
                            }
                        }
                    ),
                    Tool(
                        name="health",
                        description="Health check endpoint",
                        inputSchema={
                            "type": "object",
                            "properties": {}
                        }
                    )
                ]
            )
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            
            if name == "run_selection_pipeline":
                return await self.run_selection_pipeline(arguments)
            elif name == "get_last_results":
                return await self.get_last_results(arguments)
            elif name == "connect_agent_instructions":
                return await self.connect_agent_instructions(arguments)
            elif name == "health":
                return await self.health_check()
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def run_selection_pipeline(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Run the selection pipeline."""
        user_task = arguments.get("user_task", "")
        max_candidates = arguments.get("max_candidates", 50)
        
        if not user_task:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="Error: user_task is required"
                    )
                ],
                isError=True
            )
        
        try:
            # Run the pipeline
            result = await run_pipeline(user_task, max_candidates)
            
            # Format the response
            ranked_servers = result.get("ranked_servers", [])
            
            response_text = f"Pipeline completed successfully!\n\n"
            response_text += f"Found {len(ranked_servers)} ranked servers for task: '{user_task}'\n\n"
            
            for i, server in enumerate(ranked_servers[:5], 1):  # Show top 5
                response_text += f"{i}. {server['name']} (Score: {server['score']})\n"
                response_text += f"   Endpoint: {server['endpoint']}\n"
                response_text += f"   Summary: {server['summary'][:100]}...\n\n"
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=response_text
                    )
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error running pipeline: {str(e)}"
                    )
                ],
                isError=True
            )
    
    async def get_last_results(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Get last results from database."""
        limit = arguments.get("limit", 10)
        
        try:
            db = SessionLocal()
            try:
                # Get the most recent completed run
                latest_run = db.query(Run).filter(
                    Run.status == "completed"
                ).order_by(Run.finished_at.desc()).first()
                
                if not latest_run or not latest_run.result:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text="No completed runs found"
                            )
                        ]
                    )
                
                ranked_servers = latest_run.result.get("ranked_servers", [])
                ranked_servers = ranked_servers[:limit]
                
                response_text = f"Last {len(ranked_servers)} results from run {latest_run.id}:\n\n"
                response_text += f"Task: {latest_run.user_task}\n\n"
                
                for i, server in enumerate(ranked_servers, 1):
                    response_text += f"{i}. {server['name']} (Score: {server['score']})\n"
                    response_text += f"   Endpoint: {server['endpoint']}\n"
                    response_text += f"   Summary: {server['summary'][:100]}...\n\n"
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=response_text
                        )
                    ]
                )
                
            finally:
                db.close()
                
        except Exception as e:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error getting results: {str(e)}"
                    )
                ],
                isError=True
            )
    
    async def connect_agent_instructions(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Get connection instructions for top servers."""
        top_k = arguments.get("top_k", 3)
        
        try:
            db = SessionLocal()
            try:
                # Get top ranked servers
                results = db.query(DBServer).join(
                    Run, DBServer.id == Run.id
                ).filter(
                    Run.status == "completed"
                ).order_by(Run.finished_at.desc()).limit(top_k).all()
                
                if not results:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text="No servers found"
                            )
                        ]
                    )
                
                # Generate connection instructions
                instructions = {
                    "servers": [],
                    "client_config": {
                        "timeout": 30,
                        "retries": 3,
                        "backoff_factor": 2
                    },
                    "capabilities": [],
                    "suggested_timeouts": {
                        "connection": 10,
                        "read": 30,
                        "write": 30
                    },
                    "auth_notes": [],
                    "retry_config": {
                        "max_retries": 3,
                        "backoff_factor": 2,
                        "status_forcelist": [500, 502, 503, 504]
                    }
                }
                
                for server in results:
                    server_info = {
                        "name": server.name,
                        "endpoint": server.endpoint,
                        "connection_string": f"mcp://{server.endpoint}"
                    }
                    instructions["servers"].append(server_info)
                
                response_text = f"Connection instructions for top {len(results)} servers:\n\n"
                response_text += f"Client Configuration:\n"
                response_text += f"- Timeout: {instructions['client_config']['timeout']}s\n"
                response_text += f"- Retries: {instructions['client_config']['retries']}\n\n"
                
                response_text += f"Servers:\n"
                for i, server in enumerate(instructions["servers"], 1):
                    response_text += f"{i}. {server['name']}\n"
                    response_text += f"   Connection: {server['connection_string']}\n\n"
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=response_text
                        )
                    ]
                )
                
            finally:
                db.close()
                
        except Exception as e:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error generating instructions: {str(e)}"
                    )
                ],
                isError=True
            )
    
    async def health_check(self) -> CallToolResult:
        """Health check endpoint."""
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"OK - MCP Multi-Agent Selector v0.1.0 - {datetime.utcnow().isoformat()}"
                )
            ]
        )
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mcp-multiagent-selector",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )


async def main():
    """Main entry point."""
    server = MCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main()) 