# Deployment Guide - Lead Generator MCP Server

## 🚀 Quick Deploy Options

### Option 1: Render.com (Recommended)

1. **Fork this repo** to your GitHub account
2. **Connect Render** to your GitHub account
3. **Create new Web Service** in Render:
   - Repository: `your-username/puchai-mcp-hack`
   - Branch: `main`
   - Root Directory: `lead-generator-mcp`
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python server.py`

4. **Set Environment Variables** in Render:
   ```
   AUTH_TOKEN=your_secure_bearer_token_here
   MY_NUMBER=919998881729
   SERPER_API_KEY=your_serper_dev_api_key
   GEMINI_API_KEY=your_google_gemini_api_key
   CSV_TTL_SECONDS=3600
   MAX_CONCURRENCY=4
   BASE_URL=https://your-app-name.onrender.com
   ```

5. **Deploy** and get your HTTPS URL

### Option 2: Railway.app

1. **Connect Railway** to your GitHub repo
2. **Deploy** from `lead-generator-mcp` directory
3. **Set environment variables** (same as above)
4. **Get deployment URL**

### Option 3: Heroku

1. **Install Heroku CLI**
2. **Create app**: `heroku create your-app-name`
3. **Set config vars**: `heroku config:set AUTH_TOKEN=...`
4. **Deploy**: `git push heroku main`

## 🔑 Required API Keys

### 1. Serper.dev API Key
- Sign up: https://serper.dev/
- Free tier: 2,500 searches/month
- Copy API key to `SERPER_API_KEY`

### 2. Google Gemini API Key
- Get key: https://makersuite.google.com/app/apikey
- Free tier available
- Copy to `GEMINI_API_KEY`

### 3. Auth Token
- Generate a secure random string
- Use for Puch AI authentication
- Set as `AUTH_TOKEN`

## 📱 Connect to Puch AI

Once deployed:

```
/mcp connect https://your-app-name.onrender.com your_auth_token_here
```

## 🧪 Test Your Deployment

```bash
curl -X POST https://your-app-name.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_auth_token" \
  -d '{"method": "tools/list"}'
```

Should return available tools: `validate`, `discuss`, `build`, `create`

## 🔍 Debugging

- **Check logs** in your deployment platform
- **Verify environment variables** are set correctly
- **Test API keys** individually if needed
- **Ensure HTTPS** is working (required by Puch AI)

## 📊 Usage Flow

1. **User**: "Find dentists in Toronto"
2. **discuss**: AI extracts requirements
3. **build**: Generates leads (2-5 minutes)  
4. **create**: Returns CSV with contacts

Ready for the hackathon! 🏆