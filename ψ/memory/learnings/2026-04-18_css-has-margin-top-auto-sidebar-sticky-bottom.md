---
name: CSS :has() + margin-top auto for sticky-bottom Streamlit sidebar element
description: Make a sidebar element stick to the bottom without position:fixed — use flex column + :has() selector
type: feedback
date: 2026-04-18
---

To make a sidebar element (e.g. profile card) stay pinned at the bottom of the Streamlit sidebar:

**Why:** Streamlit wraps every `st.markdown` in its own `div > div > stMarkdownContainer` chain. You can't add `margin-top: auto` to the content div directly. But you CAN target the ancestor wrapper using the modern CSS `:has()` selector.

**How to apply:**
```css
/* Make stVerticalBlock a flex column */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
  height: 100% !important;
  display: flex !important;
  flex-direction: column !important;
  overflow-y: auto !important;
}

/* Push the wrapper that contains .profile-card to the bottom */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(.profile-card) {
  margin-top: auto !important;
  border-top: 1px solid var(--sidebar-3) !important;
}
```

Works in Chrome (production browser). Requires CSS `:has()` support (Chrome 105+). Cleaner than `position: fixed` which requires hardcoding sidebar width.
