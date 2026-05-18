#!/usr/bin/env python3
"""
Index pre-processed MD files (with YAML frontmatter).
Use this when MD files already exist — skips OCR step.

Usage:
    python index_md_folder.py --dir ψ/lab/sample-docs/
    python index_md_folder.py --dir /path/to/md_files/ --dry-run
    python index_md_folder.py --dir data/md_backup --force-reindex --file doc_X.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm

from src.ingestion.md_loader import load_md_file, _parse_frontmatter
from src.ingestion.dedup import is_indexed, mark_indexed, delete_by_source_id, stats as dedup_stats
from src.indexing.manager import IndexManager

_THAI_DIGIT_MAP = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def _normalize_numerals(text: str) -> str:
    return text.translate(_THAI_DIGIT_MAP)


def _metadata_prefix(meta: dict) -> str:
    """Same prefix logic as batch_index.py — keeps dedup hashes consistent."""
    parts = []
    if meta.get("ref_number"):
        ref = _normalize_numerals(str(meta["ref_number"]))
        parts.append(ref)
        if "/" in ref:
            suffix = ref.rsplit("/", 1)[-1].strip()
            if suffix.isdigit():
                parts.append(suffix)
    if meta.get("date"):
        parts.append(str(meta["date"]))
    if meta.get("category"):
        parts.append(str(meta["category"]))
    if not parts:
        return ""
    return "[" + " | ".join(parts) + "]\n\n"



def parse_args():
    p = argparse.ArgumentParser(description="Index MD files into vector store")
    p.add_argument("--dir", required=True, type=Path, help="Directory containing .md files")
    p.add_argument("--dry-run", action="store_true", help="Show chunks without indexing")
    p.add_argument(
        "--force-reindex",
        action="store_true",
        help="Delete existing vectors + dedup entries for --file before re-indexing",
    )
    p.add_argument(
        "--file",
        type=str,
        action="append",
        dest="files",
        metavar="FILENAME",
        help="Filename(s) to process (repeatable). Required with --force-reindex.",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if args.force_reindex and not args.files:
        print("Error: --force-reindex requires --file <filename>")
        sys.exit(1)

    if args.files:
        md_files = []
        for name in args.files:
            matches = list(args.dir.glob(name)) or [args.dir / name]
            md_files.extend([f for f in matches if f.exists()])
        if not md_files:
            print(f"No matching files found in {args.dir}")
            sys.exit(1)
        print(f"Processing {len(md_files)} file(s): {[f.name for f in md_files]}")
    else:
        md_files = sorted(args.dir.glob("*.md"))
        print(f"Found {len(md_files)} MD files in {args.dir}")

    if args.dry_run:
        for f in md_files:
            chunks = load_md_file(f)
            print(f"\n  {f.name}: {len(chunks)} chunks")
            for c in chunks[:2]:
                print(f"    [{c.metadata.get('section','')}] {c.text[:80]}...")
        return

    index = IndexManager()

    # --- force-reindex: purge old data before indexing ---
    if args.force_reindex:
        vector_store = index.vector
        for md_file in md_files:
            chunks = load_md_file(md_file)
            if chunks:
                source_name = chunks[0].metadata.get("source_name") or md_file.name
            else:
                # Inactive or empty file — parse frontmatter directly so delete_by_source_name
                # matches the .pdf source_name stored in Qdrant (not the .md filename).
                text = md_file.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(text)
                source_name = meta.get("source_file") or meta.get("original_filename") or md_file.name

            # 1. Delete from vector store
            n_vec = vector_store.delete_by_source_name(source_name)
            print(f"  [{md_file.name}] Deleted {n_vec} vectors (source_name={source_name!r})")

            # 2. Delete from dedup DB by source_id (file_id) — covers old and new hashes
            source_id = (chunks[0].metadata.get("file_id") if chunks else None) or md_file.stem
            n_dedup = delete_by_source_id(source_id)
            print(f"  [{md_file.name}] Deleted {n_dedup} dedup entries (source_id={source_id!r})")

    # --- normal indexing loop ---
    total_new = 0
    total_skip = 0
    save_every = 100

    for i, md_file in enumerate(tqdm(md_files, desc="Indexing MD files"), 1):
        chunks = load_md_file(md_file)
        new_texts, new_metas = [], []

        for chunk in chunks:
            prefix = _metadata_prefix(chunk.metadata)
            enriched = prefix + chunk.text if prefix else chunk.text
            if is_indexed(enriched):
                total_skip += 1
                continue
            new_texts.append(enriched)
            new_metas.append(chunk.metadata)

        if new_texts:
            index.add_batch(new_texts, new_metas)
            source_id = chunks[0].metadata.get("file_id") or md_file.stem
            for t in new_texts:
                mark_indexed(t, source_id=source_id)
            total_new += len(new_texts)

        if i % save_every == 0:
            index.save()

    index.save()
    stats = dedup_stats()
    print(f"\nDone: {total_new} new chunks indexed, {total_skip} skipped")
    print(f"Total in DB: {stats['total_indexed_chunks']} chunks")


if __name__ == "__main__":
    main()
