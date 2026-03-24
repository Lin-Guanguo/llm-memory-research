# OpenClaw Memory System Research

Last Updated: 2026-03-24

Source: [openclaw/openclaw](https://github.com/openclaw/openclaw)

Research focus: How OpenClaw persists and retrieves cross-session memory. This complements `openclaw.research.md` (which covers context management only).

---

## Architecture Overview

OpenClaw has the most sophisticated memory system among all coding agents studied. While Claude Code, Codex, and Gemini CLI rely on plain files (CLAUDE.md, AGENTS.md) with no indexing or retrieval intelligence, OpenClaw implements a full **hybrid search pipeline with temporal decay, MMR diversity re-ranking, and an automatic pre-compaction memory flush**.

Key source locations:

| Layer | Path | Role |
|-------|------|------|
| Memory Manager | `src/memory/manager.ts` | Core indexing, search orchestration, file watching |
| Hybrid Search | `src/memory/hybrid.ts` | Vector + BM25 weighted merge |
| Temporal Decay | `src/memory/temporal-decay.ts` | Recency-aware score adjustment |
| MMR Re-ranking | `src/memory/mmr.ts` | Diversity-aware result deduplication |
| Memory Schema | `src/memory/memory-schema.ts` | SQLite schema (files, chunks, embeddings, FTS) |
| Memory Tools | `src/agents/tools/memory-tool.ts` | `memory_search` and `memory_get` tool definitions |
| Memory Flush | `src/auto-reply/reply/memory-flush.ts` | Pre-compaction memory persistence trigger |
| Session Files | `src/memory/session-files.ts` | JSONL session transcript parsing for indexing |
| Query Expansion | `src/memory/query-expansion.ts` | Keyword extraction for FTS-only fallback |
| QMD Backend | `src/memory/qmd-manager.ts` | Experimental external search sidecar |
| Official Docs | `docs/concepts/memory.md` | User-facing memory documentation |

---

## Two-Tier Storage: Daily Log + Evergreen Knowledge

Memory is **plain Markdown files in the agent workspace** — the files are the source of truth.

```
~/.openclaw/workspace/
├── MEMORY.md              ← Evergreen: curated long-term knowledge, never decays
├── memory/
│   ├── 2026-03-24.md      ← Daily Log: today's append-only notes
│   ├── 2026-03-23.md      ← Daily Log: yesterday's notes
│   ├── projects.md        ← Evergreen: topic file, never decays
│   └── network.md         ← Evergreen: topic file, never decays
```

### Tier 1: Daily Log (`memory/YYYY-MM-DD.md`)

- One file per day, append-only
- Date parsed from filename via regex: `/memory\/(\d{4})-(\d{2})-(\d{2})\.md$/` (`temporal-decay.ts:15`)
- Only today's and yesterday's daily logs are loaded at session start
- Subject to temporal decay (§ Temporal Decay)

### Tier 2: Evergreen (`MEMORY.md`, non-dated `memory/*.md`)

- Curated, durable knowledge — preferences, decisions, reference info
- `MEMORY.md` takes precedence over `memory.md` if both exist (`docs/concepts/memory.md:26`)
- `MEMORY.md` only loaded in private sessions, never in group contexts (`docs/concepts/memory.md:28`)
- **Never decayed** — evergreen detection via `isEvergreenMemoryPath()` (`temporal-decay.ts:71-80`)

### When to Write

From `docs/concepts/memory.md`:
- Decisions, preferences, durable facts → `MEMORY.md`
- Day-to-day notes, running context → `memory/YYYY-MM-DD.md`
- If user says "remember this," write it to disk (do not keep in RAM)

---

## Hybrid Search Pipeline

OpenClaw's retrieval is a four-stage pipeline — significantly more sophisticated than any other coding agent studied:

```
Query
  │
  ├─► Vector Search (cosine similarity via embedding provider)
  │
  ├─► BM25 Keyword Search (FTS5 full-text search)
  │
  ▼
Weighted Merge (0.7 × vector + 0.3 × keyword)
  │
  ▼
Temporal Decay (optional, exponential decay by file age)
  │
  ▼
Sort by score
  │
  ▼
MMR Re-ranking (optional, diversity-aware deduplication)
  │
  ▼
Top-K Results → memory_search tool response
```

### Stage 1: Parallel Search

Vector and keyword searches run in parallel (`manager-search.ts`):

- **Vector**: Cosine similarity via embedding provider (OpenAI, Gemini, Voyage, Mistral, Ollama, or local GGUF)
- **Keyword**: FTS5 BM25 rank, converted to 0..1 score: `textScore = 1 / (1 + max(0, bm25Rank))` (`hybrid.ts:46-55`)

### Stage 2: Weighted Merge

```typescript
finalScore = vectorWeight × vectorScore + textWeight × textScore
// Default: 0.7 × vector + 0.3 × keyword
```

Candidates are unioned by chunk ID. A chunk appearing in both vector and keyword results gets both scores combined (`hybrid.ts:57-155`).

### Stage 3: Temporal Decay (Optional)

Exponential decay based on file age:

```
decayedScore = score × e^(-λ × ageInDays)
where λ = ln(2) / halfLifeDays
```

Default half-life: **30 days** (`temporal-decay.ts:10-12`).

| Age | Score multiplier |
|-----|-----------------|
| Today | 100% |
| 7 days | ~84% |
| 30 days | 50% (half-life) |
| 90 days | 12.5% |
| 180 days | ~1.6% |

**Evergreen exemption**: `MEMORY.md`, `memory.md`, and non-dated `memory/*.md` files return `null` from `extractTimestamp()`, so they are never decayed (`temporal-decay.ts:92-95`).

**Date extraction order**:
1. Parse date from filename (`memory/YYYY-MM-DD.md`)
2. If evergreen → no decay (return `null`)
3. Fallback: file `mtime` (used for session transcripts)

### Stage 4: MMR Re-ranking (Optional)

**Maximal Marginal Relevance** (Carbonell & Goldstein, 1998) reduces redundant results — important when daily logs repeat similar content across days.

Formula: `MMR = λ × relevance − (1−λ) × max_similarity_to_selected`

- Similarity measured via **Jaccard coefficient** on tokenized text (`mmr.ts:41-61`)
- Default λ = 0.7 (balanced, slight relevance bias)
- Iteratively selects items that maximize MMR score (`mmr.ts:116-183`)
- Scores normalized to [0, 1] before comparison (`mmr.ts:139-148`)

---

## Memory Tools

Two agent-facing tools exposed via `src/agents/tools/memory-tool.ts`:

### `memory_search`

- **Description**: "Mandatory recall step: semantically search MEMORY.md + memory/*.md (and optional session transcripts) before answering questions about prior work, decisions, dates, people, preferences, or todos"
- **Parameters**: `query` (string), `maxResults?` (number), `minScore?` (number)
- **Returns**: Snippets with path, line range, score, provider/model metadata, citation
- **Citations**: Configurable (`auto`/`on`/`off`); auto mode shows citations in DMs, suppresses in groups

### `memory_get`

- **Description**: "Safe snippet read from MEMORY.md or memory/*.md with optional from/lines; use after memory_search to pull only the needed lines and keep context small"
- **Parameters**: `path` (string), `from?` (number), `lines?` (number)
- **Graceful degradation**: Returns `{ text: "", path }` if file doesn't exist (no exception)

---

## Pre-Compaction Memory Flush

The most architecturally significant feature — **connecting context compaction to memory persistence**.

When a session approaches compaction threshold, OpenClaw injects a **silent agentic turn** that reminds the model to write durable knowledge to `memory/YYYY-MM-DD.md` before the context is purged.

### Trigger Conditions (`memory-flush.ts:170-215`)

Two independent triggers:
1. **Token-based**: `totalTokens >= contextWindow - reserveTokensFloor - softThresholdTokens` (default soft threshold: 4000 tokens)
2. **Transcript size-based**: Session transcript exceeds `forceFlushTranscriptBytes` (default: 2 MB)

### Flush Behavior

- **Silent**: Default prompts include `NO_REPLY` token so user never sees the turn
- **One flush per compaction cycle**: Tracked via `memoryFlushCompactionCount` in session entry (`memory-flush.ts:222-228`)
- **Workspace must be writable**: Skipped if sandbox has `workspaceAccess: "ro"` or `"none"`
- **Date-aware**: Prompt replaces `YYYY-MM-DD` with actual date in user's timezone (`memory-flush.ts:43-57`)
- **Safety hints enforced**: Even if user overrides prompt, these hints are always appended (`memory-flush.ts:151-159`):
  - Store only in `memory/YYYY-MM-DD.md`
  - Append-only (don't overwrite existing entries)
  - Treat MEMORY.md, SOUL.md, TOOLS.md, AGENTS.md as read-only during flush

### Default Prompts

System prompt:
```
Pre-compaction memory flush turn.
The session is near auto-compaction; capture durable memories to disk.
Store durable memories only in memory/YYYY-MM-DD.md (create memory/ if needed).
Treat workspace bootstrap/reference files such as MEMORY.md, SOUL.md, TOOLS.md, and AGENTS.md as read-only during this flush; never overwrite, replace, or edit them.
If memory/YYYY-MM-DD.md already exists, APPEND new content only and do not overwrite existing entries.
You may reply, but usually NO_REPLY is correct.
```

User prompt:
```
Pre-compaction memory flush.
Store durable memories only in memory/YYYY-MM-DD.md (create memory/ if needed).
...
If nothing to store, reply with NO_REPLY.
```

---

## Indexing & Storage

### SQLite Schema (`memory-schema.ts`)

Per-agent SQLite database at `~/.openclaw/memory/<agentId>.sqlite`:

| Table | Purpose |
|-------|---------|
| `meta` | Key-value metadata store |
| `files` | File metadata: path, source, hash, mtime, size |
| `chunks` | Text chunks: id, path, source, start/end line, hash, model, text, embedding, updated_at |
| `embedding_cache` | Cached embeddings by provider/model/hash |
| `chunks_fts` | FTS5 virtual table for BM25 keyword search |
| `chunks_vec` | Vector table via sqlite-vec extension for cosine similarity |

### Chunking

- Default: **400 tokens per chunk**, 80-token overlap
- Configurable via `memorySearch.chunking.tokens` / `.overlap`
- Snippet output capped at 700 chars (`manager.ts:34`)

### Sync Triggers

| Trigger | Description |
|---------|-------------|
| Session start | If `sync.onSessionStart = true` |
| On search | If `sync.onSearch = true` and index is dirty |
| Interval | Default 5-minute refresh |
| File watch | Debounced 1.5s via chokidar watcher |

### Watch Paths

```
MEMORY.md
memory.md
memory/**/*.md
```

Hash-based deduplication detects unchanged content, avoiding re-embedding.

---

## Embedding Providers

6 providers supported, auto-selected in priority order (`memory-search.ts`):

| Priority | Provider | Default Model | Dimensions |
|----------|----------|---------------|------------|
| 1 | local | `embeddinggemma-300m-qat-Q8_0.gguf` (auto-download, ~0.6 GB) | varies |
| 2 | openai | `text-embedding-3-small` | 1536 |
| 3 | gemini | `gemini-embedding-001` or `gemini-embedding-2-preview` | 768/1536/3072 |
| 4 | voyage | `voyage-4-large` | 1024 |
| 5 | mistral | `mistral-embed` | varies |
| 6 | ollama | `nomic-embed-text` (self-hosted, not auto-selected) | varies |

Auto-selection only triggers if explicit `memorySearch.provider` is not set.

Vector acceleration: sqlite-vec extension for native SQLite cosine distance queries; falls back to JS computation if unavailable.

---

## Experimental Features

### Session Transcript Indexing

Index session JSONL files and surface via `memory_search`:

- Opt-in: `memorySearch.experimental.sessionMemory = true`
- Delta-based sync: triggers after `deltaBytes` (100KB) or `deltaMessages` (50 lines)
- Asynchronous, best-effort — never blocks `memory_search`
- Isolated per agent
- Session text extracted from JSONL: User/Assistant turns, sensitive text redacted (`session-files.ts:46-72`)

### QMD Backend

External local-first search sidecar (`memory.backend = "qmd"`):

- Combines BM25 + vectors + reranking via [QMD](https://github.com/tobi/qmd)
- Auto-downloads GGUF models from HuggingFace
- Runs in self-contained XDG home under `~/.openclaw/agents/<id>/qmd/`
- Automatic fallback to builtin SQLite if QMD fails

### Multimodal Memory (Gemini Embedding 2)

Index images and audio alongside Markdown:

- Requires `gemini-embedding-2-preview`
- Supported: `.jpg`, `.png`, `.webp`, `.gif`, `.heic`, `.heif`, `.mp3`, `.wav`, `.ogg`, `.opus`, `.m4a`, `.aac`, `.flac`
- Search queries remain text; Gemini compares text queries against image/audio embeddings
- Only applies to files in `memorySearch.extraPaths`, not default memory roots

### Query Expansion (FTS-only fallback)

When no embedding provider is available, `query-expansion.ts` extracts keywords from conversational queries for FTS search. Includes stop word removal for English, Spanish, and CJK.

---

## Comparison: OpenClaw vs Other Coding Agent Memory Systems

| Dimension | OpenClaw | Claude Code | Codex | Gemini CLI | Pi |
|-----------|---------|-------------|-------|------------|-----|
| **Storage format** | Markdown files (daily + evergreen) | CLAUDE.md + MEMORY.md | AGENTS.md | GEMINI.md | None |
| **Indexing** | SQLite (embeddings + FTS5) | None | None | None | None |
| **Search** | Hybrid (vector + BM25) | Text search (grep/glob) | Text search (rg) | Text search (grep/glob) | None |
| **Temporal awareness** | Exponential decay (30-day half-life) | None | None | None | None |
| **Diversity re-ranking** | MMR (Jaccard-based) | None | None | None | None |
| **Pre-compaction persistence** | Automatic memory flush | None | None | None | None |
| **Session transcript search** | Optional (experimental) | None | None | None | None |
| **Multimodal memory** | Image + audio (Gemini, experimental) | None | None | None | None |
| **Embedding providers** | 6 (OpenAI, Gemini, Voyage, Mistral, Ollama, local) | N/A | N/A | N/A | N/A |

OpenClaw is the **only coding agent** that treats memory as a first-class retrieval problem with IR techniques (hybrid search, temporal decay, MMR). All others treat memory as plain files read at session start.

---

## Design Philosophy

1. **Files as source of truth**: All memory lives in plain Markdown — readable, editable, version-controllable. The SQLite index is derived and can be rebuilt.
2. **Two temporal modes**: Daily logs decay, evergreen knowledge persists. This matches human memory — recent events are vivid, important facts last forever.
3. **Pluggable retrieval**: Builtin SQLite or QMD sidecar; 6 embedding providers; hybrid search configurable at every stage.
4. **Context↔Memory bridge**: The pre-compaction memory flush is architecturally unique — it's the only system that automatically persists context into memory before compaction destroys it.
5. **Graceful degradation**: No embedding provider → FTS-only with query expansion. No FTS → vector-only. No vector → search disabled. Each layer falls back independently.

---

## Significance for Blog

OpenClaw's memory system demonstrates that the **context management ↔ memory persistence boundary is a design choice, not a given**. Most agents treat context (within-session) and memory (cross-session) as separate systems. OpenClaw's pre-compaction memory flush explicitly bridges the two: context that's about to be compressed gets an opportunity to become durable memory first.

This is the only implementation found that addresses the research finding in `findings.md` ("Memory and Context Are the Same Problem at Different Time Scales") at the architecture level.
