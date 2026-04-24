# LiCoMemory Technical Research Report

Last Updated: 2026-04-15

> **Research Methodology**: This document was generated through close reading of the [arXiv paper 2511.01448](https://arxiv.org/abs/2511.01448) (v2, January 2026) and inspection of the associated public repository at [github.com/EverM0re/LiCoMemory](https://github.com/EverM0re/LiCoMemory). Cross-referencing was done with two sibling research notes in this repository: [graphiti.research.md](./graphiti.research.md) (a heavy bi-temporal KG) and [mastra.research.md](./mastra.research.md) (a pure-compression working-memory system), to position LiCoMemory in the contemporary design space for LLM agent memory.

## Overview

**LiCoMemory** (Lightweight and Cognitive Agentic Memory) is a memory framework proposed by Zhengjun Huang, Zhoujin Tian, Qintian Guo, Fangyuan Zhang, Yingli Zhou, Di Jiang, Zeying Xie, and Xiaofang Zhou (arXiv 2511.01448, v1 Nov 2025, v2 Jan 2026). Its central artifact is **CogniGraph** — a three-layer hierarchical graph (session summaries → entity-relation triples → raw dialogue chunks) whose declared purpose is to serve as a *semantic index* rather than a knowledge repository.

The pitch is explicitly comparative. LiCoMemory's authors argue that existing graph-based memory systems (Zep/Graphiti, Mem0g, MemOS) "intertwine semantic content with relational topology, leading to heavy, redundant, and inflexible graph representations," and that existing non-graph systems (Mem0, MemoryBank, A-Mem) flatten retrieval and lose the temporal / multi-session structure that long-term dialogue requires. CogniGraph's solution is to strip nodes and edges down to "essential identifiers without verbose descriptions" and use graph topology as a *scaffold* that points back to original dialogue chunks when the actual content is needed.

Headline claims from the abstract:
- Up to **23% improvement in accuracy** over the second-best baseline on long-term dialogue benchmarks.
- Construction latency of **21 seconds** on LoCoMo vs. Mem0's 1,772 s and Zep's 2,871 s — "more than an order of magnitude" reduction.
- Construction token consumption of **13.52k** vs. Mem0's 49.3k and Zep's 212.5k — "over 3× reduction."
- Query latency around **1.5–1.6 s**, competitive with or slightly better than Mem0 and Zep.

Source code is MIT-like open (license not explicitly declared in the repo at time of analysis), Python-only, and research-grade (41 GitHub stars, 2 forks as of April 2026). The implementation relies on Llama-3.1-8B-Instruct for construction, BGE-M3 for embeddings, and downstream Llama-3.1-70B-Instruct-Turbo or GPT-4o-mini as the generating model.

---

## 1. CogniGraph Architecture — Entities and Relations as Semantic Index

CogniGraph is the single conceptual contribution of the paper. It has three layers stacked vertically, each pointing "downward" to the next via identifier-based hyperlinks.

### Session Layer (top)

Each node represents one dialogue session and stores:
- A **textual summary** distilled by an LLM capturing high-level context.
- A set of **distilled keywords** (`keys`) representing the central entities, topics, and temporal markers of that session.
- A **timestamp** anchoring the session in calendar time.

This layer is the routing layer. Queries are first matched against session summaries via embedding similarity before any graph traversal takes place. In effect, the session layer prunes the search space before triple-level retrieval begins.

### Entity-Relation Layer (middle)

A lightweight knowledge graph composed of (entity, relation, entity) triples extracted from dialogue. The paper emphasizes:

> "Each entity node and relation edge retains only essential identifiers without verbose descriptions."

No descriptive embeddings are stored in the nodes. No attribute bags, no wiki-style summaries on entity pages. A node is effectively a canonical name plus a type tag plus a list of back-pointers to the triples that mention it. A relation edge is a type label plus timestamp plus pointer to the sentence it was extracted from.

Contrast this with Graphiti, where each entity node carries a `summary` string (LLM-generated) that is re-embedded and participates directly in hybrid search. In Graphiti the node *is* a search target; in CogniGraph the node is an *address* that, when hit, directs the retriever to the actual dialogue chunk.

### Chunk Layer (bottom)

Original dialogue turns / chunks. Every triple in the middle layer carries a hyperlink to the exact chunk it was extracted from, enabling bidirectional traceability:

- Forward (chunk → triple): populated at extraction time.
- Backward (triple → chunk): used at retrieval time to surface evidence alongside the answer.

### How This Differs from a Traditional KG

A traditional KG is a *content store*: it is expected to answer queries purely from its node/edge attributes. CogniGraph explicitly refuses this role. The graph is a lookup table whose sole purpose is to translate an unstructured query into a small, structured set of addresses in the raw dialogue. The content you actually feed the generator is pulled from the chunk layer, not the graph.

This is closer to how RAG over a document store works (where the vector index is clearly not the content) than to how Graphiti, ZepKG, Mem0g, or AgenticMemory-style KGs are typically used (where the graph nodes themselves carry answer content).

---

## 2. Temporal + Hierarchy-Aware Search

The retrieval algorithm exploits both the hierarchy and the temporal metadata. It has three signals that are fused into a single relevance score.

### Stage 1 — Query Preparation

Extract the query's entity mentions with an LLM/NER step, embed the raw query with BGE-M3, and capture the query timestamp (used as anchor for temporal decay).

### Stage 2 — Session-Level Filtering

Compute cosine similarity between the query embedding and each session summary's embedding. Extract session-level relevance `S_s`. Only sessions above a ranking cutoff advance; this bounds the number of triples that need to be scored in the next stage.

### Stage 3 — Triple-Level Scoring

Inside the shortlisted sessions, score every triple by semantic similarity `S_t` against the query. The paper combines `S_s` and `S_t` into a harmonic-mean style joint score:

```
S_sem = 2 · S_s · S_t / (S_s + S_t)
```

This gives credit only to triples whose *session* is relevant AND whose *content* is relevant — a multiplicative AND rather than a noisy OR. It is the operational expression of what the paper calls "hierarchy-aware" retrieval: the session layer is not just a pre-filter, it continues to contribute to the final score.

### Stage 4 — Temporal Modulation (Weibull Decay)

Time is not a filter, it is a modulator. The decay function is a Weibull kernel:

```
w(Δτ) = exp[ −(Δτ / τ̂)^t_k ]
```

where:
- `Δτ` is the gap between query time and triple timestamp.
- `τ̂` is the **median** time-gap across the retrieved triples — a per-query adaptive scale rather than a fixed constant. This is the paper's way of letting the decay shape adapt to whether the relevant memories are concentrated in the last day or spread over months.
- `t_k = 0.1` is the Weibull shape parameter used in experiments, producing a heavy-tailed decay that is gentle on old items but still distinguishes recent from ancient.

### Stage 5 — Final Relevance and Top-k

```
R(t) = S_sem · w(Δτ)
```

Top-15 triples by `R(t)` are selected. The paper is explicit that "time dimension modulates rather than dominates the semantic signal" — temporal decay reshapes the ranking but never overrides a strong semantic match.

### Hierarchy Traversal on Output

After triple selection, the system walks *back up and down* the hierarchy:
- **Up**: retrieve the session summary for context framing.
- **Down**: retrieve the raw dialogue chunks linked to each winning triple.

The final prompt assembled for the generator therefore contains: (a) session summaries for the winning sessions, (b) the top-k triples as structured knowledge, and (c) the original chunks as evidence. This is the "coherent and fine-grained" retrieval the paper advertises.

---

## 3. Reranking and Hyperlinks to Dialogue Evidence

### Reranking

Strictly speaking, LiCoMemory does *not* use a cross-encoder reranker in the Hindsight / Cohere Rerank sense. Its "reranking" *is* the unified scoring formula `R(t) = S_sem · w(Δτ)`. The candidates from session-level shortlisting are re-scored with the joint hierarchy+temporal function, and that re-scored ranking is the final order. No second-stage neural reranker is trained or invoked.

This is worth flagging because it means the quality of retrieval is entirely governed by:
- The quality of BGE-M3 similarity (fixed, off-the-shelf).
- The Weibull decay hyperparameters (`t_k = 0.1`, adaptive `τ̂`).
- The hierarchy harmonic-mean fusion.

There is no learned calibration, no LLM-as-judge reranker, no listwise or pairwise rerank step.

### Hyperlinks to Dialogue Evidence

The "hyperlink" terminology in the paper is literal for the data model but abstract for the implementation. Every triple carries a unique identifier of the chunk it came from. During update (dialogue ingestion):

1. A new turn is chunked.
2. An LLM extracts triples (entity, relation, entity) from the chunk.
3. Each extracted triple is stored with `source_chunk_id` set.
4. If a triple duplicates an existing one (detected by type-aware semantic similarity matching), the existing triple's `source_chunk_ids` list is *appended*, not replaced — producing a multi-evidence edge.

At retrieval time, the generator receives both the triple and the chunks in its `source_chunk_ids`. This is the paper's answer to hallucination and overcompression: the triple tells the LLM what to look for; the chunk tells it what was actually said.

Implementation in the repo appears to treat this as plain object IDs and Python dict joins — there is no graph DB, no neo4j, no LiteLiteral hyperlink format. "Hyperlink" is doing rhetorical work; the mechanism is a foreign-key-style reference.

---

## 4. Empirical Results

### 4.1 Main Benchmarks

LiCoMemory is evaluated on **LoCoMo** (Long Conversation Memory, ~500-turn synthetic dialogues) and **LongMemEval** (realistic long-session QA with temporal, multi-session, and knowledge-update subsets). Two generator models: Llama-3.1-70B-Instruct-Turbo and GPT-4o-mini.

**LongMemEval, Llama-3.1-70B:**

| System | Accuracy | Recall |
|--------|---------|--------|
| **LiCoMemory** | **69.20%** | **72.39%** |
| Zep (2nd) | 60.20% | 62.74% |
| Improvement | +9.00 pp | +9.65 pp |

**LoCoMo, Llama-3.1-70B:**

| System | Accuracy | Recall |
|--------|---------|--------|
| **LiCoMemory** | **62.99%** | **64.51%** |
| Mem0g (2nd) | 55.48% | 59.32% |
| Improvement | +7.51 pp | +5.19 pp |

**GPT-4o-mini:**

| Benchmark | LiCoMemory | 2nd best (Mem0g) | Gap |
|-----------|-----------|------------------|-----|
| LongMemEval | 73.80% / 76.63% | 64.80% / 69.53% | +9.0 / +7.1 pp |
| LoCoMo | 67.20% / 68.09% | 56.96% / 63.14% | +10.24 / +4.95 pp |

### 4.2 Where Does the "23% improvement" Come From?

The headline "up to 23%" is *not* the overall accuracy improvement. Overall improvements are in the 7–10 point range. The 23% figure is reported in the paper's abstract as the *maximum single improvement across subsets*, and breaking down Figure 4 it corresponds to relative gains on the hardest subsets:

- **LongMemEval Multi-Session subset**: +26.6% relative over Mem0.
- **LoCoMo Temporal-Reasoning subset**: +19.2% relative over MemOS.
- **LongMemEval Temporal-Reasoning subset**: +15.9% relative.

Averaging or selecting these gives the "~23%" figure advertised. This is consistent with the architectural bets: hierarchy helps multi-session routing, Weibull decay helps temporal reasoning, and those are exactly the subsets where LiCoMemory pulls ahead.

### 4.3 Update Latency and Scale

**LoCoMo construction (Table 2):**

| System | Construction tokens | Construction latency |
|--------|--------------------|-----------------------|
| Zep | 212.5k | 2,871 s |
| Mem0 | 49.3k | 1,772 s |
| **LiCoMemory** | **13.52k** | **21 s** |

Zep's construction-latency disadvantage is the bi-temporal edge invalidation work described in the Graphiti research note — every new fact triggers contradiction checks and edge-invalidations via LLM calls. LiCoMemory avoids this entirely: new triples append, duplicates merge by similarity, no LLM-driven re-evaluation of historical edges.

**Query time** (average): LiCoMemory 1.52 s (LoCoMo) / 1.62 s (LongMemEval) vs. Mem0 1.78 s and Zep 5.22 s. Token consumption at query: 1.3k vs. Mem0's 2.2k.

### 4.4 Ablation Highlights

From Figure 5 (ablation study):
- Remove **structured retrieval** (graph triples): 73.8 → 51.6, a 22-point drop. This is the largest ablation effect and validates that the graph structure matters beyond pure chunk retrieval.
- Remove **temporal awareness** (no Weibull decay): 71.4 → 48.9 on the temporal-reasoning subset. Temporal decay is load-bearing exactly where you would expect.
- Remove **summary guidance** (skip session layer): 73.8 → 61.4 overall, 64.7 → 42.9 on multi-session. The session layer is the biggest contributor to multi-session coherence.

### 4.5 Baseline Coverage Caveat

LiCoMemory compares against seven baselines: **MemoryBank, MemOS, Mem0, Mem0g, A-Mem, Zep, and LoCoMo's own baseline**. It does **not** compare against Graphiti-standalone, Hindsight, HippoRAG-2, or LangMem. Given that Hindsight reports 91.4% on LongMemEval with a 120B model (vs. LiCoMemory's 69.2% with a 70B model), the "second-best" framing should be read as "second-best among the seven baselines chosen by the authors," not "second-best in the field."

---

## 5. Comparison with Graphiti and Mastra

LiCoMemory sits at an interesting midpoint on a spectrum from "heavy KG" to "pure compression":

| Axis | Graphiti (heavy KG) | LiCoMemory (light graph) | Mastra (pure compression) |
|------|---------------------|---------------------------|---------------------------|
| **Primary structure** | Bi-temporal KG on Neo4j/FalkorDB | 3-layer hierarchical graph (custom Python) | Flat working-memory notes + optional semantic recall |
| **What nodes store** | Name + LLM summary + attributes + embeddings | Canonical ID + type + pointer to chunks | N/A (no graph) |
| **Temporal model** | Bi-temporal (valid_at, invalid_at) per edge, with LLM-driven invalidation | Per-triple timestamp + adaptive Weibull decay | Timestamped notes, no formal temporal model |
| **Edge invalidation** | LLM judges contradictions, invalidates edges | No invalidation; duplicates merge, old triples naturally decayed | Compression rewrite overwrites |
| **Update cost** | Heavy (≈3k s / LoCoMo dataset) | Very light (≈21 s / LoCoMo dataset) | Very light (append + periodic compression) |
| **Content source for LLM** | Node summaries + edge facts (graph IS the content) | Raw dialogue chunks linked from triples (graph is an index) | Compressed text blob (graph-free) |
| **Storage backend** | Neo4j / FalkorDB / Kuzu | In-process Python dicts, custom graph | Postgres / SQLite / vector DB |
| **Retrieval** | Hybrid: cosine + BM25 + graph traversal + cross-encoder rerank | Hierarchy-pruned + semantic + Weibull-decay fusion | Vector search over notes (+ "working memory" always in prompt) |
| **Benchmark positioning** | Zep numbers: ~71% LongMemEval | 69.2% LongMemEval (Llama-70B) | Not formally benchmarked on LongMemEval/LoCoMo |

**Graphiti** pays heavy ingest cost for an always-consistent KG that can answer queries about *what was true when*. LiCoMemory deliberately rejects this trade; its graph can contain contradictions, because the generator always resolves them by reading the linked chunks.

**Mastra** rejects graphs entirely and does compression of long history into a curated working-memory Markdown blob, with optional semantic recall over notes. LiCoMemory is halfway here: it has compressed summaries (session layer + keywords), but they are *addresses* that lead back to uncompressed chunks, not replacements for the chunks.

The cleanest one-line positioning: **Graphiti stores content in the graph; Mastra stores content in a compressed blob; LiCoMemory stores content in the chunks and uses the graph as the table-of-contents.**

---

## 6. "Semantic Index" vs Knowledge Graph — Real Distinction or Rhetorical Reframe?

This is the paper's sharpest branding claim, and it deserves scrutiny.

**Arguments that "semantic index ≠ KG" is a real distinction:**

1. **Schema commitment differs.** CogniGraph nodes carry only canonical identifier and type; they are deliberately not loaded with LLM-written summaries or attribute bags. A traditional KG (including Graphiti) embeds substantive content into the node/edge itself. In LiCoMemory, if you want the actual facts, you have to dereference a chunk pointer.
2. **Consistency contract differs.** A KG typically promises some degree of consistency (no contradictions, bi-temporal truth tracking in Graphiti's case). CogniGraph makes no such promise — duplicate triples accumulate evidence pointers, contradictions coexist, and it is the generator's job to reconcile them from the linked chunks at query time. This is exactly how a *document index* behaves, not how a KG behaves.
3. **Failure mode differs.** If a KG node's summary is wrong, queries over that node return wrong answers directly. If a CogniGraph node's identifier is wrong, the worst case is you miss a chunk — the chunk itself is still verbatim.
4. **Update cost reflects it.** LiCoMemory's 21-second LoCoMo construction is only possible because it skips the LLM-driven edge-invalidation / summary-regeneration steps that make Graphiti take ~3,000 s. That cost asymmetry is real and structural, not cosmetic.

**Arguments that it's partly rhetorical:**

1. The data model is *still* (entity, relation, entity) triples. You can call that a semantic index, but every major KG ingestion system produces the same shape.
2. "Lightweight KG with chunk pointers" is not a novel object — RAG systems have paired entity indexes with chunk pointers since at least HippoRAG and GraphRAG (2024). What's novel in LiCoMemory is the explicit three-layer design with session-level routing, not the "graph-as-index" concept per se.
3. The term "semantic index" is doing double duty: sometimes meaning "the graph topology indexes content chunks" (clear), sometimes meaning "the graph is just a better embedding index" (blurry). The paper is not crisp on which.

**Verdict: it is a real but narrow distinction.** The substantive claim — that you can strip node/edge content down to identifiers and recover the content from linked chunks at query time — is a defensible architectural choice with measurable latency consequences. The claim that this makes CogniGraph categorically "not a KG" is rhetorical polish; it is more accurate to call CogniGraph a *minimalist, inconsistency-tolerant KG used as an index over chunks*. That is still a useful design point, and the numbers back up that it translates to real update-latency and quality gains over the Zep/Mem0g style.

---

## 7. Implementation

**Repository**: [github.com/EverM0re/LiCoMemory](https://github.com/EverM0re/LiCoMemory)

**Language**: Python (100%). Configuration via `config/Memory.yaml`.

**Module layout** (from repo inspection):

```
LiCoMemory/
├── base/           # base classes / interfaces
├── chunking/       # dialogue chunking
├── config/         # yaml configs incl. Memory.yaml
├── coregraph/      # CogniGraph data structures and construction
├── dataset/, data/ # benchmark data loaders (LoCoMo, LongMemEval)
├── evaluation/     # benchmark evaluation harness
├── prompt/         # prompt templates for extraction + QA
├── query/          # retrieval / ranking pipeline
├── utils/
└── main.py
```

**Dependencies**: declared in `requirements.txt`. The paper specifies the following model/library stack:
- **Embeddings**: BGE-M3 (HuggingFace).
- **Construction LLM**: Llama-3.1-8B-Instruct (local or API).
- **Generation LLM**: Llama-3.1-70B-Instruct-Turbo (Together.ai-style) or GPT-4o-mini (OpenAI).
- **Hardware for reported experiments**: NVIDIA A100 80GB GPUs.

**Storage backend**: custom in-process Python data structures. No Neo4j, no Postgres, no pgvector. The graph is held in memory during operation and persisted to disk as serialized Python objects. This is consistent with the "lightweight" positioning but also means the system is not built for multi-tenant or concurrent production workloads.

**Hyperparameters** used in the paper:
- `k = 15` retrieved triples.
- `t_k = 0.1` Weibull shape.
- `τ̂` = median of Δτ across the retrieved set (adaptive, no tuning).

**Maturity signal**: 41 GitHub stars, 2 forks as of April 2026; no tagged releases; MIT-style repo but license file presence is not confirmed. This is a research codebase, not a deployable memory service.

---

## 8. Limitations

The paper identifies two in its own limitations section, and I'll add several that follow from close reading:

**Paper-declared:**
1. **Single-modality.** Text-only dialogue. No images, audio, or sensor data ingestion.
2. **LLM dependency at construction.** Every session summary, keyword list, and triple extraction requires LLM calls. Even at 13.5k tokens per LoCoMo dataset, this scales linearly with dialogue volume and incurs monetary cost at deployment.

**Derived from close reading:**
3. **No cross-encoder reranker.** The "rerank" step is just the unified scoring formula. Systems that add a learned cross-encoder (Hindsight, mem0 with BGE reranker) can extract more precision from the same candidate pool.
4. **Narrow baseline set.** The comparison omits Graphiti-standalone, Hindsight, HippoRAG-2, LangMem, and Letta. "Second-best" is scoped to the seven systems the authors selected. Hindsight's reported 91.4% on LongMemEval suggests LiCoMemory's 69.2% is not state of the art overall, even if it is Pareto-optimal on the latency dimension.
5. **No multi-tenant / concurrency story.** In-process Python dicts as storage means the current implementation cannot back a multi-user agent service without a significant re-architecture.
6. **No entity disambiguation beyond similarity matching.** The paper's deduplication is "type-aware and semantic similarity." Real-world coreference (two "Alice"s, one person changing jobs) is not addressed.
7. **The 23% headline is a best-subset number, not overall.** Anyone reading the abstract should know overall gains are 7–10 points, with the 23% coming from temporal-reasoning and multi-session subsets specifically.
8. **Weibull `τ̂` adapts per query, but there's no sensitivity analysis.** Whether performance degrades on queries where the retrieved Δτ distribution is pathological (e.g., only very recent or only very old) is not studied.

---

## 9. Takeaways

1. **The graph-as-index framing is the real contribution.** Strip node/edge content to identifiers, push content into a chunk layer, dereference at query time. This is what enables the 100× construction-latency gap vs. Zep.
2. **Hierarchy pays off on multi-session benchmarks.** The session layer is not decorative — ablation shows it drives +22 points on the LongMemEval multi-session subset. For agents that talk to the same user across weeks, this is the mechanism that matters.
3. **Weibull adaptive decay is a neat idea.** Using the median of retrieved Δτ as the scale parameter is a principled way to make temporal decay work on both short-term and long-term queries without per-query tuning. Other systems (Graphiti, Hindsight) use fixed time windows.
4. **"Second-best" is a framing.** LiCoMemory beats its chosen seven baselines decisively but does not set overall state of the art on LongMemEval — Hindsight's 91.4% (120B) and 83.6% (20B) are both higher than LiCoMemory's 69.2% (70B). What LiCoMemory wins unambiguously is the latency / cost frontier.
5. **Good positioning against Graphiti.** Graphiti's bi-temporal consistency is genuinely expensive; LiCoMemory's "no invalidation, just decay + chunk evidence" is a clean alternative for teams that don't need truth-time reasoning.
6. **Good positioning against Mastra.** Mastra's working-memory compression loses evidence. LiCoMemory keeps the chunks accessible via graph-to-chunk pointers, giving a middle path between compression and full retention.
7. **Not production-ready yet.** In-process Python graph, no storage backend, no concurrency story, no released version. This is a paper + research codebase; it is not yet a library you drop into an agent service.
8. **"Semantic index ≠ KG" is partly real, partly rhetorical.** Real: identifier-only nodes, no consistency contract, chunk-dereferenced content, very fast updates. Rhetorical: the data model is still entity-relation triples, which is what every KG has. Call it a minimalist KG used as a content-addressable index and the claim becomes precise.

---

## Sources

- [arXiv 2511.01448 — LiCoMemory (v2, Jan 2026)](https://arxiv.org/abs/2511.01448) (accessed: 2026-04-15)
- [arXiv HTML view](https://arxiv.org/html/2511.01448) (accessed: 2026-04-15)
- [GitHub: EverM0re/LiCoMemory](https://github.com/EverM0re/LiCoMemory) (accessed: 2026-04-15)
- Sibling research notes in this repo: [graphiti.research.md](./graphiti.research.md), [mastra.research.md](./mastra.research.md), [hindsight.research.md](./hindsight.research.md)
- LongMemEval benchmark: [arXiv 2410.10813](https://arxiv.org/abs/2410.10813)
- LoCoMo benchmark: [arXiv 2402.17753](https://arxiv.org/abs/2402.17753)
