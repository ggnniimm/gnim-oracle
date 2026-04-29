# Handoff: CookieManager Production Error Diagnosis

**Date**: 2026-04-24 20:00
**Session**: b89520ec | gnim-oracle
📡 Session: b89520ec | gnim-oracle

> **STATUS (2026-04-29)**: ✅ RESOLVED — verified on production
> - `streamlit-authenticator` = 0.4.2 ✓ (matches requirements.txt)
> - Container uptime: 4 days (rebuild was applied ~25 เม.ย.)
> - https://mwaprocure.gnim.cloud/ → HTTP 200, no CookieManager error in logs
> - Note: `streamlit-cookies-controller` NOT installed but `extra-streamlit-components` 0.1.81 is — auth works via the latter, original diagnosis about backend switch was partially incorrect
> - See: `ψ/memory/learnings/2026-04-29_cookiemanager-fix-already-applied.md`

## What We Did

- Diagnosed production error on mwaprocure.gnim.cloud: `extra_streamlit_components.CookieManager.cookie_manager` failing to load
- Root cause: Docker image on production was built from old requirements — `streamlit-authenticator` installed is likely 0.3.x (uses `extra_streamlit_components`) but `requirements.txt` now says `==0.4.2` (uses `streamlit-cookies-controller`, no frontend component)
- Confirmed nginx IS in use on production as reverse proxy (from deploy gotchas memory)
- Fix identified but NOT yet applied: rebuild Docker image on server

## Pending

- [ ] SSH to server (31.97.188.155) and check installed version: `docker exec thai-legal-rag-app-1 pip show streamlit-authenticator`
- [ ] If not 0.4.2 → rebuild: `docker compose build app && docker compose up -d app`
- [ ] Verify login works after rebuild at mwaprocure.gnim.cloud
- [ ] Close stale PRs: #13 TC-051, #12 TC-011, #11 eval regression (all old branches)
- [ ] Stale branches: `feat/claude-design-ui`, `fix/stale-cookie-and-rag-improvements`

## Next Session

- [ ] Apply the Docker rebuild fix on production server
- [ ] Test login flow end-to-end after fix
- [ ] Clean up stale PRs (#11, #12, #13) and branches

## Key Files

- `ψ/lab/thai-legal-rag/requirements.txt` — `streamlit-authenticator==0.4.2`
- `ψ/lab/thai-legal-rag/app/streamlit_app.py` — uses `stauth.Authenticate` + `cookie_controller`
- `ψ/lab/thai-legal-rag/docker-compose.yml` — production deployment config
- `ψ/memory/learnings_hostinger_vps_deploy.md` — nginx websocket headers, server quirks
