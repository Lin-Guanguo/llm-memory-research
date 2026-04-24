# Academic Memory & Retrieval Layer Research Plan

Last Updated: 2026-04-15

## Goal

Extend existing research (product/engineering-side) with two underexplored directions:
1. **Academic memory architectures** — papers and research prototypes not covered by the product-focused Q1 survey
2. **Retrieval layer (Embedding) deep dive** — text chunking/segmentation and retrieval architecture, going below the "vector DB" product layer

## Scope

### In scope

- **Academic memory papers**: cognitive-inspired architectures (episodic/hippocampal), agentic memory, benchmark methodology
- **Retrieval internals**: chunking strategies, late interaction (ColBERT), Matryoshka embeddings, rerankers, hybrid retrieval

### Out of scope (explicitly)

- Context research beyond coding agents — the current 7-agent coding survey (`context.summary.md`) is considered sufficient
- Non-memory / non-retrieval directions outside the A-line framework
- Product-layer memory tools not already covered (Zep, LangMem, Cognee, etc.) — academic contrast is the priority

## Direction 1: Academic Memory Research

### Recency policy

**Prioritize by year, deep-dive only recent work:**

1. **2026 papers — highest priority.** Deep-dive study, per-paper `*.research.md`.
2. **2025 papers — second priority.** Deep-dive if still load-bearing in 2026 citations.
3. **Pre-2025 papers — reference only.** Read abstracts and cite as background; do NOT spend time on full deep-dives. Use them to understand lineage (e.g., "MemoryBank 2023 introduced Ebbinghaus decay, used by X 2026").

Rationale: the field moves fast enough that 2023-2024 architectures are mostly superseded or absorbed into newer work. Time is better spent on the current frontier than on archaeological reconstruction.

### Papers to study

**Tier 1 — 2026 (deep dive)**:
- To be identified during Phase 1 literature scan. Start from 2026 citations in Hindsight, Supermemory ASMR, MemOS, and current LongMemEval/LoCoMo leaderboard entries.

**Tier 2 — 2025 (deep dive if still relevant)**:

| Paper / System | Year | Why notable |
|---|---|---|
| **HippoRAG 2** | 2025 | Improvements to triple extraction and retrieval over HippoRAG v1 |
| (others TBD) | 2025 | Identify during literature scan |

**Tier 3 — Pre-2025 (reference only, no deep dive)**:

| Paper / System | Year | Use as reference for |
|---|---|---|
| A-Mem (Agentic Memory) | 2024 | Zettelkasten-style self-organizing memory lineage |
| HippoRAG v1 | 2024 NeurIPS | Hippocampus metaphor + personalized PageRank origin |
| EM-LLM (Episodic Memory) | 2024 | Boundary-detection episode formation origin |
| Self-RAG / Corrective RAG | 2024 | Retrieval reflection loop origin |
| MemoryBank | 2023 | Ebbinghaus-curve forgetting origin |
| Generative Agents (Stanford Park) | 2023 | Importance+recency+relevance triple-score + reflection tree origin |
| MemGPT paper | 2023 | OS-paging metaphor (the paper behind Letta) |

### Benchmark methodology study

| Benchmark | Purpose |
|---|---|
| **LongMemEval** | Multi-session dialog memory; already have scores, need methodology |
| **LoCoMo** | Long conversational memory |
| **MemoryBench** (Supermemory) | Unified harness — deferred in Plan 3, revisit here |
| **RULER / NIAH** | Long-context retrieval (orthogonal but often compared) |

**Output**: one research.md per paper + `memory.academic.summary.md` synthesizing paper-vs-product patterns.

### Key questions

- Which academic ideas have migrated into products (and which haven't)?
- Hippocampus/episodic metaphors: useful architectural prior, or post-hoc framing?
- How do academic systems handle forgetting/decay vs product systems (most products: none)?
- Is the "reflection" step (Generative Agents, Hindsight) doing real work, or is it extraction-under-another-name?

## Direction 2: Retrieval Layer (Embedding) Research

### Why this direction

Existing research covers vector DBs at the **product layer** (Qdrant, Chroma) but skips the actual retrieval stack: how text is split, embedded, matched, and reranked. This is the layer that determines retrieval quality independent of which DB you pick.

### Topics

**2a. Text chunking & segmentation**

| Topic | Notes |
|---|---|
| Fixed-size chunking (baseline) | Token/char-count splits, overlap windows |
| Recursive / semantic chunking | LangChain RecursiveCharacterSplitter, semantic chunking via embedding distance |
| Late chunking (Jina) | Embed first, chunk after — preserves long-range context |
| Agentic chunking | LLM-driven segmentation (Propositionizer, etc.) |
| Structure-aware chunking | Markdown/code/PDF-aware splits |
| Parent-child / hierarchical | Small chunks for retrieval, large for context (multi-vector) |

**2b. Embedding model architecture**

| Topic | Notes |
|---|---|
| **Dense bi-encoder** baseline (SBERT, BGE, E5) | Standard sentence-pair similarity |
| **ColBERT / late interaction** | Per-token vectors + MaxSim; higher quality, higher cost |
| **Matryoshka embeddings** | Truncatable dimensions; cost/quality tradeoff at query time |
| **Sparse / learned sparse** (SPLADE) | Interpretable, BM25-compatible |
| **Multi-vector vs single-vector** | When each pays off |

**2c. Retrieval architecture**

| Topic | Notes |
|---|---|
| Hybrid retrieval (BM25 + vector) | RRF, weighted fusion |
| Query rewriting / expansion | HyDE, multi-query, decomposition |
| Rerankers | Cross-encoders (Cohere Rerank, Jina Reranker, BGE-reranker) |
| Contextual embeddings (Anthropic) | Doc context prepended before embedding |
| Metadata filtering | Pre-filter vs post-filter tradeoffs |

**2d. Production RAG stacks to survey**

- **LlamaIndex** chunking + retrieval patterns
- **LangChain** retrievers catalog
- **Haystack** / **Vespa** — pipeline-oriented stacks
- **Anthropic Contextual Retrieval** (official cookbook)

### Output

- `retrieval/chunking.research.md` — chunking strategies comparison
- `retrieval/embedding-models.research.md` — bi-encoder vs ColBERT vs Matryoshka vs sparse
- `retrieval/retrieval-architecture.research.md` — hybrid, reranker, query rewriting
- `retrieval.summary.md` — cross-cutting findings, tradeoffs, "what to pick when"

### Key questions

- Chunking: does "semantic chunking" actually beat fixed-size + overlap in practice, or is the hype overstated?
- ColBERT: when does late interaction earn its 10-100x cost?
- Reranker: is a 2-stage (retrieve + rerank) pipeline always worth it?
- How do Dayfold-style "LIKE-only" systems compare to vector on this user's scale (≤1000 projects/user)? — tie back to user's own impl

## Direction 3: (Not in this plan) Context & Learning

- **Context**: current 7-agent coding survey is sufficient per user decision
- **Learning**: tracked separately in `plan/2-learning-research.md`

## Phasing

**Phase 1** — Academic memory literature scan (direction 1):
- Identify 2026 memory papers (forward-citation search from Hindsight, Supermemory ASMR, MemOS; arxiv 2026 cs.CL filter; leaderboard paper trails)
- Triage into Tier 1 (2026, deep dive) / Tier 2 (2025, deep dive if relevant) / Tier 3 (pre-2025, reference only)
- Deep-dive Tier 1 first, then Tier 2

**Phase 2** — Benchmark methodology deep dive:
LongMemEval, LoCoMo, MemoryBench harness

**Phase 3** — Retrieval chunking & embedding models (direction 2a, 2b)

**Phase 4** — Retrieval architecture & production stacks (direction 2c, 2d)

**Phase 5** — Cross-cutting synthesis:
- `memory.academic.summary.md` (academic × product comparison)
- `retrieval.summary.md`
- Update `findings.md` with new cross-domain patterns
- Revisit Dayfold design: which academic ideas / retrieval techniques would measurably help

## Deliverables

- 5-8 new `*.research.md` files (one per major paper/topic)
- 2 new summary files (`memory.academic.summary.md`, `retrieval.summary.md`)
- Updated `findings.md`, `summary.md` / `summary.chinese.md`
- Update root `README.md` index

## References

To be gathered per-paper during Phase 1. Starting points:
- [A-Mem arxiv](https://arxiv.org/abs/2502.12110)
- [HippoRAG arxiv](https://arxiv.org/abs/2405.14831)
- [EM-LLM arxiv](https://arxiv.org/abs/2407.09450)
- [Generative Agents arxiv](https://arxiv.org/abs/2304.03442)
- [MemGPT arxiv](https://arxiv.org/abs/2310.08560)
- [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [Jina Late Chunking](https://jina.ai/news/late-chunking-in-long-context-embedding-models/)
- [ColBERT v2 arxiv](https://arxiv.org/abs/2112.01488)
- [Matryoshka Embeddings](https://arxiv.org/abs/2205.13147)
