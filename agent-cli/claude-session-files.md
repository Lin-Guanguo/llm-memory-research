# Claude Code Session Files Structure

Last Updated: 2025-12-17

## Overview

Claude Code stores session data in `~/.claude/` directory. Beyond session files, it maintains comprehensive data for history, analytics, plugins, and more.

**Example Sessions**:
- `0340f328-33c2-42fb-b9fa-ae58a9d8a799` (from project `dayfold_webapp`)
- `a13cb7a0-f145-4ae2-80f2-dd489a02c51c` (from project `claudecodeui`)

## File Structure Summary

```
~/.claude/
├── CLAUDE.md                          # Global user instructions
├── history.jsonl                      # Global user input history (cross-session)
├── settings.json                      # User settings (plugins, statusLine)
├── stats-cache.json                   # Usage statistics and analytics
│
├── projects/                          # Per-project session files
│   └── {project-path-encoded}/
│       ├── {sessionId}.jsonl          # Main session conversation
│       └── agent-{agentId}.jsonl      # Sub-agent conversations (from Task tool)
│
├── debug/                             # Debug logs per session
│   └── {sessionId}.txt
│
├── file-history/                      # File version backups
│   └── {sessionId}/
│       └── {fileHash}@v{n}
│
├── todos/                             # TodoWrite persistence
│   └── {sessionId}-agent-{sessionId}.json
│
├── session-env/                       # Session environment (usually empty)
│   └── {sessionId}/
│
├── shell-snapshots/                   # Shell state snapshots
│   └── snapshot-{shell}-{timestamp}-{id}.sh
│
├── plans/                             # Planning mode files
│   └── {random-name}.md
│
├── ide/                               # IDE integration locks
│   └── {pid}.lock
│
├── plugins/                           # Plugin system
│   ├── installed_plugins.json
│   ├── known_marketplaces.json
│   ├── cache/                         # Plugin cache
│   └── marketplaces/                  # Plugin sources
│
├── skills/                            # User-defined skills
│   └── {skill-name}/
│       └── SKILL.md
│
├── statsig/                           # Feature flags (Statsig)
│   ├── statsig.stable_id.*
│   ├── statsig.session_id.*
│   └── statsig.cached.evaluations.*
│
├── telemetry/                         # Telemetry data
│
└── downloads/                         # Downloaded tools (e.g., ripgrep)
```

## Files for Example Sessions

### Session 1: `0340f328-33c2-42fb-b9fa-ae58a9d8a799` (dayfold_webapp)

| File | Path |
|------|------|
| Conversation | `~/.claude/projects/-Users-linguanguo-dev-dayfold-webapp/0340f328-33c2-42fb-b9fa-ae58a9d8a799.jsonl` |
| Session Env | `~/.claude/session-env/0340f328-33c2-42fb-b9fa-ae58a9d8a799/` |
| Todos | `~/.claude/todos/0340f328-33c2-42fb-b9fa-ae58a9d8a799-agent-0340f328-33c2-42fb-b9fa-ae58a9d8a799.json` |
| File History | `~/.claude/file-history/0340f328-33c2-42fb-b9fa-ae58a9d8a799/` |
| Debug Log | `~/.claude/debug/0340f328-33c2-42fb-b9fa-ae58a9d8a799.txt` |

### Session 2: `a13cb7a0-f145-4ae2-80f2-dd489a02c51c` (claudecodeui)

| File | Path |
|------|------|
| Conversation | `~/.claude/projects/-Users-linguanguo-dev-claudecodeui/a13cb7a0-f145-4ae2-80f2-dd489a02c51c.jsonl` |
| Session Env | `~/.claude/session-env/a13cb7a0-f145-4ae2-80f2-dd489a02c51c/` |
| Todos | `~/.claude/todos/a13cb7a0-f145-4ae2-80f2-dd489a02c51c-agent-a13cb7a0-f145-4ae2-80f2-dd489a02c51c.json` |
| File History | `~/.claude/file-history/a13cb7a0-f145-4ae2-80f2-dd489a02c51c/` |
| Debug Log | `~/.claude/debug/a13cb7a0-f145-4ae2-80f2-dd489a02c51c.txt` |

---

## 1. Conversation Files (`projects/*.jsonl`)

**Location**: `~/.claude/projects/{project-path-encoded}/{sessionId}.jsonl`

**Purpose**: Stores all conversation messages (user, assistant, system).

### File Naming

| Pattern | Description |
|---------|-------------|
| `{uuid}.jsonl` | Main session conversation |
| `agent-{hash}.jsonl` | Sub-agent conversation (spawned by Task tool) |

### Message Types

| type | Description |
|------|-------------|
| `user` | User messages (with `message.role = "user"`) |
| `assistant` | Assistant messages (with `message.role = "assistant"`) |
| `system` | System events (hooks, compaction, commands) |
| `summary` | Session summary (for session list display) |
| `file-history-snapshot` | File state snapshots |

### System Message Subtypes

| subtype | Description |
|---------|-------------|
| `init` | Session initialization |
| `stop_hook_summary` | Hook execution summary |
| `local_command` | Local command execution |
| `compact_boundary` | Marks where conversation was compacted |

### Example Entry (User Message)

```json
{
  "parentUuid": "previous-message-uuid",
  "sessionId": "0340f328-33c2-42fb-b9fa-ae58a9d8a799",
  "type": "user",
  "message": {
    "role": "user",
    "content": "Help me refactor this code"
  },
  "uuid": "current-message-uuid",
  "timestamp": "2025-12-07T08:00:00.000Z",
  "cwd": "/Users/linguanguo/dev/dayfold_webapp"
}
```

### Example Entry (Assistant with Tool Use)

```json
{
  "sessionId": "0340f328-33c2-42fb-b9fa-ae58a9d8a799",
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      { "type": "text", "text": "Let me read the file first." },
      { "type": "tool_use", "id": "toolu_xxx", "name": "Read", "input": { "file_path": "/path/to/file" } }
    ]
  },
  "uuid": "message-uuid",
  "timestamp": "2025-12-07T08:00:05.000Z"
}
```

### Example Entry (Compact Boundary)

```json
{
  "type": "system",
  "subtype": "compact_boundary",
  "content": "Conversation compacted",
  "sessionId": "0340f328-33c2-42fb-b9fa-ae58a9d8a799",
  "compactMetadata": {
    "trigger": "auto",
    "preTokens": 156579
  },
  "timestamp": "2025-12-07T07:48:48.698Z"
}
```

---

## 2. Session Environment (`session-env/`)

**Location**: `~/.claude/session-env/{sessionId}/`

**Purpose**: Store session-specific environment variables.

**Note**: Usually empty directory. May be used for future features or specific session configurations.

---

## 3. Todo List (`todos/`)

**Location**: `~/.claude/todos/{sessionId}-agent-{sessionId}.json`

**Purpose**: Persist TodoWrite tool data across session.

### Format

```json
[
  {
    "content": "Implement user authentication",
    "status": "completed",
    "activeForm": "Implementing user authentication"
  },
  {
    "content": "Write unit tests",
    "status": "in_progress",
    "activeForm": "Writing unit tests"
  }
]
```

### Status Values

| Status | Description |
|--------|-------------|
| `pending` | Task not started |
| `in_progress` | Currently working on |
| `completed` | Task finished |

---

## 4. File History (`file-history/`)

**Location**: `~/.claude/file-history/{sessionId}/{fileHash}@v{n}`

**Purpose**: Store file version backups for undo/revert functionality.

### File Naming

- `{fileHash}` - Hash of the original file path
- `@v{n}` - Version number (v1, v2, v3...)

### Example Files

```
~/.claude/file-history/0340f328-33c2-42fb-b9fa-ae58a9d8a799/
├── 27f22ea7d8c75a76@v1    # First backup of file A
├── 27f22ea7d8c75a76@v2    # Second version of file A
├── 41a54c2ac1135936@v1    # First backup of file B
├── 41a54c2ac1135936@v2    # Second version of file B
└── 41a54c2ac1135936@v3    # Third version of file B
```

### Content

Plain text file content (exact copy of the file at that version).

---

## 5. Debug Logs (`debug/`)

**Location**: `~/.claude/debug/{sessionId}.txt`

**Purpose**: Detailed debug information for troubleshooting.

### Log Contents

- LSP server initialization
- Hook execution details
- Permission rule applications
- Shell environment snapshots
- Configuration file writes
- Plugin and skill loading

### Example Log Entry

```
2025-12-07T04:17:24.497Z [DEBUG] Watching for changes in setting files...
2025-12-07T04:17:24.544Z [DEBUG] [LSP MANAGER] initializeLspServerManager() called
2025-12-07T04:17:24.546Z [DEBUG] Applying permission update: Adding 38 allow rule(s)...
2025-12-07T04:17:25.145Z [DEBUG] Ripgrep first use test: PASSED (mode=builtin)
```

---

## 6. Global History (`history.jsonl`)

**Location**: `~/.claude/history.jsonl`

**Purpose**: Global index of all user messages across all sessions. Similar to Codex's `history.jsonl`.

### Format

```json
{"display":"commit","pastedContents":{},"timestamp":1764179016070,"project":"/Users/linguanguo/dev/TermSupervisor","sessionId":"a9f00076-3216-43eb-b0f6-c72fa205e2ee"}
{"display":"汇总今天工作","pastedContents":{},"timestamp":1764178742168,"project":"/Users/linguanguo/dev/CyberMnema","sessionId":"74bf72dd-c554-4bdb-bb23-e229689586fa"}
```

| Field | Description |
|-------|-------------|
| `display` | User message text |
| `pastedContents` | Content pasted by user (usually empty `{}`) |
| `timestamp` | Unix timestamp (milliseconds) |
| `project` | Project path |
| `sessionId` | Session UUID (links to session file) |

**Use cases**:
- Cross-session search by keyword
- User activity analytics
- Session discovery by project

---

## 7. Settings (`settings.json`)

**Location**: `~/.claude/settings.json`

**Purpose**: User preferences and plugin configuration.

### Format

```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y ccstatusline@latest",
    "padding": 0
  },
  "enabledPlugins": {
    "frontend-design@claude-code-plugins": true,
    "agent-sdk-dev@claude-code-plugins": true,
    "commit-commands@claude-code-plugins": true,
    "feature-dev@claude-code-plugins": true,
    "document-skills@anthropic-agent-skills": true
  }
}
```

| Field | Description |
|-------|-------------|
| `statusLine.type` | Status line type: `command` / `text` / `none` |
| `statusLine.command` | Command to generate status line |
| `enabledPlugins` | Plugin enable/disable state by `name@marketplace` |

---

## 8. Usage Statistics (`stats-cache.json`)

**Location**: `~/.claude/stats-cache.json`

**Purpose**: Cached analytics for `/stats` command.

### Format

```json
{
  "version": 1,
  "lastComputedDate": "2025-12-16",
  "dailyActivity": [
    { "date": "2025-12-08", "messageCount": 11075, "sessionCount": 10, "toolCallCount": 3790 }
  ],
  "dailyModelTokens": [
    { "date": "2025-12-08", "tokensByModel": { "claude-opus-4-5-20251101": 1610931 } }
  ],
  "modelUsage": {
    "claude-opus-4-5-20251101": {
      "inputTokens": 4167204,
      "outputTokens": 7120303,
      "cacheReadInputTokens": 3684266252,
      "cacheCreationInputTokens": 176738437
    }
  },
  "totalSessions": 428,
  "totalMessages": 76318,
  "longestSession": {
    "sessionId": "d52f4b60-e29a-4582-b30c-f36a65e11fb5",
    "duration": 384389416,
    "messageCount": 311
  },
  "firstSessionDate": "2025-11-26T17:38:35.489Z",
  "hourCounts": { "20": 64, "21": 46, "11": 43 }
}
```

**Unique feature**: Claude Code is the only tool that provides this level of usage analytics locally.

---

## 9. Shell Snapshots (`shell-snapshots/`)

**Location**: `~/.claude/shell-snapshots/snapshot-{shell}-{timestamp}-{id}.sh`

**Purpose**: Capture shell environment (PATH, aliases) for consistent command execution.

### Format

```bash
# Snapshot file
# Unset all aliases to avoid conflicts with functions
unalias -a 2>/dev/null || true
# Check for rg availability
if ! command -v rg >/dev/null 2>&1; then
  alias rg='/Users/linguanguo/.claude/downloads/claude-2.0.54-darwin-arm64 --ripgrep'
fi
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:...
```

**Contents**:
- Shell environment variables (PATH)
- Alias configurations
- Ripgrep fallback setup

---

## 10. Plans (`plans/`)

**Location**: `~/.claude/plans/{random-name}.md`

**Purpose**: Store planning mode markdown files.

### Naming

Uses auto-generated adjective-verb-noun combinations:
- `binary-plotting-gizmo.md`
- `composed-floating-pebble.md`
- `melodic-waddling-rainbow.md`

### Format

```markdown
# Event Debug Page - Design Plan

## Goal
Add an "Event" debug page to `apps/debug/` for publishing Redis Pub/Sub events.

## Files to Modify/Create
1. `apps/debug/templates/base.html` - Add nav link
2. `apps/debug/templates/event.html` (new) - Form UI
3. `apps/debug/services/event.py` (new) - EventService class
4. `apps/debug/main.py` - Add routes

## Implementation Order
1. Create `services/event.py`
2. Create `templates/event.html`
3. Update `templates/base.html`
4. Update `main.py`
```

---

## 11. Plugins (`plugins/`)

**Location**: `~/.claude/plugins/`

**Structure**:
```
plugins/
├── installed_plugins.json     # Installed plugin registry
├── known_marketplaces.json    # Marketplace sources
├── cache/                     # Downloaded plugin cache
│   └── {marketplace}/{plugin}/{version}/
└── marketplaces/              # Marketplace repos
    └── {marketplace-name}/
```

### installed_plugins.json

```json
{
  "version": 2,
  "plugins": {
    "frontend-design@claude-code-plugins": [{
      "scope": "user",
      "installPath": "/Users/.../.claude/plugins/cache/claude-code-plugins/frontend-design/1.0.0",
      "version": "1.0.0",
      "installedAt": "2025-12-08T03:05:06.460Z",
      "gitCommitSha": "de49a076792f56beefb78b18fa60015145532808",
      "isLocal": true
    }]
  }
}
```

### known_marketplaces.json

```json
{
  "claude-code-plugins": {
    "source": { "source": "github", "repo": "anthropics/claude-code" },
    "installLocation": "/Users/.../.claude/plugins/marketplaces/claude-code-plugins",
    "lastUpdated": "2025-12-17T11:18:49.250Z"
  },
  "anthropic-agent-skills": {
    "source": { "source": "github", "repo": "anthropics/skills" },
    "installLocation": "/Users/.../.claude/plugins/marketplaces/anthropic-agent-skills",
    "lastUpdated": "2025-12-17T07:45:08.553Z"
  }
}
```

---

## 12. Skills (`skills/`)

**Location**: `~/.claude/skills/{skill-name}/SKILL.md`

**Purpose**: User-defined skills (custom prompts/workflows).

### Structure

```
skills/
├── codex/
│   └── SKILL.md
└── gemini/
    └── SKILL.md
```

---

## 13. Feature Flags (`statsig/`)

**Location**: `~/.claude/statsig/`

**Purpose**: Statsig feature flag integration.

| File | Description |
|------|-------------|
| `statsig.stable_id.*` | Persistent user ID for feature flags |
| `statsig.session_id.*` | Current session ID |
| `statsig.cached.evaluations.*` | Cached feature flag values |
| `statsig.failed_logs.*` | Failed log uploads |

---

## 14. IDE Integration (`ide/`)

**Location**: `~/.claude/ide/{pid}.lock`

**Purpose**: Lock files for IDE integrations (VS Code, JetBrains, etc.).

### Format

```json
{
  "type": "vscode",
  "vscodeWorkspacePath": "...",
  "webSocketPort": 45123
}
```

---

## Session ID Patterns

### Main Session vs Sub-Agent

| Pattern | Example | Description |
|---------|---------|-------------|
| UUID | `0340f328-33c2-42fb-b9fa-ae58a9d8a799` | Main session ID |
| `agent-{hash}` | `agent-71e369cc` | Sub-agent spawned by Task tool |

### Files Created per Agent

When Task tool spawns a sub-agent:
- Creates `agent-{agentId}.jsonl` in projects
- May share parent session's file-history
- Has separate entries in todos with `agent-{agentId}` suffix

---

## Project Path Encoding

Project paths are encoded for directory names:
- `/` replaced with `-`
- Prefix `-` added

**Example**:
- Original: `/Users/linguanguo/dev/dayfold_webapp`
- Encoded: `-Users-linguanguo-dev-dayfold-webapp`

---

## Related Documentation

- [Architecture Analysis](./architecture-analysis.md) - Overall UI architecture and mechanisms
- [Session File Schema](./claude-session-file-schema.md) - Detailed JSON schema for each file type
