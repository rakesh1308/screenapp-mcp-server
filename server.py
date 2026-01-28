"""
SSE MCP Server for ScreenApp
Using the actual working ScreenApp API endpoints
"""

import asyncio
import json
import os
from typing import Any, Dict, Optional, List
from datetime import datetime
import httpx
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

# ============================================================================
# Configuration  
# ============================================================================

# Use the ACTUAL ScreenApp API URL (not v2)
SCREENAPP_API_BASE_URL = os.getenv("SCREENAPP_API_BASE_URL", "https://api.screenapp.io")
SCREENAPP_API_KEY = os.getenv("SCREENAPP_API_KEY", "")

app = FastAPI(
    title="ScreenApp MCP Server",
    description="MCP server for managing ScreenApp recordings and AI analysis",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ScreenApp API Helper Functions
# ============================================================================

def get_headers() -> Dict[str, str]:
    """Get headers for ScreenApp API requests"""
    return {
        "Authorization": f"Bearer {SCREENAPP_API_KEY}",
        "Content-Type": "application/json"
    }


async def make_screenapp_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make HTTP request to ScreenApp API"""
    url = f"{SCREENAPP_API_BASE_URL}{endpoint}"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        if method.upper() == "GET":
            response = await client.get(url, headers=get_headers(), params=params)
        elif method.upper() == "POST":
            response = await client.post(url, headers=get_headers(), json=data)
        elif method.upper() == "PUT":
            response = await client.put(url, headers=get_headers(), json=data)
        elif method.upper() == "DELETE":
            response = await client.delete(url, headers=get_headers(), json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()


# ============================================================================
# MCP Tool Handlers
# ============================================================================

async def handle_get_profile(arguments: dict) -> dict:
    """Get user profile"""
    result = await make_screenapp_request("GET", "/user/v1/profile")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_list_teams(arguments: dict) -> dict:
    """List all teams"""
    result = await make_screenapp_request("GET", "/team/v1")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_get_team(arguments: dict) -> dict:
    """Get team details"""
    team_id = arguments.get("team_id")
    result = await make_screenapp_request("GET", f"/team/v1/{team_id}")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_list_recordings(arguments: dict) -> dict:
    """List recordings"""
    team_id = arguments.get("team_id")
    limit = arguments.get("limit", 20)
    offset = arguments.get("offset", 0)
    
    params = {"limit": limit, "offset": offset}
    result = await make_screenapp_request("GET", f"/file/v1/list/{team_id}", params=params)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_get_recording(arguments: dict) -> dict:
    """Get recording details"""
    file_id = arguments.get("file_id")
    result = await make_screenapp_request("GET", f"/file/v1/{file_id}")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_search_recordings(arguments: dict) -> dict:
    """Search recordings"""
    team_id = arguments.get("team_id")
    query = arguments.get("query")
    created_after = arguments.get("created_after")
    created_before = arguments.get("created_before")
    owner_ids = arguments.get("owner_ids")
    parent_ids = arguments.get("parent_ids")
    
    data = {"query": query}
    if created_after:
        data["createdAfter"] = created_after
    if created_before:
        data["createdBefore"] = created_before
    if owner_ids:
        data["ownerIds"] = owner_ids
    if parent_ids:
        data["parentIds"] = parent_ids
    
    result = await make_screenapp_request("POST", f"/file/v1/search/{team_id}", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_ask_recording(arguments: dict) -> dict:
    """Ask AI about a recording"""
    file_id = arguments.get("file_id")
    question = arguments.get("question")
    
    data = {"question": question}
    result = await make_screenapp_request("POST", f"/file/v1/{file_id}/ask", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_ask_multiple_recordings(arguments: dict) -> dict:
    """Ask AI across multiple recordings"""
    team_id = arguments.get("team_id")
    question = arguments.get("question")
    file_ids = arguments.get("file_ids")
    
    data = {"question": question}
    if file_ids:
        data["fileIds"] = file_ids
    
    result = await make_screenapp_request("POST", f"/file/v1/ask/{team_id}", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_get_usage_stats(arguments: dict) -> dict:
    """Get usage statistics"""
    result = await make_screenapp_request("GET", "/user/v1/usage")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


# ============================================================================
# MCP Tool Definitions
# ============================================================================

TOOLS = [
    {
        "name": "get_profile",
        "description": "Get the current user's ScreenApp profile information",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "list_teams",
        "description": "List all teams the user belongs to in ScreenApp",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_team",
        "description": "Get detailed information about a specific team",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"}
            },
            "required": ["team_id"]
        }
    },
    {
        "name": "list_recordings",
        "description": "List recordings from a specific team with pagination. Returns video files with transcripts, summaries, and metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"},
                "limit": {"type": "number", "description": "Number of recordings to return (default: 20, max: 100)", "default": 20},
                "offset": {"type": "number", "description": "Pagination offset (default: 0)", "default": 0}
            },
            "required": ["team_id"]
        }
    },
    {
        "name": "get_recording",
        "description": "Get detailed information about a specific recording including full transcript, speakers, duration, and video URLs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The recording/file ID"}
            },
            "required": ["file_id"]
        }
    },
    {
        "name": "search_recordings",
        "description": "Search for content within recording transcripts using keywords. Returns matching recordings with context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"},
                "query": {"type": "string", "description": "Search query string"},
                "created_after": {"type": "string", "description": "Filter recordings created after this date (ISO 8601 format)"},
                "created_before": {"type": "string", "description": "Filter recordings created before this date (ISO 8601 format)"},
                "owner_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of owner IDs to filter by"
                },
                "parent_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of parent folder IDs to filter by"
                }
            },
            "required": ["team_id", "query"]
        }
    },
    {
        "name": "ask_recording",
        "description": "Ask AI a question about a specific recording using its transcript. Great for extracting key points, action items, or specific information.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The recording/file ID"},
                "question": {"type": "string", "description": "Question to ask about the recording (e.g., 'What were the main action items?', 'Summarize the key points')"}
            },
            "required": ["file_id", "question"]
        }
    },
    {
        "name": "ask_multiple_recordings",
        "description": "Ask AI a question across multiple recordings to find patterns, common themes, or synthesize information from multiple sources.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"},
                "question": {"type": "string", "description": "Question to ask across recordings"},
                "file_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific file IDs to query. If omitted, searches across all team recordings."
                }
            },
            "required": ["team_id", "question"]
        }
    },
    {
        "name": "get_usage_stats",
        "description": "Get usage statistics and billing information for the account including storage used, minutes processed, and API calls.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handler mapping
TOOL_HANDLERS = {
    "get_profile": handle_get_profile,
    "list_teams": handle_list_teams,
    "get_team": handle_get_team,
    "list_recordings": handle_list_recordings,
    "get_recording": handle_get_recording,
    "search_recordings": handle_search_recordings,
    "ask_recording": handle_ask_recording,
    "ask_multiple_recordings": handle_ask_multiple_recordings,
    "get_usage_stats": handle_get_usage_stats,
}


# ============================================================================
# FastAPI Endpoints (same as Dify MCP)
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "ScreenApp MCP Server",
        "version": "1.0.0",
        "protocol": "MCP over SSE",
        "status": "running",
        "endpoints": {
            "sse": "/sse",
            "health": "/health",
            "message": "/message"
        },
        "tools": len(TOOLS),
        "tool_names": [tool["name"] for tool in TOOLS]
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "screenapp_url": SCREENAPP_API_BASE_URL,
        "api_key_configured": bool(SCREENAPP_API_KEY),
        "tools_available": len(TOOLS)
    }


@app.options("/sse")
async def sse_options():
    """Handle CORS preflight for SSE endpoint"""
    return JSONResponse(
        content={"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )


@app.post("/message")
async def handle_message(request: Request):
    """Handle MCP messages via POST"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON"}
        )
    
    request_id = body.get("id", 1)
    method = body.get("method", "")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "screenapp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }
    
    elif method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name in TOOL_HANDLERS:
            try:
                result = await TOOL_HANDLERS[tool_name](arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32600,
            "message": "Invalid request"
        }
    }


@app.get("/sse")
async def sse_handler_get(request: Request):
    """SSE endpoint - GET method"""
    
    async def event_stream():
        try:
            init_message = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "screenapp",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
            yield f"event: message\ndata: {json.dumps(init_message)}\n\n"
            
            while True:
                await asyncio.sleep(15)
                yield ": heartbeat\n\n"
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            error_message = {
                "jsonrpc": "2.0",
                "method": "notifications/error",
                "params": {
                    "error": str(e)
                }
            }
            yield f"event: error\ndata: {json.dumps(error_message)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "text/event-stream"
        }
    )


@app.post("/sse")
async def sse_handler_post(request: Request):
    """SSE endpoint - POST method"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
        )
    
    request_id = body.get("id", 1)
    method = body.get("method", "")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "screenapp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }
    
    elif method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name in TOOL_HANDLERS:
            try:
                result = await TOOL_HANDLERS[tool_name](arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting ScreenApp MCP Server on port {port}")
    print(f"📡 API URL: {SCREENAPP_API_BASE_URL}")
    print(f"✅ API Key configured: {bool(SCREENAPP_API_KEY)}")
    print(f"🛠️  Tools available: {len(TOOLS)}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )