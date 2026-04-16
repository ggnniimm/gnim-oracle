# Stale Cookie + st.rerun() = Infinite Loop

**Date**: 2026-04-16
**Context**: Tried replacing st.stop() with st.rerun() for auto-recovery from stale auth cookies
**Tags**: #streamlit #cookie #authenticator #deploy

## Problem

After deploy, stale browser cookie → `authenticator.login()` throws exception. First fix attempt:
```python
except Exception:
    session_state.pop(keys)
    st.rerun()  # ← INFINITE LOOP
```

`pop()` clears Python session state but NOT the browser cookie. On rerun, authenticator reads the cookie again → same exception → rerun → forever. Site went down.

## Solution

Delete cookie at browser level via JS, then meta-refresh:
```python
except Exception:
    session_state.pop(keys)
    st.markdown(
        f'<meta http-equiv="refresh" content="1">'
        f'<script>document.cookie="{cookie_name}=; Max-Age=0; path=/";</script>',
        unsafe_allow_html=True,
    )
```

## Key Insight

Streamlit session state ≠ browser cookie. They're two separate layers. The authenticator reads the cookie BEFORE session state matters. When the bug originates in the browser (cookie), the fix must reach the browser (JS).

## Files

- `app/streamlit_app.py`: stale cookie exception handler
