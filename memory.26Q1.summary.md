# LLM Memory Systems: 2026 Q1 Update

Last Updated: 2026-03-24

Previous baseline: `memory.summary.md` (2025-12)

---

## What Changed Since 2025

The 2025 landscape was dominated by Mem0 (fact extraction + vector/graph dual storage), Letta (three-tier self-editing memory), and Graphiti (temporal knowledge graph). Three months later, four new systems have emerged with fundamentally different approaches.

### The Biggest Shift: Anti-RAG Movement

In 2025, the assumption was "memory = retrieval = vector database." The 2026 Q1 projects challenge this:

| Project | Uses vector DB? | Uses LLM for retrieval? | Core approach |
|---------|:--------------:|:----------------------:|---------------|
| Mem0 (2025) | ✓ | ✓ (fact extraction) | Vector + graph dual storage |
| Letta (2025) | ✓ (archival tier) | ✓ (self-editing) | Three-tier virtual context |
| Graphiti (2025) | ✗ | ✓ | Temporal knowledge graph |
| **Supermemory ASMR** | ✗ | ✓ (3+3 agent pipeline) | LLM-as-retriever, ensemble voting |
| **Observational Memory (Mastra)** | ✗ | ✓ (Observer+Reflector) | Pure compression, no retrieval at all |
| **Hindsight** | Hybrid (BM25+semantic) | ✓ (Cara reflect agent) | Four cognitive networks + graph traversal |
| **MemOS** | Optional (Qdrant) | ✓ | OS abstraction over three memory types |

Three out of four new systems don't use vector databases. The field is moving from "embed and search" toward "compress and reason."

---

## New Projects

### Supermemory (ASMR)

**Approach**: Replace vector search entirely with LLM reasoning.

- 3 observer agents extract structured knowledge across 6 dimensions (personal info, preferences, events, temporal data, updates, assistant info)
- 3 search agents do retrieval via LLM reasoning (direct facts, contextual clues, temporal reconstruction)
- Ensemble voting: 8-variant cluster (98.6% oracle) or 12-variant decision forest (97.2% consensus)
- 11-15 LLM calls per question

**Reality check**: The ~99% score uses oracle evaluation (any of 8 attempts correct = correct). Production engine uses pgvector and scores 81.6%. ASMR is experimental, not yet open-sourced (promised April 2026).

**Detail**: `supermemory.research.md`

### Observational Memory (Mastra)

**Approach**: Pure compression, zero retrieval. Everything stays in the context window.

- Observer agent triggers at 30K tokens, compresses raw messages into dated observations (5-40x compression)
- Reflector agent triggers at 40K tokens, garbage-collects stale observations
- No vector DB, no graph store — "everything is text in context"
- Prompt caching enables 4-10x cost reduction (stable text prefix)

**Why it matters**: Simplest architecture yet highest single-model score (94.87% with gpt-5-mini on LongMemEval). Proves that careful compression alone can beat complex retrieval systems.

**Source code findings**: Observer uses temperature 0.3, thinking budget 215 tokens. Reflector has 5 compression escalation levels. Degenerate repetition detection prevents observation loops.

**Detail**: `mastra.research.md`

### Hindsight

**Approach**: Structure memory like human cognition — separate facts from experiences from opinions.

- Four memory networks: World (objective facts), Experience (personal events), Observation (inferred patterns), Opinion (deprecated in current code)
- **Tempr** (retain+recall): LLM fact extraction with 5W schema, entity resolution, four link types (semantic, temporal, causal, entity). 4-way parallel retrieval (semantic + BM25 + graph + temporal) with RRF fusion
- **MPFP** algorithm: Novel sublinear graph traversal combining meta-path patterns with Forward Push propagation
- **Cara** (reflect): Agentic loop with disposition traits (skepticism, literalism, empathy) and hierarchical retrieval (mental models > observations > raw facts)

**Why it matters**: Most technically deep system. Uses a 20B open-source model to lift accuracy from 39% to 83.6%, proving architecture matters more than model size. 91.4% with Gemini-3 Pro.

**Detail**: `hindsight.research.md`

### MemOS

**Approach**: Don't invent new memory algorithms — build an OS layer that manages all types.

- Three-layer architecture: Interface (API parsing) → Operation (MemScheduler, MemLifecycle, MemOperator) → Infrastructure (storage backends)
- **MemCube**: Standardized container with metadata (user_id, source, timestamp, importance_score, TTL)
- Three memory types:
  - **Plaintext**: Text memories with naive/general/tree backends (Neo4j tree is most advanced)
  - **Activation**: KV-cache snapshots (functional but limited to local HuggingFace models)
  - **Parametric**: LoRA weight memories (**still a stub/placeholder** — most ambitious but least implemented)
- Heavy infrastructure: Neo4j + Qdrant + Redis + MySQL

**Why it matters**: Only system that explicitly models the three pillars (text/cache/weights) in one framework. But the Parametric Memory vision — writing memories into model weights — remains unrealized.

**Detail**: `memos.research.md`

---

## Benchmark Landscape

| System | LongMemEval | LoCoMo | Model | Year |
|--------|:-----------:|:------:|-------|------|
| Supermemory ASMR (oracle) | 98.6% | — | GPT-4o × 8 | 2026 |
| **Observational Memory** | **94.87%** | — | gpt-5-mini | 2026 |
| Hindsight | 91.4% | 89.61% | Gemini-3 Pro | 2025-12 |
| Supermemory (production) | 81.6% | — | — | 2026 |
| Mem0 | — | ~58% | — | 2025 |

Note: Benchmark numbers are self-reported and methodologies vary. ASMR's 98.6% uses oracle evaluation. Direct comparison across systems requires caution.

---

## Emerging Patterns

### Pattern 1: Compression Is Becoming a First-Class Memory Strategy

In 2025, compression (compaction) was an emergency measure for context overflow. In 2026, Observational Memory proves it can be the **entire memory architecture** — and beat retrieval-based systems on benchmarks.

### Pattern 2: LLM-as-Retriever Replacing Vector Search

Both Supermemory ASMR and Hindsight's Cara use LLM reasoning for retrieval instead of (or alongside) embedding similarity. The tradeoff: better semantic understanding vs higher cost per query.

### Pattern 3: Cognitive Architecture Emerging

Hindsight's four-network model (facts/experiences/observations/opinions) and MemOS's three memory types (text/cache/weights) both try to model memory **the way humans think about memory**, not just as a key-value store.

### Pattern 4: The Weight-Writing Frontier Remains Unrealized

MemOS is the only system that explicitly attempts Parametric Memory (LoRA weight updates). It's still a stub. The gap between "external memory" and "learned memory" identified in our findings remains wide.

---

## Updated Technology Landscape (2025 → 2026 Q1)

| Dimension | 2025 State | 2026 Q1 State |
|-----------|-----------|---------------|
| **Primary storage** | Vector DB (Qdrant, Chroma, pgvector) | Shifting: plain text in context, graph, or no persistent store |
| **Retrieval** | Embedding similarity (RAG) | Diversifying: LLM reasoning, graph traversal, pure compression |
| **Compression** | Emergency compaction only | First-class strategy (Observational Memory) |
| **Cognitive modeling** | Flat fact lists (Mem0) | Structured networks (Hindsight 4-network, MemOS 3-type) |
| **Weight updates** | Not attempted | Attempted but not realized (MemOS LoRA stub) |
| **Benchmark SOTA** | ~80% LongMemEval | ~95% LongMemEval (single model, non-oracle) |
| **Cost efficiency** | High (multiple LLM calls + embedding) | Improving (Mastra: 10x reduction via prompt caching) |

---

## References

- [Supermemory ASMR blog](https://blog.supermemory.ai/we-broke-the-frontier-in-agent-memory-introducing-99-sota-memory-system/)
- [Observational Memory research](https://mastra.ai/research/observational-memory)
- [Hindsight paper (arxiv 2512.12818)](https://arxiv.org/abs/2512.12818)
- [MemOS paper (arxiv 2507.03724)](https://arxiv.org/abs/2507.03724)
- [5 Memory Systems Compared](https://dev.to/varun_pratapbhardwaj_b13/5-ai-agent-memory-systems-compared-mem0-zep-letta-supermemory-superlocalmemory-2026-benchmark-59p3)
