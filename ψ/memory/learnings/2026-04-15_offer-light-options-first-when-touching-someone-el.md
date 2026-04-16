---
title: Offer light options first when touching someone else's infrastructure.
tags: [options-ordering, external-contribution, conservative-defaults, principle-3, reversibility, git, fork-pr]
created: 2026-04-15
source: rrr: gnim-oracle-qdrant
project: github.com/soul-brews-studio/gnim-oracle
---

# Offer light options first when touching someone else's infrastructure.

Offer light options first when touching someone else's infrastructure.

When a fix lives in a repo owned by someone else (shared infra, upstream lib, another team's project), option ordering has a social-capital asymmetry:

- Heavy-first (fork→PR→...): user feels pressure to step DOWN. Each step feels like sunk cost if they back out.
- Light-first (local-only → optional fork → optional PR): user feels invited to step UP. Every earlier step is reversible by doing nothing.

Default to light-first for external infrastructure. The conservative anchor for external contribution is "don't contribute yet, just use it."

Applied ordering:
1. Keep fix local only (running clone gets it at runtime, zero external footprint)
2. Fork + PR (only if user asks for more)
3. File issue first, let maintainer drive (only if user wants to ship broadly)

Companion: pushing to a fork is reversible (`git push fork --delete`). Don't treat pushed work as a one-way door.

Related to Gnim Principle 3 "External Brain, Not Command" — presenting heavy options first subtly nudges the decision; light-first respects user autonomy.

Real trigger: 2026-04-15 MCP stdio fix in arra-oracle-v3. I proposed fork+PR first; Ming pushed back twice before we retreated to local-only. Better ordering would have avoided the churn.

---
*Added via Oracle Learn*
