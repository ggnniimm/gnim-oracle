# MMR See-Saw: Counterpoint Docs Hit a Retrieval Ceiling

**Date**: 2026-05-09
**Context**: thai-legal-rag, TC-066 (ref_sac_o_72_2564 vs ref_sac_o_233_2553)

## The Pattern

Two court cases describe the SAME factual scenario (ส่งงานไม่ครบถ้วน แต่ตรวจรับงานไปแล้ว) with OPPOSITE legal conclusions:
- อ.233/2553 → ผู้รับจ้างต้องรับผิดชดใช้
- อ.72/2564 → ผู้รับจ้างไม่ต้องรับผิด

A query that asks about this scenario ("ผลเป็นอย่างไร") has a semantic direction — the embedding space pulls toward one answer. Adding BM25 anchors to boost the counterpoint doc creates a see-saw: one doc in, the other out.

## The Diagnostic Signal

When you try to boost doc B and the ⚠ FLIPS (from "B not cited" to "A not cited"), you've confirmed the see-saw. This means:
- The retrieval pool has a fixed slot for this topic
- MMR is enforcing diversity between similar docs
- Adding more anchors to B just makes it win that slot at A's expense

**Stop at the first flip.** Further attempts waste time.

## Why Query Direction Matters

ref_sac_o_72_2564's content ("ไม่ต้องรับผิด") is semantically OPPOSITE to the query direction. Even with identical BM25 scores, vector retrieval ranks it lower. Making it win requires such a strong BM25 boost that it displaces the doc the query naturally retrieves.

## The Right Fixes

**Option 1: Accept ⚠** — If the TC passes and the counterpoint is just an expected_sources note, the ⚠ is acceptable. The answer is one-sided but correct.

**Option 2: Cross-ref inject** — Add the counterpoint content INTO the doc that wins retrieval (ref_sac_o_233_2553). LLM cites both through the winning doc. This is the correct tool for counterpoint cases.

**Option 3: Add a query-specific TC** — If the counterpoint matters enough, add a TC that queries specifically for it ("กรณีที่ผู้รับจ้างไม่ต้องรับผิด แม้ส่งงานไม่ครบถ้วน"). That query naturally attracts the counterpoint doc.

## What Does NOT Work

- Adding "ผลเป็นอย่างไร" to counterpoint doc lead bullet → causes see-saw
- Adding same phrase to both docs → they compete equally, MMR picks one
- Stripping overlap content from counterpoint doc → reduces its relevance, still loses
- Expanding counterpoint doc to more chunks → still loses on semantic direction

## Broader Principle

Cross-ref inject is not a hack. It's the correct architectural choice when:
1. Two docs describe the same scenario with opposite conclusions
2. The query has a natural semantic direction toward one conclusion
3. Both conclusions need to appear in a single answer

The injection ensures the complete legal picture appears regardless of retrieval dynamics.
