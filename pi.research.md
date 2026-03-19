# Pi Context Management Research

Last Updated: 2026-03-19

Source: [badlogic/pi-mono](https://github.com/badlogic/pi-mono)

Research focus: How Pi assembles and manages context within a conversation.

---

## Architecture Overview

Pi is a monorepo with three layers relevant to context management:

| Layer | Package | Role |
|-------|---------|------|
| LLM call | `pi-ai` | Unified multi-provider API, streaming, overflow detection |
| Agent runtime | `pi-agent-core` | Agent loop, message types, tool execution, context transform hooks |
| Coding agent | `pi-coding-agent` | System prompt construction, compaction, session management, custom message types |

## Context Assembly Flow

Every LLM call goes through `streamAssistantResponse` in `agent-loop.ts:238-259`:

```
AgentMessage[]                    ← Full conversation history (includes custom types)
    │
    ▼ transformContext()          ← Optional hook: prune, inject external context
    │                               (agent-core provides interface, coding-agent does NOT use it)
    │
    ▼ convertToLlm()             ← Key transform: AgentMessage[] → Message[]
    │                               - bashExecution → user message
    │                               - compactionSummary → user message (wrapped in <summary> tags)
    │                               - branchSummary → user message
    │                               - custom → user message
    │                               - excludeFromContext messages filtered out
    │                               - user/assistant/toolResult passed through
    │
    ▼ Context { systemPrompt, messages, tools }
    │
    ▼ streamSimple() → Send to LLM
```

**Key insight**: Context is a **single array that accumulates indefinitely**. Every user message, assistant response, tool call, and tool result is appended. The LLM sees the full history on every call until compaction fires.

## System Prompt Construction

`system-prompt.ts` builds the system prompt by concatenating sections in order:

1. **Role definition** — "You are an expert coding assistant operating inside pi..."
2. **Available tools** — Dynamically generated based on enabled tools (read/bash/edit/write/grep/find/ls)
3. **Guidelines** — Dynamically derived from tool combinations (e.g., has edit → "read before edit", has grep → "prefer grep over bash")
4. **Pi documentation** — File path references to docs/examples
5. **appendSystemPrompt** — Custom user-provided text
6. **Project Context** — AGENTS.md and other context files, each as `## {path}\n\n{content}`
7. **Skills** — Available skills list (only if read tool is available)
8. **Date + working directory** — Always appended last

If `customPrompt` is provided, it replaces sections 1-4 entirely but still appends 5-8.

System prompt is ~300 words in its default form (without project context or skills).

## Message Type System

Pi uses a two-level message type system:

**LLM-level (`pi-ai`):**
- `UserMessage` — `{ role: "user", content, timestamp }`
- `AssistantMessage` — `{ role: "assistant", content, usage, stopReason, ... }`
- `ToolResultMessage` — `{ role: "toolResult", toolCallId, content, isError, ... }`

**Agent-level (`pi-coding-agent` extends via declaration merging):**
- `BashExecutionMessage` — `{ role: "bashExecution", command, output, exitCode, ... }`
- `CustomMessage` — `{ role: "custom", customType, content, display, ... }`
- `CompactionSummaryMessage` — `{ role: "compactionSummary", summary, tokensBefore, ... }`
- `BranchSummaryMessage` — `{ role: "branchSummary", summary, fromId, ... }`

The `convertToLlm()` function converts agent-level messages to LLM-level messages at the call boundary. This separation allows the agent to carry UI-specific and bookkeeping messages without polluting the LLM context.

## Compaction (Context Compression)

### Trigger Conditions

Two cases, checked after each `agent_end` event and before each prompt submission:

1. **Threshold**: `contextTokens > contextWindow - reserveTokens` (default reserve: 16384 tokens)
2. **Overflow**: LLM returns context overflow error (detected via regex patterns matching 15+ provider error formats in `overflow.ts`)

### Algorithm

1. **Find cut point**: Walk backwards from newest message, accumulate estimated token counts until reaching `keepRecentTokens` (default: 20000). Cut at that point.
2. **Cut rules**: Valid cut points are user/assistant/custom/bashExecution messages. Never cut at toolResult (must stay paired with its toolCall).
3. **Generate summary**: Use LLM to create structured summary of discarded messages with format: Goal / Constraints & Preferences / Progress (Done/In Progress/Blocked) / Key Decisions / Next Steps / Critical Context.
4. **Incremental update**: If previous compaction exists, use `UPDATE_SUMMARIZATION_PROMPT` to merge new information into existing summary rather than regenerating from scratch.
5. **Split turn handling**: If cut point falls mid-turn, generate a separate turn prefix summary to provide context for the retained suffix.
6. **File tracking**: Append read/modified file lists to summary for continuity.

### Token Estimation

Uses `chars / 4` heuristic (conservative, overestimates). Images estimated at 1200 tokens (4800 chars).

When available, uses actual `usage` data from the last assistant message for more accurate context size tracking.

### Context Lifecycle

```
[sys prompt] + [msg1] + [msg2] + ... + [msgN]       ← Accumulate
                                                       ↓ Trigger threshold
[sys prompt] + [compaction summary] + [recent msgs]  ← After compaction
                     ↓ Continue accumulating
[sys prompt] + [compaction summary] + [recent] + [msgN+1] + ...
                                                       ↓ Trigger again
[sys prompt] + [updated summary] + [recent msgs]     ← Incremental update
```

Compaction summaries are injected as user messages wrapped in `<summary>` tags.

### Extension Hook

Extensions can intercept compaction via `session_before_compact` event and provide their own `CompactionResult`, completely replacing the default summarization logic.

## Subagent Model

Pi's agent-core has **no built-in subagent concept**. Subagents are implemented as an extension example (`examples/extensions/subagent/`).

### Implementation

Subagents are spawned as **separate OS processes**: `spawn("pi", ["--mode", "json", "--no-session", ...])`.

- **Process-level isolation**: Each subagent has its own context window
- **`--no-session`**: No persistence, disposable
- **One-way information flow**: Only the subagent's final text output returns to the main context. Subagent cannot see main context.
- **Three modes**: Single, Parallel (max 8 tasks, 4 concurrent), Chain (sequential with `{previous}` placeholder)

### Agent Definitions

Agents are markdown files with YAML frontmatter specifying name, description, tools, and model. Stored in `~/.pi/agent/agents/` (user-level) or `.pi/agents/` (project-level).

## Design Philosophy

1. **Minimalism**: ~300 word system prompt, 4 core tools (read/write/edit/bash), no built-in subagent
2. **Full context trust**: No token budgeting or selective inclusion — send everything until physical limit
3. **Late intervention**: Compaction only fires when approaching the context window limit, not proactively
4. **Extension over built-in**: Features like subagents, custom compaction, and context transforms are extension points, not core features
5. **Two-level message abstraction**: Agent-level messages carry rich metadata; conversion to LLM format happens only at the call boundary

## Comparison Notes

| Aspect | Pi | OpenClaw (ContextEngine) |
|--------|-----|------------------------|
| Context strategy | Accumulate all, compact when full | Assemble per-call with token budget |
| Token budgeting | None (full context until limit) | Per-section budget allocation via `assemble()` |
| Compaction | LLM-generated structured summary | Pluggable via ContextEngine slot |
| Subagent | Extension (process isolation) | (TBD - needs research) |
| System prompt | ~300 words, dynamic tool/guideline sections | Complex multi-section construction |
