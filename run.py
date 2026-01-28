# run.py
import uvicorn
from server import mcp
import os

if __name__ == "__main__":
    # Get the ASGI application from FastMCP
    app = mcp.get_asgi_app()
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )