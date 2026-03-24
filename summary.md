# LLM Agent Information Management: Research Summary

Last Updated: 2026-03-24

<!--
编写原则：
1. 只写洞察，不复述实现 — 架构细节通过 link 到 *.research.md 解决
2. 表格呈现事实，正文提炼观点 — 正文只写表格看不出来的判断和趋势
3. 每个 section 有且只有一个核心论点
4. 避免跨 Part 重复 — 同一观点只在最合适的位置出现一次，其他地方用 (见 §X.X) 引用
5. link 代替展开 — 超过 2 句话的细节就应该是一个 link
-->

A synthesis of research across 20+ projects studying how LLM agents manage information — from memory frameworks and context management to the frontier of continuous learning.

---

## 0. Two Analytical Angles

This research examines LLM agent information management from two complementary angles.

### Angle 1: Three Methods — How Agents Handle Information

| Method | What it does | Maturity |
|--------|-------------|----------|
| **Compression** | Reduce information to fit constraints — summarization, fact extraction, truncation | Production-ready, universally deployed |
| **Retrieval** | Select relevant information from a larger pool — vector search, text search, graph traversal | Production-ready, approaches vary widely |
| **Learning** | Write knowledge into model weights so it persists without external storage | Research frontier, no production deployment |

### Angle 2: Three Directions — Where Agents Apply These Methods

| Direction | Time scale | Research status |
|-----------|-----------|-----------------|
| **Memory** | Cross-session — persist knowledge between conversations | 15 projects studied |
| **Context** | Within-session — manage the context window during a conversation | 7 agents + Anthropic guidance studied |
| **Learning** | Post-deployment — adapt model weights after training | Plan written, not started |

Part 1-3 follows the three directions. Part 4 discusses cross-domain findings visible only when studying memory and context together.

---

## 1. Memory: Persisting Knowledge Across Conversations

### 1.1 Consumer Product Memory: Two Philosophies

Reverse engineering of ChatGPT and Claude reveals two opposing approaches. ([ChatGPT details](./reverse-engineer/chatgpt-memory-reverse-engineering.md) | [Claude details](./reverse-engineer/claude-memory-reverse-engineering.md))

| | ChatGPT | Claude |
|--|---------|--------|
| **Strategy** | Pre-inject everything | Retrieve on demand |
| **Mechanism** | 33 pre-computed facts + recent chat summaries, always in context | `conversation_search` and `recent_chats` tools, invoked when needed |
| **Trade-off** | Fixed token cost, automatic continuity | Variable cost, risk of missing relevant info |

Neither uses vector databases or RAG at runtime — both rely on simpler approaches than expected.

### 1.2 Memory Frameworks: Two Generations

#### Generation 1 (2024-2025): Foundational Approaches

| Framework | Core idea | What makes it different | Production adoption |
|-----------|-----------|------------------------|-------------------|
| [**Mem0**](./mem0.research.md) | LLM-driven fact CRUD | LLM decides ADD/UPDATE/DELETE on atomic facts; dual storage (vector + graph) | AWS Agent SDK official provider |
| [**Letta**](./letta.research.md) | Three-tier self-editing memory | Agent writes to its own prompt (Core/Recall/Archival); active, not passive | 11x sales AI, Kognitos |
| [**Graphiti**](./graphiti.research.md) | Bi-temporal knowledge graph | Temporal validity on entities and relationships; graph traversal retrieval | Zep AI (YC), 21.2k stars |

Key differentiator from traditional RAG: all three use **active memory management** — the LLM decides what to store and delete, rather than passively chunking documents. ([Production details](./production-adoption.research.md))

#### Generation 2 (2026 Q1): New Wave

| System | Core innovation | LongMemEval |
|--------|----------------|-------------|
| [**Hindsight**](./hindsight.research.md) | Four memory networks (World/Experience/Observation) + reflect operation; multi-strategy retrieval (graph + BM25 + vector) | 91.4% |
| [**Mastra OM**](./mastra.research.md) | Pure compression, **no retrieval** — Observer + Reflector agents compress everything into context | 94.87% |
| [**MemOS**](./memos.research.md) | Memory as OS resource; MemCube unifies three types (plaintext, KV-cache, weights) | N/A |
| [**Supermemory**](./supermemory.research.md) | ASMR: LLM-as-retriever replaces vector DB; 3+3 agent pipeline with ensemble voting | 98.6% (oracle) |

The generation shift reveals two key trends: **LLM-as-retriever** replacing vector search (Supermemory), and **pure compression** as a viable alternative to retrieval entirely (Mastra OM — 94.87% with zero retrieval challenges the assumption that retrieval is necessary).

### 1.3 Coding Assistant Memory

A different domain where memory means "understanding the codebase":

| Assistant | Key innovation |
|-----------|---------------|
| [**Cursor**](./cursor.research.md) | Custom embedding model trained from agent session traces |
| [**Augment**](./augmentcode.research.md) | Real-time personal index per developer; edit event streaming (+2.6% improvement) |
| [**Continue**](./continue.research.md) | BYOM architecture with content-addressed caching |

See [memory.ecosystem.md](./memory.ecosystem.md) for full market overview including vector databases (Qdrant, Chroma), graph databases, and embedding models.

---

## 2. Context: Managing the Conversation Window

### 2.1 Universal Pattern

All 7 agents studied share the same base model: ([Full comparison](./context.summary.md))

```
Messages accumulate → Threshold reached → Compress/summarize → Continue with summary
```

The differences are in **when**, **how**, and **where** compression happens.

### 2.2 Architecture Spectrum

| Agent | Key characteristic | Detail |
|-------|-------------------|--------|
| [**Pi**](./pi.research.md) | Minimal | Single LLM summary at near-limit; ~300 word system prompt; no pre-processing |
| [**Codex**](./codex-context.research.md) | Per-item truncation | 10KB limit per tool output at record time; dual compaction (server encrypted + client LLM) |
| [**Gemini CLI**](./gemini-cli.research.md) | Verified compression | LLM summary + second LLM probe to catch omissions; 50% threshold |
| [**OpenCode**](./opencode.research.md) | Two-phase | Prune old tool outputs first, then LLM summary; resumable sub-agents; fork/revert |
| [**Claude Code**](./claude-code-context.research.md) | Server-side + model-aware | API compaction with 9-section summary; model knows its remaining budget (`<budget:token_budget>`) |
| [**OpenClaw**](./openclaw.research.md) | Multi-stage pipeline | sanitize → validate → truncate → assemble; pluggable ContextEngine with 7 lifecycle hooks |

### 2.3 Key Design Patterns

These patterns reveal a common trajectory: **compression responsibility is shifting from client heuristics toward server-side APIs and model self-management**.

**Reactive → Proactive Compression** — Most agents wait until context is nearly full. Exceptions: Codex truncates per-item at entry, Gemini CLI pre-summarizes tool outputs. Earlier, lighter compression reduces the risk of a single catastrophic information loss event.

**Client-Side → Server-Side Compaction** — Claude Code (`compact-2026-01-12`) and Codex (`/responses/compact`) offload compaction to server APIs. This enables encrypted state preservation, mid-stream compaction, and simpler client implementations.

**Model Self-Management** — Claude Code's `<budget:token_budget>` makes the model aware of remaining capacity. Combined with server-side compaction, the model can self-manage without client heuristics. No other agent has this — it may represent the direction all agents converge toward.

**Context Rot** — Anthropic identifies four types of context degradation: poisoning (stale info), distraction (irrelevant info), confusion (similar info), clash (contradictory info). Most agents only address distraction. The other three are largely unmitigated. ([Anthropic guidance details](./anthropic-context-engineering.research.md))

---

## 3. Learning: Writing Knowledge Into Weights (TODO)

The third method and third research direction. Currently **no production agent** uses weight updates for personalization — all rely on external memory (compression + retrieval).

Research plan covers four directions: ([Full plan](./plan/2-learning-research.md))

| Direction | What | Status |
|-----------|------|--------|
| Academic survey | Continual learning, catastrophic forgetting, self-evolving LLMs | TODO |
| Per-user personalization | Multi-LoRA serving, Sakana Doc-to-LoRA, DoorDash production case | TODO |
| VTuber / Character AI | Neuro-sama (weight-embedded personality) vs prompt-crafted personality | TODO |
| Hybrid pipeline | Accumulate external memories → batch LoRA fine-tune → deploy | TODO (speculative) |

Key question: **Is per-user LoRA a viable middle ground between prompt injection and full fine-tuning?**

---

## 4. Cross-Domain Findings

Findings visible only when studying memory and context together. ([Full findings with 10 detailed analyses](./findings.md))

### Memory and Context Are the Same Problem at Different Time Scales

Compaction IS memory creation. When Claude Code generates a 9-section summary during compaction, it creates a "memory" of the conversation. When Mem0 extracts facts, it "compacts" the conversation into durable storage. The methods (compression, retrieval) are shared; only the time scale differs. Techniques from one domain should transfer to the other.

### Two Philosophies Appear in Both Domains

"Give everything, trust the model" (ChatGPT pre-injects all facts; Pi sends full history) vs "Curate aggressively, minimize noise" (Claude retrieves on-demand; OpenClaw's multi-stage pipeline). Neither is strictly better. As context windows grow (1M+), the balance shifts toward "trust the model" — but context rot (§2.3) pushes back. This tension is unresolved.

### Compression Quality Is the Shared Unsolved Problem

Every system that compresses — whether memory extraction (Mem0 losing nuance) or context compaction (Pi's unverified summary) — risks silent information loss. No system reliably knows what was lost. Gemini CLI's two-pass probe (§2.2) is the only verification attempt, and it doubles the cost.

### Graph Structures Are Unexplored in Context

Graphiti's bi-temporal knowledge graph is a memory breakthrough (§1.2). In context management, no agent uses graph structures — all use linear message arrays. No one tracks causal relationships between tool calls or how user intent evolves during a conversation.

### Text Search Dominates Over RAG in Agentic Loops

Every coding agent studied uses `grep`/`glob` (text search) at runtime, not vector search. Reasons: zero index cost, exact matching, always current, explainable. RAG appears in the memory layer (cross-session retrieval) but not in real-time agent operation. This suggests RAG's value is in **knowledge-base retrieval**, not **agentic execution**. ([Full analysis](./findings.md#finding-10-text-search-dominates-over-rag-in-practice))

### Sub-Agents Are a Compression Strategy

Sub-agents appear as a context management technique: give a focused task its own clean context window, return a compressed summary. This is the same pattern as memory extraction — take raw experience, distill it, store only the distillation. Designing sub-agent boundaries is fundamentally a compression design problem.

---

## 5. Open Questions

### Compression
- **Verification**: Can we build a cheaper alternative to Gemini CLI's two-pass probe?
- **Optimal threshold**: Pi compresses near the limit, Gemini CLI at 50%. Where's the optimal point?
- **Encrypted vs readable**: Codex preserves opaque model state; Claude Code produces readable 9-section text. Which loses less?

### Retrieval
- **Graph in context**: Could graph-based context representation (§4) produce better compression than linear summaries?
- **LLM-as-retriever**: Supermemory's ASMR replaces vector DB with LLM reasoning. Viable direction, or cost prohibitive?
- **Prompt placement**: No agent validates whether rules in system prompt vs user message affect quality. No A/B testing exists.

### Learning
- **Weight-based memory**: Is per-user LoRA viable? What's the update cycle and storage cost?
- **Hybrid pipeline**: Can agents accumulate external memories and periodically fine-tune them into weights?
- **Personality boundary**: At what point does fine-tuning produce something prompt engineering can't replicate?

---

## Research Materials

### Individual Project Research

| Category | Projects |
|----------|----------|
| Memory frameworks (Gen 1) | [Mem0](./mem0.research.md), [Letta](./letta.research.md), [Graphiti](./graphiti.research.md) |
| Memory frameworks (Gen 2) | [Hindsight](./hindsight.research.md), [Mastra OM](./mastra.research.md), [MemOS](./memos.research.md), [Supermemory](./supermemory.research.md) |
| Vector databases | [Qdrant](./qdrant.research.md), [Chroma](./chroma.research.md) |
| Coding assistants | [Cursor](./cursor.research.md), [Augment](./augmentcode.research.md), [Continue](./continue.research.md) |
| Context management | [Pi](./pi.research.md), [OpenClaw](./openclaw.research.md), [Gemini CLI](./gemini-cli.research.md), [Claude Code](./claude-code-context.research.md), [Codex](./codex-context.research.md), [OpenCode](./opencode.research.md) |
| Reverse engineering | [ChatGPT Memory](./reverse-engineer/chatgpt-memory-reverse-engineering.md), [Claude Memory](./reverse-engineer/claude-memory-reverse-engineering.md) |
| Official guidance | [Anthropic Context Engineering](./anthropic-context-engineering.research.md) |

### Summary Documents

| Document | Scope |
|----------|-------|
| [findings.md](./findings.md) | Cross-domain findings (10 findings, detailed analysis) |
| [context.summary.md](./context.summary.md) | Context management comparison (6 agents, patterns, open questions) |
| [memory.summary.md](./memory.summary.md) | Memory research summary (Phase 1: 2025-12) |
| [memory.ecosystem.md](./memory.ecosystem.md) | Market overview (GitHub stars, funding, selection guides) |

### Plans

| Document | Status |
|----------|--------|
| [plan/1-context-research.md](./plan/1-context-research.md) | Completed |
| [plan/2-learning-research.md](./plan/2-learning-research.md) | TODO (4 research directions planned) |
| [plan/3-memory-update.md](./plan/3-memory-update.md) | Research done, summary pending |
