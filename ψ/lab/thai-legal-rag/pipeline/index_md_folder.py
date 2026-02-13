#!/usr/bin/env python3
"""
Index pre-processed MD files (with YAML frontmatter).
Use this when MD files already exist — skips OCR step.

Usage:
    python index_md_folder.py --dir ψ/lab/sample-docs/
    python index_md_folder.py --dir /path/to/md_files/ --dry-run
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm

from src.ingestion.md_loader import load_md_file
from src.ingestion.dedup import is_indexed, mark_indexed, stats as dedup_stats
from src.indexing.manager import IndexManager


def parse_args():
    p = argparse.ArgumentParser(description="Index MD files into FAISS + LightRAG")
    p.add_argument("--dir", required=True, type=Path, help="Directory containing .md files")
    p.add_argument("--dry-run", action="store_true", help="Show chunks without indexing")
    p.add_argument("--no-lightrag", action="store_true", help="FAISS only")
    return p.parse_args()


def main():
    args = parse_args()
    md_files = sorted(args.dir.glob("*.md"))
    print(f"Found {len(md_files)} MD files in {args.dir}")

    if args.dry_run:
        for f in md_files:
            chunks = load_md_file(f)
            print(f"\n  {f.name}: {len(chunks)} chunks")
            for c in chunks[:2]:
                print(f"    [{c.metadata.get('section','')}] {c.text[:80]}...")
        return

    index = IndexManager(use_lightrag=not args.no_lightrag)
    total_new = 0
    total_skip = 0

    for md_file in tqdm(md_files, desc="Indexing MD files"):
        chunks = load_md_file(md_file)
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
                mark_indexed(t, source_id=md_file.stem)
            total_new += len(new_texts)

    index.save()
    stats = dedup_stats()
    print(f"\nDone: {total_new} new chunks indexed, {total_skip} skipped")
    print(f"Total in DB: {stats['total_indexed_chunks']} chunks")


if __name__ == "__main__":
    main()
