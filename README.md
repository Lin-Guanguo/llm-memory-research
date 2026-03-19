# LLM Agent Research

Last Updated: 2026-03-19

A systematic research project studying LLM agent internals: memory implementations and context management across frameworks, products, and agent CLI tools.

---

## Research Directions

1. **Memory** — How agents persist and retrieve knowledge across conversations
2. **Context** — How agents assemble and manage context within a conversation (token generation, prompt stitching, token budgeting)

---

## Repository Structure

```
llm-agent-research/
├── plan/                                    # Research plans
│   └── 1-context-research.md                # Context research plan & steps
│
├── Memory Research (*.research.md)
│   ├── production-adoption.research.md      # Production deployment cases
│   ├── ecosystem.md                         # Market analysis & priorities
│   ├── summary.md                           # Reverse-engineering findings
│   ├── mem0.research.md                     # Mem0: LLM-driven CRUD memory
│   ├── letta.research.md                    # Letta: Three-tier self-editing memory
│   ├── graphiti.research.md                 # Graphiti: Bi-temporal knowledge graph
│   ├── qdrant.research.md                   # Qdrant: Filtrable HNSW vector DB
│   ├── chroma.research.md                   # Chroma: Developer-friendly vector DB
│   ├── continue.research.md                 # Continue: Open-source coding assistant
│   ├── cursor.research.md                   # Cursor: Custom embedding training
│   └── augmentcode.research.md              # Augment: Real-time personal index
│
├── Context Research
│   ├── pi.research.md                        # Pi: Minimal agent loop & compaction
│   ├── openclaw.research.md                  # OpenClaw: Pluggable ContextEngine
│   ├── gemini-cli.research.md                # Gemini CLI: Context management (open source)
│   ├── (TBD) claude-code-context.research.md  # Claude Code: Reverse engineering
│   └── (TBD) codex-context.research.md      # Codex: Reverse engineering
│
├── reverse-engineer/                        # Product reverse-engineering
│   ├── chatgpt-memory-reverse-engineering.md
│   └── claude-memory-reverse-engineering.md
│
├── agent-cli/                               # Agent CLI session file analysis
│   ├── agent-files-analysis.md              # Cross-tool comparison
│   ├── claude-session-files.md              # Claude Code session structure
│   ├── codex-session-files.md               # Codex session structure
│   ├── gemini-session-files.md              # Gemini CLI session structure
│   └── *-session-file-schema.md             # Detailed JSON schemas
│
├── Git Submodules (Source Code)
│   ├── mem0/                                # github.com/mem0ai/mem0
│   ├── letta/                               # github.com/letta-ai/letta
│   ├── graphiti/                            # github.com/getzep/graphiti
│   ├── continue/                            # github.com/continuedev/continue
│   ├── pi-mono/                              # github.com/badlogic/pi-mono
│   ├── openclaw/                             # github.com/openclaw/openclaw
│   └── gemini-cli/                           # github.com/google-gemini/gemini-cli
│
├── blog.chinese.md                          # Chinese blog post
└── demos/                                   # Experimental implementations
    └── knowledge-base/                      # ChromaDB vector search demo
```

---

## Memory Research Index

### Summary & Analysis

| File | Content |
|------|---------|
| `production-adoption.research.md` | Real-world adoption: Mem0 (AWS SDK), Letta (11x, Kognitos), Graphiti (Zep AI) |
| `ecosystem.md` | GitHub stars, funding data, market segmentation, research priorities |
| `summary.md` | Consolidated findings from reverse-engineering and open-source analysis |

### Memory Frameworks

| File | Project | Key Innovation |
|------|---------|----------------|
| `mem0.research.md` | [Mem0](https://github.com/mem0ai/mem0) | LLM-driven fact extraction + conflict resolution + ADD/UPDATE/DELETE |
| `letta.research.md` | [Letta](https://github.com/letta-ai/letta) | Three-tier memory (Core/Recall/Archival) + agent self-editing prompts |
| `graphiti.research.md` | [Graphiti](https://github.com/getzep/graphiti) | Bi-temporal knowledge graph (valid_time + transaction_time) |

### Vector Databases

| File | Project | Key Innovation |
|------|---------|----------------|
| `qdrant.research.md` | [Qdrant](https://github.com/qdrant/qdrant) | Filtrable HNSW + sparse vectors + RRF/DBSF hybrid search |
| `chroma.research.md` | [Chroma](https://github.com/chroma-core/chroma) | Pre-filtering + Rust v1.0 rewrite + developer experience focus |

### Coding Assistants

| File | Project | Key Innovation |
|------|---------|----------------|
| `cursor.research.md` | [Cursor](https://cursor.com) | Custom embeddings trained from agent session traces |
| `augmentcode.research.md` | [Augment](https://augmentcode.com) | Real-time personal index + edit events (+2.6% improvement) |
| `continue.research.md` | [Continue](https://github.com/continuedev/continue) | BYOM architecture + content-addressed caching |

### Reverse Engineering

| File | Target | Key Finding |
|------|--------|-------------|
| `reverse-engineer/chatgpt-memory-reverse-engineering.md` | ChatGPT | Pre-computed summaries always injected (33 facts + recent chat summaries) |
| `reverse-engineer/claude-memory-reverse-engineering.md` | Claude | On-demand tool-based retrieval (`conversation_search`, `recent_chats`) |

### Agent CLI Analysis

| File | Content |
|------|---------|
| `agent-cli/agent-files-analysis.md` | Cross-tool comparison: Claude Code vs Codex vs Gemini |
| `agent-cli/claude-session-files.md` | Claude Code: `~/.claude/` structure, JSONL format, plaintext compression |
| `agent-cli/codex-session-files.md` | Codex: `~/.codex/` structure, encrypted JWT compression |
| `agent-cli/gemini-session-files.md` | Gemini: `~/.gemini/` structure, server-side compression |

---

## Context Research Index

### Open Source Agents

| File | Project | Key Finding |
|------|---------|-------------|
| `pi.research.md` | [Pi](https://github.com/badlogic/pi-mono) | Minimal: infinite accumulate → single LLM summary compaction. No pre-send processing, no token budgeting. ~300 word system prompt. Subagent via extension (process isolation) |
| `openclaw.research.md` | [OpenClaw](https://github.com/openclaw/openclaw) | Multi-stage pipeline: sanitize → validate → truncate → assemble. Pluggable ContextEngine (7 lifecycle hooks). Per-provider turn validation. Built-in subagent via gateway RPC (bidirectional) |
| `gemini-cli.research.md` | [Gemini CLI](https://github.com/google-gemini/gemini-cli) | Two-pass verified compression (generate + probe). Tool output pre-summarization with reverse token budget. 50% threshold (aggressive). In-process subagents with fresh chat instance |

### Reverse Engineering (Planned)

| File | Project | Status |
|------|---------|--------|
| `claude-code-context.research.md` | Claude Code | TBD |
| `codex-context.research.md` | Codex | TBD |

See [plan/1-context-research.md](./plan/1-context-research.md) for detailed research plan.

---

## Setup

```bash
# Clone with submodules
git clone --recursive <repo-url>

# Or initialize submodules after clone
git submodule update --init --recursive
```

---

## License

Personal research project. Submodules retain their original licenses.
