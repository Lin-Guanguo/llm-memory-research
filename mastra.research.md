# Mastra Observational Memory Research Report

Last Updated: 2026-03-24

> **Research Methodology**: Sections 1-14 were generated through web research of official Mastra documentation, research pages, blog posts, third-party coverage, and community discussions. Section 15 was produced by reading the Mastra monorepo source code (`packages/memory/src/processors/observational-memory/`).

## Sources

- [Mastra Docs: Observational Memory](https://mastra.ai/docs/memory/observational-memory) (accessed: 2026-03-24)
- [Mastra Research: 95% on LongMemEval](https://mastra.ai/research/observational-memory) (accessed: 2026-03-24)
- [Mastra Blog: Announcing Observational Memory](https://mastra.ai/blog/observational-memory) (accessed: 2026-03-24)
- [VentureBeat: Observational memory cuts AI agent costs 10x](https://venturebeat.com/data/observational-memory-cuts-ai-agent-costs-10x-and-outscores-rag-on-long) (accessed: 2026-03-24)
- [The Decoder: Traffic light emojis for efficient compression](https://the-decoder.com/mastras-open-source-ai-memory-uses-traffic-light-emojis-for-more-efficient-compression/) (accessed: 2026-03-24)
- [DEV Community: 4 Architectures Racing to Fix Agent Memory](https://dev.to/ai_agent_digest/your-ai-agents-memory-is-broken-here-are-4-architectures-racing-to-fix-it-55j1) (accessed: 2026-03-24)
- [TechBuddies: How Mastra Beats RAG](https://www.techbuddies.io/2026/02/12/how-mastras-observational-memory-beats-rag-for-long-running-ai-agents/) (accessed: 2026-03-24)
- [Hacker News: Ask HN: Views on Mastra's SOTA Memory?](https://news.ycombinator.com/item?id=46992444) (accessed: 2026-03-24)
- [GitHub Issue #13470: Observational Memory + Adaptive Thinking](https://github.com/mastra-ai/mastra/issues/13470) (accessed: 2026-03-24)

---

## Overview

**Mastra Observational Memory (OM)** is a text-based, dual-agent memory system for long-context agentic applications. Instead of storing raw conversation history or using vector-database retrieval, OM compresses messages into a structured observation log that lives entirely in the LLM context window. Two background agents — an **Observer** and a **Reflector** — continuously monitor conversations and maintain this log, replacing raw message history as it grows.

Key claims:
- **94.87% on LongMemEval** (gpt-5-mini) — highest recorded score on this benchmark by any system
- **4-10x cost reduction** via prompt caching (observations form a stable, cacheable prefix)
- **No vector database, no graph store** — "everything is text in context"
- **Open source** as part of the Mastra framework (`@mastra/memory` package)

---

## 1. Core Architecture

### Two-Block Context Structure

OM divides the agent's context window into two blocks:

```
┌─────────────────────────────────────────────────────┐
│  System Prompt                                       │
├─────────────────────────────────────────────────────┤
│  Block 1: Observations (compressed, stable prefix)   │  ← Cacheable
│  - Reflections (condensed observations)              │
│  - Observations (dated event log)                    │
├─────────────────────────────────────────────────────┤
│  Block 2: Recent Messages (raw, growing)             │  ← Active conversation
└─────────────────────────────────────────────────────┘
```

The design enables **prompt caching**: Block 1 is append-only and stable between turns, so the prefix (system prompt + observations) achieves full cache hits on every turn. Only during infrequent reflection cycles is the cache invalidated.

### Three-Tier Hierarchy

1. **Recent messages** — Exact conversation history for current tasks
2. **Observations** — Compressed notes from the Observer about what occurred
3. **Reflections** — Further-condensed observations when the observation log grows too long

### Dual-Agent Process

```
Messages accumulate → [30K tokens] → Observer compresses → Observations grow → [40K tokens] → Reflector condenses
     (raw)                                 (5-40x smaller)                          (further condensed)
```

---

## 2. Observer Agent

**Purpose**: Watches conversations and produces dated, prioritized observations when message history exceeds the token threshold.

**Trigger**: Activates when raw message tokens exceed **30,000 tokens** (configurable via `observation.messageTokens`).

**What it tracks**:
- Specific events, decisions, and state changes
- Current task the agent is performing
- Suggested response for continuity
- Optional thread titles when conversation topics shift

**Compression ratios**:
- Text-only content: **3-6x** compression (approximately 6x in LongMemEval runs)
- Tool-call-heavy workloads: **5-40x** compression (e.g., a Playwright MCP page snapshot of 50K+ tokens compresses to a few hundred tokens of observations)

**Multimodal handling**: Maintains readable placeholders for attachments (e.g., `[Image #1: reference-board.png]`, `[File #1: floorplan.pdf]`) while forwarding actual attachment parts.

**Context optimization**: `observation.previousObserverTokens` can tail-truncate the observation history passed to the Observer, reducing costs on very long conversations while maintaining task/response metadata for orientation.

### Observation Format

Observations use a structured, human-readable text format with emoji-based priority and temporal anchoring:

```
Date: 2026-01-15
- 🔴 12:10 User is building a Next.js app with Supabase auth, due in 1 week (meaning January 22nd 2026)
  - 🔴 12:10 App uses server components with client-side hydration
  - 🟡 12:12 User asked about middleware configuration for protected routes
  - 🔴 12:15 User stated the app name is "Acme Dashboard"
```

**Priority levels** (repurposed software logging levels as emojis that LLMs parse effectively):
- 🔴 **Red**: Critical information
- 🟡 **Yellow**: Potentially relevant
- 🟢 **Green**: Pure context / informational

**Three-date temporal model** (critical for temporal reasoning in benchmarks):
- **Observation date**: When the observation was created
- **Referenced date**: Date mentioned in the content
- **Relative date**: Computed offset from observation date

---

## 3. Reflector Agent

**Purpose**: Garbage-collects and condenses observations when they exceed their own threshold.

**Trigger**: Activates when observation tokens exceed **40,000 tokens** (configurable via `reflection.observationTokens`).

**Operations**:
- Combines related observation items
- Reflects on patterns
- Removes observations that have been superseded
- Produces a condensed summary layer

**Background processing**: Runs asynchronously via `reflection.bufferActivation` (default 0.5) when observations reach 50% of the reflection threshold.

---

## 4. Token Budget System

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `observation.messageTokens` | 30,000 | Threshold to trigger Observer |
| `reflection.observationTokens` | 40,000 | Threshold to trigger Reflector |
| `observation.bufferTokens` | 0.2 (20% of messageTokens) | Background buffering frequency (~6K tokens with defaults) |
| `observation.bufferActivation` | 0.8 | Aggressiveness of message clearing upon activation |
| `observation.blockAfter` | 1.2x messageTokens | Safety synchronous threshold (36K with defaults) |
| `reflection.blockAfter` | 1.2x observationTokens | Safety synchronous threshold |

**Token counting**: Uses fast local estimation via `tokenx` for text, with provider-aware heuristics for multimodal content. Per-part estimates are cached in `part.providerMetadata.mastra` and reused when cache version/tokenizer match.

### Async Buffering Mechanism

Enabled by default to prevent agent pauses during observation:

1. As conversations grow, background Observer calls run at regular intervals (~every 6K tokens with defaults)
2. Each call produces "chunks" of buffered observations stored separately
3. When message tokens reach the threshold, buffered chunks activate instantly
4. Corresponding raw messages are removed from context without blocking

**Safety mechanism**: If agents produce messages faster than the Observer processes them, `blockAfter` (1.2x) forces synchronous observation as a last resort while preserving a minimum remaining context.

---

## 5. Scopes

### Thread Scope (Default, Recommended)

Each thread maintains separate observations. Well-tested for general-purpose and long-horizon agentic use cases.

### Resource Scope (Experimental)

Observations shared across all threads for a resource (typically a user), enabling cross-conversation memory. Caveats: unobserved messages across all threads are processed together (can be slow), and the system prompt may need tweaking to prevent one thread from continuing another's work.

---

## 6. Retrieval Mode (Experimental)

Normal OM is lossy — compression removes original wording. Retrieval mode preserves access to raw messages by:

- Storing `range` metadata (`startId:endId`) on each observation group
- Registering a `recall` tool agents can call to page through raw messages behind any range
- Supporting detail levels, part indexing, pagination, and token limiting

Only active for thread-scoped OM.

---

## 7. Benchmark Results: LongMemEval

| System | Model | Score | Notes |
|--------|-------|-------|-------|
| **Mastra OM** | gpt-5-mini | **94.87%** | Highest recorded score by any system |
| **Mastra OM** | gemini-3-pro | **93.27%** | 9-point gain over gpt-4o |
| **Mastra OM** | gpt-4o | **84.23%** | Beats oracle (82.4%) by 2 points |
| Oracle baseline | gpt-4o | 82.40% | Given only answer-containing conversations |
| Supermemory | — | 81.60% | Previous SOTA |
| Mastra RAG | gpt-4o | 80.05% | topK=20 |
| Hindsight | — | ~80.7% | Four parallel retrieval strategies + neural reranking |
| Zep | — | 71.20% | Knowledge graph approach |

**Per-category highlights (gpt-5-mini)**:
- Knowledge-update: 96.2%
- Temporal-reasoning: 95.5%
- Single-session-preference: 100%
- Multi-session categories: 87.2% (tied with existing systems — the weakest area)

**Average context window** during benchmark: ~30K tokens.

**Key insight**: OM uses a single pass with a stable context window, while competitors like Hindsight require multi-stage retrieval with neural reranking.

---

## 8. Cost Analysis

### Prompt Caching Advantage

The core economic argument: OM's append-only, stable prefix maximizes prompt cache hit rates.

| Phase | Cache behavior |
|-------|---------------|
| Normal turns (between observations) | Full cache hit — prefix unchanged |
| After Observer appends | Partial cache hit — most prefix unchanged |
| After Reflector rewrites | Cache invalidated — infrequent |

Provider prompt caching reduces token costs by **4-10x** for repeated prefixes. Since OM keeps the prefix stable across most turns, the effective cost reduction is substantial.

### vs. RAG Systems

RAG performs fresh retrieval each turn, producing an unstable prefix that cannot be cached. OM's compression eliminates retrieval entirely, and the stable prefix enables caching. Combined with 5-40x compression of tool-heavy outputs, the claimed total cost reduction is **up to 10x**.

### Background Agent Overhead

The Observer and Reflector agents themselves incur compute costs for their LLM calls. The system recommends fast, cheap models (default: `google/gemini-2.5-flash`; also tested with `openai/gpt-5-mini`, `anthropic/claude-haiku-4-5`, `deepseek/deepseek-reasoner`).

---

## 9. Configuration & Usage

### Basic Setup

```typescript
import { Memory } from '@mastra/memory'
import { Agent } from '@mastra/core/agent'

const agent = new Agent({
  name: 'my-agent',
  instructions: 'You are a helpful assistant.',
  model: 'openai/gpt-5-mini',
  memory: new Memory({
    options: {
      observationalMemory: true,  // Uses default google/gemini-2.5-flash
    },
  }),
})
```

### Custom Model & Token Budgets

```typescript
const memory = new Memory({
  options: {
    observationalMemory: {
      model: 'google/gemini-2.5-flash',
      observation: {
        messageTokens: 30_000,
        bufferTokens: false,       // Disable async buffering (use synchronous)
      },
      reflection: {
        observationTokens: 40_000,
      },
      scope: 'thread',            // Default; 'resource' for cross-thread
      retrieval: true,            // Enable raw message recall (experimental)
    },
  },
})
```

### Storage Requirements

Only three database adapters supported: `@mastra/pg`, `@mastra/libsql`, `@mastra/mongodb`. No vector database needed.

---

## 10. Design Philosophy: "Everything Is Text in Context"

OM deliberately rejects:
- **Vector databases**: No embedding, no similarity search, no retrieval pipeline
- **Knowledge graphs**: No entity extraction, no relationship tracking
- **Structured objects**: Observations are formatted text, not JSON/structured data

The rationale:
1. **Text is the universal interface** — LLMs process text natively; structured formats add translation overhead
2. **Append-only text enables caching** — stable prefixes maximize prompt cache hits
3. **No retrieval means no retrieval failures** — RAG systems depend on embedding quality and similarity thresholds
4. **Simpler infrastructure** — standard SQL databases (Postgres/LibSQL/MongoDB) replace vector DB + embedding pipeline

This contrasts sharply with mem0 (LLM-driven CRUD on atomic facts), Graphiti (bi-temporal knowledge graph), and Zep (temporal entity graphs).

---

## 11. Comparison with Other Memory Systems

| Feature | Mastra OM | mem0 | Letta (MemGPT) | Graphiti/Zep | RAG (generic) |
|---------|-----------|------|-----------------|--------------|----------------|
| **Storage** | Text in context | Vector + graph | Three-tier (Core/Recall/Archival) | Temporal knowledge graph | Vector DB |
| **Compression** | Observer agent (5-40x) | LLM fact extraction | Agent self-editing | Graph construction | Chunk + embed |
| **Retrieval** | None (in-context) | Vector similarity + graph traversal | Agent-initiated tool calls | Graph traversal | Embedding similarity |
| **Vector DB required** | No | Yes | Yes | Yes (Neo4j/similar) | Yes |
| **Prompt caching** | Excellent (stable prefix) | Poor (dynamic retrieval) | Moderate | Poor | Poor |
| **LongMemEval (gpt-4o)** | 84.23% | — | — | 71.20% (Zep) | 80.05% |
| **Cross-session** | Experimental (resource scope) | Yes (user_id scoping) | Yes (archival memory) | Yes (temporal graph) | Yes |
| **Update mechanism** | Lossy compression (append + condense) | Active CRUD (ADD/UPDATE/DELETE) | Agent-driven edits | Graph mutation | Append-only |
| **Best for** | Long-running single-agent sessions | User personalization | Stateful agents with self-editing | Complex entity relationships | Document retrieval |

### vs. Traditional Compaction/Summarization

OM is NOT standard summarization. Key differences:

| Aspect | Standard Compaction | Observational Memory |
|--------|-------------------|---------------------|
| Output format | Prose summary ("documentation-style narrative") | Event-based decision log (dated, prioritized bullets) |
| Granularity | Captures gist, loses specifics | Preserves specific events, decisions, state changes |
| Frequency | Bulk (when approaching limit) | Incremental (~every 30K tokens, with async buffering) |
| Temporal info | Usually lost | Three-date model (observation/referenced/relative) |
| Priority info | None | Emoji-based priority (🔴/🟡/🟢) |

---

## 12. Limitations & Criticisms

### Acknowledged Limitations

1. **Lossy compression**: Compression inherently drops details that might become important later. No semantic faithfulness validation — the Reflector triggers on token thresholds, not content quality.

2. **Multi-session weakness**: LongMemEval multi-session categories scored 87.2%, only tying existing systems. Cross-conversation synthesis remains challenging.

3. **Incompatibility with some models**: Cannot use Anthropic Claude 4.5 models as Observer or Reflector agents (as of March 2026).

4. **Integration conflicts**: Known issue with Anthropic's adaptive thinking feature — the agent can lose track of conversation state, assume it has already responded, or make confused context statements (GitHub issue #13470).

5. **Resource scope immaturity**: Cross-thread observation processing can be slow for users with many existing threads.

### Community Criticisms (Hacker News)

From [HN thread](https://news.ycombinator.com/item?id=46992444):

- **Benchmark-tuned, not production-proven**: "The implementation appears heavily tuned toward performing well on LongMemEval" but doesn't guarantee robust production behavior.
- **Context compression, not true memory**: Functionally closer to context management optimized for single tasks than genuine long-term memory.
- **Memory drift risk**: Observer prompts may create incorrect inferences (e.g., assuming actions completed based on elapsed time).
- **Recency bias**: Emphasizes recent information while gradually compressing away older but still important details.
- **Limited grounding**: No mechanism to trace observations back to raw message evidence, making error detection harder (partially addressed by experimental retrieval mode).
- **Industry confusion**: "The industry can't seem to decide on what 'memory' even means" — memory benchmarks are inadequate for evaluating production systems.

---

## 13. Positioning in the Memory Landscape

OM occupies a unique position: it rejects the infrastructure complexity of vector/graph approaches in favor of text-in-context simplicity. This trades:

**Gains**:
- Dramatically simpler infrastructure (no vector DB, no embedding pipeline)
- Superior prompt caching (stable prefix)
- Strong single-session recall (94.87% on LongMemEval)
- Lower latency (no retrieval step at inference)

**Sacrifices**:
- No structured entity/relationship tracking (unlike Graphiti, mem0 graph mode)
- Lossy by design (unlike mem0's active CRUD preserving atomic facts)
- Weaker cross-session synthesis (unlike Zep/mem0's user-scoped retrieval)
- Observation quality depends on Observer model capabilities

The system fits best for **long-running, single-agent sessions** with heavy tool use (browser agents, coding agents, research agents) where conversation context outweighs cross-session knowledge retrieval. It is less suitable for multi-user systems with complex entity relationships or compliance scenarios requiring full-corpus recall.

---

## 14. Relationship to Cross-Domain Findings

OM maps cleanly onto the [Three Pillars framework](./findings.md):

- **Pillar 1 (Compression)**: OM is fundamentally a hierarchical compression system — messages compress to observations, observations compress to reflections. It adds structure (dates, priorities, event logs) that standard compaction lacks.
- **Pillar 2 (Retrieval)**: OM deliberately eliminates retrieval. Everything stays in context. This is the "give everything, trust the model" philosophy taken to its logical extreme — but with aggressive compression to make "everything" fit.
- The observation format (dated, prioritized event log) is a notable innovation over both prose summaries and atomic facts. It preserves more temporal and priority structure than any compaction approach studied in the context research, while being more context-efficient than raw history.

OM validates Finding 1 ("Memory and Context Are the Same Problem"): it is simultaneously a memory system (persists knowledge across turns) and a context management system (compresses to fit the window). The Observer is functionally identical to compaction in coding agents (Claude Code, Gemini CLI), but with richer output format and continuous operation rather than threshold-triggered bulk summarization.

---

## 15. Source Code Analysis

> **Source**: Mastra monorepo, `packages/memory/src/processors/observational-memory/`. All paths below are relative to `packages/memory/src/processors/observational-memory/`.

### File Layout

| File | Purpose |
|------|---------|
| `observational-memory.ts` | Core `ObservationalMemory` class — implements `Processor` interface; orchestrates Observer/Reflector lifecycle, threshold management, async buffering, activation, context injection |
| `observer-agent.ts` | Observer system prompt, extraction instructions, output parsing, message formatting, degenerate detection, context optimization |
| `reflector-agent.ts` | Reflector system prompt, compression levels 0-4, prompt building, output parsing, validation |
| `types.ts` | All config interfaces (`ObservationConfig`, `ReflectionConfig`), marker data types for streaming, `DataOmStatusPart` for UI feedback |
| `thresholds.ts` | Dynamic threshold calculation, buffer token resolution, retention floor math, chunk boundary logic |
| `token-counter.ts` | Token estimation via `tokenx` library; per-part caching in `providerMetadata.mastra`; provider-aware image token heuristics (OpenAI tile model, Anthropic pixel model, Google resolution tiers) |
| `date-utils.ts` | Relative time annotation (`addRelativeTimeToObservations`), inline estimated-date expansion, future-intent detection for "likely already happened" hints |
| `anchor-ids.ts` | Ephemeral `[O1]`, `[O1-N1]` anchor IDs injected before Reflector input and stripped after — helps Reflector reference specific observations during consolidation |
| `observation-groups.ts` | `<observation-group id="..." range="startId:endId">` wrapper for retrieval mode; parsing, reconciliation after reflection |
| `observation-utils.ts` | `getObservationsAsOf()` — time-travel query filtering observation chunks by message boundary timestamps |
| `operation-registry.ts` | Process-level operation tracking (observing/reflecting/buffering) to detect stale DB flags from crashed processes |
| `tool-result-helpers.ts` | Tool result sanitization, encrypted content stripping, token-budget truncation for tool outputs sent to Observer |
| `markers.ts` | Factory functions for streaming marker data parts (start/end/failed/activation) |
| `repro-capture.ts` | Debug reproduction capture for diagnosing OM issues |
| `../tools/om-tools.ts` | The `recall` tool for retrieval mode — cursor-based pagination through raw messages behind observation groups |

### Observer Agent: Implementation Details

**System prompt construction** (`buildObserverSystemPrompt()` in `observer-agent.ts`):

The Observer prompt is assembled from three exported constant blocks:
1. `OBSERVER_EXTRACTION_INSTRUCTIONS` (~260 lines) — detailed rules for observation extraction
2. `OBSERVER_OUTPUT_FORMAT_BASE` — the output XML structure specification
3. `OBSERVER_GUIDELINES` — terse style rules and completion tracking guidance

Key behavioral rules embedded in the prompt:

- **User assertions vs. questions**: "User stated: X" (authoritative) vs. "User asked: X" (request). Assertions take precedence — "the user is the source of truth about their own life."
- **State change framing**: "User will use the new method (replacing the old approach)" — explicitly marks superseded information.
- **Temporal anchoring**: Two timestamps per observation — message time at the START (always), referenced date at the END (only when a specific date can be calculated). Vague references like "recently" do NOT get end dates.
- **Unusual phrasing preservation**: `User stated they did a "movement session" (their term for exercise)` — quotes exact non-standard terminology.
- **Precise action verbs**: "getting" must be resolved to "subscribed to", "purchased", "received as gift", etc.
- **Recommendation detail preservation**: Lists must keep distinguishing attributes per item, not just "recommended 5 hotels."
- **Completion tracking**: `✅` markers are "memory signals" — without them the assistant may repeat finished work. Strict rules for when to use them (user confirmed) vs. not (assistant merely responded).
- **Grouped tool calls**: Bad: 3 separate "viewed file X" observations. Good: one parent "Agent browsed source files for auth flow" with sub-bullets for each result.

**Model settings defaults** (from `OBSERVATIONAL_MEMORY_DEFAULTS`):
- Observer: `temperature: 0.3`, `maxOutputTokens: 100_000`
- Observer providerOptions: `google.thinkingConfig.thinkingBudget: 215` (very small thinking budget — fast extraction, not deep reasoning)
- Reflector: `temperature: 0`, `maxOutputTokens: 100_000`
- Reflector providerOptions: `google.thinkingConfig.thinkingBudget: 1024` (larger thinking budget — needs to reason about what to keep/remove)

**Message formatting for Observer** (`formatObserverMessage()` in `observer-agent.ts`):

Messages are formatted as `**Role (timestamp):**\n{content}`, separated by `---`. Tool invocations are formatted as `[Tool Call: name]\n{args}` or `[Tool Result: name]\n{result}`. Tool results are truncated to 10,000 tokens (`DEFAULT_OBSERVER_TOOL_RESULT_MAX_TOKENS`) using binary search to find the optimal truncation point. Images/files become placeholder text like `[Image #1: photo.png]` while actual attachment parts are forwarded to the LLM for multimodal processing.

**Degenerate repetition detection** (`detectDegenerateRepetition()` in `observer-agent.ts`):

A safety mechanism against LLM repeat loops (observed with Gemini Flash). Two strategies:
1. Sample ~50 windows of 200 chars each; if >40% are duplicates, flag as degenerate.
2. Any single line >50,000 chars is automatically degenerate.

When degenerate output is detected, the Observer retries once. If the retry is also degenerate, it throws an error rather than storing garbage.

**Line sanitization** (`sanitizeObservationLines()`): Individual observation lines are truncated at 10,000 characters (`MAX_OBSERVATION_LINE_CHARS`).

**Context optimization** (`optimizeObservationsForContext()`): Before observations are injected into the Actor's context, the yellow (🟡) and green (🟢) emojis are stripped (only red 🔴 survives), arrow indicators (`->`) are removed, and semantic bracket labels are cleaned. This further compresses the observation text presented to the main agent.

### Reflector Agent: Implementation Details

**System prompt** (`buildReflectorSystemPrompt()` in `reflector-agent.ts`):

The Reflector is introduced as "the memory consciousness of an AI assistant" and told "your reflections are THE ENTIRETY of the assistant's memory. Any information you do not add to your reflections will be immediately forgotten."

Key instructions:
- Re-organize and streamline observations; draw connections and conclusions.
- "Understand that other parts of your mind may get off track in details or side quests" — the Reflector is explicitly tasked with detecting when the agent went off-track.
- Condense older observations more aggressively, retain more detail for recent ones.
- Preserve `✅` completion markers and their concrete outcomes.
- User assertions take precedence over questions.
- Thread attribution: consolidate universal facts across threads, preserve thread-specific context.

**Output format**: XML tags — `<observations>`, `<current-task>`, `<suggested-response>`.

**Anchor IDs for Reflector context** (`anchor-ids.ts`): Before the Reflector sees observations, ephemeral IDs like `[O1]`, `[O1-N1]`, `[O2]` are injected at the start of each observation line. This gives the Reflector concrete references to work with during consolidation. After parsing the Reflector's output, anchor IDs are stripped via `stripEphemeralAnchorIds()`.

**Compression level escalation** (`callReflector()` in `observational-memory.ts`):

The Reflector uses a retry loop with 5 compression levels (0-4). The system starts at level 0 (no explicit compression guidance) and escalates if the output fails to compress below the `observationTokens` threshold:

| Level | Detail Target | Key Guidance |
|-------|--------------|-------------|
| 0 | No guidance | First attempt — just reflect |
| 1 | 8/10 detail | "Condense more observations into higher-level reflections" |
| 2 | 6/10 detail | "Heavily condense... merge related items aggressively" |
| 3 | 4/10 detail | "Summarize oldest 50-70% into brief paragraphs, drop procedural details" |
| 4 | 2/10 detail | "Collapse ALL tool call sequences into outcome-only observations" |

The retry is capped at `min(MAX_COMPRESSION_LEVEL, startLevel + 3)` — so at most 4 attempts. If degenerate output persists at the max level, the loop breaks and accepts whatever it has.

Validation: `validateCompression()` simply checks `reflectedTokens < targetThreshold`.

### Threshold and Trigger System

**Dynamic thresholds** (`calculateDynamicThreshold()` in `thresholds.ts`):

When `shareTokenBudget: true`, the message threshold becomes a `ThresholdRange { min, max }` where `max = messageTokens + observationTokens` (the total budget) and `min = messageTokens` (the base). The effective threshold is `max(totalBudget - currentObservationTokens, baseThreshold)`. This means early in a conversation (when observations are empty), messages can use the full 70K budget. As observations grow, message space shrinks back to the base 30K.

**Buffer tokens resolution** (`resolveBufferTokens()`): Fractional values (0 < x < 1) are multiplied by the message threshold. Default 0.2 means buffer every 6,000 tokens (20% of 30K).

**Block-after resolution** (`resolveBlockAfter()`): Values between 1 and 100 (exclusive) are multipliers. Default 1.2 means synchronous observation is forced at 36,000 tokens (120% of 30K).

**Retention floor** (`resolveRetentionFloor()`): `bufferActivation: 0.8` means retain `30000 * (1 - 0.8) = 6000` tokens of raw messages after activation. Values >= 1000 are absolute token counts.

**Chunk boundary selection** (`calculateProjectedMessageRemoval()`): The activation logic iterates through buffered chunks to find the best boundary that gets closest to the retention target. It uses an "over-bias" strategy (prefer removing slightly more than the target) but has a safeguard: if overshooting would eat >95% of the retention floor, it falls back to the best under-boundary.

### Token Counting

**Library**: Uses `tokenx` (`estimateTokenCount()`) — a fast local token estimator, not an actual tokenizer.

**Per-part caching**: Token estimates are cached in `part.providerMetadata.mastra.tokenEstimate` with a version number (`TOKEN_ESTIMATE_CACHE_VERSION = 6`). On subsequent calls, if the cache version and estimator source match, the cached value is reused.

**Image token estimation**: Provider-aware heuristics:
- **OpenAI**: Tile-based model — `85 base + 170 per tile`, default 4 tiles if dimensions unknown.
- **Anthropic**: Pixel-based — `1 token per 750 pixels`, with max long edge of 1568px.
- **Google**: Resolution-tier model — Gemini 3 uses per-resolution token counts (280 for low, 560 medium, 1120 high, 2240 ultra_high). Legacy Gemini uses 258 tokens per tile.

**Message counting**: Each message incurs a per-message overhead (`TOKENS_PER_MESSAGE`) plus the sum of its parts. A per-conversation overhead (`TOKENS_PER_CONVERSATION`) is added once.

### How Observations Are Stored and Formatted

**Database record**: An `ObservationalMemoryRecord` (defined in `@mastra/core/storage`) contains:
- `activeObservations`: The full observation text
- `observationTokenCount`: Cached token count
- `lastObservedAt`: Cursor timestamp for loading unobserved messages
- `generationCount`: Reflection generation counter
- `pendingMessageTokens`: Accumulated token count for pending (not yet observed) messages
- `isObserving`/`isReflecting`: Concurrency flags
- `bufferedObservationChunks`: JSON-serialized buffered chunks awaiting activation
- `bufferedReflection`: Pre-computed reflection awaiting activation
- `lastBufferedAtTokens`: Token boundary tracking for buffer intervals

**Observation format in context**: When injected into the Actor's context window, observations are preceded by `OBSERVATION_CONTEXT_PROMPT` ("The following observations block contains your memory of past conversations with this user.") and followed by `OBSERVATION_CONTEXT_INSTRUCTIONS` which tell the model to prefer the most recent information, treat planned actions with past dates as completed, and always prioritize the most recent user message.

**Continuation hint**: After observed messages are removed and replaced with observations, a `OBSERVATION_CONTINUATION_HINT` system message is injected. It explicitly tells the model: "this is not a new conversation", "do not say 'Hi there!'", "do not refer to your 'memory observations' directly". This prevents the common failure mode where LLMs reset their conversational tone after context compression.

**Date annotation at context time**: `addRelativeTimeToObservations()` annotates observation date headers with relative time ("5 days ago", "2 weeks ago"). It also expands inline estimated dates: `(meaning May 30, 2023)` becomes `(meaning May 30, 2023 - 3 weeks ago)`. For future-intent observations that are now past-dated, it adds "likely already happened".

**Retrieval mode**: In retrieval mode, observations are wrapped in `<observation-group id="..." range="startId:endId">` tags. The `recall` tool (in `../tools/om-tools.ts`) uses cursor-based pagination with `startId:endId` ranges to fetch raw messages from storage behind any observation group. It supports detail levels ("low" = truncated, "high" = full), part-level indexing, and forward/backward pagination.

### Integration Architecture

**Processor interface**: `ObservationalMemory` implements the `Processor` interface with two hooks:
- `processInputStep()`: Called before each agent step. Loads historical messages, checks thresholds, activates buffered observations/reflections, injects observation context, triggers async buffering, and performs synchronous observation/reflection when thresholds demand it.
- `processOutputResult()`: Called after agent execution. Persists new messages to storage.

**Agent creation**: Observer and Reflector are standard Mastra `Agent` instances, lazily created via `getObserverAgent()` / `getReflectorAgent()`. They use the `agent.stream()` API for generation.

**Concurrency control**: An in-memory mutex (`locks` Map) serializes observation/reflection cycles per resource/thread within a single process. Static maps (`asyncBufferingOps`, `lastBufferedBoundary`, `lastBufferedAtTime`, `sealedMessageIds`) are shared across all `ObservationalMemory` instances because the processor is recreated per agent loop step.

**Operation registry** (`operation-registry.ts`): A process-level refcount tracker for active operations. Used to detect stale DB flags: if `isObserving=true` in the DB but no operation is registered in the current process, the flag was left by a crashed process and can be safely cleared.

### Notable Implementation Details Not in Docs

1. **Thinking budget asymmetry**: Observer gets only 215 thinking tokens (fast, shallow extraction) while Reflector gets 1024 (deeper reasoning for consolidation). Both use `google/gemini-2.5-flash` by default.

2. **Context optimization strips priority emojis**: When observations are presented to the Actor, 🟡 and 🟢 emojis are removed — only 🔴 survives. The priority emojis serve the Observer/Reflector pipeline but are considered visual noise for the main agent. This means the three-level priority system (red/yellow/green) is internal to the memory pipeline; the Actor only sees critical (🔴) and unmarked items.

3. **Degenerate output detection and retry**: Both Observer and Reflector have built-in detection for LLM repetition loops (sliding window analysis + line length check). On detection, each retries once. This is a practical defense against known Gemini Flash failure modes.

4. **Reflector receives Observer's instructions**: The Reflector prompt embeds the full `OBSERVER_EXTRACTION_INSTRUCTIONS`, `OBSERVER_OUTPUT_FORMAT_BASE`, and `OBSERVER_GUIDELINES` inside an `<observational-memory-instruction>` block. This gives the Reflector full context on how observations were created, enabling more intelligent consolidation.

5. **Anchor IDs for Reflector**: Ephemeral sequential IDs (`[O1]`, `[O2]`, `[O1-N1]`) are injected into observations before the Reflector processes them, then stripped from its output. This provides concrete references for the Reflector to track individual observations during reorganization.

6. **Stale boundary reset**: At the start of each turn (step 0), if the DB's `lastBufferedAtTokens` exceeds the current context size (e.g., after a reflection dramatically shrank the context), the boundary is reset to the current context size. Without this, the buffer interval logic would skip triggering until tokens grew past the stale boundary.

7. **Sealed message tracking**: Messages that have been persisted during async buffering are marked as "sealed." The `saveMessagesWithSealedIdTracking()` method prevents duplicate inserts by skipping sealed messages that don't yet contain observation boundary markers.

8. **Time-travel observation query**: `getObservationsAsOf()` in `observation-utils.ts` can filter observations to show only what existed at a given timestamp. Each observation chunk boundary contains an ISO 8601 timestamp; chunks with boundary dates after the target are excluded.

9. **Shared token budget**: When `shareTokenBudget: true`, message and observation token spaces are not independent — unused observation space flows into the message budget. With 30K/40K defaults this creates a 70K total budget that dynamically reallocates based on current observation size.

10. **Tool result truncation for Observer**: Tool results sent to the Observer are capped at 10,000 tokens using binary search for optimal truncation. Additionally, encrypted content fields are redacted (`[stripped encryptedContent: N characters]`).
