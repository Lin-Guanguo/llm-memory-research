# Cross-Domain Findings: Memory × Context

Last Updated: 2026-03-23

Findings from studying memory implementations (8 projects) and context management (7 agents) in LLM systems.

---

## Framework: Three Pillars of LLM Information Management

Memory and context are not separate problems — they are the same problem at different time scales. Context is "memory within a conversation"; memory is "context across conversations." Compaction generates summaries that are functionally identical to memory extraction.

All mechanisms studied across both domains reduce to **three fundamental pillars**:

### Pillar 1: Compression

Reduce information to fit constraints. Necessary because context windows are finite and attention degrades with length (context rot).

| Approach | Mechanism | Examples |
|----------|-----------|---------|
| **Programmatic removal** | Rule-based truncation, no LLM involved | Codex per-item truncation (10KB limit), OpenCode `prune()` (erase old tool outputs) |
| **Tool result clearing** | Remove raw results of past tool calls | Claude Code `context_editing` API, Gemini CLI reverse token budget |
| **LLM summarization** | Generate compressed summary when approaching threshold | All agents' compaction (Pi 6-section, Claude Code 9-section, Gemini CLI with verification probe) |
| **Hierarchical compression** | Multi-level: recent → detailed, old → summary, very old → facts | Memory systems (Mem0 extracts facts, Letta's three-tier Core/Recall/Archival) |

### Pillar 2: Retrieval

Select relevant information from a larger pool and inject into context. Necessary because not all stored information is relevant to the current task.

| Approach | When loaded | Examples |
|----------|-------------|---------|
| **Preload everything** | Session start, fixed cost | ChatGPT Memory (33 facts always injected), Pi (full history every call) |
| **Preload important + JIT rest** | Hybrid: important at start, details on demand | Claude Code (CLAUDE.md preloaded + glob/grep on demand), Gemini CLI (GEMINI.md + tools) |
| **On-demand only** | When model decides to search | Claude Memory (`conversation_search` tool), vector search (Qdrant/Chroma) |
| **Per-node filtering** | Per LLM call, tag-based | Self-developed workflow agent (context_filter: Full/Cap-restricted/None per capability) |
| **Hierarchical retrieval** | Top-level first, drill down | Claude Code memory (MEMORY.md first 200 lines preloaded, deeper content via memory_search/memory_get) |

Current trend: **Hybrid** (preload + JIT) is the dominant approach. Preload everything doesn't scale; pure JIT is too aggressive and risks missing information.

### Pillar 3: Continuous Learning (Unexplored)

Write knowledge into model weights so it persists without external storage. This would eliminate the need for external memory systems entirely.

| Status | Details |
|--------|---------|
| **Academic research** | Continual learning, catastrophic forgetting mitigation (LoRA, self-distillation, rehearsal) |
| **Production reality** | No coding agent does this. All use external memory (Pillar 1 + 2) instead of weight updates |
| **Blockers** | Catastrophic forgetting, compute cost, no standard methodology for per-user adaptation |
| **Future direction** | May converge with memory — e.g., accumulate external memories, then periodically batch-write into weights via fine-tuning |

The most effective systems combine Pillar 1 and 2: **compress what's old, retrieve what's relevant**. Pillar 3 remains a research frontier.

---

## Detailed Findings

## Finding 1: Memory and Context Are the Same Problem at Different Time Scales

Memory (cross-session) and context (within-session) face identical challenges:

| Challenge | Memory | Context |
|-----------|--------|---------|
| What to keep | Fact extraction (Mem0), entity tracking (Zep) | Compaction summary (all agents) |
| What to discard | Conflict resolution, outdated facts | Old tool outputs, resolved errors |
| How to compress | LLM summarization, knowledge graph | LLM summarization, structured templates |
| How to retrieve | Vector search, graph traversal, pre-injection | Full context, filtering, token budgeting |

Compaction IS memory creation. When Claude Code generates a 9-section summary during compaction, it's creating a "memory" of the conversation. When Mem0 extracts facts from a conversation, it's "compacting" the conversation into durable storage.

**Implication**: Techniques from one domain likely transfer to the other. Graph-based memory (Graphiti) has no equivalent in context management yet. Proactive compression from context (self-developed workflow agent's per-node summary) has no equivalent in memory yet.

## Finding 2: Two Philosophies Appear in Both Domains

**"Give everything, trust the model"**
- Memory: ChatGPT pre-injects all 33 facts every conversation
- Context: Pi sends full history every LLM call

**"Curate aggressively, minimize noise"**
- Memory: Claude retrieves on-demand via `conversation_search`
- Context: OpenClaw's multi-stage pipeline, self-developed workflow agent's per-node context_filter

Neither philosophy is strictly better. The "trust the model" approach is simpler to implement and works well with large context windows. The "curate" approach scales better but adds engineering complexity and risks filtering out relevant information.

As context windows grow (1M+ tokens), the balance shifts toward "trust the model" for context management. But context rot (accuracy degradation with length) pushes back toward curation. This tension is unresolved.

## Finding 3: Compression Quality Is the Shared Unsolved Problem

Every system that compresses information risks losing something critical.

**Memory side**:
- Mem0's fact extraction can lose nuance ("user prefers Python" loses the context of *why*)
- Letta's self-editing memory can drift from the original facts over many updates
- Graphiti's knowledge graph preserves relationships but may miss implicit context

**Context side**:
- Pi's single-pass summary has no verification — information loss is silent
- Gemini CLI adds a second LLM "probe" call to catch omissions (only agent to do this)
- Claude Code uses 9 structured sections to ensure coverage, but doesn't verify
- Codex's encrypted server-side compaction preserves latent model state, but is opaque

No system has a reliable way to know what was lost during compression. Gemini CLI's probe is the closest attempt, but it doubles the cost.

## Finding 4: Structured vs Narrative Is a Fundamental Split

Memory research found three forms: structured facts (Mem0), narrative text (Letta), relationship graphs (Graphiti).

Context research found the same split: all mainstream agents use a single narrative channel (conversation messages), while self-developed workflow agent separates structured data (Ports) from narrative context (ContextMessages).

In mainstream agents, structured data (JSON tool results, code snippets, file contents) is forced into the narrative conversation format. This wastes tokens and makes extraction harder for the model. The dual-channel approach addresses this but adds architectural complexity.

**Implication**: The industry-standard "everything is a message" approach may be fundamentally wasteful for structured workflows. As agent tasks become more complex (multi-step, multi-tool), pressure to separate channels will increase.

## Finding 5: Server-Side Processing Is the Trend

Both domains are moving computation server-side:

| Era | Memory | Context |
|-----|--------|---------|
| Early | Client-side vector DB (Chroma, Qdrant) | Client-side compaction (Pi, Gemini CLI) |
| Current | Cloud memory services, API-integrated | Server-side compaction API (Claude Code `compact-2026-01-12`, Codex `/responses/compact`) |
| Emerging | Model-native memory (ChatGPT built-in) | Model-native context awareness (Claude `<budget:token_budget>`) |

The endpoint is likely **model-native**: the model itself manages both memory and context, with the harness providing only raw inputs. Claude's context awareness (model knows its remaining token budget) is a step in this direction.

## Finding 6: Sub-Agents Are a Context Strategy, Not Just a Feature

Sub-agents appear in context research as a practical solution to context overflow: give a focused task its own clean context window, return a compressed summary.

This is the same pattern as memory extraction: take raw experience, distill it into a compact representation, store only the distillation.

| Pattern | Memory equivalent | Context equivalent |
|---------|------------------|-------------------|
| Extract and store | Mem0 fact extraction | Sub-agent returns summary |
| Full vs compressed | Raw conversation vs facts | Full tool output vs summary_exchange |
| Selective retrieval | Vector search top-k | context_filter per node |

**Implication**: Designing sub-agent boundaries is fundamentally a compression design problem — what information should cross the boundary, and in what form.

## Finding 7: Knowledge Graphs Are Unexplored in Context

Memory research identified Graphiti's bi-temporal knowledge graph as the 2025 breakthrough (21.2k GitHub stars). It tracks entities, relationships, and temporal validity.

In context management, **no agent uses graph structures**. All use linear message arrays + text summaries. No one tracks:
- Causal relationships between tool calls
- How user intent evolves during a conversation
- Dependencies between code modifications

This is a potential research direction: could graph-based context representation produce better compression than linear summaries? The information exists (tool A's output fed into tool B's input), but it's flattened into text when it enters the context.

## Finding 8: No One Validates Prompt Placement Empirically

All studied agents use simple prompt placement strategies (system prompt at start, everything else in messages). None run A/B tests on:
- Whether rules in system prompt vs user message affect output quality
- Whether message ordering within context affects task completion
- Whether filtering context (OpenClaw/self-developed workflow agent) improves or degrades performance vs sending everything (Pi)

The AI Muse 18-model benchmark is the closest empirical work, and it only tested constraint compliance, not agent task performance. This is a gap in the field.

## Finding 9: Both Domains Reduce to Two Fundamental Operations — Compression and Retrieval

Every mechanism studied in both memory and context can be classified as either **compression** (reduce information to fit constraints) or **retrieval** (select relevant information from a larger pool).

| | Compression | Retrieval |
|--|-------------|-----------|
| **Memory** | Mem0 fact extraction, Letta self-editing, ChatGPT pre-computed summaries | Claude `conversation_search`, vector search (Qdrant/Chroma), Graphiti graph traversal |
| **Context** | Compaction (all agents), tool output truncation/summarization, summary_exchange | OpenClaw `assemble(tokenBudget)`, self-developed workflow agent context_filter, sub-agent targeted exploration |

Each system is a different mix of the two:

- **Compression-heavy**: Pi (send everything, compact when full), ChatGPT Memory (pre-compress 33 facts, always inject)
- **Retrieval-heavy**: Claude Memory (on-demand search, no pre-injection), Graphiti (graph traversal for relevant entities)
- **Balanced**: OpenClaw (filter + assemble + compact), Claude Code (server-side compact + sub-agent exploration), self-developed workflow agent (per-node filter + proactive summary)

Core tradeoff:
- **Compression**: Information is irreversibly lost, but context stays small and cost is low
- **Retrieval**: Information is preserved, but requires indexing/query infrastructure and may miss relevant items

This framing suggests that advancing either domain means improving one of two things: better compression (lose less during summarization) or better retrieval (find more relevant information with less noise). The most effective systems will combine both — compress what's old, retrieve what's relevant.

## Finding 10: Text Search Dominates Over RAG in Practice

Despite the hype around RAG (Retrieval-Augmented Generation) and vector databases, **no coding agent uses RAG in its core agentic loop**. All 7 studied agents rely on text search:

| Agent | Search tool | Method |
|-------|-----------|--------|
| Claude Code | `glob`, `grep`, `Read` | File pattern matching + regex |
| Codex | `rg` (ripgrep) | Regex text search |
| OpenCode | ripgrep | Regex text search |
| Gemini CLI | built-in grep/glob | File pattern + regex |
| Pi | `grep`, `find` | Standard unix tools |
| OpenClaw | inherited from Pi | Same |
| Self-developed agent | N/A (data via ports) | Structured port bindings |

Anthropic calls this "Agentic Search" — but the underlying mechanism is `glob` + `grep`, not embedding similarity.

### Why text search wins in coding agents

| Factor | Text search (grep/glob) | RAG (vector search) |
|--------|------------------------|-------------------|
| **Index cost** | Zero — scan on demand | High — must compute embeddings upfront |
| **Latency** | ripgrep: milliseconds on large codebases | Vector query: faster, but index must exist |
| **Precision** | Exact — find exactly `handleAuth` | Fuzzy — may return semantically similar but wrong results |
| **Explainability** | You know why it matched | Opaque similarity score |
| **Staleness** | Always current (reads live files) | Index can be stale after edits |

### Where RAG does appear

RAG is used in the **memory** layer (cross-session retrieval), not the context layer (within-session search):

| Scenario | Best method | Why |
|----------|-----------|-----|
| Find a function in codebase | Text search | Exact identifier match, zero index cost |
| Find relevant past conversation | Vector search (RAG) | Natural language, semantic matching needed |
| Find user preferences in memory | Text search may suffice | Short structured facts, keyword matching works |
| Find related documentation | Vector search (RAG) | Long natural language, semantic relevance |

### The production reality

Memory research found the same pattern: ChatGPT Memory uses pre-computed facts (no RAG at runtime), Claude Memory uses tool-based search. The vector databases studied (Qdrant, Chroma) are powerful infrastructure, but the agents that ship to millions of users chose simpler approaches.

This suggests RAG's value is in **knowledge-base retrieval** (documentation, past conversations) rather than **real-time agent operation** (finding code, executing tasks).

---

## Summary Table

| Finding | Status | Action |
|---------|--------|--------|
| Memory ≈ Context at different time scales | Established | Transfer techniques across domains |
| Two philosophies (trust vs curate) | Observed, no winner | Choice depends on context window size and task type |
| Compression quality unsolved | Universal problem | Gemini CLI's probe approach worth investigating |
| Structured vs narrative split | Emerging recognition | Dual-channel architectures may become standard |
| Server-side trend | In progress | Expect more API-native memory and context features |
| Sub-agents = compression strategy | Underrecognized | Design sub-agent boundaries as compression boundaries |
| Knowledge graphs unexplored in context | Gap | Research opportunity |
| Prompt placement unvalidated | Gap | Empirical testing needed |
| Compression + Retrieval as two fundamental ops | Framework | Use to classify and evaluate any memory/context mechanism |
| Text search dominates over RAG in practice | Observed | RAG for knowledge bases; text search for real-time agent operation |
