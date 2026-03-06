# Don't Name-Drop Tools Without Evidence

**Date**: 2026-03-05
**Context**: thai-legal-rag legal map discussion
**Source**: Ming's challenge — "มีคนใช้ Lightrag ในงานกฎหมายจริงๆ หรอ ไปหาจากไหนค้างใช่มั๊ย"

## Pattern

When discussing technical approaches, I used "Neo4j/LightRAG style" as if LightRAG is established in legal tech. It's not — it's a general-purpose open-source KG+RAG tool with no verified legal deployments.

## Why It Happened

- Wanted to sound comprehensive and specific
- Conflated "this tool exists" with "this tool is used in this domain"
- Same pattern as OCR hallucination: filling gaps with plausible specifics

## Rule

If you can't cite evidence that a specific tool is used in the domain being discussed, use generic descriptions:
- BAD: "Knowledge Graph — Neo4j/LightRAG style"
- GOOD: "Knowledge Graph approach (e.g., Neo4j for graph storage)"

## Meta-Pattern

AI hallucination is recursive. In the same session:
1. Found Gemini OCR hallucinating examples in บทสรุปสำหรับสืบค้น
2. I hallucinated a tool reference in discussion

Both follow the same pattern: filling in plausible-sounding details not grounded in evidence.

## Tags

`honesty`, `hallucination`, `domain-expertise`, `legal-tech`, `trust`
