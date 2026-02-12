# Lesson: Session Hygiene for Long Research Sessions

**Date**: 2026-02-12
**Source**: Full-day dig retrospective

## Core Lessons

### 1. Experiment files need context notes
Any file committed to `ψ/lab/` should have accompanying context. Options:
- Commit message with "what we tested / what we found"
- `ψ/lab/README.md` or per-experiment `notes.md`
- At minimum: first comment in the file explaining the experiment

Without this, lab artifacts are archaeologically opaque 3 months later.

### 2. Long sessions need checkpoints
Sessions >2 hours covering multiple topics risk context drift and silent omissions.
Rule of thumb: `/forward` at every major topic transition, not just at end of day.

Good transitions to checkpoint at:
- End of "research" before starting "implementation"
- After deep-diving one codebase before moving to another
- After completing a deliverable (learning doc, design doc)

### 3. Every session deserves a retrospective — even infrastructure ones
Morning sessions with "just permissions and schedule" still contain:
- Decisions about tool design
- Patterns about what tools Ming actually uses
- Friction points in the workflow

These are worth capturing in /rrr even if brief (10-minute retro).

### 4. /dig as reconstruction tool
`/rrr --dig` can reconstruct day's work from .jsonl session files even without real-time /rrr.
Use when: end of day, missed checkpoint, want day summary across multiple sessions.
Limitation: can't recover the "why" of decisions — only the "what" (commits + timestamps).

## Tags
`session-hygiene`, `checkpointing`, `experiment-logging`, `retrospective`
