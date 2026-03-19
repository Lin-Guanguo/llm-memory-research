# OpenClaw Context Management Research

Last Updated: 2026-03-19

Source: [openclaw/openclaw](https://github.com/openclaw/openclaw)

Research focus: How OpenClaw assembles and manages context within a conversation, and how it differs from Pi (its underlying engine).

---

## Architecture Overview

OpenClaw is built on top of Pi (`pi-agent-core`, `pi-ai`), but adds a substantial context management layer on top. Key source locations:

| Layer | Path | Role |
|-------|------|------|
| Context Engine | `src/context-engine/` | Pluggable context assembly interface (7 lifecycle methods) |
| Agent Runtime | `src/agents/pi-embedded-runner/run/attempt.ts` | Multi-stage context pipeline before each LLM call |
| System Prompt | `src/agents/system-prompt.ts` | Complex multi-section prompt construction |
| Compaction | `src/agents/pi-embedded-runner/compact.ts` | Delegates to Pi's compaction or custom engine |
| Subagent | `src/agents/subagent-spawn.ts`, `subagent-registry.ts` | Built-in subagent lifecycle via gateway RPC |
| History | `src/agents/pi-embedded-runner/history.ts` | Turn-based history truncation |
| Session Sanitize | `src/agents/pi-embedded-runner/sanitize-session-history.ts` | Provider-specific message cleanup |

## Context Assembly Flow

Unlike Pi's simple "accumulate all → send all → compact when full", OpenClaw has a **multi-stage pipeline** executed before each LLM call (`attempt.ts:2130-2189`):

```
messages (raw conversation history, accumulated like Pi)
    │
    ▼ sanitizeSessionHistory()         ← Clean: remove invalid tool results, fix pairing
    │
    ▼ validateGeminiTurns()            ← Provider-specific turn validation (Gemini rules)
    ▼ validateAnthropicTurns()         ← Provider-specific turn validation (Anthropic rules)
    │
    ▼ limitHistoryTurns()              ← Config-based truncation (per DM/channel limit)
    │
    ▼ sanitizeToolUseResultPairing()   ← Repair orphaned tool results after truncation
    │
    ▼ contextEngine.assemble()         ← Pluggable: assemble context under token budget
    │   ├── LegacyContextEngine: pass-through (no-op)
    │   └── Custom engine: RAG, vector store, selective retrieval, etc.
    │
    ▼ systemPromptAddition             ← Context engine can inject extra system prompt text
    │
    ▼ Send to LLM
```

### Three Lines of Defense (vs Pi's One)

| Defense | Mechanism | Weight | Pi equivalent |
|---------|-----------|--------|---------------|
| 1st | `limitHistoryTurns()` | Lightweight, hard truncation by turn count | None |
| 2nd | `contextEngine.assemble()` | Pluggable, token-budget-aware assembly | `transformContext` hook (exists but unused) |
| 3rd | Compaction | Heavy, LLM-generated summary | Same (inherited from Pi) |

Pi only has the 3rd line. OpenClaw adds two layers before compaction can even trigger.

## ContextEngine Interface

The pluggable contract (`src/context-engine/types.ts`) defines 7 lifecycle methods:

| Method | Required | Purpose |
|--------|----------|---------|
| `bootstrap()` | Optional | Initialize engine state for a session, import historical context |
| `ingest()` | Required | Ingest a single message into the engine's store |
| `ingestBatch()` | Optional | Ingest a completed turn batch as one unit |
| `afterTurn()` | Optional | Post-turn lifecycle (persist context, trigger background compaction) |
| `assemble()` | Required | **Core: assemble model context under a token budget** |
| `compact()` | Required | Compress context (summaries, pruning, etc.) |
| `prepareSubagentSpawn()` | Optional | Prepare engine state before child agent starts |
| `onSubagentEnded()` | Optional | Notify engine that a subagent lifecycle ended |
| `dispose()` | Optional | Cleanup resources |

### AssembleResult

```typescript
type AssembleResult = {
  messages: AgentMessage[];        // Ordered messages for model context
  estimatedTokens: number;         // Token estimate of assembled context
  systemPromptAddition?: string;   // Optional text prepended to system prompt
};
```

### Registry and Resolution

- Engines are registered via `registerContextEngine(id, factory)` (public SDK) or `registerContextEngineForOwner(id, factory, owner)` (core)
- Resolution order: `config.plugins.slots.contextEngine` → default slot ("legacy")
- Only one engine active at a time (slot, not hook — exclusive)
- Registry is process-global (survives duplicated dist chunks)

### LegacyContextEngine (Default)

The default engine (`src/context-engine/legacy.ts`) is essentially a no-op wrapper:

- `ingest()` → no-op (SessionManager handles persistence)
- `assemble()` → pass-through (returns messages as-is, estimatedTokens: 0)
- `afterTurn()` → no-op
- `compact()` → delegates to Pi's built-in compaction via `delegateCompactionToRuntime()`

The real value is the **interface**: third-party plugins can replace LegacyContextEngine with custom implementations (RAG pipeline, vector store, graph-based context, etc.).

## History Truncation

`limitHistoryTurns()` (`src/agents/pi-embedded-runner/history.ts`) provides pre-compaction truncation:

- Walks backwards through messages, counting user turns
- When count exceeds configured limit, slices from that point
- Limits are configurable per provider/channel/DM:
  - `channels.<provider>.historyLimit` — for channel/group sessions
  - `channels.<provider>.dmHistoryLimit` — for DM sessions
  - `channels.<provider>.dms.<userId>.historyLimit` — per-user DM override

This means long-running DM or channel sessions get automatic turn-based truncation even without compaction.

## System Prompt Construction

OpenClaw's system prompt (`src/agents/system-prompt.ts`) is significantly more complex than Pi's ~300 words. It's built from 15+ sections:

1. **Identity** — "You are a personal assistant running inside OpenClaw."
2. **Tooling** — Dynamic tool list with descriptions (20+ possible tools)
3. **Tool Call Style** — Narration guidelines
4. **Safety** — Anthropic-inspired safety rules
5. **CLI Quick Reference** — OpenClaw subcommand reference
6. **Skills** — Available skills with mandatory scan-before-reply instructions
7. **Memory Recall** — memory_search/memory_get instructions
8. **Authorized Senders** — Owner identity (raw or hashed)
9. **Messaging** — Cross-session messaging, sub-agent orchestration
10. **Reply Tags** — Native reply/quote support
11. **Voice (TTS)** — Text-to-speech hints
12. **Documentation** — OpenClaw docs references
13. **Workspace** — Working directory and sandbox info
14. **Sandbox** — Container workspace guidance (if sandboxed)
15. **Self-Update** — Gateway update instructions
16. **Model Aliases** — Provider/model alias mappings
17. **Date & Time** — User timezone

Three prompt modes:
- `"full"` — All sections (main agent)
- `"minimal"` — Reduced: Tooling + Workspace + Runtime only (subagents)
- `"none"` — Just identity line

## Provider-Aware Context Sanitization

Unlike Pi, OpenClaw sanitizes messages per provider before sending:

- `validateGeminiTurns()` — Enforces Gemini's alternating turn rules
- `validateAnthropicTurns()` — Enforces Anthropic's turn rules
- `sanitizeToolUseResultPairing()` — Ensures every tool_result has a matching tool_use
- `sanitizeSessionHistory()` — Removes invalid entries, repairs broken state

These run as part of the pre-LLM pipeline, ensuring messages conform to each provider's API constraints.

## Subagent Model

OpenClaw has a **built-in, gateway-mediated** subagent system (not an extension like Pi).

### Spawn Flow

```
Main agent (sessionKey: agent:main:xxx)
  │
  ├─ tool call: sessions_spawn({ task: "...", agentId: "worker" })
  │     │
  │     ├─ Generate childSessionKey: "agent:worker:subagent:<uuid>"
  │     ├─ callGateway("sessions.patch") → create child session
  │     ├─ buildSubagentSystemPrompt() → build minimal system prompt for child
  │     ├─ contextEngine.prepareSubagentSpawn() → engine prepares child context state
  │     ├─ callGateway("agent") → send task message to child
  │     └─ registerSubagentRun() → track in subagent registry
  │
  ├─ Child runs in fully independent session with own context
  │
  ├─ Auto-announce: child pushes completion event to parent (push-based, no polling)
  │
  └─ Parent can also:
     sessions_send() → send messages to child (steering)
     sessions_history() → read child's conversation history
     subagents(action=steer|kill) → intervene mid-run
```

### Key Characteristics

- **Gateway RPC isolation**: Not process-level (like Pi's `spawn`), but session-level via gateway
- **Bidirectional communication**: Parent can steer/read child; child auto-announces completion
- **Context engine awareness**: `prepareSubagentSpawn()` and `onSubagentEnded()` lifecycle hooks
- **Depth limits**: Configurable max spawn depth prevents infinite nesting
- **Modes**: `"run"` (one-shot, cleanup after) or `"session"` (persistent, thread-bound)
- **Attachments**: Can pass files to subagents via base64-encoded attachments
- **Sandbox inheritance**: Child inherits or requires sandbox based on parent's status

## Comparison: Pi vs OpenClaw

| Aspect | Pi | OpenClaw |
|--------|-----|---------|
| **Context accumulation** | Infinite, full context sent every call | Infinite storage, but multi-stage pipeline before sending |
| **Pre-send processing** | None (optional `transformContext` hook, unused) | sanitize → validate → truncate → assemble |
| **Turn-based truncation** | None | `limitHistoryTurns()` per channel/DM config |
| **Token budgeting** | None | `assemble(tokenBudget)` via ContextEngine |
| **Provider awareness** | None (same format for all) | Per-provider turn validation (Gemini, Anthropic) |
| **Compaction** | LLM summary, threshold-triggered | Same base (inherited from Pi), but engine can override |
| **ContextEngine** | N/A | Pluggable slot interface, 7 lifecycle methods |
| **System prompt** | ~300 words, dynamic tool/guideline sections | 15+ sections, full/minimal/none modes |
| **Subagent** | Extension (process isolation, one-way) | Built-in (gateway RPC, bidirectional, lifecycle hooks) |
| **Subagent context** | Fully isolated, only text result returns | Isolated sessions, but parent can read history/steer |

## Design Philosophy

1. **Defense in depth**: Three layers of context management (truncate → assemble → compact) vs Pi's single layer
2. **Pluggable over hardcoded**: ContextEngine as a slot allows complete replacement of context strategy
3. **Provider-aware**: Unlike Pi's universal approach, OpenClaw adapts messages to each LLM provider's constraints
4. **Gateway-mediated orchestration**: Subagents communicate through the gateway, enabling bidirectional control and lifecycle management
5. **Configuration-driven**: History limits, context engine selection, and subagent behavior are all configurable per session/channel/provider
