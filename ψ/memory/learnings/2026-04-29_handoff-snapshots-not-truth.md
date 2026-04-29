---
name: Handoffs are snapshots, not ground truth
description: Handoffs from previous sessions can be obsolete — Ming may have acted between sessions without closing the loop. Always verify production/repo state before executing documented actions.
type: feedback
date: 2026-04-29
---

# Handoffs are snapshots, not ground truth

**Rule**: Handoffs describe state **at the moment of writing**. Between handoff and next session, Ming may have acted independently and not appended a closing note. Always verify current state before executing the handoff's "next action."

**Why**: Today's session almost rebuilt a Docker image that had already been rebuilt 4 days earlier (between handoff write at 24 เม.ย. 20:00 and recap at 29 เม.ย. 07:46). Ming worked on the issue solo, fixed it, but never circled back to mark the handoff resolved. The handoff still confidently said "fix not yet applied" — language that read like ground truth but was 5 days stale.

Same session almost deleted `feat/claude-design-ui` because the handoff called it a "stale branch." Reality: 3 unmerged commits of UI redesign work. The handoff's word "stale" was a generalization, not a description.

**How to apply**:
1. **Before SSH/deploy/rebuild** based on a handoff: verify with `pip show`, `docker ps` uptime, `curl` HTTP status. Stale handoff + production action = potential pointless or destructive operation.
2. **Before deleting a branch** the handoff calls "stale": run `git log main..<branch> --oneline` to see what's actually there. Combine with `git branch --merged main` to know if work would be lost.
3. **Before closing a PR** the handoff calls "stale": check `gh pr view N --json state` — it may already be closed, or may still have value.
4. **When the handoff is right but actions changed reality**: append a STATUS block to the handoff (Nothing is Deleted), don't overwrite. Future-you reading the handoff later sees both the original diagnosis and the actual outcome.

**Related memories**:
- `feedback_verify-production-before-deploy.md`
- `feedback_verify-before-act.md`

**Concrete pattern that emerged today**: tag-then-delete for unmerged branches that should be archived but not lost. `git tag archive/<name> <branch> -m "..."` + `git push origin archive/<name>` + `git branch -D <branch>`. Preserves commit hashes forever, removes branch list noise. Revive: `git checkout -b <branch> archive/<name>`.
