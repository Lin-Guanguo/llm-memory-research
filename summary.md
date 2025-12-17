# LLM Memory Systems: A Reverse Engineering Study

## Overview

This document summarizes findings from reverse-engineering how major AI systems implement memory - both consumer products (ChatGPT, Claude), developer tools (Claude Code, Codex CLI, Gemini CLI), and open source memory frameworks (mem0, Letta).

---

## Part 1: Consumer AI Memory (ChatGPT vs Claude)

Based on reverse-engineering by [Manthan Gupta](https://manthanguptaa.in/).

### ChatGPT Memory Architecture

Four-layer context structure:
1. **Session Metadata** - Device, location, usage patterns (ephemeral)
2. **User Memory** - Explicit facts stored long-term (33 facts in example)
3. **Recent Conversations Summary** - Lightweight digest of past chats (titles + snippets)
4. **Current Session** - Sliding window of full messages

Key insight: **No vector database, no RAG**. Pre-computed summaries injected directly.

### Claude Memory Architecture

Tool-based selective retrieval:
1. **System Prompt** - Static instructions
2. **User Memories** - Long-term facts in XML format
3. **Conversation History** - Rolling window + on-demand tools
4. **Current Message**

Key tools:
- `conversation_search` - Semantic search past conversations
- `recent_chats` - Time-based retrieval
- `memory_user_edits` - Explicit memory management

### Philosophy Comparison

| Aspect | ChatGPT | Claude |
|--------|---------|--------|
| History Retrieval | Pre-computed summaries (always injected) | On-demand tools (selective) |
| Trade-off | Automatic continuity | On-demand depth |
| Efficiency | Fixed token cost | Variable (only when needed) |

---

## Part 2: AI Coding CLI Memory

Reverse-engineered local storage of Claude Code, Codex (OpenAI), and Gemini CLI.

### Storage Comparison

| Tool | Location | Format | Message Types |
|------|----------|--------|---------------|
| Claude Code | `~/.claude/projects/` | JSONL | ~6 |
| Codex | `~/.codex/sessions/` | JSONL | 10+ |
| Gemini | `~/.gemini/tmp/` | JSON | 3 |

### Context Compression Strategies

| Tool | Method | Visibility |
|------|--------|------------|
| **Claude** | Plaintext summary in same file | Fully readable |
| **Codex** | Encrypted JWT in same file | Opaque |
| **Gemini** | New file, server-side storage | Not stored locally |

### Unique Strengths

**Claude Code**: Most comprehensive local data
- Usage analytics, plugin system, planning mode, file history, IDE integration

**Codex**: Most detailed logging
- Encrypted compression, ghost snapshots, rate limit tracking, agent reasoning

**Gemini**: Simplest architecture
- Single JSON per session, structured thinking, easiest to parse

### Design Philosophy

| Aspect | Claude | Codex | Gemini |
|--------|--------|-------|--------|
| Transparency | High | Low | None |
| Server Dependency | Low | High | High |
| Debuggability | Easy | Hard | Medium |

---

## Part 3: Open Source Memory Frameworks

### mem0

TODO

### Letta (MemGPT)

TODO

---

## Key Takeaways

1. **No complex RAG in production**: Both ChatGPT and Claude use simpler approaches than expected - pre-computed summaries or selective tool calls.

2. **Transparency vs Privacy trade-off**: Claude favors transparency (readable summaries), Codex/Gemini favor privacy (encrypted or server-side).

3. **Tool-based memory is flexible**: Claude's approach of using tools (`conversation_search`) for retrieval allows dynamic context loading without fixed overhead.

4. **Local storage varies widely**: From Gemini's minimal 3-type JSON to Codex's 10+ event types, complexity reflects different priorities.

5. **Memory management is mostly explicit**: All systems rely heavily on explicit user commands ("remember this") rather than fully autonomous memory extraction.

---

## References

- [ChatGPT Memory Reverse Engineering](https://manthanguptaa.in/posts/chatgpt_memory/) - Manthan Gupta
- [Claude Memory Reverse Engineering](https://manthanguptaa.in/posts/claude_memory/) - Manthan Gupta
- [mem0](https://github.com/mem0ai/mem0) - Memory layer for personalized AI
- [Letta](https://github.com/letta-ai/letta) - LLM agents with self-managing memory
