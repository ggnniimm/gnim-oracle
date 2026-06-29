---
name: layered-debug-stop-checkpoints
description: Layered debug sessions need explicit "stop and re-orient" checkpoints — without them, the right move (workaround + learning) gets crowded out by tactical fixing
metadata:
  type: feedback
---

# Layered debug needs stop-checkpoints

**Rule**: When a debug session has peeled into 3+ layers (e.g. "is file indexed?" → OCR fix → retrieval design hole → infra workaround), pause explicitly and ask: *"what's the smallest thing that unblocks the user right now?"* Often the answer is a workaround + saved learning, not the perfect fix.

**Why**: Without this pause, the next tactical step crowds out the strategic choice. In the 2026-05-23 session I burned ~20 minutes trying SSH fingerprint format variants (ed25519, ecdsa, multi-line, prefix-on/off, action v1.0.3→v1.2.0, debug:true) when the right move — drop `fingerprint:`, accept threat-model trade-off, document — was available from minute 1. The 4th identical-shape variant is the signal: stop tweaking the format, route around or get deeper visibility.

**How to apply**:
1. **When you notice you're trying the 4th variant of the same shape** (4th regex, 4th secret format, 4th rerank weight) → stop. The pattern isn't yielding. Either go deeper (read the source code of the thing you're tweaking) or route around (workaround + save learning + move on).
2. **When a session has gone through 3+ "and then we found that..." layers** → before starting the 4th layer, pause for one user-facing sentence: "current state is X, the obvious-but-not-ideal unblock is Y, the perfect fix needs Z — which?" Let the user pick the depth.
3. **Pre-commit to workaround acceptability**. Before going deep, articulate what an acceptable workaround would look like. If you can name it, the deep dive is opt-in. If you can't, the deep dive isn't optional yet.

**Concrete examples from this session**:
- OCR fix peeled into "found 2nd file with same pattern" — paused, asked Ming B1 (verify Drive) vs B2 (trust filename) — clean checkpoint ✓
- Retrieval gap peeled into 3 fix candidates — listed all 3, asked which one, got "fix 1" — clean checkpoint ✓
- GHA fingerprint **didn't get a checkpoint** until format-tweaking attempt 5 — me deciding to "lui" with workaround came late, after the user lost patience. Should have offered the workaround at attempt 2 or 3, with the trade-off explicit.

Related: [[verify-before-act]], [[scope-stay-in-project]].
