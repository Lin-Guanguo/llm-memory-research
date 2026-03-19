# OpenCode Context Management Research

Last Updated: 2026-03-19

Source: [anomalyco/opencode](https://github.com/anomalyco/opencode) (open source, TypeScript/Bun, added as submodule)

Research focus: How OpenCode manages context within a conversation.

---

## Architecture Overview

OpenCode is an open-source coding agent built with TypeScript/Bun. Key source locations at `packages/opencode/src/`:

| Component | Path | Role |
|-----------|------|------|
| Compaction | `session/compaction.ts` | Prune tool outputs + LLM summarization |
| Prompt loop | `session/prompt.ts` | Main agent loop, message dispatch |
| System prompt | `session/system.ts` | Provider-specific system prompt selection |
| Instructions | `session/instruction.ts` | AGENTS.md / CLAUDE.md / CONTEXT.md loading |
| Revert | `session/revert.ts` | Conversation fork/revert with snapshot rollback |
| Message model | `session/message-v2.ts` | Message types, parts, error handling |
| Agent definitions | `agent/agent.ts` | Agent registry (build, plan, explore, compaction, etc.) |
| Task tool | `tool/task.ts` | Sub-agent spawning via task sessions |
| Summary | `session/summary.ts` | Diff-based session summary |

## Context Accumulation Model

Like all other studied agents, OpenCode uses **infinite message accumulation**. Messages are stored in SQLite (`session.sql.ts`) and loaded for each LLM call via `MessageV2.toModelMessages()`.

## Compaction: Two-Phase Strategy

OpenCode's compaction (`session/compaction.ts`) is a **two-phase process**: prune first, then summarize.

### Phase 1: Prune (Tool Output Truncation)

```typescript
PRUNE_PROTECT = 40_000   // Keep last 40K tokens of tool outputs intact
PRUNE_MINIMUM = 20_000   // Only prune if >20K tokens can be reclaimed
```

Algorithm:
1. Walk backwards through message parts
2. Skip the last 2 user turns entirely (protect recent context)
3. Skip protected tools (e.g., `skill`)
4. After 40K tokens of tool outputs, mark remaining older tool outputs as `compacted`
5. Compacted tool outputs are stripped from context when sent to LLM

This is similar to Gemini CLI's reverse token budget, but operates at the part level rather than the message level.

### Phase 2: Summarize (LLM Compaction)

Trigger: `isOverflow()` checks if total tokens >= usable context (input limit - reserved buffer).

```typescript
COMPACTION_BUFFER = 20_000  // Default reserved tokens
```

Process:
1. A hidden `compaction` agent is invoked (not user-selectable)
2. Full message history (with media stripped) is sent to the compaction model
3. Default compaction prompt generates a structured summary:

```
## Goal
[What goal(s) is the user trying to accomplish?]

## Instructions
[Important instructions, plans, specs]

## Discoveries
[Notable things learned during conversation]

## Accomplished
[Completed, in-progress, and remaining work]

## Relevant files / directories
[Structured file list]
```

4. Summary stored as an assistant message with `summary: true` flag
5. If overflow persists after compaction, falls back to replaying the last user message with a note

### Compaction Model Selection

The compaction agent can use a different model than the main conversation:

```typescript
const model = agent.model
  ? await Provider.getModel(agent.model.providerID, agent.model.modelID)
  : await Provider.getModel(userMessage.model.providerID, userMessage.model.modelID)
```

### Plugin Hook

Plugins can intercept compaction via `experimental.session.compacting` to inject additional context or replace the compaction prompt entirely.

## System Prompt: Provider-Specific

OpenCode selects different base system prompts based on the model provider:

```typescript
if (model.api.id.includes("gpt-5")) return [PROMPT_CODEX]
if (model.api.id.includes("gpt-") || ...) return [PROMPT_BEAST]
if (model.api.id.includes("gemini-")) return [PROMPT_GEMINI]
if (model.api.id.includes("claude")) return [PROMPT_ANTHROPIC]
if (model.api.id.includes("trinity")) return [PROMPT_TRINITY]
return [PROMPT_DEFAULT]
```

Additional system prompt components:
- **Environment info**: working directory, platform, date, git status (wrapped in `<env>` tags)
- **Skills**: available skills with verbose descriptions
- **Instructions**: AGENTS.md, CLAUDE.md, CONTEXT.md files loaded from directory hierarchy (global → project)

### Instruction File Loading

Similar to Codex's AGENTS.md approach:
- Global: `~/.config/opencode/AGENTS.md`, `~/.claude/CLAUDE.md`
- Project: walks up from CWD to workspace root, loading AGENTS.md/CLAUDE.md/CONTEXT.md
- Supports `OPENCODE_CONFIG_DIR` and `OPENCODE_DISABLE_PROJECT_CONFIG` flags

## Sub-Agent Architecture

OpenCode has a **Task tool** (`tool/task.ts`) for spawning sub-agents:

### Spawn Flow

```
Main agent (session A)
  │
  ├─ tool_call: task({ subagent_type: "explore", prompt: "...", description: "..." })
  │     │
  │     ├─ Session.create({ parentID: session A }) → new session B
  │     ├─ SessionPrompt.prompt({ sessionID: B, agent: "explore", ... })
  │     │     └─ Sub-agent runs in session B with own context
  │     │
  │     └─ Returns: "task_id: {session_id}\n<task_result>\n{last text output}\n</task_result>"
  │
  ├─ tool_result: sub-agent's final text (back in session A's context)
  │
  └─ Can resume: task({ task_id: "...", prompt: "continue" }) → resumes session B
```

### Key Characteristics

- **Session-level isolation**: Each sub-agent gets its own SQLite session
- **Resumable**: Pass `task_id` to continue a previous sub-agent session (unique among studied agents)
- **Permission-controlled**: Sub-agent permissions derived from agent definition + config, with glob pattern matching
- **Model inheritance**: Sub-agent uses parent's model unless agent definition specifies otherwise
- **No todowrite/todoread**: Explicitly disabled for sub-agents
- **Task nesting control**: Agents can be configured to allow or deny spawning further sub-agents

### Built-in Agent Types

| Agent | Mode | Description |
|-------|------|-------------|
| `build` | primary | Default agent, full tool access |
| `plan` | primary | Plan mode, edit tools denied |
| `explore` | subagent | Read-only file search specialist |
| `compaction` | hidden | Summarization agent (auto-triggered) |
| Custom agents | configurable | User-defined via config |

## Conversation Fork/Revert

OpenCode has a unique **revert system** (`session/revert.ts`):

1. User can revert to any previous message in the conversation
2. System takes a **filesystem snapshot** before revert
3. All file patches applied after the revert point are rolled back
4. Diff is computed and stored for reference
5. Conversation continues from the reverted point

This enables branching exploration without losing the ability to go back. No other studied agent has filesystem-integrated revert.

## Unique Features

### Inception Messages (from issue tracker)

Messages that survive all compactions — "permanent bedrock" context. Not fully visible in current source, but referenced in issues and documentation as a planned/experimental feature.

### LSP Diagnostics Integration

Tool execution results are validated using LSP diagnostics before entering the conversation context. This adds a code-aware quality check that no other agent performs.

### Event Bus Architecture

`Bus.publish()` / `Bus.subscribe()` pattern with a `GlobalBus` enables cross-instance context awareness. Compaction events, session changes, and file modifications are broadcast system-wide.

## Comparison with Other Agents

| Aspect | OpenCode | Most similar to |
|--------|----------|----------------|
| **Compaction** | Two-phase: prune tool outputs + LLM summary | Gemini CLI (also has tool output pre-processing + summarization) |
| **Compaction prompt** | 5-section template (Goal/Instructions/Discoveries/Accomplished/Files) | Claude Code (9 sections), Pi (6 sections) |
| **Provider-specific prompts** | Different base prompt per model family | OpenClaw (provider-aware validation) |
| **Sub-agent** | Session-based, resumable | Claude Code (multiple types), but OpenCode adds resumability |
| **Fork/revert** | Filesystem snapshot + rollback | Unique — no other agent has this |
| **Instruction files** | AGENTS.md + CLAUDE.md + CONTEXT.md hierarchy | Codex (AGENTS.md hierarchy) |
| **Plugin hooks** | `experimental.session.compacting` | OpenClaw (ContextEngine plugin slot) |
| **Tool output pruning** | Reverse walk, protect recent 40K tokens | Gemini CLI (reverse token budget, 50K) |

## Summary

OpenCode sits between Pi's minimalism and Claude Code's complexity. Its two-phase compaction (prune + summarize) is well-designed, and the resumable sub-agent sessions and filesystem-aware revert are unique features. The provider-specific system prompt selection shows awareness of model differences that most agents ignore. The plugin hook for compaction opens extensibility similar to OpenClaw's ContextEngine but at a simpler level.
