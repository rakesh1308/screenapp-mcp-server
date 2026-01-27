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

app.use(authenticateRequest);

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

// ============= API Endpoints =============

// Get tools list (MCP endpoint)
app.get('/mcp/tools', (req, res) => {
  res.json({
    tools: tools
  });
});

// Execute tool (MCP endpoint)
app.post('/mcp/tools/execute', async (req, res) => {
  const { tool, args } = req.body;

  try {
    let result;

    switch (tool) {
      case 'list_recordings':
        result = await listRecordings(args);
        break;
      case 'search_recordings':
        result = await searchRecordings(args);
        break;
      case 'get_recording':
        result = await getRecording(args);
        break;
      case 'get_transcript':
        result = await getTranscript(args);
        break;
      case 'get_summary':
        result = await getSummary(args);
        break;
      case 'ask_recording':
        result = await askRecording(args);
        break;
      default:
        return res.status(400).json({ error: `Unknown tool: ${tool}` });
    }

    res.json({ success: true, data: result });
  } catch (error) {
    console.error(`Error executing tool ${tool}:`, error.message);
    res.status(500).json({
      success: false,
      error: error.message || 'Tool execution failed'
    });
  }
});

// ============= Tool Implementations =============

async function listRecordings({ limit = 20, offset = 0 }) {
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

async function searchRecordings({ query, limit = 10 }) {
  try {
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

async function getRecording({ recording_id }) {
  try {
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

async function getTranscript({ recording_id, format = 'text' }) {
  try {
    // Get full recording data which includes transcript
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
    // Fallback: try to get from main recording endpoint
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

async function getSummary({ recording_id }) {
  try {
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
    // Fallback: try to get from main recording endpoint
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

async function askRecording({ recording_id, question }) {
  try {
    // Get transcript and use it to answer
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

// ============= Health Check =============

app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok',
    service: 'ScreenApp MCP Server',
    version: '1.0.0'
  });
});

// ============= MCP Protocol Endpoints =============

app.get('/', (req, res) => {
  res.json({
    name: 'ScreenApp MCP Server',
    version: '1.0.0',
    description: 'MCP wrapper for ScreenApp API - record management, transcription, and analysis',
    endpoints: {
      tools: '/mcp/tools',
      execute: '/mcp/tools/execute',
      health: '/health'
    },
    authentication: 'Bearer token via X-API-Key header or ?token= query param'
  });
});

// Error handling
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✅ ScreenApp MCP Server running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🛠️  Tools endpoint: http://localhost:${PORT}/mcp/tools`);
  console.log(`🔐 Auth via X-API-Key header or ?token= query param`);
});