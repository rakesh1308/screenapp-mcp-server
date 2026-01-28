# server.py
from fastmcp import FastMCP
import httpx
import os
import sys
from typing import Optional, List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("ScreenApp MCP Server")

# ScreenApp API configuration
SCREENAPP_API_BASE = "https://api.screenapp.io/v2"
SCREENAPP_API_KEY = os.getenv("SCREENAPP_API_KEY")

def get_headers() -> Dict[str, str]:
    """Get authorization headers for ScreenApp API"""
    if not SCREENAPP_API_KEY:
        raise ValueError("SCREENAPP_API_KEY environment variable is not set")
    
    return {
        "Authorization": f"Bearer {SCREENAPP_API_KEY}",
        "Content-Type": "application/json"
    }

# ============================================================================
# TEAM MANAGEMENT
# ============================================================================

@mcp.tool()
async def list_teams() -> dict:
    """List all teams the user belongs to"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{SCREENAPP_API_BASE}/teams",
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to list teams: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def get_team(team_id: str) -> dict:
    """Get detailed information about a specific team
    
    Args:
        team_id: The team ID
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{SCREENAPP_API_BASE}/team/{team_id}",
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get team: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# RECORDING/FILE MANAGEMENT
# ============================================================================

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
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{SCREENAPP_API_BASE}/teams/{team_id}/recordings",
                headers=get_headers(),
                params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to list recordings: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def get_recording(file_id: str) -> dict:
    """Get detailed information about a specific recording
    
    Args:
        file_id: The recording/file ID
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{SCREENAPP_API_BASE}/recordings/{file_id}",
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get recording: {e}")
            return {"success": False, "error": str(e)}

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
    payload = {"query": query}
    if created_after:
        payload["createdAfter"] = created_after
    if created_before:
        payload["createdBefore"] = created_before
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/teams/{team_id}/recordings/search",
                headers=get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to search recordings: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# AI ANALYSIS
# ============================================================================

@mcp.tool()
async def ask_recording(file_id: str, question: str) -> dict:
    """Ask AI a question about a specific recording
    
    Args:
        file_id: The recording/file ID
        question: Question to ask about the recording
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/recordings/{file_id}/ask",
                headers=get_headers(),
                json={"question": question}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to ask recording: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def ask_multiple_recordings(
    team_id: str,
    question: str,
    file_ids: Optional[List[str]] = None
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
        
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/teams/{team_id}/recordings/ask",
                headers=get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to ask multiple recordings: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def ask_multimodal(
    file_id: str,
    prompt_text: str,
    transcript_start: int = 0,
    transcript_end: int = 120
) -> dict:
    """Ask a multimodal AI question about a file using transcript and video
    
    Args:
        file_id: ID of the file to analyze
        prompt_text: The question or prompt to ask
        transcript_start: Start time for transcript segment (seconds, default: 0)
        transcript_end: End time for transcript segment (seconds, default: 120)
    """
    payload = {
        "promptText": prompt_text,
        "mediaAnalysisOptions": {
            "transcript": {
                "segments": [{"start": transcript_start, "end": transcript_end}]
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/files/{file_id}/ask/multimodal",
                headers=get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed multimodal analysis: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# USER PROFILE
# ============================================================================

@mcp.tool()
async def get_profile() -> dict:
    """Get the current user's ScreenApp profile information"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{SCREENAPP_API_BASE}/profile",
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get profile: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# WEBHOOK MANAGEMENT
# ============================================================================

@mcp.tool()
async def register_team_webhook(team_id: str, url: str, name: str) -> dict:
    """Register a webhook URL for team events
    
    Args:
        team_id: ID of the team
        url: Webhook URL to receive events
        name: Name/description of the webhook
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/team/{team_id}/integrations/webhook",
                headers=get_headers(),
                json={"url": url, "name": name}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to register team webhook: {e}")
            return {"success": False, "error": str(e)}

# Health check
@mcp.tool()
async def health_check() -> dict:
    """Check if the MCP server is running and API key is configured"""
    return {
        "status": "healthy",
        "api_configured": bool(SCREENAPP_API_KEY),
        "base_url": SCREENAPP_API_BASE
    }

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    # Check API key
    if not SCREENAPP_API_KEY:
        logger.error("ERROR: SCREENAPP_API_KEY environment variable is not set")
        sys.exit(1)
    
    logger.info("Starting ScreenApp MCP Server...")
    logger.info(f"API Base URL: {SCREENAPP_API_BASE}")
    
    # Run the server with SSE transport
    mcp.run(transport="sse")