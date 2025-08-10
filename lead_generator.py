"""
Lead Generator using Serper.dev API
Core logic for finding business leads through web search and places API.
"""

import asyncio
import csv
import hashlib
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import httpx


class LeadGenerationError(Exception):
    """Custom exception for lead generation errors."""
    pass


class LeadGenerator:
    """Lead generator using Serper.dev API for business discovery."""
    
    def __init__(self):
        self.api_key = os.environ.get("SERPER_API_KEY")
        if not self.api_key:
            raise LeadGenerationError("SERPER_API_KEY environment variable is required")
        
        self.base_url = "https://google.serper.dev"
        self.timeout = 15.0
        self.rate_limit_delay = 1.2  # Seconds between requests
        
        # Create static directory for CSV files
        self.static_dir = os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(self.static_dir, exist_ok=True)
    
    async def _make_request(
        self, 
        endpoint: str, 
        payload: Dict[str, Any],
        retries: int = 3
    ) -> Dict[str, Any]:
        """Make a request to Serper.dev API with retry logic."""
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(retries):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:
                        # Rate limited - wait longer
                        wait_time = (attempt + 1) * 2
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        response.raise_for_status()
                        
                except httpx.TimeoutException:
                    if attempt == retries - 1:
                        raise LeadGenerationError("Request timeout - Serper API is not responding")
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
                except httpx.HTTPStatusError as e:
                    if attempt == retries - 1:
                        raise LeadGenerationError(f"Serper API error: {e.response.status_code}")
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
                except Exception as e:
                    if attempt == retries - 1:
                        raise LeadGenerationError(f"Network error: {str(e)}")
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        raise LeadGenerationError("Failed to get response after all retries")
    
    async def _search_places(self, query: str, location: str, limit: int) -> List[Dict[str, Any]]:
        """Search for businesses using Places API."""
        
        payload = {
            "q": f"{query} {location}",
            "gl": self._get_country_code(location),
            "hl": "en",
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
                    "email": "",  # Places API doesn't provide emails
                    "website": place.get("website", "").strip(),
                    "address": place.get("address", "").strip(),
                    "rating": place.get("rating", ""),
                    "source": "Places API",
                    "search_query": query
                }
                
                # Only include if we have at least name and some contact info
                if lead["name"] and (lead["phone"] or lead["website"]):
                    leads.append(lead)
            
            return leads
            
        except Exception as e:
            raise LeadGenerationError(f"Places search failed: {str(e)}")
    
    async def _search_web(self, query: str, location: str, limit: int) -> List[Dict[str, Any]]:
        """Search for businesses using web search for additional leads."""
        
        # Enhance query for better lead discovery
        search_query = f'"{query}" "{location}" phone email contact'
        
        payload = {
            "q": search_query,
            "gl": self._get_country_code(location),
            "hl": "en",
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
                    "address": location,
                    "rating": "",
                    "source": "Web Search",
                    "search_query": query
                }
                
                # Only include if we have meaningful data
                if lead["name"] and (lead["phone"] or lead["email"] or lead["website"]):
                    leads.append(lead)
            
            return leads
            
        except Exception as e:
            # Don't fail completely if web search fails - places might work
            print(f"Web search failed: {str(e)}")
            return []
    
    def _get_country_code(self, location: str) -> str:
        """Get country code for location."""
        location_lower = location.lower()
        
        country_codes = {
            "canada": "ca",
            "toronto": "ca",
            "vancouver": "ca",
            "montreal": "ca",
            "calgary": "ca",
            "ottawa": "ca",
            "united states": "us",
            "usa": "us",
            "new york": "us",
            "los angeles": "us",
            "chicago": "us",
            "houston": "us",
            "miami": "us",
            "united kingdom": "gb",
            "uk": "gb",
            "london": "gb",
            "manchester": "gb",
            "birmingham": "gb",
            "australia": "au",
            "sydney": "au",
            "melbourne": "au",
            "brisbane": "au",
        }
        
        for key, code in country_codes.items():
            if key in location_lower:
                return code
        
        return "us"  # Default to US
    
    def _clean_phone(self, phone: str) -> str:
        """Clean and format phone number."""
        if not phone:
            return ""
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Basic validation - should have at least 7 digits
        digits = re.sub(r'[^\d]', '', cleaned)
        if len(digits) < 7:
            return ""
        
        return cleaned
    
    def _extract_phone(self, text: str) -> str:
        """Extract phone number from text."""
        if not text:
            return ""
        
        # Common phone patterns
        patterns = [
            r'\+?1?[\s\-\.]?\(?(\d{3})\)?[\s\-\.]?(\d{3})[\s\-\.]?(\d{4})',  # US/Canada
            r'\+?44[\s\-\.]?(\d{4})[\s\-\.]?(\d{6})',  # UK
            r'\+?61[\s\-\.]?(\d{1})[\s\-\.]?(\d{4})[\s\-\.]?(\d{4})',  # Australia
            r'(\d{3})[\s\-\.](\d{3})[\s\-\.](\d{4})',  # Generic
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._clean_phone(match.group(0))
        
        return ""
    
    def _extract_email(self, text: str) -> str:
        """Extract email address from text."""
        if not text:
            return ""
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        
        return match.group(0) if match else ""
    
    def _extract_business_name(self, title: str) -> str:
        """Extract business name from search result title."""
        if not title:
            return ""
        
        # Remove common suffixes and clean up
        name = title.split(" - ")[0]  # Remove everything after " - "
        name = title.split(" | ")[0]  # Remove everything after " | "
        
        # Remove common website indicators
        name = re.sub(r'\s*\|\s*.*$', '', name)
        name = re.sub(r'\s*-\s*.*$', '', name)
        
        return name.strip()
    
    def _deduplicate_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate leads based on phone number, email, or website."""
        seen = set()
        unique_leads = []
        
        for lead in leads:
            # Create a key based on available identifiers
            identifiers = []
            if lead.get("phone"):
                identifiers.append(f"phone:{lead['phone']}")
            if lead.get("email"):
                identifiers.append(f"email:{lead['email']}")
            if lead.get("website"):
                # Normalize website URL
                try:
                    parsed = urlparse(lead["website"])
                    domain = parsed.netloc.lower().replace("www.", "")
                    if domain:
                        identifiers.append(f"domain:{domain}")
                except:
                    pass
            
            # If no identifiers, use name + location
            if not identifiers:
                identifiers.append(f"name:{lead.get('name', '').lower().strip()}")
            
            # Create deduplication key
            dedup_key = "|".join(sorted(identifiers))
            
            if dedup_key not in seen:
                seen.add(dedup_key)
                unique_leads.append(lead)
        
        return unique_leads
    
    def _generate_csv_filename(self, industry: str, location: str) -> str:
        """Generate a unique CSV filename."""
        # Create a hash of the parameters for uniqueness
        hash_input = f"{industry}_{location}_{datetime.now().strftime('%Y%m%d')}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        
        # Clean industry and location for filename
        clean_industry = re.sub(r'[^\w\s-]', '', industry).strip()
        clean_industry = re.sub(r'[-\s]+', '_', clean_industry)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"leads_{clean_industry}_{hash_suffix}_{timestamp}.csv"
    
    def _save_csv(self, leads: List[Dict[str, Any]], filename: str) -> str:
        """Save leads to CSV file and return the file path."""
        filepath = os.path.join(self.static_dir, filename)
        
        if not leads:
            # Create empty CSV with headers
            headers = ["name", "phone", "email", "website", "address", "rating", "source", "search_query"]
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
            return filepath
        
        # Get all possible fields from leads
        all_fields = set()
        for lead in leads:
            all_fields.update(lead.keys())
        
        # Define preferred field order
        field_order = ["name", "phone", "email", "website", "address", "rating", "source", "search_query"]
        
        # Add any additional fields not in the preferred order
        ordered_fields = field_order + [f for f in sorted(all_fields) if f not in field_order]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=ordered_fields)
            writer.writeheader()
            writer.writerows(leads)
        
        return filepath
    
    async def generate_leads(
        self, 
        industry: str, 
        location: str, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Generate leads for a specific industry and location.
        
        Args:
            industry: Type of business to search for
            location: Geographic location
            limit: Maximum number of leads to return
            
        Returns:
            Dictionary containing CSV URL and metadata
        """
        try:
            all_leads = []
            
            # Search using Places API (primary source)
            places_leads = await self._search_places(industry, location, limit)
            all_leads.extend(places_leads)
            
            # Add delay to respect rate limits
            await asyncio.sleep(self.rate_limit_delay)
            
            # Search using Web API for additional leads (if we need more)
            remaining_limit = limit - len(places_leads)
            if remaining_limit > 0:
                web_leads = await self._search_web(industry, location, remaining_limit)
                all_leads.extend(web_leads)
            
            # Deduplicate leads
            unique_leads = self._deduplicate_leads(all_leads)
            
            # Limit to requested number
            final_leads = unique_leads[:limit]
            
            # Generate CSV filename
            csv_filename = self._generate_csv_filename(industry, location)
            
            # Save to CSV
            csv_path = self._save_csv(final_leads, csv_filename)
            
            # Generate public URL (assuming the server serves static files)
            csv_url = f"/static/{csv_filename}"
            
            return {
                "csv_url": csv_url,
                "csv_filename": csv_filename,
                "total_leads": len(final_leads),
                "places_leads": len(places_leads),
                "web_leads": len(all_leads) - len(places_leads),
                "duplicates_removed": len(all_leads) - len(unique_leads)
            }
            
        except Exception as e:
            raise LeadGenerationError(f"Lead generation failed: {str(e)}")