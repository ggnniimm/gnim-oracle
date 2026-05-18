---
name: ocr-classifier-misroute-large-pdf-timeout
description: Flash OCR classifier misroutes ข้อหารือ เป็น Circular เมื่อเห็น "ว" ในลายมือเลือน + PDF >1MB timeout ต้องใช้ per_page
metadata:
  type: project
---

## Facts

### 1. OCR Classifier misroutes ข้อหารือ → Circular

Flash classifier ใช้ rule: "ถ้าเลขหนังสือมี ว → Circular" — ปกติถูก แต่ถ้าลายมือเขียนเลือน OCR อ่านเลขผิดเป็น "ว XXX" จะ misclassify ข้อหารือเป็นหนังสือเวียน ใช้ template ผิด ผลลัพธ์ขาดหัวข้อ ข้อเท็จจริง/ประเด็นข้อหารือ/ข้อวินิจฉัย

**Fix**: bypass `pdf_to_markdown()` เรียก `extract()` โดยตรงพร้อม `doc_type="Ruling_Committee"`

```python
from src.ingestion.ocr import extract, generate_anchor, _inject_frontmatter_fields, ...
text = extract(pdf_bytes, file_id=file_id, filename=filename, doc_type="Ruling_Committee")
```

**Why:** `pdf_to_markdown()` ไม่มี parameter override doc_type — ต้อง call internal functions ตรง

### 2. PDF >1MB → 504 DEADLINE_EXCEEDED บน gemini-2.5-pro

Single-call streaming timeout สำหรับ PDF ใหญ่ (ทดสอบที่ 1587 KB)

**Fix**: `per_page=True, page_delay=10.0`

```python
text = extract(pdf_bytes, ..., per_page=True, page_delay=10.0)
```

**How to apply:**
- PDF < 1MB → single call ปกติ
- PDF > 1MB หรือ > ~5 หน้า → per_page=True
- กวจ_ว189 (1587 KB, หลายหน้า) failed single → passed per_page

**Why:** Pro streaming มี deadline cutoff, per_page แบ่ง PDF เป็นหน้าๆ แต่ละ call เล็กลง

Related: [[verify-before-act]]
