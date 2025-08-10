#!/usr/bin/env python3
"""
Puch AI MCP Server - Lead Generation Tool
A winning MCP server for the Puch AI hackathon that provides immediate value.
"""

import asyncio
import os
from datetime import datetime
from typing import Optional, Dict, Any

from fastmcp import FastMCP
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from lead_generator import LeadGenerator, LeadGenerationError

# Initialize FastMCP server
mcp = FastMCP("Puch AI Lead Generator")

# Initialize lead generator
lead_gen = LeadGenerator()

@mcp.tool()
def validate() -> Dict[str, str]:
    """
    Validation tool required by Puch AI MCP protocol.
    Returns the phone number in the format required by Puch AI.
    
    Returns:
        dict: Contains phone number in {country_code}{number} format
    """
    return {
        "phone": "918905981880"
    }

@mcp.tool()
async def find_leads(
    industry: str,
    location: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Find business leads for a specific industry and location.
    
    This tool searches for businesses and generates a CSV file with contact information
    including names, phone numbers, emails, and source URLs.
    
    Args:
        industry: The type of business (e.g., "dentists", "lawyers", "restaurants")
        location: The geographic location (e.g., "Toronto", "New York", "London UK")
        limit: Maximum number of leads to find (default: 20, max: 50)
        
    Returns:
        dict: Contains CSV file URL, summary statistics, and metadata
    """
    try:
        # Validate inputs
        if not industry or not industry.strip():
            raise ValueError("Industry parameter is required and cannot be empty")
        
        if not location or not location.strip():
            raise ValueError("Location parameter is required and cannot be empty")
        
        # Clamp limit to reasonable bounds
        limit = max(1, min(limit, 50))
        
        # Generate leads
        result = await lead_gen.generate_leads(
            industry=industry.strip(),
            location=location.strip(),
            limit=limit
        )
        
        return {
            "success": True,
            "csv_url": result["csv_url"],
            "total_leads": result["total_leads"],
            "industry": industry,
            "location": location,
            "generated_at": datetime.now().isoformat(),
            "message": f"Generated {result['total_leads']} leads for {industry} in {location}"
        }
        
    except LeadGenerationError as e:
        return {
            "success": False,
            "error": str(e),
            "industry": industry,
            "location": location,
            "message": f"Failed to generate leads: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "industry": industry,
            "location": location,
            "message": "An unexpected error occurred during lead generation"
        }

def create_static_dir():
    """Create static directory if it doesn't exist."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    return static_dir

if __name__ == "__main__":
    # Ensure static directory exists
    static_dir = create_static_dir()
    
    # Add static file serving to FastMCP's FastAPI app
    app = mcp.get_fastapi_app()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    
    # Run the server
    mcp.run(port=port, host="0.0.0.0")