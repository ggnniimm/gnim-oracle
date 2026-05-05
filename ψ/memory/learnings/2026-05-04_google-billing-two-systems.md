# Google Cloud Billing: Two Separate Systems

**Date**: 2026-05-04
**Context**: thai-legal-rag embedding quota hunt

## The Split

Google Cloud has two completely separate billing systems that do NOT share credits:

| System | API | Credits | Quota |
|--------|-----|---------|-------|
| **Vertex AI** | `aiplatform.googleapis.com` | GCP credits ($300 trial) | ~7 texts/min default (low) |
| **AI Studio** | `generativelanguage.googleapis.com` | AI Studio prepayment only | 1500 RPM paid tier |

## Key Facts

- **$300 GCP trial credits explicitly CANNOT be used for AI Studio** — documented in Google Cloud Free Tier ToS: "You cannot use your $300 welcome credit toward Gemini Developer API (AI Studio) costs"
- Vertex AI embedding quota (~7 texts/min) is a **platform policy** — same on every new GCP project regardless of billing status
- `unset VARIABLE` in shell doesn't block `python-dotenv` — use `export VARIABLE=` (empty string) instead
- Changing embedding models = re-tuning all RAG artifacts (cross-refs, rescue phrases, eval TCs) — not just a config change

## To Get High Quota

- **Stay on gemini-embedding-2-preview (Vertex)**: Request quota increase — free, takes 1-3 days
- **Use AI Studio high quota**: Add prepayment credits to AI Studio separately (real money)
- **OpenAI**: High quota but breaks all existing RAG tuning — not viable without full re-tune
