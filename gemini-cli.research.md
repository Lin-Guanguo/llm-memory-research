# Gemini CLI Context Management Research

Last Updated: 2026-03-19

Source: [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) (Apache 2.0)

Research focus: How Gemini CLI assembles and manages context within a conversation.

---

## Architecture Overview

Gemini CLI is a monorepo with the core logic in `packages/core/src/`. Key locations for context management:

| Component | Path | Role |
|-----------|------|------|
| Chat state | `core/geminiChat.ts` | Manages conversation history array, sends messages to API |
| Agent loop | `agents/local-executor.ts` | Orchestrates turns, triggers compression, manages subagents |
| Turn | `core/turn.ts` | Single turn execution: stream response, handle tool calls |
| Compression | `services/chatCompressionService.ts` | Chat history compression (summarization + truncation) |
| Tool output summarizer | `utils/summarizer.ts` | LLM-based tool output summarization |
| System prompt | `prompts/promptProvider.ts`, `prompts/snippets.ts` | Section-based system prompt construction |
| Token limits | `core/tokenLimits.ts` | Per-model token limit definitions |

## Context Accumulation Model

Like Pi, Gemini CLI uses a **single history array that accumulates indefinitely**:

```typescript
// geminiChat.ts
this.history.push(userContent);           // User message added
const requestContents = this.getHistory(true);  // Full history sent to API
// ... after response ...
this.history.push({ role: 'model', parts: consolidatedParts }); // Model response added
```

Every `sendMessageStream()` call sends the **full curated history** to the Gemini API. There is no pre-send truncation or token budgeting pipeline like OpenClaw.

## Compression (Chat Compression Service)

### Trigger

Compression triggers when token count exceeds a threshold (`chatCompressionService.ts`):

```
DEFAULT_COMPRESSION_TOKEN_THRESHOLD = 0.5  (50% of model's token limit)
```

Called from `local-executor.ts` after each turn via `tryCompressChat()`.

### Algorithm: Three-Phase Compression

**Phase 1: Tool Output Truncation (Budget-Based)**

`truncateHistoryToBudget()` implements a "Reverse Token Budget" strategy:
- Iterates from **newest to oldest** messages
- Keeps a running tally of function response tokens
- Recent tool outputs preserved in full (high-fidelity for current context)
- Once budget exceeded (`COMPRESSION_FUNCTION_RESPONSE_TOKEN_BUDGET = 50,000` tokens), older large tool outputs truncated to last 30 lines, full output saved to temp file
- This runs BEFORE summarization, ensuring the summarizer doesn't get overwhelmed

**Phase 2: LLM Summarization with Verification**

1. Find split point: keep last 30% of history (`COMPRESSION_PRESERVE_THRESHOLD = 0.3`), compress the older 70%
2. Split point must land on a user message (not on a function response)
3. High-fidelity decision: if original (pre-truncation) history fits in model's token limit, send original to summarizer for better quality; otherwise send truncated version
4. Generate `<state_snapshot>` using a dedicated compression prompt
5. **Verification probe**: A second LLM call critically evaluates the snapshot and improves it if information was lost
6. If previous snapshot exists in history, instruction to **integrate** it (incremental update)

**Phase 3: Fallback (Truncation Only)**

If summarization previously failed (`hasFailedCompressionAttempt`):
- Skip LLM summarization entirely
- Only apply Phase 1 truncation
- Status: `CONTENT_TRUNCATED` (vs `COMPRESSED` for full summarization)

### Post-Compression History Structure

```
[user: <state_snapshot>...]      ← Summary injected as user message
[model: "Got it. Thanks..."]     ← Synthetic acknowledgment
[...recent 30% of history...]    ← Preserved recent messages
```

## Tool Output Summarization

Separate from chat compression, Gemini CLI has a dedicated tool output summarizer (`utils/summarizer.ts`):

- Triggered when individual tool results exceed a size threshold
- Uses a dedicated LLM call with `summarizer-default` model config
- Context-aware summarization: uses conversation history to understand what information matters
- Different strategies for: directory listings (structural), text content, shell command output (preserves error stack traces)

This means large tool outputs can be summarized **before** they even enter the main context, unlike Pi where full tool results always go into context.

## System Prompt Construction

`promptProvider.ts` builds the system prompt from composable sections:

| Section | Content |
|---------|---------|
| `preamble` | Identity, interactive vs non-interactive mode |
| `coreMandates` | Core behavioral rules, memory instructions |
| `subAgents` | Available sub-agent definitions |
| `agentSkills` | Available skills with descriptions and locations |
| `taskTracker` | Task tracking instructions (if enabled) |
| `primaryWorkflows` | Coding workflow guidance, tool usage patterns |
| `planningWorkflow` | Plan mode specific instructions (if in plan mode) |
| `operationalGuidelines` | Shell efficiency, interactive shell guidance |
| `sandbox` | Sandbox mode guidance (macos-seatbelt, generic, outside) |
| `interactiveYoloMode` | Auto-approve mode instructions |
| `gitRepo` | Git-specific instructions (if in a git repo) |
| `finalReminder` | Legacy model compatibility reminder |

Notable features:
- **Section toggleable**: Each section can be enabled/disabled via `isSectionEnabled()` with env var overrides
- **Model-aware**: Modern vs legacy model snippets (`snippets.ts` vs `snippets.legacy.ts`)
- **Template override**: `GEMINI_SYSTEM_MD` env var can point to a custom system.md file
- **Hierarchical memory**: Supports global + extension + project level memory injection
- **GEMINI.md context files**: Project-specific instructions loaded from filesystem

## Subagent Model

Gemini CLI has **in-process subagents** via `LocalAgentExecutor`:

```
Main agent (LocalAgentExecutor)
  │
  ├─ tool call: subagent_tool({ task: "..." })
  │     │
  │     └─ LocalSubagentInvocation
  │           └─ Creates new LocalAgentExecutor (in same process)
  │           └─ New GeminiChat instance (independent history)
  │           └─ Own system prompt (from agent definition)
  │           └─ Streams activity back to parent as tool live output
  │
  ├─ tool result: subagent's final output text
  │
  └─ Continues in main context
```

Key characteristics:
- **In-process, new chat instance**: Subagent runs in the same Node.js process but with a **fresh `GeminiChat` (independent history)**
- **Agent definitions**: Loaded from filesystem (`agentLoader.ts`), specify name, description, model config, tools, system prompt
- **Activity streaming**: Subagent streams progress (thoughts, tool calls) back to parent as `ToolLiveOutput`
- **Built-in agents**: `codebase-investigator` (fast recon), `browser` agent, `cli-help-agent`, `generalist-agent`
- **A2A support**: Also supports Agent-to-Agent protocol for remote agents
- **One-way context**: Parent's context doesn't flow to subagent; only final result returns

## Comparison: Pi vs OpenClaw vs Gemini CLI

| Aspect | Pi | OpenClaw | Gemini CLI |
|--------|-----|---------|------------|
| **Context model** | Infinite accumulate | Infinite + multi-stage pipeline | Infinite accumulate |
| **Pre-send processing** | None | sanitize → validate → truncate → assemble | None |
| **Compression trigger** | `contextWindow - reserve` | Same (inherited from Pi) | `50% of token limit` |
| **Compression approach** | LLM summary (1 call) | Same (inherited) + engine can override | LLM summary (2 calls: generate + verify) |
| **Tool output handling** | Full results in context | Full results in context | Pre-summarization of large outputs + budget-based truncation |
| **Verification** | None | None | Probe step verifies snapshot quality |
| **Fallback on failure** | Error | Error | Truncation-only mode (no LLM re-attempt) |
| **Subagent** | Extension (process isolation) | Built-in (gateway RPC) | Built-in (in-process, new chat) |
| **Subagent context** | Fully isolated | Isolated + bidirectional communication | Isolated (new GeminiChat instance) |
| **System prompt** | ~300 words | 15+ sections, 3 modes | Section-based, toggleable, model-aware |

## Session Storage vs Runtime Context

Previous research (`agent-cli/gemini-session-files.md`) analyzed Gemini CLI's session file structure:

- Sessions stored as single JSON files at `~/.gemini/tmp/{project-hash}/chats/session-{date}-{hash}.json`
- Simple flat structure: `{ sessionId, projectHash, messages: [...] }`
- Three message types: `user`, `gemini`, `info`

The earlier finding noted "context managed server-side, not exposed to client". Source code analysis reveals this is **not accurate for the current version** — compression is fully client-side:

1. `ChatCompressionService` runs locally, calling the Gemini API for summarization
2. The `<state_snapshot>` is injected as a user message into the local chat history
3. `chat.setHistory(newHistory)` replaces the in-memory history after compression
4. Session files record the full conversation including compressed state

Key insight: the **session file shows the final state** (post-compression history), but **the compression logic itself** (split point calculation, truncation, summarization, verification) is invisible in the session file — only the result is persisted.

## Unique Design Choices

1. **Two-pass compression**: Generate summary → verify → fix. Extra LLM call but higher quality snapshots
2. **Tool output pre-summarization**: Large tool results summarized BEFORE entering context, not just at compaction time. This is unique — Pi and OpenClaw put full tool results into context
3. **Reverse Token Budget for tool outputs**: Newest tool results get full fidelity, oldest get truncated first. Smart prioritization
4. **Graceful degradation**: If summarization fails once, switches to truncation-only mode for all subsequent compressions (avoids repeated expensive failures)
5. **50% threshold**: More aggressive compression trigger than Pi's "near the limit" approach. Compresses when half the context window is used
6. **State snapshot format**: Uses `<state_snapshot>` XML tags in the summary, enabling detection of previous snapshots for incremental updates
7. **In-process subagents**: Unlike Pi (OS process) or OpenClaw (gateway RPC), subagents run in the same Node.js process with a fresh chat instance. Simplest isolation model
