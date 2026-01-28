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

# Initialize FastMCP (only 'name' parameter)
mcp = FastMCP("ScreenApp")

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
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()

# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def get_profile() -> dict:
    """Get the current user's ScreenApp profile information"""
    return await make_api_request("GET", "/user/v1/profile")

@mcp.tool()
async def list_teams() -> dict:
    """List all teams the user belongs to in ScreenApp"""
    return await make_api_request("GET", "/team/v1")

@mcp.tool()
async def get_team(team_id: str) -> dict:
    """Get detailed information about a specific team
    
    Args:
        team_id: The team ID
    """
    return await make_api_request("GET", f"/team/v1/{team_id}")

@mcp.tool()
async def list_recordings(team_id: str, limit: int = 20, offset: int = 0) -> dict:
    """List recordings from a specific team with pagination
    
    Args:
        team_id: The team ID
        limit: Number of recordings to return (default: 20, max: 100)
        offset: Pagination offset (default: 0)
    """
    params = {"limit": limit, "offset": offset}
    return await make_api_request("GET", f"/file/v1/list/{team_id}", params=params)

@mcp.tool()
async def get_recording(file_id: str) -> dict:
    """Get detailed information about a specific recording including transcript
    
    Args:
        file_id: The recording/file ID
    """
    return await make_api_request("GET", f"/file/v1/{file_id}")

@mcp.tool()
async def search_recordings(
    team_id: str,
    query: str,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None
) -> dict:
    """Search for content within recording transcripts
    
    Args:
        team_id: The team ID
        query: Search query string
        created_after: Filter recordings created after this date (ISO 8601 format)
        created_before: Filter recordings created before this date (ISO 8601 format)
    """
    data = {"query": query}
    if created_after:
        data["createdAfter"] = created_after
    if created_before:
        data["createdBefore"] = created_before
    
    return await make_api_request("POST", f"/file/v1/search/{team_id}", data=data)

@mcp.tool()
async def ask_recording(file_id: str, question: str) -> dict:
    """Ask AI a question about a specific recording using its transcript
    
    Args:
        file_id: The recording/file ID
        question: Question to ask about the recording (e.g., 'What were the main action items?')
    """
    data = {"question": question}
    return await make_api_request("POST", f"/file/v1/{file_id}/ask", data=data)

@mcp.tool()
async def ask_multiple_recordings(
    team_id: str,
    question: str,
    file_ids: Optional[List[str]] = None
) -> dict:
    """Ask AI a question across multiple recordings to find patterns or insights
    
    Args:
        team_id: The team ID
        question: Question to ask across recordings
        file_ids: Optional list of specific file IDs to query. If omitted, searches all team recordings.
    """
    data = {"question": question}
    if file_ids:
        data["fileIds"] = file_ids
    
    return await make_api_request("POST", f"/file/v1/ask/{team_id}", data=data)

@mcp.tool()
async def get_usage_stats() -> dict:
    """Get usage statistics and billing information for the account"""
    return await make_api_request("GET", "/user/v1/usage")

# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Validate API key
    if not SCREENAPP_API_KEY:
        logger.error("❌ ERROR: SCREENAPP_API_KEY environment variable is not set")
        import sys
        sys.exit(1)
    
    logger.info("🚀 Starting ScreenApp MCP Server")
    logger.info(f"📡 API Base: {SCREENAPP_API_BASE}")
    logger.info(f"✅ API Key configured: {SCREENAPP_API_KEY[:10]}...{SCREENAPP_API_KEY[-4:]}")
    
    # Get the HTTP app from FastMCP
    app = mcp.http_app()
    
    # Run with uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")