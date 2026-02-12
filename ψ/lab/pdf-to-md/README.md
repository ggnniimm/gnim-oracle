# Thai Legal PDF → MD Pipeline

แปลง PDF เอกสารราชการไทย → Markdown + metadata สำหรับ RAG

## Architecture

```
Google Drive PDF
    ↓  download (direct URL หรือ Drive API)
    ↓  Gemini Flash OCR
    ↓  extract metadata อัตโนมัติ
    ↓  inject YAML frontmatter
    ↓
Markdown file พร้อม metadata
```

## Setup

```bash
pip install google-generativeai pyyaml
export GEMINI_API_KEY=your_key_here
```

## การใช้งาน

### Single file (ทดสอบ)

```bash
# ระบุ Drive file ID (จาก URL: /file/d/FILE_ID/view)
python ocr_pipeline.py \
  --drive-id 1AbCdEfGhIjKlMnOpQrStUvWxYz \
  --output output/test.md \
  --doc-type ข้อหารือ \
  --issued-by กวจ. \
  --topic "การจัดซื้อจัดจ้าง"
```

### Batch (~700 ไฟล์)

1. เตรียม CSV (ดู `batch_template.csv`):

```csv
drive_id,filename,doc_type,issued_by,topic,subtopic,date_be,title
1AbCdEf...,กวจ-001.pdf,ข้อหารือ,กวจ.,การจัดซื้อจัดจ้าง,ราคากลาง,2566,
```

2. Dry run ก่อน:

```bash
python ocr_pipeline.py --batch files.csv --dry-run
```

3. Run จริง:

```bash
python ocr_pipeline.py --batch files.csv --output-dir ./output/
```

### Resume ที่ค้างไว้

Script จะ skip ไฟล์ที่ทำไปแล้ว (บันทึกใน `batch_log.csv`) อัตโนมัติ

## Output Format

ทุกไฟล์จะมี YAML frontmatter:

```yaml
---
title: "..."
doc_type: "ข้อหารือ"
issued_by: "กวจ."
doc_number: "กวจ. 0405.2/ว 135"
date_be: "2566"
laws_referenced:
  - "พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560"
sections_referenced:
  - "มาตรา 56"
source_drive: "https://drive.google.com/file/d/FILE_ID/view"
ocr_engine: "gemini-2.0-flash"
status: "active"
quality: "good"
---
```

## Rate Limit

- Gemini Flash free tier: **15 RPM** (requests per minute)
- Script ใช้ 1 req/file + delay 1 วินาที
- 700 ไฟล์ ≈ 50 นาที (เสร็จในวันเดียว)

## Metadata ที่ Gemini Extract อัตโนมัติ

| Field | ตัวอย่าง |
|-------|---------|
| doc_number | กวจ. 0405.2/ว 135 |
| date_be | 2566 |
| date_full_be | 2566-01-15 |
| laws_referenced | พ.ร.บ. จัดซื้อฯ 2560 |
| sections_referenced | มาตรา 56 |
| summary | สรุป 1-2 ประโยค |

## Next Steps

- [ ] Ming upload ไฟล์ตัวอย่างมาที่ `../sample-docs/`
- [ ] ทดสอบ script กับ 5-10 ไฟล์
- [ ] Review quality (OCR accuracy, metadata accuracy)
- [ ] ปรับ prompt ถ้า quality ไม่ดี
- [ ] Batch run ทั้ง 700 ไฟล์
- [ ] Load MD files เข้า RAG (LightRAG + BGE-M3)

## Files

| File | Description |
|------|-------------|
| `ocr_pipeline.py` | Main pipeline script |
| `batch_template.csv` | CSV template สำหรับ batch |
| `../sample-docs/TEMPLATE.md` | MD template / ตัวอย่าง frontmatter |
