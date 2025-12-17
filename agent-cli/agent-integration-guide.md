# AI Agent CLI Integration Guide

Last Updated: 2025-12-08

## Overview

This document covers programmatic integration options for three AI coding assistants: **Claude Code**, **Codex (OpenAI)**, and **Gemini CLI**. Including SDK, non-interactive CLI, and CI/CD integration.

---

## Quick Comparison

| Feature | Claude Code | Codex | Gemini |
|---------|-------------|-------|--------|
| **SDK** | ✅ TypeScript/Python | ✅ TypeScript | ❌ None |
| **Non-interactive CLI** | ✅ `-p` | ✅ `codex exec` | ✅ `-p` |
| **JSON output** | ✅ `--output-format json` | ✅ `--json` | ✅ `--output-format json` |
| **Stdin pipe** | ✅ | ✅ | ✅ |
| **GitHub Action** | ❌ | ✅ Official | ❌ |
| **Session resume** | ✅ `--resume` | ✅ `resume` | ❌ |

---

## 1. Claude Code

### SDK: `@anthropic-ai/claude-agent-sdk`

**Install**:
```bash
npm install @anthropic-ai/claude-agent-sdk
# or
pip install claude-agent-sdk
```

**Basic Usage** (TypeScript):
```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

const result = await query({
  prompt: "Analyze this codebase",
  options: {
    cwd: "/path/to/project",
    model: "sonnet",
    permissionMode: "bypassPermissions"
  }
});

for await (const message of result) {
  console.log(message);
}
```

**Features**:
- Full Claude Code capabilities
- Plugin support
- CLAUDE.md memory files
- MCP server integration
- Multi-provider auth (Anthropic, Bedrock, Vertex)

### Non-Interactive CLI (`-p`)

```bash
# Basic usage
claude -p "How many files are in this project?"

# With JSON output
claude -p "Summarize this code" --output-format stream-json

# Pipe input
cat file.txt | claude -p "summarize this"

# With tool restrictions
claude -p "Stage and commit changes" --allowedTools "Bash,Read"

# Full auto mode (skip permissions)
claude -p "Fix the bug" --dangerously-skip-permissions
```

**Sources**:
- [Claude Agent SDK npm](https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk)
- [Claude Agent SDK Docs](https://docs.claude.com/en/api/agent-sdk/overview)
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless)
- [Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)

---

## 2. Codex (OpenAI)

### SDK: `@openai/codex-sdk`

**Install**:
```bash
npm install @openai/codex-sdk
```

**Basic Usage**:
```typescript
import { Codex } from "@openai/codex-sdk";

const codex = new Codex();
const thread = codex.startThread();
const turn = await thread.run("Diagnose the test failure and propose a fix");

console.log(turn.finalResponse);
console.log(turn.items);
```

**Streaming Events**:
```typescript
const { events } = await thread.runStreamed("Fix the issue");

for await (const event of events) {
  switch (event.type) {
    case "item.completed":
      console.log("item", event.item);
      break;
    case "turn.completed":
      console.log("usage", event.usage);
      break;
  }
}
```

**Structured Output (JSON Schema)**:
```typescript
const schema = {
  type: "object",
  properties: {
    summary: { type: "string" },
    status: { type: "string", enum: ["ok", "action_required"] },
  },
  required: ["summary", "status"],
  additionalProperties: false,
} as const;

const turn = await thread.run("Summarize repo status", { outputSchema: schema });
```

**Resume Thread**:
```typescript
const thread = codex.resumeThread(savedThreadId);
await thread.run("Continue the fix");
```

### Non-Interactive CLI (`codex exec`)

```bash
# Basic usage
codex exec "your task"

# JSON output
codex exec --json "your task"

# Full auto mode (allow edits)
codex exec --full-auto "your task"

# Dangerous mode (network + edits)
codex exec --sandbox danger-full-access "your task"

# Resume last session
codex exec resume --last

# Resume specific session
codex exec resume <SESSION_ID>

# API key override
CODEX_API_KEY=your-key codex exec --json "task"
```

### GitHub Action

```yaml
# .github/workflows/codex-autofix.yml
name: Codex Auto-Fix
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  autofix:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: openai/codex-action@v1
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          prompt: "Fix the CI failure"
          safety-strategy: drop-sudo
```

**Sources**:
- [Codex SDK Docs](https://developers.openai.com/codex/sdk/)
- [Codex SDK npm](https://www.npmjs.com/package/@openai/codex-sdk)
- [Codex SDK GitHub](https://github.com/openai/codex/tree/main/sdk/typescript)
- [Codex GitHub Action](https://github.com/openai/codex-action)
- [Auto-fix CI with Codex](https://developers.openai.com/codex/guides/autofix-ci/)
- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference)

---

## 3. Gemini CLI

### No SDK Available

Currently no official SDK. There's a [feature request](https://github.com/google-gemini/gemini-cli/issues/2023) for TypeScript SDK support.

### Non-Interactive CLI (`-p`)

```bash
# Basic usage
gemini -p "your prompt"
# or
gemini "your prompt"

# JSON output
gemini -p "prompt" --output-format json

# Streaming JSON
gemini -p "prompt" --output-format stream-json

# Pipe input
cat src/auth.py | gemini -p "Review for security issues"
echo "Count to 10" | gemini

# YOLO mode (no confirmations)
gemini -p "task" --yolo
# or
gemini -y "task"

# Commit message from diff
git diff --cached | gemini -p "Write commit message" --output-format json
```

### CI/CD Integration

```yaml
# GitLab CI example
code_review:
  image: node:20
  script:
    - npm install -g @anthropic-ai/gemini-cli
    - gemini -p "Review changed files" --yolo --output-format json > review.json
  artifacts:
    paths:
      - review.json
```

**Key Flags**:
- `-p, --prompt`: Non-interactive mode
- `-y, --yolo`: Skip all confirmations
- `--output-format json`: JSON output
- `--output-format stream-json`: Real-time JSONL events
- `--allowed-tools`: Restrict available tools

**Sources**:
- [Gemini CLI Headless Mode](https://geminicli.com/docs/cli/headless/)
- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli)
- [Gemini CLI Tips](https://github.com/addyosmani/gemini-cli-tips)
- [Gemini CLI SDK Request](https://github.com/google-gemini/gemini-cli/issues/2023)

---

## Integration Recommendations

### By Use Case

| Use Case | Claude | Codex | Gemini |
|----------|--------|-------|--------|
| **Web UI backend** | Agent SDK | TypeScript SDK | CLI `-p` |
| **CI/CD automation** | CLI `-p` | GitHub Action | CLI `-p --yolo` |
| **Scripting** | CLI `-p` | `codex exec` | CLI `-p` |
| **IDE extension** | Agent SDK | JSON-RPC Server | CLI |

### By Complexity

| Complexity | Recommendation |
|------------|----------------|
| **Simple scripting** | All three CLI `-p` modes work well |
| **Full integration** | Claude Agent SDK or Codex SDK |
| **CI/CD** | Codex GitHub Action (best), others use CLI |

---

## Authentication Summary

| Agent | Auth Method |
|-------|-------------|
| **Claude** | `ANTHROPIC_API_KEY` env var |
| **Codex** | `OPENAI_API_KEY` or `CODEX_API_KEY` env var |
| **Gemini** | Google account OAuth or API key |

---

## Related Documentation

- [Agent Files Analysis](./agent-files-analysis.md) - Session file comparison
- [Claude Session Files](./claude-session-files.md)
- [Codex Session Files](./codex-session-files.md)
- [Gemini Session Files](./gemini-session-files.md)
