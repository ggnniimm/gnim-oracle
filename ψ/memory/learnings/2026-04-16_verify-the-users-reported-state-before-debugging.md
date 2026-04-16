---
title: Verify the user's reported state before debugging.
tags: [debugging, verification, ux, user-reports, process]
created: 2026-04-16
source: rrr: gnim-oracle-qdrant
---

# Verify the user's reported state before debugging.

Verify the user's reported state before debugging.

When a user reports "X is broken / missing / not working," resist the instinct to start debugging X. User bug reports describe symptoms, not causes. Often the user is in a different state than they think (logged out, wrong tab, wrong password, stale cache) and the thing they say is "broken" is actually fine.

Process:
1. Reproduce the user's view end-to-end — open the UI in a browser (or Playwright), log in as the user, observe what they observe.
2. If the UI shows the data, the bug isn't "data missing" — it's "user's session/state was different." Explain that to the user.
3. Only after verification fails should you form hypotheses about internal causes.

Verification cost: ~5 min. Speculation cost: can spiral into hours of bad fixes.

Corollary: ask for credentials upfront when UI verification is needed. Guessing wastes timeout cycles.

Case (2026-04-16): Ming reported "chat history หาย." Server check showed file intact (70 KB, 8 chats). Rather than hypothesize about hash changes or save failures, I ran Playwright with the correct password — sidebar rendered all 8 chats. Ming had simply failed to log in earlier and interpreted "login screen" as "history gone." Zero code changes needed.

---
*Added via Oracle Learn*
