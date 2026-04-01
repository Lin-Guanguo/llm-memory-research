# Claude Code Agent Swarm Architecture (Source Code Analysis)

Last Updated: 2026-03-31

Sources:
- Claude Code v2.1.88 source map leak (submodule: `claude-code-sourcemap/`)
- Key files: `utils/swarm/`, `utils/teammateMailbox.ts`, `hooks/useInboxPoller.ts`, `tools/SendMessageTool/`, `tools/TeamCreateTool/`

Research focus: Multi-agent collaboration architecture — how Claude Code implements agent-to-agent communication, task coordination, and permission synchronization in its Agent Swarm system.

---

## 1. Architecture Overview

Agent Swarm is a multi-agent collaboration system where a **leader** agent coordinates multiple **teammate** agents working in parallel. Each agent is a full Claude Code instance with its own context, tools, and (optionally) memory.

```
┌─────────────────────────────────────────────────┐
│                    Leader Agent                   │
│  (user interacts here, delegates work)           │
│                                                   │
│  Tools: TeamCreate, SendMessage, TaskCreate/      │
│         TaskUpdate, TaskList, Agent               │
└──────────┬──────────┬──────────┬────────────────┘
           │          │          │
      ┌────▼───┐ ┌────▼───┐ ┌───▼────┐
      │Worker A│ │Worker B│ │Worker C│
      │(tmux)  │ │(iTerm) │ │(in-proc)│
      └────────┘ └────────┘ └────────┘
           ↕          ↕          ↕
    File Mailbox  File Mailbox  Memory Direct
```

## 2. Execution Backends

Three backends for running teammate agents:

| Backend | How it runs | Communication | Process model |
|---------|------------|---------------|---------------|
| **tmux** | Separate Claude Code process per tmux pane | File-based mailbox | Multi-process |
| **iTerm2** | Separate process per iTerm2 split pane | File-based mailbox | Multi-process |
| **in-process** | Same Node.js process, AsyncLocalStorage isolation | Memory direct (shared AppState) | Single-process, concurrent |

Backend selection is automatic based on environment detection. In-process is the newest and avoids the overhead of spawning separate processes.

## 3. File-Based Mailbox System

### 3.1 Storage

```
~/.claude/teams/{team_name}/inboxes/
├── team-lead.json       # Leader's inbox
├── researcher.json      # Worker "researcher"'s inbox
└── tester.json          # Worker "tester"'s inbox
```

Each file is a JSON array of messages:

```json
[
  {
    "from": "team-lead",
    "text": "Investigate the login bug",
    "timestamp": "2026-03-31T10:00:00Z",
    "read": false,
    "color": "blue",
    "summary": "investigate login bug"
  }
]
```

### 3.2 Write Path

`writeToMailbox()` in `teammateMailbox.ts`:
1. Ensure inbox directory exists
2. Acquire file lock (`proper-lockfile`, retry 10 times, 5-100ms exponential backoff)
3. Read current inbox JSON
4. Append new message with `read: false`
5. Write back to file
6. Release lock

File locking is necessary because multiple agent processes may write to the same inbox concurrently.

### 3.3 Read Path — Polling

`useInboxPoller` React hook in `hooks/useInboxPoller.ts`:

```typescript
const INBOX_POLL_INTERVAL_MS = 1000
useInterval(() => void poll(), shouldPoll ? INBOX_POLL_INTERVAL_MS : null)
```

Every 1 second, each agent reads its own inbox file, filters for `read === false` messages, processes them by type, then marks as read. No file watcher, no IPC, no push — pure polling.

**In-process teammates** do NOT use the inbox poller. They use `waitForNextPromptOrShutdown()` which receives prompts directly via shared AppState. However, they still use the file mailbox for sending messages to the leader (for UI consistency).

## 4. Message Types

The mailbox carries **8+ structured message types**, not just chat:

| Message Type | Direction | Purpose |
|---|---|---|
| Regular text | Bidirectional | Agent-to-agent conversation / results |
| `permission_request` | Worker → Leader | "I need to run `rm -rf`, please approve" |
| `permission_response` | Leader → Worker | "Approved / Denied" |
| `sandbox_permission_request` | Worker → Leader | "I need network access to github.com" |
| `sandbox_permission_response` | Leader → Worker | "Allowed / Denied" |
| `plan_approval_request` | Worker → Leader | "Here's my plan, please review" |
| `plan_approval_response` | Leader → Worker | "Plan approved, proceed" |
| `shutdown_request` | Leader → Worker | "Please shut down" |
| `shutdown_approved` | Worker → Leader | "Shut down complete, here's my paneId for cleanup" |
| `team_permission_update` | Leader → Workers | "Global permission change, sync your context" |
| `mode_set_request` | Leader → Worker | "Switch to acceptEdits mode" |
| `idle_notification` | Worker → Leader | "I'm done with my current task" (auto-sent by system) |

Message type identification is done by parsing the JSON text field — each type has a `type` field in the JSON payload, detected by functions like `isPermissionRequest()`, `isShutdownApproved()`, etc.

## 5. Message Delivery Semantics

### 5.1 Idle vs Busy

When the inbox poller finds messages:

```
Recipient is idle (no active query):
  → Format as <teammate-message> XML
  → Submit immediately as new user turn
  → Model starts processing right away

Recipient is busy (mid-turn, tool execution):
  → Queue in AppState.inbox.messages (status: 'pending')
  → When current turn ends, deliver queued messages as new user turn
  → Prevents mid-turn interruption
```

### 5.2 Message Format to Model

Regular messages are wrapped in XML before submission as a user message:

```xml
<teammate-message teammate_id="researcher" color="blue" summary="found the bug">
Here is the investigation result: the login bug is caused by...
</teammate-message>
```

This is submitted as a regular user turn — from the model's perspective, it's indistinguishable from a user typing a message. The XML wrapper gives context about who sent it.

### 5.3 Mark-As-Read After Delivery

Messages are marked read **only after** successful delivery or reliable queuing in AppState. If the process crashes between poll and mark, messages will be re-delivered on next poll. This prevents message loss at the cost of potential duplicate delivery.

## 6. Result Passing: Dual-Path Design

A common concern: what if a worker finishes a task but forgets to send results?

**Path 1: Model actively sends via SendMessage**

The system prompt tells each teammate: "Your plain text output is NOT visible to other agents — to communicate, you MUST call this tool."

Workers should use `SendMessage` to report results. Content can be arbitrarily long.

**Path 2: System auto-sends idle notification (fallback)**

When a teammate's query loop ends (model returns `end_turn`), the system **automatically**:
1. Marks the task as idle
2. Sends an `idle_notification` to the leader's mailbox with metadata:
   - `idleReason`: 'available' | 'interrupted' | 'failed'
   - `summary`: Brief description
   - `completedTaskId`: Which task was completed
   - `completedStatus`: 'resolved' | 'blocked' | 'failed'
   - `failureReason`: If failed
3. Enters `waitForNextPromptOrShutdown()` — waits for new instructions

This is a **system-level guarantee** — regardless of whether the model remembered to send a message, the leader always knows when a worker finishes.

The prompt explicitly states:
> "Teammates go idle between turns — after each turn, teammates automatically go idle and send a notification."

## 7. Task Coordination

Swarm uses a shared task list (not mailbox) for work coordination:

```
Leader creates tasks → TaskCreate
Workers check for tasks → TaskList
Workers claim tasks → TaskUpdate (set owner)
Workers mark done → TaskUpdate (set completed)
```

Prompt guidance for workers:
1. Check TaskList periodically, **especially after completing each task**
2. Claim unassigned, unblocked tasks (prefer lowest ID first)
3. Mark tasks completed, then check for next work
4. If all tasks blocked, notify leader

This means the task list acts as a **shared work queue**, while the mailbox handles communication and control signals.

## 8. Permission Centralization

All permission prompts from workers are **forwarded to the leader's terminal**:

```
Worker encounters permission-gated tool call
  → Worker writes permission_request to Leader's mailbox
  → Worker starts polling own mailbox for response
  → Leader's inbox poller detects request
  → Leader's UI shows tool-specific permission dialog to user
  → User approves/denies
  → Leader writes permission_response to Worker's mailbox
  → Worker receives response, continues or aborts
```

This means the user only interacts with **one terminal** (the leader's), even though multiple agents are running. Workers never prompt the user directly.

The leader can also **broadcast permission updates** — if the user approves "always allow Bash in /src/", the leader sends `team_permission_update` to all workers so they don't ask again.

## 9. Comparison with DIY tmux Approach

| Aspect | DIY tmux sendkeys | Native Agent Swarm |
|---|---|---|
| Communication channel | Terminal stdin (sendkeys) | File-based mailbox (JSON + file lock) |
| Message format | Unstructured text (simulated typing) | Structured JSON (from, text, read, summary, type) |
| Result retrieval | Read terminal output directly | Mailbox messages + idle notifications |
| Permission handling | Each pane independent | Centralized to leader |
| Delivery guarantee | None (fire and forget) | Mark-as-read after delivery; re-poll on crash |
| Idle detection | Manual (check terminal output) | Automatic idle notification from system |
| Process lifecycle | Manual spawn/kill | Automatic spawn/terminate/kill + reconnection |
| In-process option | Not possible | Supported (AsyncLocalStorage isolation) |

Key difference: DIY approach works at the **terminal I/O layer** (parsing rendered UI text), while native swarm works at the **application layer** (structured messages, typed protocols). The application layer is more reliable but requires framework support.

## 10. Prompt Engineering for Swarm

The system prompt has specific additions for swarm mode:

**Teammate addendum** (`TEAMMATE_SYSTEM_PROMPT_ADDENDUM`):
```
You are running as an agent in a team. To communicate with anyone:
- Use SendMessage with to: "<name>" for specific teammates
- Use SendMessage with to: "*" sparingly for broadcasts
Just writing a response in text is NOT visible to others — you MUST use SendMessage.
```

**Anti-patterns explicitly forbidden**:
- "Do not use terminal tools to view your team's activity" — prevents tmux output scraping
- "Do NOT send structured JSON status messages" — use TaskUpdate instead
- "Don't originate shutdown_request unless asked"

**Task protocol**:
- Workers claim tasks by setting `owner` via TaskUpdate
- Prefer tasks in ID order (earlier tasks set up context for later ones)
- Check TaskList after completing each task
- If all tasks blocked, notify leader

## 11. Key Architectural Insights

1. **Mailbox as universal bus**: A single file-based mailbox system carries all inter-agent communication — chat, permissions, lifecycle control, mode changes. Simple implementation (JSON files + file locks), complex protocol built on top.

2. **System-level idle guarantee**: The "forgetting to report" problem is solved at the system level, not the prompt level. The query loop exit always triggers `sendIdleNotification()`, regardless of what the model did or didn't do.

3. **Centralized permission model**: Having all permission prompts flow to one terminal is a UX decision — the user doesn't need to switch between terminals to approve things. This also enables global permission broadcasting.

4. **Task list as coordination layer**: The mailbox handles communication, but the task list handles **coordination** (what needs doing, who's doing it, what's blocked). These are separate systems with separate concerns.

5. **Three backends, one protocol**: Whether running in tmux, iTerm2, or in-process, the communication protocol (mailbox + task list) is identical. Only the process spawning and terminal rendering differ.
