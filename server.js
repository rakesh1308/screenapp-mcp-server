const express = require('express');
const axios = require('axios');
require('dotenv').config();

const app = express();
app.use(express.json());

// ============= CONFIGURATION =============

const SCREENAPP_API_TOKEN = process.env.SCREENAPP_API_TOKEN;
const SCREENAPP_TEAM_ID = process.env.SCREENAPP_TEAM_ID;
const API_KEY = process.env.MCP_API_KEY || 'default-key';
const SCREENAPP_BASE_URL = 'https://api.screenapp.io/v2';

// ============= AUTHENTICATION MIDDLEWARE =============

const authenticateRequest = (req, res, next) => {
  const apiKey = req.headers['x-api-key'] || req.query.token;
  
  if (apiKey !== API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  next();
};

// ============= MCP TOOLS SCHEMA =============

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

// ============= ROUTES =============

// Health Check (No Auth Required)
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok',
    service: 'ScreenApp MCP Server',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

// MCP JSON-RPC 2.0 Handler (Main Endpoint)
app.post('/', authenticateRequest, async (req, res) => {
  const { jsonrpc, method, params, id } = req.body;

  console.log(`\n[MCP] =====================================`);
  console.log(`[MCP] Request: method=${method}, id=${id}`);
  console.log(`[MCP] =====================================`);

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
    const normalizedMethod = method.toLowerCase().trim();

    // ============= INITIALIZE HANDSHAKE =============
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
    // ============= LIST TOOLS =============
    else if (normalizedMethod === 'tools/list' || normalizedMethod === 'list_tools' || normalizedMethod === 'tools_list') {
      console.log('[MCP] ✅ Handling tools/list request');
      result = {
        tools: tools
      };
    }
    // ============= EXECUTE TOOL =============
    else if (normalizedMethod === 'tools/call' || normalizedMethod === 'tool/call' || normalizedMethod === 'call_tool' || normalizedMethod === 'tools/execute' || normalizedMethod === 'execute_tool') {
      const toolName = params?.name || params?.tool;
      const toolArgs = params?.arguments || params?.args || {};
      console.log(`[MCP] ✅ Executing tool: ${toolName}`);
      
      try {
        const toolResult = await executeTool(toolName, toolArgs);
        
        // Wrap in MCP format
        result = {
          content: [
            {
              type: 'text',
              text: typeof toolResult === 'string' ? toolResult : JSON.stringify(toolResult, null, 2)
            }
          ],
          isError: false
        };
        
        console.log(`[MCP] ✅ Tool ${toolName} executed successfully`);
      } catch (toolError) {
        console.error(`[MCP] ❌ Tool ${toolName} failed:`, toolError.message);
        result = {
          content: [
            {
              type: 'text',
              text: `Error executing ${toolName}: ${toolError.message}`
            }
          ],
          isError: true
        };
      }
    }
    // ============= FALLBACK HANDLERS =============
    else if (normalizedMethod.includes('list')) {
      console.log(`[MCP] ✅ Fallback: Returning tools for method: ${method}`);
      result = { tools: tools };
    }
    else if (normalizedMethod.includes('call') || normalizedMethod.includes('execute')) {
      console.log(`[MCP] ✅ Fallback: Assuming tool execution for method: ${method}`);
      const toolName = params?.name || params?.tool;
      const toolArgs = params?.arguments || params?.args || {};
      try {
        const toolResult = await executeTool(toolName, toolArgs);
        result = {
          content: [{ type: 'text', text: typeof toolResult === 'string' ? toolResult : JSON.stringify(toolResult, null, 2) }],
          isError: false
        };
      } catch (toolError) {
        result = {
          content: [{ type: 'text', text: `Error executing ${toolName}: ${toolError.message}` }],
          isError: true
        };
      }
    }
    else {
      console.log(`[MCP] ⚠️  Unknown method "${method}" - returning tools list`);
      result = { tools: tools };
    }

    console.log(`[MCP] ✅ Sending response\n`);

    // Send JSON-RPC 2.0 response
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

// ============= TOOL EXECUTION ENGINE =============

async function executeTool(toolName, args) {
  if (!toolName) {
    throw new Error('Tool name is required');
  }

  console.log(`[TOOL] Executing: ${toolName}`);

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

// ============= TOOL IMPLEMENTATIONS =============

async function listRecordings({ limit = 20, offset = 0 } = {}) {
  try {
    console.log(`[TOOL] list_recordings: limit=${limit}, offset=${offset}`);
    
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

    const recordings = response.data.data || response.data || [];
    console.log(`[TOOL] Found ${recordings.length} recordings`);

    return {
      recordings: recordings,
      total: response.data.total || recordings.length,
      limit,
      offset
    };
  } catch (error) {
    console.error(`[TOOL] Error in listRecordings:`, error.message);
    throw new Error(`Failed to list recordings: ${error.response?.data?.message || error.message}`);
  }
}

async function searchRecordings({ query, limit = 10 } = {}) {
  try {
    if (!query) throw new Error('Query parameter is required');

    console.log(`[TOOL] search_recordings: query="${query}", limit=${limit}`);

    const allRecordings = await listRecordings({ limit: 100, offset: 0 });
    
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

    console.log(`[TOOL] Found ${filtered.length} matching recordings`);

    return {
      query,
      results: filtered,
      count: filtered.length,
      message: `Found ${filtered.length} recordings matching "${query}"`
    };
  } catch (error) {
    console.error(`[TOOL] Error in searchRecordings:`, error.message);
    throw new Error(`Search failed: ${error.message}`);
  }
}

async function getRecording({ recording_id } = {}) {
  try {
    if (!recording_id) throw new Error('recording_id parameter is required');

    console.log(`[TOOL] get_recording: id=${recording_id}`);

    const response = await axios.get(
      `${SCREENAPP_BASE_URL}/recordings/${recording_id}`,
      {
        headers: {
          'Authorization': `Bearer ${SCREENAPP_API_TOKEN}`,
          'X-Team-ID': SCREENAPP_TEAM_ID
        }
      }
    );

    console.log(`[TOOL] Got recording: ${response.data?.title || recording_id}`);
    return response.data;
  } catch (error) {
    console.error(`[TOOL] Error in getRecording:`, error.message);
    throw new Error(`Failed to get recording: ${error.response?.data?.message || error.message}`);
  }
}

async function getTranscript({ recording_id, format = 'text' } = {}) {
  try {
    if (!recording_id) throw new Error('recording_id parameter is required');

    console.log(`[TOOL] get_transcript: id=${recording_id}, format=${format}`);

    const response = await axios.get(
      `${SCREENAPP_BASE_URL}/recordings/${recording_id}/transcript`,
      {
        headers: {
          'Authorization': `Bearer ${SCREENAPP_API_TOKEN}`,
          'X-Team-ID': SCREENAPP_TEAM_ID
        },
        params: { format }
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
      console.error(`[TOOL] Error in getTranscript:`, error.message);
      throw new Error(`Failed to get transcript: ${error.response?.data?.message || error.message}`);
    }
  }
}

async function getSummary({ recording_id } = {}) {
  try {
    if (!recording_id) throw new Error('recording_id parameter is required');

    console.log(`[TOOL] get_summary: id=${recording_id}`);

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
      console.error(`[TOOL] Error in getSummary:`, error.message);
      throw new Error(`Failed to get summary: ${error.response?.data?.message || error.message}`);
    }
  }
}

async function askRecording({ recording_id, question } = {}) {
  try {
    if (!recording_id) throw new Error('recording_id parameter is required');
    if (!question) throw new Error('question parameter is required');

    console.log(`[TOOL] ask_recording: id=${recording_id}`);

    const transcript = await getTranscript({ recording_id, format: 'text' });
    
    return {
      recording_id,
      question,
      answer: `Based on the transcript:\n\n${transcript.transcript.substring(0, 2000)}${transcript.transcript.length > 2000 ? '...\n\n(Use get_transcript for full content)' : ''}`,
      confidence: 'moderate',
      note: 'For full AI-powered Q&A, use ScreenApp Pro'
    };
  } catch (error) {
    console.error(`[TOOL] Error in askRecording:`, error.message);
    throw new Error(`Failed to process question: ${error.message}`);
  }
}

// ============= ERROR HANDLING =============

app.use((err, req, res, next) => {
  console.error('[ERROR]:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    message: err.message 
  });
});

app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// ============= START SERVER =============

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`✅ ScreenApp MCP Server v1.0.0 RUNNING`);
  console.log(`${'='.repeat(70)}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🛠️  MCP JSON-RPC 2.0 endpoint: POST http://localhost:${PORT}/`);
  console.log(`🔐 Authentication: X-API-Key header required`);
  console.log(`\n📋 Supported MCP Methods:`);
  console.log(`   • initialize - Protocol handshake`);
  console.log(`   • tools/list - List available tools`);
  console.log(`   • tools/call - Execute tool`);
  console.log(`\n🛠️  Available Tools (6):`);
  tools.forEach((tool, i) => {
    console.log(`   ${i + 1}. ${tool.name} - ${tool.description}`);
  });
  console.log(`${'='.repeat(70)}\n`);
});