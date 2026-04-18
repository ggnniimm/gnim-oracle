"""
Thai Legal RAG — Multi-session Chat Interface (Claude Design)

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data streamlit run app/streamlit_app.py
"""
import datetime
import html as _html
import json
import os
import re
import sys
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import markdown as _md_lib
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
    initial_sidebar_state="expanded",
)

# ── Design System CSS ──────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600&family=IBM+Plex+Serif:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --font-thai:  'IBM Plex Sans Thai', system-ui, sans-serif;
  --font-serif: 'IBM Plex Serif', Georgia, serif;
  --font-mono:  'IBM Plex Mono', ui-monospace, monospace;

  --paper:   oklch(0.985 0.004 80);
  --paper-2: oklch(0.970 0.006 80);
  --paper-3: oklch(0.940 0.009 78);
  --ink:     oklch(0.18 0.020 260);
  --ink-2:   oklch(0.38 0.018 260);
  --ink-3:   oklch(0.58 0.014 260);

  --accent:    oklch(0.42 0.090 260);
  --accent-lt: oklch(0.94 0.025 260);
  --seal:      oklch(0.50 0.110 68);
  --seal-bg:   oklch(0.95 0.040 78);

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
}

/* ── Base ── */
body, .stApp { background: var(--paper) !important; font-family: var(--font-thai) !important; color: var(--ink) !important; }

/* ── Hide chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Main container ── */
.main .block-container {
  padding-top: 1.25rem !important;
  padding-bottom: 5rem !important;
  max-width: 780px !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: var(--paper-2) !important;
  border-right: 1px solid var(--paper-3) !important;
}
section[data-testid="stSidebar"] > div { background: transparent !important; }
section[data-testid="stSidebar"] ::-webkit-scrollbar { width: 3px; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background: var(--paper-3); border-radius: 2px; }

/* Sidebar buttons */
section[data-testid="stSidebar"] button { font-family: var(--font-thai) !important; border-radius: var(--radius-md) !important; }
section[data-testid="stSidebar"] button[kind="primary"] { background: var(--accent) !important; border-color: var(--accent) !important; }

/* ── Brand mark (sidebar top) ── */
.brand-row { display: flex; align-items: center; gap: 10px; padding: 4px 0 12px; }
.brand-glyph {
  width: 38px; height: 38px;
  background: var(--accent); color: white;
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-serif); font-size: 22px; font-weight: 600;
  flex-shrink: 0;
}
.brand-text { line-height: 1.2; }
.brand-name { font-size: 14px; font-weight: 600; color: var(--ink); }
.brand-sub  { font-size: 10px; color: var(--ink-3); }

/* ── History group label ── */
.hist-group {
  font-size: 9.5px; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-3);
  padding: 10px 0 3px; margin: 0;
}

/* ── Q card ── */
.q-card {
  background: var(--paper-2);
  border: 1px solid var(--paper-3);
  border-radius: var(--radius-lg);
  padding: 14px 18px;
  margin: 20px 0 6px;
}
.q-label {
  font-size: 9.5px; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-3); margin-bottom: 6px;
}
.q-text { font-size: 15px; line-height: 1.65; color: var(--ink); }

/* ── A section ── */
.a-section { margin: 6px 0 4px; }
.a-badge {
  display: inline-flex; align-items: center;
  font-size: 9.5px; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent); border: 1px solid var(--accent);
  border-radius: 20px; padding: 3px 10px; margin-bottom: 10px;
}
.a-body {
  font-size: 15px; line-height: 1.8; color: var(--ink);
}
.a-body p  { margin: 0 0 0.7em; }
.a-body ul, .a-body ol { margin: 0 0 0.7em 1.2em; }
.a-body li { margin-bottom: 0.3em; }
.a-body h1, .a-body h2, .a-body h3, .a-body h4 {
  font-family: var(--font-serif); color: var(--ink);
  margin: 0.8em 0 0.3em;
}
.a-body strong { font-weight: 600; }
.a-body code { font-family: var(--font-mono); font-size: 13px; background: var(--paper-3); border-radius: 3px; padding: 1px 4px; }

/* ── Inline cite badge ── */
.cite-badge {
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--seal-bg); color: var(--seal);
  border-radius: 4px; font-size: 11px; font-weight: 600;
  padding: 1px 5px; margin: 0 1px;
  font-family: var(--font-mono); vertical-align: baseline;
  cursor: default;
}

/* ── Citations details block ── */
details.citations {
  margin-top: 14px;
  border: 1px solid var(--paper-3);
  border-radius: var(--radius-md);
  overflow: hidden;
}
details.citations summary {
  padding: 10px 14px; cursor: pointer;
  font-size: 12.5px; font-weight: 500; color: var(--ink-2);
  background: var(--paper-2);
  list-style: none;
  display: flex; align-items: center; gap: 8px;
  user-select: none;
}
details.citations summary::-webkit-details-marker { display: none; }
details.citations summary::before { content: '▸'; font-size: 11px; transition: transform 0.15s; color: var(--ink-3); }
details.citations[open] summary::before { transform: rotate(90deg); }
.cite-list { background: var(--paper); }
.cite-item {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 10px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--paper-2);
}
.cite-item:last-child { border-bottom: none; }
.cite-num {
  width: 28px; height: 28px;
  background: var(--seal-bg); color: var(--seal);
  border-radius: 5px;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  font-family: var(--font-mono); flex-shrink: 0; margin-top: 1px;
}
.cite-content { overflow: hidden; }
.cite-name {
  font-size: 13px; font-weight: 600; color: var(--ink);
  margin-bottom: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cite-excerpt {
  font-size: 11.5px; color: var(--ink-3); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.cite-link {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 500; color: var(--accent);
  text-decoration: none; margin-top: 5px;
  padding: 3px 7px; border-radius: var(--radius-sm);
  border: 1px solid var(--accent-lt);
  background: var(--accent-lt);
}
.cite-link:hover { background: var(--accent); color: white; border-color: var(--accent); }

/* ── Meta / model info ── */
.meta-info {
  font-size: 10.5px; color: var(--ink-3); margin-top: 10px;
  font-family: var(--font-mono);
}

/* ── Welcome ── */
.welcome { text-align: center; padding: 80px 20px 40px; }
.welcome h2 { font-family: var(--font-serif); font-size: 26px; color: var(--ink); margin-bottom: 8px; }
.welcome p  { color: var(--ink-3); font-size: 14px; }

/* ── Chat input ── */
div[data-testid="stChatInput"] {
  border: 1px solid var(--paper-3) !important;
  border-radius: var(--radius-lg) !important;
  background: var(--paper-2) !important;
}
div[data-testid="stChatInput"] textarea {
  font-family: var(--font-thai) !important;
  font-size: 15px !important;
  color: var(--ink) !important;
  background: transparent !important;
}

/* ── Divider ── */
hr { border-color: var(--paper-3) !important; margin: 0.5rem 0 !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* ── Auth tabs ── */
.stTabs [data-baseweb="tab-list"] { background: var(--paper-2) !important; }
.stTabs [data-baseweb="tab"] { font-family: var(--font-thai) !important; }
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)


# ── Markdown → HTML ─────────────────────────────────────────────────────────

_MD_CONVERTER = _md_lib.Markdown(extensions=["nl2br", "tables"])


def _md_to_html(text: str) -> str:
    """Convert markdown answer text to HTML, replacing [N] with cite badges."""
    _MD_CONVERTER.reset()
    body = _MD_CONVERTER.convert(text)
    # Replace [N] and [N, M] references with cite badges
    def _badge(m: re.Match) -> str:
        nums = [n.strip() for n in m.group(1).split(",")]
        return "".join(f'<span class="cite-badge">[{n}]</span>' for n in nums)
    body = re.sub(r"\[([\d ,]+)\]", _badge, body)
    return body


# ── Render helpers ───────────────────────────────────────────────────────────

def _render_q(text: str) -> str:
    safe = _html.escape(text).replace("\n", "<br>")
    return (
        f'<div class="q-card">'
        f'  <div class="q-label">คำถาม &middot; Question</div>'
        f'  <div class="q-text">{safe}</div>'
        f'</div>'
    )


def _render_a(answer: str, sources: list[dict], model: str = "", chunks: int = 0) -> str:
    body_html = _md_to_html(answer)

    # Citations block
    cites_html = ""
    if sources:
        items_html = ""
        for s in sources:
            idx   = s["index"]
            name  = _html.escape(s.get("name", ""))
            url   = s.get("url", "")
            excerpt = _html.escape(s.get("excerpt", "")[:160])
            link = (
                f'<a class="cite-link" href="{url}" target="_blank" rel="noopener">เปิด PDF ↗</a>'
                if url else ""
            )
            items_html += (
                f'<div class="cite-item">'
                f'  <div class="cite-num">{idx}</div>'
                f'  <div class="cite-content">'
                f'    <div class="cite-name">{name}</div>'
                f'    <div class="cite-excerpt">{excerpt}</div>'
                f'    {link}'
                f'  </div>'
                f'</div>'
            )
        count = len(sources)
        label = f"เอกสารอ้างอิง ({count} {'รายการ' if count > 1 else 'รายการ'})"
        cites_html = (
            f'<details class="citations">'
            f'  <summary>📄 {label}</summary>'
            f'  <div class="cite-list">{items_html}</div>'
            f'</details>'
        )

    meta_html = ""
    if model:
        meta_html = f'<div class="meta-info">{_html.escape(model)} · {chunks} chunks</div>'

    return (
        f'<div class="a-section">'
        f'  <div class="a-badge">คำตอบ</div>'
        f'  <div class="a-body">{body_html}</div>'
        f'  {cites_html}'
        f'  {meta_html}'
        f'</div>'
    )


# ── Auth ─────────────────────────────────────────────────────────────────────

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
        try:
            authenticator.login()
        except Exception:
            for key in ["authentication_status", "username", "name", "logout"]:
                st.session_state.pop(key, None)
            try:
                authenticator.cookie_controller.delete_cookie()
            except Exception:
                pass
            st.components.v1.html(
                "<script>setTimeout(function(){parent.location.reload()},1500)</script>",
                height=0,
            )
            st.stop()
        if st.session_state.get("authentication_status") is False:
            st.error("Username หรือ Password ไม่ถูกต้อง")
            col_forgot, col_reg = st.columns(2)
            with col_forgot:
                st.markdown("ลืมรหัสผ่าน?")
                if st.button("🔑 ลืมรหัสผ่าน", key="goto_forgot"):
                    st.session_state["show_inline_forgot"] = True
                    st.session_state["show_inline_register"] = False
                    st.rerun()
            with col_reg:
                st.markdown("ยังไม่ได้สมัครสมาชิก ใช่ไหม?")
                if st.button("➡️ สมัครสมาชิกเลย", type="primary", key="goto_register"):
                    st.session_state["show_inline_register"] = True
                    st.session_state["show_inline_forgot"] = False
                    st.rerun()
            if st.session_state.get("show_inline_forgot"):
                st.divider()
                st.markdown("#### ลืมรหัสผ่าน")
                try:
                    username_forgot, email_forgot, new_password = authenticator.forgot_password(
                        captcha=False, key="inline_forgot"
                    )
                    if username_forgot:
                        with open(_AUTH_CONFIG_PATH, "w") as f:
                            yaml.dump(_auth_config, f, allow_unicode=True, default_flow_style=False)
                        st.success(f"รหัสผ่านใหม่ของ **{username_forgot}**:")
                        st.code(new_password)
                        st.caption("กรุณาจดรหัสผ่านนี้ไว้ แล้วไปเปลี่ยนหลัง login")
                    elif username_forgot is False:
                        st.error("ไม่พบ username นี้ในระบบ")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            if st.session_state.get("show_inline_register"):
                st.divider()
                st.markdown("#### สมัครสมาชิก")
                try:
                    email, username, name = authenticator.register_user(
                        pre_authorized=None, captcha=False, key="inline_register",
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
            email, username, name = authenticator.register_user(pre_authorized=None, captcha=False)
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

# ── Chat persistence ──────────────────────────────────────────────────────────

_DATA_DIR   = Path(os.getenv("THAI_RAG_DATA_DIR", "data"))
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


def _chat_age_group(updated_at: float) -> str:
    """Return grouping label for sidebar history."""
    now = datetime.datetime.now()
    dt  = datetime.datetime.fromtimestamp(updated_at)
    delta = now - dt
    if delta.days == 0:
        return "วันนี้"
    elif delta.days <= 7:
        return "สัปดาห์นี้"
    elif delta.days <= 30:
        return "เดือนนี้"
    else:
        return "ก่อนหน้า"


# ── Session init ──────────────────────────────────────────────────────────────

if "chats" not in st.session_state:
    st.session_state.chats = _load_chats()

if "current_chat_id" not in st.session_state:
    if st.session_state.chats:
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


# ── Citation helpers ──────────────────────────────────────────────────────────

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
            # Use first chunk's text as excerpt
            excerpt = chunk.get("text", "")
            if len(excerpt) > 160:
                excerpt = excerpt[:157] + "…"
            source_list.append({
                "index": idx,
                "name": name,
                "url": chunk.get("file_url", ""),
                "excerpt": excerpt,
            })

    chunk_to_src: dict[int, int] = {}
    for i, chunk in enumerate(ordered_chunks, 1):
        name = chunk.get("source_name", chunk.get("source", "unknown"))
        chunk_to_src[i] = source_index[name]

    return chunk_to_src, source_list


def _replace_refs(answer: str) -> str:
    def replace(m: re.Match) -> str:
        nums = list(dict.fromkeys(int(x.strip()) for x in m.group(1).split(",")))
        return "[" + ", ".join(str(i) for i in nums) + "]"
    return re.sub(r"\[([\d ,]+)\]", replace, answer)


# ── Index (cached across reruns) ──────────────────────────────────────────────

@st.cache_resource(show_spinner="กำลังโหลด index...")
def get_retriever():
    index = IndexManager()
    return Retriever(index)


if not GEMINI_API_KEYS:
    st.error("GEMINI_API_KEY not set in environment.")
    st.stop()

retriever = get_retriever()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    # Brand mark
    st.markdown(
        '<div class="brand-row">'
        '  <div class="brand-glyph">ก</div>'
        '  <div class="brand-text">'
        '    <div class="brand-name">Thai Legal RAG</div>'
        '    <div class="brand-sub">กฎหมายจัดซื้อจัดจ้าง</div>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button("＋  บทสนทนาใหม่", use_container_width=True, type="primary"):
        cid = _new_chat_id()
        st.session_state.chats[cid] = {"messages": [], "updated_at": time.time()}
        st.session_state.current_chat_id = cid
        _save_chats(st.session_state.chats)
        st.rerun()

    st.divider()

    # History grouped by age
    sorted_chats = sorted(
        st.session_state.chats.items(),
        key=lambda x: x[1].get("updated_at", 0),
        reverse=True,
    )

    current_group: str | None = None
    for cid, chat in sorted_chats:
        group = _chat_age_group(chat.get("updated_at", 0))
        if group != current_group:
            current_group = group
            st.markdown(f'<p class="hist-group">{group}</p>', unsafe_allow_html=True)

        title    = _chat_title(chat["messages"])
        is_active = cid == st.session_state.current_chat_id
        label    = f"**{title}**" if is_active else title

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
                        st.session_state.current_chat_id = next(iter(st.session_state.chats))
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

# ── Main chat area ────────────────────────────────────────────────────────────

msgs = current_messages()

if not msgs:
    st.markdown(
        '<div class="welcome">'
        '<h2>ถามคำถามกฎหมายจัดซื้อจัดจ้าง</h2>'
        '<p>เริ่มต้นด้วยการพิมพ์คำถาม เช่น "ค่าปรับผิดสัญญามีขั้นตอนยังไง"</p>'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    for msg in msgs:
        if msg["role"] == "user":
            st.markdown(_render_q(msg["content"]), unsafe_allow_html=True)
        else:
            sources = msg.get("sources", [])
            model   = msg.get("model", "")
            chunks  = msg.get("chunks_used", 0)
            st.markdown(_render_a(msg["content"], sources, model, chunks), unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────

question = st.chat_input("พิมพ์คำถาม เช่น 'ค่าปรับผิดสัญญามีขั้นตอนยังไง'")

if question:
    msgs.append({"role": "user", "content": question})
    st.markdown(_render_q(question), unsafe_allow_html=True)

    with st.spinner("กำลังค้นหาและประมวลผล..."):
        try:
            chat_history = [
                {"role": m["role"], "content": m["content"]}
                for m in msgs[:-1]
            ]
            raw_results  = retriever.retrieve(question, expand=True, history=chat_history)
            ranked_chunks = rerank(raw_results, query=question)
            result       = generate_answer(question, ranked_chunks, history=chat_history)

            _, source_list = _build_source_map(ranked_chunks)
            answer = _replace_refs(result["answer"])

            model_label = result.get("model", "")
            chunks_used = result.get("chunks_used", 0)

            st.markdown(
                _render_a(answer, source_list, model_label, chunks_used),
                unsafe_allow_html=True,
            )

            msgs.append({
                "role": "assistant",
                "content": answer,
                "sources": source_list,
                "model": model_label,
                "chunks_used": chunks_used,
            })

            st.session_state.chats[st.session_state.current_chat_id]["messages"] = msgs
            st.session_state.chats[st.session_state.current_chat_id]["updated_at"] = time.time()
            _save_chats(st.session_state.chats)

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
            raise
