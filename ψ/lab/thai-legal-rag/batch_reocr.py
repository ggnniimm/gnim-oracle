#!/usr/bin/env python3
"""
Batch re-OCR for files with incomplete content.

Downloads PDF from Drive, splits into ~20-page chunks,
OCR each chunk via Gemini with a generic (non-structured) prompt,
combines all chunks, updates MD file, clears OCR cache.

Usage:
    cd ψ/lab/thai-legal-rag
    source ../../../.env  # or set GEMINI_API_KEY
    python3 batch_reocr.py
"""
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.0-flash"
CHUNK_SIZE = 20  # pages per chunk
DATA_DIR = Path(os.environ.get("THAI_RAG_DATA_DIR", "data"))
MD_BACKUP_DIR = DATA_DIR / "md_backup"

# Files to re-OCR: (file_id, page_count, md_filename)
FILES = [
    # Batch 1 (completed): ว647, ว196, ว1203, ว692, ว607, ว430
    # Batch 2 (remaining):
    ("1gKAW1UUvhF0dm53s8pC7T12Z1C74zAnF", 13, "กค_0433.4-ว_456_update621003.md"),
    ("17vo4FLNtcV4AKoUUVlstYqJEwogR_AuS", 24, "ว_239.md"),
    ("1JQiTMhQsoxMcE48i6S9A-NkzJ1noAD0N", 49, "การปรับปรุงบัญชีค่าแรงงานดำเนินการสำหรับถอดแบบคำนวณราคากลางงานก่อสร้าง.md"),
]

# Generic OCR prompt — captures ALL content, not just ข้อหารือ structure
GENERIC_OCR_PROMPT = """คุณเป็น OCR engine สำหรับเอกสารราชการไทย

คัดลอกข้อความทั้งหมดในเอกสาร PDF นี้ออกมาเป็น Markdown อย่างครบถ้วน

กฎ:
- คัดลอก verbatim ทุกข้อความ ทุกหน้า — ห้ามสรุป ห้ามตัด ห้ามข้าม
- รักษาโครงสร้างหัวข้อ ข้อย่อย ลำดับเลข ตาราง
- ใช้ markdown heading (#, ##, ###) ตามลำดับชั้นของเอกสาร
- ตารางให้ใช้ markdown table format
- ถ้ามีรูปภาพ/แผนภูมิ ให้อธิบายสั้นๆ ว่า [รูป: ...]
- ถ้ามีแบบฟอร์ม ให้คัดลอกทุกช่อง ทุกหัวข้อ
- Output raw Markdown — ไม่ต้องใส่ code fences (```)
- คัดลอกทุกหน้าตั้งแต่หน้าแรกถึงหน้าสุดท้าย
"""


def download_pdf(file_id: str) -> bytes:
    """Download PDF from Google Drive using the project's drive.py."""
    sys.path.insert(0, ".")
    from src.ingestion.drive import stream_pdf
    return stream_pdf(file_id)


def split_pdf(pdf_bytes: bytes, chunk_size: int = CHUNK_SIZE) -> list[bytes]:
    """Split PDF into chunks of chunk_size pages."""
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    total = len(reader.pages)
    chunks = []
    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        writer = pypdf.PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        chunks.append(buf.getvalue())
        print(f"    chunk {len(chunks)}: pages {start+1}-{end}")
    return chunks


def ocr_chunk(chunk_bytes: bytes, chunk_num: int, total_chunks: int, retries: int = 3) -> str:
    """OCR a single PDF chunk via Gemini."""
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Upload PDF chunk
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(chunk_bytes)
        tmp_path = tmp.name

    try:
        uploaded = client.files.upload(
            file=tmp_path,
            config={"mime_type": "application/pdf", "display_name": f"chunk_{chunk_num}.pdf"},
        )
        while uploaded.state.name == "PROCESSING":
            time.sleep(1)
            uploaded = client.files.get(name=uploaded.name)

        for attempt in range(retries):
            try:
                response = client.models.generate_content_stream(
                    model=MODEL,
                    contents=[GENERIC_OCR_PROMPT, uploaded],
                )
                text = ""
                for part in response:
                    if part.text:
                        text += part.text

                # Strip code fences
                text = text.strip()
                if text.startswith("```"):
                    lines = text.splitlines()
                    lines = lines[1:] if lines[0].startswith("```") else lines
                    lines = lines[:-1] if lines and lines[-1].startswith("```") else lines
                    text = "\n".join(lines).strip()

                chars = len(text)
                print(f"    chunk {chunk_num}/{total_chunks}: {chars:,} chars")
                if chars < 100 and attempt < retries - 1:
                    print(f"    ⚠ too short, retrying ({attempt+1}/{retries})...")
                    time.sleep(2)
                    continue
                return text
            except Exception as e:
                print(f"    ⚠ chunk {chunk_num} attempt {attempt+1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(5)
                else:
                    return f"[OCR ERROR chunk {chunk_num}: {e}]"
        return ""
    finally:
        os.unlink(tmp_path)
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass


def extract_frontmatter(md_text: str) -> str:
    """Extract YAML frontmatter from existing MD file."""
    lines = md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end == -1:
        return ""
    return "\n".join(lines[:end+1])


def process_file(file_id: str, page_count: int, md_filename: str) -> dict:
    """Full re-OCR pipeline for one file."""
    md_path = MD_BACKUP_DIR / md_filename
    print(f"\n{'='*60}")
    print(f"📄 {md_filename}")
    print(f"   file_id: {file_id}")
    print(f"   pages: {page_count}")

    # Read existing frontmatter
    existing_frontmatter = ""
    if md_path.exists():
        existing_text = md_path.read_text(encoding="utf-8")
        existing_frontmatter = extract_frontmatter(existing_text)
        old_chars = len(existing_text)
        print(f"   existing: {old_chars:,} chars")

    # Download PDF
    print("   ⬇ downloading PDF...")
    pdf_bytes = download_pdf(file_id)
    print(f"   PDF size: {len(pdf_bytes):,} bytes")

    # Split into chunks
    print(f"   ✂ splitting into ~{CHUNK_SIZE}-page chunks...")
    chunks = split_pdf(pdf_bytes, CHUNK_SIZE)
    print(f"   {len(chunks)} chunks")

    # OCR each chunk
    print("   🔍 OCR'ing chunks...")
    all_text = []
    for i, chunk in enumerate(chunks, 1):
        text = ocr_chunk(chunk, i, len(chunks))
        all_text.append(text)
        time.sleep(1)  # rate limit courtesy

    # Combine
    combined = "\n\n---\n\n".join(all_text)

    # Reconstruct MD with frontmatter
    if existing_frontmatter:
        final_md = existing_frontmatter + "\n\n" + combined
    else:
        final_md = combined

    new_chars = len(final_md)
    print(f"   ✅ total: {new_chars:,} chars (was {old_chars:,})")

    # Write MD
    md_path.write_text(final_md, encoding="utf-8")
    print(f"   💾 saved: {md_path}")

    # Clear OCR cache so pipeline won't use stale version
    import hashlib
    cache_dir = DATA_DIR / "ocr_cache"
    h = hashlib.sha256(file_id.encode()).hexdigest()[:16]
    cache_path = cache_dir / f"{h}.json"
    if cache_path.exists():
        cache_path.unlink()
        print(f"   🗑 cleared cache: {cache_path.name}")

    return {
        "filename": md_filename,
        "old_chars": old_chars,
        "new_chars": new_chars,
        "chunks": len(chunks),
        "ratio": new_chars / max(old_chars, 1),
    }


def main():
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not set. Run: source ../../../.env")
        sys.exit(1)

    print("🚀 Batch re-OCR — 9 files with incomplete content")
    print(f"   Model: {MODEL}")
    print(f"   Chunk size: {CHUNK_SIZE} pages")

    results = []
    for file_id, page_count, md_filename in FILES:
        try:
            result = process_file(file_id, page_count, md_filename)
            results.append(result)
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            results.append({"filename": md_filename, "error": str(e)})

    # Summary
    print(f"\n{'='*60}")
    print("📊 Summary")
    print(f"{'='*60}")
    total_old = 0
    total_new = 0
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['filename']}: {r['error']}")
        else:
            total_old += r["old_chars"]
            total_new += r["new_chars"]
            print(f"  ✅ {r['filename']}: {r['old_chars']:,} → {r['new_chars']:,} ({r['ratio']:.1f}x)")

    print(f"\n  Total: {total_old:,} → {total_new:,} chars ({total_new/max(total_old,1):.1f}x improvement)")
    print(f"\n  Next: re-index with")
    print(f"    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/index_md_folder.py --dir data/md_backup")


if __name__ == "__main__":
    main()
