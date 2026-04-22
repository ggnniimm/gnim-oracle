---
title: Streamlit custom dark sidebar requires config.toml base=light first. Without it,
tags: [streamlit, css, ui, thai-legal-rag]
created: 2026-04-18
source: rrr: gnim-oracle-qdrant
---

# Streamlit custom dark sidebar requires config.toml base=light first. Without it,

Streamlit custom dark sidebar requires config.toml base=light first. Without it, Streamlit's dark theme overrides sidebar CSS even with !important. Create .streamlit/config.toml with base="light" before injecting any design system CSS.

---
*Added via Oracle Learn*
