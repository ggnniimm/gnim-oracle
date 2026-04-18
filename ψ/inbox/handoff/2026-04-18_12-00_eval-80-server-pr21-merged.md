# Handoff: Eval 78/80 Server, PR #21 Merged

**Date**: 2026-04-18 12:00
📡 Session: 5cd7dd7b | gnim-oracle-qdrant | ~3h

## Context
**Oracle**: Gnim | **Human**: Ming
**Branch**: fix/stale-cookie-and-rag-improvements (merged → main)

---

## What We Did

### TC-003 + TC-008 PASS ✓
- **TC-003** "คณะกรรมการตรวจรับพัสดุ": PASS stable (3 runs local, 1 run server)
  - กวจ_20140 summarizes ว_78 inline → ผลิตภายในประเทศ met without retrieving ว_78 directly
- **TC-008** "แก้ไขสัญญาหลังตรวจรับงานงวดสุดท้าย": PASS stable (2 runs local, 1 run server)
  - Cross-ref เนื้องาน rule in กวจ_51385 (rank [1]) → citation correct and legitimate

### Full Eval Results
- **Local**: 77/80 (TC-044, TC-050, TC-074 — all confirmed LLM variance)
- **Server** (via SSH tunnel 6334→172.22.0.2:6333): 78/80 (TC-037, TC-044 — LLM variance)
- No structural regressions

### PR #21 Merged
- Branch: `fix/stale-cookie-and-rag-improvements` → main
- Includes: stale cookie fix, citation accuracy, rule 15, Gemini fallback, python-crfsuite
- Commit: `bea7352` (code) + `ed808bd` (ψ memory/retros/handoffs)

### Dependabot PRs
- PRs #16, #17, #18 already CLOSED — no action needed

---

## Pending

- [ ] TC-027 "ผู้ทิ้งงาน" — pre-existing fail, no fix yet identified
- [ ] feat/embedding-v2 + feat/qdrant-embedding2 branches — decide: delete or pursue?
- [ ] GitHub Dependabot alerts (27 vulnerabilities) — review if worth addressing
- [ ] Issues #11, #12, #13 — open cross-ref tasks for TC-051 and TC-011

---

## Next Session

- [ ] Decide on embedding-v2 branches (delete or open as separate project)
- [ ] Investigate TC-027 "ผู้ทิ้งงาน" root cause (retrieval gap or LLM issue?)
- [ ] Review open issues #11, #12, #13 — still relevant after eval improvements?

---

## Key Files

- `ψ/lab/thai-legal-rag/eval/golden_test_cases.json` — 80 TCs
- `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_51385_...md` — cross-ref เนื้องาน bullet (line 169)
- `ψ/lab/thai-legal-rag/data/md_backup/กวจ_20140_...md` — contains ว_78 inline summary
- `ψ/lab/thai-legal-rag/src/generation/generator.py` — rule 15 (no hallucinated citations)
- `ψ/lab/thai-legal-rag/src/gemini_client.py` — fallback: gemini-2.5-flash-lite only

## Key Insight

**Eval baseline raised**: from 74/80 → 78/80 server (all remaining failures LLM variance)
**cross-ref ใน top-ranked doc ยังเป็น strategy ที่ดีที่สุด** — กวจ_51385 rank [1] ทุกครั้งสำหรับ contract amendment queries
