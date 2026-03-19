# Claude Code Context Management Research

Last Updated: 2026-03-19

Sources:
- [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) (v2.1.79, added as submodule)
- [Anthropic Compaction API docs](https://platform.claude.com/docs/en/build-with-claude/compaction)
- [Anthropic Context Windows docs](https://platform.claude.com/docs/en/build-with-claude/context-windows)
- [Anthropic: Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Existing repo research: `agent-cli/claude-session-files.md`

Research focus: How Claude Code assembles and manages context within a conversation.

---

## Architecture Overview

Claude Code is distributed as a Bun-compiled native binary (~183MB Mach-O arm64). Source code is not public, but the community has extensively reverse-engineered it. The system prompt alone is 65+ files covering different aspects, plus 20+ system-reminder templates injected contextually.

Key context management components (from extracted prompts):

| Component | Files | Role |
|-----------|-------|------|
| Compaction prompts | 3 variants of analysis instructions + summary prompt | Generate context summaries when approaching limits |
| Conversation summarization | `agent-prompt-conversation-summarization.md` | Full 9-section summary for /compact |
| Recent message summarization | `agent-prompt-recent-message-summarization.md` | Summarize only recent portion (incremental) |
| System reminders | 20+ `system-reminder-*.md` files | Dynamic context injected per-situation |
| Sub-agent prompts | Explore, Plan, Worker Fork, etc. | Isolated context for delegated tasks |
| Memory instructions | `system-prompt-agent-memory-instructions.md` | Cross-session memory management |

## Context Accumulation Model

Like Pi, Claude Code uses **infinite context accumulation** — all messages (user, assistant, tool calls, tool results) are appended to the conversation history. The full history is sent with each API call until compaction triggers.

Session files confirm this (`agent-cli/claude-session-files.md`): JSONL format at `~/.claude/projects/{path}/{sessionId}.jsonl`, each line is a message/event entry.

## Server-Side Compaction (API Level)

Claude Code leverages Anthropic's **server-side compaction API** (beta `compact-2026-01-12`):

### How It Works

1. Enable via `context_management.edits: [{ type: "compact_20260112" }]` in API request
2. API detects when input tokens exceed the trigger threshold
3. Generates a `compaction` content block containing the summary
4. On subsequent requests, API automatically drops all message blocks prior to the compaction block

### Configuration

```json
{
  "context_management": {
    "edits": [{
      "type": "compact_20260112",
      "trigger_tokens": 100000,    // When to trigger (default: ~80% of context window)
      "preserve_system": true,     // Keep system prompt intact
      "custom_instructions": "..." // Focus areas for summary
    }]
  }
}
```

### Key Difference from Pi/OpenClaw/Gemini CLI

Compaction happens **server-side in the API**, not client-side. The client just appends the response (which may contain a compaction block) and sends it back. This is fundamentally different from:
- Pi: client-side LLM call for summarization
- OpenClaw: delegates to Pi's client-side compaction
- Gemini CLI: client-side two-pass compression

## Client-Side Compaction Prompts (Claude Code Specific)

Claude Code has its own compaction prompt layer on top of the API, with **three variants**:

### Variant 1: Full Conversation Compaction

Analyzes the entire conversation chronologically:
- Identifies user requests, approach taken, key decisions
- Captures file names, code snippets, function signatures, file edits
- Records errors encountered and fixes
- Emphasizes user feedback (especially corrections)

### Variant 2: Recent Messages Only

Same structure but only analyzes messages after the last retained context. Used for incremental compaction where earlier context is already summarized.

### Variant 3: Minimal (Experimental, Feature Flag)

Lean version where `<analysis>` is a brief planning scratchpad:
- One or two lines per section
- No code snippets or verbatim quotes in analysis
- Detail goes directly into `<summary>`
- Goal: coverage over detail in analysis phase

### Summary Structure (9 Sections)

The conversation summarization prompt produces a structured summary with:

1. **Primary Request and Intent** — User's explicit requests and intents
2. **Key Technical Concepts** — Technologies, frameworks discussed
3. **Files and Code Sections** — Files examined/modified/created with full code snippets
4. **Errors and Fixes** — Errors encountered, how fixed, user feedback
5. **Problem Solving** — Solved problems and ongoing troubleshooting
6. **All User Messages** — Every non-tool-result user message (critical for intent tracking)
7. **Pending Tasks** — Explicitly requested outstanding work
8. **Current Work** — Precise description of work in progress at compaction time
9. **Optional Next Step** — Next action, with direct quotes to prevent task drift

### SDK Compaction Prompt

A simpler variant for the Agent SDK, structured as:
1. Task Overview (request + success criteria + constraints)
2. Current State (completed work, files, artifacts)
3. Important Discoveries (constraints, decisions, errors, failed approaches)
4. Next Steps (specific actions, blockers, priority order)
5. Context to Preserve (preferences, domain details, promises)

Output wrapped in `<summary>` tags.

## Context Awareness (Model-Level Feature)

Claude 4.5+ models have built-in **context awareness** — the model knows its remaining token budget:

```xml
<!-- At conversation start -->
<budget:token_budget>1000000</budget:token_budget>

<!-- After each tool call -->
<system_warning>Token usage: 35000/1000000; 965000 remaining</system_warning>
```

This enables the model to self-manage context usage, persist on tasks until completion, and make informed decisions about when to compact.

## Thinking Block Management

Extended thinking tokens have special handling:
- Thinking blocks are **automatically stripped** from context on subsequent turns
- During tool use cycles, thinking blocks **must be preserved** until the tool cycle completes
- Effective context: `context_window = (input_tokens - previous_thinking_tokens) + current_turn_tokens`
- Cryptographic signatures verify thinking block authenticity

This is a significant context optimization — thinking can be substantial but doesn't accumulate.

## System Prompt Structure

Claude Code's system prompt is assembled from 65+ modular files:

### Core Sections
- Identity ("Claude Code, Anthropic's official CLI")
- Doing tasks (10+ sub-sections: security, read-before-modify, minimize files, no over-engineering, etc.)
- Executing actions with care (reversibility, blast radius assessment)
- Tool usage guidelines (prefer dedicated tools over Bash)
- Git operations (commit workflow, PR creation)
- Output efficiency ("go straight to the point")

### Dynamic Injections (System Reminders)
Contextually injected based on runtime events:
- `system-reminder-file-modified-by-user-or-linter.md` — When external file changes detected
- `system-reminder-compact-file-reference.md` — Reference to file read before compaction
- `system-reminder-hook-additional-context.md` — Hook-provided context
- `system-reminder-invoked-skills.md` — When a skill is activated
- `system-reminder-file-truncated.md` — When file content exceeds limits

### Approximate Token Budget
- Base system prompt: ~3,000 tokens
- Tool definitions: ~5,000 tokens
- Context buffer (reserved): ~33,000 tokens (reduced from 45,000 in earlier versions)
- Usable context: ~960,000 tokens (out of 1M)

## Sub-Agent Architecture

Claude Code has multiple sub-agent types with isolated contexts:

### Agent Types (from extracted prompts)

| Agent | Purpose | Context Model |
|-------|---------|---------------|
| **Explore** | Read-only codebase search | Fresh context, read-only tools, fast |
| **Plan** | Architecture planning | Fresh context, read-only tools |
| **Worker Fork** | Execute directive directly | Inherits full parent context, no sub-spawning |
| **Code Reviewer** | Review code changes | Fresh context with diff |
| **Code Explorer** | Deep feature analysis | Fresh context |
| **Code Architect** | Design feature architecture | Fresh context |

### Worker Fork (Unique Design)

The "fork" agent type is notable — it **inherits full conversation context** from the parent:
- `model: 'inherit'` — Uses parent's model
- `permissionMode: 'bubble'` — Permissions bubble up to parent
- `maxTurns: 200`
- `tools: [*]` — Full tool access
- Rule: "You ARE the fork. Do NOT spawn sub-agents; execute directly."
- Must commit changes and report with commit hash
- Report under 500 words, structured format: Scope → Result → Key files → Files changed → Issues

Other agents get fresh, isolated contexts with task-specific system prompts.

## Comparison: Claude Code vs Pi vs OpenClaw vs Gemini CLI

| Aspect | Pi | OpenClaw | Gemini CLI | Claude Code |
|--------|-----|---------|------------|-------------|
| **Compaction location** | Client-side | Client-side (Pi inherited) | Client-side | **Server-side API** |
| **Compaction trigger** | contextWindow - reserve | Same | 50% of limit | ~80% of limit (configurable) |
| **Summary structure** | 6 sections (Goal/Progress/Decisions/...) | Same (inherited) | `<state_snapshot>` | **9 sections** (most detailed) |
| **Verification** | None | None | 2-pass (generate + probe) | None (but 3 analysis variants) |
| **Tool output handling** | Full in context | Full in context | Pre-summarization + budget | Full in context + file reference on compact |
| **Context awareness** | None | None | None | **Model-level** (`<budget:token_budget>`) |
| **Thinking block mgmt** | N/A | N/A | N/A | **Auto-stripped** between turns |
| **System prompt size** | ~300 words | 15+ sections | Section-based, toggleable | **65+ modular files**, ~8K tokens |
| **Sub-agent types** | 1 (extension) | 1 (gateway RPC) | Multiple (in-process) | **6+ types** with different context models |
| **Context inheritance** | None | None | None | **Worker fork inherits full context** |
| **System reminders** | None | None | None | **20+ dynamic injection templates** |
| **Pre-send processing** | None | Multi-stage pipeline | None | Minimal (API handles most) |

## Unique Design Choices

1. **Server-side compaction**: Claude Code offloads compaction to the API, simplifying client logic. The client just sends messages and handles the compaction block in responses. This is architecturally the simplest client-side implementation among all studied agents.

2. **Three compaction analysis variants**: Full, recent-only, and minimal. Allows trading quality for speed. The minimal variant is behind a feature flag, suggesting active experimentation.

3. **9-section summary format**: The most detailed summary structure of all agents studied. Notably includes "All user messages" (verbatim non-tool messages) and "Current Work" with direct quotes to prevent task drift.

4. **Context awareness at model level**: The model itself knows remaining token budget via `<budget:token_budget>` and `<system_warning>` tags. No other studied agent has this — it's a model-level feature unique to Claude 4.5+.

5. **Worker fork with context inheritance**: Unlike all other sub-agent models (which use isolated contexts), the fork agent inherits the parent's full context. This enables continuation of complex tasks without context loss.

6. **Dynamic system reminders**: 20+ templates injected contextually (file changes, hook output, skill activation). This is more granular than any other agent's dynamic context injection.

7. **Thinking block auto-stripping**: Extended thinking tokens are automatically removed from subsequent turns, preventing context pollution from reasoning traces. This is a significant optimization unique to Claude's architecture.
