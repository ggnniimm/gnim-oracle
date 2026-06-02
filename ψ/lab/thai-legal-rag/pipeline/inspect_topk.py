"""Print top-K reranked chunks for queries — to diff retrieval behavior across
Approach A / B / baseline on ID+content queries (which the golden set can't cover)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.retrieval.query_expand import is_specific_query

logging.basicConfig(level=logging.ERROR)

QUERIES = [
    "ว 397 ผ่อนผันเรื่องอะไร",
    "ว 214 กำหนดกรอบระยะเวลาอย่างไร",
]

def main():
    idx = IndexManager(); r = Retriever(idx)
    for q in QUERIES:
        raw = r.retrieve(q, expand=True)
        ranked = rerank(raw, query=q)
        print(f"\n=== {q!r}  (specific={is_specific_query(q)}, "
              f"pool v={len(raw.get('vector',[]))} b={len(raw.get('bm25',[]))}, ranked={len(ranked)}) ===")
        for i, ch in enumerate(ranked[:10], 1):
            sn = str(ch.get("source_name", ""))[:38]
            print(f"  {i:2}. {sn:<40} {str(ch.get('text',''))[:55]}")

if __name__ == "__main__":
    main()
