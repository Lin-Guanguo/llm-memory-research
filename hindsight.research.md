# Hindsight Technical Research Report

Last Updated: 2026-03-24

> **Research Methodology**: This document was generated through source code analysis of the [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) repository and the associated [arXiv paper (2512.12818)](https://arxiv.org/abs/2512.12818), supplemented by web research of benchmarks, blog posts, and community discussions.

## Overview

**Hindsight** is an open-source (MIT) agent memory system by [Vectorize.io](https://vectorize.io) that organizes long-term memory into epistemically distinct networks and provides three core operations: **retain**, **recall**, and **reflect**. It achieves state-of-the-art performance on LongMemEval (91.4%) and LoCoMo (89.61%) benchmarks by combining biomimetic memory organization, multi-strategy retrieval, and disposition-aware reasoning.

The architecture unifies two subsystems described in the paper:
- **Tempr** (Temporal Entity Memory Priming Retrieval) — implements retain and recall
- **Cara** (Coherent Adaptive Reasoning Agents) — implements reflect with configurable disposition traits

**Source:** [GitHub](https://github.com/vectorize-io/hindsight) | [Paper](https://arxiv.org/abs/2512.12818) | [Docs](https://hindsight.vectorize.io)

---

## 1. Core Architecture

### Memory Networks

Hindsight organizes memory into four epistemically distinct fact types, stored as rows in a single `memory_units` PostgreSQL table differentiated by a `fact_type` column:

| Network | `fact_type` | Description | Created By |
|---------|-------------|-------------|------------|
| **World** | `world` | Objective facts about the external environment ("Alice works at Google") | Retain (LLM extraction) |
| **Experience** | `experience` | Agent's own interactions, written in first person ("I helped user debug their API") | Retain (LLM extraction, `fact_type='assistant'` in extraction schema) |
| **Observation** | `observation` | Preference-neutral entity summaries synthesized from underlying facts | Consolidation engine (automatic, post-retain) |
| **Opinion** | `opinion` | Subjective judgments with confidence scores (deprecated in current code) | Originally Cara; now removed via migration |

The paper describes four networks. In the current codebase, the valid recall fact types are `world`, `experience`, and `observation` (`VALID_RECALL_FACT_TYPES` in `response_models.py`). The opinion network has been deprecated and its entries deleted via an Alembic migration.

### Monorepo Structure

```
hindsight/
├── hindsight-api-slim/        # Core FastAPI server + memory engine (Python, uv)
│   └── hindsight_api/
│       ├── engine/            # Core memory engine
│       │   ├── memory_engine.py    # Main orchestrator
│       │   ├── retain/             # Retain pipeline modules
│       │   ├── search/             # Multi-strategy retrieval
│       │   ├── reflect/            # Cara reflect agent
│       │   ├── consolidation/      # Observation synthesis
│       │   └── directives/         # Hard behavioral rules
│       ├── api/http.py             # FastAPI HTTP routers
│       └── api/mcp.py              # MCP server
├── hindsight-control-plane/   # Admin UI (Next.js)
├── hindsight-cli/             # CLI tool (Rust)
├── hindsight-clients/         # Generated SDKs (Python, TypeScript, Rust)
├── hindsight-integrations/    # Framework integrations (LiteLLM, OpenAI, LangGraph, CrewAI, Claude Code, etc.)
└── hindsight-docs/            # Docusaurus documentation site
```

### Database Schema

PostgreSQL with pgvector. Key tables:

| Table | Purpose |
|-------|---------|
| `banks` | Memory banks (isolated per-user/agent "brains") with name, mission, disposition traits |
| `memory_units` | All facts (world, experience, observation) with embeddings, BM25 search vectors, temporal fields |
| `entities` | Canonical entity records (resolved from mentions) |
| `entity_links` | Links between memory units and entities |
| `memory_links` | Graph edges: semantic, temporal, causal, entity links between memory units |
| `documents` | Document tracking for multi-part ingestion |
| `chunks` | Raw text chunks for expand/retrieval |
| `mental_models` | User-defined stored reflect responses (pinned reflections) |

Each memory unit carries: `text`, `context`, `embedding` (vector), `search_vector` (BM25), `event_date`, `occurred_start`, `occurred_end`, `mentioned_at`, `fact_type`, `confidence_score`, `tags`, `metadata`, `document_id`, `chunk_id`.

---

## 2. Tempr: Retain and Recall

### Retain Pipeline

The retain operation (`retain/orchestrator.py`) processes content through a multi-stage pipeline:

```
Input Content
    │
    ▼
[1] Fact Extraction (LLM)
    │  - Extracts structured facts with: what, when, where, who, why
    │  - Classifies each as world or experience (assistant)
    │  - Extracts entities, causal relations, temporal ranges
    │  - Three extraction modes: standard, verbose, verbatim
    │
    ▼
[2] Embedding Generation
    │  - Augments fact text with date context
    │  - Local sentence-transformers or TEI (Text Embeddings Inference)
    │
    ▼
[3] Entity Resolution
    │  - LLM-extracted entities + user-provided entities
    │  - Resolved to canonical entity IDs via fuzzy matching
    │  - Two strategies: "full" (load all bank entities) or "trigram" (pg_trgm GIN index)
    │  - Co-occurrence tracking between entities
    │
    ▼
[4] Database Transaction (single atomic write)
    │  - Store memory units with embeddings + BM25 vectors
    │  - Create entity links
    │  - Create temporal links (time-proximity weighted, 24h window)
    │  - Create semantic links (top-5 nearest neighbors, similarity >= 0.7)
    │  - Create causal links (extracted by LLM during fact extraction)
    │  - Document and chunk tracking
    │
    ▼
[5] Post-Transaction
    │  - Flush entity stats (counts, co-occurrences)
    │  - Trigger consolidation job (background)
```

**Fact Extraction Schema** (from `fact_extraction.py`): Each fact is a Pydantic model with structured fields (`what`, `when`, `where`, `who`, `why`), combined into a single text string: `"what | Involving: who | why"`. The LLM also extracts:
- `occurred_start` / `occurred_end` — ISO timestamps for datable events
- `entities` — named entities (people, places, concepts)
- `causal_relations` — links to previous facts in the batch (index-based, forward-only)
- `fact_type` — `world` or `assistant`

### Recall Pipeline

The recall operation runs four retrieval strategies in parallel, then fuses and reranks results:

```
Query
    │
    ├──► Query Analysis (dateparser: extract temporal constraints)
    ├──► Query Embedding
    │
    ▼
┌─────────────────────────────────────────────────┐
│          4-Way Parallel Retrieval                │
│                                                  │
│  [Semantic]    [BM25]     [Graph]   [Temporal]  │
│  Vector sim    Full-text   Entity/   Time-range  │
│  HNSW index    tsvector    causal    + semantic  │
│                or vchord   traversal  spreading  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
            Reciprocal Rank Fusion (k=60)
                       │
                       ▼
            Cross-Encoder Reranking
            + Recency boost (±10%)
            + Temporal proximity boost (±10%)
                       │
                       ▼
            Token-budgeted output
```

**Retrieval details:**

1. **Semantic** — pgvector HNSW cosine similarity, per-bank per-fact-type partial indexes, over-fetches 5x then trims. Minimum similarity threshold of 0.3.
2. **BM25** — Three backends: native PostgreSQL `tsvector` / `vchord_bm25` / `pg_textsearch`. Keyword matching via tokenized query.
3. **Graph** — Three pluggable strategies:
   - **MPFP** (Meta-Path Forward Push) — default. Sublinear graph traversal combining meta-path patterns from HIN literature with Forward Push local propagation from Approximate PPR. Lazy edge loading, hop-synchronized across all patterns to minimize DB queries to O(hops). Predefined patterns like `[semantic, semantic]` (topic expansion), `[entity, temporal]` (entity timeline), `[semantic, causes]` (reasoning chains).
   - **BFS** — Spreading activation with decay (original algorithm)
   - **Link Expansion** — Direct single-hop expansion through entity, semantic, and causal links
4. **Temporal** — Two-phase: date-ranked filtering within time window, then embedding similarity on the top-50 candidates per fact type. Temporal spreading to adjacent events.

**Fusion:** Reciprocal Rank Fusion merges the four result lists. Then a cross-encoder reranker scores each candidate. Combined scoring applies recency and temporal proximity as multiplicative boosts (±10% each) on top of the cross-encoder score.

### Link Types in the Memory Graph

| Link Type | Created At | Weight Computation |
|-----------|------------|-------------------|
| `semantic` | Retain time | Cosine similarity between embeddings (top-5 neighbors, >= 0.7) |
| `temporal` | Retain time | `max(0.3, 1.0 - time_diff_hours / 24)` — proximity within 24h window |
| `causal` | Retain time | LLM-extracted `caused_by` relations with strength 0.0-1.0 |
| `entity` | Retain time | Co-occurrence through shared resolved entities |

---

## 3. Cara: Reflect

The reflect operation (`reflect/agent.py`) is an agentic loop that reasons over retrieved memories using LLM tool calling. It implements hierarchical retrieval:

### Hierarchical Retrieval Strategy

1. **Mental Models** (`search_mental_models`) — User-curated stored reflect responses (highest quality, manually maintained)
2. **Observations** (`search_observations`) — Auto-consolidated knowledge from memories, with freshness tracking (`is_stale`)
3. **Raw Facts** (`recall`) — World facts and experiences as ground truth

The agent iterates up to `DEFAULT_MAX_ITERATIONS = 10`, calling tools to gather evidence, then produces a final answer grounded in retrieved memories.

### Available Tools

| Tool | Purpose |
|------|---------|
| `search_mental_models` | Search user-curated mental models (pinned reflections) |
| `search_observations` | Search auto-consolidated observations with freshness info |
| `recall` | Search raw facts (world + experience) |
| `expand` | Retrieve full chunk/document context for a memory |
| `done` | Produce final answer with supporting memory IDs |

### Disposition Traits (Cara)

Memory banks can have configurable disposition traits that affect reflect behavior (not recall):

| Trait | Range | Low (1) | High (5) |
|-------|-------|---------|----------|
| **Skepticism** | 1-5 | Trusting — accepts information at face value | Skeptical — questions and doubts information |
| **Literalism** | 1-5 | Flexible — reads between the lines | Literal — interprets information strictly as stated |
| **Empathy** | 1-5 | Detached — ignores emotional context | Empathetic — considers feelings and relationships |

These traits are injected into the reflect system prompt as `Disposition: skepticism=3, literalism=2, empathy=4`. Given the same facts, agents with different dispositions form different conclusions.

### Directives

Separate from dispositions, **directives** are hard rules injected into prompts (e.g., "Always respond in formal English", "Never share personal data"). They are user-defined, prioritized, and enforced with stronger language in the prompt than disposition traits.

---

## 4. Consolidation (Observation Synthesis)

The consolidation engine (`consolidation/consolidator.py`) runs as a background job after retain operations. It processes new, unconsolidated memories and produces observations:

**Pipeline:**
1. Fetch unconsolidated memories from the bank
2. Retrieve existing observations for context
3. LLM decides for each batch: `CREATE` new observation, `UPDATE` existing one, or `DELETE` obsolete one
4. Store observations as `memory_units` with `fact_type='observation'`, tracking `proof_count`, `source_memory_ids`, and `history`

**Consolidation prompt rules:**
- Redundant info (same info worded differently) → UPDATE existing observation
- Contradictions/updates → capture both states with temporal markers ("used to X, now Y")
- Resolve vague references when new facts provide concrete values
- Never merge observations about different people or unrelated topics

**Observations vs. Mental Models:**
- **Observations** — auto-generated bottom-up by the consolidation engine from raw facts. Stored in `memory_units` table with `fact_type='observation'`.
- **Mental Models** — user-defined queries stored in the `mental_models` table. Refreshed on demand via reflect. Can serve as directives.

### Observation Trends

Each observation has a computed `trend` based on evidence timestamps:

| Trend | Meaning |
|-------|---------|
| `STABLE` | Evidence spread across time, continues to present |
| `STRENGTHENING` | More/denser evidence recently |
| `WEAKENING` | Evidence mostly old, sparse recently |
| `NEW` | All evidence within recent window |
| `STALE` | No evidence in recent window |

---

## 5. Benchmark Performance

### LongMemEval Results (as of January 2026)

Hindsight achieved state-of-the-art performance, the first memory system to cross 90%:

| System | Overall | Info Extract | Multi-Session | Temporal | Knowledge Update | Abstention |
|--------|---------|-------------|---------------|----------|-----------------|------------|
| **Hindsight (OSS-120B)** | **91.4%** | — | — | — | — | — |
| **Hindsight (OSS-20B)** | **83.6%** | — | — | — | — | — |
| Full-context GPT-4o | 49.0% | — | 21.1% | 31.6% | 60.3% | — |
| Full-context baseline (20B) | 39.0% | — | — | — | — | — |

Key improvements with Hindsight over full-context baseline:
- Multi-session: 21.1% → 79.7%
- Temporal reasoning: 31.6% → 79.7%
- Knowledge updates: 60.3% → 84.6%
- Overall: +44.6 points over full-context baseline

Results independently reproduced by Virginia Tech Sanghani Center and The Washington Post.

### LoCoMo Results

| System | Overall |
|--------|---------|
| **Hindsight (Gemini-3)** | **89.61%** |
| Hindsight (OSS-120B) | 85.67% |
| Hindsight (OSS-20B) | 83.18% |
| Memobase | 75.78% |

---

## 6. Comparison with Other Memory Systems

| Feature | Hindsight | Mem0 | Letta (MemGPT) | Graphiti (Zep) | Supermemory |
|---------|-----------|------|-----------------|----------------|-------------|
| **Memory Model** | 4 epistemically distinct networks (world, experience, observation + deprecated opinion) | Dual store: vector + optional graph | In-context memory management via MemGPT architecture | Temporal knowledge graph with episodic/semantic edges | Vector store with auto-chunking |
| **Storage** | PostgreSQL + pgvector (single DB) | 24+ vector stores + Neo4j/Memgraph | PostgreSQL + pgvector | Neo4j graph DB | Multiple vector backends |
| **Retrieval** | 4-way parallel (semantic + BM25 + graph + temporal) + RRF + cross-encoder reranking | Vector similarity + graph traversal + optional reranking | LLM-managed retrieval within conversation context | Graph traversal with temporal edges | Vector similarity |
| **Graph Traversal** | MPFP (sublinear, meta-path patterns, lazy loading) or BFS spreading activation | Optional Neo4j entity-relation graph | N/A (LLM decides what to retrieve) | Temporal knowledge graph with entity resolution | N/A |
| **Temporal Reasoning** | First-class: temporal links, temporal retrieval arm, date-range spreading, occurred_start/end per fact | No native temporal support | No native temporal support | Temporal edges in knowledge graph | No native temporal support |
| **Memory Updates** | Consolidation engine: auto-synthesizes observations, handles contradictions with temporal markers | LLM-driven CRUD (ADD/UPDATE/DELETE) per fact | LLM edits memory blocks in-context | Graph edge invalidation with temporal validity | Append-only |
| **Reflect/Reasoning** | Agentic loop with hierarchical retrieval (mental models → observations → raw facts) | Not built-in | LLM reasons over in-context memory | Not built-in (graph query) | Not built-in |
| **Disposition/Personality** | Configurable traits (skepticism, literalism, empathy) per bank | Not supported | Not supported | Not supported | Not supported |
| **Fact Classification** | LLM classifies: world vs. experience + causal relations + entities | Single fact type | Core memory vs. archival memory | Episodic vs. semantic edges | Single type |
| **LongMemEval** | 91.4% | 49.0% (self-reported) | Not published | 71.2% (self-reported) | Not published |
| **License** | MIT | Apache 2.0 | Apache 2.0 | Apache 2.0 | MIT |
| **Deployment** | Single Docker container (embedded PostgreSQL) or external DB | Requires separate vector store + optional graph DB | Server with PostgreSQL | Requires Neo4j + separate services | Self-hosted or cloud |

---

## 7. Key Differentiators

### vs. Mem0
- Hindsight uses four parallel retrieval strategies vs. Mem0's vector similarity + optional graph
- Hindsight has native temporal reasoning (first-class temporal links and retrieval)
- Hindsight auto-consolidates observations; Mem0 uses LLM-driven CRUD on individual facts
- Hindsight's reflect provides agentic reasoning; Mem0 has no built-in reasoning layer
- Single PostgreSQL deployment vs. Mem0's multi-service setup

### vs. Letta (MemGPT)
- Fundamentally different paradigm: Hindsight is an external memory service; Letta manages memory in-context via the LLM itself
- Hindsight's structured graph enables sublinear retrieval; Letta pays full-context LLM cost
- Hindsight provides benchmark-validated accuracy; Letta's approach is more autonomous but harder to evaluate

### vs. Graphiti (Zep)
- Both use graph-based memory, but different graph structures: Hindsight uses a heterogeneous memory graph (semantic/temporal/causal/entity edges); Graphiti uses a temporal knowledge graph
- Hindsight combines graph traversal with three other retrieval strategies (semantic, BM25, temporal) via RRF; Graphiti primarily uses graph traversal
- Hindsight's MPFP algorithm is sublinear in graph size; Graphiti uses full graph queries

### Unique Capabilities
1. **MPFP Algorithm** — Novel sublinear graph traversal combining meta-path patterns with Forward Push propagation. Hop-synchronized execution reduces DB queries to O(hops) regardless of pattern count.
2. **Epistemic Separation** — Structurally distinguishes evidence (world/experience facts) from inference (observations) from instructions (directives).
3. **Disposition-Aware Reasoning** — Same facts, different conclusions based on configurable agent personality traits.
4. **Consolidation with Temporal Markers** — Handles contradictions gracefully ("used to X, now Y") rather than overwriting.
5. **Observation Trends** — Algorithmically computed freshness signals (stable, strengthening, weakening, new, stale) on synthesized knowledge.

---

## 8. Integration Ecosystem

Hindsight provides integrations for:
- **LLM Wrappers**: LiteLLM, OpenAI-compatible (drop-in replacement for API calls)
- **Agent Frameworks**: LangGraph, CrewAI, PydanticAI, Agno, AI SDK (Vercel), Hermes
- **Coding Agents**: Claude Code, OpenClaw, NemoClaw
- **Protocol**: MCP (Model Context Protocol) server built-in

The LLM wrapper approach enables adding memory to existing agents with minimal code changes — swap the LLM client for the Hindsight wrapper, and memories are stored/retrieved automatically on each LLM call.

---

## Sources

- [arXiv Paper: Hindsight is 20/20 (2512.12818)](https://arxiv.org/abs/2512.12818)
- [GitHub Repository](https://github.com/vectorize-io/hindsight)
- [Hindsight Documentation](https://hindsight.vectorize.io)
- [Vectorize Blog: Introducing Hindsight](https://vectorize.io/blog/introducing-hindsight-agent-memory-that-works-like-human-memory)
- [VentureBeat: 91% Accuracy on LongMemEval](https://venturebeat.com/data/with-91-accuracy-open-source-hindsight-agentic-memory-provides-20-20-vision)
- [PR Newswire: Vectorize Breaks 90%](https://www.prnewswire.com/news-releases/vectorize-breaks-90-on-longmemeval-with-open-source-ai-agent-memory-system-302643146.html)
- [Vectorize: Hindsight vs Mem0](https://vectorize.io/articles/hindsight-vs-mem0)
- [Vectorize: Best AI Agent Memory Systems 2026](https://vectorize.io/articles/best-ai-agent-memory-systems)
- [Hindsight Benchmarks Repository](https://github.com/vectorize-io/hindsight-benchmarks)
