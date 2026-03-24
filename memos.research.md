# MemOS Technical Research Report

Last Updated: 2026-03-24

> **Research Methodology**: This document was generated through source code analysis of the [MemOS repository](https://github.com/MemTensor/MemOS) (v2.0.10) combined with the project's arXiv papers and web research, analyzed by Claude Code.

## Overview

**MemOS** is an open-source Memory Operating System for LLMs and AI agents, developed by [MemTensor](https://www.memtensor.com.cn/) (Shanghai). Unlike memory layers that bolt onto existing frameworks (Mem0) or agent runtimes that manage memory as part of execution (Letta), MemOS treats memory as a **first-class system resource** and introduces a three-layer OS architecture with a unified **MemCube** abstraction that encapsulates heterogeneous memory types -- plaintext, activation (KV-cache), and parametric (weights) -- under standardized scheduling and orchestration.

MemOS originated from the [Memory3 model](https://arxiv.org/abs/2407.01178) (WAIC 2024), which introduced explicit memory carriers in attention mechanisms. The short paper was released May 28, 2025 ([arXiv:2505.22101](https://arxiv.org/abs/2505.22101)), and the full paper July 4, 2025 ([arXiv:2507.03724](https://arxiv.org/abs/2507.03724)).

**Source:** [MemTensor/MemOS on GitHub](https://github.com/MemTensor/MemOS) | [PyPI: MemoryOS](https://pypi.org/project/MemoryOS/) | Apache-2.0 License

---

## 1. Three-Layer OS Architecture

MemOS adopts a modular three-layer architecture analogous to an operating system:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Interface Layer (MemReader)                       │
│  REST API · MCP Server · Python SDK · OpenClaw Plugins              │
│  Parses requests → structured memory operations                     │
├─────────────────────────────────────────────────────────────────────┤
│                    Operation Layer (MemOS Core)                      │
│  MOSCore · MemScheduler · MemLifecycle · MemFeedback                │
│  Scheduling, lifecycle, CoT decomposition, conflict resolution      │
├─────────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                              │
│  Neo4j (graph) · Qdrant (vector) · MySQL/SQLite · Redis Streams     │
│  Memory storage, access control, multi-user management              │
└─────────────────────────────────────────────────────────────────────┘
```

### Interface Layer

The entry point for all memory operations. Key components:

| Component | Location | Purpose |
|-----------|----------|---------|
| REST API | `src/memos/api/routers/` | Product, server, and admin endpoints |
| MCP Server | `src/memos/api/mcp_serve.py` | Model Context Protocol for tool-based memory access |
| MemReader | `src/memos/mem_reader/` | Translates raw input (messages, docs, images) into structured memory items |
| Python SDK | `MOS` class | Direct programmatic access (`MOS.simple()`) |

MemReader has three backends:
- **SimpleStructMemReader** -- basic text-to-memory extraction via LLM prompts
- **StrategyStructMemReader** -- strategy-based extraction with conflict resolution
- **MultiModalStructMemReader** -- handles images, tool traces, documents, URLs, and preference/skill memory

### Operation Layer

The central controller orchestrating memory lifecycle:

| Component | Location | Purpose |
|-----------|----------|---------|
| `MOSCore` | `src/memos/mem_os/core.py` | Core engine: manages MemCubes, users, chat, search |
| `MOS` | `src/memos/mem_os/main.py` | Extended core with CoT query decomposition (PRO mode) |
| `GeneralScheduler` | `src/memos/mem_scheduler/` | Async task scheduling via Redis Streams with priority queues |
| `MemFeedback` | `src/memos/mem_feedback/` | Natural-language feedback loop for memory correction |
| `UserManager` | `src/memos/mem_user/` | Multi-user access control with role-based permissions |

### Infrastructure Layer

Storage backends supporting the system:

| Backend | Used For | Notes |
|---------|----------|-------|
| Neo4j | Graph-structured tree text memory | Hierarchical topic/concept/fact organization |
| Qdrant | Vector similarity search | General text memory embedding store |
| Milvus | Preference memory vectors | MinHash deduplication + vector search |
| MySQL/SQLite | User management, history, metadata | Relational data and audit logs |
| Redis | Task scheduling, message queues | Redis Streams for async memory operations |

---

## 2. MemCube: The Unified Memory Container

MemCube is the core abstraction -- a standardized container that bundles heterogeneous memory types into a single manageable unit. Each MemCube has a `cube_id`, belongs to a `user_id`, and encapsulates up to four memory slots:

```python
# src/memos/mem_cube/general.py
class GeneralMemCube(BaseMemCube):
    _text_mem: BaseTextMemory | None     # Plaintext memory
    _act_mem: BaseActMemory | None       # Activation memory (KV-cache)
    _para_mem: BaseParaMemory | None     # Parametric memory (LoRA)
    _pref_mem: BaseTextMemory | None     # Preference memory
```

### MemCube Configuration

```python
# src/memos/configs/mem_cube.py
class GeneralMemCubeConfig(BaseMemCubeConfig):
    text_mem: MemoryConfigFactory   # backends: naive_text, general_text, tree_text
    act_mem: MemoryConfigFactory    # backends: kv_cache, vllm_kv_cache
    para_mem: MemoryConfigFactory   # backends: lora
    pref_mem: MemoryConfigFactory   # backends: pref_text
```

### Key MemCube Operations

- **`load(dir)`** / **`dump(dir)`** -- Serialize/deserialize all memory types to/from a directory
- **`init_from_dir(dir)`** -- Reconstruct a MemCube from a saved directory (includes `config.json`)
- **`init_from_remote_repo(cube_id)`** -- Load from HuggingFace datasets
- **Selective loading** -- Load only specific memory types: `load(dir, memory_types=["text_mem"])`

### Multi-Cube Composition

```python
# src/memos/multi_mem_cube/composite_cube.py
class CompositeCubeView:
    cube_views: list[SingleCubeView]

    def add_memories(...)    # Fan-out writes to all cubes
    def search_memories(...)  # Parallel search, merge results (text, act, para, pref, tool, skill)
    def feedback_memories(...)# Fan-out feedback to all cubes
```

MOSCore manages a dictionary of MemCubes (`mem_cubes: Dict[str, GeneralMemCube]`) and routes operations based on user-cube access permissions.

---

## 3. Three Memory Types

### A. Plaintext (Textual) Memory

The most developed and feature-rich memory type. Three backend implementations:

#### NaiveTextMemory (`naive_text`)
Simple in-memory list of `TextualMemoryItem` objects. No external storage dependency. Suitable for testing and lightweight use.

#### GeneralTextMemory (`general_text`)
Vector-based memory using Qdrant for similarity search:
- **Extract**: LLM extracts structured facts from conversation as `{"key": ..., "value": ..., "tags": [...]}`
- **Store**: Each memory embedded and stored in Qdrant vector DB
- **Search**: Query embedding → cosine similarity search → top-k retrieval
- **Dependencies**: Qdrant + LLM (extractor) + Embedding model

#### TreeTextMemory (`tree_text`) -- **Most Advanced**
Hierarchical graph-structured memory using Neo4j:
- **Three-level hierarchy**: Topics → Concepts → Facts (stored as Neo4j nodes/edges)
- **Dual retrieval**: BM25 keyword search + embedding-based vector search
- **Reranking**: Pluggable rerankers (cosine local, BGE, etc.) with configurable level weights
- **Background reorganization**: Async `MemoryManager` periodically restructures the graph (merges, deduplicates, builds relations)
- **Relation reasoning**: LLM-based detection of conflict/duplicate/complementary relationships between memories
- **Internet search integration**: BochaSearch and XinyuSearch for augmenting memory with web results
- **Dependencies**: Neo4j + Qdrant + LLM + Embedder + optional Reranker

**Memory Item Structure:**
```python
class TextualMemoryItem(BaseModel):
    id: str                          # UUID
    memory: str                      # The actual text content
    metadata: TextualMemoryMetadata  # Rich metadata (see below)

class TreeNodeTextualMemoryMetadata(TextualMemoryMetadata):
    memory_type: Literal[
        "WorkingMemory", "LongTermMemory", "UserMemory",
        "OuterMemory", "ToolSchemaMemory", "ToolTrajectoryMemory",
        "RawFileMemory", "SkillMemory", "PreferenceMemory"
    ]
    sources: list[SourceMessage]     # Provenance tracking
    embedding: list[float]           # Vector embedding
    status: "activated" | "resolving" | "archived" | "deleted"
    version: int                     # Version tracking
    history: list[ArchivedTextualMemory]  # Archived previous versions
    confidence: float                # 0-100 reliability score
    tags: list[str]                  # Categorization labels
    visibility: "private" | "public" | "session"
```

### B. Activation Memory (KV-Cache)

Stores transformer key-value caches as memory, enabling pre-computed context injection:

```python
# src/memos/memories/activation/kv.py
class KVCacheMemory(BaseActMemory):
    def extract(self, text: str) -> KVCacheItem:
        kv_cache = self.llm.build_kv_cache(text)  # Forward pass to build cache
        return KVCacheItem(memory=kv_cache, metadata={...})

    def add(self, memories: list[KVCacheItem]) -> None: ...
    def get_all(self) -> list[KVCacheItem]: ...
```

- Requires HuggingFace backend (local models only, not API-based LLMs)
- Also supports vLLM-based KV cache (`VLLMKVCacheMemory`)
- Used during chat: retrieved KV caches are passed as `past_key_values` to the LLM's `generate()` call
- Stored as pickle files on disk

**Use case**: Pre-encode long documents or user profiles into KV caches, then inject them at inference time to reduce re-computation latency.

### C. Parametric Memory (LoRA)

Placeholder for model weight-level memory via Low-Rank Adaptation:

```python
# src/memos/memories/parametric/lora.py -- PLACEHOLDER
class LoRAMemory(BaseParaMemory):
    # Currently a stub - load/dump produce placeholder files
    # Intended for storing per-user or per-task LoRA adapters as memory
```

The parametric memory concept is described in the paper as encoding knowledge directly into model weights through fine-tuning, but the open-source implementation is not yet functional. This is the most ambitious memory type -- it envisions a "Mem-training Paradigm" where learning and inference are unified through continuous memory-driven parameter updates.

### D. Preference Memory (Additional)

Beyond the three types from the paper, the implementation adds a fourth slot:

```python
class PreferenceTextMemory:  # backend: "pref_text"
    # Stores explicit and implicit user preferences
    # Uses Milvus for vector storage + MinHash for deduplication
    # Extracts preferences from conversation patterns
```

---

## 4. Memory Lifecycle & Scheduling

### MemScheduler

The async memory scheduling system built on Redis Streams:

```
User Message → ScheduleMessageItem → Redis Stream → Task Handlers → Memory Operations
```

Task types processed by the scheduler:
- `ADD_TASK` -- Extract and store memories from new messages
- `QUERY_TASK` -- Track search queries for analytics
- `ANSWER_TASK` -- Track assistant responses
- `MEM_READ_TASK` -- Document/URL ingestion into memory
- `PREF_ADD_TASK` -- Preference extraction

Features:
- **Priority queues** with quota-based scheduling
- **Auto-recovery** for failed tasks
- **Queue isolation** per user/cube
- **Working memory** management with periodic promotion to long-term memory

### Memory Feedback Loop

```python
# src/memos/mem_feedback/feedback.py
class MemFeedback:
    # Natural language feedback → memory correction pipeline:
    # 1. Keyword extraction & replacement
    # 2. Judgment (should this feedback change memory?)
    # 3. Comparison with existing memories
    # 4. Operation execution (update/delete/supplement)
    # Supports both English and Chinese prompts
```

### Memory Reorganization

TreeTextMemory includes a background `MemoryManager` that periodically:
1. Detects conflict/duplicate relations between memory nodes
2. Merges overlapping facts
3. Builds hierarchical topic → concept → fact trees
4. Archives superseded memory versions (full version history preserved)

---

## 5. Agent Integration

### OpenClaw Cloud Plugin

Located at `apps/MemOS-Cloud-OpenClaw-Plugin/`. Two-phase lifecycle:

1. **Before each turn (recall)**: Sends semantic search to MemOS Cloud API → injects relevant memory fragments into agent context
2. **After each turn (capture)**: Extracts key information from conversation → persists as structured memory

Key features:
- Multi-agent memory sharing via `user_id` + `agent_id` isolation
- Conversation ID tracking with configurable prefix/suffix
- Rate limiting with `MIN_CAPTURE_INTERVAL`
- Claims **72% lower token usage** vs loading full chat history

### OpenClaw Local Plugin

Located at `apps/memos-local-openclaw/`. A full on-device memory system:

- **Storage**: SQLite with FTS5 full-text search + in-process vector search
- **Recall engine** (`src/recall/engine.ts`): Hybrid FTS + vector search → RRF fusion → MMR reranking → recency decay
- **Ingest pipeline** (`src/ingest/`): LLM-based summarization with multiple providers (OpenAI, Anthropic, Gemini, Bedrock)
- **Skill memory** (`src/skill/`): Reusable skills that self-evolve -- generator, evaluator, evolver, upgrader
- **Task summarization**: Auto-summarizes completed tasks for future reference
- **Memory Viewer**: Web dashboard for browsing/managing memories
- **Multi-agent**: Memory isolation per agent with skill sharing across agents

### MCP Server

```python
# src/memos/api/mcp_serve.py
# FastMCP server exposing memory operations as MCP tools:
# - memory_add, memory_search, memory_delete, memory_feedback
# - Enables any MCP-compatible client to use MemOS as a memory backend
```

### OpenWork Integration

Located at `apps/openwork-memos-integration/`. An Electron desktop app integrating MemOS with OpenCode (coding agent), providing memory-augmented task execution with a full GUI.

---

## 6. How Memory is Stored, Retrieved, and Managed

### Storage Flow (Add)

```
Messages/Documents
    │
    ▼
MemReader (LLM extraction) ──→ list[TextualMemoryItem]
    │                               │
    │  (async via MemScheduler)     │  (sync)
    ▼                               ▼
GeneralTextMemory:                TreeTextMemory:
  embed → Qdrant                    embed → Neo4j graph nodes
                                    BM25 index update
                                    Relation detection (async)
```

### Retrieval Flow (Search)

```
Query
  │
  ├──→ TreeTextMemory: BM25 + embedding search → rerank → top-k
  ├──→ GeneralTextMemory: embed query → Qdrant similarity → top-k
  ├──→ PreferenceMemory: Milvus search → preference notes
  └──→ ActivationMemory: return KV cache for context injection
  │
  ▼
MOSSearchResult { text_mem, act_mem, para_mem, pref_mem }
  │
  ▼
System prompt injection: "## Memories:\n1. fact1\n2. fact2\n..."
```

### Chat Pipeline

```python
# Simplified from MOSCore.chat():
1. Resolve target user → get accessible cubes
2. For each cube: text_mem.search(query, top_k) → collect memories
3. Build system prompt with memory context
4. If activation memory enabled: load KV cache as past_key_values
5. LLM.generate(messages, past_key_values?) → response
6. Update chat history
7. Submit to MemScheduler for async memory extraction
```

### PRO Mode (CoT Enhancement)

When `PRO_MODE=True`, complex queries are decomposed:
1. LLM decomposes query into sub-questions (JSON: `{is_complex, sub_questions}`)
2. Each sub-question searched against memory in parallel
3. Sub-answers generated with memory context
4. Final synthesis combines all sub-answers into a coherent response

---

## 7. Evaluation & Benchmarks

MemOS includes evaluation scripts for four benchmarks:

| Benchmark | Focus | MemOS Claim |
|-----------|-------|-------------|
| **LoCoMo** | Long-term contextual memory & reasoning | 75.80 accuracy |
| **LongMemEval** | Cross-session reasoning, temporal reasoning, abstention | +40.43% vs baselines |
| **PrefEval** | Preference tracking and personalization | +2568% improvement |
| **PersonaMem** | Persona consistency across conversations | +40.75% improvement |

The evaluation framework (`evaluation/`) includes unofficial implementations of competitor systems (Mem0, Zep, Memobase, SuperMemory, MemU) for fair comparison.

Claims from README: **+43.70% accuracy vs. OpenAI Memory** and **saves 35.24% memory tokens**.

---

## 8. Comparison with Other Memory Systems

| Feature | **MemOS** | **Mem0** | **Letta (MemGPT)** |
|---------|-----------|----------|---------------------|
| **Architecture** | Three-layer OS (Interface/Operation/Infrastructure) | Memory layer (bolt-on) | Agent runtime with memory |
| **Memory Types** | Plaintext + Activation (KV-cache) + Parametric (LoRA) + Preference | Vector facts + Graph relationships | Core (in-context) + Recall (logs) + Archival (vector) |
| **Core Abstraction** | MemCube (multi-memory container) | Memory (fact store) | Agent with Block-based memory |
| **Memory Extraction** | LLM-based via MemReader (multi-modal) | LLM fact extraction + conflict resolution | Agent self-edits via tool calls |
| **Storage** | Neo4j + Qdrant + Milvus + MySQL + Redis | 24+ vector stores + Neo4j/Memgraph | Postgres + vector extensions |
| **Graph Memory** | Core feature (tree hierarchy: topic/concept/fact) | Optional (parallel to vector) | Not native |
| **KV-Cache Memory** | Native support (HuggingFace/vLLM) | No | No |
| **Weight-Level Memory** | LoRA placeholder (not yet functional) | No | No |
| **Async Scheduling** | Redis Streams with priority queues | No (sync pipeline) | Background processing via tasks |
| **Multi-Modal** | Images, documents, URLs, tool traces | Text only | Text + file attachments |
| **Memory Feedback** | Natural language correction loop | Manual update API | Agent self-correction via tools |
| **Multi-User** | Role-based access control, cube-per-user | user_id/agent_id/run_id scoping | Per-agent isolation |
| **Agent Integration** | OpenClaw plugins (cloud + local), MCP server | SDKs, Vercel AI SDK | Native agent runtime |
| **Deployment** | Docker Compose, uvicorn, Cloud API | Managed cloud or self-hosted | Server + Docker |
| **Language** | Python (core) + TypeScript (plugins) | Python | Python |
| **License** | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| **Primary Use Case** | Enterprise memory OS with multi-modal KB | Quick memory layer for existing apps | Stateful agent development |
| **Maturity** | Parametric memory is stub; tree memory most advanced | Production-ready vector+graph | Production-ready agent framework |

---

## 9. Unique Features & Contributions

1. **Unified heterogeneous memory abstraction** -- MemCube bundles plaintext, activation, and parametric memory under one container, enabling holistic memory management rather than treating each type separately.

2. **Tree-structured memory organization** -- Unlike flat vector stores, TreeTextMemory organizes knowledge hierarchically (topic → concept → fact) in Neo4j, enabling multi-granularity retrieval with BM25 + embedding + reranking.

3. **KV-cache as first-class memory** -- The only system to treat transformer KV caches as a manageable memory type that can be extracted, stored, loaded, and injected at inference time.

4. **Memory feedback loop** -- Natural language corrections flow through a judgment → comparison → operation pipeline to refine existing memories, supporting both English and Chinese.

5. **Skill memory and evolution** -- The local OpenClaw plugin introduces self-upgrading skill memory -- tasks generate reusable skills that evolve through evaluation and improvement cycles.

6. **Mem-training paradigm (vision)** -- The paper proposes blurring the line between learning and inference through continuous memory-driven parameter updates, though the LoRA implementation remains a placeholder.

7. **Rich provenance tracking** -- Every memory item records its source (chat, doc, web, file, system), version history, archived versions, confidence scores, and visibility settings.

---

## 10. Key Takeaways

1. **OS-level ambition** -- MemOS is the most architecturally ambitious memory system, treating memory as a full OS concern rather than a simple retrieval layer. The three-layer design mirrors traditional OS architecture.

2. **Implementation maturity varies** -- Plaintext/tree memory is production-quality with sophisticated retrieval and reorganization. KV-cache memory works but only with local HuggingFace models. Parametric memory (LoRA) is a placeholder.

3. **Chinese ecosystem focus** -- Heavy integration with Alibaba Cloud services (Bailian API, OSS, DashScope), Neo4j Community/Enterprise editions, and Chinese-language prompt support throughout.

4. **Benchmark leadership** -- Claims SOTA across LoCoMo, LongMemEval, PrefEval, and PersonaMem, with built-in comparison scripts against Mem0, Zep, and others.

5. **Agent integration via plugins** -- Rather than being an agent framework itself, MemOS integrates with agent platforms (OpenClaw, MCP) as a dedicated memory backend, separating concerns cleanly.

6. **Heavy infrastructure requirements** -- Full deployment requires Neo4j + Qdrant + Redis + MySQL/SQLite + LLM API, making it significantly more complex to self-host than Mem0's single-vector-store approach.

---

## References

- [MemOS GitHub Repository](https://github.com/MemTensor/MemOS)
- [MemOS Paper (Long)](https://arxiv.org/abs/2507.03724) -- "MemOS: A Memory OS for AI System" (Jul 2025)
- [MemOS Paper (Short)](https://arxiv.org/abs/2505.22101) -- "MemOS: An Operating System for Memory-Augmented Generation" (May 2025)
- [Memory3 Paper](https://arxiv.org/abs/2407.01178) -- "Memory3: Language Modeling with Explicit Memory" (2024)
- [MemOS Documentation](https://memos-docs.openmem.net/home/overview/)
- [MemOS Architecture Docs](https://memos-docs.openmem.net/home/architecture/)
- [MemOS Cloud OpenClaw Plugin](https://github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin)
- [Awesome-AI-Memory](https://github.com/IAAR-Shanghai/Awesome-AI-Memory)
- [MemOS OpenClaw Token Savings Analysis](https://medium.com/@tentenco/how-the-memos-plugin-cuts-openclaw-token-costs-by-72-9a6948fe7aef)
- [AI Memory Architecture: MemOS Governance Framework](https://blog.lqhl.me/exploring-ai-memory-architectures-part-2-memos-framework)
- Core implementation: `src/memos/mem_os/core.py` (~600 lines), `src/memos/mem_cube/general.py`
- Memory backends: `src/memos/memories/` (textual, activation, parametric)
- Scheduler: `src/memos/mem_scheduler/general_scheduler.py`
