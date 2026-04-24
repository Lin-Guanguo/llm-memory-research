# 2026 Memory Literature Scan

**Last Updated:** 2026-04-15

## Methodology

This scan searched **arxiv (cs.CL, cs.AI)**, **Google Scholar**, and **major leaderboards** (LongMemEval, LoCoMo) for 2026 and 2025 papers on LLM agent memory architectures. 

**Search queries:**
- "LLM memory" + "agent memory" + "long-term memory" (2026 filter)
- "episodic memory LLM", "memory-augmented neural networks"
- Forward citations from anchor papers (Hindsight 2512.12818, Supermemory, MemOS)
- Leaderboard paper trails (LongMemEval, LoCoMo new entries)
- Survey papers on memory systems ("Memory in the Age of AI Agents", etc.)
- Graph-based memory, continual learning, test-time training

**Coverage:** cs.CL/cs.AI arxiv, OpenReview (ICLR 2026, NeurIPS 2025), specialized blogs (Zep, Emergentmind).

---

## Tier 1 — 2026 Papers (Deep-dive Candidates)

### 1. Memory in the Age of AI Agents (Survey)
- **arxiv/link:** [2512.13564](https://arxiv.org/abs/2512.13564)
- **Authors/affil:** Yuyang Hu et al. (46 authors, multi-institutional)
- **One-line:** Consolidated taxonomy of agent memory across forms (token/parametric/latent), functions (factual/experiential/working), and dynamics (formation/evolution/retrieval).
- **Why notable:** Establishes conceptual clarity for fragmented memory research. First unified framework treating memory as first-class agent primitive. Positions memory as distinct from RAG/context engineering.
- **Benchmarks reported:** Analyzed 4+ recent benchmarks (LongMemEval, LoCoMo implicitly referenced); identifies persistent gaps in multi-session reasoning.
- **Relation to covered work:** Organizes product/paper landscape into factual vs. experiential memory; subsumes Hindsight, Supermemory, MemOS conceptually.
- **Recommend deep dive:** **YES** — This is the canonical 2026 taxonomy paper. Essential for framework coherence before diving into specific architectures.

### 2. Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers (Survey)
- **arxiv/link:** [2603.07670](https://arxiv.org/html/2603.07670v1)
- **Authors/affil:** Multi-authored survey (2026-02 or later)
- **One-line:** Structured account of memory design/implementation/evaluation in LLM agents (2022–early 2026), proposing 3D taxonomy (temporal scope, representational substrate, control policy) and examining five mechanism families.
- **Why notable:** Five mechanism families: (1) context-resident compression, (2) retrieval-augmented stores, (3) reflective self-improvement, (4) hierarchical virtual context, (5) policy-learned management. Shifts evaluation from static recall to multi-session tests interleaving memory with decision-making.
- **Benchmarks reported:** References 4 recent multi-session agentic benchmarks; reports persisting limitations across systems.
- **Relation to covered work:** Directly addresses product systems (memory modules in agents). Hierarchy aligns with Hindsight's tier 2 operations (retain/recall/reflect).
- **Recommend deep dive:** **YES** — Complementary mechanisms view to Memory in Age of Agents; clarifies design space.

### 3. Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects
- **arxiv/link:** [2512.12818](https://arxiv.org/abs/2512.12818)
- **Authors/affil:** Chris Latimer et al. (Vectorize.io, Washington Post, Virginia Tech)
- **One-line:** Structured memory architecture organizing agent knowledge into four networks (world facts, experiences, entity summaries, beliefs) with retain/recall/reflect operations; implements Tempr (temporal entity memory) + Cara (reasoning with coherent opinion network).
- **Why notable:** Addresses key gap: current systems blur evidence/inference, struggle long-horizon organization, offer limited reasoning transparency. Hindsight's tiered networks + opinion tracking is novel. **Strongest empirical result: 83.6% accuracy on LongMemEval (vs. 39% full-context baseline) using 20B model, outperforming GPT-4o full-context.**
- **Benchmarks reported:** LongMemEval: 83.6% vs 39% baseline. LoCoMo results also reported.
- **Relation to covered work:** Direct product ancestor (covered in engineering survey). This is the flagship academic paper establishing structured memory as SOTA.
- **Recommend deep dive:** **YES** — Tier 1 anchor. Core reference for retain/recall/reflect paradigm.

### 4. Graph-based Agent Memory: Taxonomy, Techniques, and Applications
- **arxiv/link:** [2602.05665](https://arxiv.org/html/2602.05665v1)
- **Authors/affil:** Multi-author survey (Feb 2026)
- **One-line:** Comprehensive graph-memory taxonomy covering short/long-term, knowledge/experience, non-structural/structural; evaluates knowledge graphs, temporal graphs, hypergraphs, hierarchical trees, hybrid graphs.
- **Why notable:** Graph-based memory emerged as 2025–2026 frontier. First systematic taxonomy. Shows why graphs model relational dependencies, hierarchy, and efficient retrieval better than flat stores.
- **Benchmarks reported:** Implicit comparison across graph variants; cites LoCoMo/LongMemEval but focuses on architectural properties.
- **Relation to covered work:** Organizes graph papers (MAGMA, Zep/Graphiti, LiCoMemory, HyperMem, etc.). Subsumes product graph approaches (Graphiti from Zep).
- **Recommend deep dive:** **MAYBE** — Excellent architectural survey. Recommend if exploring graph-specific deep-dives; may overlap with Memory in Age of Agents mechanistically.

### 5. MAGMA: A Multi-Graph based Agentic Memory Architecture for AI Agents
- **arxiv/link:** [2601.03236](https://arxiv.org/html/2601.03236v1)
- **Authors/affil:** Multi-author (Jan 2026)
- **One-line:** Extends single-graph KGs to multi-graph: orthogonal semantic, temporal, causal, entity graphs. Formulates retrieval as policy-guided traversal over relational views.
- **Why notable:** Novel multi-graph framing unifies scattered context via orthogonal semantic/temporal/causal/entity relations. Outperforms state-of-the-art agentic memory on long-horizon LoCoMo/LongMemEval tasks.
- **Benchmarks reported:** LoCoMo, LongMemEval (SOTA reported, specific numbers not extracted in search).
- **Relation to covered work:** Advances Graphiti/Zep (single temporal KG) to richer relational model. Complements Hindsight's tier-2 networks (causality, entity linking explicit).
- **Recommend deep dive:** **YES** — Multi-graph paradigm is novel and well-motivated. Strong empirical results.

### 6. SimpleMem: Efficient Lifelong Memory for LLM Agents
- **arxiv/link:** [2601.02553](https://arxiv.org/html/2601.02553v1)
- **Authors/affil:** Multi-author (Jan 5, 2026)
- **One-line:** Three-stage pipeline: (1) semantic structured compression (distill unstructured to compact indexed units), (2) online semantic synthesis (intra-session redundancy elimination), (3) intent-aware retrieval (dynamic scope planning).
- **Why notable:** Addresses token efficiency (64% improvement on LoCoMo; 30-fold inference token reduction). Emphasizes lossless compression + semantic synthesis. F1 improvement: 26.4% over baselines.
- **Benchmarks reported:** LoCoMo: 64% improvement (as of Feb 2026 update); outperforms Claude-Mem. Achieves superior accuracy/efficiency/cost balance.
- **Relation to covered work:** Orthogonal to graph-based; complements Hindsight's retain phase with compression. Text-centric (no graphs).
- **Recommend deep dive:** **YES** — Token efficiency + multimodal support differentiates. Strong practical results.

### 7. LiCoMemory: Lightweight and Cognitive Agentic Memory for Efficient Long-Term Reasoning
- **arxiv/link:** [2511.01448](https://arxiv.org/html/2511.01448)
- **Authors/affil:** Multi-author (Nov 2025 submission, 2026 work)
- **One-line:** CogniGraph—lightweight hierarchical graph using entities/relations as semantic indexing. Temporal + hierarchy-aware search with reranking; explicit hyperlinks to dialogue evidence.
- **Why notable:** 23% accuracy improvement on LoCoMo/LongMemEval. Reframes KG as semantic index (not static repo). Reduces update latency; demonstrates efficient retrieval at scale.
- **Benchmarks reported:** LoCoMo, LongMemEval (23% improvement over second-best). Temporal reasoning, multi-session consistency, retrieval efficiency all improve.
- **Relation to covered work:** Intermediate between SimpleMem (lightweight) and MAGMA (multi-graph). Adds temporal awareness; lighter than MAGMA.
- **Recommend deep dive:** **YES** — Practical efficiency gains + semantic indexing novel. Bridges graph/compression approaches.

### 8. Zep: A Temporal Knowledge Graph Architecture for Agent Memory
- **arxiv/link:** [2501.13956](https://arxiv.org/html/2501.13956v1) (published Jan 2025, 2026 refinements documented)
- **Authors/affil:** Preston Rasmussen et al. (Zep company)
- **One-line:** Graphiti engine—temporally-aware KG dynamically synthesizing unstructured (conversational) + structured (business) data; maintains fact validity windows (non-lossy history).
- **Why notable:** Production-grade temporal fact management (facts have validity windows; old facts invalidated not deleted). Outperforms MemGPT on Deep Memory Retrieval (94.8% vs 93.4%). P95 latency 300ms; used in production CRM/compliance/healthcare.
- **Benchmarks reported:** Deep Memory Retrieval (DMR): 94.8% vs MemGPT 93.4%.
- **Relation to covered work:** Forward-cited anchor from plan. Graphiti is embedded in production (Mem0, etc.). This is the canonical temporal KG paper.
- **Recommend deep dive:** **YES** — Production maturity + temporal validity windows novel. Validates graph-based approach at scale.

### 9. Adaptive Memory Admission Control for LLM Agents (A-MAC)
- **arxiv/link:** [2603.04549](https://arxiv.org/abs/2603.04549)
- **Authors/affil:** Guilin Zhang et al. (published ICLR 2026 Workshop MemAgent, Mar 4, 2026)
- **One-line:** Decomposes memory admission as structured decision: five interpretable factors (future utility, factual confidence, semantic novelty, temporal recency, content type prior) evaluated pre-storage.
- **Why notable:** Elevates memory admission to first-class control (vs. opaque LLM judgment or heuristics). Explicit tradeoffs between coverage/reliability/efficiency. Novel control-theoretic framing.
- **Benchmarks reported:** Not explicit in abstract; ICLR workshop paper likely empirical on LoCoMo/LongMemEval derivatives.
- **Relation to covered work:** Orthogonal to storage architecture (works with any backend). Complements Hindsight's retain phase with structured gating.
- **Recommend deep dive:** **MAYBE** — Strong control-theory contribution. Skip if focusing on retrieval; prioritize if studying memory lifecycle (retain → admit → recall → reflect).

### 10. A-MEM: Agentic Memory for LLM Agents (NeurIPS 2025, extended 2026)
- **arxiv/link:** [2502.12110](https://arxiv.org/html/2502.12110v11)
- **Authors/affil:** Wujiang Xu et al. (NeurIPS 2025 poster)
- **One-line:** Zettelkasten-inspired agentic memory: dynamic indexing/linking creates interconnected knowledge networks. New memories generate structured notes (descriptions, keywords, tags); trigger contextual updates to historical memories.
- **Why notable:** Zettelkasten formalism (bidirectional links, atomic notes) applied to LLM memory. Continuous refinement of understanding as new memories arrive. Empirical SOTA on 6 foundation models.
- **Benchmarks reported:** 6 foundation models tested; reported SOTA improvements (specific benchmarks unclear from abstract).
- **Relation to covered work:** Orthogonal organization principle (Zettelkasten) vs. graphs/compression. Complements graph approaches; more fine-grained note-linking.
- **Recommend deep dive:** **MAYBE** — Novel organizational metaphor. Recommend if deep-diving organizational principles; may overlap with graph-based approaches functionally.

---

## Tier 2 — 2025 Papers

### 1. Memoria: A Scalable Agentic Memory Framework for Personalized Conversational AI
- **arxiv/link:** [2512.12686](https://arxiv.org/html/2512.12686v1) (Dec 14, 2025 submission)
- **Authors/affil:** Multi-author
- **One-line:** Modular hybrid framework integrating dynamic session summarization + weighted KG-based user modeling. Four modules: conversation logging, user modeling, session summarization, context-aware retrieval.
- **Why notable:** Hybrid short-term (summarization) + long-term (KG user model) architecture. Achieves 87.1% benchmark accuracy, 38.7% latency reduction, token-efficient. Plug-and-play design.
- **Benchmarks reported:** 87.1% accuracy (benchmark unspecified); 38.7% latency reduction, reduced token usage.
- **Relation to covered work:** Adds personalization (user trait/preference modeling) vs. generic architectures. Similar to Hindsight beliefs network but KG-structured.
- **Recommend deep dive:** **MAYBE** — Personalization angle novel. Skip if focusing on core long-term reasoning; prioritize if user modeling is in scope.

### 2. MemoryBench: A Benchmark for Memory and Continual Learning in LLM Systems
- **arxiv/link:** [2510.17281](https://arxiv.org/html/2510.17281v4) (Oct 2025 submission)
- **Authors/affil:** Multi-author (THUIR, Hugging Face dataset)
- **One-line:** Comprehensive benchmark (declarative + procedural memory) with explicit/implicit user feedback. Tests continual learning, knowledge retention, task adaptation across domains/languages/input-output lengths.
- **Why notable:** First benchmark providing **all** memory types + feedback data. Shows existing systems weak on procedural knowledge utilization and continual learning efficiency. Reveals memory systems not ready for real-world feedback loops.
- **Benchmarks reported:** Open-sourced at Hugging Face. Baseline results on RAG + SOTA memory systems.
- **Relation to covered work:** Benchmarking (not architecture). Complements LongMemEval/LoCoMo by testing continual learning.
- **Recommend deep dive:** **MAYBE** — Evaluation framework. Prioritize if studying benchmark design; otherwise secondary.

### 3. Test-Time Training for Long-Context LLMs (TTT-E2E & Query-Only TTT)
- **arxiv/link:** [2512.13898](https://arxiv.org/html/2512.13898v1) (Dec 2025, "Let's (not) just put things in Context") + [2512.23675](https://arxiv.org/abs/2512.23675) (End-to-End TTT)
- **Authors/affil:** Multi-author (MIT, industry)
- **One-line:** Two variants: TTT-E2E (compress context to weights via next-token prediction, O(1) inference latency) and Query-Only TTT (lightweight query-matrix adaptation, reuse KV cache).
- **Why notable:** Novel test-time learning paradigm. TTT-E2E achieves 2.7x speedup (128K context), 35x (2M context). Avoids external memory entirely; learning is built-in.
- **Benchmarks reported:** Loss curves on long-context tasks; inference latency comparisons (vs. full attention, Mamba 2).
- **Relation to covered work:** Orthogonal to external memory (embedded learning). Complements retrieval-based systems; reduces memory need.
- **Recommend deep dive:** **MAYBE** — Represents different memory paradigm (learning-based vs. storage-based). Recommend if studying internal adaptation; secondary if external memory is focus.

### 4. Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of Evaluation and System Limitations
- **arxiv/link:** [2602.19320](https://arxiv.org/html/2602.19320v1) (Feb 22, 2026)
- **Authors/affil:** Dongming Jiang et al.
- **One-line:** Introduces concise taxonomy of Memory-Augmented Generation (4 structures: Lightweight Semantic, Entity-Centric/Personalized, Episodic/Reflective, Structured/Hierarchical). Empirical analysis of benchmark saturation, metric misalignment, backbone variance, latency overhead.
- **Why notable:** Critical analysis revealing **fragile empirical foundations**: benchmarks underscaled, metrics misaligned with semantic utility, performance backbone-dependent, system overhead overlooked. Identifies key pain points.
- **Benchmarks reported:** Analyzes (doesn't report raw scores) LongMemEval, LoCoMo, others. Shows metric sensitivity to backbone (e.g., GPT-3.5 vs GPT-4 wildly different).
- **Relation to covered work:** Meta-analysis of Tier 1 systems. Identifies evaluation pitfalls across Hindsight, SimpleMem, graph-based systems.
- **Recommend deep dive:** **YES** — Critical read for methodology soundness. Highlights what's NOT robust in current memory systems.

### 5. AgeMem: Learning Unified Long-Term and Short-Term Memory Management for LLM Agents
- **arxiv/link:** [2601.01885](https://arxiv.org/html/2601.01885v1) (Jan 5, 2026)
- **Authors/affil:** Yi Yu et al.
- **One-line:** Unified framework integrating LTM + STM as agent policy. Memory operations (store/retrieve/update/summarize/discard) exposed as tool actions. RL training via three-stage progressive GRPO.
- **Why notable:** Moves from separate LTM/STM (heuristic-driven) to learned unified policy. Autonomously decides what/when to store. Superior task performance, higher-quality LTM, efficient context on 5 long-horizon benchmarks.
- **Benchmarks reported:** 5 long-horizon benchmarks (specific names/scores not extracted, but reported improvements across all).
- **Relation to covered work:** Complements structured architectures (Hindsight, Memoria) with learned control. Similar intent to A-MAC but uses RL.
- **Recommend deep dive:** **MAYBE** — Learning-based control novel. Recommend if studying policy-driven memory; may be secondary to structural architectures.

---

## Tier 3 — Pre-2025 Reference Only

| Paper | Year | Core Idea | Absorbed By |
|-------|------|----------|-------------|
| HippoRAG | 2024 | Neurobiologically-inspired RAG; Personalized PageRank over entity graphs for multi-hop retrieval. | HippoRAG 2 (2026); Zep/Graphiti; MAGMA builds on entity graph framing |
| MemGPT | 2023 | Hierarchical memory (core context, buffer, archival); external storage with learned read/write. | All modern systems; benchmark standard (Deep Memory Retrieval). |
| MemoryBank | 2023 | Ebbinghaus forgetting curve applied to agent memory decay. | SimpleMem (semantic compression); Hindsight (reflection handles decay). |
| RAG (Retrieval-Augmented Generation) | 2020 | External store + semantic retrieval. | Foundation for all Tier 1 retrieval systems; subsumed by graph/compression variants. |
| Transformer XL, Compressive Transformers | 2018–2019 | In-context compression via segment-level recurrence. | Basis for hierarchical context approaches; superseded by external memory. |
| Neural Turing Machines, Differentiable Neural Computers | 2014–2016 | Learned addressable external memory; attention-based retrieval. | Precursor framing to modern agentic memory; theoretical foundation (Turing-complete + memory = universality). |

---

## Gaps I Couldn't Fill

1. **Specific numerical results on LoCoMo/LongMemEval for MAGMA, HyperMem:** Papers reference SOTA but search-accessible abstracts didn't yield exact accuracy percentages. (Full PDFs needed.)

2. **2026 papers on multimodal memory + agents:** Only found episodic memory benchmark (2501.13121). Likely gap in search coverage.

3. **Memory consolidation / sleep-like processes in LLMs:** Possible 2026 work; didn't surface in arxiv searches. May exist in neuroscience/biology venue crossover.

4. **Certified/trustworthy memory:** Only tangential mention in Anatomy (backbone-dependent results). Likely pre-2026 or absent.

5. **Memory for multi-agent systems:** One mention (Awesome-Efficient-Agents repo), but no dedicated 2026 paper found. May be in workflow/multi-turn literature.

6. **Hybrid internal + external memory:** TTT-E2E (internal learning) and external storage are largely separate literatures. Unified frameworks may be emerging post-April 2026.

---

## Summary

**Tier 1 (2026) top 5 for deep dive:**
1. **Memory in the Age of AI Agents** (2512.13564) — canonical taxonomy
2. **Hindsight** (2512.12818) — flagship structured memory + best empirical results
3. **MAGMA** (2601.03236) — multi-graph innovation
4. **SimpleMem** (2601.02553) — token efficiency + compression
5. **LiCoMemory** (2511.01448) — practical graph-based efficiency

**Supporting Tier 2 (2025):**
- **Anatomy of Agentic Memory** (2602.19320) — critical evaluation meta-analysis
- **MemoryBench** (2510.17281) — continual learning benchmark
- **AgeMem** (2601.01885) — learned unified memory control

**Leaderboard papers to track:**
- LongMemEval/LoCoMo leaderboards for late April–summer 2026 entries
- ICLR 2026 MemAgents workshop proceedings (submitted papers, accepted posters)

