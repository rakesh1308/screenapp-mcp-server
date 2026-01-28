"""
ScreenApp MCP Proxy Server
Proxies requests to the official ScreenApp MCP server at https://mcp.screenapp.io
"""

import asyncio
import json
import os
from typing import Any, Dict, Optional
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

# Official ScreenApp MCP Server
SCREENAPP_MCP_URL = "https://mcp.screenapp.io/mcp"
SCREENAPP_API_KEY = os.getenv("SCREENAPP_API_KEY", "")

app = FastAPI(
    title="ScreenApp MCP Proxy Server",
    description="Proxy to official ScreenApp MCP server for LobeChat compatibility",
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
# Helper Functions
# ============================================================================

def get_headers() -> Dict[str, str]:
    """Get headers for ScreenApp MCP requests"""
    return {
        "Authorization": f"Bearer {SCREENAPP_API_KEY}",
        "Content-Type": "application/json"
    }


# ============================================================================
# FastAPI Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "ScreenApp MCP Proxy Server",
        "version": "1.0.0",
        "protocol": "MCP over SSE",
        "status": "running",
        "upstream": SCREENAPP_MCP_URL,
        "endpoints": {
            "sse": "/sse",
            "health": "/health",
            "message": "/message"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "upstream": SCREENAPP_MCP_URL,
        "api_key_configured": bool(SCREENAPP_API_KEY)
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


@app.get("/sse")
async def sse_handler_get(request: Request):
    """
    Proxy SSE GET requests to official ScreenApp MCP
    """
    
    async def event_stream():
        """Stream events from upstream MCP server"""
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET",
                    f"{SCREENAPP_MCP_URL}/sse",
                    headers=get_headers()
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n"
                        else:
                            yield "\n"
                            
        except httpx.HTTPError as e:
            error_message = {
                "jsonrpc": "2.0",
                "method": "notifications/error",
                "params": {
                    "error": f"Upstream error: {str(e)}"
                }
            }
            yield f"event: error\ndata: {json.dumps(error_message)}\n\n"
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
    Proxy SSE POST requests to official ScreenApp MCP
    """
    try:
        # Get request body
        body = await request.body()
        
        # Forward to upstream MCP
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{SCREENAPP_MCP_URL}/sse",
                headers=get_headers(),
                content=body
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPError as e:
        return JSONResponse(
            status_code=getattr(e.response, 'status_code', 500),
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Upstream error: {str(e)}"
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
        )


@app.post("/message")
async def handle_message(request: Request):
    """
    Proxy message requests to official ScreenApp MCP
    """
    try:
        # Get request body
        body = await request.json()
        
        # Forward to upstream MCP
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{SCREENAPP_MCP_URL}/message",
                headers=get_headers(),
                json=body
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPError as e:
        return JSONResponse(
            status_code=getattr(e.response, 'status_code', 500),
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Upstream error: {str(e)}"
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
        )


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    if not SCREENAPP_API_KEY:
        print("❌ ERROR: SCREENAPP_API_KEY environment variable is not set")
        import sys
        sys.exit(1)
    
    print(f"🚀 Starting ScreenApp MCP Proxy Server on port {port}")
    print(f"📡 Upstream MCP: {SCREENAPP_MCP_URL}")
    print(f"✅ API Key configured")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )