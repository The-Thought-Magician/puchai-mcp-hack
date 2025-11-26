# Puch AI MCP Server Deployment Guide

## 🚀 Winning Features

This MCP server is designed to win the Puch AI hackathon by providing **immediate value** through AI-powered lead generation.

### Key Advantages:
- ✅ **MCP Protocol Compliant**: Uses FastMCP framework
- ✅ **Required validate() tool**: Returns "918905981880" as required
- ✅ **AI-Enhanced**: Uses Gemini API for intelligent query optimization
- ✅ **Multiple Search Strategies**: Combines Places API + Web Search
- ✅ **Instant Value**: User gets CSV file URL with real contact data
- ✅ **Production Ready**: Comprehensive error handling and rate limiting

## 🔧 Available Tools

### 1. `validate()` 
- **Required by Puch AI**: Returns phone "918905981880"
- No parameters needed

### 2. `find_leads_basic(industry, location, limit=20)`
- Simple lead generation using standard search
- Example: `find_leads_basic("dentists", "Toronto", 10)`

### 3. `find_leads_smart(requirement, location, limit=20)` ⭐
- **AI-Powered**: Uses Gemini to optimize search strategy
- Natural language requirements
- Example: `find_leads_smart("dentists who accept new patients in downtown Vancouver", "Vancouver", 15)`

### 4. `analyze_market(industry, location)`
- Market analysis and competition insights
- Example: `analyze_market("restaurants", "Miami")`

## 🌐 Deployment on Render

### Prerequisites:
1. Render account
2. Environment variables set as secrets:
   - `SERPER_API_KEY`: Your Serper.dev API key
   - `GEMINI_API_KEY`: Your Google Gemini API key

### Deploy Steps:
1. Connect this GitHub repo to Render
2. Use `render.yaml` configuration (already configured)
3. Set environment variable secrets in Render dashboard
4. Deploy automatically

### Manual Deployment:
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SERPER_API_KEY="your_serper_key"
export GEMINI_API_KEY="your_gemini_key"
export PORT=8080

# Run server
python enhanced_server.py
```

## 🔌 Connect to Puch AI

Once deployed, connect to Puch AI with:

```
/mcp connect https://your-render-url.com 918905981880
```

The server will respond with available tools that users can invoke naturally:

- "Find dentists in Toronto" → Uses `find_leads_smart()` 
- "Get lawyers in Vancouver" → Uses `find_leads_basic()`
- "Analyze restaurant market in Miami" → Uses `analyze_market()`

## 📊 Expected Results

Users get immediate value:
- CSV file URL with real business contacts
- Phone numbers, emails, websites, addresses
- AI-optimized search strategies
- Market analysis insights

## 🏆 Why This Wins

1. **Immediate Value**: No complex workflows - just results
2. **AI-Enhanced**: Gemini makes searches smarter
3. **Production Ready**: Comprehensive error handling, rate limiting
4. **Real Data**: Actual phone numbers and contact information
5. **Simple Integration**: Works with `/mcp connect` command
6. **Multiple Use Cases**: Lead gen + market analysis

## 🔗 API Endpoints

Once deployed, the server provides:
- MCP protocol endpoints (handled by FastMCP)
- Static file serving at `/static/` for CSV downloads
- Health checks and logging

## ⚡ Performance

- **Response Time**: < 5 seconds for most queries
- **Rate Limited**: Respects Serper.dev limits (1.2s between calls)
- **Error Handling**: Graceful fallbacks if APIs fail
- **Scalable**: FastAPI + uvicorn production server

## 🛠️ Technical Stack

- **FastMCP**: MCP protocol compliance
- **FastAPI**: High-performance API framework  
- **Serper.dev**: Google search/places data
- **Gemini AI**: Query optimization
- **httpx**: Async HTTP client
- **CSV Generation**: Clean data export