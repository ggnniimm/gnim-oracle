"""
FAISS vector store backed by Gemini embeddings.
Persists index + metadata to disk.
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path

import faiss
import numpy as np

from src.config import (
    EMBEDDING_DIM,
    FAISS_DIR,
    FAISS_TOP_K,
    GEMINI_EMBEDDING_MODEL,
)
from src.gemini_client import get_client

logger = logging.getLogger(__name__)

_INDEX_FILE = FAISS_DIR / "index.faiss"
_META_FILE = FAISS_DIR / "metadata.pkl"


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
    # Handle single text case
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return vectors / norms


class FAISSStore:
    def __init__(self):
        self._index: faiss.IndexFlatIP | None = None
        self._metadata: list[dict] = []
        self._load()

    def _load(self) -> None:
        if _INDEX_FILE.exists() and _META_FILE.exists():
            self._index = faiss.read_index(str(_INDEX_FILE))
            with open(_META_FILE, "rb") as f:
                self._metadata = pickle.load(f)
            logger.info(f"Loaded FAISS index: {self._index.ntotal} vectors, {len(self._metadata)} metadata entries")
            if self._index.ntotal != len(self._metadata):
                logger.warning(
                    f"FAISS alignment mismatch: index has {self._index.ntotal} vectors "
                    f"but metadata has {len(self._metadata)} entries. "
                    f"Search may return orphan vectors."
                )
        else:
            self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self._metadata = []
            logger.info("Created new FAISS index")

    def save(self) -> None:
        faiss.write_index(self._index, str(_INDEX_FILE))
        with open(_META_FILE, "wb") as f:
            pickle.dump(self._metadata, f)

    def add(self, text: str, metadata: dict) -> None:
        vector = _embed([text])
        self._index.add(vector)
        self._metadata.append({"text": text, **metadata})

    def add_batch(self, texts: list[str], metadatas: list[dict], batch_size: int = 100) -> None:
        """Embed and add texts in batches of batch_size (API limit: 100)."""
        if not texts:
            return
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            vectors = _embed(batch_texts)
            self._index.add(vectors)
            for text, meta in zip(batch_texts, batch_metas):
                self._metadata.append({"text": text, **meta})
            if len(texts) > batch_size:
                logger.debug(f"Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1} ({len(batch_texts)} texts)")

    def search(self, query: str, k: int = FAISS_TOP_K) -> list[dict]:
        """Returns list of {text, score, **metadata}."""
        if self._index.ntotal == 0:
            return []
        vector = _embed([query])
        scores, indices = self._index.search(vector, min(k, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if idx >= len(self._metadata):  # orphan vector (metadata removed, FAISS can't delete)
                continue
            item = dict(self._index_meta(idx))
            item["score"] = float(score)
            item["source"] = "faiss"
            results.append(item)
        return results

    def _index_meta(self, idx: int) -> dict:
        return self._metadata[idx]

    @property
    def count(self) -> int:
        return self._index.ntotal if self._index else 0
