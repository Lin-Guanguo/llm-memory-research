# Context Management in LLM Agents: Research Summary

Last Updated: 2026-03-19

---

## Studied Agents

| Agent | Type | Language | Source |
|-------|------|----------|--------|
| [Pi](https://github.com/badlogic/pi-mono) | Open source | TypeScript | `pi.research.md` |
| [OpenClaw](https://github.com/openclaw/openclaw) | Open source | TypeScript | `openclaw.research.md` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | Open source | TypeScript | `gemini-cli.research.md` |
| Claude Code | Closed source (prompts extracted) | TypeScript (Bun binary) | `claude-code-context.research.md` |
| [Codex](https://github.com/openai/codex) | Open source | Rust | `codex-context.research.md` |
| [OpenCode](https://github.com/anomalyco/opencode) | Open source | TypeScript/Bun | `opencode.research.md` |
| Dayfold Agent | Self-developed | Python (LangGraph) | `dayfold-agent-context.research.md` |

---

## Universal Pattern

All agents share the same base model:

```
Messages accumulate → Threshold reached → Compress/summarize → Continue with summary
```

Specifically:
- Single array (or equivalent) stores conversation history
- Every LLM call sends the full accumulated history
- LLM-generated summary replaces older content when approaching limits
- Summary injected as user-role message to continue the conversation

---

## Architecture Spectrum

```
Single-loop agents                          Multi-node workflow
(one context, one LLM)                      (multiple contexts, multiple LLMs)

Pi ── Codex ── Gemini CLI ── Claude Code ── OpenClaw ── Dayfold
│      │          │              │              │           │
│  per-item    2-pass         server-side    multi-stage   dual-channel
│  truncation  verify         compaction     pipeline      (Ports + Context)
│              + tool         + context      + pluggable   + per-node filter
│              pre-summary    awareness      engine        + proactive summary
│
simple ──────────────────────────────────────────── complex
```

---

## Key Dimensions Comparison

### Context Accumulation

| Agent | What enters context | Pre-processing |
|-------|-------------------|----------------|
| Pi | Full tool results, all messages | None |
| Codex | Truncated tool results (per-item, 10KB default) | Per-item truncation at record time |
| Gemini CLI | Pre-summarized large tool outputs | LLM summarization before entry + reverse token budget |
| Claude Code | Full tool results, all messages | None (API handles compaction) |
| OpenClaw | Full tool results | Multi-stage: sanitize → validate → truncate → assemble |
| Dayfold | Summary exchange only (full exchange disabled) | Per-node context_filter |

### Compaction Strategy

| Agent | Location | Trigger | Method | Verification |
|-------|----------|---------|--------|-------------|
| Pi | Client | contextWindow - 16K reserve | Single LLM call, 6-section summary | None |
| Codex (OpenAI) | Server | Configurable threshold | Encrypted opaque compaction block | N/A (server-side) |
| Codex (other) | Client | Same | Single LLM call, 4-section summary | None |
| Gemini CLI | Client | 50% of token limit | LLM summary + probe verification | 2nd LLM call verifies completeness |
| Claude Code | Server (API) | ~80% of context window | 9-section structured summary | None (but 3 analysis variants) |
| OpenClaw | Client (Pi inherited) | Same as Pi | Same as Pi, or custom ContextEngine | Depends on engine |
| Dayfold | N/A | Per-node (proactive) | summary_exchange templates | None; no reactive compaction fallback |

### Sub-Agent Context Model

| Agent | Sub-agent type | Context isolation | Return to parent |
|-------|---------------|-------------------|-----------------|
| Pi | Extension (OS process spawn) | Full isolation | Final text only |
| Codex | None | N/A | N/A |
| Gemini CLI | In-process (new GeminiChat) | Fresh chat instance | Final text only |
| Claude Code | 6+ types (Explore, Plan, Fork...) | Fresh context (except Fork: inherits parent) | Final text only |
| OpenClaw | Gateway RPC (sessions_spawn) | Session-level isolation | Text + bidirectional steering |
| Dayfold | Capability nodes | Per-node context_filter (3 tiers) | summary_exchange + port_values |

### System Prompt

| Agent | Size | Dynamic injection |
|-------|------|-------------------|
| Pi | ~300 words, single template | None |
| Codex | Single comprehensive file (prompt.md) | None |
| Gemini CLI | Section-based, toggleable, model-aware | GEMINI.md loading |
| Claude Code | 65+ modular files, ~8K tokens | 20+ system-reminder templates, per-event |
| OpenClaw | 15+ sections, 3 modes (full/minimal/none) | Minimal |
| Dayfold | YAML profile templates per capability | Per-node prompt rendering with variables |

---

## Design Patterns Identified

### Pattern 1: Reactive vs Proactive Compression

Most agents compress **reactively** — wait until context is nearly full, then compact.

Exceptions:
- **Codex**: Per-item truncation at entry time (proactive for tool outputs)
- **Gemini CLI**: Tool output pre-summarization (proactive for large results)
- **Dayfold**: summary_exchange at node completion (proactive for all node outputs)

### Pattern 2: Client-Side → Server-Side Migration

Context compaction is moving server-side:
- **2025**: Pi, Gemini CLI, OpenClaw — all client-side
- **2026**: Claude Code (`compact-2026-01-12`), Codex (`/responses/compact`) — server-side API
- Server-side enables: encrypted state preservation (Codex), mid-stream compaction (Codex), simpler clients

### Pattern 3: Single Channel vs Dual Channel

All mainstream agents use a **single channel** — everything (user messages, tool results, system reminders, summaries) goes into one conversation array.

Dayfold's dual-channel design (Ports for structured data, ContextMessages for semantic memory) is the only exception studied. This prevents structured data from inflating the conversation context.

### Pattern 4: Context Awareness as a Model Feature

Claude Code's `<budget:token_budget>` and `<system_warning>` tags make the model itself aware of remaining context capacity. No other agent has this. Combined with server-side compaction, the model can self-manage without client-side heuristics.

### Pattern 5: Sub-Agents as Context Management

Using sub-agents is fundamentally a **context management strategy**: give a focused task its own clean context window, get back a compressed summary. This pattern appears in Claude Code (Explore/Plan agents), OpenClaw (sessions_spawn), Gemini CLI (LocalAgentExecutor), and Dayfold (capability nodes with context_filter).

---

## Open Questions

1. **Graph-based context**: Memory research found knowledge graphs (Graphiti) to be a breakthrough. No agent uses graph structures for context management. Could tracking causal relationships between tool calls improve compression quality?

2. **Optimal compression threshold**: Pi compresses near the limit, Gemini CLI at 50%. What's the optimal point? Earlier compression loses less information per compression event but compresses more often.

3. **Verification cost**: Gemini CLI's two-pass verification catches lost information but doubles the compression cost. Is it worth it? No one else does it.

4. **Encrypted vs readable compaction**: Codex's server returns opaque encrypted state. This preserves model-internal representation but is unauditable. Claude Code's 9-section text summary is readable but may lose latent semantics. Which is better?

5. **When to filter vs when to send all**: Pi's "send everything" works with 1M context windows. But context rot (accuracy degradation with length) suggests filtering may be better even when context fits. Where's the crossover point?
