#!/usr/bin/env python3
"""
Extract structured MD from AC court judgment verbatim OCR files.

Workflow:
1. List MD files from AC_MD Drive folder
2. Match with PDF file_id from AC Drive folder
3. Send verbatim MD to Gemini for structured extraction
4. Save to data/md_backup/ with proper YAML frontmatter

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data_with_ac python3 pipeline/extract_ac_judgments.py --limit 1
    THAI_RAG_DATA_DIR=$(pwd)/data_with_ac python3 pipeline/extract_ac_judgments.py --all
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.config import MD_BACKUP_DIR, GEMINI_FLASH_MODEL
from src.gemini_client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FOLDER_AC_PDF = "1rp6NpjST7WFuHASlha6r4GykVWb7MCvH"
FOLDER_AC_MD  = "1Ek3E_ykOI3iBnPjZHlSfP1gKtpfGbC6i"

EXTRACT_PROMPT = """
คุณเป็นผู้เชี่ยวชาญกฎหมายปกครองของไทย

ข้อความด้านล่างคือคำพิพากษา/คำสั่งศาลปกครองแบบคำต่อคำ
กรุณาสกัดข้อมูลและจัดโครงสร้างใหม่ในรูปแบบ Markdown ตามที่กำหนด

**รูปแบบที่ต้องการ (YAML frontmatter + Markdown sections):**

```
---
original_filename: {filename}
doc_type: "คำพิพากษา"
issued_by: "ศาลปกครอง"
date: "YYYY-MM-DD"
date_be: "YYYY-MM-DD"
doc_number: "เลขคดี เช่น อ. 774/2564"
title: "ชื่อคดี/เรื่อง verbatim"
topic: "หมวดหมู่หลัก เช่น ค่าปรับ | การบอกเลิกสัญญา | การตรวจรับงาน"
subtopic: "หมวดย่อย"
court: "ชื่อศาล เช่น ศาลปกครองสูงสุด"
laws_referenced: ["กฎหมาย มาตรา/ข้อที่อ้างอิงหลัก (ไม่เกิน 5 รายการสำคัญ)"]
quality: "good"
quality_note: ""
file_id: "{file_id}"
file_url: "https://drive.google.com/file/d/{file_id}/view"
---

## สรุปข้อวินิจฉัยและแนวปฏิบัติ
[สรุปกระชับ 3-6 ประโยค: ประเด็นที่ศาลวินิจฉัย + หลักที่ได้ + แนวปฏิบัติที่นำไปใช้ได้ในทางราชการ]

## ประเด็นที่วินิจฉัย
[ระบุประเด็นหลักที่ศาลต้องวินิจฉัย เป็นข้อๆ]

## ข้อวินิจฉัย
[เหตุผลและหลักกฎหมายที่ศาลใช้ตัดสิน — คัดเฉพาะส่วนสำคัญ ไม่ต้องทั้งหมด
รวมถึงข้อต่อสู้สำคัญที่ศาลยกไม่รับ พร้อมเหตุผลที่ยก เช่น "ศาลยกข้อต่อสู้ที่ว่า... เพราะ..."]

## ข้อเท็จจริงโดยย่อ
[สรุปข้อเท็จจริงของคดี 3-5 ประโยค พอให้เข้าใจบริบท]
```

**กฎ:**
- date ใช้ปี ค.ศ. (CE), date_be ใช้ปี พ.ศ. (BE = CE+543)
- สรุปข้อวินิจฉัยและแนวปฏิบัติ ต้องเน้น "เอาไปใช้ได้อะไร" ไม่ใช่แค่สรุปคดี
- ถ้าเป็นคำสั่ง (ไม่ใช่คำพิพากษา) ให้ปรับ doc_type เป็น "คำสั่ง"
- ข้อต่อสู้ที่ศาลยกซึ่งมีนัยสำคัญทางกฎหมาย (เช่น ยกการนำกฎหมายผิดฉบับมาใช้, ยกข้อกำหนดในสัญญาที่ขัดกฎหมาย) ต้องปรากฏใน ข้อวินิจฉัย และ สรุปข้อวินิจฉัยและแนวปฏิบัติ ด้วย
- ตอบเฉพาะ Markdown ที่กำหนด ไม่ต้องมีคำอธิบายเพิ่มเติม

---

**เอกสาร:**
{content}
"""


def _drive_service():
    import os
    token_path = os.environ.get(
        "GOOGLE_TOKEN_JSON",
        str(Path.home() / "gnim-oracle/ψ/lab/sample-docs/token.json"),
    )
    creds = Credentials.from_authorized_user_file(token_path)
    return build("drive", "v3", credentials=creds)


def list_all_files(service, folder_id: str) -> dict[str, str]:
    """Returns {name: file_id} for all files in folder."""
    files = {}
    page_token = None
    while True:
        r = service.files().list(
            q=f"'{folder_id}' in parents",
            pageSize=200,
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
        ).execute()
        for f in r.get("files", []):
            files[f["name"]] = f["id"]
        page_token = r.get("nextPageToken")
        if not page_token:
            break
    return files


def download_text(service, file_id: str) -> str:
    req = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    dl = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return fh.getvalue().decode("utf-8")


def extract_structure(verbatim_text: str, filename: str, pdf_file_id: str) -> str:
    """Send verbatim MD to Gemini and get structured MD back."""
    client = get_client()
    prompt = EXTRACT_PROMPT.format(
        filename=filename,
        file_id=pdf_file_id,
        content=verbatim_text[:60000],  # ~60K chars ≈ 20+ pages
    )
    response = client.models.generate_content(
        model=GEMINI_FLASH_MODEL,
        contents=prompt,
    )
    text = response.text.strip()
    # ลบ ```markdown wrapper ถ้ามี
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1, help="Number of files to process")
    parser.add_argument("--all", action="store_true", help="Process all matched files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--file", type=str, help="Process a specific file by MD name (e.g. ref_sac_o_2120_2559.md)")
    args = parser.parse_args()

    service = _drive_service()

    logger.info("Listing files in AC and AC_MD...")
    pdf_files = list_all_files(service, FOLDER_AC_PDF)
    md_files  = list_all_files(service, FOLDER_AC_MD)

    # หาไฟล์ที่ match
    matched = []
    for md_name, md_id in md_files.items():
        pdf_name = md_name.replace(".md", ".pdf")
        if pdf_name in pdf_files:
            matched.append((md_name, md_id, pdf_name, pdf_files[pdf_name]))

    logger.info(f"Matched: {len(matched)} files")

    if args.file:
        matched = [(md, mi, pf, pi) for md, mi, pf, pi in matched if md == args.file]
        if not matched:
            logger.error(f"File not found in matched list: {args.file}")
            sys.exit(1)
    else:
        limit = len(matched) if args.all else args.limit
        matched = matched[:limit]

    for md_name, md_id, pdf_name, pdf_id in matched:
        out_path = MD_BACKUP_DIR / md_name
        if out_path.exists() and not args.force:
            logger.info(f"Already exists, skipping: {md_name}")
            continue

        logger.info(f"Processing: {md_name}")
        try:
            verbatim = download_text(service, md_id)
            structured = extract_structure(verbatim, pdf_name, pdf_id)

            out_path.write_text(structured, encoding="utf-8")
            logger.info(f"Saved: {out_path}")
        except Exception as e:
            logger.error(f"Failed {md_name}: {e}")
            continue

        time.sleep(1)  # rate limit


if __name__ == "__main__":
    main()
