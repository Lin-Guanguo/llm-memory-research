# Gemini Session Files - Detailed Schema

Last Updated: 2025-12-17

## Overview

This document provides detailed JSON schema for Gemini CLI session files. Each session is a single JSON file with a flat structure.

---

## 1. Session File Schema

```typescript
interface GeminiSession {
  sessionId: string;       // UUID v4
  projectHash: string;     // SHA-256 of project path
  startTime: string;       // ISO 8601 timestamp
  lastUpdated: string;     // ISO 8601 timestamp
  messages: GeminiMessage[];
}
```

### Example Top-Level

```json
{
  "sessionId": "92f625c6-a764-48e3-b922-3766d41f9c4c",
  "projectHash": "a33c3345ed592a7d6c2eb32b6ad11a280e0cafc473b2669402655b56894f5391",
  "startTime": "2025-11-30T10:17:28.309Z",
  "lastUpdated": "2025-11-30T10:29:00.016Z",
  "messages": [...]
}
```

---

## 2. Message Types

### 2.1 Type: `user`

User input messages.

```typescript
interface UserMessage {
  id: string;           // UUID v4
  timestamp: string;    // ISO 8601
  type: "user";
  content: string;      // User text (may include file references)
}
```

### Example

```json
{
  "id": "11f0cba9-b50b-4c62-9b56-3597c4392039",
  "timestamp": "2025-11-30T10:17:28.309Z",
  "type": "user",
  "content": "帮我 review 一下 @mnema/state-architecture/** ，有什么方案优化空间\n--- Content from referenced files ---\nContent from @mnema/state-architecture/refactor_01_timer.md:\n# Step 1: Timer 模块..."
}
```

**Note**: File references (like `@path/**`) are expanded inline in the `content` field with a delimiter `--- Content from referenced files ---`.

---

### 2.2 Type: `gemini`

Assistant responses with optional metadata.

```typescript
interface GeminiMessage {
  id: string;           // UUID v4
  timestamp: string;    // ISO 8601
  type: "gemini";
  content: string;      // Response text (markdown)
  thoughts?: ThoughtEntry[];  // Structured reasoning (when enabled)
  tokens?: TokenInfo;   // Token usage
  model?: string;       // Model name (e.g., "gemini-2.5-flash", "gemini-3-pro-preview")
  toolCalls?: ToolCall[];  // Tool invocations (if any)
}

interface ThoughtEntry {
  subject: string;      // Brief topic (e.g., "Analyzing Code Revisions")
  description: string;  // Detailed reasoning text
  timestamp: string;    // ISO 8601 timestamp of thought
}

interface TokenInfo {
  input: number;        // Input tokens
  output: number;       // Output tokens (response)
  cached: number;       // Cached input tokens
  thoughts: number;     // Tokens used for reasoning (unique to Gemini)
  tool: number;         // Tokens for tool calls
  total: number;        // Total tokens
}
```

### Thoughts/Reasoning

When thinking mode is enabled, Gemini stores structured reasoning:

```json
{
  "type": "gemini",
  "content": "The code changes introduce a robust Visual Derivation layer...",
  "thoughts": [
    {
      "subject": "Analyzing Code Revisions",
      "description": "I'm currently focused on the requested code changes. Specifically, I'm reviewing the updates in `apps/server/src/encoding/index.ts`. The main point is to segregate imports and variables...",
      "timestamp": "2025-12-16T06:35:15.023Z"
    },
    {
      "subject": "Dissecting UI/API Changes",
      "description": "I'm now shifting my focus to the UI and API adjustments, specifically in `ArtEncode.vue` and `server.ts`. I'm examining the data flow...",
      "timestamp": "2025-12-16T06:35:17.893Z"
    },
    {
      "subject": "Evaluating Extensibility and Safety",
      "description": "I've been analyzing the overall architecture and changes. Specifically, I'm pleased to see the separation of semantic and visual encoding...",
      "timestamp": "2025-12-16T06:35:24.778Z"
    }
  ],
  "tokens": {
    "input": 22629,
    "output": 805,
    "cached": 0,
    "thoughts": 3174,
    "tool": 0,
    "total": 26608
  },
  "model": "gemini-3-pro-preview"
}
```

**Key characteristics**:
- `thoughts` is an array of structured entries with `subject`/`description`
- Each thought has its own `timestamp` (streaming thoughts)
- `tokens.thoughts` tracks reasoning token usage separately
- Contrast with Codex: Gemini uses structured objects, Codex uses freeform `agent_reasoning` text

### Example

```json
{
  "id": "a4cc7d17-6246-427c-955e-e4d3ebe9031b",
  "timestamp": "2025-11-30T10:29:00.015Z",
  "type": "gemini",
  "content": "这套架构设计文档非常完整且深思熟虑...",
  "thoughts": [],
  "tokens": {
    "input": 64754,
    "output": 509,
    "cached": 58371,
    "thoughts": 0,
    "tool": 0,
    "total": 65263
  },
  "model": "gemini-2.5-flash"
}
```

---

### 2.3 Type: `info`

System information messages, typically used for session markers like compression.

```typescript
interface InfoMessage {
  id: string;           // UUID v4
  timestamp: string;    // ISO 8601
  type: "info";
  content: string;      // Usually empty for compress markers
}
```

### Example (Compress Marker)

```json
{
  "id": "e8919ca1-96bd-4ad5-b7a9-83b53d628f9e",
  "timestamp": "2025-12-17T11:05:48.626Z",
  "type": "info",
  "content": ""
}
```

**Note**: An empty `info` message typically indicates a `/compress` command was executed. See Section 6 for compress behavior details.

---

## 3. Tool Calls (When Present)

When Gemini uses tools, they appear in the message:

```typescript
interface ToolCall {
  id: string;              // Tool call ID
  name: string;            // Tool name (e.g., "read_file")
  args: Record<string, any>;  // Tool arguments
  result?: ToolResult[];   // Tool execution results
  status: "success" | "error";
  timestamp: string;
  resultDisplay?: string;
  displayName?: string;
  description?: string;
  renderOutputAsMarkdown?: boolean;
}

interface ToolResult {
  functionResponse: {
    id: string;
    name: string;
    response: {
      output: string;
    };
  };
}
```

### Example: Read File Tool

```json
{
  "id": "read_file-1764498159498-0e5a70031e8128",
  "name": "read_file",
  "args": {
    "file_path": "mnema/state-architecture/refactor_02_transitions.md"
  },
  "result": [
    {
      "functionResponse": {
        "id": "read_file-1764498159498-0e5a70031e8128",
        "name": "read_file",
        "response": {
          "output": "# Step 2: 流转表 + PaneStateMachine..."
        }
      }
    }
  ],
  "status": "success",
  "timestamp": "2025-11-30T10:22:40.139Z",
  "displayName": "ReadFile",
  "description": "Reads and returns the content of a specified file..."
}
```

---

## 4. Quick Reference: Extracting Chat Messages

### Simple Extraction

```javascript
// Parse session file
const session = JSON.parse(fs.readFileSync(sessionPath));

// Extract messages
const chatHistory = session.messages.map(msg => ({
  role: msg.type === 'user' ? 'user' : 'assistant',
  content: msg.content,
  timestamp: msg.timestamp,
  tokens: msg.tokens?.total
}));
```

### Filter by Type

```javascript
// User messages only
const userMessages = session.messages
  .filter(m => m.type === 'user')
  .map(m => m.content);

// Gemini responses only
const geminiMessages = session.messages
  .filter(m => m.type === 'gemini')
  .map(m => ({ content: m.content, model: m.model }));
```

---

## 5. File Reference Pattern

User messages often contain expanded file references:

```
{original user text}
--- Content from referenced files ---
Content from @path/to/file1.md:
{file1 content}
Content from @path/to/file2.md:
{file2 content}
```

To extract original user text:
```javascript
const originalText = content.split('--- Content from referenced files ---')[0].trim();
```

---

## 6. Compress Behavior (`/compress`)

Unlike Claude and Codex which store compression summaries inline, Gemini uses a **session split** approach.

### 6.1 Compress Sequence

When the user executes `/compress`:

1. An empty `type: "info"` message is appended to the current session file
2. A **new session file** is created with:
   - **Same sessionId** as the original
   - **New startTime** (timestamp of the first message after compress)
   - **Fresh messages array** starting from post-compress conversation

### 6.2 Example

**Before compress** (`session-2025-12-16T06-34-cb7326d0.json`):
```json
{
  "sessionId": "cb7326d0-256b-4fa8-b19c-554d0d991cd7",
  "startTime": "2025-12-16T06:35:09.158Z",
  "lastUpdated": "2025-12-17T11:05:48.627Z",
  "messages": [
    // ... full conversation history ...
    { "type": "info", "content": "" }  // compress marker
  ]
}
```

**After compress** (`session-2025-12-17T11-05-cb7326d0.json`):
```json
{
  "sessionId": "cb7326d0-256b-4fa8-b19c-554d0d991cd7",
  "startTime": "2025-12-17T11:06:07.158Z",
  "messages": [
    // fresh conversation post-compress
  ]
}
```

### 6.3 Key Characteristics

| Aspect | Gemini | Claude | Codex |
|--------|--------|--------|-------|
| Summary stored | No (server-side only) | Yes (plaintext) | Yes (encrypted) |
| Marker type | `type: "info"` (empty) | `isCompactSummary: true` | `type: "compacted"` |
| Session continuity | New file (same sessionId) | Same file | Same file |
| Client visibility | No summary visible | Full summary visible | Encrypted summary |

### 6.4 Notes

- The high input token count in post-compress messages suggests Gemini handles context compression **server-side**
- No summary is exposed to the client; context is managed transparently by the Gemini API
- Session files are linked by matching `sessionId` values across the split

---

## 7. Comparison with Claude/Codex

| Field | Gemini | Claude | Codex |
|-------|--------|--------|-------|
| Session ID | `sessionId` | In each message | `session_meta.payload.id` |
| Message ID | `id` | `uuid` | varies |
| Timestamp | `timestamp` | `timestamp` | `timestamp` |
| User content | `content` | `message.content` | `payload.content[].text` |
| Assistant content | `content` | `message.content` | `payload.content[].text` |
| Token info | `tokens` | `message.usage` | `payload.info.total_token_usage` |
| Tool calls | Inline `toolCalls` | Separate `tool_use` | Separate `function_call` |

---

## Related Documentation

- [Gemini Session Files](./gemini-session-files.md) - File structure overview
- [Agent Files Analysis](./agent-files-analysis.md) - Cross-tool comparison
