#!/usr/bin/env python3
"""
MCP Guardian Web App Launcher
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    try:
        from mcp_multiagent_selector.web_app import app
        import uvicorn
        
        print("🚀 Starting MCP Guardian Web Application...")
        print("📍 Web interface will be available at: http://localhost:8000")
        print("📚 API documentation at: http://localhost:8000/docs")
        print("🔧 Press Ctrl+C to stop the server")
        print("-" * 60)
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Error importing web app: {e}")
        print("💡 Make sure you have installed the project dependencies:")
        print("   pip install -e .")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting web app: {e}")
        sys.exit(1) 