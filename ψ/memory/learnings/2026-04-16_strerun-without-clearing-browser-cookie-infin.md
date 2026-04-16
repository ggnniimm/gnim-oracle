---
title: st.rerun() without clearing browser cookie = infinite loop. Streamlit session st
tags: [streamlit, cookie, authenticator, infinite-loop, deploy]
created: 2026-04-16
source: rrr: gnim-oracle-qdrant
---

# st.rerun() without clearing browser cookie = infinite loop. Streamlit session st

st.rerun() without clearing browser cookie = infinite loop. Streamlit session state and browser cookies are separate layers. streamlit-authenticator reads the cookie BEFORE session state matters. pop() clears Python state but NOT the browser cookie → authenticator throws on every rerun. Fix: delete cookie via JS (document.cookie with Max-Age=0) + meta http-equiv refresh. When the bug is in the browser, the fix must reach the browser.

---
*Added via Oracle Learn*
