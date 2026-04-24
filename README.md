# LLM Agent Research

Last Updated: 2026-04-15

A systematic research project studying LLM agent internals: memory implementations and context management across frameworks, products, and agent CLI tools.

Read online: [lin-guanguo.github.io/llm-memory-research](https://lin-guanguo.github.io/llm-memory-research/)

---

## Published Articles

| Article | Platform | File |
|---------|----------|------|
| [LLM记忆：设计很复杂，落地出奇简单](http://xhslink.com/o/7JBMfdnw71i) | 小红书 | `blog.1.chinese.md` |
| [我分析了 6 个主流 Agent 的记忆和上下文](https://www.xiaohongshu.com/discovery/item/69ca6277000000001b02229f) | 小红书 | `blog.2.chinese.md` / `blog.2.md` |

---

## Research Directions

1. **Memory** — How agents persist and retrieve knowledge across conversations. See [plan/3-memory-update.md](./plan/3-memory-update.md) for 2026 Q1 update plan (Supermemory, Observational Memory, Hindsight, etc.)
2. **Context** — How agents assemble and manage context within a conversation (token generation, prompt stitching, token budgeting)
3. **Learning** (in progress) — Can models learn after deployment? Continual learning, catastrophic forgetting, personalized models via fine-tuning/LoRA. See [plan/2-learning-research.md](./plan/2-learning-research.md) for detailed plan
4. **Academic Memory & Retrieval Layer** (planned) — Paper-side memory architectures (A-Mem, HippoRAG, EM-LLM, Generative Agents) and retrieval internals (chunking, ColBERT, rerankers). See [plan/4-academic-and-retrieval-research.md](./plan/4-academic-and-retrieval-research.md)

## Summary Documents

| File | Scope | Content |
|------|-------|---------|
| **[summary.md](./summary.md)** | **All directions** | Full research synthesis: two analytical angles (methods × directions), memory, context, cross-domain findings, open questions |
| **[summary.chinese.md](./summary.chinese.md)** | **All directions** | Chinese translation of summary.md |
| **[findings.md](./findings.md)** | **Cross-domain** | 10 detailed findings from studying memory × context together |
| **[memory.summary.md](./memory.summary.md)** | Memory | Consolidated findings from reverse-engineering ChatGPT, Claude, and open-source memory systems |
| **[memory.26Q1.summary.md](./memory.26Q1.summary.md)** | Memory (2026 Q1) | New projects: Supermemory, Mastra, Hindsight, MemOS. Anti-RAG trend, compression as strategy |
| **[memory.ecosystem.md](./memory.ecosystem.md)** | Memory | Market overview with GitHub stars, funding, and research priorities |
| **[context.summary.md](./context.summary.md)** | Context | Cross-project comparison (6 agents), design patterns, open questions |
| **[learning.summary.md](./learning.summary.md)** | Learning (Pillar 3) | Three personality paradigms (prompt/activation/weight), two production architectures (Neuro-sama vs Character.AI), updated Pillar 3 definition |
| **[memory.academic.summary.md](./memory.academic.summary.md)** | Memory (academic side) | 2026 taxonomy (Forms × Functions × Dynamics), methodology critique (Anatomy), 3 architectural trends (MAGMA / LiCoMemory / SimpleMem), Dayfold implications |
| **[retrieval.summary.md](./retrieval.summary.md)** | Retrieval layer | Chunking / embeddings / pipeline architecture / production stacks synthesis; 2026 default RAG stack |
| **[memory.literature-scan.md](./memory.literature-scan.md)** | Memory (academic scan) | Tier 1 (2026) / Tier 2 (2025) / Tier 3 (pre-2025) triage with arxiv links |
| **[memory.skim-summaries.md](./memory.skim-summaries.md)** | Memory (academic skim) | 7 papers × ~500 words: Du survey, graph-memory survey, A-MAC, A-MEM, Memoria, AgeMem, TTT |

---

## Repository Structure

```
llm-agent-research/
├── plan/                                     # Research plans
│   ├── 1-context-research.md                 # Context research plan & steps (completed)
│   ├── 2-learning-research.md                # Continuous learning research plan (in progress)
│   ├── 3-memory-update.md                    # 2026 Q1 memory update plan (research done)
│   └── 4-academic-and-retrieval-research.md  # Academic memory papers + retrieval/embedding layer (planned)
│
├── Summary & Cross-Domain
│   ├── summary.md                            # Full research synthesis (EN)
│   ├── summary.chinese.md                    # Full research synthesis (CN)
│   ├── findings.md                           # Cross-domain findings (Memory × Context)
│   ├── memory.summary.md                     # Memory research summary (Phase 1)
│   ├── memory.26Q1.summary.md                # Memory research summary (2026 Q1)
│   ├── memory.ecosystem.md                   # Market analysis & priorities
│   ├── context.summary.md                    # Context research summary
│   └── learning.summary.md                   # Learning (Pillar 3) research summary
│
├── Academic Memory Deep Dives (*.research.md, 2026 papers)
│   ├── memory-survey-2026.research.md        # Memory in the Age of AI Agents (2512.13564) — 3-axis taxonomy
│   ├── memory-anatomy.research.md            # Anatomy of Agentic Memory (2602.19320) — methodology critique
│   ├── magma.research.md                     # MAGMA (2601.03236) — four orthogonal graphs
│   ├── licomemory.research.md                # LiCoMemory (2511.01448) — CogniGraph semantic index
│   ├── simplemem.research.md                 # SimpleMem (2601.02553) — three-stage compression
│   ├── a-mem.research.md                     # A-MEM (2502.12110) — Zettelkasten + metadata evolution
│   └── agemem.research.md                    # AgeMem (2601.01885) — RL-trained GRPO memory policy
│
├── Retrieval Layer Research
│   ├── retrieval/chunking.research.md        # Text chunking strategies (fixed/recursive/semantic/late/agentic)
│   ├── retrieval/embedding-models.research.md # Dense/ColBERT/Matryoshka/SPLADE/rerankers/2026 frontier
│   ├── retrieval/retrieval-architecture.research.md # Hybrid/HyDE/rerank/agentic/GraphRAG/long-context
│   └── retrieval/production-stacks.research.md # LlamaIndex/LangChain/Haystack/Vespa comparison
│
├── papers/pdfs/                              # Archived arxiv PDFs (13 papers)
│
├── Memory Research (*.research.md)
│   ├── mem0.research.md                      # Mem0: LLM-driven CRUD memory
│   ├── letta.research.md                     # Letta: Three-tier self-editing memory
│   ├── graphiti.research.md                  # Graphiti: Bi-temporal knowledge graph
│   ├── hindsight.research.md                 # Hindsight: Four memory networks + reflect
│   ├── mastra.research.md                    # Mastra OM: Pure compression, no retrieval
│   ├── memos.research.md                     # MemOS: Memory as OS resource
│   ├── supermemory.research.md               # Supermemory: ASMR, LLM-as-retriever
│   ├── qdrant.research.md                    # Qdrant: Filtrable HNSW vector DB
│   ├── chroma.research.md                    # Chroma: Developer-friendly vector DB
│   ├── cursor.research.md                    # Cursor: Custom embedding training
│   ├── augmentcode.research.md               # Augment: Real-time personal index
│   ├── continue.research.md                  # Continue: Open-source coding assistant
│   ├── production-adoption.research.md       # Production deployment cases
│   └── openclaw-memory.research.md           # OpenClaw: Hybrid search + temporal decay + memory flush
│
├── Context Research
│   ├── pi.research.md                        # Pi: Minimal agent loop & compaction
│   ├── openclaw.research.md                  # OpenClaw: Pluggable ContextEngine
│   ├── gemini-cli.research.md                # Gemini CLI: Two-pass verified compression
│   ├── claude-code-context.research.md       # Claude Code: Server-side compaction + context awareness
│   ├── codex-context.research.md             # Codex: Dual compaction + per-item truncation
│   ├── opencode.research.md                  # OpenCode: Two-phase compaction + fork/revert
│   └── anthropic-context-engineering.research.md  # Anthropic official guidance vs practice
│
├── Continuous Learning Research
│   ├── neuro-sama.research.md               # Neuro-sama: Weight-based personality, iterative fine-tuning
│   ├── character-ai.research.md             # Character.AI: Meta-character training, DPO + personality constitutions
│   ├── personality-engineering.research.md   # Personality engineering: prompting vs fine-tuning vs activation engineering
│   ├── multi-lora.research.md               # Multi-LoRA: Serving (S-LoRA/vLLM), per-user generation, composition
│   └── hybrid-memory-weight.research.md     # Hybrid memory→weight: 5 architectures, forgetting, production status
│
├── reverse-engineer/                         # Product reverse-engineering
│   ├── chatgpt-memory-reverse-engineering.md
│   └── claude-memory-reverse-engineering.md
│
├── agent-cli/                                # Agent CLI session file analysis
│   ├── agent-files-analysis.md               # Cross-tool comparison
│   ├── agent-integration-guide.md            # Integration guide
│   ├── claude-session-files.md               # Claude Code session structure
│   ├── claude-session-file-schema.md         # Claude Code JSON schema
│   ├── codex-session-files.md                # Codex session structure
│   ├── codex-session-file-schema.md          # Codex JSON schema
│   ├── gemini-session-files.md               # Gemini CLI session structure
│   └── gemini-session-file-schema.md         # Gemini CLI JSON schema
│
├── Git Submodules (Source Code)
│   ├── mem0/                                 # github.com/mem0ai/mem0
│   ├── letta/                                # github.com/letta-ai/letta
│   ├── graphiti/                             # github.com/getzep/graphiti
│   ├── hindsight/                            # github.com/vectorize-io/hindsight
│   ├── mastra/                               # github.com/mastra-ai/mastra
│   ├── memos/                                # github.com/MemTensor/MemOS
│   ├── supermemory/                          # github.com/supermemoryai/supermemory
│   ├── continue/                             # github.com/continuedev/continue
│   ├── pi-mono/                              # github.com/badlogic/pi-mono
│   ├── openclaw/                             # github.com/openclaw/openclaw
│   ├── gemini-cli/                           # github.com/google-gemini/gemini-cli
│   ├── codex-cli/                            # github.com/openai/codex
│   ├── opencode/                             # github.com/anomalyco/opencode
│   ├── claude-code-system-prompts/           # github.com/Piebald-AI/claude-code-system-prompts
│   └── claude-code-sourcemap/                # github.com/ChinaSiro/claude-code-sourcemap (v2.1.88 source)
│
├── Blog Posts
│   ├── blog.1.chinese.md                     # Blog #1: LLM记忆 (Chinese)
│   ├── blog.1.md                             # Blog #1: LLM Memory (English)
│   ├── blog.2.chinese.md                     # Blog #2: 6 Agent 上下文与记忆对比 (Chinese)
│   └── blog.2.md                             # Blog #2: Context & Memory comparison (English)
│
├── Claude Code Source Analysis
│   ├── claude-code-sourcemap.research.md     # Core architecture (v2.1.88 source map)
│   ├── claude-code-swarm.research.md         # Agent Swarm architecture
│   ├── claude-code-buddy.research.md         # Buddy/Companion architecture
│   ├── claude-code-buddy.product.research.md # Buddy product design (EN)
│   └── claude-code-buddy.product.research.chinese.md  # Buddy product design (CN)
│
└── demos/                                    # Experimental implementations
    └── knowledge-base/                       # ChromaDB vector search demo
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

### Memory Frameworks (Gen 2, 2026 Q1)

| File | Project | Key Innovation |
|------|---------|----------------|
| `hindsight.research.md` | [Hindsight](https://github.com/vectorize-io/hindsight) | Four memory networks (World/Experience/Observation) + reflect. MPFP graph traversal. 91.4% LongMemEval |
| `mastra.research.md` | [Observational Memory (Mastra)](https://mastra.ai/research/observational-memory) | Pure compression, no retrieval. Observer+Reflector agents. 94.87% LongMemEval |
| `memos.research.md` | [MemOS](https://github.com/MemTensor/MemOS) | Three-layer memory OS (Plaintext/Activation/Parametric). MemCube container |
| `supermemory.research.md` | [Supermemory](https://github.com/supermemoryai/supermemory) | ASMR: LLM-as-retriever, 3+3 agent pipeline, ensemble voting. 98.6% oracle |

### Coding Assistants

| File | Project | Key Innovation |
|------|---------|----------------|
| `cursor.research.md` | [Cursor](https://cursor.com) | Custom embeddings trained from agent session traces |
| `augmentcode.research.md` | [Augment](https://augmentcode.com) | Real-time personal index + edit events (+2.6% improvement) |
| `continue.research.md` | [Continue](https://github.com/continuedev/continue) | BYOM architecture + content-addressed caching |
| `openclaw-memory.research.md` | [OpenClaw](https://github.com/openclaw/openclaw) | Hybrid search (vector + BM25) + temporal decay + MMR. Pre-compaction memory flush bridges context→memory. Most sophisticated memory system among coding agents |

### Reverse Engineering

| File | Target | Key Finding |
|------|--------|-------------|
| `reverse-engineer/chatgpt-memory-reverse-engineering.md` | ChatGPT | Pre-computed summaries always injected (33 facts + recent chat summaries) |
| `reverse-engineer/claude-memory-reverse-engineering.md` | Claude | On-demand tool-based retrieval (`conversation_search`, `recent_chats`) |
| `claude-code-sourcemap.research.md` | Claude Code (source) | **Source-level analysis** from v2.1.88 source map leak. 4-tier compaction, Sonnet-as-memory-selector, prompt cache architecture, plugin marketplace, coordinator mode |
| `claude-code-swarm.research.md` | Claude Code (source) | **Agent Swarm architecture**: file-based mailbox (JSON + file lock), 8+ message types (chat/permission/shutdown/sync), 1s polling, idle notification guarantee, centralized permission model, task list coordination |
| `claude-code-buddy.research.md` | Claude Code (source) | **Buddy/Companion architecture**: side-channel inference, process model, billing separation, prompt cache integration, feature staging infrastructure |
| `claude-code-buddy.product.research.md` | Claude Code (source) | **Buddy product design analysis** (EN): user needs, interaction model, engagement patterns in a productivity tool |
| `claude-code-buddy.product.research.chinese.md` | Claude Code (source) | Same as above (CN) |

### Agent CLI Analysis

| File | Content |
|------|---------|
| `agent-cli/agent-files-analysis.md` | Cross-tool comparison: Claude Code vs Codex vs Gemini |
| `agent-cli/agent-integration-guide.md` | Integration guide for agent CLI tools |
| `agent-cli/claude-session-files.md` | Claude Code: `~/.claude/` structure, JSONL format, plaintext compression |
| `agent-cli/claude-session-file-schema.md` | Claude Code: detailed JSON schema |
| `agent-cli/codex-session-files.md` | Codex: `~/.codex/` structure, encrypted JWT compression |
| `agent-cli/codex-session-file-schema.md` | Codex: detailed JSON schema |
| `agent-cli/gemini-session-files.md` | Gemini: `~/.gemini/` structure, server-side compression |
| `agent-cli/gemini-session-file-schema.md` | Gemini: detailed JSON schema |

---

## Context Research Index

### Open Source Agents

| File | Project | Key Finding |
|------|---------|-------------|
| `pi.research.md` | [Pi](https://github.com/badlogic/pi-mono) | Minimal: infinite accumulate → single LLM summary compaction. No pre-send processing, no token budgeting. ~300 word system prompt. Subagent via extension (process isolation) |
| `openclaw.research.md` | [OpenClaw](https://github.com/openclaw/openclaw) | Multi-stage pipeline: sanitize → validate → truncate → assemble. Pluggable ContextEngine (7 lifecycle hooks). Per-provider turn validation. Built-in subagent via gateway RPC (bidirectional). See also `openclaw-memory.research.md` for memory system |
| `gemini-cli.research.md` | [Gemini CLI](https://github.com/google-gemini/gemini-cli) | Two-pass verified compression (generate + probe). Tool output pre-summarization with reverse token budget. 50% threshold (aggressive). In-process subagents with fresh chat instance |
| `codex-context.research.md` | [Codex](https://github.com/openai/codex) | Dual compaction (server encrypted + client LLM). Per-item tool output truncation at record time. Mid-stream compaction. Single flat loop (no sub-agents). Rust implementation. Minimal 4-section compaction prompt |
| `opencode.research.md` | [OpenCode](https://github.com/anomalyco/opencode) | Two-phase compaction (prune tool outputs + LLM summary). Provider-specific system prompts. Resumable sub-agent sessions. Filesystem-aware fork/revert. Plugin hooks for compaction |

### Reverse Engineering

| File | Project | Key Finding |
|------|---------|-------------|
| `claude-code-context.research.md` | Claude Code | Server-side API compaction (simplest client). 9-section summary (most detailed). Model-level context awareness (`<budget:token_budget>`). Worker fork inherits full parent context. 65+ modular system prompt files + 20+ dynamic reminders |
| `claude-code-sourcemap.research.md` | Claude Code (source) | **Source-level verification**: 4-tier compaction (micro→cached→full→snip), prompt cache as first-class concern (section caching, beta latches, in-content reminders), forked agents with shared cache, tool concurrency partitioning |
| `anthropic-context-engineering.research.md` | Anthropic official guidance | Anthropic's recommendations vs industry practice. Four types of context rot. Three long-horizon strategies (tool result clearing → compaction → sub-agents). Compliance analysis across all studied agents |

See [plan/1-context-research.md](./plan/1-context-research.md) for detailed research plan.

---

## Continuous Learning Research Index

| File | Project | Key Finding |
|------|---------|-------------|
| `neuro-sama.research.md` | [Neuro-sama](https://vedal.ai/) | 2B param custom fine-tuned LLM (q2_k). Iterative batch fine-tuning from stream transcripts. Weight-based personality + prompt-based situational context. Closest production analog to continual learning |
| `character-ai.research.md` | [Character.AI](https://character.ai/) | DPO + personality constitutions for meta-character training. One model generalizes to ANY character. 30K msg/s, 95% KV cache hit. Four-layer system: foundation → character training → prompt → feedback |
| `personality-engineering.research.md` | Cross-project survey | Three paradigms: prompting (fragile, can't override alignment), fine-tuning (BIG5-CHAT, FinePE MoE-LoRA), activation engineering (PERSONA matches SFT training-free, Anthropic persona vectors). Activation engineering is the emerging middle ground |
| `multi-lora.research.md` | Multi-LoRA ecosystem | Serving solved (S-LoRA: 2000 adapters/GPU). Per-user adapter generation in <1s (Doc-to-LoRA, Profile-to-PEFT). Composition via TIES/DARE/MoLoRA. Production: Convirza (60+ adapters), Phonely (99.2% accuracy) |
| `hybrid-memory-weight.research.md` | Hybrid pipeline survey | No production system does full memory→weight. Letta has roadmap. Sparse memory fine-tuning: 11% vs 89% forgetting. Emerging consensus: token-first, weight-second |

See [plan/2-learning-research.md](./plan/2-learning-research.md) for detailed research plan.

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
