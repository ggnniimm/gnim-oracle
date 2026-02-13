# Lessons: Thai Legal RAG OCR Pipeline

**Date**: 2026-02-13
**Source**: rrr: thai-legal-rag-ocr-pipeline

## 1. Gemini YAML Frontmatter Defense

Gemini บางครั้ง output YAML fields เป็น `    - key: value` (list item) แทน `key: value` (flat)
ใน YAML frontmatter block (ระหว่าง `---`)

**Fix**: `_fix_frontmatter()` regex ก่อน parse:
```python
re.sub(r"^\s*-\s+(?=[a-zA-Z_]+:)", "", line)
```

## 2. LLM Verbatim Extraction

เมื่อต้องการ verbatim copy ต้อง explicit มากๆ:
- ไม่พอ: "copy ข้อความ verbatim"
- พอ: "คัดลอกออกมาทั้งหมด ห้ามสรุป ห้ามตัด ห้ามอ้างอิงว่า 'ตามที่กล่าวข้างต้น' ต้องคัดลอกข้อความจริงออกมาทั้งหมด"

## 3. google.genai SDK (v1.63.0) Patterns

Migration จาก `google.generativeai` → `google.genai`:

```python
# เดิม
import google.generativeai as genai
genai.configure(api_key=key)
result = genai.embed_content(model=m, content=text)
embedding = result["embedding"]

# ใหม่
from google import genai
client = genai.Client(api_key=key)
result = client.models.embed_content(model=m, contents=[text])
embedding = result.embeddings[0].values  # list of objects, .values attribute
```

Multi-embed (batch):
```python
result = client.models.embed_content(model=m, contents=texts)
embeddings = [e.values for e in result.embeddings]  # list of lists
```

## 4. Codespace + Google OAuth2

OAuth2 InstalledAppFlow OOB flow deprecated ตั้งแต่ 2022 ใช้ไม่ได้
Workaround ที่ดีที่สุดสำหรับ Codespace pipeline:
- ให้ user auth ใน local machine แล้ว copy `token.json` ขึ้น Codespace
- หรือใช้ Service Account (ไม่ต้องการ browser) ดีกว่า OAuth2 สำหรับ server-side

## 5. Gemini File API vs Page-by-Page

Gemini File API (`client.files.upload(pdf_bytes)`) + ส่ง whole PDF ดีกว่า
convert ทีละหน้าเป็น PNG มาก เพราะ:
- Gemini เข้าใจ document structure ข้ามหน้า
- ไม่ต้อง render image (ประหยัด dependency PyMuPDF)
- ความแม่นยำสูงกว่ามาก สำหรับ Thai government legal documents
