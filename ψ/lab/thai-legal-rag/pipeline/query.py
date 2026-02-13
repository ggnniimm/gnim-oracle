#!/usr/bin/env python3
"""
Thai Legal RAG — Query CLI

Test RAG queries against FAISS + LightRAG indexes.
Useful for verifying cross-document retrieval (ข้อหารือ + law).

Usage:
    python pipeline/query.py "มาตรา 60 บอกว่าอะไร"
    python pipeline/query.py "ข้อหารือที่อ้าง มาตรา 60 มีกี่ฉบับ" --mode global
    python pipeline/query.py "ค่าปรับผิดสัญญา" --no-lightrag --top-k 10
    python pipeline/query.py "ค่าปรับ" --no-generate   # retrieve only, no LLM answer
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer
from src.config import FAISS_TOP_K, LIGHTRAG_TOP_K

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def parse_args():
    p = argparse.ArgumentParser(description="Query Thai Legal RAG indexes")
    p.add_argument("query", nargs="?", help="Query string (Thai)")
    p.add_argument(
        "--mode",
        choices=["hybrid", "local", "global", "naive"],
        default="hybrid",
        help="LightRAG query mode (default: hybrid)",
    )
    p.add_argument("--no-lightrag", action="store_true", help="FAISS only")
    p.add_argument("--no-generate", action="store_true", help="Skip LLM answer, show chunks only")
    p.add_argument("--no-expand", action="store_true", help="Skip query expansion")
    p.add_argument("--top-k", type=int, default=FAISS_TOP_K, help=f"FAISS top-k (default {FAISS_TOP_K})")
    p.add_argument("--verbose", "-v", action="store_true", help="Show debug logs")
    return p.parse_args()


def print_separator(char="─", width=70):
    print(char * width)


def print_chunk(i: int, chunk: dict):
    source = chunk.get("source_name", chunk.get("source", "unknown"))
    category = chunk.get("category", "")
    score = chunk.get("weighted_score", chunk.get("score", 0))
    drive_id = chunk.get("source_drive_id", "")
    text = chunk.get("text", "")

    print(f"\n[{i}] {source}")
    if category:
        print(f"    Category : {category}")
    print(f"    Score    : {score:.4f}")
    if drive_id:
        print(f"    Drive    : https://drive.google.com/file/d/{drive_id}/view")
    print(f"    Text     : {text[:300]}{'...' if len(text) > 300 else ''}")


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    # Interactive mode if no query given
    if not args.query:
        try:
            args.query = input("คำถาม: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nยกเลิก")
            sys.exit(0)
        if not args.query:
            print("กรุณาระบุคำถาม")
            sys.exit(1)

    use_lightrag = not args.no_lightrag

    print(f"\nQuery    : {args.query}")
    print(f"Mode     : {'FAISS only' if not use_lightrag else f'FAISS + LightRAG ({args.mode})'}")
    print(f"Expand   : {not args.no_expand}")
    print_separator()

    # --- Load index ---
    print("Loading index...", end=" ", flush=True)
    try:
        index = IndexManager(use_lightrag=use_lightrag)
    except Exception as e:
        print(f"\nFailed to load index: {e}")
        sys.exit(1)

    # Patch LightRAG query mode if needed
    if use_lightrag and args.mode != "hybrid":
        from lightrag import QueryParam
        original_search = index.lightrag.search

        async def patched_search(query: str, k: int = LIGHTRAG_TOP_K) -> list[dict]:
            try:
                response = await index.lightrag._rag.aquery(
                    query,
                    param=QueryParam(mode=args.mode, top_k=k),
                )
                if not response:
                    return []
                return [{"text": response, "score": 1.0, "source": "lightrag", "source_name": "LightRAG Graph"}]
            except Exception as e:
                logging.warning(f"LightRAG patched search failed: {e}")
                return []

        index.lightrag.search = patched_search

    retriever = Retriever(index)
    print("done")

    # --- Retrieve ---
    print("Retrieving...", end=" ", flush=True)
    try:
        raw_results = retriever.retrieve(args.query, expand=not args.no_expand)
    except Exception as e:
        print(f"\nRetrieval failed: {e}")
        sys.exit(1)

    faiss_count = len(raw_results.get("faiss", []))
    lightrag_count = len(raw_results.get("lightrag", []))
    print(f"done (FAISS: {faiss_count}, LightRAG: {lightrag_count})")

    ranked = rerank(raw_results)
    print(f"Top {len(ranked)} chunks after reranking:")

    for i, chunk in enumerate(ranked, 1):
        print_chunk(i, chunk)

    # --- LightRAG raw response ---
    if use_lightrag and raw_results.get("lightrag"):
        print_separator()
        print("\nLightRAG Graph Response:")
        for item in raw_results["lightrag"]:
            print(item.get("text", "")[:800])

    # --- Generate ---
    if not args.no_generate and ranked:
        print_separator("═")
        print(f"\nGenerating answer...")
        print_separator("═")
        try:
            result = generate_answer(args.query, ranked)
            print(f"\n{result['answer']}")
            if result["sources"]:
                print_separator()
                print(f"\nSources ({len(result['sources'])}):")
                for src in result["sources"]:
                    drive_id = src.get("drive_id", "")
                    name = src.get("name", "unknown")
                    if drive_id:
                        print(f"  - {name}  →  https://drive.google.com/file/d/{drive_id}/view")
                    else:
                        print(f"  - {name}")
            print(f"\nModel: {result['model']} | Chunks: {result['chunks_used']}")
        except Exception as e:
            print(f"\nGeneration failed: {e}")
    elif not ranked:
        print("\nNo chunks retrieved — cannot generate answer.")


if __name__ == "__main__":
    main()
