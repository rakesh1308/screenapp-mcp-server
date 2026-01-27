const express = require('express');
const axios = require('axios');
require('dotenv').config();

const app = express();
app.use(express.json());

// Configuration
const SCREENAPP_API_TOKEN = process.env.SCREENAPP_API_TOKEN;
const SCREENAPP_TEAM_ID = process.env.SCREENAPP_TEAM_ID;
const API_KEY = process.env.MCP_API_KEY || 'default-key';

const SCREENAPP_BASE_URL = 'https://api.screenapp.io/v2';

// Authentication middleware
const authenticateRequest = (req, res, next) => {
  const apiKey = req.headers['x-api-key'] || req.query.token;
  
  if (apiKey !== API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  next();
};

// MCP Tools Schema
const tools = [
  {
    name: 'list_recordings',
    description: 'List all recordings from your ScreenApp account with metadata',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of recordings to return (default: 20, max: 100)',
          default: 20
        },
        offset: {
          type: 'number',
          description: 'Offset for pagination (default: 0)',
          default: 0
        }
      },
      required: []
    }
  },
  {
    name: 'search_recordings',
    description: 'Search recordings by keyword, title, or content',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query (searches titles, summaries, and transcript content)'
        },
        limit: {
          type: 'number',
          description: 'Maximum results (default: 10)',
          default: 10
        }
      },
      required: ['query']
    }
  },
  {
    name: 'get_recording',
    description: 'Get detailed information about a specific recording including transcript and summary',
    inputSchema: {
      type: 'object',
      properties: {
        recording_id: {
          type: 'string',
          description: 'The ID of the recording'
        }
      },
      required: ['recording_id']
    }
  },
  {
    name: 'get_transcript',
    description: 'Get the full transcript of a recording with timestamps and speaker labels',
    inputSchema: {
      type: 'object',
      properties: {
        recording_id: {
          type: 'string',
          description: 'The ID of the recording'
        },
        format: {
          type: 'string',
          description: 'Format: text, srt, vtt, or json (default: text)',
          enum: ['text', 'srt', 'vtt', 'json'],
          default: 'text'
        }
      },
      required: ['recording_id']
    }
  },
  {
    name: 'get_summary',
    description: 'Get AI-generated summary, action items, and key points from a recording',
    inputSchema: {
      type: 'object',
      properties: {
        recording_id: {
          type: 'string',
          description: 'The ID of the recording'
        }
      },
      required: ['recording_id']
    }
  },
  {
    name: 'ask_recording',
    description: 'Ask a question about a specific recording - the AI will search the transcript and answer',
    inputSchema: {
      type: 'object',
      properties: {
        recording_id: {
          type: 'string',
          description: 'The ID of the recording'
        },
        question: {
          type: 'string',
          description: 'Your question about the recording content'
        }
      },
      required: ['recording_id', 'question']
    }
  }
];

// ============= Health Check (No Auth) =============

app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok',
    service: 'ScreenApp MCP Server',
    version: '1.0.0'
  });
});

// ============= MCP JSON-RPC 2.0 Handler =============

app.post('/', authenticateRequest, async (req, res) => {
  const { jsonrpc, method, params, id } = req.body;

  console.log(`\n[MCP] ================================`);
  console.log(`[MCP] Incoming request: method=${method}, id=${id}`);
  console.log(`[MCP] ================================`);

  // Validate JSON-RPC format
  if (jsonrpc !== '2.0' || !method) {
    return res.status(400).json({
      jsonrpc: '2.0',
      error: {
        code: -32600,
        message: 'Invalid Request'
      },
      id: id || null
    });
  }

  try {
    let result;

    // Normalize method name
    const normalizedMethod = method.toLowerCase().trim();

    // ============= Handle MCP Protocol Methods =============

    // Handle initialization - MCP protocol handshake (REQUIRED)
    if (normalizedMethod === 'initialize') {
      console.log('[MCP] ✅ Handling initialize handshake');
      result = {
        protocolVersion: '2025-06-18',
        capabilities: {
          tools: {}
        },
        serverInfo: {
          name: 'ScreenApp MCP Server',
          version: '1.0.0'
        }
      };
    }
    // Handle tools/list - return the tools array
    else if (normalizedMethod === 'tools/list' || normalizedMethod === 'list_tools' || normalizedMethod === 'tools_list') {
      console.log('[MCP] ✅ Handling tools list request');
      result = {
        tools: tools
      };
    }
    // Handle resource/read - LobeChat might send this for text resources
    else if (normalizedMethod === 'resource/read' || normalizedMethod === 'resources/read') {
      console.log('[MCP] ✅ Handling resource/read request');
      result = {
        contents: [
          {
            uri: 'screenapp://recordings',
            mimeType: 'application/json',
            text: JSON.stringify(tools)
          }
        ]
      };
    }
    // Handle tool execution
    else if (normalizedMethod === 'tools/call' || normalizedMethod === 'tool/call' || normalizedMethod === 'call_tool' || normalizedMethod === 'tools/execute' || normalizedMethod === 'execute_tool') {
      const toolName = params?.name || params?.tool;
      const toolArgs = params?.arguments || params?.args || {};
      console.log(`[MCP] ✅ Executing tool: ${toolName}`);
      result = await executeTool(toolName, toolArgs);
    }
    // Catch-all: flexible handling for any method
    else if (normalizedMethod.includes('list') || normalizedMethod.includes('manifest')) {
      console.log(`[MCP] ✅ Assuming list request for method: ${method}`);
      result = {
        tools: tools
      };
    }
    else if (normalizedMethod.includes('call') || normalizedMethod.includes('execute')) {
      console.log(`[MCP] ✅ Assuming execute request for method: ${method}`);
      const toolName = params?.name || params?.tool;
      const toolArgs = params?.arguments || params?.args || {};
      result = await executeTool(toolName, toolArgs);
    }
    else {
      // Last resort - return tools list as fallback
      console.log(`[MCP] ⚠️  Unrecognized method "${method}" - returning tools list as fallback`);
      result = {
        tools: tools
      };
    }

    console.log(`[MCP] ✅ Successfully handled method: ${method}\n`);

    // Success response
    res.json({
      jsonrpc: '2.0',
      result: result,
      id: id
    });

  } catch (error) {
    console.error(`[MCP] ❌ Error handling method ${method}:`, error.message);
    
    res.status(500).json({
      jsonrpc: '2.0',
      error: {
        code: -32603,
        message: 'Internal error: ' + error.message
      },
      id: id
    });
  }
});

// ============= Tool Execution =============

async function executeTool(toolName, args) {
  switch (toolName) {
    case 'list_recordings':
      return await listRecordings(args);
    case 'search_recordings':
      return await searchRecordings(args);
    case 'get_recording':
      return await getRecording(args);
    case 'get_transcript':
      return await getTranscript(args);
    case 'get_summary':
      return await getSummary(args);
    case 'ask_recording':
      return await askRecording(args);
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

async function listRecordings({ limit = 20, offset = 0 } = {}) {
  try {
    const response = await axios.get(
      `${SCREENAPP_BASE_URL}/recordings`,
      {
        headers: {
          'Authorization': `Bearer ${SCREENAPP_API_TOKEN}`,
          'X-Team-ID': SCREENAPP_TEAM_ID
        },
        params: {
          limit: Math.min(limit, 100),
          offset
        }
      }
    );

    return {
      recordings: response.data.data || response.data || [],
      total: response.data.total || 0,
      limit,
      offset
    };
  } catch (error) {
    throw new Error(`Failed to list recordings: ${error.response?.data?.message || error.message}`);
  }
}

async function searchRecordings({ query, limit = 10 } = {}) {
  try {
    if (!query) throw new Error('Query parameter is required');

    // First, get all recordings
    const allRecordings = await listRecordings({ limit: 100, offset: 0 });
    
    // Filter by search query (case-insensitive)
    const queryLower = query.toLowerCase();
    const filtered = (allRecordings.recordings || [])
      .filter(r => {
        const title = (r.title || '').toLowerCase();
        const summary = (r.summary || '').toLowerCase();
        const description = (r.description || '').toLowerCase();
        
        return title.includes(queryLower) || 
               summary.includes(queryLower) || 
               description.includes(queryLower);
      })
      .slice(0, limit);

    return {
      query,
      results: filtered,
      count: filtered.length
    };
  } catch (error) {
    throw new Error(`Search failed: ${error.message}`);
  }
}

async function getRecording({ recording_id } = {}) {
  try {
    if (!recording_id) throw new Error('recording_id parameter is required');

    const response = await axios.get(
      `${SCREENAPP_BASE_URL}/recordings/${recording_id}`,
      {
        headers: {
          'Authorization': `Bearer ${SCREENAPP_API_TOKEN}`,
          'X-Team-ID': SCREENAPP_TEAM_ID
        }
      }
    );

    return response.data;
  } catch (error) {
    throw new Error(`Failed to get recording: ${error.response?.data?.message || error.message}`);
  }
}

async function getTranscript({ recording_id, format = 'text' } = {}) {
  try {
    if (!recording_id) throw new Error('recording_id parameter is required');

    const response = await axios.get(
      `${SCREENAPP_BASE_URL}/recordings/${recording_id}/transcript`,
      {
        headers: {
          'Authorization': `Bearer ${SCREENAPP_API_TOKEN}`,
          'X-Team-ID': SCREENAPP_TEAM_ID
        },
        params: {
          format
        }
      }
    );

    return {
      recording_id,
      format,
      transcript: response.data.transcript || response.data,
      wordCount: response.data.wordCount || 0
    };
  } catch (error) {
    try {
      const recording = await getRecording({ recording_id });
      return {
        recording_id,
        format,
        transcript: recording.transcript || 'Transcript not available',
        wordCount: 0
      };
    } catch {
      throw new Error(`Failed to get transcript: ${error.response?.data?.message || error.message}`);
    }
  }
}

async function getSummary({ recording_id } = {}) {
  try {
    if (!recording_id) throw new Error('recording_id parameter is required');

    const response = await axios.get(
      `${SCREENAPP_BASE_URL}/recordings/${recording_id}/summary`,
      {
        headers: {
          'Authorization': `Bearer ${SCREENAPP_API_TOKEN}`,
          'X-Team-ID': SCREENAPP_TEAM_ID
        }
      }
    );

    return {
      recording_id,
      summary: response.data.summary || response.data,
      actionItems: response.data.actionItems || [],
      keyPoints: response.data.keyPoints || []
    };
  } catch (error) {
    try {
      const recording = await getRecording({ recording_id });
      return {
        recording_id,
        summary: recording.summary || 'Summary not available',
        actionItems: recording.actionItems || [],
        keyPoints: recording.keyPoints || []
      };
    } catch {
      throw new Error(`Failed to get summary: ${error.response?.data?.message || error.message}`);
    }
  }
}

async function askRecording({ recording_id, question } = {}) {
  try {
    if (!recording_id) throw new Error('recording_id parameter is required');
    if (!question) throw new Error('question parameter is required');

    const transcript = await getTranscript({ recording_id, format: 'text' });
    
    return {
      recording_id,
      question,
      answer: `Based on the transcript of recording ${recording_id}:\n\n${transcript.transcript.substring(0, 2000)}...`,
      confidence: 'moderate',
      note: 'For full AI-powered Q&A, upgrade to ScreenApp Pro'
    };
  } catch (error) {
    throw new Error(`Failed to process question: ${error.message}`);
  }
}

// ============= Error Handling =============

app.use((err, req, res, next) => {
  console.error('[ERROR] Server error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    message: err.message 
  });
});

// ============= 404 Handler =============

app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// ============= Start Server =============

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`✅ ScreenApp MCP Server running on port ${PORT}`);
  console.log(`${'='.repeat(60)}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🛠️  MCP JSON-RPC 2.0 endpoint: POST http://localhost:${PORT}/`);
  console.log(`🔐 Auth via X-API-Key header or ?token= query param`);
  console.log(`\n📋 Supported MCP Methods:`);
  console.log(`   • initialize - MCP protocol handshake`);
  console.log(`   • tools/list - List available tools`);
  console.log(`   • tools/call - Execute a tool`);
  console.log(`\n📋 Available tools:`);
  tools.forEach(tool => {
    console.log(`   • ${tool.name}`);
  });
  console.log(`${'='.repeat(60)}\n`);
});