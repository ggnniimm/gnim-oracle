"""Measure the rank of ID-style (ว NNN) documents when queried by their number.

Replicates the 2026-05-28 handoff test, but on the current (clean-BM25) index.
For each "ว NNN" query, run the real retrieve+rerank pipeline and report the
1-based rank of the first chunk belonging to that ว-circular (matched by
ref_number canonical "ว <thai>" or by the canonical source_name).
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank

logging.basicConfig(level=logging.ERROR)

_THAI = "๐๑๒๓๔๕๖๗๘๙"


def to_thai(s: str) -> str:
    return "".join(_THAI[int(c)] if c.isdigit() else c for c in s)


# (number, canonical source_name substring) — the actual ว-circular document.
TARGETS = [
    ("397", "_ว397_"),
    ("214", "ว_214"),
    ("181", "/ว ๑๘๑"),     # match via ref_number (no clean filename)
    ("110", "๑๑๐/๒๕๖๑"),   # match via ref_number
    ("298", "_ว298_"),
    ("299", "_ว299_"),
    ("651", "_ว651_"),
    ("189", "_ว189_"),
]


def matches(chunk: dict, marker: str) -> bool:
    sn = str(chunk.get("source_name", ""))
    rn = str(chunk.get("ref_number", ""))
    return marker in sn or marker in rn


def main():
    index = IndexManager()
    retriever = Retriever(index)

    print(f"{'doc':<8}{'rank':<8}{'matched source_name'}")
    print("-" * 70)
    for num, marker in TARGETS:
        query = f"ว {num}"
        raw = retriever.retrieve(query, expand=True)
        ranked = rerank(raw, query=query)
        rank = None
        matched_src = ""
        for i, ch in enumerate(ranked, 1):
            if matches(ch, marker):
                rank = i
                matched_src = str(ch.get("source_name", ""))[:40]
                break
        rank_str = str(rank) if rank else f"MISS (of {len(ranked)})"
        print(f"ว{num:<7}{rank_str:<8}{matched_src}")


if __name__ == "__main__":
    main()
