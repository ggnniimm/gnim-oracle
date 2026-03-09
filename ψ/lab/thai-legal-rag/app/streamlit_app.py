"""
Thai Legal RAG — Streamlit Query Interface

Features:
- Natural language query in Thai
- Automatic fusion retrieval (FAISS + LightRAG)
- Source citations with Drive links
- Chat history per category
- API keys from env only (no UI input)
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.manager import IndexManager
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import rerank
from src.generation.generator import generate_answer
from src.config import DRIVE_FOLDER_IDS, GEMINI_API_KEYS

st.set_page_config(
    page_title="Thai Legal RAG",
    page_icon="⚖️",
    layout="wide",
)

# --- Sidebar ---
with st.sidebar:
    st.title("⚖️ Thai Legal RAG")
    st.caption("ระบบค้นหากฎหมายจัดซื้อจัดจ้างภาครัฐ")

    if not GEMINI_API_KEYS:
        st.error("GEMINI_API_KEYS not set in environment.")
        st.stop()

    category = st.selectbox(
        "หมวดหมู่เอกสาร",
        options=list(DRIVE_FOLDER_IDS.keys()),
        index=0,
    )

    use_lightrag = st.checkbox("ใช้ LightRAG (Graph-based)", value=True)

    with st.expander("ℹ️ เกี่ยวกับระบบ"):
        st.markdown("""
        **Thai Legal RAG v2**
        - OCR: Gemini Vision
        - Vector Search: FAISS + LightRAG
        - LLM: Gemini 2.0 Flash
        - Persona: นิติกรชำนาญการพิเศษ
        """)

# --- Initialize ---
@st.cache_resource
def get_index(use_lightrag_flag: bool) -> tuple:
    index = IndexManager(use_lightrag=use_lightrag_flag)
    retriever = Retriever(index)
    return index, retriever


index, retriever = get_index(use_lightrag)

# --- Chat history ---
chat_key = f"chat_{category}"
if chat_key not in st.session_state:
    st.session_state[chat_key] = []

# --- Main ---
st.header(f"ถามคำถามกฎหมาย — {category}")

# Display chat history
for msg in st.session_state[chat_key]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"📚 แหล่งอ้างอิง ({len(msg['sources'])} เอกสาร)"):
                for src in msg["sources"]:
                    drive_id = src.get("drive_id", "")
                    name = src.get("name", "Unknown")
                    if drive_id:
                        url = f"https://drive.google.com/file/d/{drive_id}/view"
                        st.markdown(f"- [{name}]({url})")
                    else:
                        st.markdown(f"- {name}")

# Query input
question = st.chat_input("พิมพ์คำถามของคุณ เช่น 'ค่าปรับผิดสัญญามีขั้นตอนยังไง'")

if question:
    # Show user message
    st.session_state[chat_key].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Retrieve + generate
    with st.chat_message("assistant"):
        with st.spinner("กำลังค้นหาและประมวลผล..."):
            try:
                raw_results = retriever.retrieve(question, expand=True)
                ranked_chunks = rerank(raw_results, query=question)
                result = generate_answer(question, ranked_chunks)

                st.markdown(result["answer"])

                if result["sources"]:
                    with st.expander(f"📚 แหล่งอ้างอิง ({len(result['sources'])} เอกสาร)"):
                        for src in result["sources"]:
                            drive_id = src.get("drive_id", "")
                            name = src.get("name", "Unknown")
                            if drive_id:
                                url = f"https://drive.google.com/file/d/{drive_id}/view"
                                st.markdown(f"- [{name}]({url})")
                            else:
                                st.markdown(f"- {name}")

                st.caption(
                    f"Model: {result['model']} | Chunks used: {result['chunks_used']} | "
                    f"FAISS: {len(raw_results.get('faiss', []))} | "
                    f"LightRAG: {len(raw_results.get('lightrag', []))}"
                )

                # Save to history
                st.session_state[chat_key].append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["sources"],
                })

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
