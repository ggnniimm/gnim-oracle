---
title: Streamlit toolbar CSS injection — interactive elements impossible
tags: [streamlit, css, ui, limitation]
created: 2026-04-14
source: rrr: gnim-oracle-qdrant
---

# Streamlit: Interactive Elements ใน Toolbar Area เป็นไปไม่ได้

การ inject CSS เพื่อ position interactive elements (buttons, popovers) ให้ไปอยู่ใน Streamlit toolbar area (top-right ข้างๆ ⋮) ไม่ได้ผล

## ที่ลองแล้วไม่ work

- `:has()` CSS selector
- `.stMainBlockContainer` selector  
- `.main .block-container > div > div:first-child` selector
- `position: fixed` + `z-index: 99999`

ทุกวิธีให้ element render ใน main content area อยู่ดี ไม่ขึ้น toolbar

## Root Cause

Streamlit renders React components ใน shadow-DOM-like structure ที่ CSS inject จาก `st.markdown(unsafe_allow_html=True)` ไม่สามารถ target ได้อย่างแม่นยำ toolbar area ถูก Streamlit จัดการ internally

## Solution ที่ใช้ได้จริง

- วาง popover ไว้ใน **sidebar ด้านล่าง** (bottom-left) แทน
- ถ้าต้องการ true top-right custom element → เปลี่ยน framework (Next.js / Gradio)

## When to apply

เมื่อต้องการ place UI element ออกนอก Streamlit's standard layout grid → อย่าพยายาม CSS hack บอก user ตรงๆ ว่าทำไม่ได้แล้วเสนอ sidebar placement แทน
