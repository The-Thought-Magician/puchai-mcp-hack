import asyncio
import os
import json
import csv
import uuid
import tempfile
import threading
import re
from datetime import datetime, timedelta
from typing import Annotated, Optional, Dict, List, Any, NoReturn

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field

import google.generativeai as genai  # type: ignore
import httpx

# --- Load environment variables ---
load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CSV_TTL_SECONDS = int(os.environ.get("CSV_TTL_SECONDS", "3600"))
MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY", "4"))
PORT = int(os.environ.get("PORT", "8086"))
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8086")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"
assert SERPER_API_KEY is not None, "Please set SERPER_API_KEY in your .env file"
assert GEMINI_API_KEY is not None, "Please set GEMINI_API_KEY in your .env file"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)  # type: ignore[attr-defined]

# --- Auth Provider ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="puch-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

# --- Rich Tool Description model ---
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# --- Data Models ---
class LeadRequirement(BaseModel):
    industry: str = Field(description="Target industry or business type")
    location: str = Field(description="Geographic area to search")
    required_fields: List[str] = Field(description="Required contact fields (name, phone, email, website)")
    additional_criteria: Optional[str] = Field(description="Additional search criteria or filters")
    max_results: int = Field(default=50, description="Maximum number of results to return")

# --- In-memory storage ---
LEAD_JOBS: Dict[str, Dict[str, Any]] = {}
CSV_FILES: Dict[str, Dict[str, Any]] = {}

# --- Utility Functions ---
def _now() -> str:
    return datetime.utcnow().isoformat()

def _error(code, msg) -> NoReturn:
    raise McpError(ErrorData(code=code, message=msg))

def _cleanup_expired_files():
    current_time = datetime.now()
    expired_jobs: List[str] = []
    for job_id, file_info in CSV_FILES.items():
        if current_time > datetime.fromisoformat(file_info['expires_at']):
            try:
                if os.path.exists(file_info['file_path']):
                    os.remove(file_info['file_path'])
                expired_jobs.append(job_id)
            except Exception as e:  # noqa: BLE001
                print(f"Error cleaning up file for job {job_id}: {e}")
    for job_id in expired_jobs:
        CSV_FILES.pop(job_id, None)
        LEAD_JOBS.pop(job_id, None)

def _start_cleanup_scheduler():
    def schedule_cleanup():
        while True:
            _cleanup_expired_files()
            threading.Event().wait(300)
    threading.Thread(target=schedule_cleanup, daemon=True).start()

# --- Serper API Utility Class ---
class SerperAPI:
    USER_AGENT = "Puch/1.0 (Lead Generator)"

    @classmethod
    async def search(cls, query: str, location: Optional[str] = None, num_results: int = 10) -> dict[str, Any]:
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json',
        }
        payload: Dict[str, Any] = {'q': query, 'num': min(num_results, 100)}
        if location:
            payload['gl'] = 'us'
            payload['hl'] = 'en'
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post("https://google.serper.dev/search", headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:  # noqa: PERF203
                _error(INTERNAL_ERROR, f"Serper API error: {str(e)}")

    @classmethod
    async def places_search(cls, query: str, location: Optional[str] = None, num_results: int = 20) -> dict[str, Any]:
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json',
        }
        payload: Dict[str, Any] = {'q': query, 'num': min(num_results, 20)}
        if location:
            payload['gl'] = 'us'
            payload['hl'] = 'en'
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post("https://google.serper.dev/places", headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:  # noqa: PERF203
                _error(INTERNAL_ERROR, f"Serper Places API error: {str(e)}")

# --- Gemini AI Utility Class ---
class GeminiAI:
    @classmethod
    async def extract_requirements(cls, user_input: str) -> dict[str, Any]:
        model = genai.GenerativeModel('gemini-1.5-flash')  # type: ignore[attr-defined]
        prompt = f"""
Extract lead generation requirements from this user request: "{user_input}"

Return a JSON object with these fields:
- industry: The business type/industry they want
- location: Geographic area to search  
- required_fields: Array of contact fields needed (name, phone, email, website)
- additional_criteria: Any specific requirements or filters
- max_results: Number of results (default 50)
- clarifying_questions: Array of questions to ask if requirements are unclear

Example response:
{{
    "industry": "dentists",
    "location": "Toronto, Canada",
    "required_fields": ["name", "phone", "email", "website"],
    "additional_criteria": "accepting new patients",
    "max_results": 50,
    "clarifying_questions": []
}}

If the request is unclear, include clarifying_questions.
"""
        try:
            response = await model.generate_content_async(prompt)
            result = response.text.strip()
            if '```json' in result:
                result = result.split('```json')[1].split('```')[0].strip()
            elif '```' in result:
                result = result.split('```')[1].split('```')[0].strip()
            return json.loads(result)
        except Exception as e:  # noqa: BLE001
            _error(INTERNAL_ERROR, f"Gemini API error: {str(e)}")

    @classmethod
    async def generate_search_queries(cls, requirements: LeadRequirement) -> List[str]:
        model = genai.GenerativeModel('gemini-1.5-flash')  # type: ignore[attr-defined]
        prompt = f"""
Generate 3-5 effective Google search queries for finding business leads with these requirements:
- Industry: {requirements.industry}
- Location: {requirements.location}  
- Additional criteria: {requirements.additional_criteria or "None"}

Focus on queries that will find business listings with contact information.
Return only the search queries, one per line.

Examples:
dentists in Toronto contact information
dental offices Toronto phone email
Toronto dentistry practices directory
"""
        try:
            response = await model.generate_content_async(prompt)
            queries = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
            return queries[:5]
        except Exception as e:  # noqa: BLE001
            _error(INTERNAL_ERROR, f"Gemini API error: {str(e)}")

# --- Lead Extraction Utility Class ---
class LeadExtractor:
    PHONE_PATTERNS = [
        r'(\+?1?[-\.\s]?)?\(?([0-9]{3})\)?[-\.\s]?([0-9]{3})[-\.\s]?([0-9]{4})',
        r'(\+?\d{1,3}[-\.\s]?)?\(?([0-9]{3})\)?[-\.\s]?([0-9]{3})[-\.\s]?([0-9]{4})',
    ]
    EMAIL_PATTERNS = [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b']

    @classmethod
    def extract_leads_from_results(cls, search_results: Dict[str, Any], places_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        leads: List[Dict[str, Any]] = []
        seen_phones: set[str] = set()

        organic_results = search_results.get('organic', []) or []
        for result in organic_results:
            lead: Dict[str, Any] = {
                'name': (result.get('title') or '').replace(' - Google Search', ''),
                'website': result.get('link', ''),
                'phone': '',
                'email': '',
                'address': '',
                'rating': '',
                'source': 'search',
            }
            snippet = result.get('snippet', '')
            phone = cls._extract_phone(snippet)
            email = cls._extract_email(snippet)
            if phone and phone not in seen_phones:
                lead['phone'] = phone
                seen_phones.add(phone)
                if email:
                    lead['email'] = email
                leads.append(lead)

        places = places_results.get('places', []) or []
        for place in places:
            phone = place.get('phoneNumber', '')
            if phone and phone not in seen_phones:
                lead = {
                    'name': place.get('title', ''),
                    'website': place.get('website', ''),
                    'phone': phone,
                    'email': '',
                    'address': place.get('address', ''),
                    'rating': place.get('rating', ''),
                    'source': 'places',
                }
                seen_phones.add(phone)
                leads.append(lead)

        return leads

    @classmethod
    def _extract_phone(cls, text: str) -> str:
        for pattern in cls.PHONE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ''

    @classmethod
    def _extract_email(cls, text: str) -> str:
        for pattern in cls.EMAIL_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ''

# --- CSV Generation Utility ---
class CSVGenerator:
    @classmethod
    async def generate_csv_file(cls, job_id: str, leads: List[Dict[str, Any]]) -> str:
        temp_dir = tempfile.gettempdir()
        csv_path = os.path.join(temp_dir, f"leads_{job_id}.csv")
        fieldnames = ['name', 'phone', 'email', 'website', 'address', 'rating', 'source']
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for lead in leads:
                row = {field: lead.get(field, '') for field in fieldnames}
                writer.writerow(row)
        return csv_path

# --- Background Processing ---
async def _process_lead_generation(job_id: str, requirements: LeadRequirement):
    try:
        job = LEAD_JOBS[job_id]
        job['progress'] = 10
        queries = await GeminiAI.generate_search_queries(requirements)
        job['progress'] = 20
        all_leads: List[Dict[str, Any]] = []
        for i, query in enumerate(queries):
            search_results = await SerperAPI.search(f"{query} {requirements.location}", requirements.location, num_results=20)
            places_results = await SerperAPI.places_search(f"{requirements.industry} {requirements.location}", requirements.location, num_results=20)
            leads = LeadExtractor.extract_leads_from_results(search_results, places_results)
            all_leads.extend(leads)
            job['progress'] = 20 + (i + 1) * (70 / max(1, len(queries)))

        unique_leads: List[Dict[str, Any]] = []
        seen_phones: set[str] = set()
        for lead in all_leads:
            phone = lead.get('phone', '')
            if phone and phone not in seen_phones and len(unique_leads) < requirements.max_results:
                seen_phones.add(phone)
                unique_leads.append(lead)

        job['status'] = 'completed'
        job['progress'] = 100
        job['results'] = unique_leads
        job['completed_at'] = _now()
    except Exception as e:  # noqa: BLE001
        job = LEAD_JOBS.get(job_id)
        if job is not None:
            job['status'] = 'failed'
            job['error'] = str(e)
        else:
            LEAD_JOBS[job_id] = {
                'status': 'failed',
                'progress': 0,
                'requirements': getattr(requirements, 'dict', lambda: {})(),
                'results': [],
                'created_at': _now(),
                'error': str(e),
            }

# --- MCP Server Setup ---
mcp = FastMCP(
    "Lead Generator MCP Server",
    auth=SimpleBearerAuthProvider(TOKEN),
)

_start_cleanup_scheduler()

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    """Validate MCP server for Puch AI integration - returns owner phone number"""
    return str(MY_NUMBER)

# --- Tool descriptions (rich) ---
DISCUSS_DESCRIPTION = RichToolDescription(
    description="Extract and clarify lead generation requirements from user input.",
    use_when="User provides a natural language request for finding business leads or contacts.",
    side_effects="Processes user input with AI and returns structured requirements or clarifying questions.",
)

BUILD_DESCRIPTION = RichToolDescription(
    description="Generate business leads based on confirmed requirements using AI-powered search.",
    use_when="User has confirmed their lead generation requirements and wants to start the process.",
    side_effects="Starts background lead generation job using Serper.dev API and AI processing.",
)

CREATE_DESCRIPTION = RichToolDescription(
    description="Generate CSV file with leads and return download URL.",
    use_when="Lead generation job is completed and user wants to download the results.",
    side_effects="Creates CSV file with contact data and provides temporary download link.",
)

# --- Tool: discuss (requirement gathering) ---
@mcp.tool(description=DISCUSS_DESCRIPTION.model_dump_json())
async def discuss(
    user_request: Annotated[str, Field(description="User's lead generation request in natural language")]
) -> str:
    try:
        requirements = await GeminiAI.extract_requirements(user_request)
        if requirements.get('clarifying_questions'):
            response = {
                "status": "needs_clarification",
                "extracted_requirements": requirements,
                "questions": requirements['clarifying_questions'],
                "message": "I need some clarification to generate the best leads for you.",
            }
        else:
            response = {
                "status": "requirements_ready",
                "requirements": requirements,
                "message": f"Ready to generate leads for {requirements.get('industry', 'businesses')} in {requirements.get('location', 'specified location')}.",
            }
        return json.dumps(response, indent=2)
    except Exception as e:  # noqa: BLE001
        _error(INTERNAL_ERROR, f"Error processing request: {str(e)}")

# --- Tool: build (lead generation) ---
@mcp.tool(description=BUILD_DESCRIPTION.model_dump_json())
async def build(
    requirements: Annotated[str, Field(description="JSON string of lead generation requirements from discuss tool")]
) -> str:
    try:
        req_data = json.loads(requirements)
        lead_req = LeadRequirement(**req_data)
        job_id = str(uuid.uuid4())
        LEAD_JOBS[job_id] = {
            'status': 'processing',
            'progress': 0,
            'requirements': lead_req.dict(),
            'results': [],
            'created_at': _now(),
        }
        asyncio.create_task(_process_lead_generation(job_id, lead_req))
        status_response = {
            "job_id": job_id,
            "status": "processing",
            "progress": 0,
            "estimated_completion": (datetime.now() + timedelta(minutes=3)).isoformat(),
            "results_count": 0,
            "message": "Lead generation started. This will take 2-5 minutes to complete.",
        }
        return json.dumps(status_response, indent=2)
    except json.JSONDecodeError:
        _error(INVALID_PARAMS, "Invalid requirements JSON")
    except Exception as e:  # noqa: BLE001
        _error(INTERNAL_ERROR, f"Error starting lead generation: {str(e)}")

# --- Tool: create (CSV generation and delivery) ---
@mcp.tool(description=CREATE_DESCRIPTION.model_dump_json())
async def create(
    job_id: Annotated[str, Field(description="Job ID from the build tool")]
) -> str:
    try:
        if job_id not in LEAD_JOBS:
            _error(INVALID_PARAMS, "Job ID not found")
        job = LEAD_JOBS[job_id]
        if job['status'] == 'processing':
            return json.dumps({
                "status": "processing",
                "message": "Lead generation still in progress. Please wait and try again.",
                "progress": job.get('progress', 0),
            })
        if job['status'] == 'failed':
            return json.dumps({
                "status": "failed",
                "message": f"Lead generation failed: {job.get('error', 'Unknown error')}",
            })
        csv_path = await CSVGenerator.generate_csv_file(job_id, job['results'])
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        expires_at = datetime.now() + timedelta(seconds=CSV_TTL_SECONDS)
        CSV_FILES[job_id] = {
            'file_path': csv_path,
            'expires_at': expires_at.isoformat(),
            'total_leads': len(job['results']),
        }
        delivery_response = {
            "job_id": job_id,
            "status": "completed",
            "total_leads": len(job['results']),
            "fields": ["name", "phone", "email", "website", "address", "rating", "source"],
            "message": f"✅ CSV generated with {len(job['results'])} leads!",
            "csv_content": csv_content,
            "filename": f"leads_{job_id}.csv",
        }
        return json.dumps(delivery_response, indent=2)
    except Exception as e:  # noqa: BLE001
        _error(INTERNAL_ERROR, f"Error creating CSV: {str(e)}")

# --- Run MCP Server ---
async def main():
    print(f"🚀 Starting Lead Generator MCP server on http://0.0.0.0:{PORT}")
    print(f"📞 Phone number for validation: {MY_NUMBER}")
    print(f"🔑 Auth token required for connection")
    print("💼 Tools: validate, discuss, build, create")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    asyncio.run(main())