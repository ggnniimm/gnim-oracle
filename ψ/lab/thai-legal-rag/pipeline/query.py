#!/usr/bin/env python3
"""
Thai Legal RAG — Query CLI

Usage:
    python pipeline/query.py "มาตรา 60 บอกว่าอะไร"
    python pipeline/query.py "ค่าปรับผิดสัญญา" --top-k 10
    python pipeline/query.py "ค่าปรับ" --no-generate   # retrieve only, no LLM answer
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer
from src.config import FAISS_TOP_K

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def parse_args():
    p = argparse.ArgumentParser(description="Query Thai Legal RAG indexes")
    p.add_argument("query", nargs="?", help="Query string (Thai)")
    p.add_argument("--no-generate", action="store_true", help="Skip LLM answer, show chunks only")
    p.add_argument("--no-expand", action="store_true", help="Skip query expansion")
    p.add_argument("--top-k", type=int, default=FAISS_TOP_K, help=f"Top-k (default {FAISS_TOP_K})")
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

    print(f"\nQuery    : {args.query}")
    from src.config import VECTOR_BACKEND
    print(f"Mode     : {VECTOR_BACKEND.capitalize()} only")
    print(f"Expand   : {not args.no_expand}")
    print_separator()

    # --- Load index ---
    print("Loading index...", end=" ", flush=True)
    try:
        index = IndexManager(use_lightrag=False)
    except Exception as e:
        print(f"\nFailed to load index: {e}")
        sys.exit(1)

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
    bm25_count = len(raw_results.get("bm25", []))
    print(f"done (vector: {faiss_count}, BM25: {bm25_count})")

    ranked = rerank(raw_results, query=args.query)
    print(f"Top {len(ranked)} chunks after reranking:")

    for i, chunk in enumerate(ranked, 1):
        print_chunk(i, chunk)

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
