"""
Thai Legal RAG — FastAPI backend
Run: uvicorn api.main:app --reload --port 8000
(from ψ/lab/thai-legal-rag/)
"""
import os
import sys
from pathlib import Path
from collections import OrderedDict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer

app = FastAPI(title="Thai Legal RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Index (singleton) ──────────────────────────────────────────────────────────

_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        index = IndexManager()
        _retriever = Retriever(index)
    return _retriever


# ── Models ─────────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[Message] = []


class Source(BaseModel):
    index: int
    name: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    model: str
    chunks_used: int


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_source_map(chunks: list[dict]) -> tuple[dict[int, int], list[Source]]:
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for chunk in chunks:
        key = chunk.get("source_name", chunk.get("source", "unknown"))
        grouped.setdefault(key, []).append(chunk)
    ordered_chunks = [c for group in grouped.values() for c in group]

    source_list: list[Source] = []
    source_index: dict[str, int] = {}
    for chunk in ordered_chunks:
        name = chunk.get("source_name", chunk.get("source", "unknown"))
        if name not in source_index:
            idx = len(source_list) + 1
            source_index[name] = idx
            source_list.append(Source(index=idx, name=name, url=chunk.get("file_url", "")))

    chunk_to_src: dict[int, int] = {}
    for i, chunk in enumerate(ordered_chunks, 1):
        name = chunk.get("source_name", chunk.get("source", "unknown"))
        chunk_to_src[i] = source_index[name]

    return chunk_to_src, source_list


import re

def _replace_refs(answer: str, chunk_to_src: dict[int, int]) -> str:
    def replace(m: re.Match) -> str:
        nums = [int(x.strip()) for x in m.group(1).split(",")]
        src_indices = list(dict.fromkeys(chunk_to_src.get(n, n) for n in nums))
        return "[" + ", ".join(str(i) for i in src_indices) + "]"
    return re.sub(r"\[([\d ,]+)\]", replace, answer)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    retriever = get_retriever()
    history = [{"role": m.role, "content": m.content} for m in req.history]

    raw_results = retriever.retrieve(req.question, expand=True, history=history)
    ranked_chunks = rerank(raw_results, query=req.question)
    result = generate_answer(req.question, ranked_chunks, history=history)

    chunk_to_src, source_list = _build_source_map(ranked_chunks)
    answer = _replace_refs(result["answer"], chunk_to_src)

    return ChatResponse(
        answer=answer,
        sources=source_list,
        model=result["model"],
        chunks_used=result["chunks_used"],
    )
