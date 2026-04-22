---
title: CSS :has() + margin-top:auto is the cleanest way to sticky-bottom a Streamlit si
tags: [streamlit, css, sidebar, ui, flex]
created: 2026-04-18
source: rrr: gnim-oracle-qdrant
---

# CSS :has() + margin-top:auto is the cleanest way to sticky-bottom a Streamlit si

CSS :has() + margin-top:auto is the cleanest way to sticky-bottom a Streamlit sidebar element. Make stVerticalBlock a flex column, then target the wrapper with :has(.profile-card) { margin-top: auto }. No need for position:fixed or hardcoded sidebar width.

---
*Added via Oracle Learn*
