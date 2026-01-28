from fastmcp import FastMCP
import httpx
import os
import sys
from typing import Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("ScreenApp MCP Server")

# ScreenApp API configuration
SCREENAPP_API_BASE = "https://api.screenapp.io/v2"
SCREENAPP_API_KEY = os.getenv("SCREENAPP_API_KEY")

def get_headers():
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
    """List all teams the user belongs to
    
    Returns:
        Dictionary containing list of teams
    """
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
        team_id: The team ID to retrieve
        
    Returns:
        Dictionary containing team details
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
        limit: Number of recordings to return (default: 20, max: 100)
        offset: Pagination offset (default: 0)
        
    Returns:
        Dictionary containing list of recordings
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
        
    Returns:
        Dictionary containing recording metadata, transcript, and analysis
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
        created_after: Filter recordings created after this date (ISO 8601 format, e.g., '2024-01-01T00:00:00Z')
        created_before: Filter recordings created before this date (ISO 8601 format)
        
    Returns:
        Dictionary containing matching recordings with highlighted snippets
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

@mcp.tool()
async def add_file_tag(file_id: str, key: str, value: str) -> dict:
    """Add a tag to a file/recording for organization
    
    Args:
        file_id: ID of the file
        key: Tag key (e.g., 'project', 'category', 'priority')
        value: Tag value (e.g., 'onboarding', 'sales-call', 'high')
        
    Returns:
        Success confirmation
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/files/{file_id}/tag",
                headers=get_headers(),
                json={"key": key, "value": value}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to add file tag: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def remove_file_tag(file_id: str, key: str) -> dict:
    """Remove a tag from a file/recording
    
    Args:
        file_id: ID of the file
        key: Tag key to remove
        
    Returns:
        Success confirmation
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(
                f"{SCREENAPP_API_BASE}/files/{file_id}/tag",
                headers=get_headers(),
                json={"key": key}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to remove file tag: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# AI ANALYSIS
# ============================================================================

@mcp.tool()
async def ask_recording(file_id: str, question: str) -> dict:
    """Ask AI a question about a specific recording using its transcript and content
    
    Args:
        file_id: The recording/file ID
        question: Question to ask about the recording (e.g., "What were the main action items?", "Summarize the key points discussed")
        
    Returns:
        AI-generated answer based on the recording content
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
    """Ask AI a question across multiple recordings to find patterns or common themes
    
    Args:
        team_id: Your ScreenApp team ID
        question: Question to ask across recordings (e.g., "What are common customer complaints?", "Compare these sales calls")
        file_ids: Optional list of specific file IDs to query. If not provided, searches across all team recordings
        
    Returns:
        AI-generated answer synthesizing information from multiple recordings
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
    """Ask a multimodal AI question about a file using transcript and video analysis
    
    Args:
        file_id: ID of the file to analyze
        prompt_text: The question or analysis prompt (e.g., "Describe what's happening in this video", "Analyze the speaker's presentation style")
        transcript_start: Start time for transcript segment in seconds (default: 0)
        transcript_end: End time for transcript segment in seconds (default: 120, use 0 for entire recording)
        
    Returns:
        AI-generated multimodal analysis combining transcript and visual information
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
    """Get the current user's ScreenApp profile information including name, email, and account settings
    
    Returns:
        Dictionary containing user profile data
    """
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

@mcp.tool()
async def get_usage_stats() -> dict:
    """Get usage statistics and billing information for the account
    
    Returns:
        Dictionary containing usage metrics (minutes processed, storage used, API calls, etc.)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{SCREENAPP_API_BASE}/account/usage",
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# WEBHOOK MANAGEMENT
# ============================================================================

@mcp.tool()
async def register_team_webhook(team_id: str, url: str, name: str) -> dict:
    """Register a webhook URL to receive real-time notifications for team recording events
    
    Args:
        team_id: ID of the team
        url: Webhook URL to receive events (must be publicly accessible HTTPS endpoint)
        name: Name/description of the webhook (e.g., "CRM Integration", "Slack Notifications")
        
    Returns:
        Success confirmation with webhook details
        
    Note:
        Webhook will receive events like: recording.completed, recording.processed, recording.failed
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

@mcp.tool()
async def unregister_team_webhook(team_id: str, url: str) -> dict:
    """Unregister/remove a webhook URL for a team
    
    Args:
        team_id: ID of the team
        url: Webhook URL to unregister (must match exactly)
        
    Returns:
        Success confirmation
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(
                f"{SCREENAPP_API_BASE}/team/{team_id}/integrations/webhook",
                headers=get_headers(),
                params={"url": url}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to unregister team webhook: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# HEALTH CHECK
# ============================================================================

@mcp.tool()
async def health_check() -> dict:
    """Check if the MCP server is running and API key is configured properly
    
    Returns:
        Server health status and configuration info
    """
    return {
        "status": "healthy",
        "api_configured": bool(SCREENAPP_API_KEY),
        "base_url": SCREENAPP_API_BASE,
        "service": "ScreenApp MCP Server",
        "version": "1.0.0"
    }

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    # Check API key before starting
    if not SCREENAPP_API_KEY:
        logger.error("❌ ERROR: SCREENAPP_API_KEY environment variable is not set")
        logger.error("Please set it with: export SCREENAPP_API_KEY='your_api_key_here'")
        sys.exit(1)
    
    logger.info("🚀 Starting ScreenApp MCP Server...")
    logger.info(f"📡 API Base URL: {SCREENAPP_API_BASE}")
    logger.info(f"✅ API Key configured: {SCREENAPP_API_KEY[:10]}...{SCREENAPP_API_KEY[-4:]}")
    
    # Run with SSE transport
    mcp.run(transport="sse")