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

**Core Innovation:** Active memory management via LLM-driven fact extraction and conflict resolution.

**Architecture:**
- **Two-Stage LLM Pipeline**: Extract facts → Compare with existing → Decide ADD/UPDATE/DELETE
- **Dual Storage**: Vector store (semantic search) + Graph store (relationships) in parallel
- **Session Scoping**: `user_id`, `agent_id`, `run_id` for multi-tenant isolation

**Key Differentiators from RAG:**
| Aspect | Traditional RAG | mem0 |
|--------|----------------|------|
| Storage Unit | Document chunks | Atomic facts |
| Updates | Append-only | Active CRUD |
| Deduplication | Vector distance | LLM reasoning |

**Ecosystem:**
- 24+ vector stores (Qdrant, Pinecone, PGVector, FAISS, etc.)
- 20+ LLMs (OpenAI, Anthropic, Gemini, Ollama, etc.)
- Graph support via Neo4j, Memgraph, Neptune

**Detailed analysis:** [mem0.research.md](mem0.research.md)

### Letta (MemGPT)

**Core Innovation:** LLM Operating System with self-editing memory and virtual context management.

**Architecture:**
- **Three-Tier Memory**: Core (always in-context) → Recall (searchable history) → Archival (vector storage)
- **Self-Editing**: Agent writes to its own prompt via tools (`core_memory_replace`, `archival_memory_insert`)
- **Virtual Context**: Summarization + paging creates illusion of infinite context window

**Key Differentiators from RAG:**
| Aspect | Standard RAG | Letta |
|--------|--------------|-------|
| Retrieval | Passive (before LLM) | Active (LLM decides when) |
| Memory | Read-only | Read/Write (self-editing) |
| State | Stateless | Stateful (persistent identity) |

**Agent Types:**
- `memgpt_agent` - Original MemGPT implementation
- `letta_v1_agent` - Simplified, no forced tool calls
- `sleeptime_agent` - Background memory management

**Detailed analysis:** [letta.research.md](letta.research.md)

---

## Key Takeaways

1. **No complex RAG in production**: Both ChatGPT and Claude use simpler approaches than expected - pre-computed summaries or selective tool calls.

2. **Transparency vs Privacy trade-off**: Claude favors transparency (readable summaries), Codex/Gemini favor privacy (encrypted or server-side).

3. **Tool-based memory is flexible**: Claude's approach of using tools (`conversation_search`) for retrieval allows dynamic context loading without fixed overhead.

4. **Local storage varies widely**: From Gemini's minimal 3-type JSON to Codex's 10+ event types, complexity reflects different priorities.

5. **Memory management is mostly explicit**: All systems rely heavily on explicit user commands ("remember this") rather than fully autonomous memory extraction.

6. **Open-source frameworks differ fundamentally**: mem0 focuses on LLM-driven fact extraction with dual storage (vector + graph), while Letta implements OS-inspired virtual memory with self-editing capabilities.

---

## References

- [ChatGPT Memory Reverse Engineering](https://manthanguptaa.in/posts/chatgpt_memory/) - Manthan Gupta
- [Claude Memory Reverse Engineering](https://manthanguptaa.in/posts/claude_memory/) - Manthan Gupta
- [mem0](https://github.com/mem0ai/mem0) - Memory layer for personalized AI
- [Letta](https://github.com/letta-ai/letta) - LLM agents with self-managing memory
