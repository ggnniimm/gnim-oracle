---
title: Eval with external LLM API needs 3 safety layers: (1) pre-flight ping before loa
tags: [eval, gemini, resilience, circuit-breaker, api]
created: 2026-04-18
source: rrr: thai-legal-rag
---

# Eval with external LLM API needs 3 safety layers: (1) pre-flight ping before loa

Eval with external LLM API needs 3 safety layers: (1) pre-flight ping before loading index — exit fast if API down; (2) per-TC try-except around generate_answer() — skip TC instead of crashing whole run; (3) circuit breaker — abort after N consecutive API-error skips. Without these, eval hangs for hours with 0 results when API is down.

---
*Added via Oracle Learn*
