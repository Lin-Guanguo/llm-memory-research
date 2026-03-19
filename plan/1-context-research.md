# Context Research Plan

Last Updated: 2026-03-19

## Goal

Research how mainstream agents assemble and manage context within a conversation:
1. How tokens are generated and streamed
2. How context (system prompt, messages, tool results) is stitched together before each LLM call
3. How different agents handle token budget, compaction, and truncation

## Research Targets

### Open Source (clone as submodule)

| Project | Repo | Focus |
|---------|------|-------|
| Pi | `badlogic/pi-mono` | Minimal agent loop, compaction strategy, session tree (JSONL), ~300 word system prompt |
| OpenClaw | `openclaw/openclaw` | Pluggable ContextEngine (v2026.3.7), assemble() interface, token budget allocation, system prompt construction |
| Gemini CLI | `google-gemini/gemini-cli` | Fully open source, Google's context management approach |

### Reverse Engineering (local installation)

| Product | Source Location | Focus |
|---------|----------------|-------|
| Claude Code | npm global package (JS, possibly minified) | System prompt construction, context window management, compaction logic |
| Codex | npm global package (JS, possibly minified) | Same as above, compare with Claude Code's approach |

### Existing Assets

- `agent-cli/` directory already has session file analysis from memory research — shows WHAT was sent but not HOW context was assembled
- Session files = conversation history (messages, tool calls, results)
- Context assembly logic (prompt building, token budgeting, message selection) is in code, not session files

## Steps

- [ ] Clone 3 open source repos as submodules
- [ ] Study Pi: core agent loop and context compaction
- [ ] Study OpenClaw: ContextEngine plugin architecture and assemble() flow
- [ ] Study Gemini CLI: context management implementation
- [ ] Reverse engineer Claude Code: locate and analyze context assembly code
- [ ] Reverse engineer Codex: locate and analyze context assembly code
- [ ] Write per-project research documents (*.research.md)
- [ ] Cross-project comparison and summary
