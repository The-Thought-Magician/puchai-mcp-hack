#!/usr/bin/env python3
"""
Enhanced Puch AI MCP Server - AI-Powered Lead Generation Tool
A winning MCP server that uses Gemini AI to create intelligent lead generation strategies.
"""

import asyncio
import os
from datetime import datetime
from typing import Optional, Dict, Any

from fastmcp import FastMCP
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from enhanced_lead_generator import EnhancedLeadGenerator, LeadGenerationError

# Initialize FastMCP server
mcp = FastMCP("Puch AI Enhanced Lead Generator")

# Initialize enhanced lead generator
enhanced_lead_gen = EnhancedLeadGenerator()

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
async def find_leads_basic(
    industry: str,
    location: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Find business leads using basic search strategy.
    
    Args:
        industry: The type of business (e.g., "dentists", "lawyers", "restaurants")
        location: The geographic location (e.g., "Toronto", "New York", "London UK")
        limit: Maximum number of leads to find (default: 20, max: 50)
        
    Returns:
        dict: Contains CSV file URL, summary statistics, and metadata
    """
    try:
        # Use basic lead generation from parent class
        result = await enhanced_lead_gen.generate_leads(
            industry=industry.strip(),
            location=location.strip(),
            limit=max(1, min(limit, 50))
        )
        
        return {
            "success": True,
            "csv_url": result["csv_url"],
            "total_leads": result["total_leads"],
            "industry": industry,
            "location": location,
            "generated_at": datetime.now().isoformat(),
            "message": f"Generated {result['total_leads']} leads for {industry} in {location}",
            "strategy": "basic"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "industry": industry,
            "location": location,
            "message": f"Basic lead generation failed: {str(e)}",
            "strategy": "basic"
        }

@mcp.tool()
async def find_leads_smart(
    requirement: str,
    location: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Find business leads using AI-powered intelligent search strategy.
    
    This tool uses Gemini AI to analyze your natural language requirement and create
    the most effective search strategy using multiple Serper.dev API endpoints.
    
    Examples:
    - "I need dentists who accept new patients in downtown Toronto"
    - "Find immigration lawyers with good reviews in Vancouver"
    - "Local restaurants that do catering in Chicago"
    - "Technology startups looking for funding in Austin"
    
    Args:
        requirement: Natural language description of what you're looking for
        location: The geographic location (e.g., "Toronto", "New York", "London UK")
        limit: Maximum number of leads to find (default: 20, max: 50)
        
    Returns:
        dict: Contains CSV file URL, AI strategy used, and detailed metadata
    """
    try:
        # Validate inputs
        if not requirement or not requirement.strip():
            raise ValueError("Requirement parameter is required and cannot be empty")
        
        if not location or not location.strip():
            raise ValueError("Location parameter is required and cannot be empty")
        
        # Clamp limit to reasonable bounds
        limit = max(1, min(limit, 50))
        
        # Generate leads using AI-enhanced strategy
        result = await enhanced_lead_gen.generate_enhanced_leads(
            user_requirement=requirement.strip(),
            location=location.strip(),
            limit=limit
        )
        
        return {
            "success": True,
            "csv_url": result["csv_url"],
            "total_leads": result["total_leads"],
            "requirement": requirement,
            "location": location,
            "generated_at": datetime.now().isoformat(),
            "ai_strategy": result["strategy_used"],
            "ai_reasoning": result["reasoning"],
            "queries_executed": result["queries_executed"],
            "strategy_results": result["strategy_results"],
            "duplicates_removed": result["duplicates_removed"],
            "message": f"AI generated {result['total_leads']} leads using {result['strategy_used']} strategy",
            "strategy": "ai_enhanced"
        }
        
    except LeadGenerationError as e:
        return {
            "success": False,
            "error": str(e),
            "requirement": requirement,
            "location": location,
            "message": f"AI lead generation failed: {str(e)}",
            "strategy": "ai_enhanced"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "requirement": requirement,
            "location": location,
            "message": "An unexpected error occurred during AI lead generation",
            "strategy": "ai_enhanced"
        }

@mcp.tool()
async def analyze_market(
    industry: str,
    location: str
) -> Dict[str, Any]:
    """
    Analyze market opportunities for a specific industry and location.
    
    This tool provides insights about market saturation, competition, and opportunities
    in a specific geographic area for a given industry.
    
    Args:
        industry: The type of business to analyze
        location: The geographic location to analyze
        
    Returns:
        dict: Market analysis including competitor count, opportunities, and insights
    """
    try:
        # Use enhanced search to get market data
        market_requirement = f"competitors analysis {industry} market research {location}"
        
        # Get sample data for market analysis
        result = await enhanced_lead_gen.generate_enhanced_leads(
            user_requirement=market_requirement,
            location=location,
            limit=30  # Get more data for analysis
        )
        
        # Analyze the results
        total_competitors = result["total_leads"]
        
        # Simple market analysis based on competitor count
        if total_competitors < 10:
            market_status = "Underserved Market"
            opportunity_level = "High"
            recommendation = "Great opportunity for new businesses"
        elif total_competitors < 25:
            market_status = "Moderate Competition"
            opportunity_level = "Medium"
            recommendation = "Room for differentiation and growth"
        else:
            market_status = "Saturated Market"
            opportunity_level = "Low"
            recommendation = "Focus on unique value proposition"
        
        return {
            "success": True,
            "industry": industry,
            "location": location,
            "competitor_count": total_competitors,
            "market_status": market_status,
            "opportunity_level": opportunity_level,
            "recommendation": recommendation,
            "data_source_url": result["csv_url"],
            "analysis_date": datetime.now().isoformat(),
            "message": f"Found {total_competitors} competitors in {industry} market in {location}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "industry": industry,
            "location": location,
            "message": f"Market analysis failed: {str(e)}"
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