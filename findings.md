# Cross-Domain Findings: Memory × Context

Last Updated: 2026-03-19

Findings from studying memory implementations (8 projects) and context management (6 agents) in LLM systems.

---

## Finding 1: Memory and Context Are the Same Problem at Different Time Scales

Memory (cross-session) and context (within-session) face identical challenges:

| Challenge | Memory | Context |
|-----------|--------|---------|
| What to keep | Fact extraction (Mem0), entity tracking (Zep) | Compaction summary (all agents) |
| What to discard | Conflict resolution, outdated facts | Old tool outputs, resolved errors |
| How to compress | LLM summarization, knowledge graph | LLM summarization, structured templates |
| How to retrieve | Vector search, graph traversal, pre-injection | Full context, filtering, token budgeting |

Compaction IS memory creation. When Claude Code generates a 9-section summary during compaction, it's creating a "memory" of the conversation. When Mem0 extracts facts from a conversation, it's "compacting" the conversation into durable storage.

**Implication**: Techniques from one domain likely transfer to the other. Graph-based memory (Graphiti) has no equivalent in context management yet. Proactive compression from context (Dayfold's per-node summary) has no equivalent in memory yet.

## Finding 2: Two Philosophies Appear in Both Domains

**"Give everything, trust the model"**
- Memory: ChatGPT pre-injects all 33 facts every conversation
- Context: Pi sends full history every LLM call

**"Curate aggressively, minimize noise"**
- Memory: Claude retrieves on-demand via `conversation_search`
- Context: OpenClaw's multi-stage pipeline, Dayfold's per-node context_filter

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

Context research found the same split: all mainstream agents use a single narrative channel (conversation messages), while Dayfold separates structured data (Ports) from narrative context (ContextMessages).

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
- Whether filtering context (OpenClaw/Dayfold) improves or degrades performance vs sending everything (Pi)

The AI Muse 18-model benchmark is the closest empirical work, and it only tested constraint compliance, not agent task performance. This is a gap in the field.

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
