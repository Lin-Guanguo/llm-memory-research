# Codex (OpenAI) Session Files Structure

Last Updated: 2025-12-17

## Overview

Codex CLI stores session data in `~/.codex/` directory. It uses JSONL format for conversation logs with detailed event-based structure.

## File Structure

```
~/.codex/
├── AGENTS.md              # User instructions (like CLAUDE.md)
├── auth.json              # Authentication credentials
├── config.toml            # Configuration file
├── history.jsonl          # Global history index (session list)
├── version.json           # CLI version info
├── log/
│   └── codex-tui.log      # Debug logs
└── sessions/
    └── YYYY/MM/DD/
        └── rollout-{timestamp}-{uuid}.jsonl  # Session conversations
```

## Reference Sessions

| Session | Size | Project |
|---------|------|---------|
| `019add38-07f3-7e93-ae71-3e0095eb0315` | 1.7MB | prompt_platform |
| `019ae296-90c0-7f12-88eb-22261c303796` | 1.6MB | dayfold_webapp |

## Key Files

### 1. Session Conversations (`sessions/YYYY/MM/DD/*.jsonl`)

**Location**: `~/.codex/sessions/{YYYY}/{MM}/{DD}/rollout-{timestamp}-{uuid}.jsonl`

**Format**: JSONL (one JSON object per line)

**Naming Pattern**: `rollout-{ISO-timestamp}-{uuid}.jsonl`
- Example: `rollout-2025-12-02T12-00-28-019add38-07f3-7e93-ae71-3e0095eb0315.jsonl`

### 2. History Index (`history.jsonl`)

**Purpose**: Global index of all user messages across sessions. Enables cross-session search.

**Format**: JSONL with entries:
```json
{
  "session_id": "019ad40c-81f1-7742-a72c-309a06f8f860",
  "ts": 1764494465,
  "text": "user message content"
}
```

| Field | Description |
|-------|-------------|
| `session_id` | Links to session file (UUID in filename) |
| `ts` | Unix timestamp (seconds) |
| `text` | User message text (full content) |

**Use cases**:
- Find sessions by keyword search
- Trace conversation history across sessions
- User behavior analytics

### 3. Configuration (`config.toml`)

Global configuration in TOML format:

```toml
model = "gpt-5.2"
model_reasoning_effort = "xhigh"

[projects."/path/to/project"]
trust_level = "trusted"

[notice]
"hide_gpt-5.1-codex-max_migration_prompt" = true
```

| Section | Description |
|---------|-------------|
| `model` | Default model selection |
| `model_reasoning_effort` | Reasoning intensity: `low` / `medium` / `high` / `xhigh` |
| `projects.*` | Per-project trust levels (`trusted` / `untrusted`) |
| `notice.*` | UI notification preferences (hide prompts) |

### 4. Authentication (`auth.json`)

OAuth/API authentication credentials (sensitive, not documented in detail).

### 5. Debug Logs (`log/codex-tui.log`)

TUI runtime logs with detailed execution trace:

```
2025-11-30T09:21:05Z INFO spawning ghost snapshot task
2025-11-30T09:21:06Z INFO ghost commit captured: 2e611a127369d3d...
2025-11-30T09:21:12Z INFO ToolCall: shell_command {"command":"ls","workdir":"..."}
2025-11-30T09:23:06Z WARN stream disconnected - retrying turn (1/5 in 193ms)...
2025-11-30T09:26:29Z WARN stream disconnected - retrying turn (1/5 in 183ms)...
```

**Logged events**:
| Event | Description |
|-------|-------------|
| Ghost snapshot | Git state capture before changes |
| ToolCall | Tool invocations with full arguments |
| Stream status | Connection retries and disconnections |
| Model selection | Model chosen for each session |

**Use cases**:
- Debug connection issues
- Trace tool execution
- Audit git operations

### 6. Version Tracking (`version.json`)

CLI version check state:

```json
{
  "latest_version": "0.73.0",
  "last_checked_at": "2025-12-17T10:54:43.943Z",
  "dismissed_version": null
}
```

| Field | Description |
|-------|-------------|
| `latest_version` | Latest available CLI version |
| `last_checked_at` | Last update check timestamp |
| `dismissed_version` | Version user dismissed update prompt for |

---

## Message Types in Session Files

Based on analysis of session files, Codex uses these primary `type` values:

| Type | Count (example) | Description |
|------|-----------------|-------------|
| `event_msg` | 783 | Event messages (user_message, agent_reasoning, context_compacted, etc.) |
| `response_item` | 724 | Response items (messages, tool calls, reasoning) |
| `token_count` | 522 | Token usage tracking |
| `turn_context` | 264 | Turn context (cwd, policies, model) |
| `function_call` | 169 | Tool invocations |
| `function_call_output` | 169 | Tool results |
| `reasoning` | 137 | Model reasoning blocks |
| `agent_reasoning` | 137 | Agent reasoning events |
| `message` | 123 | User/assistant messages |
| `ghost_snapshot` | 62 | Git snapshot metadata |
| `compacted` | varies | Context compaction entry (see schema) |
| `session_meta` | 1 | Session initialization |

---

## Chat Readability Assessment

### Can Read Chat History: **YES** (with parsing)

**Extractable Information**:
1. **User messages**: `type: "event_msg"` with `payload.type: "user_message"`
2. **Assistant text**: `type: "response_item"` with `payload.type: "message"` and `payload.role: "assistant"`
3. **Tool calls**: `type: "function_call"` with tool name and arguments
4. **Tool results**: `type: "function_call_output"` with output

**Complexity**: Medium - requires filtering by type and navigating nested payload structure.

### Key Differences from Claude

| Aspect | Codex | Claude |
|--------|-------|--------|
| Format | JSONL | JSONL |
| Nesting | Deep (`payload.content[].text`) | Medium (`message.content`) |
| Event-based | Yes (every event logged) | No (messages only) |
| Token tracking | Every response | Per message |
| Session ID | In filename + session_meta | In each message |

---

## Related Documentation

- [Codex Session File Schema](./codex-session-file-schema.md) - Detailed JSON schema
- [Agent Files Analysis](./agent-files-analysis.md) - Cross-tool comparison
