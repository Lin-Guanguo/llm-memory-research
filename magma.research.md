# MAGMA Technical Research Report

Last Updated: 2026-04-15

> **Research Methodology**: This document was produced by close reading of the MAGMA paper on arXiv ([abs/2601.03236](https://arxiv.org/abs/2601.03236), [HTML v1](https://arxiv.org/html/2601.03236v1)), cross-referenced against the companion research documents on Graphiti (`graphiti.research.md`, Zep's single temporal KG) and Hindsight (`hindsight.research.md`, four-network structured memory) in this repository. No MAGMA source code is publicly released at the time of writing, so every implementation-level detail here comes from the paper's equations, pseudo-code, and ablation tables.

## Overview

**MAGMA (Multi-Graph based Agentic Memory Architecture for AI Agents)** is a 2026 proposal by Jiang, Li, Li, and Li that reframes long-horizon agent memory as a multi-view graph problem rather than a single store. The thesis is simple and sharp: relying on semantic similarity — whether as a flat vector index or even as a single knowledge graph with mixed edge types — collapses distinct relational dimensions (what an event is *about*, *when* it happened, *why* it happened, *who* it involves) into one scalar score, which is why existing systems stumble on multi-hop, temporal, and causal queries.

MAGMA proposes to **decouple memory representation from retrieval logic** by materialising four orthogonal graphs over the same set of event nodes — **semantic, temporal, causal, entity** — and then letting a query-conditioned traversal *policy* pick which graph(s) to walk at each step. On LoCoMo the paper reports a 0.700 LLM-judge score (18.6–45.5% relative margin over A-MEM, MemoryOS, Nemori) and on LongMemEval a 61.2% average while compressing context from 101K tokens down to 0.7–4.2K per query.

The positioning relative to the other two systems in this repo is precise:
- **Graphiti (Zep, 2024)** — a *single* temporally-aware knowledge graph with bi-temporal edges.
- **Hindsight (Vectorize, 2025)** — a *single* memory graph whose rows are partitioned into four *epistemic* fact-types (world/experience/observation/opinion) and retrieved via four parallel strategies fused with RRF.
- **MAGMA (2026)** — *four separate* graphs partitioned by *relation type*, co-indexed over shared event nodes, and traversed adaptively via a rule-based intent-weighted policy.

MAGMA is therefore the first of the three to make the graph structure itself multi-view (not the node taxonomy, not the retrieval arms, but the edge topology).

**Source:** [arXiv abstract](https://arxiv.org/abs/2601.03236) | [HTML v1](https://arxiv.org/html/2601.03236v1) | [PDF](https://arxiv.org/pdf/2601.03236)

---

## 1. Architecture: Four Orthogonal Graphs

### Event Nodes (Shared Substrate)

All four graphs are built over the same node set 𝒩. Each event node is the 4-tuple

**n_i = ⟨c_i, τ_i, v_i, 𝒜_i⟩**

where `c_i` is raw event content (a conversation turn or a segmented episode), `τ_i` is a discrete timestamp, `v_i` is the dense embedding (indexed in an ANN vector DB), and `𝒜_i` is structured metadata (extracted entities, topic label, temporal cues, semantic facts). A single JSON-schema-enforced extraction prompt populates `𝒜_i` at ingest time, which the paper identifies as the critical defence against downstream hallucination — if the node's metadata is wrong, every subsequent edge inference is poisoned.

### The Four Edge Sets

| Graph | Symbol | Edge Semantics | Directionality | How Constructed |
|---|---|---|---|---|
| **Temporal** | ℰ_temp | Strict chronological ordering: edge (n_i, n_j) iff τ_i < τ_j in the same session | Directed, immutable | Mechanical; ground-truth chain from timestamps |
| **Causal** | ℰ_causal | Cause → effect: edge if S(n_j \| n_i, q) > δ under an LLM entailment check | Directed | LLM-inferred asynchronously over local 2-hop neighbourhoods |
| **Semantic** | ℰ_sem | Meaning/topic relatedness: edge if cos(v_i, v_j) > θ_sim (θ_sim ≈ 0.10–0.30) | Undirected | Cosine-similarity thresholding on embeddings |
| **Entity** | ℰ_ent | Event ↔ abstract entity-node (person, object, concept) | Bipartite | Extracted entity mentions promoted to shared nodes; solves "object permanence" across disjoint time windows |

The key architectural bet is that these four relations are *structurally different enough* to warrant separate edge sets. Semantic similarity is symmetric and dense; temporal ordering is anti-symmetric and sparse; causality is directed and sparse; entity co-occurrence is bipartite. Folding all four into a single graph (as Graphiti and Hindsight effectively do) forces the retriever to disambiguate them post-hoc; keeping them separate lets the policy exploit the structural signal directly.

### Dual-Path Update Pipeline

Updates split into a **fast path** and a **slow path**:

**Fast path (synaptic ingestion)** — on the hot write path:
1. Event segmentation from raw dialogue.
2. Embedding + vector-DB insert.
3. Temporal-backbone edge append (τ_i-1 → τ_i).
4. Enqueue the event for consolidation.

No LLM call is on the critical path. Writes are non-blocking.

**Slow path (structural consolidation)** — background worker:
1. Dequeue recent event n_t.
2. Fetch the local 2-hop neighbourhood 𝒩(n_t) and recent history ℋ_history.
3. One LLM call emits new causal and entity edges: **ℰ_new = Φ_reason(𝒩(n_t), ℋ_history)**.
4. Merge edges; deduplicate.

This is MAGMA's answer to the cost question that Graphiti's synchronous LLM-on-ingest architecture runs into: the expensive reasoning is amortised off the write path.

---

## 2. Policy-Guided Traversal

Retrieval is a four-stage pipeline. Stages 1, 2, 4 are conventional; stage 3 is where MAGMA's novelty lives.

### Stage 1 — Query Decomposition

Single LLM call produces:
- **Intent class** T_q ∈ {Why, When, Entity}. The paper commits to a small, hard-coded intent taxonomy.
- **Temporal window** [τ_s, τ_e] resolved from relative expressions ("last month", "before the trip").
- **Dense+sparse representation** — embedding q⃗ and keyword set q_key.

### Stage 2 — Anchor Identification

Find seed nodes via three-modality Reciprocal Rank Fusion over vector, keyword, and temporal filters:

**S_anchor(n) = ∑_{m ∈ {vec,key,time}} 1 / (k + r_m(n))**

Top-K anchors become the traversal frontier.

### Stage 3 — Adaptive Traversal (the policy)

This is explicitly **not a learned policy** — no RL, no gradient updates. It is a *parameterised rule* with intent-keyed weights. For a candidate transition n_i → n_j via edge type r (one of {sem, temp, causal, ent}):

**S(n_j \| n_i, q) = exp( λ₁ · φ(r, T_q) + λ₂ · sim(n⃗_j, q⃗) )**

where:
- **φ(r, T_q) = w_{T_q}^⊤ · 1_r** — dot product of an intent-specific weight vector with a one-hot edge-type indicator.
- **λ₁ = 1.0** (structural weight), **λ₂ ∈ [0.3, 0.7]** (semantic weight).

The intent-weight matrix (empirically tuned, not learned):

| Intent \ Edge type | w_causal | w_temporal | w_entity | w_semantic |
|---|---|---|---|---|
| **Why**    | 3.0–5.0 | low | low | low |
| **When**   | low | 0.5–4.0 | low | low |
| **Entity** | low | low | 2.5–6.0 | low |

Given these weights, a "Why did the user cancel the subscription?" query biases traversal toward causal edges; "When did we first discuss the refund?" biases toward temporal backbone; "What has Alice been working on?" biases toward entity links.

**Heuristic beam search** operationalises the policy: at each hop, expand the top-k scoring neighbours, up to max depth 5 and a total node budget of 200. This is the explicit cap on retrieval cost.

### Stage 4 — Graph Linearisation

The retrieved subgraph is serialised back into text for the reader LLM:
1. **Topological sort** by the dominant intent axis — temporal sort for "When" queries, causal-order DAG sort for "Why" queries.
2. **Provenance scaffolding** — each node rendered as `<t:τ_i> content <ref:id>`, letting the reader cite.
3. **Token budgeting** — high-salience nodes (high S score) stay verbatim; low-salience nodes are LLM-summarised or dropped to fit the budget.

### Is there any learning component?

No gradient-based learning. The "policy" is a fixed function with hand-tuned intent weights; the only adaptation is via the intent classifier in stage 1. This is worth emphasising because the word "policy" has RL connotations that the paper does not cash in. On the other hand, it means there is no training data requirement, no reward shaping, and no deployment-time staleness — which is a pragmatic win.

---

## 3. Empirical Results

### LoCoMo (LLM-as-a-Judge with gpt-4o-mini)

| Method | Multi-Hop | Temporal | Open-Domain | Single-Hop | Adversarial | **Overall** |
|---|---|---|---|---|---|---|
| Full Context       | 0.468 | 0.562 | 0.486 | 0.630 | 0.205 | 0.481 |
| A-MEM              | 0.495 | 0.474 | 0.385 | 0.653 | 0.616 | 0.580 |
| MemoryOS           | 0.552 | 0.422 | 0.504 | 0.674 | 0.428 | 0.553 |
| Nemori             | 0.569 | 0.649 | 0.485 | 0.764 | 0.325 | 0.590 |
| **MAGMA**          | **0.528** | **0.650** | **0.517** | **0.776** | **0.742** | **0.700** |

The headline is 0.700 overall — an 18.6–45.5% relative improvement over the baselines and, notably, a large lead on the adversarial slice (0.742 vs. 0.616 for the next best). Temporal and single-hop are the other strong slices; multi-hop is competitive but not strictly the best (Nemori's 0.569 edges MAGMA's 0.528).

### LongMemEval

| Question type | Full context (101K tok) | Nemori (3.7–4.8K tok) | **MAGMA (0.7–4.2K tok)** |
|---|---|---|---|
| Single-session-preference | 6.7% | 62.7% | **73.3%** |
| Single-session-assistant  | 89.3% | 73.2% | 83.9% |
| Temporal-reasoning        | 42.1% | 43.0% | **45.1%** |
| Multi-session             | 38.3% | 51.4% | 50.4% |
| Knowledge-update          | 78.2% | 52.6% | 66.7% |
| Single-session-user       | 78.6% | 77.7% | 72.9% |
| **Average**               | **55.0%** | **56.2%** | **61.2%** |

MAGMA's LongMemEval average of 61.2% sits well below Hindsight's public 91.4% with OSS-120B, but MAGMA publishes token cost (≤4.2K vs. Hindsight's undisclosed). On the *preference* slice MAGMA's +10.6 points over Nemori is striking — the paper attributes this to the entity graph collapsing "scattered preference mentions across sessions" into a single retrievable entity.

### Ablations (LoCoMo)

| Configuration | Judge | F1 | BLEU-1 |
|---|---|---|---|
| w/o Adaptive Policy    | 0.637 | 0.413 | 0.357 |
| w/o Causal Links       | 0.644 | 0.439 | 0.354 |
| w/o Temporal Backbone  | 0.647 | 0.438 | 0.349 |
| w/o Entity Links       | 0.666 | 0.451 | 0.363 |
| **MAGMA (Full)**       | **0.700** | **0.467** | **0.378** |

The adaptive policy contributes the single largest delta (−0.063), which is the quantitative justification for the "policy-guided" framing. Causal and temporal each contribute ~0.053; entity a smaller but still consistent 0.034. No single graph is dispensable; the system's performance is genuinely the superposition of all four views.

### System Efficiency

| Method | Build (h) | Tokens/query (k) | Latency (s) |
|---|---|---|---|
| Full Context | – | 8.53 | 1.74 |
| A-MEM        | 1.01 | 2.62 | 2.26 |
| MemoryOS     | 0.91 | 4.76 | 32.68 |
| Nemori       | 0.29 | 3.46 | 2.59 |
| **MAGMA**    | **0.39** | **3.37** | **1.47** |

MAGMA is the lowest-latency method at 1.47 s/query (including the slow path being asynchronous helps), and uses 3.37K tokens per query — roughly parity with Nemori, 29% less than MemoryOS. The 0.39h build time is within 40% of the fastest baseline.

---

## 4. Comparison with Graphiti and Hindsight

### Capability matrix

| Dimension | Graphiti (Zep) | Hindsight | MAGMA |
|---|---|---|---|
| **Graph partition axis** | None — single KG | Fact type (world/experience/observation) | Relation type (sem/temp/causal/entity) |
| **Number of graphs** | 1 | 1 (partitioned rows in `memory_units`) | 4 (co-indexed edge sets) |
| **Temporal model** | Bi-temporal (valid_time + transaction_time) on every edge, with invalidation | Per-fact `occurred_start/end`, `mentioned_at`, `event_date`; temporal links within 24h window | Temporal graph is a first-class immutable backbone; discrete τ per node |
| **Causal edges** | Not explicit | LLM-extracted `caused_by` at retain time, batch-index-scoped (forward-only) | First-class causal graph, inferred asynchronously over 2-hop neighbourhoods |
| **Entity handling** | EntityNodes resolved from mentions; EpisodicEdge MENTIONS | Canonical entity table + fuzzy-match resolution; entity links via co-occurrence | Abstract entity nodes linked bipartitely to events; explicit object-permanence design goal |
| **Semantic edges** | Via EntityEdge RELATES_TO + embedding similarity at query time | Top-5 cosine neighbours (≥0.7) computed at retain | Cosine-thresholded edge set, θ ≈ 0.10–0.30 |
| **Ingest cost model** | LLM on the write path (synchronous extraction) | LLM on the write path (fact extraction + causal extraction) + async consolidation for observations | Fast path: no LLM. Slow path: async LLM for causal/entity only |
| **Retrieval model** | Hybrid graph traversal + vector + BM25 via Neo4j Cypher / FalkorDB | 4-way parallel (semantic + BM25 + graph + temporal) → RRF → cross-encoder rerank | RRF anchor → intent-weighted rule-based traversal over 4 edge sets → beam search |
| **Adaptive per-query routing** | No — same retrieval pipeline for every query | No — all four retrieval arms always run; RRF fuses unconditionally | **Yes** — intent classifier selects edge-type weights |
| **Learning component** | None | None | None (rule-based policy) |
| **Epistemic distinction** | No | Yes (world vs. experience vs. observation vs. opinion) | No — all events are structurally equivalent |
| **Disposition / personality** | No | Yes (Cara traits) | No |
| **Published LongMemEval** | 71.2% (self-reported, Zep) | 91.4% (OSS-120B) | 61.2% |
| **Published LoCoMo** | Not public | 89.61% (Gemini-3) | 70.0% (judge) |
| **Open source** | Yes (Apache 2.0) | Yes (MIT) | No code released at time of writing |

### Where MAGMA is genuinely different

1. **Partition by relation, not by epistemology.** Hindsight splits memory by *what the fact is about the world* (objective/subjective/synthesised). MAGMA splits by *how one memory relates to another* (meaning/time/cause/identity). These are *orthogonal axes* — a future system could in principle combine both (four fact types × four edge types).

2. **Per-query edge-type weighting.** Graphiti treats every query with the same traversal logic. Hindsight always runs all four retrieval arms and fuses them with RRF regardless of query. MAGMA is the only one of the three that *changes its traversal behaviour based on query intent*. The ablation (−0.063 without the policy) quantifies the value.

3. **Async causal inference.** Graphiti's LLM extraction is on the write path. Hindsight does causal extraction inside the retain LLM call (also write path) but defers observation synthesis to background consolidation. MAGMA pushes both causal and entity inference fully off the write path, which is the lowest-latency ingest of the three.

4. **Compressed context at query time.** MAGMA explicitly reports 0.7–4.2K tokens per query on LongMemEval. Hindsight has token budgeting but doesn't publish the same metric; Graphiti reports graph-query latency but not token cost per answer.

### Where MAGMA is weaker

1. **Raw benchmark number.** Hindsight's 91.4% on LongMemEval and 89.61% on LoCoMo dwarf MAGMA's 61.2% / 70.0%. Some of this gap is model-side (Hindsight's best numbers use OSS-120B or Gemini-3; MAGMA's LoCoMo numbers are judged by gpt-4o-mini and it's unclear which reader LLM it uses), but the headline-number gap is large enough that the *representational* wins don't translate to SOTA accuracy yet.

2. **No epistemic model.** MAGMA makes no distinction between objective world facts, the agent's own experiences, and the agent's opinions. This is a principled choice — its unit is the event — but in a coding-assistant deployment, "the test failed" (experience) and "Python 3.12 released in October 2023" (world fact) are used very differently, and MAGMA can't route on that distinction.

3. **No consolidation / abstraction layer.** Hindsight's observation network synthesises *new* knowledge from raw facts and tracks trends (strengthening/weakening/stale). Graphiti's CommunityNode clusters related entities. MAGMA has no equivalent — the node set is always raw events, and the graphs are built over them. For long-horizon memory where abstraction matters, this is a gap.

4. **Hand-tuned intent weights.** The policy's intent weight matrix is empirically set. The three-way taxonomy (Why/When/Entity) is also hand-picked and doesn't obviously cover e.g. "preference" or "counterfactual" queries. A learned policy is the obvious extension but nothing in the paper moves that way.

5. **No public code.** Both Graphiti and Hindsight ship production-ready implementations. MAGMA is, at present, a paper with equations and numbers — reproducibility is an open question.

---

## 5. Implementation Concerns

### Extraction cost

Per event, the ingest pipeline spends:
- 1 structured-extraction LLM call (for 𝒜_i) — on the write path but small prompt.
- 1 consolidation LLM call over a 2-hop neighbourhood — asynchronous but grows with graph density.

If we optimistically assume ~500 tokens in + 200 out for extraction and ~2000 tokens in + 300 out for consolidation (2-hop neighbourhood is non-trivial), a 1000-event session costs roughly 2M LLM tokens ingested, 500K generated. This is comparable to Hindsight's retain pipeline (fact extraction + entity resolution + causal extraction) but shifted more to the background. It is *more* expensive than Graphiti on a per-edge basis because MAGMA does two LLM passes (extraction + consolidation) vs. Graphiti's one.

### Graph update latency

Fast path is O(1) amortised (vector DB insert + one temporal edge append). Slow path latency is a worker-queue SLO, not a user-facing number, but the 2-hop neighbourhood fetch is the bottleneck — if causal edges proliferate, the neighbourhood size grows and consolidation slows. The paper doesn't publish worst-case numbers here.

### Storage overhead

Each event participates in up to four edge sets. Semantic edges are O(K) per node (top-K neighbours, bounded). Temporal edges are O(1) per node (chain). Causal edges are LLM-inferred and typically sparse. Entity edges depend on entity density but are bipartite, so O(#entities mentioned). The paper admits "higher implementation and memory overhead" vs. flat vector systems. A back-of-envelope: if K=10 for semantic and average entity-per-event is 3, each event adds ~15 edges — roughly 3× the edge count of a pure semantic index.

The bigger storage concern is the *vector DB + graph DB* pairing. Graphiti uses Neo4j/FalkorDB + embedding fields. Hindsight is single-store (PostgreSQL with pgvector + `memory_links` table). MAGMA's paper is implementation-agnostic but the natural deployment is vector DB + graph DB, which is two services.

### Where a production implementation would struggle

- **Causal edge correctness.** LLM causal inference is noisy. Graphiti has the same problem. Hindsight constrains it to forward-only within a batch. MAGMA's 2-hop-neighbourhood scope is broader, which means more candidates for hallucinated causal edges. The paper's `δ` threshold is the only guard.
- **Intent classifier reliability.** A "Why" intent misclassified as "When" routes the entire beam search down the wrong edge weights. Robustness data would be welcome but is not reported.
- **Eviction.** Like Graphiti and Hindsight, MAGMA is append-oriented. Nothing in the paper addresses forgetting, compaction, or graph pruning at scale.

---

## 6. Stated Limitations

The paper itself lists three:

1. **LLM reasoning dependency.** Consolidation quality tracks the backbone LLM; extraction errors and hallucinated causal edges are explicitly called out as vulnerabilities.

2. **Storage and implementation overhead.** Multi-graph substrate + dual-stream processing is heavier than flat vector systems. Not suitable for ultra-resource-constrained deployments.

3. **Narrow evaluation scope.** Evaluation covers conversational/agentic benchmarks only (LoCoMo, LongMemEval). Multimodal and heterogeneous-observation agents would need adaptation.

To these I would add:

4. **Fixed intent taxonomy.** Why/When/Entity misses preference, counterfactual, procedural, and planning queries.
5. **No learned policy.** The policy is a hand-tuned rule, not a learned function — it won't adapt to new workloads.
6. **No abstraction layer.** No counterpart to Hindsight's observations or Graphiti's communities.
7. **Benchmark gap to Hindsight.** Head-to-head on LongMemEval, MAGMA is 30 points behind.

---

## 7. Takeaways: When Would You Pick Multi-Graph?

The honest answer: **pick multi-graph when your query mix is genuinely heterogeneous and your ingest budget is constrained**.

Concretely, prefer MAGMA-style multi-graph when:
- Queries split cleanly across temporal ("when did…"), causal ("why did…"), and entity ("what about X") axes, and you can afford an intent classifier upstream.
- You need low write-path latency — the async consolidation model is the cheapest of the three.
- You want explainable retrieval — the intent-weighted beam search produces a traversal trace you can log and audit.
- You are doing research or building infrastructure that will iterate on the policy (e.g., replacing the rule-based policy with RL).

Prefer Graphiti-style single temporal KG when:
- Your dominant need is **bi-temporal provenance** (point-in-time queries, "what did we know when"). Graphiti's invalidation model is more mature here.
- You want off-the-shelf Neo4j integration and production maturity.

Prefer Hindsight-style epistemically-partitioned single graph when:
- **Accuracy matters more than architecture novelty.** Hindsight's public LongMemEval/LoCoMo numbers are the current bar.
- You need epistemic distinction (agent experience vs. world facts) for disposition-aware reasoning.
- You want abstraction (observations, trends) in addition to raw events.
- You want a single-DB deployment (PostgreSQL-only).

And importantly, the three are not mutually exclusive at the architectural level. A natural synthesis — and the research direction MAGMA implicitly opens — would be a **multi-graph memory partitioned by both relation type (MAGMA's axis) and epistemic type (Hindsight's axis), with bi-temporal edges (Graphiti's axis) and a learned policy over edge-type weights**. Each of the three papers contributes an orthogonal improvement; MAGMA's specific contribution is demonstrating that factoring the *edge topology* along relation type yields measurable gains (0.063 judge-score points from the adaptive policy alone), which is evidence that the multi-view graph structure is not just aesthetically cleaner but empirically better.

For a coding-assistant deployment (the target scenario in this repo's `CLAUDE.md`), Hindsight remains the pragmatic choice today — it is open-source, benchmark-leading, and has the epistemic separation that coding work needs (code facts vs. user preferences vs. session experiences). MAGMA's ideas — async consolidation, intent-weighted traversal, relation-typed edge partitioning — are worth porting into such a system, but as design inspiration rather than drop-in replacement.

---

## Sources

- [arXiv: MAGMA (2601.03236)](https://arxiv.org/abs/2601.03236) (accessed: 2026-04-15)
- [arXiv HTML v1](https://arxiv.org/html/2601.03236v1) (accessed: 2026-04-15)
- Companion reports in this repo: [graphiti.research.md](./graphiti.research.md), [hindsight.research.md](./hindsight.research.md)
- LoCoMo benchmark: [Maharana et al., 2024](https://arxiv.org/abs/2402.17753) (accessed: 2026-04-15)
- LongMemEval benchmark: [Wu et al., 2024](https://arxiv.org/abs/2410.10813) (accessed: 2026-04-15)
