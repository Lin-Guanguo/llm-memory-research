# Codex Session Files - Detailed Schema

Last Updated: 2025-12-17

## Overview

This document provides detailed JSON schema for Codex (OpenAI CLI) session files. Each line in the JSONL file is a JSON object with a `type` field determining its structure.

---

## 1. Common Structure

Every line has these top-level fields:

```typescript
interface CodexLogEntry {
  timestamp: string;  // ISO 8601 timestamp
  type: string;       // Entry type (see below)
  payload: object;    // Type-specific payload
}
```

---

## 2. Type: `session_meta`

First entry in every session file. Contains session initialization data.

### Schema

```typescript
interface SessionMeta {
  timestamp: string;
  type: "session_meta";
  payload: {
    id: string;           // Session UUID
    timestamp: string;    // Session start time
    cwd: string;          // Working directory
    originator: string;   // "codex_cli_rs"
    cli_version: string;  // e.g., "0.63.0"
    instructions: string; // AGENTS.md content
    source: string;       // "cli"
    model_provider: string; // "openai"
    git?: {
      commit_hash: string;
      branch: string;
      repository_url?: string;
    };
  };
}
```

### Example

```json
{
  "timestamp": "2025-12-02T04:00:28.175Z",
  "type": "session_meta",
  "payload": {
    "id": "019add38-07f3-7e93-ae71-3e0095eb0315",
    "timestamp": "2025-12-02T04:00:28.147Z",
    "cwd": "/Users/linguanguo/dev/prompt_platform",
    "originator": "codex_cli_rs",
    "cli_version": "0.63.0",
    "instructions": "# Development Guidelines...",
    "source": "cli",
    "model_provider": "openai",
    "git": {
      "commit_hash": "2d86aa5503313924ab40321d90549c4b81605f57",
      "branch": "solution-a"
    }
  }
}
```

---

## 3. Type: `response_item`

Contains response data including messages, tool calls, and reasoning.

### Subtypes (by `payload.type`)

| `payload.type` | Description |
|----------------|-------------|
| `message` | User or assistant message |
| `function_call` | Tool invocation |
| `function_call_output` | Tool result |
| `reasoning` | Model reasoning block |
| `ghost_snapshot` | Git snapshot info |

### 3.1 Message (`payload.type: "message"`)

```typescript
interface ResponseItemMessage {
  timestamp: string;
  type: "response_item";
  payload: {
    type: "message";
    role: "user" | "assistant";
    content: ContentBlock[];
  };
}

type ContentBlock =
  | { type: "input_text"; text: string }
  | { type: "output_text"; text: string };
```

### Example: User Message

```json
{
  "timestamp": "2025-12-02T04:02:19.697Z",
  "type": "response_item",
  "payload": {
    "type": "message",
    "role": "user",
    "content": [
      {
        "type": "input_text",
        "text": "帮我设计下方案"
      }
    ]
  }
}
```

### 3.2 Function Call (`payload.type: "function_call"`)

```typescript
interface ResponseItemFunctionCall {
  timestamp: string;
  type: "response_item";
  payload: {
    type: "function_call";
    name: string;        // Tool name (e.g., "shell_command")
    arguments: string;   // JSON string of arguments
    call_id: string;     // Unique call ID for matching output
  };
}
```

### Example: Shell Command

```json
{
  "timestamp": "2025-12-02T04:02:30.562Z",
  "type": "response_item",
  "payload": {
    "type": "function_call",
    "name": "shell_command",
    "arguments": "{\"command\":\"ls\",\"workdir\":\"/Users/linguanguo/dev/prompt_platform\"}",
    "call_id": "call_v9JdxLaqRWp7o9lruJFffASC"
  }
}
```

### 3.3 Function Call Output

```typescript
interface ResponseItemFunctionCallOutput {
  timestamp: string;
  type: "response_item";
  payload: {
    type: "function_call_output";
    call_id: string;   // Matches function_call.call_id
    output: string;    // Tool execution result
  };
}
```

### Example

```json
{
  "timestamp": "2025-12-02T04:02:30.562Z",
  "type": "response_item",
  "payload": {
    "type": "function_call_output",
    "call_id": "call_v9JdxLaqRWp7o9lruJFffASC",
    "output": "Exit code: 0\nWall time: 0 seconds\nOutput:\nAGENTS.md\nCLAUDE.md\n..."
  }
}
```

### 3.4 Reasoning

```typescript
interface ResponseItemReasoning {
  timestamp: string;
  type: "response_item";
  payload: {
    type: "reasoning";
    summary: Array<{ type: "summary_text"; text: string }>;
    content: null;
    encrypted_content: string;  // Encrypted reasoning details
  };
}
```

### 3.5 Ghost Snapshot

Git state snapshot for undo/revert.

```typescript
interface ResponseItemGhostSnapshot {
  timestamp: string;
  type: "response_item";
  payload: {
    type: "ghost_snapshot";
    ghost_commit: {
      id: string;                           // Ghost commit hash
      parent: string;                       // Parent commit hash
      preexisting_untracked_files: string[];
      preexisting_untracked_dirs: string[];
    };
  };
}
```

---

## 4. Type: `event_msg`

Event messages for various activities.

### Subtypes (by `payload.type`)

| `payload.type` | Description |
|----------------|-------------|
| `user_message` | User input event |
| `agent_message` | Agent response event |
| `agent_reasoning` | Reasoning summary |
| `token_count` | Token usage info |
| `turn_aborted` | Turn interruption |

### 4.1 User Message Event

```typescript
interface EventMsgUserMessage {
  timestamp: string;
  type: "event_msg";
  payload: {
    type: "user_message";
    message: string;
    images: string[];  // Image paths if any
  };
}
```

### 4.2 Agent Reasoning Event

```typescript
interface EventMsgAgentReasoning {
  timestamp: string;
  type: "event_msg";
  payload: {
    type: "agent_reasoning";
    text: string;  // Brief reasoning summary
  };
}
```

### 4.3 Token Count

Detailed token usage and rate limit tracking per response:

```typescript
interface EventMsgTokenCount {
  timestamp: string;
  type: "event_msg";
  payload: {
    type: "token_count";
    info: {
      total_token_usage: TokenUsage;
      last_token_usage: TokenUsage;
      model_context_window: number;
    } | null;
    rate_limits: RateLimits;
  };
}

interface TokenUsage {
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
  reasoning_output_tokens: number;
  total_tokens: number;
}

interface RateLimits {
  primary: {
    used_percent: number;      // 0.0 - 100.0
    window_minutes: number;    // e.g., 300 (5 hours)
    resets_at: number;         // Unix timestamp
  };
  secondary: {
    used_percent: number;
    window_minutes: number;    // e.g., 10080 (7 days)
    resets_at: number;
  };
  credits: {
    has_credits: boolean;
    unlimited: boolean;
    balance: number | null;
  };
  plan_type: string | null;
}
```

### Example: Token Count

```json
{
  "timestamp": "2025-12-17T07:50:42.053Z",
  "type": "event_msg",
  "payload": {
    "type": "token_count",
    "info": {
      "total_token_usage": {
        "input_tokens": 16293,
        "cached_input_tokens": 4480,
        "output_tokens": 368,
        "reasoning_output_tokens": 256,
        "total_tokens": 16661
      },
      "last_token_usage": {
        "input_tokens": 13863,
        "cached_input_tokens": 2432,
        "output_tokens": 302,
        "reasoning_output_tokens": 256,
        "total_tokens": 14165
      },
      "model_context_window": 258400
    },
    "rate_limits": {
      "primary": { "used_percent": 0.0, "window_minutes": 300, "resets_at": 1765975828 },
      "secondary": { "used_percent": 0.0, "window_minutes": 10080, "resets_at": 1766562628 },
      "credits": { "has_credits": false, "unlimited": false, "balance": null },
      "plan_type": null
    }
  }
}
```

### 4.4 Review Mode Events

Code review mode entry/exit events:

```typescript
interface EventMsgEnteredReviewMode {
  timestamp: string;
  type: "event_msg";
  payload: {
    type: "entered_review_mode";
    target: {
      type: "baseBranch";
      branch: string;           // e.g., "master"
    };
    user_facing_hint: string;   // e.g., "changes against 'master'"
  };
}

interface EventMsgExitedReviewMode {
  timestamp: string;
  type: "event_msg";
  payload: {
    type: "exited_review_mode";
    review_output: {
      findings: ReviewFinding[];
      overall_correctness: string;      // e.g., "patch is correct"
      overall_explanation: string;
      overall_confidence_score: number; // 0.0 - 1.0
    };
  };
}

interface ReviewFinding {
  file: string;
  line: number;
  severity: "error" | "warning" | "info";
  message: string;
}
```

### 4.5 Context Compacted Event

Marker indicating context compression occurred:

```typescript
interface EventMsgContextCompacted {
  timestamp: string;
  type: "event_msg";
  payload: {
    type: "context_compacted";
  };
}
```

---

## 5. Type: `turn_context`

Context for each conversation turn.

```typescript
interface TurnContext {
  timestamp: string;
  type: "turn_context";
  payload: {
    cwd: string;
    approval_policy: string;      // e.g., "on-request"
    sandbox_policy: {
      type: string;               // e.g., "workspace-write"
      network_access: boolean;
      exclude_tmpdir_env_var: boolean;
      exclude_slash_tmp: boolean;
    };
    model: string;                // e.g., "gpt-5.1-codex-max"
    effort: string;               // e.g., "xhigh"
    summary: string;              // e.g., "auto"
  };
}
```

---

## 6. Type: `compacted`

Context compaction entry. When context exceeds limits, Codex compacts the conversation history into a compressed form.

### Schema

```typescript
interface CompactedEntry {
  timestamp: string;
  type: "compacted";
  payload: {
    message: string;                    // Usually empty
    replacement_history: CompactedItem[];
  };
}

type CompactedItem =
  | CompactedMessage
  | CompactedCompaction
  | CompactedGhostSnapshot;

interface CompactedMessage {
  type: "message";
  role: "user";                         // Only user messages preserved
  content: ContentBlock[];
}

interface CompactedCompaction {
  type: "compaction";
  encrypted_content: string;            // Encrypted conversation summary
}

interface CompactedGhostSnapshot {
  type: "ghost_snapshot";
  ghost_commit: {
    id: string;
    parent: string;
    preexisting_untracked_files: string[];
    preexisting_untracked_dirs: string[];
  };
}
```

### Example

```json
{
  "timestamp": "2025-12-16T03:38:49.051Z",
  "type": "compacted",
  "payload": {
    "message": "",
    "replacement_history": [
      {
        "type": "message",
        "role": "user",
        "content": [{ "type": "input_text", "text": "..." }]
      },
      {
        "type": "compaction",
        "encrypted_content": "gAAAAABpQNRJ..."
      },
      {
        "type": "ghost_snapshot",
        "ghost_commit": {
          "id": "9aa94bf2...",
          "parent": "05aa7894...",
          "preexisting_untracked_files": ["docs/alg/visual_encode.v1.1.md"],
          "preexisting_untracked_dirs": []
        }
      }
    ]
  }
}
```

### Notes

- The `replacement_history` replaces previous conversation context
- User messages are preserved in plain text for continuity
- Assistant responses are encrypted in `compaction` entries
- Git snapshots are preserved for undo capability
- Associated event: `type: "event_msg"` with `payload.type: "context_compacted"`

---

## 7. History Index Schema (`history.jsonl`)

```typescript
interface HistoryEntry {
  session_id: string;  // UUID linking to session file
  ts: number;          // Unix timestamp
  text: string;        // User message text
}
```

---

## Quick Reference: Extracting Chat Messages

### User Messages

Filter by:
1. `type: "event_msg"` + `payload.type: "user_message"` → `payload.message`
2. `type: "response_item"` + `payload.type: "message"` + `payload.role: "user"` → `payload.content[].text`

### Assistant Messages

Filter by:
1. `type: "response_item"` + `payload.type: "message"` + `payload.role: "assistant"` → `payload.content[].text`

### Tool Calls

Filter by:
1. `type: "response_item"` + `payload.type: "function_call"` → `payload.name`, `payload.arguments`

### Tool Results

Filter by:
1. `type: "response_item"` + `payload.type: "function_call_output"` → `payload.output`

---

## Related Documentation

- [Codex Session Files](./codex-session-files.md) - File structure overview
- [Agent Files Analysis](./agent-files-analysis.md) - Cross-tool comparison
