# ade-python Learning Index

## Source
- **Origin**: ./origin/
- **GitHub**: https://github.com/landing-ai/ade-python

## Explorations

### 2026-02-12 02:04 (default — 3 agents)
- [Architecture](2026-02-12/0204_ARCHITECTURE.md)
- [Code Snippets](2026-02-12/0204_CODE-SNIPPETS.md)
- [Quick Reference](2026-02-12/0204_QUICK-REFERENCE.md)

**Key insights**:
1. SDK ถูก generate จาก OpenAPI spec ด้วย Stainless — ครบ type-safe ทั้ง sync/async
2. Workflow หลัก: `parse()` → Markdown → `extract(schema)` หรือ `split(classes)`
3. สำหรับไฟล์ใหญ่ต้องใช้ `parse_jobs` (async jobs) ไม่ใช่ `parse()` ตรงๆ
4. `pydantic_to_json_schema()` แปลง Pydantic model เป็น JSON schema ที่ API รับได้
