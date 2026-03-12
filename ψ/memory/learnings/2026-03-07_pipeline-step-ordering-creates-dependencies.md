# Pipeline Step Ordering Creates Implicit Dependencies

**Date**: 2026-03-07
**Source**: thai-legal-rag reranker — glossary injection for TC-042
**Tags**: #rag #reranker #pipeline #architecture

## Pattern

When adding a new step to a multi-stage pipeline, the placement relative to other steps creates implicit dependencies. A step that injects new items must come BEFORE any step that expands or enriches those items.

## Example

Reranker pipeline: MMR selection -> source completion -> source expansion -> glossary injection

Problem: Glossary injection added 49821 to results, but source expansion had already run — so 49821 only had its anchor chunk, not the content chunks containing the key phrases.

Fix: Reorder to MMR -> source completion -> glossary injection -> source expansion. Now glossary-injected sources get expanded too.

## Additional Insight

When a step has a processing limit (e.g., "expand top 5 sources"), items added by earlier steps compete for those slots. Priority ordering (process glossary-injected items first) ensures the intended items aren't crowded out.

Selection criteria should also match injection reason: glossary-injected sources should be expanded by glossary term match count, not by generic heuristics like "longest chunk". The whole point of injection was to bring in specific content — expanding with generic criteria defeats the purpose.

## Generalization

For any pipeline with inject -> enrich stages:
1. Inject step must precede enrich step
2. Injected items may need priority in the enrich step (limited budgets)
3. Enrich criteria should be context-aware (why was this item injected?)
