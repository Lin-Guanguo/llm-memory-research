# Context Research Plan

Last Updated: 2026-03-23

## Goal

Research how mainstream agents assemble and manage context within a conversation:
1. How tokens are generated and streamed
2. How context (system prompt, messages, tool results) is stitched together before each LLM call
3. How different agents handle token budget, compaction, and truncation

## Completed

- [x] Clone open source repos as submodules (Pi, OpenClaw, Gemini CLI, Codex, OpenCode, claude-code-system-prompts)
- [x] Study Pi: core agent loop and context compaction → `pi.research.md`
- [x] Study OpenClaw: ContextEngine plugin architecture and assemble() flow → `openclaw.research.md`
- [x] Study Gemini CLI: context management implementation → `gemini-cli.research.md`
- [x] Study Claude Code: system prompts, compaction, sub-agents (via community extraction) → `claude-code-context.research.md`
- [x] Study Codex: dual compaction, context manager (open source, Rust) → `codex-context.research.md`
- [x] Study OpenCode: two-phase compaction, fork/revert, resumable sub-agents → `opencode.research.md`
- [x] Write per-project research documents (7 total)
- [x] Cross-project comparison → `context.summary.md`
- [x] Cross-domain findings (Memory × Context) → `findings.md`

## Open Areas

### Discussed but not deeply researched

| Topic | Status | Notes |
|-------|--------|-------|
| Token streaming mechanics | Mentioned in goal #1, not studied | How each agent handles SSE/WebSocket/stdio streaming. Lower priority — this is transport, not context management |
| Anthropic "Effective Context Engineering" article | Read and referenced | Could do detailed breakdown: official recommendations vs what agents actually implement |
| Prompt placement empirics | Identified as gap in findings | No agent does A/B testing. AI Muse 18-model benchmark is the closest. Would need own experiments to go further |
| Knowledge graphs for context | Identified as gap in findings | Graphiti is Memory-side only. No one applies graph structures to context management |
| Compaction quality measurement | Identified as unsolved problem | No standard metric exists. Could survey academic work on summarization evaluation |

### Not yet started

| Topic | Priority | Notes |
|-------|----------|-------|
| **Learning** (continual learning) | TODO | New research direction. Focus on academic survey + any production systems doing user-level adaptation. See CLAUDE.md |
| Cross-domain article | Future | Synthesis article covering Memory × Context × Learning findings. Not urgent — deepen understanding first |
