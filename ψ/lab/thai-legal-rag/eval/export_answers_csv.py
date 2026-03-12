"""
Export all test case queries with full RAG answers to CSV.
Usage: PYTHONUNBUFFERED=1 THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/export_answers_csv.py
"""
import csv
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer, build_context


def main():
    cases_path = Path(__file__).parent / "golden_test_cases.json"
    with open(cases_path, encoding="utf-8") as f:
        cases = json.load(f)

    print(f"Loading index...", end=" ", flush=True)
    index = IndexManager(use_lightrag=False)
    retriever = Retriever(index)
    print("done", flush=True)

    output_path = Path(__file__).parent / "tc_answers.csv"

    with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "TC_ID",
            "คำถาม",
            "คำตอบ",
            "แหล่งอ้างอิง",
            "must_contain",
            "notes",
        ])

        for i, case in enumerate(cases):
            tc_id = case["id"]
            query = case["query"]
            must_contain = ", ".join(case.get("must_contain", []))
            notes = case.get("notes", "")

            print(f"[{i+1}/{len(cases)}] {tc_id}: {query[:50]}...", flush=True)

            try:
                import asyncio
                results = asyncio.run(retriever.retrieve_async(query))
                ranked = rerank(results)
                answer_data = generate_answer(query, ranked)
                answer = answer_data["answer"]
                sources = ", ".join(s["name"] for s in answer_data["sources"])
            except Exception as e:
                answer = f"ERROR: {e}"
                sources = ""
                print(f"  ⚠ {e}", flush=True)

            writer.writerow([tc_id, query, answer, sources, must_contain, notes])

            # Rate limit protection
            if (i + 1) % 5 == 0:
                time.sleep(2)

    print(f"\nDone! Saved to: {output_path}", flush=True)


if __name__ == "__main__":
    main()
