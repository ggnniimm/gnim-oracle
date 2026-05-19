#!/usr/bin/env python3
"""OCR 3 new May 2026 files from Drive → md_backup."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.drive import stream_pdf
from src.ingestion.ocr import pdf_to_markdown

MD_BACKUP = Path("data/md_backup")

TARGET_FILES = [
    {
        "file_id": "17VJxF-RvlVtcQJAYNFR5Y5BOezf9s4hU",
        "filename": "กวจ_58936_201262_สืบราคารายเดียว.pdf",
        "modified": "2026-05-16",
        "per_page": False,
    },
    {
        "file_id": "1Snj5O1yssqwmPu70NoakqsosLBlSudRm",
        "filename": "02_กวจ_ว299_270469_แนวทางปฏิบัติในการยื่นข้อเสนอโดยวิธีคัดเลือกและวิธีเฉพาะเจาะจงฯ.pdf",
        "modified": "2026-05-08",
        "per_page": True,
    },
    {
        "file_id": "1orhfV8VCCs3-jKe31nP6iwUTfwr_tO-c",
        "filename": "01_กวจ_ว298_270469_แนวทางปฏิบัติในการอุทธรณ์ผ่านระบบอิเล็กทรอนิกส์.pdf",
        "modified": "2026-05-08",
        "per_page": True,
    },
]

for item in TARGET_FILES:
    fid = item["file_id"]
    fname = item["filename"]
    out_md = MD_BACKUP / (Path(fname).stem + ".md")

    print(f"\n[{fname}]")
    if out_md.exists():
        print(f"  already exists: {out_md.name} — skipping (use force=True to re-OCR)")
        continue

    print(f"  Downloading from Drive...")
    pdf_bytes = stream_pdf(fid)
    print(f"  Downloaded {len(pdf_bytes):,} bytes. Running OCR...")

    per_page = item.get("per_page", False)
    result = pdf_to_markdown(pdf_bytes, file_id=fid, filename=fname, force=False, per_page=per_page)
    md_text = result["text"]

    out_md.write_text(md_text, encoding="utf-8")
    lines = md_text.count("\n")
    print(f"  Saved → {out_md.name}  ({len(md_text):,} chars, doc_type={result['doc_type']!r})")

print("\nDone.")
