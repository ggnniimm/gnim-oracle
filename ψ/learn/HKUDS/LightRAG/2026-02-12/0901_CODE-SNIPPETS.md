# LightRAG Code Exploration: Key Components & Patterns

**Date**: 2026-02-12  
**Source**: /home/codespace/ghq/github.com/HKUDS/LightRAG  
**Version**: 1.4.10  
**Author**: Zirui Guo  
**Repository**: https://github.com/HKUDS/LightRAG

---

## Overview

LightRAG is a **Simple and Fast Retrieval-Augmented Generation** framework that combines knowledge graphs with vector databases for efficient information retrieval. It uses a dual-level retrieval approach with local (entity-focused) and global (relationship-focused) strategies.

---

## Architecture

### Core Files
- `lightrag.py` - Main LightRAG class (2500+ lines)
- `operate.py` - Core operations: entity extraction, graph merging, querying (4800+ lines)
- `base.py` - Abstract base classes and type definitions
- `types.py` - Pydantic models for data structures
- `utils_graph.py` - Graph utility functions and deletions
- `utils.py` - General utilities and helpers (3500+ lines)
- `kg/` - Storage implementations (11+ different backends)

---

## 1. Main Entry Point: LightRAG Class

### Initialization Pattern

```python
@final
@dataclass
class LightRAG:
    """LightRAG: Simple and Fast Retrieval-Augmented Generation."""

    # Directory
    working_dir: str = field(default="./rag_storage")
    
    # Storage backends
    kv_storage: str = field(default="JsonKVStorage")
    vector_storage: str = field(default="NanoVectorDBStorage")
    graph_storage: str = field(default="NetworkXStorage")
    doc_status_storage: str = field(default="JsonDocStatusStorage")
    
    # LLM & Embedding functions
    llm_model_func: Callable[..., Awaitable[str]] = None
    embedding_func: EmbeddingFunc = None
    
    # Query parameters
    top_k: int = field(default=get_env_value("TOP_K", DEFAULT_TOP_K, int))
    chunk_top_k: int = field(default=get_env_value("CHUNK_TOP_K", DEFAULT_CHUNK_TOP_K, int))
    max_entity_tokens: int = field(default=get_env_value("MAX_ENTITY_TOKENS", DEFAULT_MAX_ENTITY_TOKENS, int))
    max_relation_tokens: int = field(default=get_env_value("MAX_RELATION_TOKENS", DEFAULT_MAX_RELATION_TOKENS, int))
    max_total_tokens: int = field(default=get_env_value("MAX_TOTAL_TOKENS", DEFAULT_MAX_TOTAL_TOKENS, int))
    
    # Tokenizer
    tokenizer: Tokenizer = None
    tiktoken_model_name: str = field(default="gpt-4")
```

### Example Usage

```python
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed

async def initialize_rag():
    rag = LightRAG(
        working_dir="./dickens",
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )
    await rag.initialize_storages()  # Auto-initializes pipeline_status
    return rag

async def main():
    rag = await initialize_rag()
    
    # Insert document
    with open("./book.txt", "r", encoding="utf-8") as f:
        track_id = await rag.ainsert(f.read())
    
    # Query with different modes
    result_naive = await rag.aquery(
        "What are the top themes?",
        param=QueryParam(mode="naive")
    )
    result_local = await rag.aquery(
        "What are the top themes?",
        param=QueryParam(mode="local")
    )
    result_global = await rag.aquery(
        "What are the top themes?",
        param=QueryParam(mode="global")
    )
    result_hybrid = await rag.aquery(
        "What are the top themes?",
        param=QueryParam(mode="hybrid")
    )
    
    await rag.finalize_storages()

asyncio.run(main())
```

---

## 2. Document Insertion Pipeline

### Insert Methods

```python
def insert(
    self,
    input: str | list[str],
    split_by_character: str | None = None,
    split_by_character_only: bool = False,
    ids: str | list[str] | None = None,
    file_paths: str | list[str] | None = None,
    track_id: str | None = None,
) -> str:
    """Sync Insert documents with checkpoint support
    
    Args:
        input: Single document string or list of document strings
        split_by_character: Split by character first, then by token if needed
        split_by_character_only: Only split by character (no token splitting)
        ids: Document IDs (auto-generated if not provided)
        file_paths: File paths for citation tracking
        track_id: Tracking ID for monitoring (auto-generated if not provided)
    
    Returns:
        str: tracking ID for monitoring processing status
    """
    loop = always_get_an_event_loop()
    return loop.run_until_complete(
        self.ainsert(input, split_by_character, split_by_character_only, ids, file_paths, track_id)
    )

async def ainsert(
    self,
    input: str | list[str],
    split_by_character: str | None = None,
    split_by_character_only: bool = False,
    ids: str | list[str] | None = None,
    file_paths: str | list[str] | None = None,
    track_id: str | None = None,
) -> str:
    """Async Insert documents with checkpoint support"""
    if track_id is None:
        track_id = generate_track_id("insert")
    
    await self.apipeline_enqueue_documents(input, ids, file_paths, track_id)
    await self.apipeline_process_enqueue_documents(split_by_character, split_by_character_only)
    
    return track_id
```

### Chunking Pipeline

```python
def chunking_by_token_size(
    tokenizer: Tokenizer,
    content: str,
    split_by_character: str | None = None,
    split_by_character_only: bool = False,
    chunk_overlap_token_size: int = 100,
    chunk_token_size: int = 1200,
) -> list[dict[str, Any]]:
    """
    Split content into chunks by token size with optional character splitting.
    
    Strategy:
    1. If split_by_character provided, split by that character first
    2. If individual chunks exceed token limit, split them by token size
    3. If split_by_character_only=True, raise error if chunk exceeds token limit
    4. Apply token overlap between chunks for context continuity
    
    Returns:
        list[dict]: Chunks with structure:
            {
                "tokens": int,
                "content": str,
                "chunk_order_index": int
            }
    """
    tokens = tokenizer.encode(content)
    results: list[dict[str, Any]] = []
    
    if split_by_character:
        raw_chunks = content.split(split_by_character)
        new_chunks = []
        # ... process chunks with token size limits
    else:
        for index, start in enumerate(range(0, len(tokens), chunk_token_size - chunk_overlap_token_size)):
            chunk_content = tokenizer.decode(tokens[start : start + chunk_token_size])
            results.append({
                "tokens": min(chunk_token_size, len(tokens) - start),
                "content": chunk_content.strip(),
                "chunk_order_index": index,
            })
    
    return results
```

---

## 3. Entity Extraction & Graph Building

### Extract Entities Function

```python
async def extract_entities(
    chunks: dict[str, TextChunkSchema],
    global_config: dict[str, str],
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
    text_chunks_storage: BaseKVStorage | None = None,
) -> list:
    """
    Extract entities and relationships from text chunks using LLM.
    
    Process:
    1. For each chunk, call LLM with entity extraction prompt
    2. Support gleaning (continue extraction) up to entity_extract_max_gleaning times
    3. Cache LLM responses for efficiency
    4. Return list of (maybe_nodes, maybe_edges) tuples per chunk
    
    Entity Extraction Prompt includes:
    - Entity types (Person, Organization, Location, Event, etc.)
    - Examples in format: (ENTITY_NAME, ENTITY_TYPE, DESCRIPTION)
    - Delimiter configuration for parsing
    """
    use_llm_func: callable = global_config["llm_model_func"]
    entity_extract_max_gleaning = global_config["entity_extract_max_gleaning"]
    
    ordered_chunks = list(chunks.items())
    language = global_config["addon_params"].get("language", DEFAULT_SUMMARY_LANGUAGE)
    entity_types = global_config["addon_params"].get("entity_types", DEFAULT_ENTITY_TYPES)
    
    # Build context with entity types and examples
    examples = "\n".join(PROMPTS["entity_extraction_examples"])
    context_base = dict(
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        entity_types=",".join(entity_types),
        examples=examples,
        language=language,
    )
    
    # Process each chunk and collect results
    results = []
    for chunk_key, chunk_dp in ordered_chunks:
        content = chunk_dp["content"]
        file_path = chunk_dp.get("file_path", "unknown_source")
        
        # LLM call with caching
        final_result, timestamp = await use_llm_func_with_cache(
            entity_extraction_user_prompt.format(**{**context_base, "input_text": content}),
            use_llm_func,
            system_prompt=entity_extraction_system_prompt,
            cache_type="extract",
            chunk_id=chunk_key,
        )
        
        # Parse and process extraction result
        maybe_nodes, maybe_edges = await _process_extraction_result(final_result, chunk_key, timestamp, file_path)
        results.append((maybe_nodes, maybe_edges))
    
    return results
```

### Merge Nodes and Edges (Two-Phase Approach)

```python
async def merge_nodes_and_edges(
    chunk_results: list,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict[str, str],
    full_entities_storage: BaseKVStorage = None,
    full_relations_storage: BaseKVStorage = None,
    doc_id: str = None,
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
    entity_chunks_storage: BaseKVStorage | None = None,
    relation_chunks_storage: BaseKVStorage | None = None,
) -> None:
    """
    Two-phase merge: process all entities first, then all relationships.
    
    Strategy:
    1. PHASE 1: Collect all entities from all chunks
       - Process each entity concurrently with semaphore control
       - Merge entity descriptions using map-reduce LLM summarization
       - Upsert entities to vector DB and graph storage
    
    2. PHASE 2: Collect all relationships from all chunks
       - Process each relationship concurrently
       - Handle missing entities (create if needed)
       - Merge relationship descriptions
       - Upsert relationships to vector DB and graph storage
    
    3. PHASE 3: Update storage with final entity/relation lists
       - Track which documents have which entities/relations
    
    Innovation: Two-phase approach ensures data consistency and atomicity.
    Uses keyed locks to prevent race conditions on graph operations.
    """
    
    # Collect all nodes and edges with sorted keys for undirected graph
    all_nodes = defaultdict(list)
    all_edges = defaultdict(list)
    
    for maybe_nodes, maybe_edges in chunk_results:
        for entity_name, entities in maybe_nodes.items():
            all_nodes[entity_name].extend(entities)
        for edge_key, edges in maybe_edges.items():
            sorted_edge_key = tuple(sorted(edge_key))
            all_edges[sorted_edge_key].extend(edges)
    
    # Phase 1: Process entities concurrently with semaphore
    graph_max_async = global_config.get("llm_model_max_async", 4) * 2
    semaphore = asyncio.Semaphore(graph_max_async)
    
    entity_tasks = []
    for entity_name, entities in all_nodes.items():
        task = asyncio.create_task(_locked_process_entity_name(entity_name, entities))
        entity_tasks.append(task)
    
    # Phase 2: Process relationships concurrently
    edge_tasks = []
    for edge_key, edges in all_edges.items():
        task = asyncio.create_task(_locked_process_edges(edge_key, edges))
        edge_tasks.append(task)
```

### LLM-Based Entity/Relationship Description Summarization

```python
async def _handle_entity_relation_summary(
    description_type: str,
    entity_or_relation_name: str,
    description_list: list[str],
    separator: str,
    global_config: dict,
    llm_response_cache: BaseKVStorage | None = None,
) -> tuple[str, bool]:
    """
    Map-Reduce summary pattern for entity/relation descriptions.
    
    Strategy:
    1. If only 1 description: return directly (no LLM needed)
    2. If total tokens < summary_max_tokens: summarize with single LLM call
    3. If total tokens > summary_max_tokens: 
       a. Split descriptions into chunks
       b. Summarize each chunk with LLM
       c. Recursively summarize the summaries until converged
    
    Returns:
        Tuple of (final_description, was_llm_used)
    
    This is an innovative pattern that allows handling arbitrarily
    many descriptions without exploding LLM context window.
    """
    if not description_list:
        return "", False
    
    if len(description_list) == 1:
        return description_list[0], False
    
    tokenizer: Tokenizer = global_config["tokenizer"]
    summary_max_tokens = global_config["summary_max_tokens"]
    summary_context_size = global_config["summary_context_size"]
    
    # Check if summarization is needed
    total_tokens = sum(len(tokenizer.encode(d)) for d in description_list)
    
    if total_tokens < summary_context_size and len(description_list) < force_llm_summary_on_merge:
        # Return combined descriptions without LLM
        return separator.join(description_list), False
    
    # Use LLM for summarization with map-reduce pattern
    ...
```

---

## 4. Query System

### QueryParam Configuration

```python
@dataclass
class QueryParam:
    """Configuration parameters for query execution in LightRAG."""

    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = "mix"
    """
    Retrieval modes:
    - "local": Entity-focused, finds context about specific entities
    - "global": Relationship-focused, explores knowledge graph structure
    - "hybrid": Combines local and global strategies
    - "naive": Simple vector DB search without graph awareness
    - "mix": Integrates knowledge graph and vector retrieval (default)
    - "bypass": Direct LLM call without retrieval
    """

    only_need_context: bool = False
    """If True, only returns retrieved context without LLM generation"""

    only_need_prompt: bool = False
    """If True, returns the prompt sent to LLM without generation"""

    response_type: str = "Multiple Paragraphs"
    """Response format: 'Multiple Paragraphs', 'Single Paragraph', 'Bullet Points'"""

    stream: bool = False
    """Enable streaming responses"""

    top_k: int = 10
    """Number of top entities/relations to retrieve"""

    chunk_top_k: int = 10
    """Number of text chunks to retrieve and keep after reranking"""

    enable_rerank: bool = True
    """Enable reranking of retrieved chunks (if reranker available)"""

    include_references: bool = False
    """Include citation/reference information in response"""
```

### Query Methods

```python
def query(
    self,
    query: str,
    param: QueryParam = QueryParam(),
    system_prompt: str | None = None,
) -> str | Iterator[str]:
    """
    Synchronous query execution.
    
    Returns:
        str: LLM response content
        Iterator[str]: Streaming response if param.stream=True
    """
    loop = always_get_an_event_loop()
    return loop.run_until_complete(self.aquery(query, param, system_prompt))

async def aquery(
    self,
    query: str,
    param: QueryParam = QueryParam(),
    system_prompt: str | None = None,
) -> str | AsyncIterator[str]:
    """
    Asynchronous query execution (backward compatibility wrapper).
    Internally calls aquery_llm and extracts LLM response content.
    """
    result = await self.aquery_llm(query, param, system_prompt)
    llm_response = result.get("llm_response", {})
    
    if llm_response.get("is_streaming"):
        return llm_response.get("response_iterator")
    else:
        return llm_response.get("content", "")

async def aquery_data(
    self,
    query: str,
    param: QueryParam = QueryParam(),
) -> dict[str, Any]:
    """
    Data retrieval API: returns structured results WITHOUT LLM generation.
    
    Returns:
        dict with structure:
        {
            "status": "success",
            "message": "Query executed successfully",
            "data": {
                "entities": [...],
                "relationships": [...],
                "chunks": [...]
            }
        }
    """
```

### Knowledge Graph Query Function

```python
async def kg_query(
    query: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
    system_prompt: str | None = None,
    chunks_vdb: BaseVectorStorage = None,
) -> QueryResult | None:
    """
    Execute knowledge graph query and return unified QueryResult.
    
    Process:
    1. Extract high-level and low-level keywords from query
    2. Build query context by retrieving relevant entities, relations, and chunks
    3. If only_need_context=True, return context (no LLM call)
    4. If only_need_prompt=True, return the full prompt (no LLM call)
    5. Otherwise, call LLM with system prompt and context
    6. Cache results for repeated queries
    
    Returns:
        QueryResult with fields:
        - content: str (non-streaming response)
        - response_iterator: AsyncIterator[str] (streaming)
        - raw_data: dict (complete structured data)
        - is_streaming: bool
    """
    if not query:
        return QueryResult(content=PROMPTS["fail_response"])
    
    # Extract keywords using LLM
    hl_keywords, ll_keywords = await get_keywords_from_query(
        query, query_param, global_config, hashing_kv
    )
    
    logger.debug(f"High-level keywords: {hl_keywords}")
    logger.debug(f"Low-level keywords: {ll_keywords}")
    
    # Build query context
    context_result = await _build_query_context(
        query, ll_keywords_str, hl_keywords_str,
        knowledge_graph_inst, entities_vdb, relationships_vdb,
        text_chunks_db, query_param, chunks_vdb
    )
    
    # Call LLM if needed
    if not query_param.only_need_context and not query_param.only_need_prompt:
        sys_prompt = PROMPTS["rag_response"].format(
            response_type=query_param.response_type,
            context_data=context_result.context
        )
        
        response = await use_model_func(
            query,
            system_prompt=sys_prompt,
            stream=query_param.stream
        )
    
    return QueryResult(content=response, raw_data=context_result.raw_data)
```

---

## 5. Storage System

### Supported Backends

```python
STORAGES = {
    # Key-Value Storage
    "JsonKVStorage": JSON file-based key-value store,
    "RedisKVStorage": Redis backend,
    
    # Vector Database
    "NanoVectorDBStorage": Lightweight in-memory vector DB (default),
    "FaissVectorStorage": Facebook AI Similarity Search,
    "MilvusVectorStorage": Distributed vector database,
    "QdrantVectorStorage": Vector DB with advanced features,
    
    # Graph Storage
    "NetworkXStorage": In-memory graph (default, uses GraphML),
    "Neo4jStorage": Neo4j graph database,
    "MemgraphStorage": High-performance graph DB,
    
    # Document Status Tracking
    "JsonDocStatusStorage": JSON-based document status tracker,
    
    # All-in-one solutions
    "PostgresStorage": PostgreSQL for all data types,
    "MongoDBStorage": MongoDB for all data types,
}
```

### Storage Initialization Pattern

```python
# User specifies storage types
rag = LightRAG(
    working_dir="./rag_storage",
    kv_storage="JsonKVStorage",
    vector_storage="NanoVectorDBStorage",
    graph_storage="NetworkXStorage",
    doc_status_storage="JsonDocStatusStorage"
)

# Initialize storage instances
await rag.initialize_storages()

# After processing, finalize
await rag.finalize_storages()
```

---

## 6. Custom Knowledge Graph Insertion

### Custom KG Structure

```python
custom_kg = {
    "entities": [
        {
            "entity_name": "CompanyA",
            "entity_type": "Organization",
            "description": "A major technology company",
            "source_id": "Source1",
        },
        {
            "entity_name": "ProductX",
            "entity_type": "Product",
            "description": "A popular product developed by CompanyA",
            "source_id": "Source1",
        },
    ],
    "relationships": [
        {
            "src_id": "CompanyA",
            "tgt_id": "ProductX",
            "description": "CompanyA develops ProductX",
            "keywords": "develop, produce",
            "weight": 1.0,
            "source_id": "Source1",
        },
    ],
    "chunks": [
        {
            "content": "ProductX, developed by CompanyA, revolutionized the market...",
            "source_id": "Source1",
            "source_chunk_index": 0,
        },
    ],
}

rag.insert_custom_kg(custom_kg)
```

### KnowledgeGraph Data Model

```python
class KnowledgeGraphNode(BaseModel):
    id: str
    labels: list[str]
    properties: dict[str, Any]

class KnowledgeGraphEdge(BaseModel):
    id: str
    type: Optional[str]
    source: str  # id of source node
    target: str  # id of target node
    properties: dict[str, Any]

class KnowledgeGraph(BaseModel):
    nodes: list[KnowledgeGraphNode] = []
    edges: list[KnowledgeGraphEdge] = []
    is_truncated: bool = False
```

---

## 7. Key Patterns & Innovations

### Pattern 1: Token-Based Chunking with Overlap

```
Document -> Split by character (if specified) -> Token-count based splitting
          -> Apply token overlap (e.g., 100 tokens) for context continuity
          -> Validate against max chunk size
```

**Innovation**: Combines linguistic boundaries (character) with token limits to maintain semantic coherence.

### Pattern 2: Two-Phase Entity-Relation Merging

```
Extract Entities & Relations -> Phase 1: Merge Entities (concurrent)
                             -> Phase 2: Merge Relations (concurrent)
                             -> Phase 3: Update storage
```

**Innovation**: Two-phase approach ensures entities exist before relations reference them.

### Pattern 3: Map-Reduce Description Summarization

```
Multiple descriptions -> If total tokens < limit: return joined
                     -> If total tokens > limit: chunk + summarize each
                                               -> Recursively summarize summaries
                                               -> Continue until < limit
```

**Innovation**: Handles arbitrary numbers of descriptions without exploding context window.

### Pattern 4: Dual-Level Retrieval

```
Query -> Extract Keywords (high-level + low-level)
      -> Local mode: Find relevant entities, retrieve their chunks
      -> Global mode: Find important relationships, retrieve connected entities
      -> Hybrid: Combine both
      -> Mix: Use graph + vector search together
```

**Innovation**: Flexible retrieval modes for different query characteristics.

### Pattern 5: LLM Response Caching

```
Query -> Compute argument hash
      -> Check cache for identical query+mode+params
      -> If hit: return cached response
      -> If miss: call LLM, save to cache, return
```

**Innovation**: Eliminates redundant LLM calls for identical queries.

### Pattern 6: Async Pipeline with Status Tracking

```
Insert -> Enqueue documents -> Process in pipeline stages
       -> Track progress via pipeline_status dict
       -> Support cancellation at each stage
       -> Generate track_id for monitoring
```

**Innovation**: Enables progress monitoring and cancellation of long-running processes.

---

## 8. Example Implementations

### Example 1: Basic OpenAI RAG

```python
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed

async def main():
    rag = LightRAG(
        working_dir="./dickens",
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )
    
    await rag.initialize_storages()
    
    # Insert text
    with open("./book.txt", "r", encoding="utf-8") as f:
        await rag.ainsert(f.read())
    
    # Query with different modes
    for mode in ["naive", "local", "global", "hybrid", "mix"]:
        result = await rag.aquery(
            "What are the top themes?",
            param=QueryParam(mode=mode)
        )
        print(f"\n{mode.upper()}: {result}")
    
    await rag.finalize_storages()

asyncio.run(main())
```

### Example 2: Ollama Local Model

```python
import asyncio
from lightrag import LightRAG
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

async def main():
    rag = LightRAG(
        working_dir="./dickens",
        llm_model_func=ollama_model_complete,
        llm_model_name="qwen2.5-coder:7b",
        llm_model_kwargs={
            "host": "http://localhost:11434",
            "options": {"num_ctx": 8192},
        },
        embedding_func=EmbeddingFunc(
            ollama_embed.func,
            embedding_dim=768,
            max_token_size=512,
        ),
    )
    
    await rag.initialize_storages()
    # ... rest of pipeline
```

### Example 3: Graph Visualization with Neo4j

```python
# After building graph in LightRAG, visualize with Neo4j
from lightrag_webui.commons import LIGHTRAG_SCHEMA
from neo4j_visualization import visualize_graph

# Query the graph
kg = await rag.aquery_data("Your query")

# Visualize with Neo4j
visualize_graph(kg["data"]["entities"], kg["data"]["relationships"])
```

---

## 9. Configuration & Environment Variables

### Key Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=...
LLM_MODEL="gpt-4o-mini"

# Embedding Configuration
EMBEDDING_MODEL="text-embedding-3-small"

# Storage Configuration
KV_STORAGE="JsonKVStorage"
VECTOR_STORAGE="NanoVectorDBStorage"
GRAPH_STORAGE="NetworkXStorage"

# Query Parameters
TOP_K=10
CHUNK_TOP_K=10
MAX_ENTITY_TOKENS=3000
MAX_RELATION_TOKENS=3000
MAX_TOTAL_TOKENS=20000

# Chunking Configuration
CHUNK_TOKEN_SIZE=1200
CHUNK_OVERLAP_TOKEN_SIZE=100

# LLM Limits
SUMMARY_MAX_TOKENS=8192
MAX_EXTRACT_INPUT_TOKENS=100000

# Cache Configuration
ENABLE_LLM_CACHE="true"

# Reranking
RERANK_BY_DEFAULT="true"
```

---

## 10. Interesting Technical Details

### Source ID Tracking

Every entity and relationship maintains source IDs (chunk IDs) that reference them. This enables:
- Citation/provenance tracking
- Updating when source documents change
- Pruning based on document deletion

### Workspace Isolation

```python
rag = LightRAG(workspace="project_a")  # Separate namespace
# All data isolated from other workspaces
```

### Citation Support

Recent feature (2025-03) enables proper attribution:
```python
result = await rag.aquery(
    "What is X?",
    param=QueryParam(include_references=True)
)
# result includes: {"response": "...", "references": [...]}
```

### Reranking Integration

Supports reranking to improve relevance (enabled by default):
```python
result = await rag.aquery(
    "query",
    param=QueryParam(enable_rerank=True)
)
```

### Namespace-Based Locking

Uses keyed locks for concurrent graph operations:
```python
async with get_storage_keyed_lock(
    [entity_name],
    namespace="GraphDB",
    enable_logging=False
):
    # Atomic graph update
```

---

## 11. Performance Optimizations

1. **Prompt Caching**: OpenAI prompt caching for entity extraction system prompts across chunks
2. **Semaphore-Controlled Concurrency**: Limits parallel operations to prevent resource exhaustion
3. **Vector Similarity Thresholding**: Filters results below cosine similarity threshold
4. **LLM Response Caching**: Avoids redundant calls for identical queries
5. **Batch VDB Operations**: Groups vector operations for efficiency
6. **Async Everywhere**: Non-blocking I/O for all storage operations

---

## 12. Key Files to Deep-Dive

1. **lightrag.py** (2500+ lines)
   - Main LightRAG class
   - Insert pipeline coordination
   - Query routing logic
   - Storage initialization

2. **operate.py** (4800+ lines)
   - Entity extraction
   - Merge operations
   - Query execution
   - Graph operations

3. **utils_graph.py** (1500+ lines)
   - Entity/relation deletion
   - Graph traversal
   - Atomic operations

4. **kg/ directory** (11+ backends)
   - Storage implementations
   - Vendor-specific optimizations
   - Shared storage utilities

---

## References

- **GitHub**: https://github.com/HKUDS/LightRAG
- **arXiv**: https://arxiv.org/abs/2410.05779
- **PyPI**: https://pypi.org/project/lightrag-hku/
- **LearnOpenCV Tutorial**: https://learnopencv.com/lightrag/

---

**Document Generated**: 2026-02-12 09:01 UTC  
**Exploration Depth**: Comprehensive code review with pattern analysis  
**Purpose**: Knowledge preservation and architectural understanding
