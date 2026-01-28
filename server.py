"""
ScreenApp MCP Server with API Key Authentication
"""

from fastmcp import FastMCP
import httpx
import os
from typing import Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SCREENAPP_API_KEY = os.getenv("SCREENAPP_API_KEY")
SCREENAPP_API_BASE = "https://api.screenapp.io"

# Initialize FastMCP without OAuth (using API key in headers instead)
mcp = FastMCP(name="ScreenApp", description="ScreenApp MCP server")

async def get_headers() -> dict:
    """Get headers with API key"""
    return {
        "Authorization": f"Bearer {SCREENAPP_API_KEY}",
        "Content-Type": "application/json"
    }

async def make_api_request(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    params: Optional[dict] = None
) -> dict:
    """Make authenticated request to ScreenApp API"""
    url = f"{SCREENAPP_API_BASE}{endpoint}"
    headers = await get_headers()
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        if method == "GET":
            response = await client.get(url, headers=headers, params=params)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers, json=data)
        
        response.raise_for_status()
        return response.json()

# Tools (same as before but without context.auth)
@mcp.tool()
async def get_profile() -> dict:
    """Get the current user's ScreenApp profile information"""
    return await make_api_request("GET", "/user/v1/profile")

@mcp.tool()
async def list_teams() -> dict:
    """List all teams the user belongs to"""
    return await make_api_request("GET", "/team/v1")

@mcp.tool()
async def list_recordings(team_id: str, limit: int = 20, offset: int = 0) -> dict:
    """List recordings from a team
    
    Args:
        team_id: The team ID
        limit: Number of recordings (default: 20)
        offset: Pagination offset (default: 0)
    """
    params = {"limit": limit, "offset": offset}
    return await make_api_request("GET", f"/file/v1/list/{team_id}", params=params)

@mcp.tool()
async def search_recordings(team_id: str, query: str) -> dict:
    """Search recordings by query
    
    Args:
        team_id: The team ID
        query: Search query
    """
    data = {"query": query}
    return await make_api_request("POST", f"/file/v1/search/{team_id}", data=data)

@mcp.tool()
async def ask_recording(file_id: str, question: str) -> dict:
    """Ask AI about a recording
    
    Args:
        file_id: The recording ID
        question: Question to ask
    """
    data = {"question": question}
    return await make_api_request("POST", f"/file/v1/{file_id}/ask", data=data)

if __name__ == "__main__":
    import uvicorn
    
    if not SCREENAPP_API_KEY:
        logger.error("❌ SCREENAPP_API_KEY must be set")
        import sys
        sys.exit(1)
    
    logger.info("🚀 Starting ScreenApp MCP Server")
    
    app = mcp.http_app()
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")