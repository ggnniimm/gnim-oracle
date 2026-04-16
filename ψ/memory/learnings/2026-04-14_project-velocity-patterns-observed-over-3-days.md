---
title: ## Project Velocity Patterns (observed over 3 days)
tags: [project-velocity, session-planning, lightrag, architecture]
created: 2026-04-14
source: rrr: all-sessions-dig — gnim-oracle 3-day review 2026-02-13
---

# ## Project Velocity Patterns (observed over 3 days)

## Project Velocity Patterns (observed over 3 days)

1. **Long sessions → short cleanup sessions**: Ming consistently does a large build session (400-800 min) followed immediately by a short focused session (7-20 min) to clean up. After a big session, save a cleanup slot — don't end on the rough code.

2. **Plans at session start = higher quality output**: Sessions beginning with a plan document (handoff or `/standup`) produce cleaner commits and less rework than sessions that begin cold.

3. **Rebuild cost for premature architecture**: Don't treat exploration-masquerading-as-production-code as final architecture. Budget one rebuild session.

4. **LightRAG is consistently the complexity spike**: Every session touching LightRAG had a significant issue. Pin the version and test in isolation before integrating.

5. **Data gaps block validation**: Track data readiness as a blocker, not an afterthought — pipeline work can outpace data availability.

---
*Added via Oracle Learn*
