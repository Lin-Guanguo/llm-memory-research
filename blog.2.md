# Deep Comparison of Context Management & Memory Systems Across 6 Major Agents

## I Read the Source Code of 6 Agents and Found the Secrets Behind "Raising Shrimp" and "Memory"

Last Updated: 2026-03-30

> Why does **OpenClaw** feel like it understands you more over time? Why does **Claude Code** have the best coding experience? I read the **source code of 6 agents** and found the answers in their **context management** and **memory system** implementations. This article focuses on OpenClaw, with a cross-comparison of Claude Code, Codex, Gemini CLI, and others.
>
> My ultimate goal is to have an AI that can **work without my intervention** and **understand me** like a long-time collaborator — but from this research, we're still far from that.

---

## 1. OpenClaw Memory Analysis

OpenClaw is the **only coding agent with a real memory system** among all the agents I studied.

First, let's see what "memory" looks like in other agents:

| Agent | "Memory" | Search | Indexing |
|-------|----------|--------|---------|
| Claude Code | `CLAUDE.md` + `MEMORY.md` | None (entire file loaded) | None |
| Codex | `AGENTS.md` | None | None |
| Gemini CLI | `GEMINI.md` | None | None |
| OpenCode | `AGENTS.md` + `CLAUDE.md` + `CONTEXT.md` | None | None |
| Pi | None | None | None |

Their "memory" is just a plain text file loaded at startup. No search, no indexing, no temporal awareness. Your `CLAUDE.md` is 200 lines? Loaded. 2000 lines? Also loaded (eating your context window).

OpenClaw is fundamentally different.

### Two-Tier Storage: Daily Log + Evergreen Knowledge

OpenClaw's memory is **plain Markdown files** — the files themselves are the source of truth. The SQLite index is derived and can be rebuilt.

```
~/.openclaw/workspace/
├── MEMORY.md              ← Evergreen: curated long-term knowledge, never decays
├── memory/
│   ├── 2026-03-30.md      ← Daily Log: today's append-only notes
│   ├── 2026-03-29.md      ← Daily Log: yesterday's notes
│   ├── projects.md        ← Evergreen: organized by topic
│   └── network.md         ← Evergreen: organized by topic
```

The design is deliberate:
- **Daily logs** (`memory/YYYY-MM-DD.md`) are append-only, one file per day, recording the day's discoveries and decisions
- **Evergreen knowledge** (`MEMORY.md` and non-dated files under `memory/`) is curated persistent information — your preferences, project decisions, reference material
- Only today's and yesterday's logs are loaded at session start; everything else is retrieved via search on demand

This mirrors two modes of human memory: short-term memory (what happened today) and long-term memory (important facts I know).

### Four-Stage Retrieval Pipeline

When the model needs to recall something, it calls the `memory_search` tool, triggering a four-stage retrieval pipeline — this is proper information retrieval (IR) engineering, not simple file loading:

```
Query
  │
  ├─► Vector Search (cosine similarity, 6 embedding providers supported)
  │
  ├─► BM25 Keyword Search (FTS5 full-text search)
  │
  ▼
Weighted Merge (default 0.7 × vector + 0.3 × keyword)
  │
  ▼
Temporal Decay (exponential decay, 30-day half-life)
  │
  ▼
MMR Re-ranking (diversity-aware deduplication)
  │
  ▼
Top-K Results
```

**Vector + keyword search in parallel** — vector search captures semantic similarity, BM25 captures exact keyword matches, both run in parallel then merge with weighted scores. More robust than either alone.

**Temporal decay** — a dimension no other agent has. The decay formula is `score × e^(-λ × ageInDays)` with a 30-day half-life:

| Age | Score Multiplier |
|-----|-----------------|
| Today | 100% |
| 7 days | ~84% |
| 30 days | 50% |
| 90 days | 12.5% |
| 180 days | ~1.6% |

Key detail: evergreen knowledge (`MEMORY.md` and non-dated files) **never decays**. This means "you prefer Vim" always scores full marks, while "last Tuesday's debugging session" naturally fades — just like human memory works.

**MMR re-ranking** (Maximal Marginal Relevance) — daily logs may record similar content across days. MMR ensures result diversity, preventing 5 near-identical entries from being returned.

### Killer Feature: Pre-Compaction Memory Flush

This is the **most architecturally significant design** I found across all agents.

Every agent compresses (compacts) when the context is nearly full — using an LLM to generate a summary, then discarding the original conversation. The problem: compression inevitably loses information. Things that aren't important for the current task but are important about *you* — preferences you mentioned, decisions you made — just vanish.

OpenClaw's approach: **before** compression, inject a silent turn invisible to the user, reminding the model: "You're about to lose your context. Write anything important to `memory/YYYY-MM-DD.md` now."

```
Session running...
  → Token count crosses threshold
  → Silent system prompt: "Session nearing compaction. Store durable memories now."
  → Model writes important context to daily log (or replies NO_REPLY if nothing to store)
  → Compaction proceeds — context is compressed, but memories are safely on disk
```

Two trigger conditions (either one suffices):
- **Token threshold**: total tokens approaching the context window limit
- **Transcript size**: session transcript exceeds 2MB

Safety measures are thorough:
- Can only write to `memory/YYYY-MM-DD.md`; MEMORY.md and other files are read-only during flush
- If the file already exists, append only — never overwrite
- At most one flush per compaction cycle

**This is the technical root of the "raising shrimp" experience** — OpenClaw silently moves its understanding of you from the ephemeral context window to persistent memory files. The longer you use it, the more it knows about you, the more precise its retrieval. Other agents start every session from scratch; OpenClaw's every session stands on the shoulders of all previous ones.

---

## 2. OpenClaw Context Analysis

Memory makes OpenClaw unique at the cross-session level, and its context management is equally the most sophisticated at the within-session level.

### Universal Pattern

All agents share the same base model:

```
Messages accumulate → Threshold reached → Compress/summarize → Continue with summary
```

The differences lie in **when**, **how**, and **where** compression happens. OpenClaw is the most complex on all three dimensions.

### ContextEngine: Pluggable Context Assembly

The core of OpenClaw's context management is the ContextEngine — a pluggable interface defining 7 lifecycle methods:

| Method | Purpose |
|--------|---------|
| `bootstrap()` | Initialize engine state, import historical context |
| `ingest()` | Receive a single message into engine storage |
| `ingestBatch()` | Batch-receive a complete turn |
| `afterTurn()` | Post-turn lifecycle (persist, trigger background compaction) |
| `assemble()` | **Core: assemble model context under a token budget** |
| `compact()` | Compress context (summaries, pruning, etc.) |
| `prepareSubagentSpawn()` | Prepare engine state before child agent starts |
| `onSubagentEnded()` | Notify engine that a subagent ended |

The default LegacyContextEngine is essentially a pass-through, but the interface's value is clear: third-party plugins can completely replace the context strategy — RAG pipelines, vector stores, graph-based context, all plug in.

### Pre-LLM-Call Pipeline

OpenClaw doesn't send messages to the LLM as-is. Before every call, messages pass through a multi-stage pipeline:

```
Raw conversation history
    │
    ▼ sanitizeSessionHistory()        ← Clean: remove invalid tool results, fix pairing
    │
    ▼ validateGeminiTurns()           ← Per-provider validation (Gemini rules)
    ▼ validateAnthropicTurns()        ← Per-provider validation (Anthropic rules)
    │
    ▼ limitHistoryTurns()             ← Config-based turn truncation (DM/channel limits)
    │
    ▼ sanitizeToolUseResultPairing()  ← Fix orphaned tool results after truncation
    │
    ▼ contextEngine.assemble()        ← Assemble context under token budget
    │
    ▼ Send to LLM
```

### Three Lines of Defense

Compared to Pi's single line of defense (compress only when context is full), OpenClaw has three layers of reduction before compaction even triggers:

| Defense | Mechanism | Cost |
|---------|-----------|------|
| 1st | `limitHistoryTurns()` — hard truncation by turn count | Minimal |
| 2nd | `contextEngine.assemble()` — token-budget-aware assembly | Depends on engine |
| 3rd | Compaction — LLM-generated summary | High (inherited from Pi) |

In many cases, OpenClaw controls context volume through the lightweight first two defenses, avoiding the expensive LLM compression altogether.

### Provider Awareness

An easy-to-miss detail: OpenClaw validates message formats per LLM provider. Gemini requires strict alternating turns, Anthropic has its own turn rules. OpenClaw auto-adapts before sending, while Pi sends the exact same format to all providers.

### Sub-Agents: Bidirectional Communication

OpenClaw's sub-agents run via gateway RPC. The key difference from other agents is **bidirectional communication**:

```
Main Agent
  │
  ├─ sessions_spawn({ task: "...", agentId: "worker" })
  │     ├─ Sub-agent runs in an independent session
  │     ├─ Auto-pushes results to parent on completion (push, not polling)
  │
  └─ Parent can also:
     sessions_send()   → send messages to child (mid-run steering)
     sessions_history() → read child's conversation history
     subagents(action=steer|kill) → intervene or terminate
```

Other agents' sub-agents are all one-way — dispatch, wait for results, no mid-run steering. OpenClaw's parent agent can send instructions, read progress, and even terminate during execution.

### System Prompt

OpenClaw's system prompt comprises 15+ sections, including identity, tool list, safety rules, memory retrieval instructions, sub-agent orchestration, TTS voice hints, and more. Three modes:
- `full` — all sections (main agent)
- `minimal` — reduced version (sub-agents)
- `none` — identity line only

---

## 3. How Other Agents Handle Context Management

Listed from simplest to most complex.

### Pi — The Baseline

Pi is OpenClaw's underlying engine and the simplest of all agents studied.

- Infinite accumulation, sends **all** context with every LLM call
- System prompt ~300 words
- No pre-processing, no token budgeting
- Single LLM summary when approaching the limit (6-section structure)
- Works because 1M context windows are forgiving

Pi proves one thing: if the context window is large enough, "no context management" is a viable strategy.

### Codex — Truncation at Write Time + Dual Compression

Codex is the only agent written in Rust, with two unique designs:

**Truncation at write time**: every tool output is capped at 10KB *before* entering context. This is proactive compression — controlling volume at the source of information accumulation, rather than waiting until it's nearly full.

**Dual compression**:
- With OpenAI: server-side encrypted compression, returning an opaque compaction block that preserves model internal state
- With other providers: client-side LLM summary, 4-section structured template

Codex also supports **mid-stream compression** — compaction can trigger while the model is still generating. Not seen in any other agent.

### Gemini CLI — The Only One That Verifies Compression Quality

Gemini CLI does something no other agent does: **verify the compression result**.

After generating a summary, it runs a second LLM call (a "probe") to check if important information was lost. If the probe finds omissions, they're added to the summary. Doubles the cost, but catches silent information loss.

Other notable features:
- Triggers compression at 50% capacity — far more aggressive than others (Claude Code ~80%, Pi near limit)
- Pre-summarizes large tool outputs before they enter context (similar to Codex's proactive approach, but using LLM rather than hard truncation)

### OpenCode — Two-Phase Compression + Fork/Revert

OpenCode compresses in two steps:
1. **Rule-based pruning**: programmatically delete old tool outputs (cheap)
2. **LLM summary**: summarize what remains (expensive)

Cheap first, expensive second. Reasonable.

The unique feature is **filesystem-aware fork/revert** — you can branch your conversation like a git branch. Went the wrong direction? Revert back. Sub-agents run on independent SQLite sessions and can be paused and resumed.

### Claude Code — Why It Has the Best Coding Experience

Claude Code's coding experience is widely considered the best, with fast and reliable sub-agents. The core reason isn't any specific architectural innovation — it's that **Prompt Engineering is taken to the extreme**.

**65+ modular system prompt files + 20+ dynamic injections**: This is the core of Claude Code's strong coding experience. Its system prompt isn't one big file but 65+ modular files assembled on demand, covering every aspect of coding work — security checks, file modification norms, git operation workflows, output efficiency requirements, code style constraints, and more. Even more critical are the 20+ system-reminder templates dynamically injected at runtime — file modified externally? Inject a reminder. Skill activated? Inject instructions. File content truncated? Inject explanation. This keeps the model constantly aware of the latest context state, making the most appropriate decisions.

**Richest tool set**: Claude Code provides the widest tool coverage — file read/write, search, edit, Bash execution, Notebook editing, LSP support, and more. More tools means more ways to accomplish tasks without detours.

**6+ sub-agent types, each with targeted prompts**:

| Sub-Agent | Purpose | Tuning Focus |
|-----------|---------|-------------|
| Explore | Read-only code search | Fast search, read-only tools |
| Plan | Architecture planning | Read-only tools, design focus |
| Code Reviewer | Code review | Review standards and output format |
| Code Explorer | Deep feature analysis | Execution path tracing |
| Code Architect | Feature architecture design | Blueprint output format |

Good sub-agent management is fundamentally a prompt-tuning achievement — each sub-agent type has carefully designed system prompts and tool sets, ensuring optimal performance within its scope. This isn't an architectural advantage; it's massive engineering effort at the prompt layer.

**Notable features (not core to coding strength, but worth knowing)**:
- **Server-side compression**: the only agent that fully offloads compaction to a server API, resulting in the simplest client code
- **Model knows its remaining budget**: via `<budget:token_budget>` tags, Claude 4.5+ models know their context usage in real time and can self-regulate
- **Thinking block auto-cleanup**: extended thinking tokens are automatically removed on the next turn, preventing context pollution

### Six-Agent Comparison at a Glance

| Agent | Compaction Trigger | Compaction Location | Verification | Sub-Agents | Memory |
|-------|-------------------|--------------------|--------------|-----------|----|
| Pi | Near limit | Client | None | Process isolation (one-way) | None |
| Codex | Configurable | Server + Client | N/A | None | `AGENTS.md` |
| Gemini CLI | 50% capacity | Client | **2nd LLM probe** | In-process (one-way) | `GEMINI.md` |
| OpenCode | Usable limit | Client, two-phase | None | Session-based (resumable) | `AGENTS.md` etc. |
| Claude Code | ~80% capacity | **Server API** | None | **6+ types (finely tuned prompts)** | `CLAUDE.md` etc. |
| OpenClaw | Same as Pi | Client / custom engine | Depends on engine | **Gateway RPC (bidirectional)** | **Four-stage retrieval pipeline** |

---

## 4. Insights

### Memory and Context Are the Same Problem

After studying all these agents, my core conclusion is: **memory and context are not separate problems — they are the same problem at different time scales.**

| | Memory (cross-session) | Context (within-session) |
|--|----------------------|------------------------|
| What to keep | Fact extraction (Mem0), entity tracking (Graphiti) | Compaction summaries (all agents) |
| What to discard | Outdated facts, conflicts | Old tool outputs, resolved errors |
| How to compress | LLM summarization, knowledge graphs | LLM summarization, structured templates |
| How to retrieve | Vector search, graph traversal | Full context, token budgeting, sub-agents |

When Claude Code generates a 9-section structured summary during compaction, it's creating a *memory* of the conversation. When Mem0 extracts facts from a conversation, it's *compacting* the conversation into durable storage. Different terminology, same engineering.

OpenClaw's Pre-Compaction Memory Flush is the only design that acknowledges this at the architecture level — when context is about to be destroyed, it gets a chance to become durable memory first.

### Why Only OpenClaw Bridges the Two?

Positioning determines architecture.

- **Claude Code / Codex / Gemini CLI** are positioned as **task executors** — you give them a coding task, they complete it, the session ends. No need to remember who you are.
- **OpenClaw** is positioned as a **personal assistant** that happens to be good at coding — it needs to remember your preferences, project context, and work habits.

This isn't a gap in technical capability; it's a product choice. Claude Code could build a sophisticated memory system, but it chooses not to because its use case doesn't require it.

### Three Technical Trends

**Trend 1: Reactive → Proactive Compression.** Most agents wait until nearly full before compressing. Codex truncates at write time (10KB hard limit), Gemini CLI pre-summarizes large outputs. The pattern: **compress early, compress small, compress often** beats **compress late, compress everything at once**.

**Trend 2: Client-Side → Server-Side.** In 2025, all compression happened client-side. By 2026, both Claude Code and Codex shifted to server-side APIs. Benefits: encrypted state preservation, mid-stream compression, simpler client code.

**Trend 3: Manual Rules → Model Self-Management.** Claude Code is the only agent where the model knows its remaining budget. Combined with server-side compression, the model can self-regulate. This may be the convergence point for all agents — the model manages its own context, the client just provides raw inputs.

### grep Beats RAG in Practice

A potentially counterintuitive finding: every coding agent uses `grep`/`glob` for real-time code search — not vector search, not RAG.

| Dimension | Text Search (grep/glob) | RAG (Vector Search) |
|-----------|------------------------|-------------------|
| Index cost | Zero | Must pre-compute embeddings |
| Precision | Exact match `handleAuth` | May return similar but wrong results |
| Freshness | Always current | Index may lag behind edits |

RAG appears in the memory layer (cross-session retrieval), not in agent operation. Anthropic calls it "Agentic Search" — under the hood, it's grep.

---

## 5. Further Research & Unsolved Problems

### Context Rot: Four Types of Context Degradation

Anthropic identifies four types of context degradation in their Context Engineering guide:

| Type | What Happens | Who Addresses It |
|------|-------------|-----------------|
| **Poisoning** | File modified after tool result was captured | Only Claude Code (file modification detection + system-reminder injection) |
| **Distraction** | Old tool outputs consuming attention | Codex, Gemini CLI, OpenCode (truncation/pruning) |
| **Confusion** | Two similar files causing misassociation | Nobody |
| **Clash** | Old and new versions of same data coexist | OpenCode fork/revert (partial) |

Most agents only handle Distraction. Confusion and Clash are largely unaddressed — a space worth watching.

### Compression Quality: A Shared Blind Spot

Every agent that compresses faces the same problem: **nobody knows what's lost**.

- Pi: single-pass summary, no verification — you'll never know what was lost
- Gemini CLI: two-pass probe check — the only verification attempt, but doubles cost
- Claude Code: 9-section structured template — broad coverage but unverified
- Codex: server-side encrypted state — preserves model internals, but completely opaque

This is the shared unsolved problem across both memory and context. If compression quality could be measured, every agent would improve significantly.

### What Gaps Remain?

**Optimal compression threshold** — Pi compresses near the limit, Gemini CLI at 50%, Claude Code at ~80%. Which is better? Earlier compression means less information loss per event but higher frequency; later compression means lower frequency but larger loss each time. No consensus yet.

**Who's next?** Currently only OpenClaw has both complex context management and global memory. But if coding agents evolve from task executors toward personal assistants — and the trend suggests they will — memory becomes essential. That empty cell in the matrix won't stay empty for long.

---

## About This Series

I'm researching three core topics of LLM agents out of personal interest: **memory, context, and learning**. The [previous article](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/blog.1.chinese.md) covered memory systems, this one covers context management. Upcoming articles will include: the latest developments in memory systems in 2026, and research on continuous learning.

This research is driven by two goals:

**Goal 1: Have AI work completely without my intervention.** This requires AI to remember everything about me — my preferences, project context, work habits, historical decisions. As this article shows, current frameworks are still far from this goal: most agents don't even have basic cross-session memory. OpenClaw goes the deepest, but it's still limited to file-level memory storage and retrieval. I previously built a [personal knowledge base](https://www.xiaohongshu.com/discovery/item/694386e1000000001e02eaeb) as an experiment in this direction.

**Goal 2: A truly independent AI partner with its own personality.** Through learning and long-term collaboration, it could develop unique working styles and approaches — like a long-time collaborator who doesn't just execute instructions but understands how you think. This falls mainly under the third part of the research, "continuous learning," covering personality training, Multi-LoRA personalization, and the Memory → Weight hybrid pipeline.

---

## References

Based on source code analysis and reverse engineering. Full research materials:

**OpenClaw Research**:
- [OpenClaw Context Management](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/openclaw.research.md) | [OpenClaw Memory System](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/openclaw-memory.research.md)

**Other Agent Context Research**:
- [Pi](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/pi.research.md) | [Gemini CLI](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/gemini-cli.research.md) | [Claude Code](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/claude-code-context.research.md) | [Codex](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/codex-context.research.md) | [OpenCode](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/opencode.research.md)
- [Anthropic Context Engineering Guide Analysis](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/anthropic-context-engineering.research.md)

**Comprehensive Research**:
- [Research Summary](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/summary.md) | [Context Management Summary](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/context.summary.md) | [Cross-Domain Findings](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/findings.md)

**Previous Article**: [LLM Memory: Complex Design, Surprisingly Simple in Practice](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/blog.1.chinese.md)

---

*Research period: 2025-12 to 2026-03. Studied 6 agents (5 open-source + 1 reverse-engineered), 15+ memory projects, 20+ total projects. Credits: Claude / Codex / Gemini did most of the research work — I was just the conductor.*
