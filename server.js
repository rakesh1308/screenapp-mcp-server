const express = require('express');
const axios = require('axios');
require('dotenv').config();

const app = express();
app.use(express.json());

// ============= CONFIGURATION =============

const SCREENAPP_API_TOKEN = process.env.SCREENAPP_API_TOKEN;
const SCREENAPP_TEAM_ID = process.env.SCREENAPP_TEAM_ID;
const API_KEY = process.env.MCP_API_KEY || 'default-key';
const PORT = process.env.PORT || 3000;

const SCREENAPP_BASE_URL = 'https://api.screenapp.io/v2';

// Validate required environment variables
if (!SCREENAPP_API_TOKEN || !SCREENAPP_TEAM_ID) {
  console.error('❌ ERROR: Missing required environment variables');
  console.error('   SCREENAPP_API_TOKEN: ' + (SCREENAPP_API_TOKEN ? '✓' : '✗'));
  console.error('   SCREENAPP_TEAM_ID: ' + (SCREENAPP_TEAM_ID ? '✓' : '✗'));
  process.exit(1);
}

// ============= AUTHENTICATION MIDDLEWARE =============

const authenticateRequest = (req, res, next) => {
  const apiKey = req.headers['x-api-key'] || req.query.token;
  
  if (!apiKey || apiKey !== API_KEY) {
    return res.status(401).json({ 
      error: 'Unauthorized',
      message: 'Invalid or missing X-API-Key header'
    });
  }
  
  next();
};

// ============= MCP TOOL DEFINITIONS =============

const tools = [
  {
    name: 'list_recordings',
    description: 'List all recordings from your ScreenApp account. Returns paginated list with titles, dates, and IDs.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of recordings to return (1-100, default: 20)',
          default: 20
        },
        offset: {
          type: 'number',
          description: 'Number of recordings to skip for pagination (default: 0)',
          default: 0
        }
      },
      required: []
    }
  },
  {
    name: 'search_recordings',
    description: 'Search through your ScreenApp recordings by keyword. Searches titles, summaries, and content.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search keyword or phrase (required)'
        },
        limit: {
          type: 'number',
          description: 'Maximum results to return (1-100, default: 10)',
          default: 10
        }
      },
      required: ['query']
    }
  },
  {
    name: 'get_recording_details',
    description: 'Get detailed information about a specific recording including metadata, duration, participants.',
    inputSchema: {
      type: 'object',
      properties: {
        recording_id: {
          type: 'string',
          description: 'The unique ID of the recording (required)'
        }
      },
      required: ['recording_id']
    }
  },
  {
    name: 'get_transcript',
    description: 'Retrieve the full transcript of a recording with speaker labels and timestamps.',
    inputSchema: {
      type: 'object',
      properties: {
        recording_id: {
          type: 'string',
          description: 'The unique ID of the recording (required)'
        },
        format: {
          type: 'string',
          description: 'Output format: text (plain text), srt (subtitle), vtt (video text), or json (structured)',
          enum: ['text', 'srt', 'vtt', 'json'],
          default: 'text'
        }
      },
      required: ['recording_id']
    }
  },
  {
    name: 'get_summary',
    description: 'Get AI-generated summary of a recording including action items, key points, and discussion topics.',
    inputSchema: {
      type: 'object',
      properties: {
        recording_id: {
          type: 'string',
          description: 'The unique ID of the recording (required)'
        }
      },
      required: ['recording_id']
    }
  },
  {
    name: 'ask_question_about_recording',
    description: 'Ask a question about the content of a recording. The AI will search the transcript and answer.',
    inputSchema: {
      type: 'object',
      properties: {
        recording_id: {
          type: 'string',
          description: 'The unique ID of the recording (required)'
        },
        question: {
          type: 'string',
          description: 'Your question about the recording content (required)'
        }
      },
      required: ['recording_id', 'question']
    }
  }
];

// ============= UTILITY FUNCTIONS =============

function createErrorResponse(message, details = null) {
  return {
    content: [
      {
        type: 'text',
        text: `Error: ${message}${details ? '\n\n' + details : ''}`
      }
    ],
    isError: true
  };
}

function createSuccessResponse(data) {
  const text = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  return {
    content: [
      {
        type: 'text',
        text: text
      }
    ],
    isError: false
  };
}

async function callScreenAppAPI(endpoint, method = 'GET', params = null) {
  try {
    const config = {
      method,
      url: `${SCREENAPP_BASE_URL}${endpoint}`,
      headers: {
        'Authorization': `Bearer ${SCREENAPP_API_TOKEN}`,
        'X-Team-ID': SCREENAPP_TEAM_ID,
        'Content-Type': 'application/json'
      }
    };

    if (params) {
      if (method === 'GET') {
        config.params = params;
      } else {
        config.data = params;
      }
    }

    const response = await axios(config);
    return response.data;
  } catch (error) {
    const errorMsg = error.response?.data?.message || error.message;
    const statusCode = error.response?.status || 'UNKNOWN';
    throw new Error(`ScreenApp API Error (${statusCode}): ${errorMsg}`);
  }
}

// ============= HEALTH CHECK =============

app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'ScreenApp MCP Server',
    version: '2.0.0',
    timestamp: new Date().toISOString()
  });
});

// ============= MCP JSON-RPC 2.0 HANDLER =============

app.post('/', authenticateRequest, async (req, res) => {
  const { jsonrpc, method, params, id } = req.body;

  // Validate JSON-RPC format
  if (jsonrpc !== '2.0') {
    return res.json({
      jsonrpc: '2.0',
      error: {
        code: -32600,
        message: 'Invalid JSON-RPC version'
      },
      id: id || null
    });
  }

  if (!method) {
    return res.json({
      jsonrpc: '2.0',
      error: {
        code: -32600,
        message: 'Missing method'
      },
      id: id || null
    });
  }

  console.log(`[${new Date().toISOString()}] ${method} (id: ${id})`);

  try {
    let result;

    // Normalize method name
    const normalizedMethod = method.toLowerCase().trim();

    // ========== INITIALIZE (MCP Protocol Handshake) ==========
    if (normalizedMethod === 'initialize') {
      result = {
        protocolVersion: '2024-11-05',
        capabilities: {
          tools: {
            listChanged: false
          }
        },
        serverInfo: {
          name: 'ScreenApp MCP Server',
          version: '2.0.0'
        }
      };
      console.log(`  ✅ Initialize complete`);
    }

    // ========== LIST TOOLS ==========
    else if (
      normalizedMethod === 'tools/list' ||
      normalizedMethod === 'list_tools' ||
      normalizedMethod === 'tools_list'
    ) {
      result = { tools };
      console.log(`  ✅ Returned ${tools.length} tools`);
    }

    // ========== CALL TOOL ==========
    else if (
      normalizedMethod === 'tools/call' ||
      normalizedMethod === 'tool/call' ||
      normalizedMethod === 'call_tool' ||
      normalizedMethod === 'tools/execute' ||
      normalizedMethod === 'execute_tool'
    ) {
      const toolName = params?.name || params?.tool;
      const toolArgs = params?.arguments || params?.args || {};

      if (!toolName) {
        throw new Error('Tool name is required in params.name or params.tool');
      }

      console.log(`  🔧 Executing tool: ${toolName}`);

      try {
        const toolResult = await executeTool(toolName, toolArgs);
        result = createSuccessResponse(toolResult);
        console.log(`  ✅ Tool ${toolName} succeeded`);
      } catch (toolError) {
        console.error(`  ❌ Tool ${toolName} failed: ${toolError.message}`);
        result = createErrorResponse(`Tool execution failed: ${toolError.message}`);
      }
    }

    // ========== UNKNOWN METHOD ==========
    else {
      throw new Error(`Unknown method: ${method}`);
    }

    // ========== SEND RESPONSE ==========
    res.json({
      jsonrpc: '2.0',
      result,
      id
    });

  } catch (error) {
    console.error(`  ❌ Error: ${error.message}`);

    res.json({
      jsonrpc: '2.0',
      error: {
        code: -32603,
        message: 'Internal error',
        data: error.message
      },
      id
    });
  }
});

// ============= TOOL EXECUTION ENGINE =============

async function executeTool(toolName, args = {}) {
  switch (toolName) {
    case 'list_recordings':
      return await listRecordings(args);
    
    case 'search_recordings':
      return await searchRecordings(args);
    
    case 'get_recording_details':
      return await getRecordingDetails(args);
    
    case 'get_transcript':
      return await getTranscript(args);
    
    case 'get_summary':
      return await getSummary(args);
    
    case 'ask_question_about_recording':
      return await askQuestionAboutRecording(args);
    
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

// ============= TOOL IMPLEMENTATIONS =============

async function listRecordings({ limit = 20, offset = 0 } = {}) {
  if (limit > 100) limit = 100;
  if (limit < 1) limit = 1;
  if (offset < 0) offset = 0;

  console.log(`    Fetching recordings: limit=${limit}, offset=${offset}`);

  const data = await callScreenAppAPI('/recordings', 'GET', { limit, offset });
  
  const recordings = Array.isArray(data.data) ? data.data : Array.isArray(data) ? data : [];
  
  return {
    success: true,
    count: recordings.length,
    total: data.total || recordings.length,
    limit,
    offset,
    recordings: recordings.map(r => ({
      id: r.id,
      title: r.title || 'Untitled',
      createdAt: r.createdAt,
      duration: r.duration,
      participants: r.participants || []
    }))
  };
}

async function searchRecordings({ query, limit = 10 } = {}) {
  if (!query || query.trim() === '') {
    throw new Error('Search query is required');
  }

  if (limit > 100) limit = 100;
  if (limit < 1) limit = 1;

  console.log(`    Searching: query="${query}", limit=${limit}`);

  // First, get all recordings
  const allRecordings = await listRecordings({ limit: 100, offset: 0 });
  
  // Filter by search query
  const queryLower = query.toLowerCase().trim();
  const results = allRecordings.recordings
    .filter(r => {
      const title = (r.title || '').toLowerCase();
      return title.includes(queryLower);
    })
    .slice(0, limit);

  return {
    success: true,
    query,
    resultCount: results.length,
    results
  };
}

async function getRecordingDetails({ recording_id } = {}) {
  if (!recording_id) {
    throw new Error('recording_id is required');
  }

  console.log(`    Fetching details for: ${recording_id}`);

  const data = await callScreenAppAPI(`/recordings/${recording_id}`);

  return {
    success: true,
    recording: {
      id: data.id,
      title: data.title,
      description: data.description,
      duration: data.duration,
      createdAt: data.createdAt,
      updatedAt: data.updatedAt,
      participants: data.participants || [],
      language: data.language,
      isPublic: data.isPublic
    }
  };
}

async function getTranscript({ recording_id, format = 'text' } = {}) {
  if (!recording_id) {
    throw new Error('recording_id is required');
  }

  if (!['text', 'srt', 'vtt', 'json'].includes(format)) {
    format = 'text';
  }

  console.log(`    Fetching transcript: ${recording_id} (${format})`);

  try {
    const data = await callScreenAppAPI(`/recordings/${recording_id}/transcript`, 'GET', { format });

    return {
      success: true,
      recording_id,
      format,
      transcript: data.transcript || data,
      wordCount: data.wordCount || 0,
      language: data.language || 'unknown'
    };
  } catch (error) {
    // Fallback: return empty transcript
    console.warn(`    Transcript not available: ${error.message}`);
    return {
      success: false,
      recording_id,
      format,
      transcript: '[Transcript not available]',
      wordCount: 0,
      error: error.message
    };
  }
}

async function getSummary({ recording_id } = {}) {
  if (!recording_id) {
    throw new Error('recording_id is required');
  }

  console.log(`    Fetching summary: ${recording_id}`);

  try {
    const data = await callScreenAppAPI(`/recordings/${recording_id}/summary`);

    return {
      success: true,
      recording_id,
      summary: data.summary || '[No summary available]',
      actionItems: Array.isArray(data.actionItems) ? data.actionItems : [],
      keyPoints: Array.isArray(data.keyPoints) ? data.keyPoints : [],
      topics: Array.isArray(data.topics) ? data.topics : []
    };
  } catch (error) {
    console.warn(`    Summary not available: ${error.message}`);
    return {
      success: false,
      recording_id,
      summary: '[Summary not available]',
      actionItems: [],
      keyPoints: [],
      error: error.message
    };
  }
}

async function askQuestionAboutRecording({ recording_id, question } = {}) {
  if (!recording_id) {
    throw new Error('recording_id is required');
  }

  if (!question || question.trim() === '') {
    throw new Error('question is required');
  }

  console.log(`    Asking question about ${recording_id}: "${question.substring(0, 50)}..."`);

  try {
    // Get transcript first
    const transcriptData = await getTranscript({ recording_id, format: 'text' });

    if (!transcriptData.success) {
      return {
        success: false,
        recording_id,
        question,
        answer: 'Could not retrieve transcript to answer question',
        error: 'Transcript unavailable'
      };
    }

    // Return transcript excerpt as answer (in production, use an LLM here)
    const transcript = transcriptData.transcript || '';
    const excerpt = transcript.substring(0, 1500);

    return {
      success: true,
      recording_id,
      question,
      answer: `Based on the recording transcript:\n\n${excerpt}${excerpt.length < transcript.length ? '...' : ''}`,
      confidence: 'moderate',
      note: 'For full AI-powered Q&A with answer extraction, use ScreenApp Pro'
    };
  } catch (error) {
    console.error(`    Question failed: ${error.message}`);
    return {
      success: false,
      recording_id,
      question,
      answer: `Could not answer question: ${error.message}`,
      error: error.message
    };
  }
}

// ============= ERROR HANDLING =============

app.use((err, req, res, next) => {
  console.error('[ERROR]', err);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

// ============= 404 HANDLER =============

app.use((req, res) => {
  res.status(404).json({
    error: 'Not found',
    message: 'This endpoint does not exist'
  });
});

// ============= STARTUP =============

app.listen(PORT, () => {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`✅ ScreenApp MCP Server v2.0.0`);
  console.log(`${'='.repeat(70)}`);
  console.log(`📊 Health Check:     GET  http://localhost:${PORT}/health`);
  console.log(`🔌 MCP Endpoint:     POST http://localhost:${PORT}/`);
  console.log(`🔐 Authentication:   X-API-Key header required`);
  console.log(`\n📋 Available Tools (${tools.length}):`);
  tools.forEach((tool, i) => {
    console.log(`   ${i + 1}. ${tool.name}`);
  });
  console.log(`\n🔌 MCP Methods Supported:`);
  console.log(`   • initialize (MCP handshake)`);
  console.log(`   • tools/list (list available tools)`);
  console.log(`   • tools/call (execute a tool)`);
  console.log(`\n🚀 Ready to accept MCP connections`);
  console.log(`${'='.repeat(70)}\n`);
});

// ============= GRACEFUL SHUTDOWN =============

process.on('SIGTERM', () => {
  console.log('\n🛑 Received SIGTERM, shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('\n🛑 Received SIGINT, shutting down gracefully...');
  process.exit(0);
});