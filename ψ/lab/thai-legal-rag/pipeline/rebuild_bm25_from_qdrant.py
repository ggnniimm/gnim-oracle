"""Rebuild BM25 index from Qdrant — the single source of truth.

Wipes the existing bm25.pkl and rebuilds it 1:1 from the Qdrant collection,
so BM25.count == qdrant.exact_count with no duplicates and no stale chunks.

Why this exists: force-reindex APPENDS to BM25 without dedup, so repeated
reindex batches silently double/triple the index (issue #42). The deploy
step must REBUILD BM25 from Qdrant, never append. Run this after any
indexing/cleanup that changes Qdrant point membership.

Usage:
    QDRANT_URL=http://localhost:6333 THAI_RAG_DATA_DIR=$(pwd)/data \
        python3 pipeline/rebuild_bm25_from_qdrant.py
"""
import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.bm25_store import BM25Store, _INDEX_FILE

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "thai_legal_rag")
SCROLL_BATCH = 1000


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{QDRANT_URL}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req, timeout=120).read().decode())


def _exact_count() -> int:
    return _post(f"/collections/{COLLECTION}/points/count", {"exact": True})["result"]["count"]


def scroll_all() -> list[dict]:
    """Return all point payloads from the collection."""
    payloads: list[dict] = []
    offset = None
    while True:
        body = {"limit": SCROLL_BATCH, "with_payload": True, "with_vector": False}
        if offset is not None:
            body["offset"] = offset
        res = _post(f"/collections/{COLLECTION}/points/scroll", body)["result"]
        for pt in res["points"]:
            payloads.append(pt["payload"])
        offset = res.get("next_page_offset")
        if offset is None:
            break
    return payloads


def main():
    target = _exact_count()
    print(f"Qdrant {COLLECTION} exact count: {target}")

    print("Scrolling all points from Qdrant...")
    payloads = scroll_all()
    print(f"Fetched {len(payloads)} payloads")

    # Sanity: every payload must carry text
    missing_text = sum(1 for p in payloads if not p.get("text"))
    if missing_text:
        print(f"WARNING: {missing_text} payloads have no 'text' field")

    # Wipe existing index so we rebuild from scratch (not append)
    if _INDEX_FILE.exists():
        _INDEX_FILE.unlink()
        print(f"Wiped existing BM25 index at {_INDEX_FILE}")

    store = BM25Store()
    texts = [p["text"] for p in payloads]
    metas = [{k: v for k, v in p.items() if k != "text"} for p in payloads]

    BATCH = 1000
    for i in tqdm(range(0, len(texts), BATCH), desc="Tokenizing"):
        store.add_batch(texts[i:i + BATCH], metas[i:i + BATCH])

    store.save()
    print(f"Done — {store.count} docs indexed")

    # Verify: count match + zero duplicate signatures
    sigs = Counter((m.get("file_id"), m.get("chunk_index")) for m in store._metadata)
    dups = sum(1 for v in sigs.values() if v > 1)
    print(f"Verify: bm25.count={store.count} | qdrant.exact={target} | "
          f"{'MATCH' if store.count == target else 'MISMATCH'}")
    print(f"Verify: duplicate signatures = {dups} ({'clean' if dups == 0 else 'STILL DIRTY'})")


if __name__ == "__main__":
    main()
