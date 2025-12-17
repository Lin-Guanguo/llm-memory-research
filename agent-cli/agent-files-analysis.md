# AI Agent CLI Session Files Analysis

Last Updated: 2025-12-17

## Overview

This document compares session file storage mechanisms across three AI coding assistants: **Claude Code**, **Codex (OpenAI)**, and **Gemini CLI**. The focus is on **chat history readability** for potential UI integration.

## Detailed Documentation

| Agent | Files Overview | Schema Details |
|-------|----------------|----------------|
| Claude Code | [claude-session-files.md](./claude-session-files.md) | [claude-session-file-schema.md](./claude-session-file-schema.md) |
| Codex | [codex-session-files.md](./codex-session-files.md) | [codex-session-file-schema.md](./codex-session-file-schema.md) |
| Gemini | [gemini-session-files.md](./gemini-session-files.md) | [gemini-session-file-schema.md](./gemini-session-file-schema.md) |

---

## Quick Comparison

| Feature | Claude Code | Codex | Gemini |
|---------|-------------|-------|--------|
| **Location** | `~/.claude/projects/` | `~/.codex/sessions/` | `~/.gemini/tmp/` |
| **Format** | JSONL | JSONL | JSON |
| **File per session** | Yes | Yes | Yes |
| **Can read chat** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Parsing complexity** | Medium | High | **Low** |

---

## Chat Readability Summary

### ✅ All Three Support Chat History Reading

| Agent | User Messages | Assistant Messages | Tool Calls | Tool Results |
|-------|--------------|-------------------|------------|--------------|
| Claude | `type: "user"` | `type: "assistant"` | `tool_use` in content | Separate `user` message |
| Codex | `event_msg.user_message` | `response_item.message` | `function_call` | `function_call_output` |
| Gemini | `type: "user"` | `type: "gemini"` | Inline `toolCalls` | Inline in `toolCalls.result` |

---

## Parsing Complexity Ranking

### 1. Gemini - **Easiest** ⭐

```javascript
// Simple JSON parse
const session = JSON.parse(fs.readFileSync(path));
const messages = session.messages; // Direct access
```

**Pros**:
- Single JSON file (not JSONL)
- Only 2 message types (`user`, `gemini`)
- Flat structure
- Tool results inline

**Cons**:
- Must load entire file into memory
- File references expanded inline (noise in user content)

---

### 2. Claude Code - **Medium**

```javascript
// JSONL parsing required
const lines = fs.readFileSync(path, 'utf-8').split('\n');
const messages = lines
  .filter(line => line)
  .map(line => JSON.parse(line))
  .filter(entry => entry.type === 'user' || entry.type === 'assistant');
```

**Pros**:
- Clear message types
- Tool calls in same message as text
- Good for streaming (line-by-line)

**Cons**:
- Multiple message types to handle
- Need to match `tool_use` with `tool_result` by ID
- Compact summaries need special handling

---

### 3. Codex - **Most Complex**

```javascript
// JSONL + nested payload
const lines = fs.readFileSync(path, 'utf-8').split('\n');
const messages = lines
  .filter(line => line)
  .map(line => JSON.parse(line))
  .filter(entry =>
    entry.type === 'response_item' &&
    entry.payload?.type === 'message'
  )
  .map(entry => ({
    role: entry.payload.role,
    content: entry.payload.content[0]?.text
  }));
```

**Pros**:
- Most detailed logging (every event)
- Token tracking per response
- Git snapshots for undo

**Cons**:
- 10+ entry types
- Deep nesting (`payload.content[0].text`)
- Need to distinguish `event_msg` vs `response_item`
- Function calls/outputs in separate entries

---

## Recommended Integration Approach

### For UI Integration (like Claude Code UI)

| Priority | Agent | Effort | Notes |
|----------|-------|--------|-------|
| 1 | **Gemini** | Low | Simple JSON, can reuse concepts |
| 2 | **Claude** | Medium | Already implemented |
| 3 | **Codex** | High | Complex filtering needed |

### Parsing Strategy

1. **Gemini**: Direct JSON parse, map messages
2. **Claude**: JSONL parse, filter by type, handle tool matching
3. **Codex**: JSONL parse, filter by type+payload.type, extract from nested structure

---

## Key Insights

### What Each Agent Stores

| Data Type | Claude | Codex | Gemini |
|-----------|--------|-------|--------|
| User text | ✅ | ✅ | ✅ |
| Assistant text | ✅ | ✅ | ✅ |
| Tool calls | ✅ | ✅ | ✅ |
| Tool results | ✅ | ✅ | ✅ |
| Token usage | ✅ | ✅ | ✅ |
| Git state | ✅ | ✅ | ❌ |
| Session metadata | ✅ | ✅ | ✅ |
| Reasoning | ❌ | ✅ (encrypted) | ✅ (empty) |

### Session Discovery

| Agent | How to List Sessions |
|-------|---------------------|
| Claude | Glob `~/.claude/projects/*/*.jsonl` |
| Codex | Glob `~/.codex/sessions/**/*.jsonl` or parse `history.jsonl` |
| Gemini | Glob `~/.gemini/tmp/*/chats/*.json` |

---

## Context Compression (Compact) Mechanisms

All three tools support context compression to manage long conversations. Their approaches differ significantly in storage strategy and data visibility.

### Quick Comparison

| Aspect | Claude Code | Codex | Gemini |
|--------|-------------|-------|--------|
| **Command** | Auto (context limit) | Auto | `/compress` |
| **Storage Location** | Same session file | Same session file | **New session file** |
| **Summary Visibility** | Plaintext | Encrypted | Not stored locally |
| **Marker Type** | `isCompactSummary: true` | `type: "compacted"` | `type: "info"` (empty) |
| **Encryption** | No | Yes | N/A |

---

### Claude Code: Inline Plaintext Summary

**Mechanism**: Claude inserts a special user message containing the conversation summary directly in the session file.

**Storage Structure**:
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "Here is a summary of our conversation: ..."
  },
  "isCompactSummary": true
}
```

**Characteristics**:
- Summary is **fully readable** in plaintext
- Appears as a synthetic "user" message
- Followed by `compact_boundary` system message
- Original conversation entries remain in file (but truncated from context)

**Pros**:
- Transparent: users can read exactly what the AI remembers
- Debuggable: easy to verify summary quality
- Single file: no need to track multiple files

**Cons**:
- Privacy: summary content visible in local files
- File size: old messages still stored (not deleted)

---

### Codex: Inline Encrypted Summary

**Mechanism**: Codex replaces conversation history with an encrypted `compacted` entry containing a `replacement_history` array.

**Storage Structure**:
```json
{
  "timestamp": "2025-12-15T23:47:53.813Z",
  "type": "compacted",
  "payload": {
    "message": "",
    "replacement_history": [
      { "type": "message", "role": "user", "content": "..." },
      { "type": "message", "role": "assistant", "content": "..." },
      {
        "type": "compaction",
        "encrypted_content": "eyJ0eXAiOiJKV1QiLCJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..."
      }
    ]
  }
}
```

**Characteristics**:
- Summary stored as **encrypted JWT** in `compaction.encrypted_content`
- Recent messages preserved in plaintext
- Followed by `context_compacted` event marker
- Server decrypts content when resuming session

**Pros**:
- Privacy: summary content not readable locally
- Security: sensitive code/context protected
- Compact: older entries replaced, not appended

**Cons**:
- Opaque: cannot verify what AI remembers
- Server-dependent: summary only accessible via Codex API
- Debugging: harder to troubleshoot context issues

---

### Gemini: Session Split (Server-Side)

**Mechanism**: Gemini creates a new session file after compression; no summary is stored locally.

**Storage Structure**:

**Before compress** (original session):
```json
{
  "sessionId": "cb7326d0-...",
  "startTime": "2025-12-16T06:35:09.158Z",
  "messages": [
    // ... full conversation ...
    { "type": "info", "content": "" }  // compress marker
  ]
}
```

**After compress** (new session file):
```json
{
  "sessionId": "cb7326d0-...",  // same sessionId
  "startTime": "2025-12-17T11:06:07.158Z",  // new startTime
  "messages": [
    // fresh conversation only
  ]
}
```

**Characteristics**:
- Empty `info` message marks compression point
- **New file** created with same `sessionId` but new `startTime`
- **No local summary** - context managed entirely server-side
- High input token count suggests server sends compressed context

**Pros**:
- Clean files: each session file stays small
- Privacy: no summary exposed locally
- Simple parsing: no special compact handling needed

**Cons**:
- Fragmented: conversation split across files
- Opaque: no visibility into compressed context
- Linkage: must match `sessionId` across files to trace history

---

### Architectural Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLAUDE CODE                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ session.jsonl                                            │    │
│  │ ├── user: "message 1"                                    │    │
│  │ ├── assistant: "response 1"                              │    │
│  │ ├── ...                                                  │    │
│  │ ├── user: "Here is summary..." (isCompactSummary: true) │◄── PLAINTEXT
│  │ ├── system: compact_boundary                             │    │
│  │ ├── user: "new message"                                  │    │
│  │ └── assistant: "new response"                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        CODEX                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ session.jsonl                                            │    │
│  │ ├── session_meta                                         │    │
│  │ ├── event_msg: user_message                              │    │
│  │ ├── response_item: message                               │    │
│  │ ├── compacted: {                                         │    │
│  │ │     replacement_history: [                             │    │
│  │ │       { type: "compaction",                            │    │
│  │ │         encrypted_content: "eyJ..." }  ◄─── ENCRYPTED  │    │
│  │ │     ]                                                  │    │
│  │ │   }                                                    │    │
│  │ ├── context_compacted                                    │    │
│  │ ├── event_msg: user_message (new)                        │    │
│  │ └── response_item: message (new)                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       GEMINI                                     │
│  ┌─────────────────────────┐  ┌─────────────────────────┐       │
│  │ session-old.json        │  │ session-new.json        │       │
│  │ sessionId: "abc123"     │  │ sessionId: "abc123"     │       │
│  │ ├── user: "message 1"   │  │ ├── user: "new msg"     │       │
│  │ ├── gemini: "response"  │  │ └── gemini: "response"  │       │
│  │ ├── ...                 │  │                         │       │
│  │ └── info: "" ◄── MARKER │  │   ◄─── NO SUMMARY       │       │
│  └─────────────────────────┘  └─────────────────────────┘       │
│           │                              ▲                       │
│           └──────── same sessionId ──────┘                       │
│                                                                  │
│  Summary: handled entirely server-side (not stored locally)      │
└─────────────────────────────────────────────────────────────────┘
```

---

### Design Philosophy Comparison

| Philosophy | Claude | Codex | Gemini |
|------------|--------|-------|--------|
| **Transparency** | High - user can read summary | Low - encrypted | None - not stored |
| **Privacy** | Low - plaintext on disk | High - encrypted | High - server-only |
| **Debuggability** | Easy | Hard | Medium |
| **File Management** | Single file grows | Single file, compacted | Multiple small files |
| **Server Dependency** | Low | High (for decryption) | High (for context) |

### Recommendations for Integration

**If building a session viewer**:

1. **Claude**: Display `isCompactSummary` messages with special styling (e.g., collapsible summary block)

2. **Codex**: Show "Context Compressed" placeholder for `type: "compacted"` entries; cannot display actual summary

3. **Gemini**: Link sessions by `sessionId`; show timeline across split files; indicate compress points via `type: "info"`

---

## Additional Analysis: Codex & Gemini Deep Dive

### Codex: Extended File Structure

Beyond session files, Codex maintains several additional data stores:

#### Global History (`~/.codex/history.jsonl`)

A global log of all user inputs across all sessions:

```json
{"session_id":"019ad40c-...","ts":1764494465,"text":"帮我分析下..."}
{"session_id":"019ad420-...","ts":1764495481,"text":"开始实现"}
```

**Use cases**:
- Cross-session search (find past commands)
- User behavior analytics
- Session discovery by content

#### Configuration (`~/.codex/config.toml`)

```toml
model = "gpt-5.2"
model_reasoning_effort = "xhigh"

[projects."/path/to/project"]
trust_level = "trusted"

[notice]
"hide_migration_prompt" = true
```

**Key settings**:
- `model`: Default model selection
- `model_reasoning_effort`: Reasoning intensity (low/medium/high/xhigh)
- `projects.*`: Per-project trust levels
- `notice.*`: UI notification preferences

#### TUI Logs (`~/.codex/log/codex-tui.log`)

```
2025-11-30T09:21:05Z INFO spawning ghost snapshot task
2025-11-30T09:21:06Z INFO ghost commit captured: 2e611a12...
2025-11-30T09:21:12Z INFO ToolCall: shell_command {"command":"ls",...}
2025-11-30T09:23:06Z WARN stream disconnected - retrying turn (1/5)...
```

**Logged events**:
- Ghost snapshot creation (git state capture)
- Tool call invocations with arguments
- Stream connection status and retries
- Model selection per session

#### Version Tracking (`~/.codex/version.json`)

```json
{
  "latest_version": "0.73.0",
  "last_checked_at": "2025-12-17T10:54:43.943Z",
  "dismissed_version": null
}
```

---

### Codex: Session Event Types

Codex sessions contain rich event metadata:

| Event Type | Description | Key Fields |
|------------|-------------|------------|
| `session_meta` | Session init | `id`, `cwd`, `cli_version`, `instructions`, `git` |
| `response_item` | Messages | `type`, `role`, `content` |
| `event_msg.user_message` | User input | `message`, `images` |
| `event_msg.agent_reasoning` | AI thinking | `text` (reasoning content) |
| `event_msg.token_count` | Token usage | `info.total_token_usage`, `rate_limits` |
| `event_msg.entered_review_mode` | Review started | `target.branch` |
| `event_msg.exited_review_mode` | Review done | `review_output.findings[]` |
| `event_msg.context_compacted` | Compression marker | (marker only) |
| `compacted` | Compression data | `replacement_history[]` |

#### Reasoning Storage

Codex stores AI reasoning as `agent_reasoning` events:

```json
{
  "type": "event_msg",
  "payload": {
    "type": "agent_reasoning",
    "text": "**Identifying potential bugs**\n\nI found possible issues..."
  }
}
```

#### Token Tracking

Detailed breakdown per response:

```json
{
  "info": {
    "total_token_usage": {
      "input_tokens": 16293,
      "cached_input_tokens": 4480,
      "output_tokens": 368,
      "reasoning_output_tokens": 256,
      "total_tokens": 16661
    },
    "model_context_window": 258400
  },
  "rate_limits": {
    "primary": { "used_percent": 0.0, "window_minutes": 300 },
    "secondary": { "used_percent": 0.0, "window_minutes": 10080 }
  }
}
```

---

### Gemini: Extended File Structure

#### Configuration Files

| File | Content | Example |
|------|---------|---------|
| `settings.json` | Auth & features | `{"security":{"auth":{"selectedType":"vertex-ai"}}}` |
| `state.json` | UI state | `{"defaultBannerShownCount": 2}` |
| `google_accounts.json` | Account info | `{"active": null, "old": []}` |
| `installation_id` | UUID | `d32f7d70-001a-491c-b711-6f9e0afe3e3e` |

#### Project-Level Files

Each project (`~/.gemini/tmp/{projectHash}/`) contains:

| File | Description |
|------|-------------|
| `chats/session-*.json` | Session conversations |
| `logs.json` | User input history |

**logs.json**:
```json
[
  {"sessionId": "...", "messageId": 0, "type": "user", "message": "...", "timestamp": "..."}
]
```

---

### Gemini: Session Event Types

| Field | Type | Description |
|-------|------|-------------|
| `type` | `user`/`gemini`/`info` | Message role |
| `thoughts` | `ThoughtEntry[]` | Reasoning (usually empty) |
| `tokens` | `TokenInfo` | Token breakdown |
| `model` | `string` | Model (e.g., `gemini-2.5-flash`) |
| `toolCalls` | `ToolCall[]` | Inline tool invocations |

#### Thoughts/Reasoning

When enabled, Gemini stores structured reasoning:

```json
{
  "thoughts": [
    {
      "subject": "Analyzing Code Revisions",
      "description": "I'm currently focused on...",
      "timestamp": "2025-12-16T06:35:15.023Z"
    }
  ]
}
```

**vs Codex**: Gemini uses structured `subject`/`description`, Codex uses freeform `agent_reasoning` text.

#### Token Tracking

```json
{
  "tokens": {
    "input": 22629,
    "output": 805,
    "cached": 0,
    "thoughts": 3174,
    "tool": 0,
    "total": 26608
  }
}
```

**Unique**: Gemini tracks `thoughts` tokens separately.

---

### Feature Comparison Matrix

| Feature | Claude | Codex | Gemini |
|---------|--------|-------|--------|
| **File Format** | JSONL | JSONL | JSON |
| **Global History** | `history.jsonl` (global) | `history.jsonl` (global) | `logs.json` (per-project) |
| **Config File** | `settings.json` | `config.toml` | `settings.json` |
| **Model Config** | Per session | Global + trust levels | Global only |
| **Reasoning Storage** | Not stored | `agent_reasoning` events | `thoughts[]` array |
| **Token Breakdown** | `usage` object | Detailed + rate limits | Includes `thoughts` |
| **Tool Calls** | Separate entries | `function_call` events | Inline `toolCalls[]` |
| **Git Integration** | `gitCurrentState` | `git` + ghost snapshots | Not stored |
| **Debug Logs** | `debug/{session}.txt` | `codex-tui.log` | Not exposed |
| **Usage Stats** | `stats-cache.json` | Not exposed | Not exposed |
| **Plugin System** | Full (marketplaces) | Not exposed | Not exposed |
| **Planning Mode** | `plans/*.md` | Not exposed | Not exposed |
| **Shell Snapshots** | `shell-snapshots/*.sh` | Not exposed | Not exposed |
| **File History** | `file-history/` | Ghost snapshots | Not stored |
| **Feature Flags** | Statsig | Not exposed | Not exposed |
| **IDE Integration** | `ide/*.lock` | Not exposed | Not exposed |

---

### Summary: Unique Strengths

**Claude Code**:
- **Most comprehensive data storage** - plugins, plans, skills, stats, IDE integration
- Plaintext compact summaries (transparent)
- Rich usage analytics (`stats-cache.json` with daily/hourly breakdowns)
- Full plugin marketplace system
- Planning mode with auto-named markdown files
- Shell environment snapshots
- Per-file version history with hash-based naming
- IDE integration locks (VS Code, JetBrains)
- Feature flags via Statsig

**Codex**:
- Most detailed token/rate limit tracking per response
- Ghost snapshots for git undo
- Global search via `history.jsonl`
- TUI logs for debugging
- Per-project trust levels in config
- Review mode events with confidence scores

**Gemini**:
- Simplest structure (single JSON per session)
- Structured thinking with subject/description
- Separate `thoughts` token tracking
- Clean session splitting on compress
- Server-side compression (no local summary)

---

## Conclusion

All three agents store readable chat history. **Gemini is easiest to parse**, followed by Claude, with Codex being the most complex due to its event-based architecture.

For building a unified UI:
1. Start with Gemini (simplest)
2. Adapt Claude patterns (already working)
3. Add Codex support last (most filtering logic needed)
