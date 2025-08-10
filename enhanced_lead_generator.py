"""
Enhanced Lead Generator using Gemini API for intelligent query processing
Integrates Gemini AI to create more sophisticated Serper.dev API calls based on user requirements.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any

import httpx

from lead_generator import LeadGenerator, LeadGenerationError


class EnhancedLeadGenerator(LeadGenerator):
    """Enhanced lead generator using Gemini API for intelligent query processing."""
    
    def __init__(self):
        super().__init__()
        
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise LeadGenerationError("GEMINI_API_KEY environment variable is required")
        
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    async def _enhance_query_with_gemini(
        self, 
        user_requirement: str,
        location: str
    ) -> Dict[str, Any]:
        """
        Use Gemini API to analyze user requirement and generate optimized search strategy.
        
        Args:
            user_requirement: User's natural language requirement
            location: Geographic location
            
        Returns:
            Dictionary with enhanced search parameters and strategy
        """
        
        system_prompt = """You are an expert at lead generation using the Serper.dev API. Your job is to analyze user requirements and create the most effective search strategy.

SERPER.DEV API ENDPOINTS:
1. /search - Web search with organic results
2. /places - Google Places/Maps search for businesses
3. /images - Image search
4. /news - News search
5. /shopping - Shopping search
6. /jobs - Job listings

PARAMETERS:
- q: search query (required)
- gl: country code (us, ca, gb, au, etc.)
- hl: language (en, es, fr, etc.)
- num: number of results (1-100)
- type: result type (search, places, images, etc.)

LEAD GENERATION STRATEGY:
1. Use /places for local businesses (restaurants, dentists, lawyers, etc.)
2. Use /search for broader B2B leads or specific industries
3. Combine multiple queries for comprehensive coverage
4. Use location-specific terms and industry keywords
5. Include contact-finding terms like "phone", "email", "contact"

Given a user requirement, create a JSON response with:
{
  "primary_strategy": "places" or "search",
  "queries": [
    {
      "endpoint": "places" or "search",
      "q": "optimized search query",
      "gl": "country_code",
      "hl": "en",
      "num": number_of_results,
      "priority": 1-5
    }
  ],
  "reasoning": "explanation of strategy",
  "expected_lead_types": ["business type 1", "business type 2"]
}

Analyze this requirement and provide the optimal search strategy."""

        user_prompt = f"""
USER REQUIREMENT: {user_requirement}
LOCATION: {location}

Create the most effective lead generation strategy for this requirement. Focus on finding businesses with contact information (phone numbers, emails, websites).

Return only valid JSON with no additional text or formatting.
"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.gemini_base_url}/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
                
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": system_prompt + "\n\n" + user_prompt}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topP": 0.1,
                        "maxOutputTokens": 1000
                    }
                }
                
                response = await client.post(url, json=payload)
                
                if response.status_code != 200:
                    # Fallback to basic strategy
                    return self._create_fallback_strategy(user_requirement, location)
                
                result = response.json()
                
                # Extract content from Gemini response
                if "candidates" in result and result["candidates"]:
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Try to parse JSON from the response
                    try:
                        # Clean up the content (remove markdown formatting if present)
                        cleaned_content = content.strip()
                        if cleaned_content.startswith("```json"):
                            cleaned_content = cleaned_content.split("```json")[1].split("```")[0]
                        elif cleaned_content.startswith("```"):
                            cleaned_content = cleaned_content.split("```")[1].split("```")[0]
                        
                        strategy = json.loads(cleaned_content)
                        return self._validate_strategy(strategy)
                        
                    except json.JSONDecodeError:
                        # Fallback if JSON parsing fails
                        return self._create_fallback_strategy(user_requirement, location)
                
                return self._create_fallback_strategy(user_requirement, location)
                
        except Exception as e:
            print(f"Gemini API error: {str(e)}")
            return self._create_fallback_strategy(user_requirement, location)
    
    def _create_fallback_strategy(self, requirement: str, location: str) -> Dict[str, Any]:
        """Create a fallback strategy when Gemini API is unavailable."""
        
        # Simple keyword analysis for fallback
        requirement_lower = requirement.lower()
        
        # Determine if this is a local business search
        local_keywords = [
            "restaurant", "dentist", "lawyer", "doctor", "salon", "gym", "shop",
            "store", "cafe", "bar", "hotel", "repair", "service", "clinic"
        ]
        
        is_local = any(keyword in requirement_lower for keyword in local_keywords)
        
        if is_local:
            return {
                "primary_strategy": "places",
                "queries": [
                    {
                        "endpoint": "places",
                        "q": f"{requirement} {location}",
                        "gl": self._get_country_code(location),
                        "hl": "en",
                        "num": 20,
                        "priority": 1
                    }
                ],
                "reasoning": "Local business search using Places API",
                "expected_lead_types": [requirement]
            }
        else:
            return {
                "primary_strategy": "search",
                "queries": [
                    {
                        "endpoint": "search",
                        "q": f"{requirement} {location} phone email contact",
                        "gl": self._get_country_code(location),
                        "hl": "en",
                        "num": 10,
                        "priority": 1
                    },
                    {
                        "endpoint": "places",
                        "q": f"{requirement} {location}",
                        "gl": self._get_country_code(location),
                        "hl": "en",
                        "num": 10,
                        "priority": 2
                    }
                ],
                "reasoning": "Combined search strategy for broader lead generation",
                "expected_lead_types": [requirement]
            }
    
    def _validate_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize the strategy from Gemini."""
        
        # Ensure required fields
        if "queries" not in strategy:
            strategy["queries"] = []
        
        if "primary_strategy" not in strategy:
            strategy["primary_strategy"] = "places"
        
        # Validate each query
        valid_queries = []
        for query in strategy.get("queries", []):
            if isinstance(query, dict) and "q" in query and "endpoint" in query:
                # Ensure required fields with defaults
                validated_query = {
                    "endpoint": query.get("endpoint", "places"),
                    "q": query["q"],
                    "gl": query.get("gl", "us"),
                    "hl": query.get("hl", "en"),
                    "num": min(max(query.get("num", 10), 1), 50),  # Clamp between 1-50
                    "priority": query.get("priority", 1)
                }
                
                # Validate endpoint
                valid_endpoints = ["search", "places", "images", "news", "shopping", "jobs"]
                if validated_query["endpoint"] not in valid_endpoints:
                    validated_query["endpoint"] = "places"
                
                valid_queries.append(validated_query)
        
        strategy["queries"] = valid_queries
        return strategy
    
    async def generate_enhanced_leads(
        self,
        user_requirement: str,
        location: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Generate leads using enhanced Gemini-powered query analysis.
        
        Args:
            user_requirement: Natural language description of what user wants
            location: Geographic location
            limit: Maximum number of leads
            
        Returns:
            Dictionary containing CSV URL and metadata
        """
        
        try:
            # Get enhanced strategy from Gemini
            strategy = await self._enhance_query_with_gemini(user_requirement, location)
            
            all_leads = []
            strategy_results = {}
            
            # Execute queries based on strategy
            queries = sorted(strategy["queries"], key=lambda x: x.get("priority", 1))
            
            for query in queries:
                if len(all_leads) >= limit:
                    break
                
                try:
                    endpoint = query["endpoint"]
                    remaining_limit = limit - len(all_leads)
                    query_limit = min(query["num"], remaining_limit)
                    
                    if endpoint == "places":
                        leads = await self._search_places_enhanced(query, query_limit)
                    elif endpoint == "search":
                        leads = await self._search_web_enhanced(query, query_limit)
                    else:
                        # Skip unsupported endpoints for now
                        continue
                    
                    all_leads.extend(leads)
                    strategy_results[f"{endpoint}_{query.get('priority', 1)}"] = len(leads)
                    
                    # Add delay between requests
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    print(f"Query failed for {endpoint}: {str(e)}")
                    continue
            
            # Deduplicate leads
            unique_leads = self._deduplicate_leads(all_leads)
            final_leads = unique_leads[:limit]
            
            # Generate CSV
            csv_filename = self._generate_csv_filename(user_requirement, location)
            csv_path = self._save_csv(final_leads, csv_filename)
            csv_url = f"/static/{csv_filename}"
            
            return {
                "csv_url": csv_url,
                "csv_filename": csv_filename,
                "total_leads": len(final_leads),
                "strategy_used": strategy["primary_strategy"],
                "reasoning": strategy.get("reasoning", ""),
                "queries_executed": len(queries),
                "strategy_results": strategy_results,
                "duplicates_removed": len(all_leads) - len(unique_leads),
                "user_requirement": user_requirement
            }
            
        except Exception as e:
            raise LeadGenerationError(f"Enhanced lead generation failed: {str(e)}")
    
    async def _search_places_enhanced(self, query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Execute enhanced places search based on Gemini strategy."""
        
        payload = {
            "q": query["q"],
            "gl": query["gl"],
            "hl": query["hl"],
            "num": min(limit, 20)  # Places API limit
        }
        
        try:
            result = await self._make_request("places", payload)
            places = result.get("places", [])
            
            leads = []
            for place in places:
                lead = {
                    "name": place.get("title", "").strip(),
                    "phone": self._clean_phone(place.get("phoneNumber", "")),
                    "email": "",
                    "website": place.get("website", "").strip(),
                    "address": place.get("address", "").strip(),
                    "rating": place.get("rating", ""),
                    "reviews": place.get("reviewsCount", ""),
                    "category": place.get("category", ""),
                    "source": "Enhanced Places API",
                    "search_query": query["q"],
                    "strategy_priority": query.get("priority", 1)
                }
                
                if lead["name"] and (lead["phone"] or lead["website"]):
                    leads.append(lead)
            
            return leads
            
        except Exception as e:
            raise LeadGenerationError(f"Enhanced places search failed: {str(e)}")
    
    async def _search_web_enhanced(self, query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Execute enhanced web search based on Gemini strategy."""
        
        payload = {
            "q": query["q"],
            "gl": query["gl"],
            "hl": query["hl"],
            "num": min(limit, 10)
        }
        
        try:
            result = await self._make_request("search", payload)
            organic_results = result.get("organic", [])
            
            leads = []
            for result_item in organic_results:
                lead = {
                    "name": self._extract_business_name(result_item.get("title", "")),
                    "phone": self._extract_phone(result_item.get("snippet", "")),
                    "email": self._extract_email(result_item.get("snippet", "")),
                    "website": result_item.get("link", "").strip(),
                    "address": query["gl"].upper(),  # Country from query
                    "rating": "",
                    "reviews": "",
                    "category": "",
                    "source": "Enhanced Web Search",
                    "search_query": query["q"],
                    "strategy_priority": query.get("priority", 1),
                    "snippet": result_item.get("snippet", "")[:200]  # First 200 chars
                }
                
                if lead["name"] and (lead["phone"] or lead["email"] or lead["website"]):
                    leads.append(lead)
            
            return leads
            
        except Exception as e:
            # Don't fail completely if web search fails
            print(f"Enhanced web search failed: {str(e)}")
            return []