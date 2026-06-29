#!/usr/bin/env python3
"""
Structure a LOCAL verbatim court-judgment OCR into the ref_sac_* MD format.

Adapter around extract_ac_judgments.EXTRACT_PROMPT for files that are NOT yet
on Google Drive (e.g. PDFs downloaded straight from the court site). Reads a
local *_ocr_v4.md verbatim file, sends it to Gemini, and writes structured MD
with YAML frontmatter to the output path.

file_id can be a placeholder (e.g. "PENDING") — patch later with
patch_from_drive.py / patch_file_ids.py once the PDF is uploaded to Drive.

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/structure_local_judgments.py \
        --verbatim ~/Downloads/sac_judgment_o_7_2569_ocr_v4.md \
        --original-filename ref_sac_o_7_2569.pdf \
        --file-id PENDING \
        --out data/md_backup/ref_sac_o_7_2569.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import GEMINI_FLASH_MODEL
from src.gemini_client import get_client
from pipeline.extract_ac_judgments import EXTRACT_PROMPT


def structure(verbatim_text: str, filename: str, file_id: str) -> str:
    client = get_client()
    prompt = EXTRACT_PROMPT.format(
        filename=filename,
        file_id=file_id,
        content=verbatim_text[:60000],
    )
    resp = client.models.generate_content(model=GEMINI_FLASH_MODEL, contents=prompt)
    text = resp.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbatim", required=True, help="Path to local *_ocr_v4.md verbatim file")
    ap.add_argument("--original-filename", required=True, help="Canonical ref_sac_*.pdf name")
    ap.add_argument("--file-id", default="PENDING", help="Drive file_id (or PENDING placeholder)")
    ap.add_argument("--out", required=True, help="Output MD path (usually data/md_backup/ref_sac_*.md)")
    args = ap.parse_args()

    verbatim = Path(args.verbatim).read_text(encoding="utf-8")
    structured = structure(verbatim, args.original_filename, args.file_id)

    out = Path(args.out)
    out.write_text(structured + "\n", encoding="utf-8")
    print(f"✅ Wrote {out}  ({len(structured):,} chars)")


if __name__ == "__main__":
    main()
