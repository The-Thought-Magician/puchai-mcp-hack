#!/usr/bin/env node

const http = require('http');
const url = require('url');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

require('dotenv').config();

const PORT = process.env.PORT || 8080;

// In-memory job store for demonstration
const jobs = new Map();
let jobIdCounter = 1;

// MCP JSON-RPC handler
function handleMCPRequest(req, res) {
  let body = '';
  
  req.on('data', chunk => {
    body += chunk.toString();
  });
  
  req.on('end', () => {
    try {
      const request = JSON.parse(body);
      const response = processMCPRequest(request);
      
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(response));
    } catch (error) {
      console.error('MCP request error:', error);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        jsonrpc: '2.0',
        error: { code: -32603, message: 'Internal error' },
        id: null
      }));
    }
  });
}

// Process MCP JSON-RPC requests
function processMCPRequest(request) {
  const { method, params, id } = request;
  
  switch (method) {
    case 'initialize':
      return {
        jsonrpc: '2.0',
        result: {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: {}
          },
          serverInfo: {
            name: 'Lead Generator MCP Server',
            version: '1.0.0'
          }
        },
        id
      };
      
    case 'notifications/initialized':
      return {
        jsonrpc: '2.0',
        result: {},
        id
      };
      
    case 'tools/list':
      return {
        jsonrpc: '2.0',
        result: {
          tools: [
            {
              name: 'validate',
              description: 'Returns server owner phone number',
              inputSchema: {
                type: 'object',
                properties: {},
                required: []
              }
            },
            {
              name: 'search_leads',
              description: 'Start an async lead search job',
              inputSchema: {
                type: 'object',
                properties: {
                  industry: { type: 'string', description: 'Industry to search for' },
                  location: { type: 'string', description: 'Location to search in' },
                  limit: { type: 'number', description: 'Maximum number of leads', default: 10 }
                },
                required: ['industry', 'location']
              }
            },
            {
              name: 'get_status',
              description: 'Get status of a lead search job',
              inputSchema: {
                type: 'object',
                properties: {
                  job_id: { type: 'string', description: 'Job ID to check status for' }
                },
                required: ['job_id']
              }
            }
          ]
        },
        id
      };
      
    case 'tools/call':
      return handleToolCall(params, id);
      
    default:
      return {
        jsonrpc: '2.0',
        error: { code: -32601, message: 'Method not found' },
        id
      };
  }
}

// Handle tool calls
function handleToolCall(params, id) {
  const { name, arguments: args } = params;
  
  switch (name) {
    case 'validate':
      // Return server owner's phone number (no parameters needed)
      return {
        jsonrpc: '2.0',
        result: {
          content: [
            {
              type: 'text', 
              text: '918905981880'
            }
          ]
        },
        id
      };
      
    case 'search_leads':
      const jobId = `job_${jobIdCounter++}`;
      const job = {
        id: jobId,
        status: 'running',
        industry: args.industry,
        location: args.location,
        limit: args.limit || 10,
        started_at: new Date().toISOString()
      };
      
      jobs.set(jobId, job);
      
      // Start async lead search
      startLeadSearch(jobId, args.industry, args.location, args.limit || 10);
      
      return {
        jsonrpc: '2.0',
        result: {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ job_id: jobId, status: 'started' })
            }
          ]
        },
        id
      };
      
    case 'get_status':
      const jobData = jobs.get(args.job_id);
      if (!jobData) {
        return {
          jsonrpc: '2.0',
          error: { code: -32602, message: 'Job not found' },
          id
        };
      }
      
      const statusResponse = {
        job_id: args.job_id,
        status: jobData.status,
        started_at: jobData.started_at
      };
      
      if (jobData.status === 'completed' && jobData.filename) {
        statusResponse.download_url = `/download/${jobData.filename}`;
      }
      
      if (jobData.error) {
        statusResponse.error = jobData.error;
      }
      
      return {
        jsonrpc: '2.0',
        result: {
          content: [
            {
              type: 'text',
              text: JSON.stringify(statusResponse)
            }
          ]
        },
        id
      };
      
    default:
      return {
        jsonrpc: '2.0',
        error: { code: -32602, message: 'Unknown tool' },
        id
      };
  }
}

// Start async lead search
function startLeadSearch(jobId, industry, location, limit) {
  const outputFilename = `leads_${jobId}_${Date.now()}.csv`;
  const outputPath = path.join(__dirname, 'static', outputFilename);
  
  // Ensure static directory exists
  const staticDir = path.join(__dirname, 'static');
  if (!fs.existsSync(staticDir)) {
    fs.mkdirSync(staticDir, { recursive: true });
  }
  
  const child = spawn('node', [
    'lead_searcher.js',
    '--industry', industry,
    '--location', location,
    '--output', outputPath,
    '--limit', limit.toString()
  ]);
  
  let stderr = '';
  
  child.stderr.on('data', (data) => {
    stderr += data.toString();
  });
  
  child.on('close', (code) => {
    const job = jobs.get(jobId);
    if (code === 0) {
      job.status = 'completed';
      job.filename = outputFilename;
      job.completed_at = new Date().toISOString();
    } else {
      job.status = 'failed';
      job.error = stderr || 'Lead search process failed';
      job.completed_at = new Date().toISOString();
    }
    jobs.set(jobId, job);
  });
}

// Serve static files from /download/ endpoint
function serveStaticFile(req, res, filename) {
  const filePath = path.join(__dirname, 'static', filename);
  
  // Security check: ensure filename doesn't contain path traversal
  if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    res.end('Invalid filename');
    return;
  }
  
  fs.access(filePath, fs.constants.F_OK, (err) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('File not found');
      return;
    }
    
    res.writeHead(200, { 
      'Content-Type': 'text/csv',
      'Content-Disposition': `attachment; filename="${filename}"`
    });
    
    const stream = fs.createReadStream(filePath);
    stream.pipe(res);
  });
}

// Main HTTP server
const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  
  // Add CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  if (pathname === '/mcp' && req.method === 'POST') {
    handleMCPRequest(req, res);
  } else if (pathname.startsWith('/download/')) {
    const filename = pathname.substring('/download/'.length);
    serveStaticFile(req, res, filename);
  } else if (pathname === '/' || pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      status: 'ok', 
      service: 'MCP Lead Generation Server',
      endpoints: {
        mcp: '/mcp',
        download: '/download/{filename}',
        health: '/health'
      }
    }));
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not Found');
  }
});

server.listen(PORT, () => {
  console.log(`MCP Server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`MCP endpoint: http://localhost:${PORT}/mcp`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    process.exit(0);
  });
});