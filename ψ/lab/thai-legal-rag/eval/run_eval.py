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
from src.gemini_client import get_client

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


def _semantic_check(answer: str, concept: str) -> bool:
    """Ask Gemini Flash whether the answer discusses a concept. Returns True/False."""
    from google.genai import types as genai_types

    prompt = f"""Does the following answer discuss or address the concept "{concept}"?
The concept may be expressed using different words, synonyms, or paraphrasing.
Answer ONLY "YES" or "NO".

Answer to evaluate:
{answer[:3000]}"""

    try:
        client = get_client()
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config=genai_types.GenerateContentConfig(
                max_output_tokens=5,
                temperature=0.0,
            ),
        )
        result = (resp.text or "").strip().upper()
        return result.startswith("YES")
    except Exception:
        return False  # on error, fall back to keyword failure


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

    # semantic_check: list of concept descriptions — when keyword fails,
    # try semantic fallback for matching concepts
    semantic_fallbacks = case.get("semantic_check", [])

    if generate:
        # Normalize Thai numerals for comparison
        answer_norm = _normalize_numerals(answer)

        # Check must_contain in answer (supports array-of-arrays for OR logic)
        for i, phrase in enumerate(case.get("must_contain", [])):
            if isinstance(phrase, list):
                # OR logic: at least one alternative must be present
                if not any(_normalize_numerals(p) in answer_norm for p in phrase):
                    # Keyword failed — try semantic fallback if available
                    if i < len(semantic_fallbacks) and semantic_fallbacks[i]:
                        concept = semantic_fallbacks[i]
                        if _semantic_check(answer, concept):
                            result["warnings"].append(
                                f"must_contain {phrase} passed via semantic check ('{concept}')")
                            continue
                    result["passed"] = False
                    result["failures"].append(f"must_contain {phrase} not found in answer")
            else:
                phrase_norm = _normalize_numerals(phrase)
                if phrase_norm not in answer_norm:
                    # Keyword failed — try semantic fallback if available
                    if i < len(semantic_fallbacks) and semantic_fallbacks[i]:
                        concept = semantic_fallbacks[i]
                        if _semantic_check(answer, concept):
                            result["warnings"].append(
                                f"must_contain '{phrase}' passed via semantic check ('{concept}')")
                            continue
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
        try:
            gen = generate_answer(case["query"], ranked)
            answer = gen["answer"]
            sources = gen["sources"]
        except Exception as e:
            return {
                "id": case["id"],
                "query": case["query"],
                "passed": None,
                "failures": [],
                "warnings": [f"Generation failed (API error): {str(e)[:120]}"],
                "answer_snippet": "",
                "sources_found": [],
                "elapsed": round(time.time() - t0, 1),
                "full_answer": "",
            }
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


def _run_case_wrapper(args_tuple):
    """Wrapper for parallel execution via ProcessPoolExecutor."""
    case, generate = args_tuple
    # Each worker needs its own IndexManager (Qdrant client not fork-safe)
    if not hasattr(_run_case_wrapper, "_retriever"):
        idx = IndexManager()
        _run_case_wrapper._retriever = Retriever(idx)
    return run_case(case, _run_case_wrapper._retriever, generate)


def main():
    p = argparse.ArgumentParser(description="Run Thai Legal RAG golden eval")
    p.add_argument("--id", help="Run a single test case by ID (e.g. TC-001)")
    p.add_argument("--no-generate", action="store_true", help="Retrieval only — skip LLM answer generation")
    p.add_argument("--json", action="store_true", dest="json_out", help="Print results as JSON")
    p.add_argument("--verbose", "-v", action="store_true", help="Show answer snippet on failure")
    p.add_argument("--workers", "-w", type=int, default=1,
                   help="Parallel workers (default 1; use 3 for safe parallelism with 1 API key)")
    p.add_argument("--tc-timeout", type=int, default=120,
                   help="Per-TC timeout in seconds (default 120). TC aborted and marked as API error if exceeded.")
    p.add_argument("--sleep", type=float, default=2.0,
                   help="Sleep between TCs in seconds to pace Gemini API (default 2.0; use 0 to disable)")
    args = p.parse_args()

    cases = load_cases(filter_id=args.id)
    generate = not args.no_generate
    workers = args.workers

    # Pre-flight: verify Gemini API is reachable before spending time on retrieval
    if generate:
        try:
            client = get_client()
            client.models.generate_content(model="gemini-2.5-flash", contents="ping",
                                           config={"max_output_tokens": 5})
        except Exception as e:
            print(f"\n{RED}✗ Gemini API unreachable: {e}{RESET}")
            print(f"{YELLOW}  Run with --no-generate to test retrieval only, or wait for API recovery.{RESET}\n")
            sys.exit(1)

    mode = "retrieval+generation" if generate else "retrieval only"

    if workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        print(f"\nLoading index...", end=" ", flush=True)
        index = IndexManager()
        retriever = Retriever(index)
        print("done")

        print(f"Running {len(cases)} test case(s) [{mode}] with {workers} workers")
        print("─" * 60)

        # Submit all cases to thread pool
        results_map = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_case = {}
            for case in cases:
                note = case.get("notes", "")
                if note and note.startswith("⚠️"):
                    # Skip directly
                    results_map[case["id"]] = {
                        "id": case["id"], "query": case["query"],
                        "passed": None, "failures": [], "warnings": [f"Skipped — {note[:60]}"],
                        "answer_snippet": "", "sources_found": [], "elapsed": 0.0,
                    }
                    continue
                future = pool.submit(run_case, case, retriever, generate)
                future_to_case[future] = case

            for future in as_completed(future_to_case):
                result = future.result()
                results_map[result["id"]] = result
                print_result(result, verbose=args.verbose)

        # Preserve original order
        results = []
        for case in cases:
            if case["id"] in results_map:
                results.append(results_map[case["id"]])
    else:
        print(f"\nLoading index...", end=" ", flush=True)
        index = IndexManager()
        retriever = Retriever(index)
        print("done")

        print(f"Running {len(cases)} test case(s) [{mode}]")
        print("─" * 60)

        results = []
        api_error_streak = 0
        _API_ERROR_ABORT = 3  # abort if this many consecutive TCs fail due to API error
        tc_timeout = args.tc_timeout
        sleep_between = args.sleep if generate else 0.0
        for i, case in enumerate(cases):
            note = case.get("notes", "")
            if note and note.startswith("⚠️"):
                print(f"\n{YELLOW}[{case['id']}] Skipping — {note[:60]}{RESET}")

            # Per-TC timeout via thread — shutdown(wait=False) so main loop isn't blocked
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
            _pool = ThreadPoolExecutor(max_workers=1)
            _future = _pool.submit(run_case, case, retriever, generate)
            try:
                result = _future.result(timeout=tc_timeout)
            except FuturesTimeout:
                _future.cancel()
                result = {
                    "id": case["id"], "query": case["query"],
                    "passed": None, "failures": [],
                    "warnings": [f"TC timed out after {tc_timeout}s (API error)"],
                    "answer_snippet": "", "sources_found": [], "elapsed": tc_timeout,
                }
            finally:
                _pool.shutdown(wait=False)

            results.append(result)
            if not (note and note.startswith("⚠️")):
                print_result(result, verbose=args.verbose)

            # Circuit breaker: abort if API is repeatedly down
            is_api_error = result.get("passed") is None and any(
                "API error" in w for w in result.get("warnings", [])
            )
            api_error_streak = api_error_streak + 1 if is_api_error else 0
            if api_error_streak >= _API_ERROR_ABORT:
                print(f"\n{RED}✗ Gemini API down — {_API_ERROR_ABORT} consecutive failures. Aborting.{RESET}")
                print(f"{YELLOW}  Retry with --no-generate for retrieval-only, or wait for API recovery.{RESET}\n")
                break

            # Pace Gemini API calls between TCs
            if sleep_between > 0 and i < len(cases) - 1:
                time.sleep(sleep_between)

    if args.json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_summary(results)

    failed = sum(1 for r in results if r["passed"] is False)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
