"""FastAPI health endpoint."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime

from ..config import settings

app = FastAPI(title="MCP Multi-Agent Selector", version="0.1.0")


@app.get("/healthz")
async def health_check():
    """Health check endpoint for Kubernetes."""
    return JSONResponse(
        content={
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.1.0",
            "service": "mcp-multiagent-selector"
        },
        status_code=200
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse(
        content={
            "message": "MCP Multi-Agent Selector API",
            "version": "0.1.0",
            "docs": "/docs"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.fastapi_host,
        port=settings.fastapi_port
    ) 