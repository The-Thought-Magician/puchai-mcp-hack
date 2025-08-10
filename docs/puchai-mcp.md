# Puch AI MCP Integration (Captured Summary)

Captured: 2025-08-10
Source: https://puch.ai/mcp (condensed)

## Overview
Puch AI supports the Model Context Protocol (MCP) so you can connect an external MCP server that exposes tools. Extend the assistant without changing client code.

## Supported (✓)
- Core protocol messages
- Tool definitions and calls
- Authentication: Bearer token & OAuth
- Error handling

## Not Supported (✗)
- Videos extension
- Resources extension
- Prompts extension

## Quick Setup Steps
1) Prepare a public HTTPS MCP endpoint.  
2) In Puch chat, run: `/mcp connect ...`  
3) Verify Puch shows available tools or error details.  

## Command Reference (highlights)
- `/mcp connect <url> <bearer_token>` – Requires a `validate` tool returning phone in `{country_code}{number}` (e.g., 919876543210).
- `/mcp connect <url>` – OAuth flow (if supported).
- `/mcp use <server_id>` – Use a hosted server (up to 5).
- `/mcp remove <server_id>` – Remove a configured server.
- `/mcp list` – List connected servers.
- `/mcp deactivate` – Disconnect all active servers.
- `/mcp diagnostics-level (error|warn|info|debug)` – Set verbosity.
- `/mcp disable|enable <server_id>` – Toggle tool usage for a server.

## Server Requirements
### validate Tool
Accepts bearer token; must return owner phone number as `{country_code}{number}`. Example: `{"phone":"919876543210"}`.

### HTTPS
All endpoints must be HTTPS; HTTP is rejected.

### Production Readiness
Deploy on a public host (e.g., Vercel/Cloudflare/Render/Railway). Ensure availability before sharing.

## Demos & Starter
Starter: https://github.com/TurboML-Inc/mcp-starter

## Help
Discord community plus links for contact/X/Instagram/LinkedIn/Email on the page.

## Additional Links
- Getting Started
- Bearer/OAuth connect
- Hosted servers
- Disconnect / Diagnostics
- Server requirements

## Notes for This Project
- Implement `validate` first to pass Puch auth.  
- Return large artifacts via URL (not inline CSV).  
- Bearer path is enough for MVP; add OAuth later if needed.  

---
Condensed for offline reference. Check the source for updates.
