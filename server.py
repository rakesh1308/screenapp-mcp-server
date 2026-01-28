# server.py
from fastmcp import FastMCP
import httpx
import os
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

@mcp.tool()
async def add_team_tag(team_id: str, key: str, value: str) -> dict:
    """Add a tag to a team
    
    Args:
        team_id: ID of the team
        key: Tag key (e.g., 'department')
        value: Tag value (e.g., 'engineering')
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/team/{team_id}/tag",
                headers=get_headers(),
                json={"key": key, "value": value}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to add team tag: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def remove_team_tag(team_id: str, key: str) -> dict:
    """Remove a tag from a team
    
    Args:
        team_id: ID of the team
        key: Tag key to remove
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(
                f"{SCREENAPP_API_BASE}/team/{team_id}/tag",
                headers=get_headers(),
                json={"key": key}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to remove team tag: {e}")
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
    created_before: Optional[str] = None,
    owner_ids: Optional[List[str]] = None,
    parent_ids: Optional[List[str]] = None
) -> dict:
    """Search for content within recording transcripts
    
    Args:
        team_id: Your ScreenApp team ID
        query: Search query string to find in transcripts
        created_after: Filter recordings created after this date (ISO 8601)
        created_before: Filter recordings created before this date (ISO 8601)
        owner_ids: Filter by specific owner IDs
        parent_ids: Filter by specific parent folder IDs
    """
    payload = {"query": query}
    if created_after:
        payload["createdAfter"] = created_after
    if created_before:
        payload["createdBefore"] = created_before
    if owner_ids:
        payload["ownerIds"] = owner_ids
    if parent_ids:
        payload["parentIds"] = parent_ids
        
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
    """Add a tag to a file/recording
    
    Args:
        file_id: ID of the file
        key: Tag key
        value: Tag value
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
    include_transcript: bool = True,
    include_video: bool = False,
    include_screenshots: bool = False,
    transcript_start: int = 0,
    transcript_end: int = 0,
    video_start: int = 0,
    video_end: int = 0,
    screenshot_timestamps: Optional[List[int]] = None
) -> dict:
    """Ask a multimodal AI question about a file using transcript, video, and screenshots
    
    Args:
        file_id: ID of the file to analyze
        prompt_text: The question or prompt to ask
        include_transcript: Include transcript in analysis
        include_video: Include video segments in analysis
        include_screenshots: Include screenshots in analysis
        transcript_start: Start time for transcript segment (seconds)
        transcript_end: End time for transcript segment (seconds, 0 = end)
        video_start: Start time for video segment (seconds)
        video_end: End time for video segment (seconds, 0 = end)
        screenshot_timestamps: List of timestamps for screenshots (seconds)
    """
    media_options: Dict[str, Any] = {}
    
    if include_transcript:
        media_options["transcript"] = {
            "segments": [{"start": transcript_start, "end": transcript_end}]
        }
    
    if include_video:
        media_options["video"] = {
            "segments": [{"start": video_start, "end": video_end}]
        }
    
    if include_screenshots and screenshot_timestamps:
        media_options["screenshots"] = {
            "timestamps": screenshot_timestamps
        }
    
    payload = {
        "promptText": prompt_text,
        "mediaAnalysisOptions": media_options
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

@mcp.tool()
async def update_profile(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    phone_number: Optional[str] = None,
    location: Optional[str] = None,
    website: Optional[str] = None
) -> dict:
    """Update the authenticated user's profile
    
    Args:
        first_name: User's first name
        last_name: User's last name
        company: Company name
        role: Job role/title
        phone_number: Phone number
        location: Location/city
        website: Personal/company website
    """
    payload = {}
    if first_name:
        payload["firstName"] = first_name
    if last_name:
        payload["lastName"] = last_name
    if company:
        payload["company"] = company
    if role:
        payload["role"] = role
    if phone_number:
        payload["phoneNumber"] = phone_number
    if location:
        payload["location"] = location
    if website:
        payload["website"] = website
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.put(
                f"{SCREENAPP_API_BASE}/account/profile",
                headers=get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to update profile: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def add_user_tag(key: str, value: str) -> dict:
    """Add a tag to the authenticated user
    
    Args:
        key: Tag key
        value: Tag value
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/account/tag",
                headers=get_headers(),
                json={"key": key, "value": value}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to add user tag: {e}")
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

@mcp.tool()
async def unregister_team_webhook(team_id: str, url: str) -> dict:
    """Unregister a webhook URL for a team
    
    Args:
        team_id: ID of the team
        url: Webhook URL to unregister
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

@mcp.tool()
async def register_user_webhook(url: str, name: str) -> dict:
    """Register a webhook URL for user events
    
    Args:
        url: Webhook URL to receive events
        name: Name/description of the webhook
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{SCREENAPP_API_BASE}/integrations/webhook",
                headers=get_headers(),
                json={"url": url, "name": name}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to register user webhook: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def unregister_user_webhook(url: str) -> dict:
    """Unregister a webhook URL for the user
    
    Args:
        url: Webhook URL to unregister
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(
                f"{SCREENAPP_API_BASE}/integrations/webhook",
                headers=get_headers(),
                params={"url": url}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to unregister user webhook: {e}")
            return {"success": False, "error": str(e)}

# Health check endpoint
@mcp.tool()
async def health_check() -> dict:
    """Check if the MCP server is running and API key is configured"""
    return {
        "status": "healthy",
        "api_configured": bool(SCREENAPP_API_KEY),
        "base_url": SCREENAPP_API_BASE
    }