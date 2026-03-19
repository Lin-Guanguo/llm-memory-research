# LLM Agent Research

Last Updated: 2026-03-19

A systematic research project studying LLM agent internals: memory implementations and context management across frameworks, products, and agent CLI tools.

---

## Published Articles

| Article | Platform | File |
|---------|----------|------|
| [LLM记忆：设计很复杂，落地出奇简单](http://xhslink.com/o/7JBMfdnw71i) | 小红书 | `memory.blog.1.chinese.md` |

---

## Research Directions

1. **Memory** — How agents persist and retrieve knowledge across conversations
2. **Context** — How agents assemble and manage context within a conversation (token generation, prompt stitching, token budgeting)

## Summary Documents

| File | Scope | Content |
|------|-------|---------|
| **[findings.md](./findings.md)** | **Cross-domain** | 8 findings from studying memory × context together: shared patterns, unsolved problems, research gaps |
| **[memory.summary.md](./memory.summary.md)** | Memory | Consolidated findings from reverse-engineering ChatGPT, Claude, and open-source memory systems |
| **[memory.ecosystem.md](./memory.ecosystem.md)** | Memory | Market overview with GitHub stars, funding, and research priorities |
| **[context.summary.md](./context.summary.md)** | Context | Cross-project comparison (6 agents), design patterns, open questions |

---

## Repository Structure

```
llm-agent-research/
├── plan/                                    # Research plans
│   └── 1-context-research.md                # Context research plan & steps
│
├── Memory Research (*.research.md)
│   ├── production-adoption.research.md      # Production deployment cases
│   ├── memory.ecosystem.md                  # Market analysis & priorities
│   ├── memory.summary.md                    # Memory research summary
│   ├── context.summary.md                   # Context research summary
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
│   ├── claude-code-context.research.md        # Claude Code: Server-side compaction + context awareness
│   ├── codex-context.research.md             # Codex: Dual compaction + per-item truncation
│   └── dayfold-agent-context.research.md    # Dayfold: Dual-channel workflow agent
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
│   ├── gemini-cli/                           # github.com/google-gemini/gemini-cli
│   ├── claude-code-system-prompts/           # github.com/Piebald-AI/claude-code-system-prompts
│   └── opencode/                             # github.com/anomalyco/opencode
│
├── memory.blog.1.chinese.md                 # Memory research blog post (Chinese)
└── demos/                                   # Experimental implementations
    └── knowledge-base/                      # ChromaDB vector search demo
```

---

## Memory Research Index

### Summary & Analysis

| File | Content |
|------|---------|
| `production-adoption.research.md` | Real-world adoption: Mem0 (AWS SDK), Letta (11x, Kognitos), Graphiti (Zep AI) |
| `memory.ecosystem.md` | GitHub stars, funding data, market segmentation, research priorities |
| `memory.summary.md` | Consolidated findings from reverse-engineering and open-source analysis |

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
| `codex-context.research.md` | [Codex](https://github.com/openai/codex) | Dual compaction (server encrypted + client LLM). Per-item tool output truncation at record time. Mid-stream compaction. Single flat loop (no sub-agents). Rust implementation. Minimal 4-section compaction prompt |
| `opencode.research.md` | [OpenCode](https://github.com/anomalyco/opencode) | Two-phase compaction (prune tool outputs + LLM summary). Provider-specific system prompts. Resumable sub-agent sessions. Filesystem-aware fork/revert. Plugin hooks for compaction |

### Reverse Engineering

| File | Project | Key Finding |
|------|---------|-------------|
| `claude-code-context.research.md` | Claude Code | Server-side API compaction (simplest client). 9-section summary (most detailed). Model-level context awareness (`<budget:token_budget>`). Worker fork inherits full parent context. 65+ modular system prompt files + 20+ dynamic reminders |

### Self-Developed Agent

| File | Project | Key Finding |
|------|---------|-------------|
| `dayfold-agent-context.research.md` | Dayfold Agent (LangGraph workflow) | Dual-channel design (Ports for structured data + ContextMessages for semantic memory). Proactive per-node summary_exchange compression (vs reactive compaction in mainstream agents). Three-tier per-node context_filter. No compaction fallback |

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
