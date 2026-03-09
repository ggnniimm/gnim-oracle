#!/usr/bin/env python3
"""
Thai Legal RAG — Evaluation Runner

Runs golden test cases through the full pipeline (retrieve → rerank → generate)
and checks must_contain phrases in the answer and expected_sources in citations.

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/run_eval.py
    THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/run_eval.py --no-generate   # retrieval only
    THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/run_eval.py --id TC-001     # single case
    THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/run_eval.py --json          # machine-readable output
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer

# ── ANSI colours ────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

CASES_FILE = Path(__file__).parent / "golden_test_cases.json"

_THAI_DIGIT_MAP = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def _normalize_numerals(text: str) -> str:
    """Convert Thai numerals (๐-๙) to Arabic (0-9) for comparison."""
    return text.translate(_THAI_DIGIT_MAP)


def load_cases(filter_id: str | None = None) -> list[dict]:
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if filter_id:
        cases = [c for c in cases if c["id"] == filter_id]
        if not cases:
            print(f"{RED}No test case with id={filter_id!r}{RESET}")
            sys.exit(1)
    return cases


def check_case(case: dict, answer: str, sources: list[dict], generate: bool) -> dict:
    """Return pass/fail details for one test case."""
    result = {
        "id": case["id"],
        "query": case["query"],
        "passed": True,
        "failures": [],
        "warnings": [],
        "answer_snippet": answer[:300] if answer else "",
        "sources_found": [s.get("name", "") for s in sources],
    }

    if generate:
        # Normalize Thai numerals for comparison
        answer_norm = _normalize_numerals(answer)

        # Check must_contain in answer
        for phrase in case.get("must_contain", []):
            phrase_norm = _normalize_numerals(phrase)
            if phrase_norm not in answer_norm:
                result["passed"] = False
                result["failures"].append(f"must_contain '{phrase}' not found in answer")

        # Check must_not_contain
        for phrase in case.get("must_not_contain", []):
            phrase_norm = _normalize_numerals(phrase)
            if phrase_norm in answer_norm:
                result["passed"] = False
                result["failures"].append(f"must_not_contain '{phrase}' was found in answer")
    else:
        # Retrieval-only: skip answer checks, note it
        if case.get("must_contain"):
            result["warnings"].append("must_contain not checked (--no-generate)")

    # Check expected_sources (soft check — warn, don't fail)
    source_names = " ".join(s.get("name", "") for s in sources)
    for expected in case.get("expected_sources", []):
        if expected not in source_names:
            result["warnings"].append(f"expected source '{expected}' not cited")

    return result


def run_case(
    case: dict,
    retriever: Retriever,
    generate: bool,
) -> dict:
    t0 = time.time()

    # Skip unverified cases (no must_contain and no expected_sources)
    unverified = (
        not case.get("must_contain")
        and not case.get("must_not_contain")
        and not case.get("expected_sources")
    )
    if unverified:
        return {
            "id": case["id"],
            "query": case["query"],
            "passed": None,  # None = skipped
            "failures": [],
            "warnings": ["Skipped — unverified (no must_contain defined)"],
            "answer_snippet": "",
            "sources_found": [],
            "elapsed": 0.0,
        }

    raw = retriever.retrieve(case["query"])
    ranked = rerank(raw, query=case["query"])

    answer = ""
    sources = []
    if generate and ranked:
        gen = generate_answer(case["query"], ranked)
        answer = gen["answer"]
        sources = gen["sources"]
    else:
        # Retrieval-only: check source names from chunks
        seen = set()
        for chunk in ranked:
            name = chunk.get("source_name", "")
            if name and name not in seen:
                seen.add(name)
                sources.append({"name": name})

    result = check_case(case, answer, sources, generate)
    result["elapsed"] = round(time.time() - t0, 1)
    result["full_answer"] = answer
    return result


def print_result(result: dict, verbose: bool = False):
    status = result["passed"]
    rid = result["id"]
    query = result["query"]

    if status is None:
        icon = f"{YELLOW}SKIP{RESET}"
    elif status:
        icon = f"{GREEN}PASS{RESET}"
    else:
        icon = f"{RED}FAIL{RESET}"

    elapsed = result.get("elapsed", 0)
    print(f"\n{BOLD}[{rid}]{RESET} {icon}  ({elapsed}s)")
    print(f"  Query   : {query}")

    if result["sources_found"]:
        print(f"  Sources : {', '.join(result['sources_found'][:4])}")

    for w in result["warnings"]:
        print(f"  {YELLOW}⚠ {w}{RESET}")

    if not result["passed"] and result["passed"] is not None:
        for f in result["failures"]:
            print(f"  {RED}✗ {f}{RESET}")
        if verbose and result["answer_snippet"]:
            print(f"\n  {CYAN}Answer snippet:{RESET}")
            print(f"  {result['answer_snippet'][:500]}")

    if verbose and result.get("full_answer"):
        print(f"\n  {CYAN}Full answer:{RESET}")
        print(result["full_answer"])


def print_summary(results: list[dict]):
    total = len(results)
    skipped = sum(1 for r in results if r["passed"] is None)
    passed = sum(1 for r in results if r["passed"] is True)
    failed = sum(1 for r in results if r["passed"] is False)
    ran = total - skipped

    print(f"\n{'═' * 60}")
    print(f"{BOLD}SUMMARY{RESET}  {passed}/{ran} passed", end="")
    if skipped:
        print(f"  ({skipped} skipped)", end="")
    print()

    if failed:
        print(f"\n{RED}Failed cases:{RESET}")
        for r in results:
            if r["passed"] is False:
                print(f"  ✗ {r['id']}  {r['query']}")
    print(f"{'═' * 60}")


def main():
    p = argparse.ArgumentParser(description="Run Thai Legal RAG golden eval")
    p.add_argument("--id", help="Run a single test case by ID (e.g. TC-001)")
    p.add_argument("--no-generate", action="store_true", help="Retrieval only — skip LLM answer generation")
    p.add_argument("--json", action="store_true", dest="json_out", help="Print results as JSON")
    p.add_argument("--verbose", "-v", action="store_true", help="Show answer snippet on failure")
    args = p.parse_args()

    cases = load_cases(filter_id=args.id)
    generate = not args.no_generate

    print(f"\nLoading index...", end=" ", flush=True)
    index = IndexManager(use_lightrag=False)
    retriever = Retriever(index)
    print("done")

    mode = "retrieval+generation" if generate else "retrieval only"
    print(f"Running {len(cases)} test case(s) [{mode}]")
    print("─" * 60)

    results = []
    for case in cases:
        note = case.get("notes", "")
        if note and note.startswith("⚠️"):
            print(f"\n{YELLOW}[{case['id']}] Skipping — {note[:60]}{RESET}")

        result = run_case(case, retriever, generate)
        results.append(result)
        if not (note and note.startswith("⚠️")):
            print_result(result, verbose=args.verbose)

    if args.json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_summary(results)

    failed = sum(1 for r in results if r["passed"] is False)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
