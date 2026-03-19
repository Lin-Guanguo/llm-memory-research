# Codex CLI Context Management Research

Last Updated: 2026-03-19

Sources:
- [openai/codex](https://github.com/openai/codex) (open source, Rust, added as submodule)
- [Unrolling the Codex agent loop](https://openai.com/index/unrolling-the-codex-agent-loop/) (OpenAI blog)
- [Codex Prompting Guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
- [Codex CLI features](https://developers.openai.com/codex/cli/features)
- [Simon Willison reverse engineering](https://simonwillison.net/2025/Nov/9/gpt-5-codex-mini/)
- Existing repo research: `agent-cli/codex-session-files.md`

Research focus: How Codex CLI assembles and manages context within a conversation.

---

## Architecture Overview

Codex CLI is **open source** (unlike Claude Code), written in **Rust** (`codex-rs/`). The core context management code is at `codex-rs/core/src/`:

| Component | Path | Role |
|-----------|------|------|
| Context Manager | `context_manager/history.rs` | Manages conversation history vector, token estimation |
| Context Normalization | `context_manager/normalize.rs` | Ensures tool call/result pairing, image handling |
| Compaction (local) | `compact.rs` | Client-side LLM-based compaction |
| Compaction (remote) | `compact_remote.rs` | Server-side compaction via Responses API `/responses/compact` |
| System prompt | `prompt.md` (template) | Base instructions for the agent |
| Compaction prompt | `templates/compact/prompt.md` | Compaction summarization instructions |
| Custom prompts | `custom_prompts.rs` | AGENTS.md / prompt file loading |
| Truncation | `truncate.rs` | Tool output truncation policies |
| Turn management | `state/turn.rs` | Turn lifecycle |
| Message history | `message_history.rs` | Historical message storage |

## Context Accumulation Model

Like all other studied agents, Codex uses **a single history vector** (`ContextManager.items: Vec<ResponseItem>`) that accumulates indefinitely:

```rust
// context_manager/history.rs
pub(crate) struct ContextManager {
    items: Vec<ResponseItem>,          // Oldest → newest
    token_info: Option<TokenUsageInfo>,
    reference_context_item: Option<TurnContextItem>,  // Baseline for settings diffing
}
```

Items are appended via `record_items()` with per-item truncation applied. Before sending to the model, `for_prompt()` normalizes and filters:

```rust
pub(crate) fn for_prompt(mut self, input_modalities: &[InputModality]) -> Vec<ResponseItem> {
    self.normalize_history(input_modalities);
    self.items.retain(|item| !matches!(item, ResponseItem::GhostSnapshot { .. }));
    self.items
}
```

## Dual Compaction Strategy

Codex has **two compaction paths** depending on the provider:

```rust
pub(crate) fn should_use_remote_compact_task(provider: &ModelProviderInfo) -> bool {
    provider.is_openai()
}
```

### Path 1: Remote Compaction (OpenAI providers)

Uses the Responses API `/responses/compact` endpoint:
- Server-side compaction — the API returns a `type=compaction` item with `encrypted_content`
- The encrypted content preserves the model's latent understanding (opaque to client)
- Can trigger mid-stream: if context crosses threshold during inference, server compacts and continues
- Trims function call history to fit context window before sending to API
- Returns replacement history that the client swaps in

### Path 2: Local/Inline Compaction (non-OpenAI providers)

Client-side LLM summarization, similar to Pi:
- Uses a dedicated compaction prompt (`templates/compact/prompt.md`)
- Prompt: "You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff summary..."
- Summary structure: Progress/decisions, constraints/preferences, remaining work, critical data
- Summary injected as a user message with `SUMMARY_PREFIX`
- Collects all user messages from history and preserves them alongside the summary

### Compaction Trigger

- `auto_compact_token_limit` — per-model configurable threshold
- `effective_context_window_percent` — default 95% of context window
- When context overflow occurs during compaction itself, falls back to removing oldest items one by one

### Post-Compaction History Structure

```
[summary message: SUMMARY_PREFIX + LLM summary]    ← Compacted summary
[preserved user messages]                           ← All user messages retained
[initial context injection (mid-turn only)]         ← Re-injected context settings
[ghost snapshots]                                   ← Preserved across compaction
```

Key detail: `InitialContextInjection` enum controls whether context is re-injected:
- `DoNotInject` — Pre-turn/manual compaction; next turn will re-inject naturally
- `BeforeLastUserMessage` — Mid-turn compaction; must inject because model expects it

## Tool Output Truncation

Codex has a per-model **truncation policy** applied at record time:

```rust
// From model_info.rs - default fallback
truncation_policy: TruncationPolicyConfig::bytes(/*limit*/ 10_000),
```

- Tool outputs are truncated when they exceed the model's configured limit
- Two modes: `Bytes` (byte limit) or `Tokens` (token limit)
- Applied per-item as items are recorded into the context manager
- This is pre-compaction — large tool outputs never fully enter the context

## System Prompt

The base system prompt (`prompt.md`) is a single comprehensive file covering:

1. **Identity** — "You are a coding agent running in the Codex CLI"
2. **Capabilities** — Receive prompts, stream responses, emit function calls
3. **AGENTS.md spec** — How instruction files are discovered and applied (scoped by directory)
4. **Responsiveness** — Preamble message guidelines before tool calls
5. **Planning** — `update_plan` tool usage with quality examples
6. **Task execution** — Autonomy, validation, `apply_patch` usage
7. **Ambition vs precision** — New tasks → creative; existing code → surgical
8. **Progress updates** — Concise status messages for long tasks
9. **Final answer formatting** — Detailed style guidelines (headers, bullets, monospace, tone)
10. **Tool guidelines** — Shell commands (prefer `rg`), `update_plan`

### Instruction File Loading

Codex enumerates instruction files from multiple locations:
- `~/.codex/` (global)
- Each directory from repo root to CWD
- Optional fallback names, size cap
- Merged in order: later directories override earlier ones
- Priority: system > developer > user > assistant

## Sub-Agent Architecture

Codex does not appear to have a built-in sub-agent spawning mechanism in the same sense as Claude Code's Agent tool or OpenClaw's `sessions_spawn`. The architecture relies on:

- **Single agent loop** — One `ContextManager` per session
- **Guardian/review sessions** — Separate review process for security, but using the same model infrastructure
- **No explicit sub-agent tool** in the base tool set

This is the simplest agent model among all studied — a single flat loop with no delegation.

## Comparison: All Five Agents

| Aspect | Pi | OpenClaw | Gemini CLI | Claude Code | Codex |
|--------|-----|---------|------------|-------------|-------|
| **Language** | TypeScript | TypeScript | TypeScript | TypeScript (Bun binary) | **Rust** |
| **Open source** | Yes | Yes | Yes | No | **Yes** |
| **Context model** | Accumulate all | Accumulate + pipeline | Accumulate all | Accumulate all | **Accumulate + per-item truncation** |
| **Compaction** | Client LLM (1 call) | Client (inherited Pi) | Client LLM (2 pass) | **Server-side API** | **Dual: server (OpenAI) / client (others)** |
| **Remote compaction** | No | No | No | Yes (API `compact-2026-01-12`) | **Yes (Responses API `/responses/compact`)** |
| **Encrypted state** | No | No | No | No | **Yes (opaque `encrypted_content`)** |
| **Tool output truncation** | None (full in context) | None | Pre-summarization + budget | None (file ref on compact) | **Per-item truncation at record time** |
| **Compaction prompt** | 6 sections | Same (inherited) | `<state_snapshot>` | 9 sections | **4 sections (minimal)** |
| **Mid-stream compaction** | No | No | No | No | **Yes (server triggers mid-inference)** |
| **Sub-agent** | Extension (process) | Built-in (gateway) | Built-in (in-process) | Built-in (6+ types) | **None (single loop)** |
| **System prompt** | ~300 words | 15+ sections | Toggleable sections | 65+ files | **Single comprehensive file** |
| **Context awareness** | None | None | None | Model-level budget | None |

## Unique Design Choices

1. **Dual compaction path**: OpenAI providers use server-side compaction with encrypted state preservation; non-OpenAI providers fall back to client-side LLM summarization. Best of both worlds for a multi-provider agent.

2. **Encrypted compaction content**: The server returns `encrypted_content` that preserves the model's latent understanding — the client treats it as opaque. This is unique among all studied agents and potentially preserves more semantic fidelity than text summaries.

3. **Mid-stream compaction**: The Responses API can trigger compaction mid-inference when context crosses the threshold, emitting a compaction item in the same stream. No other agent supports this.

4. **Per-item truncation at record time**: Unlike Gemini CLI (which truncates at compression time) or others (which don't truncate at all), Codex truncates each tool output as it enters the context. This prevents context from ever growing uncontrollably.

5. **Minimal compaction prompt**: Only 4 bullet points ("progress/decisions, constraints, remaining work, critical data"). Far simpler than Claude Code's 9 sections. Trades detail for speed.

6. **No sub-agents**: The simplest agent model — a single flat loop. Complex tasks are handled through planning (`update_plan`) rather than delegation. This keeps the context management simple but limits parallelism.

7. **Rust implementation**: Only Rust-based agent among the five studied. This enables fine-grained memory control and the per-item truncation strategy, which would be harder to implement efficiently in JavaScript.

8. **AGENTS.md scoping**: Directory-scoped instruction files with merge semantics and explicit priority ordering (system > developer > user > assistant). More structured than Claude Code's CLAUDE.md approach.
