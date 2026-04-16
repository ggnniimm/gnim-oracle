"""
Export all TC queries with full RAG answers to a self-contained HTML file.
Citations [N] in the answer text are mapped to footnotes at the bottom of each card.

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data_with_ac python3 eval/export_answers_html.py
    THAI_RAG_DATA_DIR=$(pwd)/data_with_ac python3 eval/export_answers_html.py --id TC-066
"""
import argparse
import html
import json
import re
import sys
import time
from collections import OrderedDict
from datetime import datetime
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


def _build_source_map(chunks: list[dict]) -> tuple[dict[int, int], list[dict]]:
    """
    Replicate build_context() ordering to map chunk index [N] → source document index.
    Returns (chunk_to_src_idx, source_list).
    source_list items: {index, name, file_url}
    """
    # Replicate the grouped ordering from build_context()
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for chunk in chunks:
        key = chunk.get("source_name", chunk.get("source", "unknown"))
        grouped.setdefault(key, []).append(chunk)
    ordered_chunks = [c for group in grouped.values() for c in group]

    source_list: list[dict] = []
    source_index: dict[str, int] = {}
    for chunk in ordered_chunks:
        name = chunk.get("source_name", chunk.get("source", "unknown"))
        if name not in source_index:
            idx = len(source_list) + 1
            source_index[name] = idx
            source_list.append({
                "index": idx,
                "name": name,
                "file_url": chunk.get("file_url", ""),
            })

    chunk_to_src: dict[int, int] = {}
    for i, chunk in enumerate(ordered_chunks, 1):
        name = chunk.get("source_name", chunk.get("source", "unknown"))
        chunk_to_src[i] = source_index[name]

    return chunk_to_src, source_list


def _replace_refs(answer: str, chunk_to_src: dict[int, int]) -> str:
    """Replace [N] or [N, M, ...] chunk refs in answer text with [source_index]."""
    def replace(m: re.Match) -> str:
        nums = [int(x.strip()) for x in m.group(1).split(",")]
        src_indices = list(dict.fromkeys(chunk_to_src.get(n, n) for n in nums))
        return "[" + ", ".join(str(i) for i in src_indices) + "]"
    return re.sub(r"\[([\d ,]+)\]", replace, answer)


# ── HTML templates ────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thai Legal RAG — TC Answers</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Sarabun', 'Noto Sans Thai', sans-serif; font-size: 15px;
        background: #f5f5f5; color: #222; }}
header {{ background: #1a237e; color: white; padding: 16px 24px;
          display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
header h1 {{ font-size: 18px; font-weight: 600; flex: 1; }}
header .stats {{ font-size: 13px; opacity: .8; }}
.toolbar {{ background: white; padding: 12px 24px; border-bottom: 1px solid #ddd;
            display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
            position: sticky; top: 0; z-index: 10;
            box-shadow: 0 2px 4px rgba(0,0,0,.08); }}
.filter-btn {{ padding: 5px 15px; border-radius: 20px; border: 1px solid #ccc;
               cursor: pointer; font-size: 13px; background: white; }}
.filter-btn.active {{ background: #1a237e; color: white; border-color: #1a237e; }}
.search {{ flex: 1; max-width: 320px; padding: 6px 12px;
           border: 1px solid #ccc; border-radius: 6px; font-size: 14px; }}
.count {{ font-size: 13px; color: #666; margin-left: auto; }}
.cards {{ padding: 20px 24px; display: flex; flex-direction: column; gap: 14px; }}
.card {{ background: white; border-radius: 8px; overflow: hidden;
         box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
.card.pass {{ border-left: 4px solid #66bb6a; }}
.card.fail {{ border-left: 4px solid #ef5350; }}
.card-header {{ padding: 11px 16px; display: flex; align-items: baseline;
                gap: 10px; cursor: pointer; user-select: none; }}
.card-header:hover {{ background: #fafafa; }}
.tc-id {{ font-weight: 700; font-size: 12px; color: #666; min-width: 58px; }}
.badge {{ padding: 2px 9px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
.badge.pass {{ background: #e8f5e9; color: #2e7d32; }}
.badge.fail {{ background: #ffebee; color: #c62828; }}
.query {{ flex: 1; font-weight: 500; font-size: 14px; }}
.toggle {{ color: #bbb; font-size: 11px; }}
.card-body {{ padding: 0 16px 16px; border-top: 1px solid #f0f0f0; display: none; }}
.card-body.open {{ display: block; }}
.failure {{ background: #fff3e0; border-radius: 4px; padding: 8px 12px;
            font-size: 13px; color: #e65100; margin-top: 12px; }}
.section {{ font-size: 11px; font-weight: 700; text-transform: uppercase;
            color: #aaa; margin: 14px 0 6px; letter-spacing: .5px; }}
.answer {{ white-space: pre-wrap; line-height: 1.75; font-size: 14px; color: #333; }}
/* citation badge inside answer */
.answer sup {{ font-size: 10px; }}
.refs {{ margin-top: 14px; display: flex; flex-direction: column; gap: 5px; }}
.ref-item {{ display: flex; align-items: flex-start; gap: 8px; font-size: 13px; }}
.ref-num {{ min-width: 26px; font-weight: 700; color: #1565c0; }}
.ref-link {{ color: #1565c0; text-decoration: none; }}
.ref-link:hover {{ text-decoration: underline; }}
.ref-link::after {{ content: " ↗"; font-size: 10px; opacity: .6; }}
.no-link {{ color: #555; }}
.hidden {{ display: none !important; }}
</style>
</head>
<body>
<header>
  <h1>Thai Legal RAG — TC Answers</h1>
  <span class="stats">{generated_at} &nbsp;|&nbsp; {pass_count}/{total_count} PASS</span>
</header>
<div class="toolbar">
  <button class="filter-btn active" data-filter="all">ทั้งหมด</button>
  <button class="filter-btn" data-filter="pass">✓ PASS</button>
  <button class="filter-btn" data-filter="fail">✗ FAIL</button>
  <input class="search" type="text" placeholder="ค้นหา TC / คำถาม…" id="search">
  <span class="count" id="count"></span>
</div>
<div class="cards" id="cards">
{cards}
</div>
<script>
const cards = Array.from(document.querySelectorAll('.card'));
let filter = 'all';

document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filter = btn.dataset.filter;
    applyFilters();
  }});
}});
document.getElementById('search').addEventListener('input', applyFilters);

function applyFilters() {{
  const q = document.getElementById('search').value.toLowerCase();
  let n = 0;
  cards.forEach(card => {{
    const statusOk = filter === 'all' || card.classList.contains(filter);
    const textOk = !q || card.dataset.text.includes(q);
    card.classList.toggle('hidden', !(statusOk && textOk));
    if (statusOk && textOk) n++;
  }});
  document.getElementById('count').textContent = n + ' รายการ';
}}

document.querySelectorAll('.card-header').forEach(h => {{
  h.addEventListener('click', () => {{
    const body = h.nextElementSibling;
    const icon = h.querySelector('.toggle');
    body.classList.toggle('open');
    icon.textContent = body.classList.contains('open') ? '▲' : '▼';
  }});
}});

// Auto-open FAIL cards
cards.forEach(card => {{
  if (card.classList.contains('fail')) {{
    card.querySelector('.card-body').classList.add('open');
    card.querySelector('.toggle').textContent = '▲';
  }}
}});

applyFilters();
</script>
</body>
</html>
"""


def _render_card(tc_id, query, status, failure, answer_text, source_list):
    sl = status.lower()
    icon = "✓" if status == "PASS" else "✗"

    failure_html = ""
    if failure:
        failure_html = f'<div class="failure">⚠ {html.escape(failure)}</div>'

    refs_html = ""
    for s in source_list:
        num = s["index"]
        name = html.escape(s["name"])
        file_url = s.get("file_url", "")
        if file_url:
            link = f'<a class="ref-link" href="{file_url}" target="_blank">{name}</a>'
        else:
            link = f'<span class="no-link">{name}</span>'
        refs_html += f'<div class="ref-item"><span class="ref-num">[{num}]</span>{link}</div>'

    data_text = html.escape(f"{tc_id} {query} {status}".lower())

    return f"""<div class="card {sl}" data-text="{data_text}">
  <div class="card-header">
    <span class="tc-id">{html.escape(tc_id)}</span>
    <span class="badge {sl}">{icon} {status}</span>
    <span class="query">{html.escape(query)}</span>
    <span class="toggle">▼</span>
  </div>
  <div class="card-body">
    {failure_html}
    <div class="section">คำตอบ</div>
    <div class="answer">{html.escape(answer_text)}</div>
    <div class="section">References</div>
    <div class="refs">{refs_html}</div>
  </div>
</div>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="Run single TC by ID")
    parser.add_argument("--out", default="eval/tc_answers.html")
    args = parser.parse_args()

    cases_path = Path(__file__).parent / "golden_test_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if args.id:
        cases = [c for c in cases if c["id"] == args.id]

    print("Loading index...", end=" ", flush=True)
    index = IndexManager(use_lightrag=False)
    retriever = Retriever(index)
    print("done", flush=True)

    cards = []
    pass_count = 0

    for i, case in enumerate(cases):
        tc_id = case["id"]
        query = case["query"]
        print(f"[{i+1}/{len(cases)}] {tc_id}: {query[:50]}", flush=True)

        try:
            results = retriever.retrieve(query, expand=True)
            ranked = rerank(results, query=query)
            answer_data = generate_answer(query, ranked)
            raw_answer = answer_data["answer"]

            chunk_to_src, source_list = _build_source_map(ranked)
            answer_text = _replace_refs(raw_answer, chunk_to_src)
        except Exception as e:
            answer_text = f"ERROR: {e}"
            source_list = []
            print(f"  ⚠ {e}", flush=True)

        status, failure = _check(case, answer_text)
        if status == "PASS":
            pass_count += 1
        print(f"  → {status}" + (f"  {failure}" if failure else ""), flush=True)

        cards.append(_render_card(tc_id, query, status, failure, answer_text, source_list))

        if (i + 1) % 5 == 0:
            time.sleep(1)

    output = _HTML_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        pass_count=pass_count,
        total_count=len(cases),
        cards="\n".join(cards),
    )

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    print(f"\nDone → {output_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()
