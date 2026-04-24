# Memory Research: Academic Side Summary (2026)

Last Updated: 2026-04-15

Synthesis of 5 deep-dive papers + 7 skim papers covering 2026 academic memory architectures. Companion to `memory.summary.md` (engineering side) and `memory.26Q1.summary.md` (product Q1 update).

Source files:
- Deep dives: `memory-survey-2026.research.md`, `memory-anatomy.research.md`, `magma.research.md`, `licomemory.research.md`, `simplemem.research.md` (+ `a-mem.research.md`, `agemem.research.md` pending)
- Skims: `memory.skim-summaries.md` (7 papers)
- Literature scan: `memory.literature-scan.md`

---

## 1. The 2026 Taxonomy (anchor paper: "Memory in the Age of AI Agents", 2512.13564)

Three orthogonal axes — the canonical framework our existing research should be organized against:

| Axis | Dimensions |
|------|------------|
| **Forms** (substrate) | token-level (flat / planar / hierarchical), parametric (weights / adapters), latent (hidden state / KV-style) |
| **Functions** (purpose) | factual (user/world), experiential (case / strategy / skill), working (task scratchpad) |
| **Dynamics** (lifecycle) | formation, evolution (consolidation / updating / forgetting), retrieval (timing / query / strategy / post-processing) |

### Where existing systems sit on the cube

| System | Form | Function | Evolution |
|--------|------|----------|-----------|
| Mem0 | planar token-level | factual | LLM-CRUD |
| Letta | hierarchical token-level | factual + working | LLM self-edit |
| Graphiti / Zep | hierarchical token-level (graph) | factual | bi-temporal |
| Hindsight | hierarchical token-level | **factual + experiential + observational** (rare breadth) | retain/recall/reflect |
| Mastra OM | planar token-level | working-primary + factual | pure compression, no retrieval |
| MemOS | **token + parametric + latent** (rare breadth) | factual | OS-like paging |
| Supermemory ASMR | planar token-level | factual | LLM-as-retriever |
| ChatGPT / Claude | planar token-level | factual | pre-computed summaries / on-demand tools |
| OpenClaw memory | planar token-level | factual + working | pre-compaction flush |

**Observation**: the engineering crowd is concentrated in ONE corner of the cube (token-level × factual × retrieval-heavy). Hindsight and MemOS are the rare outliers broad on one axis each. **Letta is a taxonomy blind spot** — its substrate is ordinary but its *locus of control* (LLM edits its own memory via tools) has no axis in the framework.

### Gaps the survey itself has

1. **No "who manages memory" axis** — LLM-managed / service-managed / user-managed is orthogonal
2. **No cost model** — latency, storage, token, and training costs not factored
3. **Benchmarks only probe factual corner** — LongMemEval / LoCoMo say nothing about experiential or working memory

---

## 2. Methodology Warning: "Anatomy of Agentic Memory" (2602.19320)

This paper invalidates much of how we (and the broader field) have been comparing memory systems.

### Four evaluation pitfalls

| Pitfall | Concrete evidence |
|---------|-------------------|
| **Benchmark saturation** | LongMemEval-S and LoCoMo both sit in "Moderate saturation" band — top systems now within noise of full-context baseline |
| **Metric misalignment** | Lexical-overlap scores (F1 on golden spans) diverge from LLM-judge semantic utility; gaps up to ~15 points |
| **Backbone variance** | Same memory system swings 40+ points just from backbone swap (gpt-4o-mini → Qwen-2.5-3B on LoCoMo); format-error rate 2x |
| **Latency overhead** | Most papers don't report per-query cost; hidden cost often dominates |

### Required triage for valid comparison

Any cross-system accuracy claim must include:
1. **Δ = Score_MAG − Score_FullContext** on matched backbone (not raw score)
2. **Same backbone** across systems being compared
3. **LLM-as-judge with multi-rubric validation** (not just F1)
4. **Latency / maintenance cost** reported

### What this means for our existing research (corrections backlog)

**Claims that need asterisks**:
- `hindsight.research.md`: "91.4% on LongMemEval" — valid only paired with backbone (Gemini-3 Pro) and without implying cross-system comparability
- `supermemory.research.md`: "98.6% oracle" — self-report, no backbone-controlled Δ, not comparable
- `magma.research.md` & others with benchmark tables mixing Mem0 (49%) / Graphiti (71.2%) / Hindsight (91.4%) — different backbones, different splits, invalid cross-paper table
- `memory.26Q1.summary.md` "Mastra OM 94.87% LongMemEval" — valid only with backbone (gpt-5-mini) noted

**Action item**: pass over all `*.research.md` files and add a "⚠️ Backbone-dependent, cross-system comparison invalid" note wherever single-number benchmark claims appear without Δ.

---

## 3. Three 2026 Architectural Trends

### 3.1 Edge topology by relation type (MAGMA)

Single-graph KGs (Graphiti, LiCoMemory) store all edges in one structure. MAGMA (2601.03236) factors into **four orthogonal graphs**:
- **Semantic** (cosine threshold) — "similar to"
- **Temporal** (timestamp chain, immutable backbone) — "before/after"
- **Causal** (LLM-inferred with δ threshold) — "caused by"
- **Entity** (bipartite event↔entity) — "about"

Retrieval is a rule-based policy (Why/When/Entity classifier) that picks edge-type weights at query time.

**Performance**: LoCoMo judge-score 0.700 vs A-MEM 0.580 / MemoryOS 0.553 (+18-45% relative). But **LongMemEval only 61.2%**, 30 points behind Hindsight. Latency 1.47s/query, fastest.

**Verdict**: a design axis (relation-type factoring) orthogonal to Hindsight's (fact-type factoring) and Graphiti's (single-graph bi-temporal). Not a drop-in replacement; a future synthesis target.

### 3.2 Minimalist graph as semantic index (LiCoMemory)

LiCoMemory (2511.01448) reframes KG from "authoritative data store" to "pointer index":
- Nodes carry only identifiers, **no content**
- No consistency contract (duplicates and contradictions coexist)
- Content resolved via chunk pointers at query time
- Session-level + triple-level similarity fused with harmonic mean
- Weibull decay (scale = Δτ median across retrieved triples) modulates scores

**Performance**: +7-10 points overall vs second-best, **23% headline only on temporal-reasoning subset**. Biggest win: construction latency **21s vs Zep's 2871s — ~100× faster ingest**.

**Verdict**: "semantic index ≠ KG" is half-real (3 structural distinctions that yield measurable latency wins) and half-marketing (underlying data model is still entity-relation triples). Honest framing: **inconsistency-tolerant minimalist KG used as content-addressable index**.

### 3.3 Pareto-efficient compression (SimpleMem)

SimpleMem (2601.02553) optimizes the **cheap-context regime**:
- Stage 1: info-score-gated compression
- Stage 2: affinity-based consolidation (τ=0.85)
- Stage 3: adaptive-k hybrid retrieval

**Performance**: 531 tokens/query on LoCoMo vs Mem0 973 / baseline 16910. **+26.4% avg F1 over Mem0** (the "64% LoCoMo" claim from earlier summaries was false — actual headline is 26.4%; 44% only on MultiHop subcategory). Absolute F1 43.24 — far below Hindsight's LoCoMo 89.61.

**Verdict**: **academic efficiency flagship, not deployable SOTA**. Three techniques worth stealing: (1) information-score pre-filter, (2) ISO-8601 normalization at extraction, (3) query-complexity-driven top-k.

---

## 4. Emerging directions (from 7 skim papers)

### 4.1 Memory evolution (A-MEM, 2502.12110) — deep dive: `a-mem.research.md`

**Mechanism**: when a new note is inserted, top-k embedding neighbors (default k=10) each trigger an LLM call `Ps3` that can rewrite `keywords`, `tags`, `context description` of the historical note — but **never** the original `content`. This **content-immutable + metadata-mutable** split is A-MEM's distinctive architectural bet.

**Comparison with already-covered mechanisms**:
- Mem0 rewrites content (LLM-CRUD on facts)
- Graphiti invalidates via bi-temporal (old facts marked expired, new facts added)
- Hindsight synthesizes observations (derives new nodes, doesn't edit historical ones)
- **A-MEM: edits historical metadata in place, keeps content frozen** — no parallel in existing engineering systems

**Numbers** (LoCoMo / GPT-4o-mini):
- Temporal F1: 45.85 vs MemGPT 25.52
- Ablation: evolution adds +14.6 F1 over link-generation alone
- Tokens/op: 1,200-2,500 vs MemGPT ~16,900 (6.76-14.1× reduction — matches 7-13× claim)
- Cost <$0.0003/op, latency 1.1-5.4s

**Production verdict**: `agiresearch/A-mem` MIT, ~970 stars, ChromaDB-backed. **Prototype-grade only** — synchronous, single-tenant, no conflict resolution / rollback, worst-case 12 LLM calls per insert (write amplification). Temporal-reasoning-heavy agents benefit; write-heavy deployments need async evolution + neighbor-cap engineering.

### 4.2 Learned memory policy (AgeMem, 2601.01885) — deep dive: `agemem.research.md`

**Mechanism**: six memory ops (Add / Update / Delete / Retrieve / Summary / Filter) exposed as tool actions. Decision-making LLM's weights fine-tuned via three-stage progressive step-wise GRPO with task-reward gradients flowing through every memory op. Trained on Qwen2.5-7B and Qwen3-4B.

**"Learned" vs "Prompted" — narrower gap than expected**:
- Real distinction: AgeMem modifies LLM weights; Mem0/Letta/Hindsight run prompted calls with fixed weights
- **But ablation shows tool vocabulary alone (no RL) captures 40-60% of gains**
- RL on top adds only ~6 points on HotpotQA
- **Exposing ops > learning a policy** for most gains

**Numbers** (5 × 2 benchmark cells, all beat Mem0):
- HotpotQA: +7.78 / +16.33 across backbones
- SciWorld: +8.56 / +8.10
- BabyAI: +12.5 (Qwen3-4B)
- Average success: 41.96% / 54.31%
- Memory quality: 0.533-0.605 vs 0.479-0.513
- Token reduction: only 3-5% vs RAG (not a headline)

**Reproducibility caveats**:
- **No GPU-hours / step count / learning rate disclosed** in paper
- Inferred: tens to low-hundreds of H100s (GRPO on 7B with long trajectories)
- **No code release mentioned**
- Baselines only compared against Mem0 (no Hindsight / Mastra / Graphiti)
- Per Anatomy methodology: no Δ vs Full-Context, backbones both Qwen-family → cross-system validity unverified

### 4.3 Related: A-MAC (2603.04549, admission-only learned control)

Narrows scope to admission gate only; 5 interpretable factors (future utility, factual confidence, semantic novelty, temporal recency, content type prior). Useful reference for a single-stage interpretable gate; see `memory.skim-summaries.md` for details.

### 4.3 Weight-as-memory (TTT-E2E, 2512.13898 + 2512.23675)

Test-time training compiles long context into weights at serving time: 2.7× speedup at 128K, 35× at 2M. **Orthogonal paradigm** — not storage-based memory at all. Fits CLAUDE.md's Pillar 3 (continual learning) TODO. Belongs with `plan/2-learning-research.md`, not this plan.

### 4.4 Multi-graph taxonomies (Graph-based Agent Memory survey, 2602.05665)

Systematizes graph memory variants: KG / temporal / hypergraph / hierarchical tree / hybrid. Would sharpen `graphiti.research.md` and blog #2 if we expand graph coverage.

### 4.5 Personalization-driven architecture (Memoria, 2512.12686)

Four modules: logging + user modeling + summarization + context-aware retrieval. Weighted KG for user trait modeling. Similar in spirit to Graphiti + decay layer. Skip unless user modeling becomes in-scope.

---

## 5. Translating to the Dayfold design

User's Dayfold memory (`/Users/linguanguo/dev/dayfold_webapp-memory/agent/docs/tech-design-memory.md`) sits at token-level × factual × retrieval-heavy with nightly batch extraction and LIKE-only search.

### Academic ideas worth considering

| Idea | Source | Applicability to Dayfold |
|------|--------|--------------------------|
| **Info-score pre-filter** | SimpleMem Stage 1 | Could gate which project gets memorized in Extractor 1.4, skip zero-signal "pure gen image" projects more aggressively |
| **ISO-8601 normalization at extraction** | SimpleMem | Useful for EventMemory timeline — normalize date phrasing so LIKE search hits |
| **Adaptive-k hybrid retrieval** | SimpleMem Stage 3 | memory_retriever's 4-tool-call cap could use query-complexity heuristic to pick depth |
| **Minimalist graph as index** | LiCoMemory | If LIKE scan ever hits limits, move to "entity id → project pointer" index before full KG |
| **Memory evolution** | A-MEM | UserProfile regeneration currently overwrites — consider retroactive keyword/tag updates instead of full rewrite |
| **Δ vs Full-Context eval** | Anatomy | Dayfold's Phase 4 retriever eval must include "no-memory baseline" comparison, not just absolute accuracy |

### Warnings

- **Don't benchmark Dayfold's retriever against public LongMemEval/LoCoMo numbers** — different backbone, different domain, different task. Build own eval set (per Plan 4 Phase 4 recommendation).
- **Don't trust "X% improvement" claims from memory papers** without checking (a) backbone, (b) Δ baseline, (c) whether it's subset or overall.

---

## 6. Open questions surfaced

1. **Can Hindsight's four epistemic networks + MAGMA's relation-type factoring + LiCoMemory's pointer-only nodes be unified?** Each is one cut through the design space; nobody has combined all three.
2. **When does "learned policy" (AgeMem) beat "prompted LLM" (Mem0) enough to justify the RL training pipeline?** Current benchmarks can't answer this due to backbone variance.
3. **Is memory evolution (A-MEM) decidable at extraction time or does it require retrieval-time re-check?** Paper says extraction-time; but that means stale evolution if no re-check.
4. **Are any 2026 benchmarks NOT saturated and NOT backbone-sensitive?** Anatomy paper says no — this is the biggest research gap.

---

## 7. Reading order recommendation

**If starting fresh**:
1. `memory-survey-2026.research.md` — taxonomy anchor
2. `memory-anatomy.research.md` — methodological skepticism (read before any benchmark claims)
3. `memory.skim-summaries.md` — landscape breadth
4. Specific deep dives on topics you care about: `magma.research.md` / `licomemory.research.md` / `simplemem.research.md` / `a-mem.research.md` / `agemem.research.md`
5. Tie back to engineering: re-read `memory.summary.md` and `memory.26Q1.summary.md` with the taxonomy + methodology lens applied
