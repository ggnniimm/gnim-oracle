# ARCHITECTURE — LandingAI ADE Python SDK

## Project Overview

**LandingAI ADE (Agentic Document Extraction) Python Library** is a fully-typed Python SDK for interacting with the LandingAI REST API, providing document parsing, splitting, and data extraction capabilities with support for both synchronous and asynchronous clients.

> Generated from OpenAPI spec using **Stainless** code generation framework.

---

## Directory Structure

```
src/landingai_ade/
├── __init__.py                 # Public API exports
├── _client.py                  # Main sync/async client (1,098 lines)
├── _base_client.py             # Base HTTP client infrastructure (2,127 lines)
├── _exceptions.py              # Exception hierarchy
├── _models.py                  # Pydantic model utilities
├── _response.py                # Response wrapper and parsing
├── _types.py                   # Type definitions
├── _files.py                   # File upload handling
├── _streaming.py               # Streaming response handling
│
├── _utils/                     # Internal utilities
│   ├── _logs.py
│   ├── _json.py
│   ├── _transform.py
│   └── ...
│
├── lib/                        # Public SDK extensions
│   ├── schema_utils.py         # pydantic_to_json_schema()
│   └── url_utils.py            # URL/local path handling
│
├── resources/                  # API resource managers
│   └── parse_jobs.py           # Async parse jobs (create, list, get)
│
└── types/                      # API contract types
    ├── parse_response.py
    ├── extract_response.py
    ├── split_response.py
    ├── parse_job_*.py
    └── shared/
        ├── parse_metadata.py
        └── parse_grounding_box.py
```

---

## Core Client Architecture

### Entry Points
- **`LandingAIADE`** — Synchronous client
- **`AsyncLandingAIADE`** — Asynchronous client
- Both aliases: `Client`, `AsyncClient`

### Client Methods

```
client.parse(document/document_url, model, save_to?)   → ParseResponse
client.extract(schema, markdown/markdown_url, save_to?) → ExtractResponse
client.split(split_class, markdown, model)              → SplitResponse
client.parse_jobs.create()                              → ParseJobCreateResponse
client.parse_jobs.list()                                → ParseJobListResponse
client.parse_jobs.get(job_id)                           → ParseJobGetResponse
```

---

## Request/Response Flow

```
User Code
   ↓
Client Method (parse/extract/split)
   ↓
maybe_transform() → Prepare request params
extract_files() → Handle file uploads (multipart/form-data)
   ↓
SyncAPIClient.post() / AsyncAPIClient.post()
   ↓
httpx.Client / httpx.AsyncClient
   ↓
_response.APIResponse → construct_type() → Pydantic validation
   ↓
_save_response() → Optional JSON file save
   ↓
Return Pydantic model
```

---

## Response Types

| Type | Contents |
|------|----------|
| `ParseResponse` | `chunks`, `markdown`, `metadata`, `splits`, `grounding` |
| `ExtractResponse` | `extraction`, `extraction_metadata`, `metadata` |
| `SplitResponse` | `splits` (classification, pages, markdowns), `metadata` |
| `ParseJobGetResponse` | `job_id`, `status`, `progress`, `data` |

**Chunk structure:**
```python
class Chunk(BaseModel):
    id: str
    grounding: ChunkGrounding   # bounding box + page
    markdown: str
    type: str
```

---

## Error Hierarchy

```
LandingAiadeError
└── APIError
    ├── APIStatusError
    │   ├── BadRequestError (400)
    │   ├── AuthenticationError (401)
    │   ├── PermissionDeniedError (403)
    │   ├── NotFoundError (404)
    │   ├── ConflictError (409)
    │   ├── UnprocessableEntityError (422)
    │   ├── RateLimitError (429)
    │   └── InternalServerError (5xx)
    ├── APIConnectionError
    ├── APITimeoutError
    └── APIResponseValidationError
```

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `httpx` | HTTP client (sync & async) |
| `pydantic` | Data validation & serialization |
| `anyio` | Async library abstraction |
| `typing-extensions` | Extended type hints (Python 3.9+) |
| `aiohttp` (optional) | Alternative async HTTP backend |

---

## Design Patterns

1. **Pluggable HTTP Backends** — `DefaultHttpxClient`, `DefaultAsyncHttpxClient`, `DefaultAioHttpClient`
2. **Automatic Retry** — Exponential backoff, default 2 retries (408/409/429/5xx)
3. **Raw Response Access** — `client.with_raw_response.parse(...)` → httpx.Response
4. **Streaming** — `client.with_streaming_response.parse(...)` → iter_bytes/iter_lines
5. **Client Copy Pattern** — `client.with_options(timeout=10).parse(...)` for per-request overrides
6. **Save-to-File** — `save_to="./output"` auto-saves JSON as `{stem}_{method}_output.json`

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `VISION_AGENT_API_KEY` | API authentication |
| `LANDINGAI_ADE_BASE_URL` | Custom endpoint override |
| `LANDINGAI_ADE_LOG` | Logging level (info/debug) |

**Environments:** `production` (default) → `api.va.landing.ai` | `eu` → `api.va.eu-west-1.landing.ai`
