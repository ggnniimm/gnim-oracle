"""
Qdrant vector store backed by Gemini embeddings.
In-memory mode with optional disk persistence.
Drop-in replacement for FAISSStore.
"""
from __future__ import annotations

import logging
import uuid

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from src.config import (
    EMBEDDING_DIM,
    FAISS_TOP_K,
    GEMINI_EMBEDDING_MODEL,
    QDRANT_PATH,
    QDRANT_URL,
)
from src.gemini_client import get_client

logger = logging.getLogger(__name__)

_COLLECTION = "thai_legal_rag"


def _embed(texts: list[str], _retries: int = 3) -> np.ndarray:
    """Embed a list of texts using Gemini embedding model (with retry)."""
    import time
    for attempt in range(1, _retries + 1):
        try:
            client = get_client()
            result = client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=texts,
            )
            break
        except Exception as e:
            if attempt == _retries:
                raise
            logger.warning(f"Embed attempt {attempt} failed: {e}, retrying in {attempt * 2}s...")
            time.sleep(attempt * 2)
    vectors = np.array([e.values for e in result.embeddings], dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    # Normalize for cosine similarity (Qdrant cosine does this too, but keep consistent)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return vectors / norms


class QdrantStore:
    def __init__(self):
        if QDRANT_URL:
            # Server mode (Docker / Qdrant Cloud)
            self._client = QdrantClient(url=QDRANT_URL)
            logger.info(f"Qdrant server mode: {QDRANT_URL}")
        elif QDRANT_PATH:
            # Persistent local storage
            self._client = QdrantClient(path=str(QDRANT_PATH))
            logger.info(f"Qdrant local mode: {QDRANT_PATH}")
        else:
            # Pure in-memory
            self._client = QdrantClient(":memory:")
            logger.info("Qdrant in-memory mode")
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = [c.name for c in self._client.get_collections().collections]
        if _COLLECTION not in collections:
            self._client.create_collection(
                collection_name=_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection '{_COLLECTION}' (dim={EMBEDDING_DIM})")
        else:
            info = self._client.get_collection(_COLLECTION)
            logger.info(f"Loaded Qdrant collection '{_COLLECTION}': {info.points_count} points")

    def add(self, text: str, metadata: dict) -> None:
        vector = _embed([text])
        point_id = str(uuid.uuid4())
        self._client.upsert(
            collection_name=_COLLECTION,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector[0].tolist(),
                    payload={"text": text, **metadata},
                )
            ],
        )

    def add_batch(self, texts: list[str], metadatas: list[dict], batch_size: int = 100) -> None:
        """Embed and add texts in batches of batch_size (API limit: 100)."""
        if not texts:
            return
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            vectors = _embed(batch_texts)
            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[j].tolist(),
                    payload={"text": text, **meta},
                )
                for j, (text, meta) in enumerate(zip(batch_texts, batch_metas))
            ]
            self._client.upsert(
                collection_name=_COLLECTION,
                points=points,
            )
            if len(texts) > batch_size:
                logger.debug(
                    f"Embedded batch {i // batch_size + 1}/"
                    f"{(len(texts) - 1) // batch_size + 1} ({len(batch_texts)} texts)"
                )

    def search(self, query: str, k: int = FAISS_TOP_K, payload_filter: dict | None = None) -> list[dict]:
        """Returns list of {text, score, **metadata}."""
        total = self._client.get_collection(_COLLECTION).points_count
        if total == 0:
            return []
        vector = _embed([query])
        qdrant_filter = (
            Filter(must=[FieldCondition(key=payload_filter["field"], match=MatchValue(value=payload_filter["value"]))])
            if payload_filter
            else None
        )
        response = self._client.query_points(
            collection_name=_COLLECTION,
            query=vector[0].tolist(),
            limit=min(k, total),
            query_filter=qdrant_filter,
        )
        results = []
        for hit in response.points:
            item = dict(hit.payload)
            item["score"] = float(hit.score)
            item["source"] = "faiss"  # keep compatible with reranker weight keys
            results.append(item)
        return results

    def delete_by_source_name(self, source_name: str) -> int:
        """Delete all points whose source_name matches (exact). Returns count deleted."""
        deleted = 0
        offset = None
        flt = Filter(must=[FieldCondition(key="source_name", match=MatchValue(value=source_name))])
        while True:
            result, next_offset = self._client.scroll(
                collection_name=_COLLECTION,
                scroll_filter=flt,
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            if not result:
                break
            ids = [p.id for p in result]
            self._client.delete(
                collection_name=_COLLECTION,
                points_selector=ids,
            )
            deleted += len(ids)
            if next_offset is None:
                break
            offset = next_offset
        logger.info(f"Deleted {deleted} points for source_name={source_name!r}")
        return deleted

    def save(self) -> None:
        """No-op for Qdrant — data is persisted automatically in local mode."""
        pass

    @property
    def count(self) -> int:
        return self._client.get_collection(_COLLECTION).points_count
