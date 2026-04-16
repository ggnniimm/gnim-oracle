---
title: Vector Store Path Alignment — Indexer and Search Must Use Same Path + Collection
tags: [vector-search, lancedb, bge-m3, ollama, arra-oracle, path-alignment, debugging]
created: 2026-04-15
source: rrr: gnim-oracle-qdrant oracle KB fix session
---

# Vector Store Path Alignment — Indexer and Search Must Use Same Path + Collection

## Rule
When vector search returns negative scores or garbage results, check THREE things:
1. **Model installed?** — `ollama list` to verify the embedding model exists
2. **Index populated?** — does the vector store directory actually exist and have data?
3. **Path + collection aligned?** — does the indexer write to the SAME path/collection that the search reads from?

## Root Cause Pattern
arra-oracle-v3 had a design mismatch:
- **Indexer** (`cli.ts`): writes to `CHROMADB_DIR` (`~/.chromadb/`) with collection `oracle_knowledge`
- **Search** (`factory.ts` bge-m3 preset): reads from `LANCEDB_DIR` (`~/.arra-oracle-v2/lancedb/`) with collection `oracle_knowledge_bge_m3`

Result: vector search returns 6 results with scores like -315 to -374 (distance metric on an empty/wrong table).

## Fix
Patch `factory.ts` bge-m3 preset to match where indexer actually writes:
```ts
'bge-m3': {
  collection: COLLECTION_NAME,  // 'oracle_knowledge' — matches indexer
  model: 'bge-m3',
  dataPath: CHROMADB_DIR,       // '~/.chromadb' — matches indexer
},
```
Then re-index with `ORACLE_EMBEDDING_MODEL=bge-m3` so vectors use the right model.

## Diagnosis Steps
1. `ollama list` — check model is installed
2. `ls ~/.arra-oracle-v2/lancedb/` + `ls ~/.chromadb/` — find where data actually is
3. Read `factory.ts` `getEmbeddingModels()` — find what path/collection search expects
4. Read `indexer/cli.ts` + `indexer/index.ts` — find what path/collection indexer writes
5. Compare → patch to align

## After Fix
- `ollama pull bge-m3` (1.2 GB)
- Patch `factory.ts`
- Re-run: `ORACLE_REPO_ROOT=/path/to/repo ORACLE_EMBEDDING_MODEL=bge-m3 bun run index`
- Restart Claude to reload MCP server with new code

## MCP env var: ORACLE_REPO_ROOT
Must be set in MCP registration so server knows where `ψ/` lives:
```bash
claude mcp add "arra-oracle-v2" -s local \
  -e ORACLE_REPO_ROOT=/path/to/repo \
  -- bun /path/to/arra-oracle-v3/src/index.ts
```
