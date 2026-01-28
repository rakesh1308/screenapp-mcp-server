from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
import httpx
import os
import sys
import json
import asyncio
from typing import Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
# INITIALIZE FASTAPI APP
# ============================================================================

app = FastAPI(
    title="ScreenApp MCP Server",
    version="1.0.0",
    description="MCP server for ScreenApp API integration"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# INITIALIZE FASTMCP
# ============================================================================

mcp = FastMCP("ScreenApp")

# ============================================================================
# HTTP ENDPOINTS (for health checks and manifest)
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "service": "ScreenApp MCP Server",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "sse": "/sse",
            "manifest": "/manifest"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "api_configured": bool(SCREENAPP_API_KEY),
        "base_url": SCREENAPP_API_BASE
    }

@app.options("/sse")
async def sse_options():
    """Handle CORS preflight for SSE"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/sse")
@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP communication"""
    
    async def event_generator():
        """Generate SSE events"""
        try:
            # Read request body for POST
            if request.method == "POST":
                body = await request.body()
                if body:
                    data = json.loads(body)
                    logger.info(f"Received MCP request: {data}")
            
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
            
            # Keep connection alive
            while True:
                await asyncio.sleep(15)
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                
        except Exception as e:
            logger.error(f"SSE error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/manifest")
async def get_manifest():
    """MCP manifest endpoint"""
    return {
        "name": "ScreenApp",
        "version": "1.0.0",
        "description": "ScreenApp API integration for video/audio transcription and analysis",
        "protocol_version": "1.0",
        "capabilities": {
            "tools": True,
            "prompts": False,
            "resources": False
        },
        "tools": [
            {
                "name": "list_teams",
                "description": "List all teams the user belongs to",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "list_recordings",
                "description": "List recordings from a specific team",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team_id": {"type": "string"},
                        "limit": {"type": "number"},
                        "offset": {"type": "number"}
                    },
                    "required": ["team_id"]
                }
            },
            {
                "name": "get_recording",
                "description": "Get detailed information about a specific recording",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_id": {"type": "string"}
                    },
                    "required": ["file_id"]
                }
            },
            {
                "name": "search_recordings",
                "description": "Search for content within recording transcripts",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team_id": {"type": "string"},
                        "query": {"type": "string"},
                        "created_after": {"type": "string"},
                        "created_before": {"type": "string"}
                    },
                    "required": ["team_id", "query"]
                }
            },
            {
                "name": "ask_recording",
                "description": "Ask AI a question about a specific recording",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_id": {"type": "string"},
                        "question": {"type": "string"}
                    },
                    "required": ["file_id", "question"]
                }
            },
            {
                "name": "ask_multiple_recordings",
                "description": "Ask AI a question across multiple recordings",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team_id": {"type": "string"},
                        "question": {"type": "string"},
                        "file_ids": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["team_id", "question"]
                }
            },
            {
                "name": "get_profile",
                "description": "Get user profile information",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
    }

# ============================================================================
# FASTMCP TOOLS
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
        except Exception as e:
            logger.error(f"Failed to list teams: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def list_recordings(team_id: str, limit: int = 20, offset: int = 0) -> dict:
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
        except Exception as e:
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
        except Exception as e:
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
        query: Search query string
        created_after: Filter by date (ISO 8601)
        created_before: Filter by date (ISO 8601)
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
        except Exception as e:
            logger.error(f"Failed to search recordings: {e}")
            return {"success": False, "error": str(e)}

@mcp.tool()
async def ask_recording(file_id: str, question: str) -> dict:
    """Ask AI a question about a specific recording
    
    Args:
        file_id: The recording/file ID
        question: Question to ask
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
        except Exception as e:
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
        question: Question to ask
        file_ids: Optional list of specific file IDs
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
        except Exception as e:
            logger.error(f"Failed to ask multiple recordings: {e}")
            return {"success": False, "error": str(e)}

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
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Check API key
    if not SCREENAPP_API_KEY:
        logger.error("❌ ERROR: SCREENAPP_API_KEY environment variable is not set")
        sys.exit(1)
    
    logger.info("🚀 Starting ScreenApp MCP Server...")
    logger.info(f"📡 API Base URL: {SCREENAPP_API_BASE}")
    logger.info(f"✅ API Key configured")
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")