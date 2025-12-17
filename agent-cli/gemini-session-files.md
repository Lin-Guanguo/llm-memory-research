# Gemini CLI Session Files Structure

Last Updated: 2025-12-17

## Overview

Gemini CLI stores session data in `~/.gemini/` directory. It uses a single JSON file per session with a simpler structure compared to Codex/Claude.

## File Structure

```
~/.gemini/
├── GEMINI.md              # User instructions (like CLAUDE.md)
├── google_accounts.json   # Google account management
├── installation_id        # Unique installation UUID
├── settings.json          # CLI settings (auth, features)
├── state.json             # UI state (banners, etc.)
└── tmp/
    └── {project-hash}/
        ├── chats/
        │   └── session-{date}-{hash}.json  # Session conversations
        └── logs.json      # Per-project user input history
```

## Global Configuration Files

### settings.json

Authentication and feature settings:

```json
{
  "security": {
    "auth": {
      "selectedType": "vertex-ai"
    }
  },
  "general": {
    "previewFeatures": true
  }
}
```

| Field | Description |
|-------|-------------|
| `security.auth.selectedType` | Auth method: `vertex-ai` / `google-ai` |
| `general.previewFeatures` | Enable preview features |

### state.json

UI state tracking:

```json
{
  "defaultBannerShownCount": 2
}
```

### google_accounts.json

Account management:

```json
{
  "active": null,
  "old": []
}
```

### installation_id

Unique installation UUID (plain text file):

```
d32f7d70-001a-491c-b711-6f9e0afe3e3e
```

## Reference Sessions

| Session | Size | Project Hash |
|---------|------|--------------|
| `session-2025-11-30T10-16-92f625c6.json` | 229KB | `a33c3345...` |
| `session-2025-11-30T11-32-e086460b.json` | 213KB | `a33c3345...` |

## Key Files

### 1. Session Conversations (`tmp/{hash}/chats/*.json`)

**Location**: `~/.gemini/tmp/{project-hash}/chats/session-{date}-{hash}.json`

**Format**: Single JSON file (not JSONL)

**Naming Pattern**: `session-{YYYY-MM-DD}T{HH-MM}-{short-hash}.json`

### 2. Project Hash

Projects are identified by SHA-256 hash of the project path.

Example: `/Users/linguanguo/dev/termsupervisor` → `a33c3345ed592a7d6c2eb32b6ad11a280e0cafc473b2669402655b56894f5391`

### 3. Project Logs (`tmp/{hash}/logs.json`)

Per-project user input history (similar to Codex's global `history.jsonl`):

```json
[
  {
    "sessionId": "d33523c8-52e8-42fb-84d2-7212bf063d91",
    "messageId": 0,
    "type": "user",
    "message": "帮我查阅互联网资料...",
    "timestamp": "2025-12-08T14:04:16.711Z"
  },
  {
    "sessionId": "1c469382-d661-4048-8d37-7b87230a24bb",
    "messageId": 1,
    "type": "user",
    "message": "/compress",
    "timestamp": "2025-12-17T11:05:27.946Z"
  }
]
```

| Field | Description |
|-------|-------------|
| `sessionId` | Links to session file (short hash in filename) |
| `messageId` | Sequence number within session |
| `type` | Always `"user"` |
| `message` | User input text |
| `timestamp` | ISO 8601 timestamp |

**Use cases**:
- Find sessions by command (e.g., `/compress`)
- Track user activity within project
- Debug session history

---

## Session File Structure

### Top-Level Fields

```typescript
interface GeminiSession {
  sessionId: string;      // UUID
  projectHash: string;    // Project path hash
  startTime: string;      // ISO 8601
  lastUpdated: string;    // ISO 8601
  messages: GeminiMessage[];
}
```

### Message Types

Gemini uses **3 message types**:

| Type | Description |
|------|-------------|
| `user` | User input messages |
| `gemini` | Assistant responses |
| `info` | System info (e.g., compress marker) |

---

## Chat Readability Assessment

### Can Read Chat History: **YES** (very simple)

**Extractable Information**:
1. **User messages**: `type: "user"` → `content`
2. **Assistant messages**: `type: "gemini"` → `content`
3. **Token usage**: `type: "gemini"` → `tokens`
4. **Tool calls**: Embedded in gemini messages (if any)

**Complexity**: **Low** - Simple flat structure, easy to parse.

### Key Differences from Claude/Codex

| Aspect | Gemini | Claude | Codex |
|--------|--------|--------|-------|
| Format | JSON | JSONL | JSONL |
| Message types | 3 | 6+ | 10+ |
| Structure | Flat array | Per-line | Per-line |
| Tool calls | Inline | Separate | Separate |
| Session metadata | Top-level | First line | First line |
| Compress storage | New file (server-side) | Inline (plaintext) | Inline (encrypted) |

---

## Advantages

1. **Simplest structure** - Single JSON file, flat message array
2. **Easy to parse** - No need to handle JSONL line-by-line
3. **All data in one place** - No separate index files
4. **Clear message types** - `user`, `gemini`, and `info`

## Limitations

1. **No streaming support** - Must load entire file
2. **No tool call separation** - Tool calls embedded in content
3. **No event logging** - Less granular than Codex
4. **No visible compress summary** - Context managed server-side, not exposed to client

---

## Related Documentation

- [Gemini Session File Schema](./gemini-session-file-schema.md) - Detailed JSON schema
- [Agent Files Analysis](./agent-files-analysis.md) - Cross-tool comparison
