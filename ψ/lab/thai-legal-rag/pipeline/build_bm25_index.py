"""One-time: build BM25 index from existing FAISS metadata.pkl."""
import pickle
import sys
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import FAISS_DIR, BM25_DIR
from src.indexing.bm25_store import BM25Store

_BM25_FILE = BM25_DIR / "bm25.pkl"


def main():
    meta_path = FAISS_DIR / "metadata.pkl"
    if not meta_path.exists():
        print(f"ERROR: metadata.pkl not found at {meta_path}")
        sys.exit(1)

    meta = pickle.loads(meta_path.read_bytes())
    print(f"Building BM25 from {len(meta)} existing chunks...")

    # Wipe existing index so we rebuild from scratch (not append)
    if _BM25_FILE.exists():
        _BM25_FILE.unlink()
        print("Wiped existing BM25 index.")

    store = BM25Store()
    # Extract text from copies to avoid mutating the loaded list
    texts = [d["text"] for d in meta]
    metas = [{k: v for k, v in d.items() if k != "text"} for d in meta]

    BATCH = 1000
    for i in tqdm(range(0, len(texts), BATCH)):
        store.add_batch(texts[i:i + BATCH], metas[i:i + BATCH])

    store.save()
    print(f"Done — {store.count} docs indexed")


if __name__ == "__main__":
    main()
