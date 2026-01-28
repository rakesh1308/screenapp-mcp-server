from fastmcp import FastMCP
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="ScreenApp MCP Server")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ScreenApp API configuration
SCREENAPP_API_BASE = "https://api.screenapp.io/v2"
SCREENAPP_API_KEY = os.getenv("SCREENAPP_API_KEY")

def get_headers():
    if not SCREENAPP_API_KEY:
        raise ValueError("SCREENAPP_API_KEY not set")
    return {
        "Authorization": f"Bearer {SCREENAPP_API_KEY}",
        "Content-Type": "application/json"
    }

# Health check
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "ScreenApp MCP Server",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "api_configured": bool(SCREENAPP_API_KEY)
    }

# MCP Manifest endpoint (required by LobeChat)
@app.get("/manifest")
async def get_manifest():
    return {
        "name": "ScreenApp MCP Server",
        "version": "1.0.0",
        "description": "MCP server for ScreenApp API integration",
        "tools": [
            {
                "name": "list_teams",
                "description": "List all teams the user belongs to",
                "parameters": {}
            },
            {
                "name": "list_recordings",
                "description": "List recordings from ScreenApp",
                "parameters": {
                    "team_id": {"type": "string", "required": True},
                    "limit": {"type": "number", "default": 20},
                    "offset": {"type": "number", "default": 0}
                }
            },
            {
                "name": "search_recordings",
                "description": "Search for content within recording transcripts",
                "parameters": {
                    "team_id": {"type": "string", "required": True},
                    "query": {"type": "string", "required": True}
                }
            },
            {
                "name": "ask_recording",
                "description": "Ask AI a question about a specific recording",
                "parameters": {
                    "file_id": {"type": "string", "required": True},
                    "question": {"type": "string", "required": True}
                }
            },
            {
                "name": "get_profile",
                "description": "Get the current user's ScreenApp profile",
                "parameters": {}
            }
        ]
    }

# Tool execution endpoint
class ToolRequest(BaseModel):
    tool: str
    parameters: dict = {}

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    try:
        if request.tool == "list_teams":
            return await list_teams()
        elif request.tool == "list_recordings":
            return await list_recordings(**request.parameters)
        elif request.tool == "search_recordings":
            return await search_recordings(**request.parameters)
        elif request.tool == "ask_recording":
            return await ask_recording(**request.parameters)
        elif request.tool == "get_profile":
            return await get_profile()
        else:
            raise HTTPException(status_code=404, detail=f"Tool '{request.tool}' not found")
    except Exception as e:
        logger.error(f"Error executing tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API functions
async def list_teams():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{SCREENAPP_API_BASE}/teams",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()

async def list_recordings(team_id: str, limit: int = 20, offset: int = 0):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{SCREENAPP_API_BASE}/teams/{team_id}/recordings",
            headers=get_headers(),
            params={"limit": limit, "offset": offset}
        )
        response.raise_for_status()
        return response.json()

async def search_recordings(team_id: str, query: str, created_after: str = None, created_before: str = None):
    payload = {"query": query}
    if created_after:
        payload["createdAfter"] = created_after
    if created_before:
        payload["createdBefore"] = created_before
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{SCREENAPP_API_BASE}/teams/{team_id}/recordings/search",
            headers=get_headers(),
            json=payload
        )
        response.raise_for_status()
        return response.json()

async def ask_recording(file_id: str, question: str):
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{SCREENAPP_API_BASE}/recordings/{file_id}/ask",
            headers=get_headers(),
            json={"question": question}
        )
        response.raise_for_status()
        return response.json()

async def get_profile():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{SCREENAPP_API_BASE}/profile",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")