# Section Files + Cache Patterns

**Date**: 2026-02-14
**Source**: Session — per-section MD files + Gemini วรรค splitting

---

## 1. Belt-and-Suspenders สำหรับ Cached Processing

เมื่อ pipeline มี cache layer (JSON) ที่เก็บ processed data:
- Cache อาจถูก generate ก่อน processing logic จะสมบูรณ์
- การ re-apply processing ตอน read-time (เช่น `_strip_page_headers` ใน `_build_section_md`) ปลอดภัยกว่าการเชื่อ cache
- Pattern: **"process at write AND at read"** สำหรับ transformations ที่ idempotent

---

## 2. Gemini สำหรับ Semantic Boundary Detection ใน Thai Legal

Thai legal paragraph (วรรค) boundaries ไม่มี lexical marker ที่ reliable:
- PyMuPDF extract text จาก PDF ราชกิจจาฯ โดยไม่ใส่ blank lines ระหว่างวรรค
- Heuristic regex จับได้แค่บาง pattern (ชื่อ authority, list items)
- **Gemini Flash เป็น correct tool** สำหรับ semantic paragraph detection
- Implementation: fallback เฉพาะเมื่อ blank-line split ได้ 1 วรรค + content ≥ 300 chars

---

## 3. Per-Section Intermediate Cache Pattern

สำหรับ document processing pipeline ที่มี human review:
```
full_doc.md (source of truth)
    ↓ auto-generate
sections/ (intermediate cache, regenerable)
    ├── มาตรา_001.md  ← YAML frontmatter + context header + text
    └── ...
```
- ไฟล์ section แต่ละไฟล์มี YAML frontmatter สำหรับ metadata
- Context header ช่วย embedding มี signal ของ law + chapter
- `regenerate_sections.py` ให้ rebuild จาก JSON cache โดยไม่ต้อง re-OCR

---

## 4. Thai Filename Diacritics บน Linux

- `ข้อ_001.md` (มี diacritic) ทำงานได้บน Linux/macOS filesystems ปกติ
- ควร explicit กับ user ถ้าเลือก encoding แบบใดแบบหนึ่ง อย่า silently simplify
