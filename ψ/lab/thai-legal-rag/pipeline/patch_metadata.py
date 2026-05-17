"""
Patch metadata.pkl and bm25.pkl for chunks that have empty ref_number.
Re-parses the source MD files (now with hybrid format support) and
updates metadata in-place — no re-embedding needed.
"""
import pickle
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import FAISS_DIR, BM25_DIR, MD_BACKUP_DIR
from src.ingestion.md_loader import load_md_file

_FIELDS_TO_PATCH = ["ref_number", "date", "topic", "file_url",
                    "file_id", "law_section", "tags", "category"]


def _build_patch_lookup() -> dict[str, dict[int, dict]]:
    """Re-parse all MD files → {source_name: {chunk_index: metadata}}.

    Indexes under multiple keys to handle mismatches between what md_loader
    produces (source_name from frontmatter, e.g. "file.pdf") and what the
    existing index stores (the .md filename used during ingestion).
    """
    lookup: dict[str, dict[int, dict]] = {}
    md_dir = Path(MD_BACKUP_DIR)
    md_files = sorted(md_dir.glob("*.md"))
    print(f"Re-parsing {len(md_files)} MD files...")
    for md_file in md_files:
        try:
            chunks = load_md_file(md_file)
        except Exception as e:
            print(f"  SKIP {md_file.name}: {e}")
            continue
        if not chunks:
            continue
        chunk_map = {
            c.metadata.get("chunk_index", i): c.metadata
            for i, c in enumerate(chunks)
        }
        # Index under frontmatter source_name (e.g. "file.pdf")
        lookup[chunks[0].metadata.get("source_name", md_file.name)] = chunk_map
        # Also index under the .md filename itself (what the index may store)
        lookup[md_file.name] = chunk_map
    return lookup


def patch_faiss_metadata(lookup: dict) -> int:
    meta_path = FAISS_DIR / "metadata.pkl"
    meta: list[dict] = pickle.loads(meta_path.read_bytes())

    patched = 0
    for item in meta:
        if item.get("ref_number"):
            continue  # already has ref — skip
        source_name = item.get("source_name", "")
        chunk_index = item.get("chunk_index", -1)
        fresh = lookup.get(source_name, {}).get(chunk_index)
        if not fresh:
            continue
        for field in _FIELDS_TO_PATCH:
            if not item.get(field) and fresh.get(field):
                item[field] = fresh[field]
        patched += 1

    meta_path.write_bytes(pickle.dumps(meta))
    print(f"FAISS metadata: patched {patched} chunks → saved")
    return patched


def patch_bm25_metadata(lookup: dict) -> int:
    bm25_path = BM25_DIR / "bm25.pkl"
    if not bm25_path.exists():
        print("BM25 index not found — skip")
        return 0

    data = pickle.loads(bm25_path.read_bytes())
    bm25_meta: list[dict] = data["metadata"]

    patched = 0
    for item in bm25_meta:
        if item.get("ref_number"):
            continue
        source_name = item.get("source_name", "")
        chunk_index = item.get("chunk_index", -1)
        fresh = lookup.get(source_name, {}).get(chunk_index)
        if not fresh:
            continue
        for field in _FIELDS_TO_PATCH:
            if not item.get(field) and fresh.get(field):
                item[field] = fresh[field]
        patched += 1

    bm25_path.write_bytes(pickle.dumps(data))
    print(f"BM25 metadata:  patched {patched} chunks → saved")
    return patched


def main():
    lookup = _build_patch_lookup()
    print(f"Lookup built: {len(lookup)} source files\n")

    faiss_patched = patch_faiss_metadata(lookup)
    bm25_patched = patch_bm25_metadata(lookup)

    print(f"\nDone — FAISS: {faiss_patched}, BM25: {bm25_patched} chunks patched")

    # Verify
    meta = pickle.loads((FAISS_DIR / "metadata.pkl").read_bytes())
    still_empty = [d for d in meta
                   if not d.get("ref_number") and d.get("category") == "ข้อหารือ กวจ."]
    print(f"Remaining empty ref_number (ข้อหารือ): {len(still_empty)}")


if __name__ == "__main__":
    main()
