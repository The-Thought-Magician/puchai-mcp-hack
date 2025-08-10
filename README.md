# Lead Generator MCP Server

AI-powered lead generation server for Puch AI using MCP (Model Context Protocol).

## 🎯 Features

- **Natural Language Processing**: Describe your lead needs in plain English
- **AI-Powered Search**: Uses Gemini 2.5 Flash to generate optimized search queries
- **Google Search Integration**: Leverages Serper.dev API for comprehensive results
- **Automated Contact Extraction**: Finds phone numbers, emails, and websites
- **CSV Export**: Downloadable contact lists ready for CRM import
- **Secure & Temporary**: Files auto-expire after 1 hour for privacy

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.lead_generator .env

# Edit .env and add your API keys:
# - AUTH_TOKEN: Your bearer token for Puch AI
# - MY_NUMBER: Your WhatsApp number (e.g., 919876543210)
# - SERPER_API_KEY: From https://serper.dev/
# - GEMINI_API_KEY: From https://makersuite.google.com/app/apikey
```

### 2. Install Dependencies

```bash
# Install with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

### 3. Run the Server

```bash
# Activate environment
source .venv/bin/activate

# Run server
python lead_generator_server.py
```

Server starts on `http://0.0.0.0:8086`

### 4. Connect to Puch AI

```
/mcp connect https://your-domain.com/mcp your_auth_token_here
```

## 🛠️ Usage Workflow

### 1. Discuss Requirements
```
User: "Find dentists in Toronto"
AI: Extracts requirements → {industry: "dentists", location: "Toronto", ...}
```

### 2. Generate Leads
```
AI: Uses requirements → Calls Serper API → Processes with Gemini
Status: "Processing... 2-5 minutes"
```

### 3. Download CSV
```
AI: Returns download URL → CSV with contacts ready for use
Format: name, phone, email, website, address, rating, source
```

## 🔧 API Keys Required

1. **Serper.dev API Key**
   - Sign up at https://serper.dev/
   - Get 2,500 free searches/month
   - Used for Google Search & Places data

2. **Google Gemini API Key**
   - Get from https://makersuite.google.com/app/apikey
   - Free tier available
   - Used for requirement extraction and query generation

3. **Puch AI Auth Token**
   - Your unique bearer token for MCP connection
   - Set as AUTH_TOKEN in environment

## 📋 MCP Tools

- **`validate`**: Required by Puch AI - returns phone number
- **`discuss`**: Extract lead requirements from natural language
- **`build`**: Generate leads using AI-powered search
- **`create`**: Generate CSV and return download URL

## 🏗️ Architecture

```
User Input → Gemini AI → Serper.dev → Lead Extraction → CSV Export
     ↓           ↓            ↓             ↓            ↓
"Find lawyers" → Query Gen → Google API → Contact Data → Download URL
```

## 🔒 Security Features

- Bearer token authentication
- Temporary file storage (1-hour TTL)
- Automatic cleanup of expired files
- No persistent storage of personal data
- Rate limiting and error handling

## 🚀 Deployment

For production deployment:

1. **Render.com** (Recommended)
   - Connect GitHub repo
   - Set environment variables
   - Auto-deploy with HTTPS

2. **Railway.app**
   - One-click deploy
   - Built-in environment management

3. **Heroku**
   - Traditional PaaS option
   - Requires Procfile

## 📊 Expected Results

- **Speed**: 2-5 minutes for 50+ leads
- **Quality**: 80%+ valid contact information
- **Coverage**: Business name, phone, email, website
- **Sources**: Google Search + Google Places
- **Format**: CRM-ready CSV export

## 🤝 Contributing

This is a hackathon project for Puch AI. Feel free to extend and improve!

---

**Built for Puch AI MCP Hackathon** 🏆