"""
Rebuild FAISS index from metadata.pkl.

Use after any operation that modifies metadata.pkl without updating FAISS
(e.g., removing chunks via filtering — FAISS has no delete API).
"""
import pickle, sys, time
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True, raise_error_if_not_found=False))

import faiss
import numpy as np
from src.config import FAISS_DIR, EMBEDDING_DIM
from src.indexing.faiss_store import _embed

META_FILE = FAISS_DIR / "metadata.pkl"
INDEX_FILE = FAISS_DIR / "index.faiss"
BATCH_SIZE = 100


def main():
    meta = pickle.loads(META_FILE.read_bytes())
    print(f"Rebuilding FAISS index from {len(meta)} metadata entries...")

    texts = [m["text"] for m in meta]

    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    total = len(texts)
    batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for i in tqdm(range(0, total, BATCH_SIZE), total=batches, desc="Embedding"):
        batch = texts[i:i + BATCH_SIZE]
        vectors = _embed(batch)
        index.add(vectors)
        time.sleep(0.1)  # gentle rate limit

    assert index.ntotal == len(meta), f"Mismatch: {index.ntotal} vectors vs {len(meta)} metadata"

    faiss.write_index(index, str(INDEX_FILE))
    print(f"\nDone — {index.ntotal} vectors saved to {INDEX_FILE}")
    print("FAISS index is now aligned with metadata.pkl")


if __name__ == "__main__":
    main()
