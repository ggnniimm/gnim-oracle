---
title: Streamlit toolbar CSS injection — interactive elements เป็นไปไม่ได้
tags: [streamlit, css, ui, limitation, positioning]
created: 2026-04-14
source: rrr: gnim-oracle-qdrant
project: github.com/ggnniimm/gnim-oracle-qdrant
---

# Streamlit toolbar CSS injection — interactive elements เป็นไปไม่ได้

Streamlit toolbar CSS injection — interactive elements เป็นไปไม่ได้

การ inject CSS เพื่อ position interactive elements (buttons, popovers) ให้ไปอยู่ใน Streamlit toolbar area (top-right ข้างๆ ⋮) ไม่ได้ผล ไม่ว่าจะใช้ :has() selector, .stMainBlockContainer, .main .block-container > div > div:first-child, หรือ position: fixed + z-index: 99999

Root cause: Streamlit renders React components ใน structure ที่ CSS จาก st.markdown(unsafe_allow_html=True) ไม่สามารถ target toolbar area ได้

Solution จริง: วาง element ใน sidebar ด้านล่างแทน ถ้าต้องการ true custom positioning → เปลี่ยน framework (Next.js / Gradio)

When to apply: เมื่อ user ขอวาง UI element ออกนอก Streamlit standard layout → บอกตรงๆ ว่าทำไม่ได้ เสนอ sidebar placement แทน อย่าพยายาม CSS hack หลายรอบ

---
*Added via Oracle Learn*
