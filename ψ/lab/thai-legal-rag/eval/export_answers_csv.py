"""
Export all TC queries with full RAG answers + PASS/FAIL to CSV (Excel-ready).
Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data_with_ac python3 eval/export_answers_csv.py
    THAI_RAG_DATA_DIR=$(pwd)/data_with_ac python3 eval/export_answers_csv.py --id TC-066
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer

_THAI_DIGIT_MAP = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def _normalize(text: str) -> str:
    return text.translate(_THAI_DIGIT_MAP)


def _check(case: dict, answer: str) -> tuple[str, str]:
    answer_norm = _normalize(answer)
    failures = []

    for phrase in case.get("must_contain", []):
        if isinstance(phrase, list):
            if not any(_normalize(p) in answer_norm for p in phrase):
                failures.append(f"must_contain {phrase} ไม่พบ")
        else:
            if _normalize(phrase) not in answer_norm:
                failures.append(f"must_contain '{phrase}' ไม่พบ")

    for phrase in case.get("must_not_contain", []):
        if _normalize(phrase) in answer_norm:
            failures.append(f"must_not_contain '{phrase}' พบในคำตอบ")

    return ("PASS" if not failures else "FAIL", "; ".join(failures))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="Run single TC by ID")
    parser.add_argument("--out", default="eval/tc_answers.csv", help="Output CSV path")
    args = parser.parse_args()

    cases_path = Path(__file__).parent / "golden_test_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if args.id:
        cases = [c for c in cases if c["id"] == args.id]

    print("Loading index...", end=" ", flush=True)
    index = IndexManager(use_lightrag=False)
    retriever = Retriever(index)
    print("done", flush=True)

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "TC_ID",
            "คำถาม",
            "PASS/FAIL",
            "failure_detail",
            "คำตอบ",
            "แหล่งอ้างอิง (cited)",
            "must_contain",
            "must_not_contain",
            "expected_sources",
            "notes",
        ])

        for i, case in enumerate(cases):
            tc_id = case["id"]
            query = case["query"]
            print(f"[{i+1}/{len(cases)}] {tc_id}: {query[:50]}", flush=True)

            try:
                results = retriever.retrieve(query, expand=True)
                ranked = rerank(results, query=query)
                answer_data = generate_answer(query, ranked)
                answer = answer_data["answer"]
                cited = [s["name"] for s in answer_data["sources"]]
            except Exception as e:
                answer = f"ERROR: {e}"
                cited = []
                print(f"  ⚠ {e}", flush=True)

            status, detail = _check(case, answer)
            print(f"  → {status}" + (f"  {detail}" if detail else ""), flush=True)

            writer.writerow([
                tc_id,
                query,
                status,
                detail,
                answer,
                ", ".join(cited),
                ", ".join(
                    ("|".join(p) if isinstance(p, list) else p)
                    for p in case.get("must_contain", [])
                ),
                ", ".join(case.get("must_not_contain", [])),
                ", ".join(case.get("expected_sources", [])),
                case.get("notes", ""),
            ])

            if (i + 1) % 5 == 0:
                time.sleep(1)

    print(f"\nDone → {output_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()
