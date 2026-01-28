"""
SSE MCP Server for ScreenApp
Complete implementation for Claude.ai and LobeChat remote MCP integration
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

SCREENAPP_API_BASE_URL = os.getenv("SCREENAPP_API_BASE_URL", "https://api.screenapp.io/v2")
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
            response = await client.delete(url, headers=get_headers())
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()


# ============================================================================
# MCP Tool Handlers
# ============================================================================

async def handle_list_teams(arguments: dict) -> dict:
    """List all teams"""
    result = await make_screenapp_request("GET", "/teams")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_get_team(arguments: dict) -> dict:
    """Get team details"""
    team_id = arguments.get("team_id")
    result = await make_screenapp_request("GET", f"/team/{team_id}")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_list_recordings(arguments: dict) -> dict:
    """List recordings"""
    team_id = arguments.get("team_id")
    limit = arguments.get("limit", 20)
    offset = arguments.get("offset", 0)
    
    params = {"limit": limit, "offset": offset}
    result = await make_screenapp_request("GET", f"/teams/{team_id}/recordings", params=params)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_get_recording(arguments: dict) -> dict:
    """Get recording details"""
    file_id = arguments.get("file_id")
    result = await make_screenapp_request("GET", f"/recordings/{file_id}")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_search_recordings(arguments: dict) -> dict:
    """Search recordings"""
    team_id = arguments.get("team_id")
    query = arguments.get("query")
    
    data = {"query": query}
    if arguments.get("created_after"):
        data["createdAfter"] = arguments["created_after"]
    if arguments.get("created_before"):
        data["createdBefore"] = arguments["created_before"]
    
    result = await make_screenapp_request("POST", f"/teams/{team_id}/recordings/search", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_ask_recording(arguments: dict) -> dict:
    """Ask AI about a recording"""
    file_id = arguments.get("file_id")
    question = arguments.get("question")
    
    data = {"question": question}
    result = await make_screenapp_request("POST", f"/recordings/{file_id}/ask", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_ask_multiple_recordings(arguments: dict) -> dict:
    """Ask AI across multiple recordings"""
    team_id = arguments.get("team_id")
    question = arguments.get("question")
    file_ids = arguments.get("file_ids")
    
    data = {"question": question}
    if file_ids:
        data["fileIds"] = file_ids
    
    result = await make_screenapp_request("POST", f"/teams/{team_id}/recordings/ask", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_ask_multimodal(arguments: dict) -> dict:
    """Multimodal AI analysis"""
    file_id = arguments.get("file_id")
    prompt_text = arguments.get("prompt_text")
    transcript_start = arguments.get("transcript_start", 0)
    transcript_end = arguments.get("transcript_end", 120)
    
    data = {
        "promptText": prompt_text,
        "mediaAnalysisOptions": {
            "transcript": {
                "segments": [{"start": transcript_start, "end": transcript_end}]
            }
        }
    }
    
    result = await make_screenapp_request("POST", f"/files/{file_id}/ask/multimodal", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_get_profile(arguments: dict) -> dict:
    """Get user profile"""
    result = await make_screenapp_request("GET", "/profile")
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_add_file_tag(arguments: dict) -> dict:
    """Add tag to file"""
    file_id = arguments.get("file_id")
    key = arguments.get("key")
    value = arguments.get("value")
    
    data = {"key": key, "value": value}
    result = await make_screenapp_request("POST", f"/files/{file_id}/tag", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_remove_file_tag(arguments: dict) -> dict:
    """Remove tag from file"""
    file_id = arguments.get("file_id")
    key = arguments.get("key")
    
    data = {"key": key}
    result = await make_screenapp_request("DELETE", f"/files/{file_id}/tag", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_register_webhook(arguments: dict) -> dict:
    """Register team webhook"""
    team_id = arguments.get("team_id")
    url = arguments.get("url")
    name = arguments.get("name")
    
    data = {"url": url, "name": name}
    result = await make_screenapp_request("POST", f"/team/{team_id}/integrations/webhook", data=data)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def handle_unregister_webhook(arguments: dict) -> dict:
    """Unregister team webhook"""
    team_id = arguments.get("team_id")
    url = arguments.get("url")
    
    params = {"url": url}
    result = await make_screenapp_request("DELETE", f"/team/{team_id}/integrations/webhook", params=params)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


# ============================================================================
# MCP Tool Definitions
# ============================================================================

TOOLS = [
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
        "description": "List recordings from a specific team with pagination",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"},
                "limit": {"type": "number", "description": "Number of recordings to return (default: 20)", "default": 20},
                "offset": {"type": "number", "description": "Pagination offset (default: 0)", "default": 0}
            },
            "required": ["team_id"]
        }
    },
    {
        "name": "get_recording",
        "description": "Get detailed information about a specific recording including transcript and metadata",
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
        "description": "Search for content within recording transcripts using keywords",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"},
                "query": {"type": "string", "description": "Search query string"},
                "created_after": {"type": "string", "description": "Filter recordings created after this date (ISO 8601)"},
                "created_before": {"type": "string", "description": "Filter recordings created before this date (ISO 8601)"}
            },
            "required": ["team_id", "query"]
        }
    },
    {
        "name": "ask_recording",
        "description": "Ask AI a question about a specific recording using its transcript",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The recording/file ID"},
                "question": {"type": "string", "description": "Question to ask about the recording"}
            },
            "required": ["file_id", "question"]
        }
    },
    {
        "name": "ask_multiple_recordings",
        "description": "Ask AI a question across multiple recordings to find patterns or insights",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"},
                "question": {"type": "string", "description": "Question to ask across recordings"},
                "file_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific file IDs to query"
                }
            },
            "required": ["team_id", "question"]
        }
    },
    {
        "name": "ask_multimodal",
        "description": "Ask a multimodal AI question about a recording using both transcript and video",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The recording/file ID"},
                "prompt_text": {"type": "string", "description": "The question or analysis prompt"},
                "transcript_start": {"type": "number", "description": "Start time for transcript segment in seconds (default: 0)", "default": 0},
                "transcript_end": {"type": "number", "description": "End time for transcript segment in seconds (default: 120)", "default": 120}
            },
            "required": ["file_id", "prompt_text"]
        }
    },
    {
        "name": "get_profile",
        "description": "Get the current user's ScreenApp profile information",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "add_file_tag",
        "description": "Add a tag to a file/recording for organization",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The file ID"},
                "key": {"type": "string", "description": "Tag key (e.g., 'project', 'category')"},
                "value": {"type": "string", "description": "Tag value"}
            },
            "required": ["file_id", "key", "value"]
        }
    },
    {
        "name": "remove_file_tag",
        "description": "Remove a tag from a file/recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The file ID"},
                "key": {"type": "string", "description": "Tag key to remove"}
            },
            "required": ["file_id", "key"]
        }
    },
    {
        "name": "register_webhook",
        "description": "Register a webhook URL to receive real-time notifications for team recording events",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"},
                "url": {"type": "string", "description": "Webhook URL (must be HTTPS)"},
                "name": {"type": "string", "description": "Name/description of the webhook"}
            },
            "required": ["team_id", "url", "name"]
        }
    },
    {
        "name": "unregister_webhook",
        "description": "Unregister/remove a webhook URL for a team",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "The team ID"},
                "url": {"type": "string", "description": "Webhook URL to unregister"}
            },
            "required": ["team_id", "url"]
        }
    }
]

# Tool handler mapping
TOOL_HANDLERS = {
    "list_teams": handle_list_teams,
    "get_team": handle_get_team,
    "list_recordings": handle_list_recordings,
    "get_recording": handle_get_recording,
    "search_recordings": handle_search_recordings,
    "ask_recording": handle_ask_recording,
    "ask_multiple_recordings": handle_ask_multiple_recordings,
    "ask_multimodal": handle_ask_multimodal,
    "get_profile": handle_get_profile,
    "add_file_tag": handle_add_file_tag,
    "remove_file_tag": handle_remove_file_tag,
    "register_webhook": handle_register_webhook,
    "unregister_webhook": handle_unregister_webhook,
}


# ============================================================================
# FastAPI Endpoints
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
    """
    Handle MCP messages via POST
    Alternative to SSE for tools that prefer request/response
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON"}
        )
    
    request_id = body.get("id", 1)
    method = body.get("method", "")
    
    # Handle initialize
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
    
    # Handle tools/list
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }
    
    # Handle tools/call
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
    """
    SSE endpoint for MCP protocol - GET method
    Returns a stream of events
    """
    
    async def event_stream():
        """Generate SSE events"""
        
        try:
            # Send initial server info
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
            
            # Keep connection alive with heartbeat
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
    """
    SSE endpoint for MCP protocol - POST method
    Handles method calls and returns JSON-RPC responses
    """
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
    
    # Handle initialize
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
    
    # Handle tools/list
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }
    
    # Handle tools/call
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
    
    # Unknown method
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