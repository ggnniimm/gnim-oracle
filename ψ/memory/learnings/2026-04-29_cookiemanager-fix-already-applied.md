# Learning: Verify Production State Before Acting on Stale Handoff

**Date**: 2026-04-29
**Context**: Recap session opened with handoff from 24 เม.ย. saying "rebuild Docker image — fix not yet applied"

## What Happened

Started executing the documented fix (SSH + `docker compose build app && docker compose up -d app`) — but checked production state first. Found:

| Check | Expected (per handoff) | Actual on prod |
|---|---|---|
| `streamlit-authenticator` version | 0.3.x (broken) | **0.4.2** ✓ |
| Container uptime | needs rebuild | **4 days** (rebuilt ~25 เม.ย.) |
| https://mwaprocure.gnim.cloud/ | CookieManager error | **HTTP 200** ✓ |
| Recent docker logs | CookieManager errors | only Gemini retries (unrelated) |

Conclusion: someone (likely Ming) already applied the fix between 24 เม.ย. handoff and 29 เม.ย. recap.

## Diagnosis Detail Worth Noting

`streamlit-authenticator==0.4.2` works **without** `streamlit-cookies-controller` on prod — `extra-streamlit-components 0.1.81` is installed (transitive) and that's enough. Original handoff claim "0.4.2 uses streamlit-cookies-controller, no frontend component" was partially wrong — 0.4.2 still works with extra-streamlit-components for cookie storage.

## Lesson

**Stale handoffs lie. Always verify current production state before executing the documented action.** Especially:
- Container uptime (`docker ps`) — tells you if a rebuild has happened since
- Live HTTP status (`curl`) — tells you if the symptom is still there
- Installed package version (`pip show`) — tells you if the fix is already in

This is an instance of the existing `verify-before-act` and `verify-production-before-deploy` feedback patterns. Not new — but worth a fresh datapoint: **handoffs from a few days ago can already be obsolete**, especially when Ming worked on the issue between sessions without writing a closing note.

## Related

- Handoff: `ψ/inbox/handoff/2026-04-24_20-00_cookiemanager-production-fix.md` (now marked RESOLVED)
- Memory: `feedback_verify-production-before-deploy.md`
- Memory: `feedback_verify-before-act.md`
