# Claude Code Source Code Analysis (v2.1.88 Source Map Leak)

Last Updated: 2026-04-01

Sources:
- [ChinaSiro/claude-code-sourcemap](https://github.com/ChinaSiro/claude-code-sourcemap) (added as submodule)
- npm package `@anthropic-ai/claude-code@2.1.88` — `cli.js.map` (57MB, SourceMap v3 with embedded `sourcesContent`)
- Extraction: 4756 sources → 1884 `.ts/.tsx` files, 33MB of TypeScript

Research focus: Source-level verification and deep analysis of Claude Code's architecture, complementing our previous reverse-engineering from system prompts and session files.

---

## Background

On 2026-03-31, the community discovered that Anthropic's npm package `@anthropic-ai/claude-code` v2.1.88 shipped with a full source map (`cli.js.map`) containing the original TypeScript source code in its `sourcesContent` field. This is a classic build configuration oversight — the Bun bundler embedded debug information in the production artifact.

**Verification**: The npm package metadata, code structure, internal feature gates (GrowthBook, Statsig), codenames (KAIROS, TENGU), and behavioral alignment with the running product all confirm authenticity.

---

## Architecture Overview

Claude Code is a **React Ink terminal application** built with Bun, structured as a monolithic TypeScript codebase.

```
src/                          (1884 files, 33MB)
├── main.tsx                  # CLI entry point, startup profiling
├── QueryEngine.ts            # Core agent loop orchestrator (1295 lines)
├── Tool.ts                   # Tool abstraction (793 lines)
├── tools/                    # 30+ tool implementations (184 files)
├── commands/                 # Slash commands (207 files)
├── services/                 # API, MCP, analytics (130 files)
│   ├── api/claude.ts         # API request builder (3419 lines)
│   ├── compact/              # Compaction: micro, full, cached, snip
│   ├── extractMemories/      # Background memory extraction agent
│   └── mcp/                  # MCP client, types, connections
├── utils/                    # Largest module (564 files)
│   ├── claudemd.ts           # CLAUDE.md discovery & loading (1400+ lines)
│   ├── messages.ts           # Message normalization pipeline (5500+ lines)
│   ├── permissions/          # Multi-level permission system
│   └── plugins/              # Plugin loader (110KB), marketplace (93KB)
├── components/               # React Ink UI (389 files)
├── hooks/                    # React hooks (104 files)
├── constants/                # Prompts, system sections (21 files)
│   ├── prompts.ts            # System prompt builder (914 lines)
│   └── systemPromptSections.ts  # Memoized prompt section caching
├── buddy/                    # Companion virtual pet (6 files, feature-gated)
├── memdir/                   # Memory system (8 files)
├── plugins/                  # Plugin registration (2 files)
├── skills/                   # Skills system (20 files)
├── coordinator/              # Multi-agent orchestration
├── vim/                      # Vim mode
├── voice/                    # Voice interaction
└── remote/                   # Remote sessions
```

---

## 1. Context Window Construction & Prompt Assembly

### 1.1 System Prompt: Sectioned & Cached

System prompts are built from **reusable sections** with a dual-tier caching mechanism:

```typescript
// Stable section — survives /clear and /compact, enables prompt cache reuse
systemPromptSection(name, compute)

// Volatile section — breaks cache every turn (used sparingly)
DANGEROUS_uncachedSystemPromptSection(name, compute, reason)
```

**Assembly order** (in `services/api/claude.ts`, lines 1358-1369):
1. Attribution header (fingerprint-based)
2. CLI-specific prefix
3. Default system prompt sections (tools, instructions, memory, etc.)
4. Optional advisor model instructions
5. Optional Chrome tool search instructions
6. Prompt caching metadata wrapping

**Key insight**: The sections pattern means most of the system prompt is **computed once per session** and reused across turns. Only volatile sections (current date, git status) cause partial cache invalidation.

### 1.2 Context Providers

Dynamic context injected per-session (`context.ts`):
- **Git status**: Truncated to 2000 chars with warning
- **CLAUDE.md files**: Loaded via `utils/claudemd.ts` with nested discovery
- **Current date**: ISO format
- **Memory instructions**: Built once, cached for session

### 1.3 Message Normalization Pipeline

Before API submission, messages pass through a sophisticated normalization pipeline (`utils/messages.ts:1989`):

```
reorderAttachmentsForAPI()
  → filter virtual messages (UI-only)
  → strip advisor blocks, caller fields
  → convert system local-command messages to user messages
  → ensure tool-use/tool-result pairing (synthetic blocks for missing pairs)
  → merge consecutive thinking blocks
  → merge consecutive user messages
```

**Critical detail**: The system creates **synthetic error blocks** when a tool-use has no matching tool-result (prevents API rejection). This is essential for interrupted tool executions.

### 1.4 Four-Tier Compaction

The compaction system is far more sophisticated than our system-prompt reverse-engineering revealed.

**Why this wasn't visible before**: Our prior research (`claude-code-context.research.md`) concluded "Claude Code's client is the simplest — it relies on server-side compaction." This was wrong. Microcompaction and cached microcompaction are **pure client-side code logic** — they don't use any LLM prompts, so there are no prompt files to reverse-engineer. They are just code-level `if (age > 24h) clear()` or `if (tokens > limit) truncate()` operations. The "flashy" 9-section summary (full compaction) is actually the **least frequently triggered** tier; the silent microcompaction layer does most of the work.

| Tier | File | Trigger | Strategy |
|------|------|---------|----------|
| **Microcompaction** | `services/compact/microCompact.ts` (19K lines) | Per-turn | Token-based truncation of old tool results; time-based clearing (>24h) |
| **Cached microcompaction** | `services/compact/cachedMicrocompact.js` | Feature-gated | Pins cache edits across turns for prompt-cache efficiency |
| **Full compaction** | `services/compact/compact.ts` (60K lines) | Context limit | Forked agent summarizes full history; creates `SystemCompactBoundaryMessage` |
| **Snip compaction** | Feature-gated (`HISTORY_SNIP`) | Conditional | Old context removal via lazy-loaded module |

**Microcompaction targets** (only compactable tools): File I/O, Bash, Grep, Glob, Web tools. Non-compactable tools (like Agent) retain full results.

### 1.5 Prompt Cache as First-Class Architectural Constraint

Prompt cache is not a post-hoc optimization — it is a **hard architectural constraint** that shapes every context assembly decision.

**Why it matters economically**: Claude Code sends the full context (system prompt + tool definitions + instructions + history) with every API call. The system prompt alone can be 30K-50K tokens. With Anthropic's prompt caching, a cache hit on the prefix costs ~10x less than a miss. Over a session of dozens to hundreds of tool-use turns, this difference is massive. Every line of code that changes the system prompt prefix is, in effect, **a line that costs money per subsequent turn**.

**Three key mechanisms**:

1. **System prompt sections with `DANGEROUS_` gate**: Volatile sections that change per-turn (current date, git status) are explicitly marked `DANGEROUS_uncachedSystemPromptSection()`. The function name forces developers to **consciously acknowledge** they are breaking cache. This is a guard against accidental cache invalidation from well-intentioned code changes.

2. **System reminders in message content, not system prompt**: The `<system-reminder>` tags we see mid-conversation (deferred tools, memory staleness warnings, etc.) could logically go in the system prompt. But Claude Code deliberately injects them into user messages or tool result blocks — because modifying the system prompt would change the prefix and invalidate cache. Placing them in content preserves the prefix.

3. **Beta header sticky latches**: AFK mode, fast mode, thinking mode use one-way latches — once set in a session, they never toggle back. If a user turns on fast mode then turns it off, the header stays "on" in API requests. This is semantically imprecise but cache-optimal: flipping headers back and forth would invalidate cache on every toggle.

4. **Memoized context**: `getSystemContext()` and `getUserContext()` use lodash memoize with explicit `.cache.clear?.()` — context is computed once and reused unless explicitly invalidated.

**The underlying principle**: Every decision about "should I change this field in the API request?" is first evaluated against the question: **will this break prompt cache?** If yes, either find another way or mark it as `DANGEROUS_`. This is what makes cache a "first-class citizen" — it's a constraint that other designs must work around, not an optimization layered on afterward.

---

## 2. Memory System

### 2.1 Storage Architecture

Memory uses a **file-based hierarchical structure** — no database, no vector store:

```
~/.claude/projects/{sanitized-git-root}/memory/   # Auto-memory (per-project)
~/.claude/projects/{sanitized-git-root}/memory/team/  # Team memory (TEAMMEM feature)
~/.claude/agent-memory/{agentType}/               # Agent memory (3 scopes)
```

Path resolution priority:
1. `CLAUDE_CODE_REMOTE_MEMORY_DIR` env var (remote/cowork override)
2. `autoMemoryDirectory` in settings.json (policy/local/user only — NOT projectSettings)
3. Default path above

### 2.2 MEMORY.md Index

`MEMORY.md` is an **index file, not storage** (`memdir/memdir.ts:34`):

- Max 200 lines (`MAX_ENTRYPOINT_LINES`)
- Max 25KB (`MAX_ENTRYPOINT_BYTES`)
- Format: `- [Title](file.md) — one-line hook`
- **Dual truncation**: Line-count first, then byte-count at last newline boundary
- The system detects which cap fired to provide targeted user guidance

### 2.3 Memory Types

Four exclusive types (`memdir/memoryTypes.ts`):

| Type | Purpose | When to Save |
|------|---------|--------------|
| `user` | Role, goals, knowledge, preferences | Learning about the user |
| `feedback` | Approach guidance (do/don't), validated decisions | Corrections or confirmations |
| `project` | Ongoing work, goals, deadlines | Who doing what, why, by when |
| `reference` | Pointers to external systems | External resource locations |

**Explicit exclusions** (lines 183-195): code patterns, architecture, git history, debugging solutions, CLAUDE.md content, ephemeral task details.

### 2.4 Memory Retrieval: Three-Layer Architecture

Memory retrieval operates in three independent layers, from cheapest to most expensive:

**Layer 1: Static Injection (session start, zero extra API cost)**
- MEMORY.md index loaded via `claudemd.ts` as an "AutoMem" type MemoryFile
- Injected into user context alongside CLAUDE.md and .claude/rules/*.md
- Cached by `systemPromptSection()` — read once per session, not refreshed mid-conversation
- Even if user updates MEMORY.md during conversation, current session sees old version

**Layer 2: Side Query Prefetch (per-turn, 1 Sonnet call)**

`findRelevantMemories.ts` — NOT an agent, just a single API call:
1. `scanMemoryFiles()` reads frontmatter (first 30 lines) from all memory files (up to 200)
2. `formatMemoryManifest()` formats one line per file: `- [type] filename (timestamp): description`
3. Sends full manifest (~few thousand tokens) + user query to Sonnet via `sideQuery()`
4. Sonnet returns JSON: `{ selected_memories: ["file1.md", "file2.md"] }` (max 5, max_tokens=256)
5. Selected files' full content read via `readMemoriesForSurfacing()` (with line/byte truncation)
6. Injected as `<system-reminder>` attachment in user message content (not system prompt — preserves cache)

Key details:
- **Not keyword search** — Sonnet does semantic matching on frontmatter descriptions, no keyword extraction step
- **Prefetch pattern** — launched at start of user turn, runs in parallel with tool execution, consumed only if settled (never blocks)
- **Dedup** — `alreadySurfaced` set filters files shown in prior turns; `readFileState` filters files model already Read/Wrote/Edited
- **Disposable** — bound with `using` in query.ts, auto-aborted on user Escape

**Layer 3: Autonomous Search (on-demand, model decides)**

The system prompt (`buildSearchingPastContextSection()`) teaches the model two grep-based search methods:
1. Search memory directory: `Grep pattern="<term>" path="~/.claude/.../memory/" glob="*.md"`
2. Search session logs (last resort — large files, slow): `Grep pattern="<term>" path="~/.claude/.../" glob="*.jsonl"`

The synonyms and creative search terms users observe come from the **main agent (Opus) generating Grep tool calls**, not from the side query.

**Layer relationships:**
- Layer 1 ensures MEMORY.md index is always visible (zero latency)
- Layer 2 supplements with the most relevant specific files (async, non-blocking)
- Layer 3 is fallback for anything not covered by Layers 1-2 (expensive but flexible)
- If information is important enough, the background extraction agent will have saved it to a memory file, making Layers 1-2 sufficient for most cases

**B. Background Extraction** (`services/extractMemories/extractMemories.ts`):
- Runs post-turn when the main agent produces a final response with no tool calls
- Uses **forked-agent pattern** sharing the parent's prompt cache
- **Mutual exclusion**: When the main agent writes memories, the extractor skips that turn (`hasMemoryWritesSince`)

### 2.5 Extraction Agent Permissions

The background extraction agent has **surgically limited tool access** (`createAutoMemCanUseTool`):

| Permission | Tools |
|------------|-------|
| Read (unrestricted) | FILE_READ, GREP, GLOB |
| Read-only Bash | ls, find, grep, cat, stat, wc, head, tail |
| Write (memory dir only) | FILE_EDIT, FILE_WRITE — restricted to auto-memory paths |
| **Denied** | MCP, Agent, write-capable Bash, networking |

**Extraction prompt strategy** (2-turn budget):
- Turn 1: All parallel FILE_READ calls
- Turn 2: All parallel FILE_WRITE/EDIT calls
- No interleaving; no source verification

### 2.6 Memory Staleness

Staleness is tracked via `memdir/memoryAge.ts`:
- `memoryAgeDays()`: Floor-rounded age
- `memoryFreshnessNote()`: Wrapped in `<system-reminder>` tags for >1 day old memories
- The model is told: "this was written N days ago — verify before acting on it"

### 2.7 CLAUDE.md Discovery

CLAUDE.md loading (`utils/claudemd.ts`) follows a strict priority order:

1. **Managed** (system-level): `/etc/claude-code/CLAUDE.md`
2. **User global**: `~/.claude/CLAUDE.md`
3. **Project**: `CLAUDE.md`, `.claude/CLAUDE.md` (traversed from cwd upward to git root)
4. **Local**: `CLAUDE.local.md` (private, not committed)
5. **Conditional rules**: `.claude/rules/*.md` with frontmatter glob patterns

**@include directive**: Transitive inclusion with circular-reference prevention. Supported formats: `@path`, `@./relative`, `@~/home`, `@/absolute`. Binary files silently rejected.

### 2.8 Memory Persistence Model

Memory is **independent of context window** — compaction does not affect memories:

| Store | Lifecycle | Affected by compaction? |
|-------|-----------|------------------------|
| Context window messages | Volatile — truncated by micro/full/snip compaction | Yes |
| `memory/*.md` files | Persistent on disk — only deleted by explicit model/user action | No |
| `MEMORY.md` index | Persistent on disk — monotonically growing | No |
| Session JSONL logs | Persistent, append-only | No |

Even after heavy compaction reduces a session to a single summary paragraph, all memory files remain on disk and are accessible via Layer 2 (side query) and Layer 3 (Grep). This is the key architectural separation: **context is working memory (volatile), memory files are long-term memory (persistent), session logs are episodic memory (persistent)**.

### 2.9 Design Philosophy: Simplicity over Scalability

Claude Code's memory system is deliberately simple because of an implicit constraint: **single project, single user, bounded scale**.

Hard limits in source code:
- `MAX_MEMORY_FILES = 200` — scan cap
- `FRONTMATTER_MAX_LINES = 30` — per-file frontmatter read
- `MAX_ENTRYPOINT_LINES = 200` / `MAX_ENTRYPOINT_BYTES = 25KB` — MEMORY.md cap

200 files × ~150 chars description ≈ 30KB manifest ≈ few thousand tokens. Sonnet can process this in a single call with no difficulty.

This means Claude Code **does not need** the complex retrieval infrastructure other systems require:
- No vector database (vs OpenClaw's Qdrant/Chroma)
- No embedding model (vs Cursor's custom-trained embeddings)
- No temporal decay (vs OpenClaw's time-weighted scoring)
- No hybrid search (vs OpenClaw's vector + BM25 + MMR)
- No memory hierarchy/tiering (vs Letta's Core/Recall/Archival)

The trade-off: **not scalable** — if memory files grew to thousands, the manifest wouldn't fit in a single Sonnet call. But for a project-scoped coding assistant, this won't happen.

### 2.10 AutoDream: Offline Memory Consolidation

`services/autoDream/` implements an automatic **memory garbage collection** agent — the only system we've studied that does this.

**Trigger conditions** (three gates, cheapest first):
1. **Time gate**: ≥ 24 hours since last consolidation (`minHours: 24`)
2. **Session gate**: ≥ 5 new sessions since last consolidation (`minSessions: 5`)
3. **Lock**: No other process is currently consolidating

**Execution** — a forked agent runs the "Dream" prompt with 4 phases:
1. **Orient**: `ls` memory directory, read MEMORY.md, skim existing topic files
2. **Gather**: Find new information from daily logs, stale memories, or targeted transcript grep
3. **Consolidate**: Merge new signal into existing files, convert relative dates to absolute, delete contradicted facts
4. **Prune**: Clean MEMORY.md index — remove stale pointers, shorten verbose entries, add new pointers

**Why this matters**: Every other memory system we've studied (Mem0, Letta, OpenClaw, ChatGPT) only writes and retrieves memories. None automatically consolidates, deduplicates, or prunes. Claude Code treats memory as something that **degrades over time** and needs periodic maintenance — like a database that needs vacuuming.

The prompt explicitly says: "You are performing a dream — a reflective pass over your memory files." The metaphor is intentional — like biological memory consolidation during sleep.

**KAIROS mode variant**: In assistant mode (long-lived sessions), memories are written as append-only daily logs (`logs/YYYY/MM/YYYY-MM-DD.md`). A separate `/dream` skill consolidates these logs into topic files + MEMORY.md. This is a two-stage write pipeline: fast append → periodic consolidation.

### 2.11 Agent Memory: Per-Agent Isolated Memory

`tools/AgentTool/agentMemory.ts` implements **independent memory per custom agent type**, with three scopes:

| Scope | Path | Shared across projects? | Git-tracked? |
|-------|------|------------------------|-------------|
| `user` | `~/.claude/agent-memory/{agentType}/` | Yes — intentionally cross-project | No |
| `project` | `.claude/agent-memory/{agentType}/` | No | Yes (committable) |
| `local` | `.claude/agent-memory-local/{agentType}/` | No | No |

**How it's activated**: Custom agents (defined as `.md` files by plugins or users) declare memory scope in frontmatter:

```yaml
---
name: code-reviewer
memory: user
---
```

**Who uses it**: Only user/plugin-defined persistent agents. Built-in sub-agents (Explore, Plan, etc.) are stateless — they have no memory. This feature targets a future ecosystem of **persistent, specialized agents** that accumulate domain knowledge over time.

The `user` scope is cross-project by design. The prompt tells the agent: "keep learnings general since they apply across all projects." A code-review agent's learned preferences should be portable. The `project` scope is for project-specific agent knowledge that should be shared via git.

**Current status**: Not widely used — most users haven't created custom persistent agents yet. The `~/.claude/agent-memory/` directory doesn't exist on typical installations.

### 2.12 Team Memory Sync (Not Yet Launched)

`services/teamMemorySync/` implements a **client-server memory synchronization system** — currently behind double feature gates (`feature('TEAMMEM')` + GrowthBook `tengu_herring_clock`, default false).

**Architecture**:
- Server API: `GET/PUT /api/claude_code/team_memory?repo={owner/repo}` (Anthropic hosted)
- Per-repo scope identified by git remote hash
- Shared across all authenticated organization members
- **Server-wins** pull semantics (server overwrites local)
- Delta upload (only changed content hashes)
- File deletions do NOT propagate (delete local → next pull restores it)
- Built-in secret scanner (`secretScanner.ts`) prevents accidental sensitive data upload

**Storage path**: `{autoMemPath}/team/` — a subdirectory within the existing auto-memory directory.

**Significance**: This is the first evidence of any coding agent building a **shared team memory layer**. All other systems we've studied treat memory as single-user. Claude Code is preparing infrastructure for team-level knowledge sharing — project conventions, architectural decisions, common pitfalls — synced automatically across team members.

**Current status**: Code complete but not publicly launched. Likely targeting Teams/Enterprise product line (requires OAuth + organization permissions).

### 2.13 Unified Markdown Frontmatter Pattern

The memory system's frontmatter-based retrieval is not unique — it's a **codebase-wide pattern** used for all extensible content:

| Content type | Frontmatter fields | How frontmatter is used |
|---|---|---|
| Memory files | name, description, type | Sonnet selects relevant files by description |
| Skills | name, description, allowedTools, model, whenToUse | Model decides whether to invoke a skill |
| Agents | name, description, tools, model | Model decides whether to spawn an agent |
| Commands | name, description, model, allowedTools | Slash command registration |
| Rules | globs | Conditional injection based on file path matching |

All use the same format: **YAML frontmatter for structured metadata (retrieval/filtering), Markdown body for unstructured content (injection/reading)**. This means the entire extension system — memories, skills, agents, commands — uses the same "search by metadata, load by content" pattern.

---

## 3. `<system-reminder>`: In-Band Signaling Channel

### 3.1 Implementation

Trivially simple — just an XML tag wrapper:

```typescript
export function wrapInSystemReminder(content: string): string {
  return `<system-reminder>\n${content}\n</system-reminder>`
}
```

No special API semantics, no special tokens. Pure text injected into `user` message content blocks.

### 3.2 What Gets Wrapped

All dynamic context that needs mid-conversation injection:

| Content | Source |
|---------|--------|
| Memory file content + staleness warning | `findRelevantMemories` → attachment |
| Token budget (`Token usage: 35000/1000000`) | budget attachment |
| USD budget (`$0.5/$10`) | cost attachment |
| Output token stats | output token attachment |
| Hook blocking errors | hook system |
| Task completion/stop notifications | background agents |
| Deferred tools availability | tool search |
| MCP server instructions | MCP system |
| File read warnings (empty, large) | FileReadTool |
| Companion intro (buddy feature) | `companion_intro` attachment — injected once per session, tells main model to defer to companion bubble. See [claude-code-buddy.research.md](./claude-code-buddy.research.md) §4 |

### 3.3 Why This Design

Three reasons to use tagged wrappers in message content instead of direct system prompt injection or plain text concatenation:

**1. Prompt cache preservation**: System prompt is cached prefix. Injecting dynamic content there would invalidate cache every turn. Placing it in message content preserves the prefix.

**2. Role semantics**: The `user` role is the only freely writable channel (system is cached, assistant is model output). But `user` messages aren't all user-generated. The `<system-reminder>` tag creates a **sub-channel** within user messages. The system prompt tells the model: "Tags contain information from the system. They bear no direct relation to the specific tool results or user messages in which they appear." This gives the model appropriate weight — treat as reference context, not user instruction.

**3. Programmatic handling**: Code uses `startsWith('<system-reminder>')` to identify system-injected content for merging (`smooshSystemReminderSiblings`), filtering, and cleanup. Without tags, code cannot distinguish system context from user input.

### 3.4 Practical Takeaway for Agent Developers

For simple single-turn or short-conversation agents, inline template rendering (Jinja, f-strings) is sufficient. The `<system-reminder>` pattern becomes valuable when:
- Multi-turn conversations need prompt cache efficiency
- Dynamic context has a shorter lifecycle than the conversation
- Code needs to programmatically identify and manage injected context
- Multiple sources inject context into the same message stream

The tag format doesn't matter (XML, Markdown callouts, custom delimiters). What matters is: (1) tell the model what the tag means in system prompt, (2) use the tag as an anchor in code for filtering/merging, (3) keep dynamic content out of the cached system prompt prefix.

---

## 4. Tool System & Agent Loop

### 4.1 Tool Abstraction

`Tool.ts` (793 lines) defines the complete tool interface:

- `call()`: Execute with parsed input
- `inputSchema`: Zod-based validation
- `checkPermissions()`: Tool-specific permission logic
- `isConcurrencySafe()`: Whether parallel execution is safe (default: false — fail-closed)
- `isReadOnly()`: Whether it modifies state (default: false — assume writes)

### 4.2 Tool Execution Pipeline

`services/tools/toolOrchestration.ts` implements batch execution:

1. **Partition** tool calls into batches via `partitionToolCalls()`
2. **Concurrent batches**: Multiple read-only tools (`isConcurrencySafe=true`) run in parallel
3. **Serial batches**: Write tools run one-at-a-time
4. **Concurrency cap**: `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` (default 10)

### 4.3 The Agent Loop

`query.ts` (the `queryLoop` function, lines 241-1400+) is the core agent loop:

```
State = {
  messages, toolUseContext, turnCount,
  autoCompactTracking, maxOutputTokensRecoveryCount,
  hasAttemptedReactiveCompact, stopHookActive, transition
}

Each iteration:
  1. Context Preparation → query chain tracking, message boundaries
  2. Content Processing → tool result budgets, snip/micro compaction
  3. API Request → build system + user context, stream Claude API
  4. Streaming Response → accumulate chunks, detect stop_reason
  5. Tool Execution → runTools() from orchestration, stream results
  6. Continue/Terminal → check token budget, max turns, stop hooks
  7. If continue: loop; if terminal: return with usage info
```

**Loop termination**: `maxTurns` parameter + `maxBudgetUsd` for cost control.

### 4.4 Multi-Agent: AgentTool

`tools/AgentTool/AgentTool.tsx` enables recursive subagent spawning:

**Input schema** (lines 82-125):
- `prompt`: Task description
- `subagent_type`: Specialized agent type (Explore, Plan, etc.)
- `model`: Override (sonnet/opus/haiku)
- `run_in_background`: Async execution
- `isolation`: 'worktree' for git-isolated copy

**Execution flow** (`tools/AgentTool/runAgent.ts`):
1. Initialize agent-specific MCP servers from frontmatter
2. Resolve tool pool: filter parent tools based on agent permissions
3. Create isolated subagent context (cloned parent, shared file cache)
4. Run `query()` with agent-specific system prompt
5. Save transcript to sidechain (separate file per agent)
6. Return result to parent

### 4.5 Coordinator Mode

`coordinator/coordinatorMode.ts` — Feature-gated (`COORDINATOR_MODE`):
- Transforms agent into orchestrator role
- Workers spawned via AgentTool with restricted tool lists
- Workers notified via `<task-notification>` XML blocks
- Coordinator continues workers via `SendMessageTool`

### 4.6 Permission System

Multi-level permission gates (`utils/permissions/permissions.ts`):

1. **Rule sources**: localSettings, userSettings, projectSettings, cliArg, command, session
2. **Modes**: 'default' (ask), 'auto' (classifier), 'plan' (explicit approval), 'ask' (always ask)
3. **Classifier** (feature: `TRANSCRIPT_CLASSIFIER`): ML-based safe/unsafe classification
4. **Denial tracking**: Auto-deny after 3 consecutive denials; fallback to prompting after threshold

---

## 5. Plugin & Skills System

### 5.1 Plugin Types

Three categories:
- **Bundled**: Ship with CLI, toggleable via `/plugin` UI. Registered via `registerBuiltinPlugin()`
- **Marketplace**: External, installed from registries. Cached at `~/.claude/plugins/cache/`
- **Session-only**: Via `--plugin-dir` CLI flag

### 5.2 Plugin Manifest (`plugin.json`)

Validated by `utils/plugins/schemas.ts` (58KB):

```
name, version, description
commands: slash commands (markdown files)
agents: custom AI agents (markdown)
skills: skill directories
hooks: lifecycle event handlers (22 event types)
mcpServers: MCP server configs
lspServers: LSP server configs
userConfig: user-configurable options (prompted at enable time)
channels: message-injecting MCP servers
dependencies: required plugins (resolved per-marketplace)
```

**Security validation**:
- Reserved marketplace name protection (blocks `official-claudia` impersonation)
- Non-ASCII character blocking (homograph attack prevention)
- Source verification for official names (must come from `github.com/anthropics/`)

### 5.3 Marketplace Architecture

`utils/plugins/marketplaceManager.ts` (93KB):

**Sources**:
- `github:owner/repo` — GitHub repository
- `git:https://...` — Git URL
- `npm:package-name` — NPM package
- `url:https://...` — Remote JSON manifest
- `local:/path/to/dir` — Local directory

Enterprise features: strict allow-lists (`strictKnownMarketplaces`), blocked lists (`blockedMarketplaces`), managed settings policy enforcement.

### 5.4 Skills Execution

Skills invoked via the `SkillTool` (`tools/SkillTool/SkillTool.ts`):
- Lists available skills (bundled + plugin-provided)
- Executes in **forked sub-agent contexts** with isolated token budgets
- Supports inline (same context) and fork (isolated) execution modes
- Model override and tool permission validation

### 5.5 Hook System

22 event types including: PreToolUse, PostToolUse, PostToolUseFailure, PermissionDenied, UserPromptSubmit, SessionStart, SessionEnd, Stop, Setup, FileChanged, CwdChanged.

- Plugins register hooks via manifest or `hooks.json`
- Function hooks execute TypeScript callbacks in-memory
- **Hot reload** supported when remote settings change
- Atomic clear-then-register prevents race conditions

---

## 6. Key Findings & Comparisons

### 6.1 Confirms & Extends Prior Research

| Topic | Prior Understanding (reverse-engineering) | Source Code Reality |
|-------|------------------------------------------|---------------------|
| Compaction | Server-side API + client prompts | **Four-tier system**: micro, cached-micro, full, snip. Client-side micro layers invisible from prompts. Comparable to Codex's per-item truncation but with additional cache-aware and time-based tiers |
| Memory | File-based, MEMORY.md index | Confirmed. Plus: **Sonnet-as-selector** for retrieval, mutual-exclusion extraction agent |
| System prompt | 65+ modular files | **Sectioned + dual-tier cached**. Volatile sections explicitly separated |
| Sub-agents | Worker fork inherits parent context | Confirmed. Plus: **isolated MCP servers per agent**, shared file cache (LRU) |
| Context awareness | `<budget:token_budget>` tags | Plus: **beta header latches** for cache stability, pending state management |

### 6.2 Novel Findings Not Visible from Prompts

1. **Prompt cache as first-class concern**: The entire architecture is designed around maximizing prompt cache hit rates. Beta header latches, system-reminder-in-content (not system), memoized context — all serve this goal.

2. **Microcompaction is the workhorse**: Full compaction (the flashy 9-section summary) is the fallback. Most context management happens at the microcompaction layer — silent, per-turn truncation of old tool results.

3. **Memory extraction is a forked agent**: The auto-memory system spawns a separate agent process that shares the parent's prompt cache. It has a strict 2-turn budget (read, then write). This explains why memory extraction doesn't interrupt the main conversation.

4. **Tool concurrency model**: Tools declare `isConcurrencySafe()` (default false). The orchestrator partitions tool calls into concurrent vs serial batches. This is why multiple file reads happen in parallel but edits are sequential.

5. **Async generators everywhere**: The entire tool execution → agent loop → UI rendering pipeline uses async generators (`yield*`). This enables streaming progress updates, tool results, and UI rendering without blocking.

6. **Plugin security is enterprise-grade**: Homograph attack prevention, reserved name protection, source verification for official plugins, strict marketplace allow-lists. This goes far beyond typical open-source plugin systems.

7. **Memory retrieval uses a side LLM call**: Finding relevant memories isn't keyword matching or embedding search — it's a separate Sonnet API call that picks up to 5 relevant files from frontmatter descriptions. This is expensive but high-quality.

8. **AutoDream: offline memory consolidation**: A background agent periodically (every 24h + 5 sessions) runs a "dream" pass — merging, deduplicating, pruning, and re-indexing memory files. No other agent system we've studied does automatic memory maintenance.

9. **Agent Memory with three scopes**: Custom agents can have their own isolated persistent memory (user/project/local scope), independent of the main auto-memory. Infrastructure for a future persistent agent ecosystem.

10. **Team Memory Sync (unreleased)**: Full client-server sync for team-shared memory, with delta upload, secret scanning, and server-wins semantics. First evidence of any coding agent building shared team memory.

11. **sideQuery as a general-purpose side channel**: The memory retrieval sideQuery (§2.4 Layer 2) is not a one-off — the `/buddy` companion observer reuses the same pattern for a completely different purpose (generating reactive commentary). This establishes sideQuery as a reusable primitive: cheap async inference that runs parallel to or after the main agent loop, with no tool access and fire-and-forget semantics. See [claude-code-buddy.research.md](./claude-code-buddy.research.md) §2.

12. **Compile-time feature gates and dead-code elimination**: `feature()` from `bun:bundle` is a compile-time macro. Features like BUDDY, COORDINATOR_MODE, VOICE_MODE, and KAIROS are evaluated at build time; false branches are eliminated by the bundler along with their imports. This means source maps (generated pre-DCE) contain unreleased feature code that is absent from production bundles — **presence in source map ≠ presence in production**. This also explains the internal (`'ant'`) vs external (`'external'`) build distinction used for staged rollouts. See [claude-code-buddy.research.md](./claude-code-buddy.research.md) §5.

### 6.3 Comparison with Other Agents

| Feature | Claude Code | OpenClaw | Gemini CLI | Codex |
|---------|------------|----------|------------|-------|
| Compaction | 4-tier (micro→cached→full→snip) | Delegates to Pi | Two-pass verified | Dual (server+client) |
| Memory storage | Plain files + MEMORY.md index | Vector DB (Qdrant/Chroma) | None | None |
| Memory retrieval | LLM-as-selector (Sonnet) | Hybrid search (vector+BM25) | N/A | N/A |
| Sub-agents | Recursive AgentTool + Coordinator | Gateway RPC bidirectional | Fresh chat instance | None (flat loop) |
| Plugin system | Full marketplace + hooks + MCP + LSP | None | Extensions | None |
| Prompt cache | First-class (latches, sections, in-content reminders) | N/A | N/A | N/A |
| Permission model | ML classifier + rules + denial tracking | None (trust user) | Basic allowlist | Sandbox |

### 6.4 Architecture Patterns Worth Noting

1. **Forked agent with shared cache**: Both memory extraction and full compaction use forked agents that share the parent's prompt cache. This avoids redundant API costs for system prompt processing.

2. **Dual truncation strategy**: MEMORY.md uses both line and byte caps because long-line indexes can slip past line limits. The system detects which cap fired and provides targeted guidance.

3. **Tool result budget pattern**: Large tool results (>maxResultSizeChars) are persisted to disk; only a preview goes to the API. This prevents token explosion from huge outputs.

4. **Pending state for undo**: History entries kept in-memory pending array before disk flush, enabling undo via `removeLastFromHistory()` when user presses Escape during submission.

5. **Deterministic-from-hash + model-generated split**: The buddy companion separates its data into deterministic "bones" (species, rarity, stats — derived from `hash(userId)` via Mulberry32 PRNG, never persisted) and model-generated "soul" (name, personality — created once, stored in config). This prevents users from editing config to change rarity while allowing Anthropic to rename species without breaking companions. A useful pattern for any personalization feature. See [claude-code-buddy.research.md](./claude-code-buddy.research.md) §1.

### 6.5 Forked/Side Inference Taxonomy

The codebase uses several patterns for running inference outside the main agent loop. Cataloguing them reveals a spectrum from heavy (full agent fork) to light (single API call):

| Pattern | Mechanism | Blocks main? | Shares prompt cache? | Tool access? | Trigger |
|---------|-----------|-------------|---------------------|-------------|---------|
| Full compaction | Forked agent | Yes (at context limit) | Yes | None | Context overflow |
| Memory extraction | Forked agent, 2-turn budget | No (post-turn) | Yes | Read + write (memory dir) | Main agent's final response |
| AutoDream | Forked agent, 4-phase | No (background, 15s cap) | Yes | Read + write (memory dir) | 24h + 5 sessions gate |
| Memory retrieval | sideQuery, 1 Sonnet call | No (prefetch) | No | None | Turn start |
| Companion observer | sideQuery (inferred), 1 call | No (fire-and-forget) | No | None | Turn end |

The common theme: **all side inference is non-blocking relative to the main conversation loop**. The only blocking case (full compaction) is triggered by necessity (context overflow), not by choice. See [claude-code-buddy.research.md](./claude-code-buddy.research.md) §6.2 for detailed comparison.

---

## 7. Implications for Agent Research

### For Memory Research
- Claude Code validates the **file-based memory** approach at production scale — no vector DB needed for coding agent memory
- The **LLM-as-selector** pattern for memory retrieval is a notable alternative to embedding-based search
- The **mutual exclusion** between main agent and extraction agent prevents memory conflicts
- Memory type taxonomy (user/feedback/project/reference) with explicit exclusions is a well-designed ontology
- **AutoDream** introduces a new concept: **memory maintenance as a first-class operation**. Memory is not write-once — it degrades and needs periodic consolidation, like biological memory during sleep
- **Team Memory Sync** signals the industry direction: from single-user memory to **shared organizational memory**. This could change how teams encode and transmit project knowledge
- **Agent Memory scopes** suggest a future where specialized agents accumulate their own domain expertise independently — moving toward a **multi-agent knowledge ecosystem**

### For Context Research
- **Prompt cache optimization** is a critical but under-discussed aspect of agent context management
- **Microcompaction** (silent per-turn tool result truncation) handles most context pressure — full compaction is rare
- The **system-reminder-in-content** pattern shows that mid-conversation context injection doesn't need to break prompt caches — and the buddy companion intro confirms this discipline extends to every feature, not just core ones
- **Four-tier compaction** shows that production agents need multiple granularity levels, not just one compaction strategy

### For Agent Architecture Research
- The **async generator pipeline** pattern (tool execution → agent loop → UI) enables streaming without blocking
- **Tool concurrency classification** (read-safe vs write-unsafe) is essential for parallel tool execution
- **Recursive subagents with isolated MCP** enables composable agent architectures
- The **coordinator mode** pattern (orchestrator + workers + task notifications) is a production-ready multi-agent design
- **sideQuery is a reusable primitive**, not a memory-specific utility. It serves memory retrieval and companion reactions equally — any cheap, async, non-blocking supplementary inference fits this pattern
- **Compile-time feature gates** (`feature()` + Bun DCE) provide a clean staging mechanism: code can live in trunk long before it ships, with zero runtime cost when disabled. Source maps leak unreleased code because they are generated pre-DCE

### Deep Dive: Buddy/Companion Feature

For a detailed analysis of the `/buddy` companion system — its data model, observer mechanism, rendering, billing separation, and feature staging infrastructure — see [claude-code-buddy.research.md](./claude-code-buddy.research.md).
