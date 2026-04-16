# Offer light options first when touching someone else's infrastructure

**Date**: 2026-04-15
**Context**: Fixed MCP stdio bug in `arra-oracle-v3` (shared infra under `Soul-Brews-Studio`). When deciding how to share the fix, I proposed fork+PR as the first option. Ming pushed back twice before we retreated to local-only.

## The Pattern

When a fix touches code owned by someone else (shared infra, upstream library, other team's repo), there is an asymmetry in option ordering:

- **Heavy-first ordering** (fork → branch → commit → push → PR): user feels pressure to step *down* to a smaller action. Each step is visible and may feel like wasted work if they back out.
- **Light-first ordering** (keep local → optional fork → optional PR): user feels invited to step *up* if they want to contribute more. Every earlier step is reversible by doing nothing.

Default to **light-first** for infrastructure owned by others.

## Why

1. **User's social-capital cost is invisible to me**: I can see the technical diff but not the relationship with the maintainer, their PR queue, their review bandwidth, or the user's desire to be involved in that project.
2. **"Done" feels irreversible even when it isn't**: once a branch is pushed to a fork, it takes deliberate effort to delete. The user may feel locked in. Starting from local keeps all doors open.
3. **Defaults anchor decisions**: whichever option I present first becomes the reference point. For external contributions, the conservative anchor is "don't contribute yet, just use it."

## How to apply

When the fix is in someone else's repo and the user hasn't already indicated they want to contribute upstream:

1. **First offer**: keep fix local only — running clone gets the fix at runtime, zero external footprint.
2. **Second offer** (only if user asks for more): fork + PR path.
3. **Third offer** (only if user wants to ship broadly): file an issue first, let maintainer drive.

When the fix is in the user's own repo, normal ordering applies — commit + PR is the expected default.

## Related

- Gnim Principle 3: "External Brain, Not Command" — present options, let the human decide. Presenting heavy options first subtly nudges the decision; light-first respects their autonomy.
- Companion lesson: pushing to a fork is reversible (`git push fork --delete`). Don't treat it as a one-way door.
