"""
LightRAG wrapper (async).
Graph-based RAG for multi-document reasoning.
Uses Gemini Flash for LLM + Gemini embeddings.
"""
from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

import google.generativeai as genai
import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete
from lightrag.utils import EmbeddingFunc

from src.config import (
    EMBEDDING_DIM,
    GEMINI_API_KEYS,
    GEMINI_EMBEDDING_MODEL,
    GEMINI_FLASH_MODEL,
    LIGHTRAG_DIR,
    LIGHTRAG_TOP_K,
)

logger = logging.getLogger(__name__)

_KEY_INDEX = 0


def _next_key() -> str:
    global _KEY_INDEX
    if not GEMINI_API_KEYS:
        raise ValueError("No GEMINI_API_KEYS configured.")
    key = GEMINI_API_KEYS[_KEY_INDEX % len(GEMINI_API_KEYS)]
    _KEY_INDEX += 1
    return key


async def _gemini_llm_func(prompt: str, **kwargs) -> str:
    """Async LLM function for LightRAG."""
    genai.configure(api_key=_next_key())
    model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, lambda: model.generate_content(prompt)
    )
    return response.text


async def _gemini_embedding_func(texts: list[str]) -> np.ndarray:
    """Async embedding function for LightRAG."""
    genai.configure(api_key=_next_key())
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: genai.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            content=texts,
            task_type="retrieval_document",
        ),
    )
    vectors = np.array(result["embedding"], dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    return vectors


def _build_lightrag() -> LightRAG:
    embedding_func = EmbeddingFunc(
        embedding_dim=EMBEDDING_DIM,
        max_token_size=8192,
        func=_gemini_embedding_func,
    )
    return LightRAG(
        working_dir=str(LIGHTRAG_DIR),
        llm_model_func=_gemini_llm_func,
        embedding_func=embedding_func,
    )


class LightRAGStore:
    def __init__(self):
        self._rag = _build_lightrag()
        logger.info(f"LightRAG initialized at {LIGHTRAG_DIR}")

    async def add(self, text: str, metadata: dict | None = None) -> None:
        """Insert text into LightRAG graph."""
        await self._rag.ainsert(text)

    async def add_batch(self, texts: list[str]) -> None:
        for text in texts:
            await self.add(text)

    async def search(self, query: str, k: int = LIGHTRAG_TOP_K) -> list[dict]:
        """Hybrid search using LightRAG."""
        try:
            response = await self._rag.aquery(
                query,
                param=QueryParam(mode="hybrid", top_k=k),
            )
            if not response:
                return []
            return [
                {
                    "text": response,
                    "score": 1.0,
                    "source": "lightrag",
                    "source_name": "LightRAG Graph",
                }
            ]
        except Exception as e:
            logger.warning(f"LightRAG search failed: {e}")
            return []
