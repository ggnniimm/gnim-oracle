# Verify User State Before Debugging a Reported Bug

**Date**: 2026-04-16
**Context**: Ming reported "chat history หาย ของ ming" — turned out the data was fine, user just couldn't log in
**Tags**: #debugging #verification #ux #authentication

## Problem

User says "X is broken / missing / not working." Natural instinct: start debugging X. Add logs, check code paths, form hypotheses about what might have corrupted X.

This wastes time when the actual issue is the user is in a different state than they think — e.g., logged out, wrong tab, wrong env, cache. The "broken" thing is often fine.

## Specific Case

Ming reported Ming's chat history was gone. Server check showed:
- File `chat_sessions_ming.json` existed (70 KB, 8 chats)
- Docker container could read it
- `_load_chats()` code path was correct

I was about to write a speculative hypothesis list (hash change? save failure? volume mount bug?). Instead I ran Playwright with the correct password → sidebar rendered all 8 chats. **Data was never lost.** Ming had likely tried logging in with the wrong password, seen only the login screen, and concluded "history is gone."

## Solution

Always verify the reported failure end-to-end before debugging:

1. **Reproduce the user's view** — open the UI in a browser (or Playwright), log in as the user, observe what they observe.
2. **If the UI shows the data**, the bug isn't "data missing" — it's "user's session/state was different."
3. **Only after verification fails** should you form hypotheses about internal causes.

Verification cost: ~5 min (Playwright login + screenshot).
Speculation cost: can spiral into hours of bad fixes.

## Key Insight

User bug reports describe symptoms, not causes. Treat "X is broken" as a hypothesis, not a fact — and the cheapest way to test the hypothesis is to reproduce the user's view. If you can see the data from the same entry point the user sees, the data isn't missing; the user's path to it is.

Related: always ask for credentials upfront when UI verification is needed. Guessing passwords wastes timeout cycles.

## Files

- No code files — this is a process learning
