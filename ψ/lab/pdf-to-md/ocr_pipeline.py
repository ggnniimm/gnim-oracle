#!/usr/bin/env python3
"""
Thai Legal PDF → MD Pipeline
Google Drive PDF → Gemini Flash OCR → Markdown + metadata

Usage:
    # Single file
    python ocr_pipeline.py --drive-id FILE_ID --output output.md

    # Batch from CSV (columns: drive_id, filename, doc_type, issued_by, topic)
    python ocr_pipeline.py --batch files.csv --output-dir ./output/

    # Dry run (show what would be processed)
    python ocr_pipeline.py --batch files.csv --dry-run

Requirements:
    pip install google-generativeai google-auth google-api-python-client pyyaml
    export GEMINI_API_KEY=...
    export GOOGLE_SERVICE_ACCOUNT_JSON=path/to/service_account.json  # optional, for Drive API
"""

import os
import sys
import csv
import json
import time
import argparse
import base64
from datetime import date
from pathlib import Path
from typing import Optional
import tempfile

import yaml
import google.generativeai as genai


# ─── Config ───────────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-2.0-flash"
RATE_LIMIT_DELAY = 1.0  # seconds between requests (free tier: 15 RPM)
MAX_RETRIES = 3

OCR_SYSTEM_PROMPT = """คุณเป็น OCR specialist สำหรับเอกสารราชการไทย

งานของคุณ:
1. แปลงเนื้อหา PDF เป็น Markdown ที่อ่านได้
2. รักษาโครงสร้างเดิม: หัวข้อ, ย่อหน้า, รายการ, ตาราง
3. แก้คำที่ OCR อาจผิดพลาด โดยอาศัยบริบทกฎหมาย
4. ใช้ตัวเลขอารบิกแทนเลขไทยในส่วนที่เป็นมาตรา/ข้อ (เช่น "มาตรา 56" ไม่ใช่ "มาตรา ๕๖")
5. ไม่เพิ่มเนื้อหาที่ไม่มีในเอกสาร

รูปแบบ Output:
- ใช้ # สำหรับหัวข้อหลัก, ## สำหรับหัวข้อรอง
- ใช้ - สำหรับรายการ
- ใช้ | สำหรับตาราง (Markdown table format)
- เว้นบรรทัดระหว่างย่อหน้า

สิ่งที่ต้องระบุท้ายเอกสาร (JSON block):
```json
{
  "extracted_metadata": {
    "doc_number": "เลขที่หนังสือ หรือ null",
    "date_be": "ปีพ.ศ. หรือ null",
    "date_full_be": "ปีพ.ศ.-เดือน-วัน หรือ null",
    "laws_referenced": ["รายการกฎหมายที่อ้างถึง"],
    "sections_referenced": ["มาตรา/ข้อที่อ้างถึง"],
    "summary": "สรุป 1-2 ประโยค ว่าเอกสารนี้เกี่ยวกับอะไร"
  }
}
```"""


# ─── Drive Download ────────────────────────────────────────────────────────────

def download_from_drive(drive_id: str, dest_path: str) -> bool:
    """Download PDF from Google Drive using direct URL (public files) or Drive API."""

    # Try direct download first (works for publicly shared files)
    import urllib.request
    url = f"https://drive.google.com/uc?export=download&id={drive_id}"

    try:
        urllib.request.urlretrieve(url, dest_path)
        # Check if we got a real PDF (not an HTML confirmation page)
        with open(dest_path, 'rb') as f:
            header = f.read(4)
        if header == b'%PDF':
            return True
        # Large files need confirmation token
        return _download_large_drive_file(drive_id, dest_path)
    except Exception as e:
        print(f"  Direct download failed: {e}", file=sys.stderr)
        return False


def _download_large_drive_file(drive_id: str, dest_path: str) -> bool:
    """Handle Google Drive's virus scan confirmation for large files."""
    import urllib.request
    import urllib.parse
    import http.cookiejar

    session_opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    # First request to get confirmation token
    url = f"https://drive.google.com/uc?export=download&id={drive_id}"
    response = session_opener.open(url)
    html = response.read().decode('utf-8', errors='replace')

    # Extract confirm token
    import re
    token_match = re.search(r'confirm=([0-9A-Za-z_]+)', html)
    if not token_match:
        return False

    confirm_url = f"https://drive.google.com/uc?export=download&confirm={token_match.group(1)}&id={drive_id}"

    with session_opener.open(confirm_url) as response:
        with open(dest_path, 'wb') as f:
            f.write(response.read())

    with open(dest_path, 'rb') as f:
        return f.read(4) == b'%PDF'


# ─── Gemini OCR ────────────────────────────────────────────────────────────────

def ocr_pdf_with_gemini(pdf_path: str, model) -> Optional[dict]:
    """Send PDF to Gemini Flash and get back markdown + extracted metadata."""

    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content([
                OCR_SYSTEM_PROMPT,
                {
                    "inline_data": {
                        "mime_type": "application/pdf",
                        "data": pdf_b64
                    }
                },
                "แปลงเอกสาร PDF นี้เป็น Markdown และ extract metadata ตามรูปแบบที่กำหนด"
            ])

            text = response.text

            # Split markdown content and JSON metadata
            md_content = text
            extracted_meta = {}

            # Find and parse the JSON block at the end
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                try:
                    meta_block = json.loads(json_match.group(1))
                    extracted_meta = meta_block.get("extracted_metadata", {})
                    # Remove the JSON block from markdown content
                    md_content = text[:json_match.start()].strip()
                except json.JSONDecodeError:
                    pass

            return {
                "markdown": md_content,
                "extracted_meta": extracted_meta
            }

        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # exponential backoff

    return None


# ─── Build Final MD ────────────────────────────────────────────────────────────

def build_md_with_frontmatter(
    markdown_content: str,
    extracted_meta: dict,
    user_meta: dict,  # from CSV or CLI args
    drive_id: str,
    original_filename: str,
    page_count: int = 0
) -> str:
    """Combine OCR output + metadata into final MD with YAML frontmatter."""

    # Merge metadata: user_meta takes priority over extracted
    title = user_meta.get("title") or extracted_meta.get("summary", "")[:80] or original_filename

    frontmatter = {
        "title": title,
        "doc_type": user_meta.get("doc_type", "ข้อหารือ"),
        "issued_by": user_meta.get("issued_by", ""),
        "doc_number": extracted_meta.get("doc_number") or user_meta.get("doc_number", ""),
        "date_be": extracted_meta.get("date_be") or user_meta.get("date_be", ""),
        "date_full_be": extracted_meta.get("date_full_be") or user_meta.get("date_full_be", ""),
        "topic": user_meta.get("topic", "การจัดซื้อจัดจ้าง"),
        "subtopic": user_meta.get("subtopic", ""),
        "laws_referenced": extracted_meta.get("laws_referenced", []),
        "sections_referenced": extracted_meta.get("sections_referenced", []),
        "source_drive": f"https://drive.google.com/file/d/{drive_id}/view",
        "original_filename": original_filename,
        "page_count": page_count,
        "ocr_engine": GEMINI_MODEL,
        "ocr_date": date.today().isoformat(),
        "status": "active",
        "quality": "review-needed" if not markdown_content.strip() else "good",
    }

    # Add summary as subtopic if empty
    if not frontmatter["subtopic"] and extracted_meta.get("summary"):
        frontmatter["subtopic"] = extracted_meta["summary"][:200]

    yaml_str = yaml.dump(
        frontmatter,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False
    )

    drive_link = frontmatter["source_drive"]
    footer = f"\n\n---\n\n*OCR โดย {GEMINI_MODEL} | วันที่ {frontmatter['ocr_date']} | ต้นฉบับ: [Google Drive]({drive_link})*"

    return f"---\n{yaml_str}---\n\n{markdown_content}{footer}\n"


# ─── Single File Processing ────────────────────────────────────────────────────

def process_single(
    drive_id: str,
    output_path: str,
    user_meta: dict,
    model,
    original_filename: str = ""
) -> bool:
    """Process one PDF from Drive → MD."""

    if not original_filename:
        original_filename = f"{drive_id}.pdf"

    print(f"Processing: {original_filename} ({drive_id})")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Download
        print(f"  Downloading from Drive...", end=" ", flush=True)
        if not download_from_drive(drive_id, tmp_path):
            print("FAILED")
            return False
        print("OK")

        # Get page count
        page_count = _get_pdf_page_count(tmp_path)

        # OCR
        print(f"  OCR with Gemini ({page_count} pages)...", end=" ", flush=True)
        result = ocr_pdf_with_gemini(tmp_path, model)
        if not result:
            print("FAILED")
            return False
        print("OK")

        # Build final MD
        final_md = build_md_with_frontmatter(
            result["markdown"],
            result["extracted_meta"],
            user_meta,
            drive_id,
            original_filename,
            page_count
        )

        # Write output
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_md)

        print(f"  Saved: {output_path}")
        return True

    finally:
        os.unlink(tmp_path)


def _get_pdf_page_count(pdf_path: str) -> int:
    """Quick page count without heavy dependencies."""
    try:
        import struct
        with open(pdf_path, 'rb') as f:
            content = f.read()
        count = content.count(b'/Page\n') + content.count(b'/Page\r') + content.count(b'/Page ')
        return max(count, 1)
    except Exception:
        return 0


# ─── Batch Processing ─────────────────────────────────────────────────────────

def process_batch(csv_path: str, output_dir: str, model, dry_run: bool = False):
    """
    Process multiple files from a CSV.

    CSV format (with header):
    drive_id,filename,doc_type,issued_by,topic,subtopic,date_be,title

    Minimal CSV (only drive_id required):
    drive_id
    """

    output_dir = Path(output_dir)
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Progress tracking
    log_path = output_dir / "batch_log.csv"
    processed = set()
    if log_path.exists() and not dry_run:
        with open(log_path, 'r') as f:
            for row in csv.DictReader(f):
                if row.get("status") == "ok":
                    processed.add(row["drive_id"])

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Batch: {len(rows)} files, {len(processed)} already done")

    if dry_run:
        for row in rows:
            print(f"  [DRY] {row.get('filename', row['drive_id'])}")
        return

    log_entries = []
    success = 0
    failed = 0
    skipped = 0

    for i, row in enumerate(rows, 1):
        drive_id = row["drive_id"].strip()

        if drive_id in processed:
            print(f"[{i}/{len(rows)}] SKIP (already done): {drive_id}")
            skipped += 1
            continue

        filename = row.get("filename", f"{drive_id}.pdf").strip()
        output_filename = Path(filename).stem + ".md"
        output_path = output_dir / output_filename

        user_meta = {k: v.strip() for k, v in row.items() if k != "drive_id" and v}

        print(f"[{i}/{len(rows)}] ", end="")
        ok = process_single(drive_id, str(output_path), user_meta, model, filename)

        log_entries.append({
            "drive_id": drive_id,
            "filename": filename,
            "output": str(output_path),
            "status": "ok" if ok else "failed",
            "timestamp": date.today().isoformat()
        })

        if ok:
            success += 1
            # Append to log immediately (resume safety)
            with open(log_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["drive_id", "filename", "output", "status", "timestamp"])
                if not log_path.stat().st_size:
                    writer.writeheader()
                writer.writerow(log_entries[-1])
        else:
            failed += 1

        # Rate limiting
        if i < len(rows):
            time.sleep(RATE_LIMIT_DELAY)

    print(f"\nDone: {success} ok, {failed} failed, {skipped} skipped")
    print(f"Log: {log_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Thai Legal PDF → MD Pipeline via Gemini Flash OCR"
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--drive-id", help="Google Drive file ID (single file)")
    mode.add_argument("--batch", metavar="CSV", help="CSV file for batch processing")

    parser.add_argument("--output", help="Output .md path (single file mode)")
    parser.add_argument("--output-dir", default="./output", help="Output directory (batch mode)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")

    # Metadata overrides (single file mode)
    parser.add_argument("--doc-type", default="ข้อหารือ")
    parser.add_argument("--issued-by", default="กวจ.")
    parser.add_argument("--topic", default="การจัดซื้อจัดจ้าง")
    parser.add_argument("--title", default="")
    parser.add_argument("--filename", default="", help="Original filename")

    args = parser.parse_args()

    # Init Gemini
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
    else:
        model = None

    if args.drive_id:
        # Single file mode
        output_path = args.output or f"{args.drive_id}.md"
        user_meta = {
            "doc_type": args.doc_type,
            "issued_by": args.issued_by,
            "topic": args.topic,
            "title": args.title,
        }
        ok = process_single(args.drive_id, output_path, user_meta, model, args.filename)
        sys.exit(0 if ok else 1)

    else:
        # Batch mode
        process_batch(args.batch, args.output_dir, model, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
