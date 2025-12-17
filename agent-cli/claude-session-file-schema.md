# Claude Code Session Files - Detailed Schema

Last Updated: 2025-12-08

## Overview

This document provides detailed JSON schema analysis for all session-related files in Claude Code. Each file type's structure, field types, and variations are documented.

Reference sessions:
- `0340f328-33c2-42fb-b9fa-ae58a9d8a799` (dayfold_webapp)
- `a13cb7a0-f145-4ae2-80f2-dd489a02c51c` (claudecodeui)

---

## 1. Conversation Files (`projects/*.jsonl`)

**Location**: `~/.claude/projects/{project-path-encoded}/{sessionId}.jsonl`

Each line is a JSON object. The `type` field determines the structure.

### 1.1 Common Fields (All Types)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uuid` | `string` | Yes | Unique message identifier (UUID v4) |
| `sessionId` | `string` | Yes | Parent session identifier |
| `timestamp` | `string` | Yes | ISO 8601 timestamp |
| `parentUuid` | `string\|null` | Yes | Previous message UUID (null for first message or after compact) |
| `type` | `string` | Yes | Message type: `user`, `assistant`, `system`, `summary`, `file-history-snapshot`, `queue-operation` |
| `cwd` | `string` | No | Working directory at time of message |
| `version` | `string` | No | Claude Code version (e.g., "2.0.60", "2.0.61") |
| `gitBranch` | `string` | No | Current git branch |
| `isSidechain` | `boolean` | No | Whether this is a side conversation branch |
| `userType` | `string` | No | User type (e.g., "external") |
| `slug` | `string` | No | Human-readable session identifier (e.g., "dazzling-popping-wren") |

---

### 1.2 Type: `user`

User messages sent to Claude.

#### Schema

```typescript
interface UserMessage {
  type: "user";
  uuid: string;
  sessionId: string;
  parentUuid: string | null;
  timestamp: string;
  cwd: string;
  version: string;
  gitBranch: string;
  isSidechain: boolean;
  userType: string;

  message: {
    role: "user";
    content: string | ContentBlock[];
  };

  // Optional fields
  thinkingMetadata?: {
    level: "none" | "low" | "medium" | "high";
    disabled: boolean;
    triggers: string[];
  };
  todos?: Todo[];
  isCompactSummary?: boolean;        // True if this is a compact summary injection
  isVisibleInTranscriptOnly?: boolean; // Hidden from normal display
}
```

#### Content Block Types (when content is array)

**Text Block:**
```json
{ "type": "text", "text": "message content" }
```

**Tool Result Block:**
```json
{
  "tool_use_id": "toolu_xxx",
  "type": "tool_result",
  "content": "result text or array",
  "is_error": false
}
```

#### Example: Simple Text Message

```json
{
  "parentUuid": null,
  "isSidechain": false,
  "userType": "external",
  "cwd": "/Users/linguanguo/dev/dayfold_webapp",
  "sessionId": "0340f328-33c2-42fb-b9fa-ae58a9d8a799",
  "version": "2.0.60",
  "gitBranch": "lgg/dev",
  "type": "user",
  "message": {
    "role": "user",
    "content": "review 一下现在的 langgraph 图设计"
  },
  "uuid": "880a9364-634b-4cc1-9acb-7992e89e69b8",
  "timestamp": "2025-12-07T04:18:24.082Z",
  "thinkingMetadata": {
    "level": "none",
    "disabled": true,
    "triggers": []
  },
  "todos": []
}
```

#### Example: Tool Result Message

```json
{
  "parentUuid": "c24724ea-c3af-44f6-8f87-dd81b705e583",
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      {
        "tool_use_id": "toolu_018Dk8tSPFgQJN2S1haw7Kw4",
        "type": "tool_result",
        "content": [
          {
            "type": "text",
            "text": "Agent execution result..."
          }
        ]
      }
    ]
  },
  "uuid": "edfca883-f934-480c-9b68-ce9cb2958917",
  "timestamp": "2025-12-07T04:19:32.222Z",
  "toolUseResult": {
    "status": "completed",
    "prompt": "original task prompt",
    "agentId": "12c788e6",
    "content": [{ "type": "text", "text": "..." }]
  }
}
```

#### Example: Compact Summary (Special User Message)

```json
{
  "parentUuid": "4833fe7a-6ec2-4701-a547-82a92a02cf8a",
  "type": "user",
  "message": {
    "role": "user",
    "content": "This session is being continued from a previous conversation that ran out of context. The conversation is summarized below:\nAnalysis:\n..."
  },
  "isVisibleInTranscriptOnly": true,
  "isCompactSummary": true,
  "uuid": "0456c057-773d-4a14-bef3-5ea6a2953604",
  "timestamp": "2025-12-07T07:48:48.698Z"
}
```

---

### 1.3 Type: `assistant`

Claude's responses, including text and tool use.

#### Schema

```typescript
interface AssistantMessage {
  type: "assistant";
  uuid: string;
  sessionId: string;
  parentUuid: string;
  timestamp: string;
  requestId: string;  // Anthropic API request ID

  message: {
    model: string;      // e.g., "claude-opus-4-5-20251101"
    id: string;         // Anthropic message ID "msg_xxx"
    type: "message";
    role: "assistant";
    content: ContentBlock[];
    stop_reason: string | null;
    stop_sequence: string | null;
    usage: UsageInfo;
  };
}

interface UsageInfo {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
  cache_creation: {
    ephemeral_5m_input_tokens: number;
    ephemeral_1h_input_tokens: number;
  };
  service_tier: string;
}
```

#### Content Block Types

**Text Block:**
```json
{
  "type": "text",
  "text": "Claude's response text"
}
```

**Tool Use Block:**
```json
{
  "type": "tool_use",
  "id": "toolu_xxx",
  "name": "ToolName",
  "input": { /* tool-specific parameters */ }
}
```

#### Example: Text Response

```json
{
  "parentUuid": "880a9364-634b-4cc1-9acb-7992e89e69b8",
  "sessionId": "0340f328-33c2-42fb-b9fa-ae58a9d8a799",
  "message": {
    "model": "claude-opus-4-5-20251101",
    "id": "msg_01CVcDokUeKzMUjj5TRGxRt5",
    "type": "message",
    "role": "assistant",
    "content": [
      {
        "type": "text",
        "text": "I'll first explore the current LangGraph graph implementation."
      }
    ],
    "stop_reason": null,
    "stop_sequence": null,
    "usage": {
      "input_tokens": 3,
      "cache_creation_input_tokens": 9272,
      "cache_read_input_tokens": 15414,
      "output_tokens": 1,
      "service_tier": "standard"
    }
  },
  "requestId": "req_011CVrgYAupL4YnibtDuha9z",
  "type": "assistant",
  "uuid": "87b6fe83-7a09-4aca-9377-052735b46545",
  "timestamp": "2025-12-07T04:18:27.549Z"
}
```

#### Example: Tool Use (Task Agent)

```json
{
  "parentUuid": "87b6fe83-7a09-4aca-9377-052735b46545",
  "message": {
    "model": "claude-opus-4-5-20251101",
    "role": "assistant",
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_018Dk8tSPFgQJN2S1haw7Kw4",
        "name": "Task",
        "input": {
          "description": "Explore LangGraph V3 graph",
          "prompt": "Thoroughly explore the LangGraph V3 graph...",
          "subagent_type": "Explore"
        }
      }
    ]
  },
  "type": "assistant",
  "uuid": "c24724ea-c3af-44f6-8f87-dd81b705e583"
}
```

#### Example: Tool Use (Read)

```json
{
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_01BUmhj9xvcNJk12k6x1JWMi",
        "name": "Read",
        "input": {
          "file_path": "/Users/linguanguo/dev/dayfold_webapp/docs/refactor_graph.md"
        }
      }
    ]
  },
  "type": "assistant"
}
```

#### Example: Tool Use (Edit)

```json
{
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_013AZR9vcn9JGoKCpyPmzYCC",
        "name": "Edit",
        "input": {
          "file_path": "/Users/linguanguo/dev/dayfold_webapp/docs/refactor_graph.md",
          "old_string": "# LangGraph V3 Refactor Plan\n\nLast Updated: 2025-12-04",
          "new_string": "# LangGraph V3 Refactor Plan\n\nLast Updated: 2025-12-07"
        }
      }
    ]
  },
  "type": "assistant"
}
```

---

### 1.4 Type: `system`

System events and commands. The `subtype` field determines the specific type.

#### Schema

```typescript
interface SystemMessage {
  type: "system";
  subtype: "init" | "stop_hook_summary" | "local_command" | "compact_boundary";
  uuid: string;
  sessionId: string;
  parentUuid: string | null;
  timestamp: string;
  level: "info" | "warning" | "error" | "suggestion";
  content?: string;
  isMeta?: boolean;
}
```

#### Subtype: `stop_hook_summary`

Hook execution summary after assistant response.

```typescript
interface StopHookSummary extends SystemMessage {
  subtype: "stop_hook_summary";
  hookCount: number;
  hookInfos: Array<{ command: string }>;
  hookErrors: string[];
  preventedContinuation: boolean;
  stopReason: string;
  hasOutput: boolean;
  toolUseID: string;
}
```

**Example:**

```json
{
  "parentUuid": "473b0706-6be5-4206-ace9-2cb6cee3ea02",
  "sessionId": "0340f328-33c2-42fb-b9fa-ae58a9d8a799",
  "type": "system",
  "subtype": "stop_hook_summary",
  "hookCount": 1,
  "hookInfos": [
    {
      "command": "(pgrep -f termsupervisor >/dev/null && curl -s --max-time 2 -X POST http://localhost:8765/api/hook -H 'Content-Type: application/json' -d '{...}' &) || true"
    }
  ],
  "hookErrors": [],
  "preventedContinuation": false,
  "stopReason": "",
  "hasOutput": true,
  "level": "suggestion",
  "timestamp": "2025-12-07T04:21:46.651Z",
  "uuid": "fdf8c340-37e4-4f38-95bd-c9ec6c8f0360",
  "toolUseID": "0b007e3b-c3e4-428f-a387-3ac11cc134b0"
}
```

#### Subtype: `local_command`

Slash command execution.

```typescript
interface LocalCommand extends SystemMessage {
  subtype: "local_command";
  content: string;  // Contains XML-formatted command info
}
```

**Content format:**
```xml
<command-name>/add-dir</command-name>
<command-message>add-dir</command-message>
<command-args></command-args>
```

**Or for output:**
```xml
<local-command-stdout>Workspace dialog dismissed</local-command-stdout>
```

**Example:**

```json
{
  "parentUuid": "bca9e88a-ed6c-4e15-b6b3-ef1d7d9ffea3",
  "sessionId": "0340f328-33c2-42fb-b9fa-ae58a9d8a799",
  "type": "system",
  "subtype": "local_command",
  "content": "<command-name>/add-dir</command-name>\n            <command-message>add-dir</command-message>\n            <command-args></command-args>",
  "level": "info",
  "timestamp": "2025-12-07T07:44:44.410Z",
  "uuid": "a1ccd655-ab60-401b-8a2b-075eb1c1ba12",
  "isMeta": false
}
```

#### Subtype: `compact_boundary`

Marks where conversation was compacted.

```typescript
interface CompactBoundary extends SystemMessage {
  subtype: "compact_boundary";
  content: "Conversation compacted";
  logicalParentUuid: string;  // UUID of last message before compact
  compactMetadata: {
    trigger: "auto" | "manual";
    preTokens: number;  // Token count before compaction
  };
}
```

**Example:**

```json
{
  "parentUuid": null,
  "logicalParentUuid": "91049500-4044-4e87-acb0-3842774db4ec",
  "sessionId": "0340f328-33c2-42fb-b9fa-ae58a9d8a799",
  "type": "system",
  "subtype": "compact_boundary",
  "content": "Conversation compacted",
  "isMeta": false,
  "timestamp": "2025-12-07T07:48:48.698Z",
  "uuid": "4833fe7a-6ec2-4701-a547-82a92a02cf8a",
  "level": "info",
  "compactMetadata": {
    "trigger": "auto",
    "preTokens": 156579
  }
}
```

---

### 1.5 Type: `summary`

Session summary for display in session list.

#### Schema

```typescript
interface SummaryMessage {
  type: "summary";
  summary: string;      // Short description of session
  leafUuid: string;     // UUID of the last message in conversation
}
```

**Example:**

```json
{
  "type": "summary",
  "summary": "LangGraph distributed workflow shutdown mechanism analysis",
  "leafUuid": "91049500-4044-4e87-acb0-3842774db4ec"
}
```

---

### 1.6 Type: `file-history-snapshot`

File state snapshots for undo/revert functionality.

#### Schema

```typescript
interface FileHistorySnapshot {
  type: "file-history-snapshot";
  messageId: string;           // Associated message UUID
  isSnapshotUpdate: boolean;   // false=initial, true=update
  snapshot: {
    messageId: string;
    timestamp: string;
    trackedFileBackups: {
      [filePath: string]: {
        backupFileName: string;  // Hash@version format
        version: number;
        backupTime: string;
      };
    };
  };
}
```

**Example (Initial - empty):**

```json
{
  "type": "file-history-snapshot",
  "messageId": "880a9364-634b-4cc1-9acb-7992e89e69b8",
  "snapshot": {
    "messageId": "880a9364-634b-4cc1-9acb-7992e89e69b8",
    "trackedFileBackups": {},
    "timestamp": "2025-12-07T04:18:24.087Z"
  },
  "isSnapshotUpdate": false
}
```

**Example (Update - with backups):**

```json
{
  "type": "file-history-snapshot",
  "messageId": "d25d71ef-9398-43cd-aa8a-b9bc4a385ade",
  "snapshot": {
    "messageId": "880a9364-634b-4cc1-9acb-7992e89e69b8",
    "trackedFileBackups": {
      "docs/refactor_graph.md": {
        "backupFileName": "d358f484ed29fb31@v1",
        "version": 1,
        "backupTime": "2025-12-07T04:20:56.513Z"
      }
    },
    "timestamp": "2025-12-07T04:18:24.087Z"
  },
  "isSnapshotUpdate": true
}
```

---

## 2. Todo List (`todos/*.json`)

**Location**: `~/.claude/todos/{sessionId}-agent-{sessionId}.json`

Simple JSON array of todo items.

#### Schema

```typescript
type TodoList = Todo[];

interface Todo {
  content: string;       // Task description (imperative form)
  status: "pending" | "in_progress" | "completed";
  activeForm: string;    // Task description (active form, e.g., "Implementing...")
}
```

**Example:**

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
  },
  {
    "content": "Update documentation",
    "status": "pending",
    "activeForm": "Updating documentation"
  }
]
```

**Note**: Empty todo list is represented as `[]`.

---

## 3. File History (`file-history/{sessionId}/*`)

**Location**: `~/.claude/file-history/{sessionId}/{fileHash}@v{n}`

Plain text files containing exact file content at each version.

#### File Naming

| Component | Description |
|-----------|-------------|
| `{fileHash}` | 16-character hash derived from file path |
| `@v{n}` | Version number (1, 2, 3...) |

#### Content

Plain text - exact copy of the file content at that version.

**Example filename**: `d358f484ed29fb31@v1`

**Example content** (first 50 lines of a markdown file):

```markdown
# LangGraph V3 Refactor Plan

Last Updated: 2025-12-07

## Context
- Current V3 graph (`services/langgraph_agent/workflow/story_graph_v3.py`)...
```

---

## 4. Debug Logs (`debug/{sessionId}.txt`)

**Location**: `~/.claude/debug/{sessionId}.txt`

Plain text log file with timestamped debug entries.

#### Format

```
{ISO8601 timestamp} [DEBUG] {message}
```

#### Log Categories

| Category | Description |
|----------|-------------|
| `[LSP MANAGER]` | LSP server initialization |
| `[LSP SERVER MANAGER]` | LSP server state |
| Settings | Permission rules, file watching |
| Skills/Plugins | Plugin and skill loading |
| Shell | Shell environment snapshots |
| Git | Repository detection |
| Hooks | Hook execution |
| File writes | Atomic file operations |

**Example:**

```
2025-12-07T04:17:24.497Z [DEBUG] Watching for changes in setting files...
2025-12-07T04:17:24.544Z [DEBUG] [LSP MANAGER] initializeLspServerManager() called
2025-12-07T04:17:24.544Z [DEBUG] [LSP MANAGER] Created manager instance, state=pending
2025-12-07T04:17:24.546Z [DEBUG] Applying permission update: Adding 38 allow rule(s)...
2025-12-07T04:17:24.547Z [DEBUG] Found 0 plugins (0 enabled, 0 disabled)
2025-12-07T04:17:24.569Z [DEBUG] Writing to temp file: ~/.claude/todos/{sessionId}.json.tmp.4699
2025-12-07T04:17:24.570Z [DEBUG] File written atomically
2025-12-07T04:17:25.145Z [DEBUG] Ripgrep first use test: PASSED (mode=builtin)
2025-12-07T04:17:25.377Z [DEBUG] Successfully parsed and validated hook JSON output
```

---

## 5. Session Environment (`session-env/{sessionId}/`)

**Location**: `~/.claude/session-env/{sessionId}/`

Empty directory for session-specific environment variables.

**Note**: Currently unused. Reserved for future features or custom session configurations.

---

### 1.7 Type: `queue-operation`

Message queue operations for pending user input (including images).

#### Schema

```typescript
interface QueueOperation {
  type: "queue-operation";
  operation: "enqueue" | "dequeue" | "remove";
  timestamp: string;
  sessionId: string;
  content?: string;  // User message content (may include "[Image #N]" placeholder)
}
```

**Example (Enqueue with Image):**

```json
{
  "type": "queue-operation",
  "operation": "enqueue",
  "timestamp": "2025-12-08T03:37:10.789Z",
  "sessionId": "a13cb7a0-f145-4ae2-80f2-dd489a02c51c",
  "content": "[Image #1] 我在这个 session 里上传个图片，这个消息你不用处理"
}
```

**Example (Remove after processing):**

```json
{
  "type": "queue-operation",
  "operation": "remove",
  "timestamp": "2025-12-08T03:37:12.389Z",
  "sessionId": "a13cb7a0-f145-4ae2-80f2-dd489a02c51c"
}
```

**Note on Images:**
- Images are NOT stored in the JSONL file directly
- The `[Image #N]` placeholder indicates an image was attached
- Actual image data is saved to temporary files (see `server/claude-sdk.js:handleImages()`)
- Temp files are stored in `{cwd}/.tmp/images/{timestamp}/image_{n}.{ext}`
- After processing, temp files are cleaned up

---

### 1.8 Enhanced Tool Result Fields

When `type: "user"` contains `tool_result`, additional metadata is included in `toolUseResult`:

#### For Bash Tool Results

```typescript
interface BashToolUseResult {
  stdout: string;
  stderr: string;
  interrupted: boolean;
  isImage: boolean;  // True if output contains image data
}
```

**Example:**

```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [{
      "tool_use_id": "toolu_01Ghdes6ZnjVAL7iZX87cEqY",
      "type": "tool_result",
      "content": "output text",
      "is_error": false
    }]
  },
  "toolUseResult": {
    "stdout": "output text",
    "stderr": "",
    "interrupted": false,
    "isImage": false
  }
}
```

#### For Edit Tool Results

```typescript
interface EditToolUseResult {
  filePath: string;
  oldString: string;
  newString: string;
  originalFile: string;        // Full file content before edit
  structuredPatch: Patch[];    // Diff information
  userModified: boolean;
  replaceAll: boolean;
}

interface Patch {
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  lines: string[];  // Lines with "-" (removed) or "+" (added) prefix
}
```

#### For Read Tool Results

```typescript
interface ReadToolUseResult {
  type: "text";
  file: {
    filePath: string;
    content: string;
  };
}
```

#### For Task (Agent) Tool Results

```typescript
interface TaskToolUseResult {
  status: "completed" | "error";
  prompt: string;
  agentId: string;
  content: ContentBlock[];
}
```

---

## Quick Reference: Type Discrimination

### Message Types in JSONL

| `type` | `subtype` / Flag | Description |
|--------|------------------|-------------|
| `user` | - | User message or tool result |
| `user` | `isCompactSummary: true` | Compact summary injection |
| `assistant` | - | Claude response |
| `system` | `init` | Session initialization |
| `system` | `stop_hook_summary` | Hook execution summary |
| `system` | `local_command` | Slash command |
| `system` | `compact_boundary` | Compaction marker |
| `summary` | - | Session summary |
| `file-history-snapshot` | - | File backup state |
| `queue-operation` | `operation: enqueue` | User message queued (may include image) |
| `queue-operation` | `operation: dequeue` | Message dequeued for processing |
| `queue-operation` | `operation: remove` | Message removed from queue |

### Content Block Types (in message.content array)

| `type` | Location | Description |
|--------|----------|-------------|
| `text` | user/assistant | Plain text content |
| `tool_use` | assistant | Tool invocation |
| `tool_result` | user | Tool execution result |

---

## Related Documentation

- [Session Files Overview](./claude-session-files.md) - High-level file structure
- [Architecture Analysis](./architecture-analysis.md) - UI integration mechanisms
