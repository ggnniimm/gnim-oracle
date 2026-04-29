#!/usr/bin/env python3
"""
Consistency Check — run a query N times through the RAG pipeline,
compare answers, citations, and retrieval stability.

Usage:
    cd ψ/lab/thai-legal-rag
    QDRANT_URL=http://localhost:6333 THAI_RAG_DATA_DIR=$(pwd)/data \
        python3 scripts/consistency_check.py "ผู้รับจ้างส่งของช้า..." --n 3

    # Save as eval candidate (staging — review before merging into golden_test_cases.json)
    python3 scripts/consistency_check.py "<query>" --n 3 --save-tc

Output: data/consistency_runs/YYYY-MM-DD_HHMM_<slug>.md (gitignored).
TC candidates: eval/golden_test_cases.candidates.json (gitignored — review then merge manually).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer

OUT_DIR = Path(__file__).parent.parent / "data" / "consistency_runs"
GOLDEN_PATH = Path(__file__).parent.parent / "eval" / "golden_test_cases.json"
CANDIDATES_PATH = Path(__file__).parent.parent / "eval" / "golden_test_cases.candidates.json"


def _slugify(query: str, max_len: int = 50) -> str:
    s = re.sub(r"[^฀-๿a-zA-Z0-9\s]", "", query)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:max_len] or "query"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def run_once(query: str, retriever: Retriever, idx: int) -> dict:
    t0 = time.time()
    raw = retriever.retrieve(query)
    ranked = rerank(raw, query=query)
    gen = generate_answer(query, ranked)
    return {
        "run": idx,
        "answer": gen["answer"],
        "answer_hash": _hash(gen["answer"]),
        "sources": [s.get("name", "") for s in gen.get("sources", [])],
        "top_retrieved": [c.get("source_name", "") for c in ranked[:5]],
        "chunks_used": gen.get("chunks_used", 0),
        "elapsed": round(time.time() - t0, 1),
    }


def _next_tc_id() -> str:
    if not GOLDEN_PATH.exists():
        return "TC-001"
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    nums = [int(c["id"].split("-")[1]) for c in cases if c.get("id", "").startswith("TC-")]
    return f"TC-{(max(nums) + 1) if nums else 1:03d}"


def build_tc_candidate(query: str, runs: list[dict], agg: dict, tc_id: str) -> dict:
    """Build a TC stub from consistency-run results. expected_sources and must_contain
    are intentionally left empty — Ming reviews _candidate_sources (full filenames)
    and trims to the meaningful substring (e.g., the circular number '012804') before
    merging into golden_test_cases.json. Same for must_contain phrases."""
    # Intersection of source filenames across runs — Ming trims these to substrings
    name_sets = [set(r.get("sources", [])) for r in runs]
    common_names = sorted(set.intersection(*name_sets)) if name_sets and all(name_sets) else []

    note_parts = [
        f"Auto-generated from consistency_check on {datetime.now().strftime('%Y-%m-%d %H:%M')}.",
        f"Runs={agg['n']}, unique_answers={agg['unique_answers']}/{agg['n']}, "
        f"sources_identical={agg['sources_identical']}, jaccard={agg['retrieval_jaccard_avg']}.",
        "TODO before merging into golden_test_cases.json:",
        "  (1) trim _candidate_sources to substrings (e.g. 'กวจ_012804_...' → '012804') and move to expected_sources;",
        "  (2) fill must_contain by reading the consistency-run report.",
    ]

    return {
        "id": tc_id,
        "query": query,
        "expected_sources": [],
        "must_contain": [],
        "must_not_contain": [],
        "_candidate_sources": common_names,
        "notes": " ".join(note_parts),
    }


def save_tc_candidate(tc: dict) -> Path:
    """Append TC to staging file (creates if missing). Doesn't touch golden_test_cases.json."""
    if CANDIDATES_PATH.exists():
        existing = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    else:
        existing = []
    existing.append(tc)
    CANDIDATES_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return CANDIDATES_PATH


def aggregate(runs: list[dict]) -> dict:
    n = len(runs)
    source_sets = [set(r["sources"][:3]) for r in runs]
    sources_identical = all(s == source_sets[0] for s in source_sets) if n > 1 else True

    retrieval_sets = [set(r["top_retrieved"]) for r in runs]
    jaccards = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = retrieval_sets[i], retrieval_sets[j]
            if a or b:
                jaccards.append(len(a & b) / len(a | b))
    avg_jaccard = round(sum(jaccards) / len(jaccards), 3) if jaccards else 1.0

    return {
        "n": n,
        "sources_identical": sources_identical,
        "retrieval_jaccard_avg": avg_jaccard,
        "unique_answers": len(set(r["answer_hash"] for r in runs)),
        "avg_latency": round(sum(r["elapsed"] for r in runs) / n, 1),
    }


def render_md(query: str, runs: list[dict], agg: dict, timestamp: str) -> str:
    lines = [
        f"# Consistency Check — {timestamp}",
        "",
        f"**Query**: {query}",
        f"**Runs**: {agg['n']}",
        "",
        "## Summary",
        f"- Top-3 citations identical: {'✓ Yes' if agg['sources_identical'] else '⚠️ No'}",
        f"- Top-5 retrieval Jaccard avg: {agg['retrieval_jaccard_avg']}",
        f"- Distinct unique answers: {agg['unique_answers']}/{agg['n']}",
        f"- Avg latency: {agg['avg_latency']}s",
        "",
        "## Citation Stability (referenced docs from `gen.sources`)",
        "| Run | Sources |",
        "|---|---|",
    ]
    for r in runs:
        srcs = ", ".join(r["sources"][:5]) or "(none)"
        lines.append(f"| {r['run']} | {srcs} |")

    lines += [
        "",
        "## Retrieval Stability (top-5 from reranker)",
        "| Run | Top-5 docs |",
        "|---|---|",
    ]
    for r in runs:
        docs = ", ".join(r["top_retrieved"]) or "(none)"
        lines.append(f"| {r['run']} | {docs} |")

    lines += ["", "## Answers (full)"]
    for r in runs:
        lines += [
            "",
            f"### Run {r['run']} — hash `{r['answer_hash']}`, {r['elapsed']}s, chunks={r['chunks_used']}",
            "",
            r["answer"],
            "",
        ]

    lines.append("## Verdict")
    if agg["sources_identical"] and agg["retrieval_jaccard_avg"] >= 0.8:
        lines.append("- ✓ Retrieval & citations stable")
    else:
        lines.append("- ⚠️ Retrieval/citation drift — investigate `reranker.py`, glossary, cross-refs")
    if agg["unique_answers"] == 1:
        lines.append("- ✓ Answer identical across runs")
    elif agg["unique_answers"] <= max(1, agg["n"] // 2 + 1):
        lines.append(f"- ⚠️ Answer variance ({agg['unique_answers']}/{agg['n']}) — likely LLM stochasticity")
    else:
        lines.append(f"- 🔴 High answer variance ({agg['unique_answers']}/{agg['n']}) — review prompt rules")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG consistency check")
    parser.add_argument("query", help="Query text")
    parser.add_argument("--n", type=int, default=3, help="Number of runs (default: 3)")
    parser.add_argument("--no-save", action="store_true", help="Skip saving the MD report")
    parser.add_argument(
        "--save-tc",
        action="store_true",
        help="Append a TC stub to eval/golden_test_cases.candidates.json (review before merging into golden)",
    )
    parser.add_argument("--tc-id", help="Override TC id (default: next free TC-NNN from golden file)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📊 Consistency check: {args.query[:80]!r} × {args.n}")
    print("   Initializing retriever...", flush=True)
    manager = IndexManager()
    retriever = Retriever(manager)

    runs: list[dict] = []
    for i in range(1, args.n + 1):
        print(f"   Run {i}/{args.n}...", end=" ", flush=True)
        r = run_once(args.query, retriever, i)
        runs.append(r)
        print(f"done ({r['elapsed']}s, hash {r['answer_hash']}, {len(r['sources'])} sources)")

    agg = aggregate(runs)

    print("\n📋 Summary:")
    print(f"   Top-3 sources identical: {'✓' if agg['sources_identical'] else '⚠️'}")
    print(f"   Retrieval Jaccard avg:   {agg['retrieval_jaccard_avg']}")
    print(f"   Unique answers:          {agg['unique_answers']}/{agg['n']}")
    print(f"   Avg latency:             {agg['avg_latency']}s")

    if not args.no_save:
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        filename = f"{now.strftime('%Y-%m-%d_%H%M')}_{_slugify(args.query)}.md"
        out_path = OUT_DIR / filename
        out_path.write_text(render_md(args.query, runs, agg, timestamp), encoding="utf-8")
        rel = out_path.relative_to(Path(__file__).parent.parent)
        print(f"\n💾 Saved report: {rel}")

    if args.save_tc:
        tc_id = args.tc_id or _next_tc_id()
        tc = build_tc_candidate(args.query, runs, agg, tc_id)
        path = save_tc_candidate(tc)
        rel = path.relative_to(Path(__file__).parent.parent)
        print(f"\n📝 TC candidate appended: {rel}")
        print(f"   ID: {tc_id}, _candidate_sources: {len(tc['_candidate_sources'])} filenames")
        print("   ⚠️  Trim _candidate_sources → expected_sources, fill must_contain, then merge into golden.")


if __name__ == "__main__":
    main()
