#!/usr/bin/env python3
"""
Thai Legal RAG — Law Indexer

Processes all PDFs in the Drive "Law" folder:
  Download → Extract (PyMuPDF/Gemini) → Parse มาตรา/ข้อ → Chunk → Index

Usage:
    python batch_index_law.py
    python batch_index_law.py --dry-run
    python batch_index_law.py --no-lightrag
    python batch_index_law.py --force     # ignore cache, re-extract all
    python batch_index_law.py --file-id FILE_ID   # single file only

Requires:
    DRIVE_FOLDER_LAW=<folder_id>  in .env
"""
import argparse
import datetime
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm

from src.ingestion.drive import list_pdfs, stream_pdf
from src.ingestion.law_extractor import extract_law
from src.ingestion.chunker_law import chunk_law_document
from src.ingestion.dedup import is_indexed, mark_indexed, stats as dedup_stats
from src.indexing.manager import IndexManager
from src.config import FAILED_LOG_DIR, get_drive_folder_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="Index Thai law PDFs from Google Drive")
    p.add_argument("--dry-run", action="store_true", help="Show files/sections without indexing")
    p.add_argument("--no-lightrag", action="store_true", help="FAISS only (skip LightRAG)")
    p.add_argument("--force", action="store_true", help="Re-extract even if cached")
    p.add_argument("--file-id", help="Process a single file by Drive ID")
    return p.parse_args()


def main():
    args = parse_args()

    # ── List files ──────────────────────────────────────────────────────────
    try:
        folder_id = get_drive_folder_id("กฎหมาย")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(f"Listing PDFs in Law folder: {folder_id}")
    all_files = list_pdfs(folder_id)

    if args.file_id:
        all_files = [f for f in all_files if f["id"] == args.file_id]
        if not all_files:
            # Allow processing without listing if file_id provided directly
            all_files = [{"id": args.file_id, "name": f"{args.file_id}.pdf"}]

    logger.info(f"Found {len(all_files)} PDF(s)")

    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"DRY RUN — {len(all_files)} files")
        print(f"{'='*60}")
        for f in all_files:
            print(f"\n  [{f['id']}] {f['name']}")
            try:
                pdf_bytes = stream_pdf(f["id"])
                doc = extract_law(pdf_bytes, f["id"], f["name"], force=args.force)
                chunks = chunk_law_document(doc)
                print(f"    Sections: {doc.total_sections}")
                print(f"    Chunks:   {len(chunks)}")
                print(f"    OCR:      {doc.ocr_engine}")
                if chunks:
                    print(f"    Sample chunk[0]: {chunks[0].text[:120]}...")
            except Exception as e:
                print(f"    ERROR: {e}")
        return

    # ── Index ───────────────────────────────────────────────────────────────
    index = IndexManager(use_lightrag=not args.no_lightrag)
    failed: list[str] = []
    total_new = 0
    total_skip = 0

    for f in tqdm(all_files, desc="Law files"):
        file_id = f["id"]
        filename = f["name"]
        logger.info(f"Processing: {filename}")

        try:
            pdf_bytes = stream_pdf(file_id)
            doc = extract_law(pdf_bytes, file_id, filename, force=args.force)
            chunks = chunk_law_document(doc)

            new_texts, new_metas = [], []
            for chunk in chunks:
                if is_indexed(chunk.text):
                    total_skip += 1
                    continue
                new_texts.append(chunk.text)
                new_metas.append(chunk.metadata)

            if new_texts:
                index.add_batch(new_texts, new_metas)
                for t in new_texts:
                    mark_indexed(t, source_id=Path(filename).stem)
                total_new += len(new_texts)
                logger.info(f"  → {len(new_texts)} new chunks indexed ({total_skip} skipped)")
            else:
                logger.info(f"  → all {len(chunks)} chunks already indexed (skipped)")

        except Exception as e:
            logger.error(f"FAILED: {filename} — {e}")
            failed.append(f"{file_id}\t{filename}\t{e}")

    index.save()

    # ── Summary ─────────────────────────────────────────────────────────────
    stats = dedup_stats()
    print(f"\n{'='*60}")
    print(f"Done: {total_new} new chunks indexed, {total_skip} skipped")
    print(f"Total in DB: {stats['total_indexed_chunks']} chunks")
    print(f"{'='*60}")

    if failed:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fail_path = FAILED_LOG_DIR / f"law_failed_{ts}.txt"
        fail_path.write_text("\n".join(failed), encoding="utf-8")
        print(f"\n{len(failed)} file(s) failed → {fail_path}")


if __name__ == "__main__":
    main()
