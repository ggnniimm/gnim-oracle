"""
Thai Legal RAG — Multi-session Chat Interface

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data streamlit run app/streamlit_app.py
"""
import json
import re
import sys
import time
import uuid
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

# ── Chat persistence ────────────────────────────────────────────────────────────

import os
_DATA_DIR = Path(os.getenv("THAI_RAG_DATA_DIR", "data"))
_CHAT_STORE = _DATA_DIR / "chat_sessions.json"


def _load_chats() -> dict:
    if _CHAT_STORE.exists():
        try:
            return json.loads(_CHAT_STORE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_chats(chats: dict) -> None:
    _CHAT_STORE.write_text(
        json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _new_chat_id() -> str:
    return str(uuid.uuid4())[:8]


def _chat_title(messages: list) -> str:
    for m in messages:
        if m["role"] == "user":
            text = m["content"]
            return text[:45] + "…" if len(text) > 45 else text
    return "บทสนทนาใหม่"


# ── Session init ────────────────────────────────────────────────────────────────

if "chats" not in st.session_state:
    st.session_state.chats = _load_chats()

if "current_chat_id" not in st.session_state:
    if st.session_state.chats:
        # Open most recent chat
        st.session_state.current_chat_id = max(
            st.session_state.chats,
            key=lambda cid: st.session_state.chats[cid].get("updated_at", 0),
        )
    else:
        cid = _new_chat_id()
        st.session_state.chats[cid] = {"messages": [], "updated_at": time.time()}
        st.session_state.current_chat_id = cid


def current_messages() -> list:
    return st.session_state.chats[st.session_state.current_chat_id]["messages"]


# ── Citation helpers ────────────────────────────────────────────────────────────

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


# ── Index (cached across reruns) ───────────────────────────────────────────────

@st.cache_resource(show_spinner="กำลังโหลด index...")
def get_retriever():
    index = IndexManager(use_lightrag=False)
    return Retriever(index)


if not GEMINI_API_KEYS:
    st.error("GEMINI_API_KEY not set in environment.")
    st.stop()

retriever = get_retriever()

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚖️ Thai Legal RAG")

    if st.button("＋  New chat", use_container_width=True, type="primary"):
        cid = _new_chat_id()
        st.session_state.chats[cid] = {"messages": [], "updated_at": time.time()}
        st.session_state.current_chat_id = cid
        _save_chats(st.session_state.chats)
        st.rerun()

    st.divider()

    # List chats sorted by recency
    sorted_chats = sorted(
        st.session_state.chats.items(),
        key=lambda x: x[1].get("updated_at", 0),
        reverse=True,
    )

    for cid, chat in sorted_chats:
        title = _chat_title(chat["messages"])
        is_active = cid == st.session_state.current_chat_id
        label = f"**{title}**" if is_active else title

        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(label, key=f"chat_{cid}", use_container_width=True):
                st.session_state.current_chat_id = cid
                st.rerun()
        with col2:
            if st.button("🗑", key=f"del_{cid}", help="ลบบทสนทนา"):
                del st.session_state.chats[cid]
                if st.session_state.current_chat_id == cid:
                    if st.session_state.chats:
                        st.session_state.current_chat_id = next(
                            iter(st.session_state.chats)
                        )
                    else:
                        ncid = _new_chat_id()
                        st.session_state.chats[ncid] = {"messages": [], "updated_at": time.time()}
                        st.session_state.current_chat_id = ncid
                _save_chats(st.session_state.chats)
                st.rerun()

    st.divider()
    with st.expander("ℹ️ เกี่ยวกับระบบ"):
        st.markdown("""
**Thai Legal RAG**
- Vector: Qdrant + BM25 hybrid
- Embedding: gemini-embedding-2-preview
- LLM: Gemini 2.0 Flash
- Persona: นิติกรชำนาญการพิเศษ
        """)

# ── Main chat area ─────────────────────────────────────────────────────────────

msgs = current_messages()

if not msgs:
    st.markdown("### ถามคำถามกฎหมายจัดซื้อจัดจ้าง")
    st.caption("เริ่มต้นด้วยการพิมพ์คำถาม เช่น 'ค่าปรับผิดสัญญามีขั้นตอนยังไง'")
else:
    for msg in msgs:
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
    msgs.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("กำลังค้นหาและประมวลผล..."):
            try:
                chat_history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in msgs[:-1]  # exclude current question
                ]
                raw_results = retriever.retrieve(question, expand=True, history=chat_history)
                ranked_chunks = rerank(raw_results, query=question)
                result = generate_answer(question, ranked_chunks, history=chat_history)

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

                msgs.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": source_list,
                })

                # Save to file
                st.session_state.chats[st.session_state.current_chat_id]["messages"] = msgs
                st.session_state.chats[st.session_state.current_chat_id]["updated_at"] = time.time()
                _save_chats(st.session_state.chats)

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
                raise
