# DeerFlow v2.0 Memory & Context Research

Last Updated: 2026-04-22

Source: [bytedance/deer-flow](https://github.com/bytedance/deer-flow) — submodule at `deer-flow/` (pinned to `5ba1dacf`, v2.0-m1-50).

Research focus: how DeerFlow v2.0 builds per-turn context, stores and updates long-term memory, and what its "super agent harness" adds on top of LangGraph. Comparative framing against Letta, mem0, OpenClaw.

---

## TL;DR

- DeerFlow 2.0 is a ByteDance-maintained "super agent harness" built on **LangGraph 1.0 + LangChain 1.2** (`backend/packages/harness/pyproject.toml:13-22`). It is not a new agent loop — it is an orchestration + memory + sandbox + skills layer on top of `create_agent()`.
- Memory is a **flat JSON file** (`backend/.deer-flow/memory.json`), not a vector store, not a graph. Facts + 6 structured summary slots (work/personal/top-of-mind × recent/earlier/long-term). No embeddings anywhere in the memory path.
- Memory updates are **LLM-driven, debounced, and async** — queued after each turn, processed 30 s later by a background thread that calls an LLM to extract facts + refresh context summaries. Current-turn memory is never the current turn's memory.
- Context assembly is **not pluggable**. There is no engine interface like OpenClaw's `ContextEngine`. Instead, ~20 LangChain `AgentMiddleware` components compose around `create_agent()` and a single `apply_prompt_template()` builds the system prompt.
- Memory-for-injection uses **confidence ranking + a `tiktoken`-measured budget** (default 2000 tokens) — no retrieval, no relevance scoring against the current query.
- The design consciously trades **recall sophistication for debuggability**: explicit categories, explicit confidence, hand-editable JSON, user-facing memory UI (`frontend/src/core/memory/`), import/export endpoints.

---

## 1. Repository Map

All paths are relative to `deer-flow/`.

| Layer | Path | Role |
|-------|------|------|
| Harness package (PyPI publishable) | `backend/packages/harness/deerflow/` | Framework code — hard boundary enforced by CI (`tests/test_harness_boundary.py`) |
| Lead agent factory | `backend/packages/harness/deerflow/agents/lead_agent/agent.py` | `make_lead_agent()` — builds LangGraph agent with middlewares |
| Prompt assembly | `backend/packages/harness/deerflow/agents/lead_agent/prompt.py` | `apply_prompt_template()` — single-entry prompt builder |
| Middleware chain | `backend/packages/harness/deerflow/agents/middlewares/` | ~20 `AgentMiddleware` subclasses composed via `build_lead_runtime_middlewares()` in `tool_error_handling_middleware.py:128` |
| Memory subsystem | `backend/packages/harness/deerflow/agents/memory/` | Storage, queue, updater, injection, correction detection |
| Sub-agents | `backend/packages/harness/deerflow/subagents/` | `executor.py` (thread-pool background runner), builtins (`general_purpose`, `bash`) |
| Sandbox | `backend/packages/harness/deerflow/sandbox/` | Virtual-path file system; `LocalSandboxProvider` default, Docker via `community/aio_sandbox/` |
| Skills | `backend/packages/harness/deerflow/skills/` | `SKILL.md` loader/parser/installer/validator/security scanner |
| Tools | `backend/packages/harness/deerflow/tools/builtins/` | `tool_search` (deferred discovery), `ask_clarification`, `present_files`, `view_image` |
| MCP | `backend/packages/harness/deerflow/mcp/` | `MultiServerMCPClient` (lazy init) |
| Gateway app | `backend/app/gateway/` | FastAPI layer — routes for memory, skills, uploads, threads, artifacts. **Not** importable from harness |
| IM channels | `backend/app/channels/` | Feishu / Slack / Telegram adapters |
| Frontend memory UI | `frontend/src/core/memory/`, `frontend/src/app/api/memory/` | Next.js client + API routes for user-visible memory CRUD |

A non-obvious point: `deerflow-harness` is intended to be installable standalone. `test_harness_boundary.py` fails CI if any harness module imports `app.*`. That explains the duplicated config/HTTP surface in the harness.

---

## 2. Per-Turn Flow

```
User message
    │
    ▼  [~20 AgentMiddleware wrapped around LangGraph create_agent()]
    │      ThreadDataMiddleware          ← per-thread .deer-flow/threads/{id}/
    │      UploadsMiddleware             ← inject uploaded files into message
    │      SandboxMiddleware             ← acquire sandbox_id
    │      DanglingToolCallMiddleware    ← patch orphaned tool_use blocks
    │      LLMErrorHandlingMiddleware    ← provider error normalization
    │      GuardrailMiddleware           ← optional auth checks
    │      SandboxAuditMiddleware        ← security logging
    │      ToolErrorHandlingMiddleware   ← tool exception → ToolMessage
    │      SummarizationMiddleware       ← optional context reduction
    │      TodoListMiddleware            ← optional plan tracking
    │      TokenUsageMiddleware          ← optional metrics
    │      TitleMiddleware               ← auto-name thread
    │      MemoryMiddleware              ← enqueue turn for async memory update (after_agent)
    │      ViewImageMiddleware           ← base64 image injection
    │      DeferredToolFilterMiddleware  ← hide not-yet-fetched tool schemas
    │      SubagentLimitMiddleware       ← clamp task() calls to MAX_CONCURRENT_SUBAGENTS=3
    │      LoopDetectionMiddleware       ← detect tool-call loops
    │      ClarificationMiddleware       ← must be last; can interrupt turn
    │
    ▼  apply_prompt_template(subagent_enabled, max_concurrent, agent_name, available_skills)
    │      base system instruction
    │      + agent soul (optional SOUL.md)
    │      + <memory> block         ← format_memory_for_injection(), 2000-token budget
    │      + <skill_system>         ← list of SKILL.md, progressive loading
    │      + <subagent_system>     ← DECOMPOSE/DELEGATE/SYNTHESIZE + concurrency clamp
    │      + sandbox tool docs
    │      + ACP workspace docs (optional)
    │      + MCP + community + builtin tool descriptions
    │
    ▼  LangGraph create_agent() → LLM call, tool execution loop, message accumulation
    │
    ▼  Response materialized; artifacts + uploads surfaced via present_files
    │
    ▼  MemoryMiddleware.after_agent() → MemoryUpdateQueue.add(thread_id, filtered_messages)
           │
           ▼  30 s debounce (config.memory.debounce_seconds)
           │
           ▼  background thread → MemoryUpdater.update_memory() → LLM fact extraction
           │
           ▼  FileMemoryStorage.save() atomic rename → memory.json
```

The two load-bearing entry points are:
- `make_lead_agent()` at `backend/packages/harness/deerflow/agents/lead_agent/agent.py:226` — composes middlewares via `build_lead_runtime_middlewares(lazy_init=True)`.
- `apply_prompt_template()` at `backend/packages/harness/deerflow/agents/lead_agent/prompt.py:677+` — single function responsible for the full system prompt.

There is **no per-turn truncation, no per-turn retrieval, no context engine**. LangGraph handles message history as-is. `SummarizationMiddleware` is the only pre-LLM compression hook and only fires on token-limit approach.

---

## 3. Memory Subsystem

### 3.1 On-Disk Shape

```jsonc
{
  "version": "1.0",
  "lastUpdated": "2026-04-22T15:30:45Z",
  "user": {
    "workContext":     { "summary": "...", "updatedAt": "..." },
    "personalContext": { "summary": "...", "updatedAt": "..." },
    "topOfMind":       { "summary": "...", "updatedAt": "..." }
  },
  "history": {
    "recentMonths":       { "summary": "...", "updatedAt": "..." },
    "earlierContext":     { "summary": "...", "updatedAt": "..." },
    "longTermBackground": { "summary": "...", "updatedAt": "..." }
  },
  "facts": [
    { "id": "fact_abc123de",
      "content": "User works on LLM research with focus on memory systems",
      "category": "context",    // preference | knowledge | context | behavior | goal | correction
      "confidence": 0.95,        // 0.9–1.0 explicit, 0.7–0.8 strong implication, 0.5–0.6 inferred
      "createdAt": "2026-04-22T15:30:45Z",
      "source": "auto" }
  ]
}
```

Two important properties:
- **Six fixed summary slots** for structural compression (3 user × 3 time-horizon). These are always injected.
- **Facts are a flat list**, not a graph. No edges, no namespaces beyond `agent_name`, no embeddings.

Storage path defaults to `backend/.deer-flow/memory.json`; per-agent memory at `backend/.deer-flow/agents/{agent_name}/memory.json`.

### 3.2 Storage Layer

`backend/packages/harness/deerflow/agents/memory/storage.py`

- Abstract `MemoryStorage` (line 43): `load()`, `reload()`, `save()`.
- `FileMemoryStorage` (line 62): default JSON-file implementation with:
  - **mtime-keyed cache** `_memory_cache: dict[agent_name, (data, mtime)]` (line 69) — reloads automatically if the file changed on disk.
  - **Lock-guarded reads/writes** (line 70).
  - **Atomic save** (line 146): write to `{path}.{uuid}.tmp`, then `os.rename()` — crash-safe. Cache is updated only after the rename succeeds, from a deep copy.
- Pluggable via `memory.storage_class` config (reflection-loaded).

### 3.3 Update Queue (Async, Debounced)

`backend/packages/harness/deerflow/agents/memory/queue.py`

- `MemoryUpdateQueue` (line 27): process-global singleton.
- Per-`thread_id` deduplication — if two updates arrive for the same thread inside the debounce window, the later one replaces the earlier (only the newest conversation state is processed).
- Default debounce: **30 s** (`config.memory.debounce_seconds`, line 129).
- `add()` schedules a timer; `add_nowait()` fires with 0-delay for forced flush.
- `_process_queue()` runs on a background thread, sleeps 0.5 s between threads to avoid LLM rate-limit.

The implication is load-bearing: **facts extracted from turn N are available no earlier than turn N+1, typically later**. This matches OpenClaw's "post-turn ingest" pattern and the opposite of Letta's in-context tool-driven memory.

### 3.4 Updater (LLM-Driven Extraction)

`backend/packages/harness/deerflow/agents/memory/updater.py`

Per queued turn:
1. Load current memory via storage.
2. Filter the messages via `filter_messages_for_memory()` → keep only user inputs + final AI responses (tool calls/results dropped; upload-only messages dropped entirely).
3. Render conversation for the prompt.
4. Call LLM (configurable, default = main model) with `MEMORY_UPDATE_PROMPT` — asks for JSON patches to facts + context summaries.
5. Parse JSON (handles fenced code blocks).
6. Merge with deep-copied memory to avoid mutating the cache.
7. `_strip_upload_mentions_from_memory()` (≈lines 267-287) removes any sentences that refer to ephemeral upload paths like `/mnt/user-data/uploads/...` — prevents phantom files in future sessions.
8. `FileMemoryStorage.save()`.

Sync-from-async bridge: `_run_async_update_sync()` detects if already inside a running event loop and submits to `_SYNC_MEMORY_UPDATER_EXECUTOR` (4-worker ThreadPoolExecutor) — otherwise `asyncio.run()`. Exists because Gateway mode and LangGraph server mode have different loop semantics.

### 3.5 Correction & Reinforcement Detection

`backend/packages/harness/deerflow/agents/memory/message_processing.py` lines 88–110.

- **Bilingual regex** (EN + ZH) hand-maintained in code, not config.
  - Correction: `"that's wrong"`, `"try again"`, `"redo"`, `"不对"`, `"你理解错了"`, `"改用"`, `"重新来"`, …
  - Reinforcement: `"perfect"`, `"exactly right"`, `"对，就是这样"`, `"完全正确"`, `"正是我想要的"`, …
- When detected, the `MEMORY_UPDATE_PROMPT` receives a hint instructing the LLM to emit facts with `category: "correction"` and `confidence >= 0.95`, optionally with `sourceError` field describing what the agent got wrong.
- Rationale: user feedback signal is strong + cheap to catch with regex; don't pay LLM latency/cost to classify it. This is the closest thing in the codebase to continual learning — the agent persists its own known-wrong behaviors.

### 3.6 Injection

`backend/packages/harness/deerflow/agents/memory/prompt.py:201` — `format_memory_for_injection(memory_data, max_tokens=2000)`:

- Render user-context + history summaries first.
- Sort facts by `confidence` desc.
- Token-counted greedy fit using `tiktoken` (char-based fallback).
- Truncate content when budget exceeded (line 310: 95 % of budget target for margin).
- Injected as a single `<memory>` block inside `apply_prompt_template()`.

No per-query relevance scoring. No vector search. No MMR. Confidence *is* the relevance signal.

### 3.7 Configuration

```yaml
memory:
  enabled: true
  injection_enabled: true
  storage_class: deerflow.agents.memory.storage:FileMemoryStorage
  storage_path: null                  # default ~/.deer-flow/memory.json
  debounce_seconds: 30
  model_name: null                    # null ⇒ main model
  max_facts: 100
  fact_confidence_threshold: 0.7
  max_injection_tokens: 2000
```

---

## 4. Context Engineering — What's There and What Isn't

Compared to OpenClaw's three-line-of-defense (turn truncation → pluggable context engine → LLM compaction), DeerFlow has:

| Defense | Mechanism | Notes |
|---------|-----------|-------|
| 1st | `SummarizationMiddleware` | Optional; fires near token limit |
| 2nd | Memory injection with budget | Structural compression via 6 summary slots + ranked facts |
| 3rd | None explicit | LangGraph passes messages through; no compaction hook beyond summarization middleware |

There is **no plug-in context-assembly interface**. You cannot swap "how context is selected per turn" without forking. What *is* pluggable:
- `memory.storage_class` — swap JSON for SQL/vector/anything
- `middlewares` list — add/remove composition elements
- `sandbox_provider` — swap Local for Docker (AIO)
- MCP servers — add external tool sources
- Skills — drop in `SKILL.md` directories

So: extensibility lives at the middleware + tool + skill level, not at the retrieval level.

---

## 5. Sub-Agents

`backend/packages/harness/deerflow/subagents/executor.py`, with `MAX_CONCURRENT_SUBAGENTS = 3` at line 532.

- Invoked via `task(prompt, subagent_type)` tool. `SubagentLimitMiddleware` truncates extra calls *before* sending to the LLM output stream — so users see the 3-limit enforced cleanly.
- Two thread pools: scheduler (3 workers) + execution (3 workers). 15-minute per-subagent timeout.
- Inheritance from parent:
  - **Sandbox and thread_data: shared** (same `sandbox_id`, same `/mnt/user-data/`)
  - **Memory: shared** (subagent can read/write the parent's `memory.json`)
  - **Conversation history: NOT shared** (new `ThreadState`, new messages)
  - **Model: inherited unless overridden**
- Result streamed back to parent via SSE events: `task_started`, `task_running`, `task_completed | task_failed | task_timed_out`.
- Builtins:
  - `general_purpose` — full tool surface minus `task` itself (no recursive delegation)
  - `bash` — bash + file ops only

The design is Claude-Code-style "agents as first-class tools", not Letta-style "agents as standalone processes".

---

## 6. Skills

`backend/packages/harness/deerflow/skills/` — directory structure mirrors Claude Code's skill format.

- `SKILL.md` = YAML frontmatter (`name`, `description`, `license`, `allowed-tools`, …) + markdown body.
- Directories scanned: `deer-flow/skills/public/` (bundled) + `deer-flow/skills/custom/` (user-installed).
- `loader.py` / `parser.py` / `validation.py` / `security_scanner.py` — note the last: skills are treated as partially-untrusted content, scanned before install.
- Install path: `POST /api/skills/install` accepts a `.skill` ZIP, extracts into `skills/custom/`, enables via `extensions_config.json`.
- Prompt injection is **name + description only**, not full body. Agent reads skill file on demand via `read_file()` — this is progressive disclosure, same pattern as Claude Code.
- LRU-cached section in `apply_prompt_template()` is invalidated when enabled-skills set changes.

---

## 7. Sandbox

`backend/packages/harness/deerflow/sandbox/`

- Virtual paths visible to agent: `/mnt/user-data/{workspace,uploads,outputs}/`, `/mnt/skills/`, `/mnt/acp-workspace/`.
- Physical paths: `backend/.deer-flow/threads/{thread_id}/user-data/...` etc.
- `replace_virtual_path()` translates; `../` traversal prevented in tool implementations.
- Providers:
  - `LocalSandboxProvider` (default, singleton, no isolation — host filesystem)
  - `AioSandboxProvider` (`community/aio_sandbox/`) — Docker-based
- Exposes `bash`, `read_file`, `write_file`, `str_replace`, `glob`, `grep`, `list_dir`.

Local mode is fine for research; production deployments would want AIO for isolation.

---

## 8. Claude Code Integration

Two surfaces worth naming:

### 8.1 OAuth credential handoff
`backend/packages/harness/deerflow/models/credential_loader.py`

Source priority: `CLAUDE_CODE_OAUTH_TOKEN` env → `CLAUDE_CODE_CREDENTIALS_PATH` → `ANTHROPIC_AUTH_TOKEN` → `~/.claude/.credentials.json`. Prefix `sk-claude-` = API key path; otherwise OAuth path with beta headers `oauth-2025-04-20,claude-code-20250219,interleaved-thinking-2025-05-14`. Expired-token detection just logs a warning and tells user to re-run `claude` CLI.

### 8.2 Deferred tool discovery
`backend/packages/harness/deerflow/tools/builtins/tool_search.py`

Mirrors Claude Code's own tool-search mechanism:
- Agent sees only tool *names* in `<available-deferred-tools>`.
- Agent calls `tool_search("select:X,Y")` or `"+keyword rest"` to pull schemas.
- `DeferredToolRegistry` stored in a `contextvars.ContextVar` (per-request isolation, safe for async concurrency).
- `DeferredToolFilterMiddleware` removes promoted tools from the deferred registry for subsequent turns.

This is ByteDance implementing Anthropic's token-bloat mitigation verbatim.

### 8.3 ACP (Agent Client Protocol)
`invoke_acp_agent` tool can call external ACP agents (e.g., Codex) as sub-processes. Workspace at `/mnt/acp-workspace/` is volume-mounted per-thread and read-only surfaced back to the lead agent.

---

## 9. Frontend Memory Surface

`frontend/src/core/memory/` (types.ts, api.ts, hooks.ts) + `frontend/src/app/api/memory/` (Next.js API routes).

Client-side CRUD endpoints:
- `GET /api/memory` → load full memory
- `DELETE /api/memory` → wipe
- `DELETE /api/memory/facts/{factId}` → delete single fact
- `POST /api/memory/facts` → create fact manually
- `PATCH /api/memory/facts/{factId}` → edit fact content/category/confidence
- `GET /api/memory/export` / `POST /api/memory/import` → portability

Users can **see, edit, and export** their memory. This is a sharp divergence from Letta (opaque vector DB) and mem0 (API-only) and aligns with the recent industry shift toward user-controllable memory (ChatGPT memory controls, Claude memory preview, Dayfold's LIKE-only model).

---

## 10. Comparative Framing

### vs. Letta (MemGPT)

| Aspect | Letta | DeerFlow |
|--------|-------|----------|
| Memory tiers | Core / Recall / Archival (vectors) | 6 summary slots + flat facts (no vectors) |
| Update trigger | LLM tool-call (`archival_memory_insert`) | Debounced post-turn LLM extraction |
| Retrieval | Vector search (RRF hybrid) | Confidence ranking, no query-dependent scoring |
| Agent model | Stateful agents, unbounded context via paging | Stateless turns + external memory injection |
| Source citing | Archival passages | Facts don't cite source turn |

### vs. mem0

| Aspect | mem0 | DeerFlow |
|--------|------|----------|
| Fact extraction | Explicit pipeline (extract → conflict-resolve → CRUD) | Single LLM call per debounce window returns JSON patch |
| Conflict resolution | LLM reasons over retrieved-neighbor vs new fact | Depends entirely on LLM prompt behavior inside update call |
| Scoping | `user_id` × `agent_id` × `run_id` | `agent_name` only |
| Graph memory | Neo4j option | None |
| Vector store | 24+ providers | None |

### vs. OpenClaw

| Aspect | OpenClaw | DeerFlow |
|--------|----------|----------|
| Context engine | 7-method pluggable interface | None; monolithic `apply_prompt_template()` |
| Turn truncation | Hard truncation + pluggable assemble + compaction | Optional summarization middleware only |
| Subagent lifecycle | Gateway RPC, cross-process | Thread pools, in-process |
| Skills | Not present | `SKILL.md` + progressive loading |
| Sandbox | Not present | Virtual FS + local/Docker providers |

### vs. LangGraph

DeerFlow *is* LangGraph 1.0 + LangChain 1.2 underneath (`backend/packages/harness/pyproject.toml:13-22`). What it adds:
- 20-component middleware chain composed for you
- Full memory subsystem (storage, queue, updater, injection, prompts)
- Sandbox with virtual paths
- Skills (SKILL.md)
- Subagents as in-process tools
- MCP client with lazy init
- Deferred tool discovery
- Claude Code OAuth + ACP
- Embedded Python client (`client.py`) that bypasses the HTTP gateway

---

## 11. Design Choices Worth Flagging

1. **Regex for user-feedback detection, bilingual, hand-maintained.** Cheap, fast, and it's the only place "continual learning" leaks in. Any correction raises a high-confidence fact with an optional `sourceError`. (`message_processing.py:88-110`)
2. **Upload-mention stripping before persistence.** Prevents phantom `/mnt/user-data/uploads/...` references from leaking into future sessions. (`updater.py:_strip_upload_mentions_from_memory`)
3. **Atomic memory writes with deep-copy cache update.** Crash-safe, and prevents the mtime cache from ever holding a reference that the on-disk file doesn't match. (`storage.py:146-174`)
4. **Debounced + per-thread-deduplicated queue.** Rapid-fire turns from the same thread collapse to a single update — saves LLM cost at the price of memory lag.
5. **Confidence, not similarity, drives injection.** No embedding budget, no retrieval drift, no reranker tuning. Entire signal comes from the update LLM's self-assigned confidence.
6. **CI-enforced harness/app boundary.** `tests/test_harness_boundary.py` forbids harness → app imports. Makes the harness PyPI-publishable and explains duplicated config surface.
7. **Deferred tool discovery via `contextvars.ContextVar`.** Per-request registry isolation under asyncio — the same pattern Claude Code uses internally, lifted directly.
8. **No vector store anywhere in the memory path.** Explicit product choice: explainability and user-editability > recall sophistication.
9. **User-facing memory CRUD UI.** Users can edit/delete/export memory, including individual facts. Aligned with 2026 industry trend (OpenAI, Anthropic, Dayfold).
10. **Gateway mode vs LangGraph mode.** Same harness runs in two deployment shapes; the sync/async bridge in `updater.py` exists precisely because of this duality.

---

## 12. Known Gaps / Limitations

- **No context-assembly pluggability.** You can add middlewares but you can't replace how the system prompt is built without forking `prompt.py`.
- **No per-query retrieval.** Memory injection is query-independent; any "relevance" comes from the confidence assigned at update time.
- **No fact relationships.** Flat list, no graph structure. Conflict resolution depends entirely on the update-LLM's prompt behavior.
- **Single namespace per agent.** No multi-tenant scoping beyond `agent_name` — `user_id` / `run_id` are not first-class.
- **Memory is one turn behind.** Debounce → background thread → LLM call → persist. User sees their new fact reflected only in a later conversation.
- **Local sandbox is not isolated.** Host filesystem access; production needs AIO Docker.
- **No streaming memory updates.** Memory cannot be written mid-turn (except via direct file edits) — no equivalent of Letta's in-context `core_memory_replace`.

---

## 13. Key Files (for deep-dives)

| Topic | File | Line |
|-------|------|------|
| Lead agent factory | `backend/packages/harness/deerflow/agents/lead_agent/agent.py` | `make_lead_agent()` @ 226 |
| Prompt assembly | `backend/packages/harness/deerflow/agents/lead_agent/prompt.py` | `apply_prompt_template()` @ 677+ |
| Middleware composition | `backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py` | `build_lead_runtime_middlewares()` @ 128 |
| Memory storage | `backend/packages/harness/deerflow/agents/memory/storage.py` | `FileMemoryStorage` @ 62, `save()` @ 146 |
| Memory queue | `backend/packages/harness/deerflow/agents/memory/queue.py` | `MemoryUpdateQueue` @ 27 |
| Memory updater | `backend/packages/harness/deerflow/agents/memory/updater.py` | `update_memory()` @ 299+ |
| Memory injection | `backend/packages/harness/deerflow/agents/memory/prompt.py` | `format_memory_for_injection()` @ 201 |
| Correction regex | `backend/packages/harness/deerflow/agents/memory/message_processing.py` | 88–110 |
| Subagent executor | `backend/packages/harness/deerflow/subagents/executor.py` | `MAX_CONCURRENT_SUBAGENTS=3` @ 532 |
| Tool search (deferred) | `backend/packages/harness/deerflow/tools/builtins/tool_search.py` | — |
| Sandbox abstract | `backend/packages/harness/deerflow/sandbox/sandbox.py` | 6–94 |
| Claude OAuth | `backend/packages/harness/deerflow/models/credential_loader.py` | — |
| Harness deps | `backend/packages/harness/pyproject.toml` | 13–22 |
| Harness boundary CI | `backend/tests/test_harness_boundary.py` | — |
| Frontend memory types | `frontend/src/core/memory/types.ts` | — |

---

## 14. Research Hooks (Follow-Ups for This Repo)

- **Benchmark**: DeerFlow is a clean comparator for memory-benchmarking (LongMemEval, MEMENTO, LoCoMo) — it exposes a tuning surface (`debounce_seconds`, `max_injection_tokens`, `fact_confidence_threshold`) that isolates the injection-budget variable cleanly. Worth including in the `memory-survey-2026.research.md` comparison table.
- **Correction/reinforcement channel**: The regex + `category:"correction"` flow is the most unambiguous in-the-wild implementation of "update from user feedback" I've seen in an open-source agent. Worth writing up as a standalone pattern for `hybrid-memory-weight.research.md` — it's not weight-level learning, but it's the closest data-level analogue.
- **User-facing memory UI**: `frontend/src/core/memory/` + API routes is a reference implementation for the pattern noted in `dayfold_webapp-memory` — user-controllable memory with confidence editing. Worth comparing against ChatGPT memory surface and Anthropic's memory preview.
- **Claude-Code-style tool search**: DeerFlow lifts the deferred-tool pattern directly. Cross-reference with `claude-code-context.research.md`.
- **Harness boundary pattern**: The CI-enforced harness/app split is a clean architectural pattern worth noting in `openclaw-memory.research.md` or a new `harness-patterns.research.md`.
