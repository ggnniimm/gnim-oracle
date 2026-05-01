# Trust break = diagnostic signal, not interpersonal problem (2026-05-01)

## Pattern

When the user gets sharp ("มั่วมาก", "ไม่มีความเชื่อใจแล้ว", "ทำไมไม่ใช้อันล่าสุด"), the first instinct is to defend or hedge. The right move: **stop, probe widely, accept that they're seeing something I'm missing**.

## Source case (2026-04-30 → 05-01)

I spent 6 hours making "fixes" on a thai-legal-rag corpus that was the wrong source-of-truth. /recap put me in `gnim-oracle/` and I assumed that was canonical. Each fix verified 3/3 PASS, MEMORY.md updates landed, learnings got written — all in the wrong repo. The system gave me no signal.

When Ming opened mwaprocure and saw doc links 404'ing, his sharpness ("ไม่มีความเชื่อใจแล้ว") was the **only available diagnostic signal**. I almost wrote a "let me explain why this is fine" reply. Instead, I went to: stop edits, probe wider (sibling repos, drive_mapping, Qdrant payloads, BM25 backups), surface the actual fork (gnim-oracle vs gnim-oracle-qdrant).

That sharpness was correct AND it was load-bearing. Without it the session would have committed to MORE wrong-repo work.

## How to apply

When the user shows frustration mid-session:
1. **Default to "they see something I don't"** — not "they're stressed, manage tone"
2. **Stop substantive work** — do NOT propose more fixes until you understand what they're noticing
3. **Probe wider than the current scope** — sibling repos, environment variables, alternative paths, recent backups — anything you took as a default assumption
4. **Surface findings honestly** — including the part where I was wrong

## Anti-pattern to avoid

- "Sorry for the confusion, here's what's going on..." then more fixes in the same wrong direction
- Defensive explanation ("technically the file_ids did update — at least in Qdrant payload...")
- Reassuring the user that things are fine before verifying

## Why this matters

The ML/dev assistant default is to keep moving forward — mistakes feel expensive to acknowledge. But a wrong-direction session compounds. The user's frustration is often their compressed intuition that the model has lost the plot. Treating that signal as *information* not *interpersonal noise* is what lets the recovery be fast.

Pair with:
- `2026-04-30_wrong-repo-source-of-truth.md` — the specific instance
- `feedback_verify-before-act.md` — verify-before-fix general pattern
