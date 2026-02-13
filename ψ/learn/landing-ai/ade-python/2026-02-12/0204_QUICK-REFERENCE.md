# QUICK REFERENCE — LandingAI ADE Python SDK

**LandingAI ADE** คือ Python SDK สำหรับ Agentic Document Extraction — แปลง PDF/รูปภาพ/สเปรดชีตเป็น structured data โดยใช้ AI

---

## Install & Setup

```bash
pip install landingai-ade
export VISION_AGENT_API_KEY="your-key"
```

---

## Supported File Types

- **Documents**: PDF, PNG, JPEG, JPG, TIFF, BMP, GIF, WebP
- **Spreadsheets**: XLSX, CSV

---

## 3 Core Operations

| Method | Input | Output |
|--------|-------|--------|
| `parse()` | PDF/image file | Markdown + chunks + metadata |
| `extract()` | Markdown + JSON schema | Structured data (dict) |
| `split()` | Markdown + class definitions | Document classification per page |

---

## Workflow ทั่วไป

```
PDF → parse() → markdown → extract(schema) → structured data
                          → split(classes) → classified sections
```

---

## Quick Examples

```python
from landingai_ade import LandingAIADE
from landingai_ade.lib import pydantic_to_json_schema
from pydantic import BaseModel, Field
from pathlib import Path

client = LandingAIADE()  # uses VISION_AGENT_API_KEY

# Parse
result = client.parse(document=Path("doc.pdf"), model="dpt-2-latest")
print(result.markdown)

# Extract
class Invoice(BaseModel):
    total: float = Field(description="Total amount")
    vendor: str = Field(description="Vendor name")

result = client.extract(schema=pydantic_to_json_schema(Invoice), markdown=Path("doc.pdf"))
print(result.extraction)   # {"total": 1500.0, "vendor": "ABC Co."}
```

---

## Models

| Model | Use for |
|-------|---------|
| `dpt-2-latest` | Parsing documents |
| `extract-latest` | Extracting structured data |
| `split-latest` | Splitting/classifying |

---

## Environments

```python
client = LandingAIADE(environment="production")  # default
client = LandingAIADE(environment="eu")          # EU region
```

---

## For Large Files → Async Jobs

```python
job = client.parse_jobs.create(document=Path("large.pdf"), model="dpt-2-latest")
status = client.parse_jobs.get(job.job_id)   # check: pending/processing/completed/failed
```

---

## Gotchas

1. **API key** ต้องชื่อ `VISION_AGENT_API_KEY` (ไม่ใช่ `LANDING_AI_API_KEY`)
2. **extract()** รับ `markdown` เป็น string หรือ Path ก็ได้ — ถ้า Path จะ parse ให้ก่อน
3. **Large files** → ใช้ `parse_jobs` แทน `parse()` ตรงๆ
4. **schema** ต้อง pass เป็น JSON string (ใช้ `pydantic_to_json_schema()`)
5. Credit ถูก consume ทุก call — monitor `response.metadata.credit_usage`

---

## Links

- Docs: https://docs.landing.ai/ade/ade-overview
- Playground: https://va.landing.ai
- Discord: https://discord.com/invite/RVcW3j9RgR
- File types: https://docs.landing.ai/ade/ade-file-types
