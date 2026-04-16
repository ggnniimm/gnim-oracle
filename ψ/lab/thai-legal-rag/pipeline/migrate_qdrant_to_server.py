"""
Migrate Qdrant local-mode data → Qdrant server (Docker).
Reads all points from local path store and upserts to server — no re-embedding needed.

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data_with_ac python3 pipeline/migrate_qdrant_to_server.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import QDRANT_PATH
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from tqdm import tqdm

LOCAL_URL = "http://localhost:6333"
COLLECTION = "thai_legal_rag"
BATCH = 200


def main():
    print(f"Source (local): {QDRANT_PATH}")
    print(f"Target (server): {LOCAL_URL}")

    src = QdrantClient(path=str(QDRANT_PATH))
    dst = QdrantClient(url=LOCAL_URL)

    # Check source
    src_info = src.get_collection(COLLECTION)
    total = src_info.points_count
    print(f"Source points: {total:,}")

    # Recreate collection on server
    existing = [c.name for c in dst.get_collections().collections]
    if COLLECTION in existing:
        print("Deleting existing server collection...")
        dst.delete_collection(COLLECTION)

    dst.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        on_disk_payload=True,
    )
    print("Created collection on server.")

    # Scroll all points from local and upsert to server
    offset = None
    uploaded = 0
    with tqdm(total=total, unit="pts") as bar:
        while True:
            result, next_offset = src.scroll(
                collection_name=COLLECTION,
                limit=BATCH,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            if not result:
                break

            points = [
                PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                for p in result
            ]
            dst.upsert(collection_name=COLLECTION, points=points)
            uploaded += len(points)
            bar.update(len(points))

            if next_offset is None:
                break
            offset = next_offset

    print(f"\nDone — migrated {uploaded:,} points to {LOCAL_URL}")
    dst_info = dst.get_collection(COLLECTION)
    print(f"Server points: {dst_info.points_count:,}")


if __name__ == "__main__":
    main()
