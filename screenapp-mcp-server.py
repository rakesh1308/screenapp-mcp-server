# screenapp_mcp/server.py
from fastmcp import FastMCP
import httpx
import os
from typing import Optional

# Initialize MCP server
mcp = FastMCP("ScreenApp MCP Server")

# ScreenApp API configuration
SCREENAPP_API_BASE = "https://api.screenapp.io/v2"
SCREENAPP_API_KEY = os.getenv("SCREENAPP_API_KEY")  # Set this in environment

async def get_headers():
    """Get authorization headers for ScreenApp API"""
    return {
        "Authorization": f"Bearer {SCREENAPP_API_KEY}",
        "Content-Type": "application/json"
    }

@mcp.tool()
async def list_recordings(
    team_id: str,
    limit: int = 20,
    offset: int = 0
) -> dict:
    """List recordings from ScreenApp
    
    Args:
        team_id: Your ScreenApp team ID
        limit: Number of recordings to return (default: 20)
        offset: Pagination offset (default: 0)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SCREENAPP_API_BASE}/teams/{team_id}/recordings",
            headers=await get_headers(),
            params={"limit": limit, "offset": offset}
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_recording(file_id: str) -> dict:
    """Get detailed information about a specific recording
    
    Args:
        file_id: The recording/file ID
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SCREENAPP_API_BASE}/recordings/{file_id}",
            headers=await get_headers()
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def search_recordings(
    team_id: str,
    query: str,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None
) -> dict:
    """Search for content within recording transcripts
    
    Args:
        team_id: Your ScreenApp team ID
        query: Search query string to find in transcripts
        created_after: Filter recordings created after this date (ISO 8601)
        created_before: Filter recordings created before this date (ISO 8601)
    """
    params = {"query": query}
    if created_after:
        params["createdAfter"] = created_after
    if created_before:
        params["createdBefore"] = created_before
        
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SCREENAPP_API_BASE}/teams/{team_id}/recordings/search",
            headers=await get_headers(),
            json=params
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def ask_recording(file_id: str, question: str) -> dict:
    """Ask AI a question about a specific recording
    
    Args:
        file_id: The recording/file ID
        question: Question to ask about the recording
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{SCREENAPP_API_BASE}/recordings/{file_id}/ask",
            headers=await get_headers(),
            json={"question": question}
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def ask_multiple_recordings(
    team_id: str,
    question: str,
    file_ids: Optional[list[str]] = None
) -> dict:
    """Ask AI a question across multiple recordings
    
    Args:
        team_id: Your ScreenApp team ID
        question: Question to ask across recordings
        file_ids: Optional specific file IDs to query
    """
    payload = {"question": question}
    if file_ids:
        payload["fileIds"] = file_ids
        
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{SCREENAPP_API_BASE}/teams/{team_id}/recordings/ask",
            headers=await get_headers(),
            json=payload
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_profile() -> dict:
    """Get the current user's ScreenApp profile information"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SCREENAPP_API_BASE}/profile",
            headers=await get_headers()
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def list_teams() -> dict:
    """List all teams the user belongs to"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SCREENAPP_API_BASE}/teams",
            headers=await get_headers()
        )
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    mcp.run()