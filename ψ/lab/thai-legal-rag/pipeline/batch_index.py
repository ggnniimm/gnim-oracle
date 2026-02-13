#!/usr/bin/env python3
"""
Thai Legal RAG — Batch Indexer (canonical CLI)

Usage:
    python batch_index.py --folder-id DRIVE_FOLDER_ID --category กรมบัญชีกลาง
    python batch_index.py --folder-id DRIVE_FOLDER_ID --category กรมบัญชีกลาง --dry-run
    python batch_index.py --folder-id DRIVE_FOLDER_ID --category กรมบัญชีกลาง --retry-file failed_20260213.txt
"""
import argparse
import datetime
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm

from src.ingestion.drive import list_pdfs, stream_pdf
from src.ingestion.ocr import pdf_to_text
from src.ingestion.chunker import chunk_document
from src.ingestion.dedup import is_indexed, mark_indexed, stats as dedup_stats
from src.indexing.manager import IndexManager
from src.config import FAILED_LOG_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Thai Legal RAG Batch Indexer")
    p.add_argument("--folder-id", required=True, help="Google Drive folder ID")
    p.add_argument("--category", required=True, help="Category label (e.g. กรมบัญชีกลาง)")
    p.add_argument("--dry-run", action="store_true", help="List files only, don't index")
    p.add_argument(
        "--retry-file",
        type=Path,
        default=None,
        help="Path to failed_TIMESTAMP.txt — retry only those file IDs",
    )
    p.add_argument(
        "--no-lightrag",
        action="store_true",
        help="Skip LightRAG indexing (FAISS only, faster)",
    )
    return p.parse_args()


def load_retry_ids(path: Path) -> set[str]:
    return set(line.strip() for line in path.read_text().splitlines() if line.strip())


def main():
    args = parse_args()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    failed_log = FAILED_LOG_DIR / f"failed_{timestamp}.txt"

    logger.info(f"Listing files in folder: {args.folder_id}")
    files = list_pdfs(args.folder_id)
    logger.info(f"Found {len(files)} PDF files")

    # Filter by retry list if provided
    if args.retry_file:
        retry_ids = load_retry_ids(args.retry_file)
        files = [f for f in files if f["id"] in retry_ids]
        logger.info(f"Retry mode: {len(files)} files to retry")

    if args.dry_run:
        print(f"\n--- DRY RUN: {len(files)} files would be indexed ---")
        for f in files:
            print(f"  [{f['mimeType'].split('/')[-1]}] {f['name']} ({f['id']})")
        return

    index = IndexManager(use_lightrag=not args.no_lightrag)
    failed: list[str] = []
    indexed_count = 0
    skipped_count = 0

    for file_info in tqdm(files, desc="Indexing", unit="file"):
        file_id = file_info["id"]
        file_name = file_info["name"]

        try:
            # 1. Download
            logger.debug(f"Downloading: {file_name}")
            pdf_bytes = stream_pdf(file_id)

            # 2. OCR → text
            logger.debug(f"OCR: {file_name}")
            text = pdf_to_text(pdf_bytes, file_id=file_id)

            if not text.strip():
                logger.warning(f"Empty text after OCR: {file_name}")
                failed.append(file_id)
                continue

            # 3. Chunk
            chunks = chunk_document(
                text,
                source_drive_id=file_id,
                source_name=file_name,
                category=args.category,
            )

            # 4. Dedup + index
            new_chunks = []
            new_metas = []
            for chunk in chunks:
                if is_indexed(chunk.text):
                    continue
                new_chunks.append(chunk.text)
                new_metas.append(chunk.metadata)

            if not new_chunks:
                logger.debug(f"All chunks already indexed: {file_name}")
                skipped_count += 1
                continue

            # Batch add to FAISS
            index.add_batch(new_chunks, new_metas)

            # Mark as indexed
            for text_chunk in new_chunks:
                mark_indexed(text_chunk, source_id=file_id)

            indexed_count += 1
            logger.info(f"Indexed: {file_name} ({len(new_chunks)} new chunks)")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Failed: {file_name} ({file_id}): {e}")
            failed.append(file_id)

    # Save FAISS index
    index.save()

    # Write failed log
    if failed:
        failed_log.write_text("\n".join(failed))
        logger.warning(f"Failed files logged to: {failed_log}")

    # Summary
    db_stats = dedup_stats()
    print(f"\n{'='*50}")
    print(f"Done! Category: {args.category}")
    print(f"  Indexed:   {indexed_count} files")
    print(f"  Skipped:   {skipped_count} files (already indexed)")
    print(f"  Failed:    {len(failed)} files")
    print(f"  Total DB:  {db_stats['total_indexed_chunks']} chunks")
    if failed:
        print(f"  Retry with: --retry-file {failed_log}")
    print("="*50)


if __name__ == "__main__":
    main()
