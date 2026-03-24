# From Chat Memory to Agent Context: Where Does LLM "Memory" Actually Live?

Last Updated: 2026-03-24

> Previous reverse-engineering work has shown that ChatGPT and Claude take opposite approaches to memory — but at least they *try*. Then I looked at the agent side — Claude Code, Codex, Gemini CLI — and found that their context management is impressively complex, but their "memory" is shockingly primitive. Just flat files loaded at startup. No search, no indexing, no decay. Why the split? And is anyone trying to bridge the gap?

This is the second article in a series. The [first one](blog.1.chinese.md) covered consumer product memory (ChatGPT vs Claude) and open-source memory frameworks (Mem0, Letta, Graphiti). This one goes deeper into the agent side — how 6 coding agents manage their context window, why none of them have real memory, and the one exception that does.

Based on source code analysis of 6 open-source/reverse-engineered agents + Anthropic's official context engineering guidance.

---

## 1. Two Worlds, Split Apart

There's a surprising divide in how LLMs handle information persistence:

**Consumer products** (ChatGPT, Claude, Gemini web) have **global memory** — they remember who you are across conversations. ChatGPT pre-injects ~33 facts every session. Claude offers `conversation_search` to retrieve past context on demand. They're designed as personal assistants.

**Agent applications** (Claude Code, Codex, Gemini CLI) have **no global memory** — but they have sophisticated context management within a session. They compress, summarize, and juggle a context window that constantly grows as tools return results. They're designed as task executors.

| | Global memory | No global memory |
|--|--------------|-----------------|
| **Complex context management** | ??? | Claude Code, Codex, Gemini CLI, OpenCode |
| **Simple context management** | ChatGPT, Claude, Gemini Web | Pi |

Notice the empty cell. No agent sits in both quadrants — complex context management *and* global memory. We'll come back to that.

Why the split? Because the products serve different purposes. A personal assistant needs to remember your preferences. A coding agent needs to survive a 200-turn debugging session without losing the thread. These are different engineering problems — but they shouldn't have to be.

---

## 2. Agent Context Management: Same Pattern, Wildly Different Execution

### The Universal Pattern

Every agent studied shares the same base model:

```
Messages accumulate → Threshold reached → Compress/summarize → Continue with summary
```

That's it. The differences are in **when**, **how**, and **where** compression happens.

### The Architecture Spectrum

From minimal to maximal, here's what each agent actually does:

**Pi** — The baseline. Infinite accumulation, full context sent every LLM call, single LLM summary when approaching the limit. ~300-word system prompt. No pre-processing, no token budgeting. It works because 1M context windows are forgiving.

**Codex** — Adds per-item truncation: every tool output is capped at 10KB *at record time*, before it enters the context. Plus dual compaction — server-side encrypted compression (opaque, preserves model state) and client-side LLM summary (readable, for other providers). The only agent written in Rust.

**Gemini CLI** — The only agent that *verifies* its compression. After generating a summary, it runs a second LLM call (a "probe") to check if anything important was lost. This doubles the cost but catches silent information loss. Triggers compression at 50% capacity — much more aggressive than others.

**OpenCode** — Two-phase approach: first prune old tool outputs programmatically (cheap), then LLM-summarize what remains (expensive). Also uniquely offers resumable sub-agent sessions and filesystem-aware fork/revert — you can branch your conversation like a git repo.

**Claude Code** — The most architecturally distinct. Compaction happens **server-side** via API — the client doesn't even generate the summary. The model itself knows its remaining budget through `<budget:token_budget>` tags. 65+ modular system prompt files, 20+ dynamic system-reminders injected per event. Sub-agents (Explore, Plan, etc.) each get fresh context windows.

**OpenClaw** — The most complex pipeline. Before every LLM call: sanitize → validate per provider → truncate by turn count → assemble under token budget via a pluggable ContextEngine with 7 lifecycle hooks. Three lines of defense before compaction even triggers (vs Pi's one). Built-in sub-agents via gateway RPC with bidirectional communication.

### The Comparison

| Agent | Compaction trigger | Compaction location | Verification | Sub-agents |
|-------|-------------------|--------------------|--------------|-----------|
| Pi | Near limit | Client, single LLM call | None | Extension (process isolation) |
| Codex | Configurable | Server (encrypted) + Client (LLM) | N/A (server opaque) | None |
| Gemini CLI | 50% capacity | Client, LLM summary | **Yes — 2nd LLM probe** | In-process (fresh chat) |
| OpenCode | At usable input limit | Client, two-phase | None | Session-based (resumable) |
| Claude Code | ~80% capacity | **Server-side API** | None (but 9-section structured summary) | 6+ types (fresh context each) |
| OpenClaw | Same as Pi (inherited) | Client, or custom engine | Depends on engine | Gateway RPC (bidirectional) |

---

## 3. Three Trends

### Trend 1: Reactive → Proactive Compression

Most agents wait until the context window is nearly full, then do a big compression. This is risky — one bad summary can lose critical information.

The exceptions are more interesting:
- **Codex** truncates tool outputs *at entry time* (10KB cap per item) — proactive, zero-cost
- **Gemini CLI** pre-summarizes large tool outputs before they enter context — proactive, LLM-assisted
- Both reduce the severity of the eventual compaction event

The pattern: **compress early, compress small, compress often** beats **compress late, compress everything at once**.

### Trend 2: Client-Side → Server-Side Compaction

In 2025, all compaction happened client-side. By 2026:
- Claude Code offloads to `compact-2026-01-12` API
- Codex uses `/responses/compact` (returns encrypted opaque state)

Server-side compaction enables things clients can't do: encrypted state preservation, mid-stream compaction (Codex can compress while the model is still generating), and dramatically simpler client code.

### Trend 3: Model Self-Management

Claude Code is the only agent where the model *knows* its own remaining context budget — via `<budget:token_budget>` and `<system_warning>` tags. Combined with server-side compaction, the model can self-manage without client heuristics.

No other agent has this. It may represent where all agents converge — the model manages its own context, and the client just provides raw inputs.

---

## 4. The Unsolved Problems

### Context Rot

Anthropic identifies four types of context degradation:

| Type | What happens | Who addresses it |
|------|-------------|-----------------|
| **Poisoning** | Stale tool results from modified files | Only Claude Code (file modification detection) |
| **Distraction** | Old tool outputs consuming attention | Codex, Gemini CLI, OpenCode (truncation/pruning) |
| **Confusion** | Similar files causing misassociation | Nobody |
| **Clash** | Old and new versions of same data | OpenCode fork/revert (partially) |

Most agents only handle distraction. The other three are largely unmitigated.

### Compression Quality: Nobody Knows What They Lose

Every agent that compresses risks silent information loss. The approaches:

- **Pi**: Single-pass summary, no verification — you'll never know what was lost
- **Gemini CLI**: Two-pass probe catches omissions — the only verification attempt, but doubles cost
- **Claude Code**: 9-section structured template ensures coverage — thorough but unverified
- **Codex**: Encrypted server-side state preserves model internals — but completely opaque

No system has a reliable way to measure compression quality. This is the shared unsolved problem across both memory and context.

### Text Search Beats RAG in Practice

This one surprised me. Every coding agent uses `grep`/`glob` for real-time code search — not vector search, not RAG:

| Factor | Text search (grep/glob) | RAG (vector search) |
|--------|------------------------|-------------------|
| Index cost | Zero | Must compute embeddings upfront |
| Precision | Exact — find `handleAuth` | Fuzzy — may return similar but wrong |
| Staleness | Always current | Index can lag behind edits |
| Speed | ripgrep: milliseconds | Vector query: fast, but index must exist |

RAG appears in the *memory* layer (cross-session retrieval) but not in agent operation. Anthropic calls it "Agentic Search" — but under the hood, it's grep.

---

## 5. The Exception: OpenClaw

Every agent above has the same story for "memory": a flat file loaded at session start.

| Agent | "Memory" | Search | Indexing |
|-------|----------|--------|---------|
| Claude Code | `CLAUDE.md` + `MEMORY.md` | None (file is just loaded whole) | None |
| Codex | `AGENTS.md` | None | None |
| Gemini CLI | `GEMINI.md` | None | None |
| OpenCode | `AGENTS.md` + `CLAUDE.md` + `CONTEXT.md` | None | None |
| Pi | None | None | None |

That's it. No search, no indexing, no temporal awareness. If your `CLAUDE.md` is 200 lines, it gets loaded. If it's 2000 lines, it still gets loaded (and eats your context window). These agents have sophisticated context management but practically zero memory.

### Why OpenClaw is different

OpenClaw isn't just a coding agent — it's designed as a **personal assistant** that happens to be good at coding. Like ChatGPT or Claude web, it needs to remember who you are. But unlike them, it also runs complex multi-turn agent tasks with sophisticated context management.

This puts it in the empty cell of our matrix:

| | Global memory | No global memory |
|--|--------------|-----------------|
| **Complex context management** | **OpenClaw** | Claude Code, Codex, Gemini CLI, OpenCode |
| **Simple context management** | ChatGPT, Claude, Gemini Web | Pi |

### How it works

**Memory storage**: Two tiers of plain Markdown files.

- `memory/YYYY-MM-DD.md` — Daily logs, append-only, one per day
- `MEMORY.md` + `memory/topics.md` — Evergreen knowledge, curated and persistent

**Memory retrieval**: A four-stage pipeline — not grep, not simple file loading.

```
Query → Vector Search + BM25 Keyword Search (parallel)
      → Weighted Merge (0.7 × vector + 0.3 × keyword)
      → Temporal Decay (30-day half-life, evergreen files exempt)
      → MMR Re-ranking (diversity-aware deduplication)
      → Top-K Results
```

This is a proper IR pipeline. Daily notes from 30 days ago score at 50% of their original relevance. Notes from 180 days ago score at ~1.6%. But `MEMORY.md` (curated knowledge) never decays. Six embedding providers supported (OpenAI, Gemini, Voyage, Mistral, Ollama, local GGUF).

**The killer feature: Pre-Compaction Memory Flush**

When a session approaches the compaction threshold, OpenClaw injects a **silent agentic turn** — invisible to the user — that tells the model: "You're about to lose your context. Write anything important to `memory/YYYY-MM-DD.md` now."

```
Session running...
  → Token count crosses threshold
  → Silent system prompt: "Session nearing compaction. Store durable memories now."
  → Model writes important context to daily log (or replies NO_REPLY if nothing to store)
  → Compaction proceeds — context is compressed, but memories are safe on disk
```

This is the only implementation found that explicitly bridges context management and memory persistence. When context is about to be destroyed, it gets a chance to become durable memory first.

---

## 6. The Bigger Picture

### Memory and Context Are the Same Problem

Studying both domains reveals they're not separate — they're the same problem at different time scales:

| | Memory (cross-session) | Context (within-session) |
|--|----------------------|------------------------|
| What to keep | Fact extraction (Mem0), entity tracking (Graphiti) | Compaction summary (all agents) |
| What to discard | Outdated facts, conflicts | Old tool outputs, resolved errors |
| How to compress | LLM summarization, knowledge graphs | LLM summarization, structured templates |
| How to retrieve | Vector search, graph traversal | Full context, token budgeting, sub-agents |

When Claude Code generates a 9-section summary during compaction, it's creating a *memory* of the conversation. When Mem0 extracts facts from a conversation, it's *compacting* the conversation into durable storage.

The terminology is different. The engineering is the same.

### Why This Matters

Consumer products solved memory but have simple context management (the API handles it). Agent applications solved context management but skipped memory (they're task-focused). OpenClaw is the first to explicitly connect the two — its pre-compaction flush is the architectural bridge.

If agents evolve from task executors toward personal assistants — and the trend suggests they will — memory becomes mandatory. The question isn't whether agents will need memory, but how they'll implement it. OpenClaw's approach — files as source of truth, hybrid search for retrieval, temporal decay for relevance, and a bridge between context and memory at the compaction boundary — is one answer.

The empty cell in the matrix won't stay empty for long.

---

## Resources

Based on source code analysis and reverse engineering. Full research materials:

**Context management research**:
- [Pi](pi.research.md) | [OpenClaw](openclaw.research.md) | [Gemini CLI](gemini-cli.research.md) | [Claude Code](claude-code-context.research.md) | [Codex](codex-context.research.md) | [OpenCode](opencode.research.md)
- [Anthropic Context Engineering guidance](anthropic-context-engineering.research.md)
- [Context summary (6 agents comparison)](context.summary.md)

**Memory research**:
- [OpenClaw memory system](openclaw-memory.research.md)
- [ChatGPT memory reverse engineering](reverse-engineer/chatgpt-memory-reverse-engineering.md) | [Claude memory reverse engineering](reverse-engineer/claude-memory-reverse-engineering.md)
- [Cross-domain findings (Memory × Context)](findings.md)

**Previous article**: [LLM Memory: Complex Design, Surprisingly Simple in Practice](blog.1.chinese.md)

---

*Research period: 2025-12 to 2026-03. 6 agents studied (5 open-source + 1 reverse-engineered), 15+ memory projects, 20+ total projects.*
