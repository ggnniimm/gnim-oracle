"""
Thai Legal RAG — Multi-session Chat Interface

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data streamlit run app/streamlit_app.py
"""
import json
import os
import re
import sys
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import streamlit as st
import streamlit_authenticator as stauth
import streamlit_authenticator.utilities.validator as _stauth_validator
import yaml

# Remove all password restrictions
_stauth_validator.Validator.diagnose_password = lambda self, password: ""
_stauth_validator.Validator.validate_password = lambda self, password: True

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


def _translate_register_error(msg: str) -> str:
    _map = {
        "Username/email already taken": "Username หรือ Email นี้มีอยู่แล้วในระบบ",
        "Email already taken": "Email นี้มีอยู่แล้วในระบบ",
        "Username is not valid": "Username ไม่ถูกต้อง (ใช้ตัวอักษรและตัวเลขเท่านั้น)",
        "Email is not valid": "รูปแบบ Email ไม่ถูกต้อง",
        "First name is not valid": "ชื่อไม่ถูกต้อง",
        "Last name is not valid": "นามสกุลไม่ถูกต้อง",
        "Passwords do not match": "รหัสผ่านไม่ตรงกัน",
        "Password/repeat password fields cannot be empty": "กรุณากรอกรหัสผ่านให้ครบ",
    }
    for key, thai in _map.items():
        if key in msg:
            return thai
    return f"เกิดข้อผิดพลาด: {msg}"


# ── Auth ────────────────────────────────────────────────────────────────────────

_AUTH_CONFIG_PATH = Path(__file__).parent / "auth_config.yaml"

with open(_AUTH_CONFIG_PATH) as f:
    _auth_config = yaml.safe_load(f)

authenticator = stauth.Authenticate(
    _auth_config["credentials"],
    _auth_config["cookie"]["name"],
    _auth_config["cookie"]["key"],
    _auth_config["cookie"]["expiry_days"],
)

if not st.session_state.get("authentication_status"):
    tab_login, tab_register, tab_forgot = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก", "ลืมรหัสผ่าน"])

    with tab_login:
        authenticator.login()
        if st.session_state.get("authentication_status") is False:
            st.error("Username หรือ Password ไม่ถูกต้อง")
            st.markdown("ยังไม่ได้สมัครสมาชิกใช่ไหม?")
            if st.button("➡️ สมัครสมาชิกเลย", type="primary"):
                st.session_state["show_inline_register"] = True
            if st.session_state.get("show_inline_register"):
                st.divider()
                st.markdown("#### สมัครสมาชิก")
                try:
                    email, username, name = authenticator.register_user(
                        pre_authorized=None,
                        captcha=False,
                        key="inline_register",
                    )
                    if username:
                        with open(_AUTH_CONFIG_PATH, "w") as f:
                            yaml.dump(_auth_config, f, allow_unicode=True, default_flow_style=False)
                        st.session_state["show_inline_register"] = False
                        st.success(f"สมัครสำเร็จ ({username}) กรุณา login ด้านบน")
                except Exception as e:
                    st.error(_translate_register_error(str(e)))

    with tab_register:
        try:
            email, username, name = authenticator.register_user(
                pre_authorized=None,
                captcha=False,
            )
            if username:
                with open(_AUTH_CONFIG_PATH, "w") as f:
                    yaml.dump(_auth_config, f, allow_unicode=True, default_flow_style=False)
                st.success(f"สมัครสมาชิกสำเร็จ ({username}) กรุณาไปที่ tab 'เข้าสู่ระบบ'")
        except Exception as e:
            st.error(_translate_register_error(str(e)))

    with tab_forgot:
        try:
            username, email, new_password = authenticator.forgot_password(captcha=False)
            if username:
                with open(_AUTH_CONFIG_PATH, "w") as f:
                    yaml.dump(_auth_config, f, allow_unicode=True, default_flow_style=False)
                st.success(f"รหัสผ่านใหม่ของ **{username}**:")
                st.code(new_password)
                st.caption("กรุณาจดรหัสผ่านนี้ไว้ แล้วไปเปลี่ยนหลัง login")
            elif username is False:
                st.error("ไม่พบ username นี้ในระบบ")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

    st.stop()

_USERNAME = st.session_state.get("username", "guest")

# ── Chat persistence ────────────────────────────────────────────────────────────

_DATA_DIR = Path(os.getenv("THAI_RAG_DATA_DIR", "data"))
_CHAT_STORE = _DATA_DIR / f"chat_sessions_{_USERNAME}.json"


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
    with st.popover(f"👤 {st.session_state.get('name', _USERNAME)}", use_container_width=True):
        st.caption(f"@{_USERNAME}")
        st.divider()
        authenticator.logout(button_name="ออกจากระบบ", location="main")
        st.divider()
        st.markdown("**🔑 เปลี่ยนรหัสผ่าน**")
        try:
            if authenticator.reset_password(_USERNAME, key="sidebar_reset"):
                with open(_AUTH_CONFIG_PATH, "w") as f:
                    yaml.dump(_auth_config, f, allow_unicode=True, default_flow_style=False)
                st.success("เปลี่ยนรหัสผ่านสำเร็จ")
        except Exception as e:
            st.error(str(e))

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
                            url = s.get("url", "")
                            if url:
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
