# Memory Papers — Combined Skim Summaries

Last Updated: 2026-04-15

> **Research Methodology**: Generated from arxiv abstracts and HTML v1 renderings (no PDFs). Each paper got one abstract fetch plus, where useful, one HTML fetch to extract concrete numbers / taxonomy entries / benchmark names. No source code was read. Companion to our deep-dive `*.research.md` set (Mem0, Letta, Graphiti, Hindsight, Mastra, Supermemory, MemOS, and others under `/docs/`). These are skims — enough to decide whether to upgrade a paper to a full deep dive, not enough to reimplement the system.

---

## Table of contents

1. [Memory for Autonomous LLM Agents (Du, 2026)](#1-memory-for-autonomous-llm-agents-mechanisms-evaluation-and-emerging-frontiers)
2. [Graph-based Agent Memory survey (Yang et al., 2026)](#2-graph-based-agent-memory-taxonomy-techniques-and-applications)
3. [A-MAC: Adaptive Memory Admission Control (Zhang et al., 2026)](#3-a-mac-adaptive-memory-admission-control-for-llm-agents)
4. [A-MEM: Agentic Memory / Zettelkasten (Xu et al., NeurIPS 2025)](#4-a-mem-agentic-memory-for-llm-agents)
5. [Memoria: Personalized Conversational AI (Sarin et al., 2025)](#5-memoria-a-scalable-agentic-memory-framework-for-personalized-conversational-ai)
6. [AgeMem: Unified LTM/STM (Yu et al., 2026)](#6-agemem-learning-unified-long-term-and-short-term-memory-management)
7. [Test-Time Training for Long-Context LLMs (Bansal et al. + Tandon et al., 2025)](#7-test-time-training-for-long-context-llms-two-papers)

---

## Summary table

| # | Paper | arxiv | One-liner | Revisit |
|---|-------|-------|-----------|---------|
| 1 | Memory for Autonomous LLM Agents | [2603.07670](https://arxiv.org/abs/2603.07670) | Second 2026 survey; write/manage/read loop across a 3D taxonomy (temporal / substrate / policy) and 5 mechanism families. | **MEDIUM** |
| 2 | Graph-based Agent Memory | [2602.05665](https://arxiv.org/abs/2602.05665) | 18-author taxonomy of KG / temporal / hierarchical / hypergraph / hybrid graph memories; places Graphiti, Zep, Mem0, MemTree, G-Memory, HyperGraphRAG on one map. | **HIGH** |
| 3 | A-MAC | [2603.04549](https://arxiv.org/abs/2603.04549) | 5-factor interpretable admission policy (utility × confidence × novelty × recency × type-prior); 0.583 F1 on LoCoMo with 31% lower latency than LLM-native. | **HIGH** |
| 4 | A-MEM (Zettelkasten) | [2502.12110](https://arxiv.org/abs/2502.12110) | Structured notes with bidirectional links, continuous evolution on insert; ~45.85 F1 multi-hop on LoCoMo vs MemGPT 25.52, 7–13× fewer tokens. | **HIGH** |
| 5 | Memoria | [2512.12686](https://arxiv.org/abs/2512.12686) | 4-module hybrid: session summaries + exponentially-decayed weighted KG; 87.1% single-session on LongMemEval-style eval, 38.7% latency cut vs full context. | LOW |
| 6 | AgeMem | [2601.01885](https://arxiv.org/abs/2601.01885) | LTM+STM as tool actions learned via 3-stage GRPO RL; +4.82 pp over Mem0 on 5 long-horizon benchmarks (ALFWorld, SciWorld, PDDL, BabyAI, HotpotQA). | **HIGH** |
| 7 | Test-Time Training for Long-Context LLMs | [2512.13898](https://arxiv.org/abs/2512.13898) + [2512.23675](https://arxiv.org/abs/2512.23675) | Two papers pushing "internalize context into weights at test time"; +12–14 pp on LongBench-v2 / ZeroScrolls; 2.7× faster than full attention at 128K. | **HIGH** |

---

## 1. Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers

**arxiv**: [2603.07670](https://arxiv.org/abs/2603.07670) | **Year**: 2026 (submitted Mar 8) | **Venue**: preprint, single-author survey (Pengfei Du)

### TL;DR
A solo-authored 2026 survey that frames agent memory as a write–manage–read loop and organizes the field along a 3D taxonomy (temporal scope × representational substrate × control policy) with five mechanism families. Positions itself as a complement to the earlier "Memory in the Age of AI Agents" survey — narrower on consumer/product angle, deeper on mechanism-level classification and the shift toward agentic evaluation.

### Key contributions
- Write–manage–read loop as the unifying abstraction; every system is described by what it writes, what it promotes/demotes, and what it reads back.
- 3D taxonomy: **temporal scope** (session vs cross-session vs lifelong), **representational substrate** (text chunks, KV/cache, embeddings, graphs, parameters), **control policy** (heuristic vs learned vs LLM-judged).
- Five mechanism families: (1) context-resident compression, (2) retrieval-augmented stores, (3) reflective self-improvement, (4) hierarchical virtual context, (5) policy-learned management.
- Documents a benchmark shift from static recall to multi-session agentic tests that interleave memory with decision-making.
- Application map: personal assistants, coding agents, open-world games, scientific reasoning, multi-agent teamwork.
- Open-challenge list: continual consolidation, causally grounded retrieval, trustworthy reflection, learned forgetting, multimodal embodied memory.

### Architecture / method
No system — a survey. The taxonomy axes are each decomposable: temporal scope distinguishes in-context working memory from cross-session caches from lifelong parametric memory; substrate covers raw text, KV-cache compression, vector embeddings, graph triples, and weight-space edits under one frame; control policy separates hand-coded recency/TF-IDF from learned scorers from LLM-as-judge admission/consolidation. The five mechanism families map cleanly onto substrate × policy — e.g. MemGPT = hierarchical virtual context + LLM-judged control, Mem0/Letta = retrieval-augmented + mixed policy, Reflexion = reflective self-improvement + LLM policy, A-MEM = retrieval + learned/LLM-generated linking, AgeMem/RL systems = policy-learned. Evaluation section catalogues four benchmarks (LongMemEval, LoCoMo, and two agentic successors).

### Empirical results
No experiments — survey. The numerical content is a tabulation of reported benchmark scores from surveyed systems. No new evaluation.

### Relation to already-covered work
Directly complements **`memory.summary.md`** and the "Memory in the Age of AI Agents" framing we used in blog #2. The 3D taxonomy is more orthogonal than our current 4-tier bucket and could sharpen our own classification of Mem0, Letta, Graphiti, Hindsight, MemOS, Supermemory. "Policy-learned management" family directly maps to paper #6 (AgeMem) in this same batch.

### When to revisit for deep dive
- Come back if: we want to rewrite the taxonomy section of `memory.summary.md` or our blog posts with cleaner axes; if we need a reference to cite for "temporal scope vs substrate vs policy" as a dimensioning.
- Skip if: we only need specific system comparisons — this survey is abstract-level, not system-detail level.

---

## 2. Graph-based Agent Memory: Taxonomy, Techniques, and Applications

**arxiv**: [2602.05665](https://arxiv.org/abs/2602.05665) | **Year**: 2026 (submitted Feb 5) | **Venue**: preprint, 18-author consortium (Jilin / HKUST-GZ / others)

### TL;DR
The field's first dedicated graph-memory survey — organizes every graph-based memory system into five structural classes and analyzes them across a four-phase lifecycle (extraction → storage → retrieval → evolution). Positions graph memory as "a unified and general perspective" where non-graph memories are degenerate cases.

### Key contributions
- Five-way graph taxonomy: **Knowledge Graphs** (triples), **Temporal Graphs** (bi-temporal: valid-time + transaction-time), **Hierarchical Structures** (trees with parent-child + clustering), **Hypergraphs** (n-ary hyperedges), **Hybrid Architectures** (e.g. hierarchical-KG + experience pool).
- Three orthogonal axes: short-term vs long-term, knowledge vs experience, non-structural vs structural.
- Four-phase lifecycle framework applied uniformly across all systems.
- Concrete system placement: Mem0 (KG via LLM extraction), Graphiti (bi-temporal KG), MemTree (dynamic hierarchical routing), Zep (time-windowed validity), G-Memory (bi-directional hierarchical traversal), HyperGraphRAG (hypergraph dual-retrieval).
- Identifies future directions: graph evolution, multimodal graph memory, graph-based forgetting.

### Architecture / method
Survey only — no new system. The bi-temporal analysis is the sharpest contribution: distinguishing valid-time (when a fact held in the world) from transaction-time (when the agent recorded it) is what lets Graphiti answer "what did Alice believe about X on day T" vs "what did we record on day T." Hypergraphs are argued to preserve n-ary relations (e.g. "Alice, Bob, Carol co-authored paper P at venue V in year Y") that binary KGs must fragment. Hierarchical structures support both top-down navigation (query → cluster → chunk) and bottom-up summarization (chunk → cluster summary → root gist). The hybrid class is a catch-all for systems that compose two primitives.

### Empirical results
No new experiments. Survey-level aggregation of reported numbers from surveyed systems; no head-to-head reevaluation.

### Relation to already-covered work
Directly relevant to **`graphiti.research.md`** (bi-temporal is its flagship feature), **`mem0.research.md`** (has an optional graph mode), **`memos.research.md`** (has a graph-like schema). This survey gives us the first principled taxonomy slot for Hindsight's four-network design — which is roughly a *typed* KG with disposition labels, i.e. a hybrid in their terms. The HyperGraphRAG entry is the most novel pointer — we have not covered n-ary hyperedge memory anywhere.

### When to revisit for deep dive
- Come back if: we're writing a graph-memory-focused blog post, expanding `graphiti.research.md`, or evaluating whether to add a hypergraph system to our tracked set.
- Skip if: we stay non-graph-centric; Mem0/Graphiti deep dives already cover the dominant KG patterns.

---

## 3. A-MAC: Adaptive Memory Admission Control for LLM Agents

**arxiv**: [2603.04549](https://arxiv.org/abs/2603.04549) | **Year**: 2026 (submitted Mar 4) | **Venue**: ICLR 2026 MemAgent Workshop

### TL;DR
A deliberately *interpretable* alternative to LLM-judged memory admission. Decomposes "should this turn be retained?" into five numeric factors, combines them with a lightweight rule-based extractor plus a single LLM utility call, and optimizes weights via cross-validation. Trades a small quality gap for 31% lower latency and policy transparency.

### Key contributions
- Five interpretable admission factors, each scored 0–1: **future utility** (likelihood of later reuse), **factual confidence** (source reliability), **semantic novelty** (distance from existing memory), **temporal recency** (decay-weighted freshness), **content type prior** (domain-specific weight on what kind of content this is).
- Hybrid pipeline: rule-based feature extraction (fast) + one LLM call for utility (slow but bounded) → linear combination with cross-validated weights.
- Ablation-identified dominant factor: **content type prior** (biggest single contributor to admission quality).
- Clean baselines vs LLM-native admission systems (which use per-turn LLM judgments).
- Benchmark: LoCoMo F1 0.583 with 31% latency reduction vs LLM-native SOTA.

### Architecture / method
Per-turn input → rule features (entity count, pronoun ratio, novelty vs embedding store, recency delta, content-type classifier) → one LLM call that emits a utility score → weighted sum → threshold admits/discards. Weights are tuned offline via cross-validation on a labeled corpus. The authors argue this replaces opaque "let the LLM decide" policies with a policy whose decisions can be attributed to specific factors — useful for debugging memory bloat or forget-regressions. Admission is the only concern; retrieval is orthogonal and uses standard vector lookup over admitted items.

### Empirical results
- LoCoMo F1: **0.583**
- Latency: **31% lower** than LLM-native SOTA admission policy
- Ablation: removing content-type-prior causes the largest drop; removing temporal recency is cheapest
- No LongMemEval numbers reported in the abstract-level content fetched

### Relation to already-covered work
Directly fills a gap in **`mem0.research.md`** and **`letta.research.md`**: both systems have implicit admission via LLM extraction, but neither exposes a tunable factor decomposition. A-MAC is the kind of ablation-driven admission policy one could retrofit into Hindsight's retain operation (see `hindsight.research.md`). Complements rather than competes with Mem0's ADD/UPDATE/DELETE extraction — A-MAC asks "admit this turn at all?", Mem0 asks "what triples does this turn imply?"

### When to revisit for deep dive
- Come back if: we're building or evaluating our own memory pipeline, especially if we need an interpretable/debuggable admission layer; if we want a principled baseline for ablating "what does each feature contribute."
- Skip if: we only care about retrieval-time quality, not write-time filtering.

---

## 4. A-MEM: Agentic Memory for LLM Agents

**arxiv**: [2502.12110](https://arxiv.org/abs/2502.12110) | **Year**: 2025 (v1 Feb, extended 2026) | **Venue**: NeurIPS 2025

### TL;DR
A Zettelkasten-inspired memory system where each new memory becomes a structured note (contextual description + keywords + tags), the system auto-generates bidirectional links to related historical notes, and insertions *retroactively update* attributes of already-stored notes. Strong multi-hop performance at much lower token cost than MemGPT-style virtual-context systems.

### Key contributions
- Zettelkasten-style structured notes as the storage primitive (not raw text, not just embeddings).
- LLM-generated bidirectional links established at insertion time based on semantic similarity.
- **Memory evolution**: inserting a new note can trigger *updates* to the contextual descriptions/tags of linked historical notes — memory is not append-only.
- Tested on six foundation models (GPT-4o, GPT-4o-mini, Qwen2.5-1.5B, Qwen2.5-3B, Llama 3.2-1B, Llama 3.2-3B) — rare breadth for a memory paper.
- Code + eval harness released.

### Architecture / method
On write: LLM extracts (content, contextual description, keywords, tags) → embeds content → queries top-k historical notes for linking candidates → LLM decides which links are meaningful → writes both the new note and updates to linked historical notes' attributes. On read: query → retrieve via embedding + link traversal → assemble context. The link graph is what separates A-MEM from vanilla vector RAG — multi-hop queries can traverse links rather than rerunning retrieval. The "evolution" step is expensive (each insert touches historical notes) but amortized because each historical note converges over time.

### Empirical results
On LoCoMo multi-hop (the category A-MEM targets):
- GPT-4o-mini: **45.85 F1** vs MemGPT 25.52
- Qwen2.5-3B: **27.59 F1** vs baseline 3.11

Token cost: **1,200–2,500 tokens/query** vs ~16,900 for LoCoMo/MemGPT (7–13× reduction).

Ablation (GPT-4o-mini, multi-hop): no links + no evolution = 24.55 F1, links only = 31.24 F1, full = 45.85 F1. Both components matter; evolution adds roughly what linking does.

### Relation to already-covered work
Cited by almost every 2026 memory paper and is the reference point for "structured LLM-generated memory with links." **`hindsight.research.md`** has a similar philosophy (typed memory units with LLM extraction) but uses fact-type categories rather than link-graphs, and does not do retroactive attribute updates. **`mem0.research.md`** does update-on-insert (ADD/UPDATE/DELETE) but operates on triples, not notes+links. A-MEM sits between Mem0 (fine-grained triples) and Hindsight (typed units) on the granularity axis. Paper #5 (Memoria) benchmarks against A-MEM directly.

### When to revisit for deep dive
- Come back if: we want to add a dedicated `a-mem.research.md` to round out the "structured agentic memory" cluster — its influence across the 2026 papers justifies one; if we're writing about memory evolution / retroactive updates.
- Skip if: we already consider Mem0 + Hindsight representative of the structured-LLM-memory class.

---

## 5. Memoria: A Scalable Agentic Memory Framework for Personalized Conversational AI

**arxiv**: [2512.12686](https://arxiv.org/abs/2512.12686) | **Year**: 2025 (Dec 14) | **Venue**: AIML Systems 2025 (Bangalore), applied-industry track

### TL;DR
An industry-style hybrid: dynamic session-level summarization (short-term coherence) + weighted KG with exponential time-decay (long-term personalization) + a persistent conversation DB + a fused retrieval layer. Optimizes for deployment constraints (token budget, latency) rather than max benchmark accuracy.

### Key contributions
- Four-module architecture (Structured Conversation DB, Dynamic User Persona KG, Session-Level Memory, Seamless Retrieval).
- **Exponential decay weighting** on KG triplets — older edges lose weight, recent interactions dominate retrieval.
- Benchmarked on the LongMemEvals dataset (148 samples, 6 question categories) against full-context and A-MEM variants.
- Reports head-to-head latency numbers, not just accuracy — rare and useful for deployment discussion.

### Architecture / method
Every turn is persisted to the conversation DB (raw + session ID + extracted triplets + summary). The Dynamic User Persona module incrementally adds to a weighted KG — nodes are entities (topics, preferences, named entities), edges carry weight that decays exponentially with time since last touch. Session-Level Memory maintains a rolling summary of the current session to fit within token budget. At retrieval time, Seamless Retrieval fuses (a) recent session summary, (b) top-weighted KG subgraph relevant to the query, (c) raw-message snippets from the DB. The exponential decay is the key trick: rather than storing everything with equal weight and doing TF-IDF/embedding reranking at query time, weight decay does the work at write time.

### Empirical results
LongMemEvals:
- Single-Session-User: **87.1%** (Memoria) vs 85.7% full context, 84.2% A-MEM/OpenAI
- Knowledge-Update: **80.8%** vs 79.4% A-MEM/OpenAI, 78.2% full context

Latency:
- **38.7% reduction** vs full-context prompting
- Single-session inference: 260 s vs 391 s (full context)
- Knowledge-update: 320 s vs 522 s
- Prompt size: ~400 tokens vs ~115K (full context) — two orders of magnitude

### Relation to already-covered work
Overlaps strongly with **`mem0.research.md`** (both do KG-based personalization with incremental updates) and the personalization angle of **`supermemory.research.md`**. Exponential-decay KG weighting is not what Graphiti does (Graphiti uses explicit bi-temporal validity windows). The +1–3 pp accuracy gain over A-MEM comes at much lower token cost — this is the "good enough + cheap" operating point for conversational personalization, not a SOTA claim.

### When to revisit for deep dive
- Come back if: we're writing about deployment-cost tradeoffs or about KG weight-decay specifically; if we want an example of an industry-conference memory paper.
- Skip if: we already cover KG personalization via Mem0 and Graphiti. The contribution is the decay trick + latency measurement, not a new paradigm.

---

## 6. AgeMem: Learning Unified Long-Term and Short-Term Memory Management

**arxiv**: [2601.01885](https://arxiv.org/abs/2601.01885) | **Year**: 2026 (Jan) | **Venue**: preprint

### TL;DR
Treats memory ops (Add, Update, Delete, Summary, Filter, Retrieve) as *tools in the agent's action space* and trains the policy end-to-end with a three-stage GRPO RL recipe. Unifies LTM and STM under one policy instead of hand-coded rules. Best-in-class on five long-horizon benchmarks.

### Key contributions
- Memory management is an agent policy, not a subsystem — the same policy that decides "call get_weather" also decides "summarize and drop this chunk of STM."
- Three-stage GRPO training curriculum: (1) LTM construction with casual interaction, (2) STM control with distractors, (3) integrated reasoning under query.
- **Step-wise GRPO** with group-normalized advantage, terminal reward broadcast uniformly across timesteps — solves the sparse-reward credit-assignment problem for memory ops.
- Evaluated on five long-horizon benchmarks: **ALFWorld, SciWorld, PDDL, BabyAI, HotpotQA**.
- Strong gains over the memory-augmented SOTA: Mem0, Mem0^g (graph variant), A-MEM, LangMem.

### Architecture / method
The LLM agent sees a tool-use API that includes task tools (move, search, etc.) and memory tools (Add, Update, Delete on LTM; Summary, Filter on STM; Retrieve across both). A rollout is: receive query → take tool actions (including memory ops) → eventually produce answer. Reward = task success at end of episode. Training stages: stage 1 pre-trains the agent to *populate* LTM from casual interaction with contextual info; stage 2 pre-trains STM filtering under distractor pressure (context resets but LTM persists); stage 3 fine-tunes end-to-end query-answering with both LTM and STM active. Step-wise GRPO assigns the terminal reward across all steps in a group with group-normalized advantage, making sparse rewards learnable.

### Empirical results
- Qwen2.5-7B-Instruct: **41.96%** average across 5 benchmarks, **+49.59% relative** over no-memory, **+4.82 pp** over Mem0 (37.14%).
- Qwen3-4B-Instruct: **54.31%** average, **+23.52%** over no-memory.
- Memory-quality scores: 0.533 (Qwen2.5-7B), 0.605 (Qwen3-4B) — well above baselines.
- Ablation: AgeMem-noRL (same architecture, no RL fine-tune) shows the RL recipe is necessary, not just the action-space design.

### Relation to already-covered work
Orthogonal to the storage-focused papers we've covered. Mem0, Letta, Graphiti, Hindsight, Supermemory, MemOS all *hand-code* the policy that decides when to write/update/delete — AgeMem learns it. This is the first strong RL result in our tracked set. Closest prior is **`letta.research.md`** (MemGPT-style LLM-as-orchestrator, but prompted rather than RL-trained). Paper #1 (Du survey) would classify this under the "policy-learned management" family.

### When to revisit for deep dive
- Come back if: we want to write about the RL-for-memory angle or "memory as policy" as a direction; if we're evaluating whether to try GRPO on our own agent stack.
- Skip if: we're focused on retrieval-time tricks or storage substrate — AgeMem's contribution is training recipe, not architecture.

---

## 7. Test-Time Training for Long-Context LLMs (two papers)

**arxiv**: [2512.13898](https://arxiv.org/abs/2512.13898) (Query-Only TTT) + [2512.23675](https://arxiv.org/abs/2512.23675) (TTT-E2E) | **Year**: 2025 (Dec) | **Venue**: preprints

### TL;DR
Two concurrent papers arguing that for very long contexts, you get more for your inference compute by *training on the context* than by sliding-window attention or thinking tokens. Query-Only TTT does targeted gradient updates per query; TTT-E2E bakes test-time learning into a sliding-window Transformer end-to-end. Strong speedups at 128K+ context.

### Key contributions
**Query-Only TTT (Bansal et al., 2512.13898)**:
- Identifies **score dilution** — self-attention score mass thins out over very long contexts — as the fundamental scaling problem, not FLOPs.
- Targeted gradient updates on the given context as alternative to inference-time scaling (thinking tokens, chain-of-thought).
- **+12.6 / +14.1 pp** for Qwen3-4B on LongBench-v2 / ZeroScrolls.

**TTT-E2E (Tandon et al., 2512.23675)**:
- Standard Transformer + sliding-window attention + *continual next-token prediction at test time* = the model compresses the context it reads into its weights.
- Meta-learning training-time: initialization is optimized for test-time learning.
- 3B model trained on 164B tokens scales with context length at same rate as full-attention Transformer — beats Mamba-2, Gated DeltaNet.
- **2.7× faster than full attention at 128K**; constant inference latency regardless of context size (RNN-like).

### Architecture / method
Query-Only TTT: at inference, given a (context, query), run a small number of gradient steps on the context (with query-conditioned loss) on a few LoRA-like parameters, then answer. The context is briefly internalized into weights for this query only, then discarded — hence "query-only." TTT-E2E: the Transformer sees context through a sliding window but also runs next-token prediction as an online learning signal; the weights updated at test time persist for the rest of the sequence, giving RNN-style constant per-token cost. Both reject the assumption that "context" and "weights" must stay separate at inference.

### Empirical results
- Query-Only TTT: +12.6 pp LongBench-v2, +14.1 pp ZeroScrolls on Qwen3-4B (averages across subsets).
- TTT-E2E: 2.7× faster than full attention at 128K, **35× at 2M** context (per prompt's cited numbers); context-length scaling matches full-attention Transformers at 3B / 164B-token training.

### Relation to already-covered work
**This is a different regime from all our memory-system papers.** Mem0, Letta, Graphiti, Hindsight, Memoria, AgeMem all treat memory as an *external store* retrieved into a fixed-weight LLM. TTT treats memory as *weight updates* — the same direction as `multi-lora.research.md` and `hybrid-memory-weight.research.md` in our docs. The most direct overlap is `hybrid-memory-weight.research.md`, which surveys the idea that memory = weights is a real alternative. Paper #1 (Du) would classify this under the *parametric* substrate and its open-challenge list calls out "weight-space memory" specifically. Relevant to the **Learning** research direction in CLAUDE.md (continual learning, LoRA, adapter-based personalization) more than to Memory.

### When to revisit for deep dive
- Come back if: we write anything about weight-as-memory, continual learning, or the Learning direction in the research plan; if we're considering whether to benchmark TTT-style approaches against RAG-style memory.
- Skip if: we stay in the external-store regime — TTT isn't directly comparable on LongMemEval/LoCoMo style benchmarks.

---

## Notes on what's missing / unverified

- Memoria's 87.1% / 38.7% numbers are single-category and averaged respectively; cross-category accuracy wasn't fetched.
- A-MEM's "extended 2026" version (beyond NeurIPS 2025 camera-ready) may have additional benchmarks not captured from v1 HTML.
- The graph-memory survey (paper 2) lists systems in narrative form — I did not enumerate the full reference list (36+ systems expected).
- AgeMem's "memory quality score" metric is novel to the paper and its definition wasn't extracted here.
- Du's survey (paper 1) is single-author; I did not verify institutional affiliation or coverage completeness against the "Memory in the Age of AI Agents" survey.
