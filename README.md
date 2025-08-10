<div align="center">

# puchai-mcp-hack

Prototype MCP (Model Context Protocol) server for automated, configurable lead generation workflows powered by Serper.dev (Google Search API) + an LLM (e.g. Gemini) + transient CSV hosting.

</div>

---

## 1. Project Goal (What & Why)
Build an MCP server that exposes a small set of tools to an MCP-compatible client (Puch AI) enabling a guided flow:

1. discuss – clarify and structure the client's lead generation requirements (industry, geography, data fields, filters, volume, exclusions).  
2. plan – convert confirmed requirements into an execution plan: which Serper.dev endpoints, query templates, pagination strategy, concurrency, dedupe keys, validation rules.  
3. build – generate a customized JavaScript scraper script (pattern similar to `sample.js`) using the plan; execute it; produce a cleaned dataset (CSV).  
4. publish (or deliver) – make the CSV available via a temporary HTTPS URL (internal ephemeral storage or lightweight object storage) and return that URL to the client.  

This abstracts technical scraping logic away from a non‑technical user while preserving transparency (the generated code can be returned for auditability).

---

## 2. Current Assets
| File | Purpose |
|------|---------|
| `sample.js` | Reference implementation of a robust Serper.dev + scraping workflow (retry, classification, CSV output). |
| `docs/puchai-mcp.md` (to be added) | Captured + summarized Puch AI MCP integration page. |
| `docs/serper-snippets.md` (to be added) | JavaScript snippets for different Serper.dev endpoints. |

---

## 3. High-Level Architecture
```
MCP Client (Puch AI)
		↕ (JSON-RPC over MCP)
MCP Server
	├─ Tool: discuss  (LLM: requirement elicitation & normalization)
	├─ Tool: plan     (LLM assisted – expand queries; choose endpoints)
	├─ Tool: build    (Generate & optionally run JS; store artifacts)
	├─ Tool: publish  (Return signed/ephemeral URL to CSV)
	└─ Tool: validate (Mandatory per Puch AI – bearer token → owner phone)

Execution Sandbox / Runner
	├─ Node.js runtime
	└─ Temp storage (e.g. /tmp or memory → upload)

Ephemeral Storage / Hosting Layer
	├─ Option A: Simple in‑process static file server (delete after TTL)
	├─ Option B: Object storage (R2/S3) with lifecycle rule (1h TTL)
	└─ Option C: Paste-style hosting service (if ToS OK)
```

---

## 4. Proposed Tool Contracts
Each tool returns structured JSON for deterministic chaining.

| Tool | Input | Output | Notes |
|------|-------|--------|-------|
| validate | `{ bearerToken }` | `{ phone:"<countrycode><number>" }` | Mandatory for Puch AI auth. |
| discuss | `{ freeformDescription }` | `{ requirements:{...}, openQuestions:[] }` | Iterative; may surface missing fields. |
| plan | `{ requirements }` | `{ plan:{ queries:[], endpoints:[], fields:[], heuristics:{} }` | Adds rate limit + dedupe strategy. |
| build | `{ plan }` | `{ code, runId, estimatedCalls, status }` | Optionally executes code immediately. |
| publish | `{ runId }` | `{ csvUrl, expiresAt, rowCount, schema }` | TTL enforcement. |

Error modes: validation error, rate limit, transient HTTP failure, execution timeout, empty results.

---

## 5. Workflow Summary
1. User describes need (e.g., “Canadian immigration law firms with phone + email”).  
2. discuss normalizes into structured requirement: vertical, geography scope, required fields, min rows, exclusions, freshness.  
3. plan chooses Serper endpoints (e.g., `search`, `places`, `news` if relevant), query templates, pagination depth, concurrency caps (respect Serper.dev + website ethics).  
4. build generates script (like `sample.js` but parameterized) including: retry, classification, validation, CSV writer, progress metrics.  
5. Script runs; dedupes; outputs CSV.  
6. publish returns URL (secured, ephemeral).  
7. Client may optionally request the generated code for audit.  

---

## 6. Neutral Assessment of Original Idea
The core concept (LLM‑assisted configuration → automated data extraction → ephemeral delivery) is feasible. Key clarifications needed:

| Aspect | Observation / Adjustment |
|--------|--------------------------|
| Output Format via MCP | MCP transports tool call results; large CSVs should not be inlined. Returning a URL (with TTL) is pragmatic. |
| Google Sheet Alternative | Adds OAuth & quota complexity; not necessary for MVP. Local hosting + signed URL simpler. |
| Serper.dev Usage | Acceptable for search endpoints; ensure compliance with Serper.dev terms & underlying Google ToS (avoid excessive automation & scraping of raw result pages). |
| Direct Website Scraping | Introduces legal/ethical considerations; consider robots.txt respect & rate limiting. |
| LLM in build step | Good for flexible code generation; must sandbox to prevent arbitrary code risk. Consider allow‑listed libs only. |
| Data Quality | Need explicit schema + validation (e.g., phone/email patterns, minimal name length) – partially demonstrated in `sample.js`. |
| Volume Expectations | Add guardrails on max pages / concurrency to avoid cost blow‑ups. |
| Privacy & Compliance | Avoid storing personally identifiable information longer than necessary; document retention policy. |
| Reliability | Include retry/backoff at both API (Serper) & HTTP scraping layer; already shown. |
| Cost Control | Plan step should forecast API call count & token usage before execution. |

Overall: Technically sound as an experiment; production hardening needed around authentication, abuse prevention, audit logging, and data governance.

---

## 7. Implementation Phases (Incremental)
| Phase | Goal | Deliverables |
|-------|------|--------------|
| 0 | Skeleton | MCP server with validate tool placeholder. |
| 1 | discuss | LLM prompt templates; requirement schema. |
| 2 | plan | Endpoint selection logic + cost estimation. |
| 3 | build | Code generation + sandbox runner + metrics. |
| 4 | publish | Temp file hosting + signed URL + TTL cleanup. |
| 5 | QA | Tests (unit for planners, integration full flow). |
| 6 | Hardening | Rate limiting, input validation, logging, error taxonomy. |

---

## 8. Environment & Config
| Variable | Purpose |
|----------|---------|
| `SERPER_API_KEY` | Serper.dev API key. |
| `GEMINI_API_KEY` (or `OPENAI_API_KEY`) | LLM provider for discuss/plan/build. |
| `CSV_TTL_SECONDS` | Expiration for hosted CSV (e.g. 3600). |
| `MAX_CONCURRENCY` | Upper bound for simultaneous HTTP fetches. |

Local `.env` example:
```
SERPER_API_KEY=xxx
GEMINI_API_KEY=xxx
CSV_TTL_SECONDS=3600
MAX_CONCURRENCY=4
```

---

## 9. Security & Safety Notes
- Never echo API keys in tool responses.  
- Sandbox generated code (VM context, disable `child_process`, restrict fs).  
- Enforce per‑run quotas (max queries, max rows).  
- Redact PII from logs beyond minimal operational metadata.  

---

## 10. Reference Script (`sample.js` Highlights)
Demonstrates:
* Robust Serper query loops with pagination & role variants.  
* Places + specialized searches for breadth.  
* Concurrency throttling (`p-limit`).  
* Deduplication via phone key, validation & classification heuristics.  
* Structured CSV export with escaping.  

Improvements to consider for generated scripts:
* Parameterize search roles, regions, page depth.  
* Abstract classification logic.  
* Configurable output schema.  
* Pluggable validation rules (phone, email, domain filters).  
* Dry‑run / estimation mode.  

---

## 11. Serper.dev Endpoint Snippets
See `docs/serper-snippets.md` for ready‑to‑use JavaScript code covering `search`, `places`, `images`, `news`, `scholar`, `shopping`, `jobs`, `patents`, etc.

---

## 12. MCP Integration Notes (Puch AI)
Condensed requirements from Puch AI docs:
* Server must be HTTPS.  
* Must implement `validate` tool (bearer token → owner phone number).  
* Tools must declare schema & be callable via MCP.  
* Large artifacts served out‑of‑band via URL (tool returns metadata).  

Full captured page: `docs/puchai-mcp.md`.

---

## 13. Roadmap / TODO
- [ ] Add project scaffold (`src/` with tool handlers).  
- [ ] Define JSON schemas (Zod / TypeBox) for each tool I/O.  
- [ ] Implement validate tool (static map or JWT).  
- [ ] Implement discuss prompts + iterative refinement loop.  
- [ ] Implement planning heuristics & cost estimation.  
- [ ] Secure code generation sandbox.  
- [ ] Implement ephemeral hosting (in‑memory + cleanup scheduler).  
- [ ] Add test harness for full pipeline.  
- [ ] Add logging + error taxonomy mapping.  

---

## 14. Resources
* Puch AI MCP docs: https://puch.ai/mcp  
* MCP Specification: https://modelcontextprotocol.io/  
* Serper.dev API: https://serper.dev/  
* Example script: `sample.js`  

---

## 15. Disclaimer
This repository is an experimental prototype. Ensure compliance with all third‑party terms (Google, Serper.dev) and local regulations regarding data collection & storage before production use.

---

## 16. License
TBD.

---

## 17. Quick Start (Future)
```
pnpm install
node server.js  # (after implementing tools)
```

---

Feel free to iterate – the structure above should make next steps explicit.