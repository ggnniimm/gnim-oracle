#!/usr/bin/env python3
"""OCR 4 new May 2026 CGD files from Drive → md_backup."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.drive import stream_pdf
from src.ingestion.ocr import pdf_to_markdown

MD_BACKUP = Path("data/md_backup")

TARGET_FILES = [
    {
        "file_id": "1dmqF8DZX6C_su9_wFZUX5ZT1vEpkGdC_",
        "filename": "01_กวจ_8938_110369_ข้อหารือแนวทางปฏิบัติประกอบหนังสือคณะกรรมการวินิจฉัยฯ+PDPA.pdf",
    },
    {
        "file_id": "1ANWxlC82_sM0jEbXcPDCcK0deapfaPKL",
        "filename": "01_กวจ_8168_050369_ข้อหารือเกี่ยวกับการพิจารณางดค่าปรับของงานจ้างก่อสร้างฯ+PDPA.pdf",
    },
    {
        "file_id": "1MCdRrcHUeaBs4DJaHBEqUFKylmQyKNLL",
        "filename": "01_กวจ_6673_190269_ข้อหารือการงดค่าปรับงานก่อสร้างเหตุจากให้ใช้กฎอัยการศึกฯ+PDPA.pdf",
    },
    {
        "file_id": "1hhZYt5rrjQRldHCNXkr-rQG8UlPxZsNx",
        "filename": "01_กวจ_3460_300169_ข้อหารือปัญหาเกี่ยวกับการตีความและการปรับใช้บทบัญญัติแห่งกฎกระทรวง+PDPA.pdf",
    },
]

for item in TARGET_FILES:
    fid = item["file_id"]
    fname = item["filename"]
    out_md = MD_BACKUP / (Path(fname).stem + ".md")

    print(f"\n[{fname}]")
    if out_md.exists():
        print(f"  already exists: {out_md.name} — skipping")
        continue

    print(f"  Downloading from Drive...")
    pdf_bytes = stream_pdf(fid)
    print(f"  Downloaded {len(pdf_bytes):,} bytes. Running OCR...")

    result = pdf_to_markdown(pdf_bytes, file_id=fid, filename=fname, force=False, per_page=False)
    md_text = result["text"]

    out_md.write_text(md_text, encoding="utf-8")
    print(f"  Saved → {out_md.name}  ({len(md_text):,} chars, doc_type={result['doc_type']!r})")

print("\nDone.")
