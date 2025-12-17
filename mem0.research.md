# mem0 Technical Research Report

Last Updated: 2025-12-17

> **Research Methodology**: This document was generated through collaborative code repository analysis by Claude Code, Gemini CLI, and Codex CLI, with final summarization by Claude Code.

## Overview

**mem0** is an open-source memory layer for LLM applications that goes beyond traditional RAG systems. It provides a self-improving, adaptive memory system that actively manages user, session, and agent states through LLM-driven fact extraction and conflict resolution.

**Source:** [mem0 GitHub Repository](https://github.com/mem0ai/mem0)

---

## 1. Core Technical Approach

### Memory Lifecycle (Key Differentiator)

Unlike standard vector stores that passively append data, mem0 **actively manages** memory:

1. **Fact Extraction** - LLM extracts atomic facts from conversations (e.g., "User likes Python")
2. **Conflict Resolution** - Retrieves existing memories and compares via LLM reasoning
3. **Action Execution** - Performs `ADD`, `UPDATE`, or `DELETE` based on semantic analysis
4. **Multi-Level Scoping** - Memories tagged with `user_id`, `agent_id`, `run_id` for precise retrieval

### vs Traditional RAG

| Feature | Traditional RAG | mem0 |
|---------|----------------|------|
| **Unit of Storage** | Document chunks (static) | Atomic facts (dynamic, synthesized) |
| **Update Mechanism** | Append-only | Active CRUD via LLM reasoning |
| **Deduplication** | Vector distance only | Semantic deduplication via LLM |
| **Relationships** | Implicit (vector proximity) | Explicit (Graph Memory) |
| **Focus** | Knowledge retrieval | User/Agent state & personalization |

---

## 2. Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Memory API Layer                        │
│     Memory, AsyncMemory, MemoryClient, AsyncMemoryClient    │
└──────────────────────────────┬──────────────────────────────┘
                               │
      ┌────────────────┬───────┴────────┬──────────────────┐
      │                │                │                  │
 ┌────▼─────┐   ┌──────▼──────┐  ┌──────▼─────┐   ┌───────▼──────┐
 │  Vector  │   │ LLM Extract │  │   Graph    │   │   SQLite     │
 │  Stores  │   │  Pipeline   │  │   Memory   │   │   History    │
 │  (24+)   │   │             │  │  (Neo4j+)  │   │              │
 └──────────┘   └─────────────┘  └────────────┘   └──────────────┘
```

### Key Abstractions

| Interface | Location | Purpose |
|-----------|----------|---------|
| `MemoryBase` | `mem0/memory/base.py` | Core API: get/get_all/update/delete/history |
| `VectorStoreBase` | `mem0/vector_stores/base.py` | CRUD + list/reset for vectors |
| `EmbeddingBase` | `mem0/embeddings/base.py` | `embed(text, memory_action)` |
| `LLMBase` | `mem0/llms/base.py` | `generate_response` with tool support |

### Memory Class Composition (`mem0/memory/main.py:172`)

```python
class Memory(MemoryBase):
    def __init__(self, config: MemoryConfig):
        self.embedding_model = EmbedderFactory.create(...)
        self.vector_store = VectorStoreFactory.create(...)
        self.llm = LlmFactory.create(...)
        self.db = SQLiteManager(...)      # History tracking
        self.reranker = RerankerFactory.create(...)  # Optional
        self.graph = GraphStoreFactory.create(...)    # Optional
```

---

## 3. Memory Processing Pipeline

### Add Pipeline (Two-Stage LLM Processing)

**Stage 1: Fact Extraction**
```
Input Messages → LLM Extraction → JSON {"facts": ["fact1", "fact2", ...]}
```
- Uses `USER_MEMORY_EXTRACTION_PROMPT` or `AGENT_MEMORY_EXTRACTION_PROMPT`
- Extracts facts **only** from user OR assistant messages based on context

**Stage 2: Memory Action Planning**
```
Extracted Facts + Existing Memories → LLM Reasoning → Action Plan
```
- For each fact: embed → search top-5 similar memories
- LLM decides: `ADD` | `UPDATE` | `DELETE` | `NONE`
- Mitigates UUID hallucination via temporary index mapping

**Parallel Execution:**
```python
with ThreadPoolExecutor() as executor:
    future1 = executor.submit(self._add_to_vector_store, ...)
    future2 = executor.submit(self._add_to_graph, ...)
```

### Search Pipeline

1. **Query Embedding** - `embed(query, action="search")`
2. **Parallel Retrieval:**
   - Vector Store: semantic similarity search
   - Graph Store: entity relationship traversal
3. **Optional Reranking** - Cohere, BGE-M3, etc.
4. **Result Merging** - `{"results": [...], "relations": [...]}`

---

## 4. Storage Layer

### Vector Stores (24+ Providers)

| Category | Providers |
|----------|-----------|
| **Cloud Native** | Qdrant, Pinecone, Weaviate, Milvus |
| **Database Extensions** | PGVector, Redis, MongoDB, Valkey |
| **Enterprise Search** | Azure AI Search, Elasticsearch, OpenSearch |
| **Data Warehouse** | Databricks, Vertex AI Vector Search |
| **Local** | FAISS, Chroma |
| **Specialized** | Cassandra, Neptune, Supabase, S3 Vectors |

### Vector Payload Structure

```python
payload = {
    "data": "The actual memory text",
    "hash": "md5_for_deduplication",
    "user_id": "user123",
    "agent_id": "agent456",
    "run_id": "run789",
    "created_at": "2024-12-17T...",
    "updated_at": "2024-12-17T...",
    # Custom metadata...
}
```

### Graph Memory

**Providers:** Neo4j (primary), Memgraph, Kuzu, Neptune

**Ingestion Algorithm:**
1. Extract entities + types via tool-calling (`EXTRACT_ENTITIES_TOOL`)
2. Extract relationships via `RELATIONS_TOOL`
3. Search existing graph for similar entities (embedding similarity)
4. LLM decides which relations to delete (`DELETE_MEMORY_TOOL_GRAPH`)
5. Delete → Add/Merge relations; store per-node embeddings

**Key Insight:** Vector and Graph are **parallel, loosely coupled projections**:
- No shared primary key
- `update/delete` operate only on vector store
- Graph can diverge unless refreshed via `add()` or cleared via `delete_all()`

### History Tracking (SQLite)

```python
class SQLiteManager:
    def add_history(self, memory_id, old_memory, new_memory, event, ...):
        # Records: ADD, UPDATE, DELETE events
        # Includes: actor_id, role, timestamps
```

---

## 5. Supported Integrations

### Embedding Models (12+)
OpenAI, Azure OpenAI, Gemini, HuggingFace, Ollama, Vertex AI, Together AI, FastEmbed, LMStudio, AWS Bedrock (Cohere, Titan)

### LLMs (20+)
OpenAI (incl. o1/o3 reasoning models), Anthropic, Gemini, Groq, Ollama, vLLM, DeepSeek, Together, LiteLLM, XAI, Sarvam, AWS Bedrock

### Rerankers
Cohere, BGE-M3, Cross-encoder models

---

## 6. Design Patterns

### Factory Pattern
```python
# Dynamic provider instantiation
llm = LlmFactory.create("openai", config=OpenAIConfig(model="gpt-4"))
vs = VectorStoreFactory.create("qdrant", {...})
```

Extensible via `register_provider()`.

### Configuration (Pydantic)
```python
MemoryConfig(
    vector_store=VectorStoreConfig(provider="qdrant", config={...}),
    llm=LlmConfig(provider="openai", config={...}),
    embedder=EmbedderConfig(provider="openai", config={...}),
    graph_store=GraphStoreConfig(provider="neo4j")
)
```

### Error Handling
- Structured exceptions in `mem0/exceptions.py`
- LLM output parsing: strip fences → regex fallback → empty fallback
- Optional dependencies raise `ImportError` with install hints

### Concurrency
- Sync: `ThreadPoolExecutor` for parallel vector + graph operations
- Async: `asyncio.to_thread()` + `gather()` for async variants

---

## 7. Critical Implementation Details

### Score Semantics Caveat
- `Memory.search` treats score as "higher is better"
- **Some providers return distance (lower is better)**: Chroma, PGVector
- `threshold` parameter interpretation is **provider-dependent**

### Agent vs User Memory Extraction
```python
def _should_use_agent_memory_extraction(self, messages, metadata):
    has_agent_id = metadata.get("agent_id") is not None
    has_assistant_messages = any(msg.get("role") == "assistant" for msg in messages)
    return has_agent_id and has_assistant_messages
```

### Vector-Graph Drift
- `reset()` clears vector + SQLite but **not graph**
- `delete_all()` clears both
- Updates/deletes don't propagate to graph

---

## 8. Memory Types

```python
class MemoryType(Enum):
    SEMANTIC = "semantic_memory"      # Fact-based, cross-session
    EPISODIC = "episodic_memory"      # Event/interaction logs
    PROCEDURAL = "procedural_memory"  # Agent behavioral patterns
```

---

## 9. Use Cases

mem0 is particularly suited for:
- **Personalized AI assistants** - Remember user preferences across sessions
- **Long-running conversational agents** - Maintain context over time
- **Multi-agent systems** - Shared memory with scoping
- **Applications requiring evolving context** - Self-improving knowledge base

---

## 10. Key Takeaways

1. **Active Memory Management** - LLMs curate, update, and delete memories (not just append)
2. **Semantic Deduplication** - Prevents redundant information via LLM reasoning
3. **Dual Storage Strategy** - Vector (similarity) + Graph (relationships) in parallel
4. **Flexible Provider Ecosystem** - 50+ pluggable backends across 5 subsystems
5. **Session Scoping** - User/Agent/Run level isolation for multi-tenant applications
6. **History Tracking** - Immutable audit log of all memory mutations

---

## References

- [mem0 GitHub Repository](https://github.com/mem0ai/mem0)
- [mem0 Documentation](https://docs.mem0.ai/)
- Core implementation: `mem0/memory/main.py` (1300+ lines)
- Factory patterns: `mem0/utils/factory.py`
- Prompts: `mem0/configs/prompts.py`
