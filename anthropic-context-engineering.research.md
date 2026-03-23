# Anthropic Context Engineering: Official Guidance vs Industry Practice

Last Updated: 2026-03-23

Sources:
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (Anthropic engineering blog)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (Anthropic engineering blog)
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works) (Claude Code official docs)
- [Managing context on the Claude Developer Platform](https://www.anthropic.com/news/context-management) (Anthropic news)
- [Context Engineering from Claude - Bojie Li analysis](https://01.me/en/2025/12/context-engineering-from-claude/) (community deep dive)
- [Compaction API docs](https://platform.claude.com/docs/en/build-with-claude/compaction)
- [Context windows docs](https://platform.claude.com/docs/en/build-with-claude/context-windows)

---

## Compression + Retrieval: How Official Docs Map to Two Fundamental Operations

All of Anthropic's context management guidance maps cleanly onto two operations: **compression** (reduce information) and **retrieval** (select relevant information).

### Compression Side

From Claude Code official docs:

> "Claude Code manages context automatically as you approach the limit. It **clears older tool outputs first**, then **summarizes the conversation** if needed."

Two layers of compression, escalating in aggressiveness:

| Layer | Mechanism | Cost | Information loss |
|-------|-----------|------|-----------------|
| 1st | Tool result clearing | Minimal — removes raw output, keeps the fact that tool was called | Low — results can be re-fetched |
| 2nd | Conversation summarization | LLM call — generates structured summary | Higher — nuance and detail may be lost |

Users can direct compression focus:
> "Add a 'Compact Instructions' section to CLAUDE.md or run `/compact` with a focus (like `/compact focus on the API changes`)"

### Retrieval Side

Three retrieval modes, from static to dynamic:

| Mode | What | When loaded | Token cost |
|------|------|-------------|-----------|
| **Pre-load** | CLAUDE.md, auto memory, system instructions | Session start | Fixed per session |
| **On-demand** | Skills (descriptions pre-loaded, full content loaded on use) | When skill is triggered | Variable |
| **JIT exploration** | Files via glob/grep/Read, web via WebSearch/WebFetch | During agentic loop | Variable |

Sub-agents as a retrieval strategy:
> "Subagents get their own fresh context, completely separate from your main conversation. Their work doesn't bloat your context. When done, they return a summary."

This is retrieval + compression in one operation: the sub-agent retrieves information (explores codebase), then compresses it (returns summary).

### The Agentic Loop as Retrieval → Action → Retrieval

Claude Code's three-phase loop maps directly:

```
gather context  →  take action  →  verify results
(retrieval)        (execution)     (retrieval again)
```

The first phase is retrieval (glob, grep, Read to understand the codebase). The third phase is also retrieval (run tests, check output). Compression happens implicitly throughout (tool results accumulate until cleared or summarized).

### What the Official Docs Don't Say

The official docs describe **what** happens but not **why these specific tradeoffs**:
- Why clear tool results before summarizing? (Because re-fetching a file is cheap; re-deriving a decision is expensive)
- Why pre-load CLAUDE.md but not skills? (Because CLAUDE.md is always relevant; skills are conditionally relevant)
- Why sub-agents return summaries, not full transcripts? (Because the parent needs the conclusion, not the journey)

These are compression/retrieval tradeoff decisions that become clear through the two-operation lens.

---

## Core Thesis

Anthropic frames context engineering as the evolution beyond prompt engineering:

> "What configuration of context is most likely to generate our model's desired behavior?"

The guiding principle: **find the smallest set of high-signal tokens that maximize the likelihood of the desired outcome**. Context is a finite resource with diminishing returns as token count increases.

## The Four Types of Context Rot

Anthropic identifies four mechanisms by which context quality degrades:

| Type | Description | Example |
|------|-------------|---------|
| **Context Poisoning** | Incorrect/outdated information corrupts reasoning | Stale tool result from a file that's since been modified |
| **Context Distraction** | Irrelevant information reduces focus | 50 unrelated tool outputs from earlier exploration |
| **Context Confusion** | Similar but distinct information causes misassociation | Two files with similar names but different purposes |
| **Context Clash** | Contradictory information creates uncertainty | Old and new versions of the same config in context |

**How studied agents handle these:**

| Rot type | Pi | OpenClaw | Gemini CLI | Claude Code | Codex | OpenCode |
|----------|-----|---------|------------|-------------|-------|----------|
| Poisoning | No protection | No protection | No protection | `system-reminder-file-modified-by-user-or-linter` detects external changes | No protection | No protection |
| Distraction | No mitigation (full context) | `limitHistoryTurns` removes old turns | Tool output pre-summarization | Sub-agents isolate exploration context | Per-item truncation removes large outputs | `prune()` erases old tool outputs |
| Confusion | No mitigation | Provider-specific turn validation | No mitigation | 20+ system reminders provide clarifying context | No mitigation | No mitigation |
| Clash | No mitigation | No mitigation | No mitigation | No mitigation | No mitigation | Fork/revert lets user branch away from conflicting state |

**Finding**: Only Claude Code actively addresses context poisoning (via file modification detection). Most agents have no defense against confusion or clash. Distraction is the most commonly addressed type, through various truncation and pruning strategies.

## Three Strategies for Long-Horizon Tasks

Anthropic recommends three approaches, in order of lightweight → heavyweight:

### Strategy 1: Tool Result Clearing

> "Once a tool has been called deep in the message history, why would the agent need to see the raw result again?"

This is described as "the safest, lightest touch form of compaction." Available as a Claude Developer Platform feature (`context_editing`).

**Who does this:**

| Agent | Approach |
|-------|----------|
| Codex | Per-item truncation at record time (10KB default) — most aggressive |
| Gemini CLI | Pre-summarization of large tool outputs + reverse token budget (protect recent, truncate old) |
| OpenCode | `prune()` erases tool outputs older than 40K tokens of recent outputs |
| Claude Code | Server-side `context_editing` API |
| Pi | Nothing — full tool results stay in context forever |
| OpenClaw | Nothing at agent level (inherited Pi behavior) |

### Strategy 2: Compaction (Summarization)

> "Distills the contents of a context window in a high-fidelity manner, enabling the agent to continue with minimal performance degradation."

Anthropic emphasizes: start by maximizing recall (preserve everything), then iterate to eliminate superfluous content.

**How each agent implements this:**

| Agent | Compaction quality approach | Sections in summary |
|-------|---------------------------|-------------------|
| Pi | Single LLM call, no verification | 6 (Goal, Constraints, Progress, Decisions, Next Steps, Critical Context) |
| Codex (local) | Single LLM call | 4 (Progress, Constraints, Remaining, Data) |
| Codex (OpenAI) | Server-side encrypted opaque state | N/A (model-internal) |
| Gemini CLI | **Two-pass: generate + verification probe** | `<state_snapshot>` (free-form) |
| Claude Code | Server-side API, 3 analysis variants | **9 sections** (most detailed — includes "All user messages" and verbatim quotes) |
| OpenCode | Single LLM call, plugin-extensible | 5 (Goal, Instructions, Discoveries, Accomplished, Files) |

**Gap identified**: Anthropic says "start by maximizing recall" but only Gemini CLI actually verifies recall with a second LLM call. All others generate once and hope for the best.

### Strategy 3: Sub-Agent Architectures

> "Specialized agents handle focused tasks with clean context windows, returning condensed summaries (1,000-2,000 tokens)."

Anthropic explicitly recommends 1,000-2,000 token summaries from sub-agents. Let's check what actually happens:

| Agent | Sub-agent return size | Matches recommendation? |
|-------|----------------------|------------------------|
| Pi | `getFinalOutput()` — last assistant text, unbounded | No limit |
| Gemini CLI | `ToolResult.llmContent` — unbounded | No limit |
| Claude Code | Agent tool result — unbounded text | No limit |
| OpenCode | Last text part wrapped in `<task_result>` — unbounded | No limit |
| OpenClaw | Completion event text — unbounded | No limit |

**Finding**: No agent enforces the 1,000-2,000 token recommendation. Sub-agent returns are all unbounded text. This is a gap between Anthropic's advice and industry practice.

## Just-In-Time Context Retrieval

Anthropic recommends against pre-loading all data:

> "Maintain lightweight identifiers (file paths, URLs, queries) and dynamically retrieve information during execution."

Claude Code demonstrates this: CLAUDE.md is pre-loaded, but files are retrieved via `glob`, `grep`, `Read` on demand.

**How studied agents compare:**

| Pattern | Agents | Anthropic alignment |
|---------|--------|-------------------|
| **Pre-load everything** | Pi (full context), ChatGPT Memory (all 33 facts) | Against recommendation |
| **Hybrid (pre-load + JIT)** | Claude Code (CLAUDE.md + tools), Gemini CLI (GEMINI.md + tools) | Matches recommendation |
| **JIT only** | None of the studied agents | Most aggressive form |
| **Per-node filtering** | Self-developed agent (context_filter per capability) | Beyond recommendation (more granular) |

## System Prompt Design

Anthropic's guidance:

> "Find the right altitude — avoid both brittle hardcoded logic and vague guidance. Specific enough to guide behavior effectively, yet flexible enough to provide strong heuristics."

**Reality check across agents:**

| Agent | System prompt approach | Anthropic alignment |
|-------|----------------------|-------------------|
| Pi | ~300 words, dynamic tool guidelines | Good altitude — minimal, adaptive |
| Codex | Single comprehensive file, clear structure | Good — organized sections |
| Gemini CLI | Toggleable sections, model-aware variants | Good — adapts to model capabilities |
| Claude Code | 65+ files, 20+ dynamic reminders | Most prescriptive — risks being "too low altitude" (too specific) |
| OpenClaw | 15+ sections, 3 modes (full/minimal/none) | Good — adapts to agent role |
| OpenCode | Provider-specific prompts | Good — adapts to model family |

## Tool Design

Anthropic's guidance:

> "Tools should be self-contained, unambiguous, and extremely clear with respect to their intended use. If humans cannot definitively determine which tool to use, agents will not perform better."

| Agent | Tool count | Clarity approach |
|-------|-----------|-----------------|
| Pi | 4 core (read/write/edit/bash) + optional (grep/find/ls) | Most focused |
| Codex | ~5 (shell, apply_patch, file ops) | Very focused |
| Claude Code | 18+ built-in tools | Largest set, but each has detailed description |
| OpenClaw | 20+ tools (including messaging, sessions, cron) | Most tools — risk of "decision paralysis" per Anthropic |
| OpenCode | Standard set + custom via plugins/MCP | Extensible |

## Evaluation

Anthropic emphasizes:
- Baseline establishment before changes
- Negative examples defining boundaries
- LLM-as-judge with rubrics
- "Nothing perfectly replaces human evaluation"

**Finding**: None of the studied agents have built-in context management evaluation. No agent measures whether its compaction lost critical information, whether its context filtering improved task completion, or whether its sub-agent summaries were sufficient. This is a universal gap.

## Multi-Session / Long-Running Agent Pattern

From the "effective harnesses" article, Anthropic recommends:
1. **Progress file** (`claude-progress.txt`) documenting completed work
2. **Init script** for reproducible environment setup
3. **Git commits** after each feature for rollback capability
4. **Two-agent pattern**: initializer + coding agent

**Who does this:**
- OpenCode's fork/revert system is the closest to this pattern (filesystem snapshots + rollback)
- Claude Code's memory system (CLAUDE.md + auto memory) partially addresses cross-session continuity
- No other agent has structured multi-session state management

## Summary: Recommendation Compliance

| Anthropic Recommendation | Fully compliant | Partially | Not at all |
|--------------------------|----------------|-----------|------------|
| Tool result clearing | Codex, OpenCode | Gemini CLI | Pi, OpenClaw |
| High-fidelity compaction | Claude Code (9 sections) | Gemini CLI (with verification) | Pi, Codex local (minimal) |
| Sub-agent 1-2K token returns | None | | All (unbounded returns) |
| JIT context retrieval | Claude Code, Gemini CLI | OpenCode | Pi |
| Context rot awareness | Claude Code (poisoning only) | | All others |
| System prompt "right altitude" | Pi, Codex, OpenCode | Gemini CLI, OpenClaw | Claude Code (possibly too prescriptive) |
| Evaluation of context quality | None | | All |
