---
name: Law-aware chunking changes retrieval landscape — run eval before deleting old data
description: Replacing generic 400-char chunks with section-aware chunks changes vector similarity scores, potentially regressing keyword-heavy queries
type: feedback
---

Switching from generic 400-char chunks to section-aware chunks (มาตรา/ข้อ level) for law files changes the embedding landscape. Bigger chunks dilute keyword density — a keyword that appeared prominently in a 400-char window gets buried in a 1500-char section chunk.

**Why:** TC-001 regressed because the old `ระเบียบ.pdf` generic chunks had "ความสัมพันธ์" in a focused 400-char window → high similarity score. After law-aware chunking, that keyword is embedded within a large section chunk → lower similarity → Qdrant retrieves a different document instead.

**How to apply:**
1. Always run eval BEFORE deleting old vector data — keep both versions temporarily for A/B comparison
2. When changing chunk strategy, expect retrieval shifts — budget time for per-TC regression analysis
3. The `--force-reindex --file` tool should search by file stem (not exact source_name) to clean up `.pdf` → `.md` transitions
4. Consider keeping small keyword-rich "anchor" chunks alongside section-aware chunks for better recall on keyword-heavy queries
