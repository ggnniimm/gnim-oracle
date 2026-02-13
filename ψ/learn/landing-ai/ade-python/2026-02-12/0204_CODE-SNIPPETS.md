# CODE SNIPPETS — LandingAI ADE Python SDK

## 1. Installation & Auth

```bash
pip install landingai-ade
export VISION_AGENT_API_KEY="your-api-key-here"
```

---

## 2. Parse Document

```python
from pathlib import Path
from landingai_ade import LandingAIADE

client = LandingAIADE()  # reads VISION_AGENT_API_KEY from env

response = client.parse(
    document=Path("invoice.pdf"),
    model="dpt-2-latest",
    save_to="./output",   # optional: auto-saves as invoice_parse_output.json
)

print(response.markdown)           # full doc as Markdown
print(response.chunks)             # list of Chunk objects
print(response.metadata)           # duration_ms, credit_usage, etc.
```

---

## 3. Extract Structured Data

```python
from pydantic import BaseModel, Field
from landingai_ade import LandingAIADE
from landingai_ade.lib import pydantic_to_json_schema

class Invoice(BaseModel):
    invoice_number: str = Field(description="Invoice number")
    total_amount: float = Field(description="Total amount due")
    vendor_name: str = Field(description="Vendor company name")
    due_date: str = Field(description="Payment due date")

schema = pydantic_to_json_schema(Invoice)

client = LandingAIADE()
response = client.extract(
    schema=schema,
    markdown=Path("invoice.pdf"),   # or pass markdown string directly
    save_to="./output",
)

print(response.extraction)           # extracted dict matching Invoice fields
print(response.extraction_metadata)  # extraction with chunk references
```

---

## 4. Split / Classify Documents

```python
# Step 1: Parse
parse_response = client.parse(document=Path("multi_doc.pdf"), model="dpt-2-latest")

# Step 2: Define classes
split_class = [
    {"name": "Invoice", "description": "Financial document requesting payment"},
    {"name": "Receipt", "description": "Proof of transaction", "identifier": "Receipt Date"},
]

# Step 3: Split
split_response = client.split(
    split_class=split_class,
    markdown=parse_response.markdown,   # pass Markdown string from parse step
    model="split-latest",
)

for split in split_response.splits:
    print(f"{split.classification} — pages: {split.pages}")
    print(f"Identifier: {split.identifier}")
```

---

## 5. Async Client

```python
import asyncio
from pathlib import Path
from landingai_ade import AsyncLandingAIADE

async def main():
    async with AsyncLandingAIADE() as client:
        response = await client.parse(
            document=Path("file.pdf"),
            model="dpt-2-latest",
        )
        print(response.markdown)

asyncio.run(main())
```

---

## 6. Async Jobs (Large Documents)

```python
from pathlib import Path
from landingai_ade import LandingAIADE

client = LandingAIADE()

# Create job
job = client.parse_jobs.create(
    document=Path("large_document.pdf"),
    model="dpt-2-latest",
)
print(f"Job ID: {job.job_id}")

# Check status
status = client.parse_jobs.get(job.job_id)
print(f"Status: {status.status}")   # pending / processing / completed / failed
print(f"Progress: {status.progress}")  # 0.0 → 1.0

# List all jobs
jobs = client.parse_jobs.list(status="completed", page=0, page_size=10)
```

---

## 7. Error Handling

```python
import landingai_ade
from landingai_ade import LandingAIADE

client = LandingAIADE()

try:
    response = client.parse(document=Path("file.pdf"))
except landingai_ade.AuthenticationError:
    print("Invalid API key")
except landingai_ade.RateLimitError:
    print("Rate limited")
except landingai_ade.APITimeoutError:
    print("Timeout — consider async jobs for large files")
except landingai_ade.APIStatusError as e:
    print(f"API error {e.status_code}: {e.response}")
```

---

## 8. File Input Methods

```python
# From local path
client.parse(document=Path("file.pdf"))

# From URL
client.parse(document_url="https://example.com/file.pdf")

# From bytes
client.parse(document=b"raw pdf bytes")

# From tuple (filename, content, mime_type)
client.parse(document=("file.pdf", b"content", "application/pdf"))

# From file-like object
with open("file.pdf", "rb") as f:
    client.parse(document=f)
```

---

## 9. Per-Request Config

```python
# Timeout override
client.with_options(timeout=60).parse(document=Path("file.pdf"))

# Retry override
client.with_options(max_retries=0).parse(document=Path("file.pdf"))

# Both
client.with_options(timeout=120, max_retries=3).parse(...)
```

---

## 10. aiohttp Backend (Better Async)

```python
import asyncio
from pathlib import Path
from landingai_ade import AsyncLandingAIADE, DefaultAioHttpClient

async def main():
    async with AsyncLandingAIADE(http_client=DefaultAioHttpClient()) as client:
        response = await client.parse(document=Path("file.pdf"), model="dpt-2-latest")
        print(response.chunks)

asyncio.run(main())
```

---

## 11. Raw HTTP Response

```python
# Access headers and raw response
raw = client.with_raw_response.parse(document=Path("file.pdf"))
print(raw.headers)
parsed = raw.parse()   # get actual ParseResponse

# Streaming
with client.with_streaming_response.parse(document=Path("file.pdf")) as resp:
    for chunk in resp.iter_bytes():
        print(chunk)
```

---

## 12. pydantic_to_json_schema Internals

```python
# src/landingai_ade/lib/schema_utils.py
def pydantic_to_json_schema(model: Type[BaseModel]) -> str:
    """
    Convert Pydantic model to JSON schema string with all $refs resolved.
    Required for the extract() API.
    """
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})
    schema = _resolve_refs(schema, defs)   # flattens nested $refs
    return json.dumps(schema)
```
