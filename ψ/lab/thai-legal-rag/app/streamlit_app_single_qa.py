"""
Thai Legal RAG — Streamlit Query Interface

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data streamlit run app/streamlit_app.py
"""
import re
import sys
from collections import OrderedDict
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer
from src.config import GEMINI_API_KEYS

st.set_page_config(
    page_title="Thai Legal RAG",
    page_icon="⚖️",
    layout="wide",
)

# ── Citation helpers (mirrors export_answers_html.py) ─────────────────────────

def _build_source_map(chunks: list[dict]) -> tuple[dict[int, int], list[dict]]:
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
                "url": chunk.get("file_url", ""),
            })

    chunk_to_src: dict[int, int] = {}
    for i, chunk in enumerate(ordered_chunks, 1):
        name = chunk.get("source_name", chunk.get("source", "unknown"))
        chunk_to_src[i] = source_index[name]

    return chunk_to_src, source_list


def _replace_refs(answer: str, chunk_to_src: dict[int, int]) -> str:
    def replace(m: re.Match) -> str:
        nums = [int(x.strip()) for x in m.group(1).split(",")]
        src_indices = list(dict.fromkeys(chunk_to_src.get(n, n) for n in nums))
        return "[" + ", ".join(str(i) for i in src_indices) + "]"
    return re.sub(r"\[([\d ,]+)\]", replace, answer)


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚖️ Thai Legal RAG")
    st.caption("ระบบค้นหากฎหมายจัดซื้อจัดจ้างภาครัฐ")

    if not GEMINI_API_KEYS:
        st.error("GEMINI_API_KEY not set in environment.")
        st.stop()

    with st.expander("ℹ️ เกี่ยวกับระบบ"):
        st.markdown("""
**Thai Legal RAG**
- Vector: Qdrant + BM25 hybrid
- Embedding: gemini-embedding-2-preview
- LLM: Gemini 2.0 Flash
- Persona: นิติกรชำนาญการพิเศษ
        """)

    if st.button("ล้างประวัติการสนทนา", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── Index (cached across reruns) ───────────────────────────────────────────────

@st.cache_resource(show_spinner="กำลังโหลด index...")
def get_retriever():
    index = IndexManager()
    return Retriever(index)


retriever = get_retriever()

# ── Chat history ───────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

st.header("ถามคำถามกฎหมายจัดซื้อจัดจ้าง")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"เอกสารอ้างอิง ({len(msg['sources'])} รายการ)"):
                for s in msg["sources"]:
                    idx = s["index"]
                    name = s["name"]
                    url = s.get("url", "")
                    if url:
                        st.markdown(f"**[{idx}]** [{name}]({url})")
                    else:
                        st.markdown(f"**[{idx}]** {name}")

# ── Input ──────────────────────────────────────────────────────────────────────

question = st.chat_input("พิมพ์คำถาม เช่น 'ค่าปรับผิดสัญญามีขั้นตอนยังไง'")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("กำลังค้นหาและประมวลผล..."):
            try:
                raw_results = retriever.retrieve(question, expand=True)
                ranked_chunks = rerank(raw_results, query=question)
                result = generate_answer(question, ranked_chunks)

                chunk_to_src, source_list = _build_source_map(ranked_chunks)
                answer = _replace_refs(result["answer"], chunk_to_src)

                st.markdown(answer)

                if source_list:
                    with st.expander(f"เอกสารอ้างอิง ({len(source_list)} รายการ)"):
                        for s in source_list:
                            idx = s["index"]
                            name = s["name"]
                            drive_id = s.get("drive_id", "")
                            if drive_id:
                                url = f"https://drive.google.com/file/d/{drive_id}/view"
                                st.markdown(f"**[{idx}]** [{name}]({url})")
                            else:
                                st.markdown(f"**[{idx}]** {name}")

                st.caption(f"Model: {result['model']} | Chunks: {result['chunks_used']}")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": source_list,
                })

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
                raise
