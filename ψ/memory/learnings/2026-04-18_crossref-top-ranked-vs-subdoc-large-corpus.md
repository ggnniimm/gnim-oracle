---
name: Cross-ref in top-ranked doc beats sub-doc in large corpus
description: When MMR diversity blocks sub-doc from top 15, cross-ref content into the consistently top-ranked doc instead
type: project
---

When RAG corpus is large (28K+ chunks) and many docs share the same topic (e.g. แก้ไขสัญญา), MMR diversity penalty will block sub-docs even with good vector scores (e.g. rank [24] on server vs rank [5] locally).

**Pattern**: Find the doc that consistently ranks [1] for the target query (e.g. กวจ_51385 ranks [1] for แก้ไขสัญญา+งวดสุดท้าย due to recency boost 2568 + heavy keyword overlap). Add a cross-ref bullet summarizing the missing doc's key content into that top-ranked doc's สรุปข้อวินิจฉัย. LLM will cite the content even though the source shown is the carrier doc, not the original.

**Why:** Sub-doc approach improves vector score but can't overcome MMR diversity in large corpus. Cross-ref in top-ranked doc is guaranteed to be in retrieved set.

**How to apply:** Before building a sub-doc, check if the target is blocked by MMR: run verbose retrieval and see if similar topic docs fill the top 15 first. If yes → skip sub-doc, go straight to cross-ref in rank [1] doc.

**Also:** Bullet insertion at TOP of สรุปข้อวินิจฉัย pushes existing content to different chunks → can cause regression. Insert cross-ref bullets at BOTTOM of section to avoid shifting chunk boundaries.
