---
name: Streamlit config.toml base=light required before custom dark-sidebar CSS
description: Without base=light in config.toml, Streamlit dark theme overrides sidebar CSS even with !important
type: feedback
date: 2026-04-18
---

When applying a custom dark sidebar + light main area to a Streamlit app, `.streamlit/config.toml` must declare `base = "light"` first.

**Why:** Streamlit's dark theme applies `background-color` to `section[data-testid="stSidebar"]` via its own stylesheet with high specificity. Even `background: var(--sidebar-bg) !important` in injected CSS lost the fight. Setting `base = "light"` in config.toml turns off Streamlit's dark-theme overrides, leaving our CSS in control.

**How to apply:** Always create `.streamlit/config.toml` before injecting design system CSS:
```toml
[theme]
base = "light"
backgroundColor = "#faf9f6"
secondaryBackgroundColor = "#f3f1eb"
textColor = "#1c1917"
```
Then the sidebar CSS (`background: #1e1b2e !important`) takes effect as intended.
