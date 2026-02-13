# Lesson: Project Velocity Patterns (3-day observation)

**Date**: 2026-02-13
**Source**: rrr: all-sessions-dig — gnim-oracle 3-day review

---

## Pattern: Long sessions → short cleanup sessions

Ming consistently does a large build session (400-800 min) followed immediately by a short focused session (7-20 min) to clean up or add the tooling layer.

Implication: after a big session, save a cleanup slot. Don't end on the big session — the code will be rough.

---

## Pattern: Plans at session start = higher quality output

Sessions that begin with a plan document (handoff or `/standup`) produce cleaner commits than sessions that begin cold (`claude --continue`). Plan-first sessions show less rework and smaller diffs per feature.

---

## Pattern: Rebuild cost for premature architecture

Session 4 (438 min) built Thai Legal RAG v1. Session 7 rebuilt it as v2 clean architecture. Total rebuild cost ≈ 350 extra minutes. Root cause: Session 4 was exploration masquerading as production code.

**Rule of thumb**: if a session is mostly research + first-attempt code, don't treat its architecture as final. Budget one rebuild session.

---

## Pattern: LightRAG is consistently the complexity spike

Every session touching LightRAG had a significant issue:
- Session 6: Python 3.12 asyncio.coroutine removed
- Session 7: LightRAG v1.3.1 API changes + async loop issues
- Session 8 (pending): law data gap prevents validation

LightRAG is powerful but fragile. Always pin the version and test in isolation before integrating.

---

## Pattern: Data gaps block validation

Pipeline was complete but untestable without the data (กฎกระทรวง upload). Architecture work outpaced data availability. Track data readiness as a blocker, not an afterthought.
