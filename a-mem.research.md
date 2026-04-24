# A-MEM: Agentic Memory for LLM Agents — Technical Research Report

Last Updated: 2026-04-15

> **Research Methodology**: This document is based on the arxiv paper [A-MEM: Agentic Memory for LLM Agents (2502.12110v11)](https://arxiv.org/abs/2502.12110) (the NeurIPS 2025 camera-ready, v11 submitted 2025-10-08), the official benchmark repository [WujiangXu/AgenticMemory](https://github.com/WujiangXu/AgenticMemory) (MIT, ~850 stars), and the companion production-oriented repository [WujiangXu/A-mem-sys](https://github.com/agiresearch/A-mem) (also MIT, ~970 stars). I also cross-checked with the skim summary already in `memory.skim-summaries.md` (§4) and aligned comparisons with our existing deep dives on Mem0, Graphiti, and Hindsight. No experiments were re-run; all numbers are reported from the paper.

---

## 1. Overview — the Zettelkasten pitch

Classical LLM agent memory systems (MemGPT, MemoryBank, ReadAgent, LangMem, Mem0) treat each remembered interaction as an isolated record — either a chunk in a vector store or a fact in a flat KV/graph. Retrieval is then a pure nearest-neighbor / LLM-judged operation over a *static* set of records. **A-MEM**, by Xu et al. (Rutgers University / AIOS Foundation, NeurIPS 2025), argues that this is the wrong default: a memory store should behave more like a **Zettelkasten** — Niklas Luhmann's slip-box system in which every note is a self-contained atomic unit, every note is explicitly *linked* to related notes, and the network of links is *rewritten* over time as new notes reveal connections that were not visible when earlier notes were recorded.

A-MEM operationalizes three ideas:

1. **Structured atomic notes.** Each interaction becomes a note with LLM-generated keywords, tags, contextual description, and an embedding — not a raw text blob.
2. **Autonomous bidirectional linking.** When a note is inserted, the system finds embedding-nearest candidates and asks an LLM to decide which ones are *semantically* linked — not just similar.
3. **Memory evolution.** Inserting a new note can *retroactively rewrite* the keywords, tags, and context description of historical notes whose meaning has shifted in light of new evidence. The original content field is preserved, so this is metadata re-interpretation, not content overwrite.

The paper's headline empirical claims: **45.85 F1 on LoCoMo multi-hop** (vs MemGPT's 25.52), and **6.76×–14.1× token reduction** vs MemGPT (the skim called this the "7–13×" range — confirmed from the paper's figures). Cost per memory operation is claimed at **<$0.0003** with GPT-4o-mini; average latency **5.4 s** with GPT-4o-mini, **1.1 s** with a locally-served Llama.

Both v1 (Feb 2025) and v11 (Oct 2025) are online; v11 is the NeurIPS camera-ready and is the version this document summarizes.

---

## 2. Note structure

A memory note `mᵢ` in A-MEM is a seven-tuple:

```
mᵢ = { cᵢ, tᵢ, Kᵢ, Gᵢ, Xᵢ, eᵢ, Lᵢ }
```

| Symbol | Field | Source | Mutable? |
|--------|-------|--------|----------|
| `cᵢ` | Original interaction content (the raw turn or utterance) | Caller | **No** — immutable |
| `tᵢ` | Timestamp | Caller / system | No |
| `Kᵢ` | Keywords (≥3, ordered by importance) | LLM (prompt Ps1) | **Yes** (via evolution) |
| `Gᵢ` | Categorical tags (≥3) | LLM (prompt Ps1) | **Yes** (via evolution) |
| `Xᵢ` | One-sentence contextual description covering topic / argument / audience | LLM (prompt Ps1) | **Yes** (via evolution) |
| `eᵢ` | Dense embedding: `eᵢ = f_enc(concat(cᵢ, Kᵢ, Gᵢ, Xᵢ))` | `all-MiniLM-L6-v2` | Recomputable |
| `Lᵢ` | Set of links to other note IDs | LLM (prompt Ps2) + similarity | **Yes** |

Two design choices here matter:

**(a) The embedding indexes not just `cᵢ` but the concatenation `cᵢ ∥ Kᵢ ∥ Gᵢ ∥ Xᵢ`.** This means the LLM-generated meta-fields ride with the content in the search vector, so retrieval benefits from the LLM's summarization. The trade-off is that **when evolution changes `Kᵢ`/`Gᵢ`/`Xᵢ`, the embedding should be re-computed** — the paper implicitly assumes this but does not emphasize the cost.

**(b) The content `cᵢ` is immutable.** Evolution only rewrites *how* a note is described/indexed, not *what* was said. This is a principled boundary: A-MEM is arguing the facts-on-record should be preserved verbatim but the agent's *interpretation* of those facts should update as more context arrives. This is analogous to how Graphiti uses temporal edge invalidation to preserve historical state, and contrasts with Mem0's UPDATE operation, which rewrites facts directly.

### 2.1 Note creation (prompt `Ps1`)

From the paper's Appendix B, verbatim:

```
Generate a structured analysis of the following content by:
1. Identifying the most salient keywords
2. Extracting core themes and contextual elements
3. Creating relevant categorical tags
Format the response as a JSON object: {keywords: [...], context: [summary], tags: [...]}
```

The LLM is called **once per new interaction** with this prompt. Its JSON output populates `Kᵢ, Gᵢ, Xᵢ`. There is no separate extraction schema per domain — the LLM decides from context what the right keywords/tags are. This keeps the system schema-free, unlike Hindsight's typed extraction (`world` / `experience` / `observation`) or Graphiti's typed entity-relation schema.

---

## 3. Linking mechanism

Link creation is **hybrid: embedding-seeded, LLM-gated**.

**Step 1 — Candidate selection (embedding).** For the incoming note `mₙ`, compute cosine similarity to every existing note and take the top-k nearest neighbors `ℳⁿ_near`. Default `k = 10`; tuned up to `k = 50` for specific model / task combinations.

```
s(n, j) = (eₙ · eⱼ) / (|eₙ| · |eⱼ|)
ℳⁿ_near = top-k by s(n, ·)
```

**Step 2 — Semantic adjudication (LLM, prompt `Ps2`).** The LLM is shown the new note and the candidate neighbors, and asked to judge which of them are truly related:

```
Analyze the new memory note according to keywords and context, with
nearest neighbors. Based on this information, determine: Should this
memory be evolved? Consider its relationships with other memories.
```

Links that pass are added *bidirectionally* into `Lₙ` and each linked `Lⱼ`. The paper does not specify a graded weight on the link (unlike Hindsight, which weights semantic/temporal/causal edges 0.0–1.0) — in the reference code, links are unweighted membership in a set.

This two-stage design is important: embedding cosine similarity alone is a noisy proxy for "same topic, different surface form"; many embedding neighbors are thematically close but not a useful follow-on reference. Gating by an LLM call cuts the link graph down to connections the LLM is willing to endorse as semantically linked, at the cost of one LLM call per insert. This is the same philosophy Mem0 uses for its ADD/UPDATE CRUD decision — use the LLM as the arbiter — but applied to link construction.

Links are used at retrieval time only indirectly (see §5): top-k retrieval returns notes, and a note's `Lᵢ` set gives the agent a hint for related context, but the paper's main retrieval path does not perform graph traversal. This is a meaningful structural difference from Graphiti (graph-walk as primary retrieval) and Hindsight (MPFP / BFS graph traversal is one of four retrieval arms).

---

## 4. Memory evolution — the key novelty

This is the mechanism that distinguishes A-MEM from every other coding-agent memory system we have studied. **When a new note is added, historical notes in its neighborhood can have their keywords, tags, and context description *rewritten*.** The content field is never rewritten; the paper is explicit that evolution is metadata re-interpretation.

### 4.1 Algorithm

```
Add note mₙ:
    1. Construct (cₙ, Kₙ, Gₙ, Xₙ) via Ps1           [single LLM call]
    2. Embed eₙ
    3. ℳⁿ_near ← top-k(s(n, ·))                     [embedding search]
    4. Links Lₙ ← Ps2(mₙ, ℳⁿ_near)                   [single LLM call]
    5. For each mⱼ ∈ ℳⁿ_near:                        [up to k LLM calls]
           mⱼ* ← LLM( mₙ ∥ (ℳⁿ_near \ mⱼ) ∥ mⱼ ∥ Ps3 )
           if evolution decided:
               update Kⱼ, Gⱼ, Xⱼ      (re-embed eⱼ if needed)
    6. Insert mₙ
```

### 4.2 Evolution prompt (`Ps3`, verbatim)

```
Analyze the new memory note. Make decisions about its evolution.
Determine: 1. What specific actions (strengthen, update_neighbor)?
1.1 If strengthen, which memory to connect? Updated tags?
1.2 If update_neighbor, update context and tags of these memories.
```

Two action types:

- **`strengthen`** — create / reinforce a link between the new note and a specific neighbor, optionally updating the new note's tags to align.
- **`update_neighbor`** — rewrite a specific neighbor's `Gⱼ` (tags) and `Xⱼ` (context), carrying forward insight from the new note into the old note's interpretation.

### 4.3 What evolution can and cannot do

| Can | Cannot |
|-----|--------|
| Rewrite `Xⱼ` (context) to reflect new perspective | Rewrite `cⱼ` (original content) |
| Rewrite `Kⱼ` (keywords) | Delete a historical note |
| Rewrite `Gⱼ` (tags) | Merge two notes into one |
| Add a bidirectional link | Resolve contradictions explicitly (no "old state / new state" temporal marker as in Hindsight's consolidation) |

The paper's text uses the words "strengthen, merge, prune" loosely in the body but the Ps3 prompt in Appendix B only materially specifies `strengthen` and `update_neighbor`. The reference code confirms: merge and prune are not implemented as first-class operations — the LLM decides what to do by rewriting fields, not by structural changes.

### 4.4 Ablation — does evolution actually help?

The paper's Table (GPT-4o-mini on LoCoMo, F1) breaks A-MEM into components:

| Configuration | Multi-Hop F1 | Temporal F1 | Single-Hop F1 |
|---|---|---|---|
| w/o Link Generation & w/o Memory Evolution (raw retrieval) | 9.65 | 24.55 | 13.28 |
| + Link Generation only | 21.35 | 31.24 | 39.17 |
| A-MEM full (+ Memory Evolution) | **27.02** | **45.85** | **44.65** |

Evolution adds **+5.67 F1** on multi-hop, **+14.61 F1** on temporal, **+5.48 F1** on single-hop over link generation alone. The temporal gain is the largest — consistent with the intuition that temporal reasoning benefits most from being able to reinterpret old notes after the fact.

### 4.5 Concrete worked example (reconstructed)

Consider a conversation that produces two notes in sequence:

- `m₁` (Monday): "User mentions she just bought a new laptop." Ps1 yields `K = [laptop, purchase, tech]`, `X = "Casual mention of recent hardware purchase."`
- `m₂` (Friday): "User asks for help installing Linux because her Mac is too locked down." Ps1 yields `K = [Linux, install, Mac, lockdown]`, `X = "User wants alternative OS on recent Mac."`

At insert time, `m₂` pulls `m₁` into `ℳⁿ_near`. Ps3 fires. The LLM rewrites `m₁`'s context from `"Casual mention of recent hardware purchase"` to something like `"Initial signal of the user's shift away from vendor-controlled platforms; prelude to Linux migration attempt"`. The *content* of `m₁` — "User mentions she just bought a new laptop" — is preserved. But future queries about "when did the user start moving toward open-source OSes" will now surface `m₁` because its rewritten context carries that theme into the embedding.

This is the mechanism's value proposition: **early signals get reindexed once later notes reveal their significance.**

---

## 5. Retrieval

Retrieval is deliberately simple:

```
Given query q:
    e_q = f_enc(q)
    scores = cos(e_q, eᵢ) for all i
    return top-k by score      (k = 10 default)
```

No BM25 arm, no graph walk, no cross-encoder reranking. The paper argues — and the ablation backs up — that the heavy lifting happens at *write* time (note construction, linking, evolution), so retrieval can remain cheap. This is a distinctive architectural bet. Hindsight spends almost all its engineering on retrieval (four parallel arms + RRF + cross-encoder); A-MEM spends almost all of its on writes.

Links `Lᵢ` on retrieved notes are present but not actively traversed during retrieval in the reference implementation. The LLM downstream answering the user question can choose to attend to link metadata if the notes' context fields flag neighbors — but this is soft, not a graph query.

---

## 6. Empirical results

### 6.1 Benchmarks

Primary benchmark: **LoCoMo** (Long Conversational Memory), 7,512 QA pairs across five categories (single-hop, multi-hop, temporal, open-domain, adversarial). Secondary: DialSim.

### 6.2 Foundation models tested

A-MEM was evaluated on six LLMs — the "six foundation models" flagged in our skim:

1. GPT-4o
2. GPT-4o-mini
3. Qwen2.5-1.5B
4. Qwen2.5-3B
5. Llama-3.2-1B
6. Llama-3.2-3B

Both commercial (OpenAI) and local (Qwen, Llama) backends are exercised — this is load-bearing for the paper's cost/latency claims.

### 6.3 LoCoMo main table (GPT-4o-mini, F1)

| Method | Single-Hop | Multi-Hop | Temporal | Open-Domain | Adversarial |
|--------|-----------|-----------|----------|-------------|-------------|
| LoCoMo baseline | 40.36 | 25.02 | 18.41 | 12.04 | 69.23 |
| ReadAgent | 9.67 | 9.15 | 12.60 | 5.31 | 9.81 |
| MemoryBank | 6.61 | 5.00 | 9.68 | 5.56 | 7.36 |
| MemGPT | 41.04 | 26.65 | 25.52 | 9.15 | 43.29 |
| **A-MEM** | **44.65** | **27.02** | **45.85** | **12.14** | **50.03** |

A-MEM wins four of five categories; on `Adversarial`, LoCoMo's strong baseline (69.23) is the topline — this is a category where most retrieval-style systems underperform. The headline delta is on **Temporal (+20.3 F1 over MemGPT)** — the category where retroactive evolution should help most.

### 6.4 Token efficiency

Reported ranges:

- **A-MEM**: ~1,200–2,500 tokens per operation
- **MemGPT / LoCoMo**: ~16,900 tokens per operation

The ratio spans **6.76× to 14.08×** depending on configuration — rounding to the paper's "7–13×" phrasing. Per-operation cost at GPT-4o-mini rates: **<$0.0003**. Latency: **5.4 s** (GPT-4o-mini) / **1.1 s** (local Llama).

The token advantage is structural: A-MEM retrieves a small set of compact notes whose context descriptions already compress the source interaction, whereas MemGPT pages full working-memory snapshots into the LLM context.

### 6.5 Scaling

Retrieval time grows from **0.31 μs @ 1K notes → 3.70 μs @ 1M notes** — linear in the number of notes (scan of a flat vector list). No ANN index is used in the benchmark code. For production, ChromaDB (used in the `A-mem-sys` companion repo) provides HNSW, which would lower this further.

### 6.6 DialSim

- A-MEM F1: 3.45
- LoCoMo baseline: 2.55 (A-MEM +35%)
- MemGPT: 1.18 (A-MEM +192%)

---

## 7. Comparison with Mem0, Graphiti, Hindsight

Where does Zettelkasten-with-evolution sit on our map?

| Axis | A-MEM | Mem0 | Graphiti | Hindsight |
|------|-------|------|----------|-----------|
| **Atom type** | Free-form note with LLM-generated keywords/tags/context | Flat natural-language fact | Typed entity + bi-temporal edge | Typed fact (world / experience / observation) |
| **Schema** | Schema-free (LLM decides tags per note) | Schema-free | Typed node/edge schema | Typed fact schema with disposition labels |
| **Write-time LLM calls** | 1 (Ps1) + 1 (Ps2) + up to k (Ps3) per insert — potentially ~12 calls per note | 1 (ADD/UPDATE CRUD decision) | 1 (extraction) + 1 (edge invalidation) | 1 (fact extraction) + background consolidation job |
| **Link model** | LLM-adjudicated links over embedding-top-k | Optional Neo4j entity-relation graph | Typed KG edges with `valid_time` + `transaction_time` | Semantic + temporal + causal + entity link graph with MPFP traversal |
| **Retroactive updates** | **Yes — core feature.** Rewrites `K/G/X` of historical notes | UPDATE via LLM CRUD rewrites fact text | Invalidates edges with `invalid_at` timestamp (preserves history) | Consolidation engine rewrites observations; `STABLE/STRENGTHENING/WEAKENING/NEW/STALE` trends |
| **Content immutable?** | Yes — only metadata changes | No — fact text is rewritten | Edges invalidated, not rewritten | Raw facts immutable; observations synthesized above |
| **Contradiction handling** | Implicit via metadata rewrite (no temporal marker) | LLM CRUD overwrites | Bi-temporal: old edge marked invalid, new edge added | Explicit "used to X, now Y" markers in observation |
| **Retrieval** | Single-arm: cosine top-k | Vector + optional graph | Graph query | 4-arm parallel (semantic, BM25, graph, temporal) + RRF + cross-encoder |
| **LoCoMo multi-hop F1 (self-reported)** | 27.02 (GPT-4o-mini) | ~varies; paper reports ~40% on full LoCoMo aggregate | Not primary benchmark | 85.67% OSS-120B overall (not directly comparable — different slicing) |
| **OSS license** | MIT | Apache 2.0 | Apache 2.0 | MIT |
| **Deployment substrate** | ChromaDB (production repo) or in-memory dict (benchmark) | 24+ vector stores + optional Neo4j | Neo4j required | Single Docker with Postgres + pgvector |

**The key architectural question A-MEM answers differently from everyone else**: *When new evidence changes the meaning of an old memory, do you (a) rewrite the old memory's content, (b) add a new memory that supersedes the old one, (c) invalidate the old memory with a timestamp, or (d) rewrite the old memory's *description* while keeping content intact?*

- Mem0 picks (a) — content rewrite.
- Hindsight picks (b/c hybrid) — observations get rewritten with temporal markers; facts are append-only.
- Graphiti picks (c) — bi-temporal edge invalidation.
- **A-MEM picks (d) — metadata re-interpretation.**

(d) is the most conservative about preserving original evidence and the most aggressive about letting retrieval surface it under new framings. The ablation shows this is worth +14.6 F1 on temporal reasoning.

---

## 8. Implementation

Two public repositories, both MIT-licensed, both from the same author Wujiang Xu:

| Repo | Purpose | Stars (Apr 2026) |
|------|---------|------------------|
| [`WujiangXu/AgenticMemory`](https://github.com/WujiangXu/AgenticMemory) | **Benchmark reproduction.** Reproduces LoCoMo/DialSim numbers from the paper. Not production-ready. | ~850 |
| [`agiresearch/A-mem` (aka `A-mem-sys`)](https://github.com/agiresearch/A-mem) | **Production-oriented reference.** ChromaDB-backed, OpenAI + Ollama backends, clean API. | ~970 |

### 8.1 Dependencies (production repo)

- Python ≥3.9
- `chromadb` — vector store (HNSW)
- `sentence-transformers` — embeddings (`all-MiniLM-L6-v2`, 384-dim)
- `openai` or `ollama` — LLM backend
- No Postgres, no Neo4j, no external services

### 8.2 Core API

```python
from agentic_memory.memory_system import AgenticMemorySystem

m = AgenticMemorySystem(llm_backend="openai", llm_model="gpt-4o-mini")
note_id = m.add_note("User prefers pytest over unittest")   # triggers Ps1+Ps2+Ps3
hits = m.search_agentic("testing preferences", k=5)          # cosine top-k
m.update(note_id, ...)
m.delete(note_id)
```

The `add_note` call is **synchronous and blocking** — it performs the full note-construction + link + evolution pipeline inline. There is no background evolution worker. This matters for production: a chatty conversation with heavy evolution (k=10 neighbors × Ps3 call each) can run ~11 LLM calls per turn in the worst case.

### 8.3 What's missing for production

- **No conflict resolution / rollback.** If Ps3 rewrites a neighbor's context badly, there is no audit trail or reversal path — the old `Xⱼ` is overwritten.
- **No async / batched evolution.** All k neighbor evolution calls serialized per insert.
- **No multi-tenant isolation.** Single in-memory / single-Chroma-collection model.
- **No embedding recomputation strategy documented.** When `Kⱼ/Gⱼ/Xⱼ` are rewritten, the cached `eⱼ` becomes stale; the production repo does recompute on update, but this adds an embedding pass per evolved neighbor.
- **No benchmarks at >1M notes on a real ANN index.**

---

## 9. Limitations and failure modes

The paper's explicit limitations section is brief. Extrapolating from our own deep-dive perspective:

1. **Evolution quality is bounded by the underlying LLM.** Small models (Qwen2.5-1.5B, Llama-3.2-1B) still win vs baselines but narrow the gap — context rewrites are only as nuanced as the rewriting model.
2. **No explicit contradiction handling.** If `m₁` says "user likes coffee" and `m₂` says "user hates coffee," Ps3 might rewrite `X₁` to "user's previous stance on coffee" or might silently overwrite — the prompt does not instruct the LLM how to mark temporal shifts. Hindsight's consolidation prompt explicitly requires "used to X, now Y" markers; A-MEM does not.
3. **Hallucinated links.** Ps2 can assert links between only-tangentially-related notes; there is no per-link confidence score and no downstream filter. Over a long conversation, the link graph can get noisy.
4. **Drift risk.** Each evolution rewrites metadata from the current LLM's perspective. After many rewrites, a historical note's `Xⱼ` can drift arbitrarily far from its content `cⱼ` — think of it as iterated LLM summarization, with no ground-truth anchor.
5. **Write-amplification cost.** Worst case, one user turn → 1 (Ps1) + 1 (Ps2) + 10 (Ps3) = 12 LLM calls. Even at GPT-4o-mini prices this dominates the inference cost of the conversation itself. Production deployments would want to cap `k` or move Ps3 to an async worker.
6. **No deletion / pruning.** The system grows monotonically. Zettelkasten has no forgetting curve (MemoryBank does); A-MEM inherits this gap.
7. **Retrieval recall is single-modal.** Because retrieval is cosine-only, queries whose surface form doesn't match any note's embedding neighborhood will miss — no BM25 fallback, no keyword search.
8. **Content immutability cuts both ways.** If the original `cⱼ` contains a factual error, A-MEM has no UPDATE path for the content — only the description. Mem0 handles this cleanly; A-MEM does not.

The paper's discussion says "different LLMs might generate slightly different contextual descriptions" — a mild framing of what is, in practice, the system's biggest operational risk.

---

## 10. Takeaways — when does Zettelkasten-with-evolution win?

A-MEM is the right architectural bet when:

- **Temporal / multi-hop reasoning matters more than simple fact recall.** The ablation shows the evolution mechanism is worth +14.6 F1 on temporal; this is where it dominates MemGPT (+20.3). If your agent mostly answers "what did the user tell me last week," Mem0's flat CRUD is probably sufficient.
- **You can afford write-time LLM calls.** A-MEM shifts cost to write time; retrieval is nearly free. If your conversation is read-heavy (user asks many questions about a fixed corpus), that trade favors A-MEM. If it is write-heavy with few reads, it hurts.
- **You want to preserve original evidence verbatim.** A-MEM's content-immutable design is the cleanest of any system we've reviewed for auditability — `cᵢ` is a faithful log; only the interpretation layer moves. For compliance / reconstruction / forensics use cases this is valuable.
- **You do not need bi-temporal / typed semantics.** If you need to answer "what did Alice believe about X on day T vs day T+7," Graphiti's bi-temporal KG is a better fit. A-MEM has no explicit temporal validity on edges.

A-MEM is the **wrong** bet when:

- You need production-grade deployment today — no multi-tenancy, no async evolution, no conflict resolution.
- You need explicit contradiction markers (Hindsight's consolidation is stronger here).
- You need typed entities for joins / queries (Mem0's optional graph or Graphiti).
- Your conversation produces many notes per turn and budget is tight — write amplification will bite.

### Where A-MEM's ideas should propagate

Even if you don't adopt A-MEM wholesale, two ideas from the paper deserve to leak into other systems:

1. **Metadata re-interpretation as a first-class operation.** Most memory systems either rewrite content or freeze it. A-MEM shows there is a middle path: freeze content, mutate description. This could plausibly be added as an *additional* write-time operation to Hindsight's consolidation engine or Mem0's CRUD loop.
2. **Link adjudication by LLM over embedding top-k.** Cheap and effective. Two LLM calls (link + evolve) per insert can be worth +18 F1 on multi-hop tasks vs pure-vector retrieval.

These two ideas are the real contribution. The Zettelkasten framing is a pedagogical wrapper; the mechanism is "LLM as a dynamic re-indexer of its own memory."

---

## Sources

- [arXiv: A-MEM (2502.12110v11)](https://arxiv.org/abs/2502.12110) (accessed: 2026-04-15) — NeurIPS 2025
- [HTML render](https://arxiv.org/html/2502.12110v11) (accessed: 2026-04-15)
- [GitHub: WujiangXu/AgenticMemory (benchmark)](https://github.com/WujiangXu/AgenticMemory) (accessed: 2026-04-15)
- [GitHub: agiresearch/A-mem (production ref)](https://github.com/agiresearch/A-mem) (accessed: 2026-04-15)
- Local PDF: `/Users/linguanguo/dev/llm-memory-research/papers/pdfs/2502.12110.pdf`
- Cross-reference: `memory.skim-summaries.md` §4 (initial skim that triggered this deep dive)
- Comparison anchors: `hindsight.research.md`, `mem0.research.md`, `graphiti.research.md`
