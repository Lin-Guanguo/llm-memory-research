# Supermemory Technical Research Report

Last Updated: 2026-03-24

> **Research Methodology**: Open-source repository analysis (GitHub `supermemoryai/supermemory`), blog post analysis, documentation review, and web search for community discussion. Note: Supermemory's backend (API server, ingestion pipeline, memory engine) is **closed source**. The open-source repo contains client SDKs, framework integrations, MCP server, and the web application shell.

## Overview

**Supermemory** is a commercial memory and context platform for AI agents, positioned as an all-in-one solution combining memory extraction, RAG, user profiles, and data connectors into a single managed API. It claims #1 performance on three major benchmarks: [LongMemEval](https://github.com/xiaowu0162/LongMemEval), [LoCoMo](https://github.com/snap-research/locomo), and [ConvoMem](https://github.com/Salesforce/ConvoMem).

Separately, Supermemory has published research on **ASMR (Agentic Search and Memory Retrieval)** -- an experimental multi-agent system that replaces vector database retrieval with LLM-powered agentic reasoning, achieving ~99% on LongMemEval-s. ASMR is **not** the production engine; it is a research prototype announced in March 2026.

**Source:** [GitHub Repository](https://github.com/supermemoryai/supermemory) | [Documentation](https://supermemory.ai/docs) | [ASMR Blog Post](https://blog.supermemory.ai/we-broke-the-frontier-in-agent-memory-introducing-99-sota-memory-system/) | [Research Page](https://supermemory.ai/research/)

---

## 1. Production System Architecture

### What's in the Open-Source Repo

The GitHub repository (`supermemoryai/supermemory`) is a **Turbo monorepo** containing client-side code only. The actual memory engine, ingestion pipeline, and search infrastructure run on Supermemory's cloud (Cloudflare Workers + PostgreSQL).

```
supermemory/ (open-source monorepo)
├── apps/
│   ├── web/              # Next.js consumer application
│   ├── mcp/              # MCP server (Cloudflare Workers + Durable Objects)
│   ├── browser-extension/ # Chrome extension
│   ├── docs/             # Documentation site
│   └── raycast-extension/ # Raycast plugin
├── packages/
│   ├── tools/            # SDK integrations (Vercel AI SDK, Mastra, OpenAI, Claude)
│   ├── lib/              # Shared client utilities
│   ├── ui/               # React UI components + memory graph visualization
│   ├── validation/       # Zod schemas (mirrors DB schema)
│   ├── hooks/            # React hooks
│   ├── ai-sdk/           # AI SDK provider
│   ├── openai-sdk-python/ # Python OpenAI SDK integration
│   ├── agent-framework-python/ # Microsoft Agent Framework integration
│   └── memory-graph/     # Force-directed graph visualization
└── skills/               # Claude Code / OpenCode skills
```

### Production Memory Engine (Closed Source)

Based on the research page and documentation, the production system implements a 5-component architecture:

```
Content Input (text, conversations, files, URLs)
        ↓
┌─────────────────────────────────────────────────────────────┐
│                  Ingestion Pipeline                          │
│  1. Chunk-based Ingestion → semantic decomposition          │
│  2. Memory Extraction → atomic facts from sessions          │
│  3. Relational Versioning → updates/extends/derives edges   │
│  4. Temporal Grounding → documentDate + eventDate           │
│  5. Embedding → Cloudflare AI vectors + pgvector            │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│                   Storage Layer                              │
│  PostgreSQL + pgvector (Hyperdrive connection pooling)       │
│  • Documents (content, chunks, embeddings, summaries)        │
│  • MemoryEntries (versioned, with relations + temporal)      │
│  • Spaces / ContainerTags (user/project scoping)             │
│  • Graph edges (similarity-based connections)                │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│                   Retrieval Layer                             │
│  • Hybrid search: RAG chunks + extracted memories            │
│  • User profiles: static (stable) + dynamic (recent)         │
│  • Semantic similarity + metadata filtering                  │
│  • Graph-based relationship traversal                        │
└─────────────────────────────────────────────────────────────┘
```

### Memory Data Model (from Zod schemas in `packages/validation/schemas.ts`)

The `MemoryEntrySchema` reveals the internal memory structure:

| Field | Type | Purpose |
|-------|------|---------|
| `memory` | string | The atomic fact content |
| `version` | number | Version counter for updates |
| `isLatest` | boolean | Whether this is the current version |
| `parentMemoryId` | string? | Previous version of this memory |
| `rootMemoryId` | string? | Original memory in the chain |
| `memoryRelations` | `Record<"updates"\|"extends"\|"derives">` | Graph edges to related memories |
| `isStatic` | boolean | Stable fact (profile) vs dynamic (recent) |
| `isForgotten` | boolean | Soft-delete flag |
| `forgetAfter` | date? | TTL for automatic expiration |
| `isInference` | boolean | Whether this was inferred, not explicitly stated |
| `sourceCount` | number | How many documents support this memory |
| `memoryEmbedding` | number[]? | Vector embedding |

Three relationship types model fact evolution:
- **`updates`**: Contradictions/corrections (e.g., "moved from NYC to SF" supersedes "lives in NYC")
- **`extends`**: Supplements existing facts with details
- **`derives`**: Inferred logic from multiple memories

### User Profile System

Profiles split into two tiers, delivered via `/v4/profile`:

```typescript
interface ProfileStructure {
  profile: {
    static?: Array<{ memory: string; metadata? }>   // Stable facts (name, preferences)
    dynamic?: Array<{ memory: string; metadata? }>   // Recent context (current projects)
  }
  searchResults: {
    results: Array<{ memory: string; similarity: number }>  // Query-relevant memories
  }
}
```

The SDK client-side deduplicates across tiers with priority: Static > Dynamic > Search Results (`packages/tools/src/tools-shared.ts:deduplicateMemories`).

### API Surface

| Endpoint | Purpose |
|----------|---------|
| `client.add()` | Ingest content (text, conversations, files) |
| `client.profile()` | User profile + optional semantic search (~50ms) |
| `client.search.memories()` | Hybrid search: RAG + memory |
| `client.search.documents()` | Document search with metadata filters |
| `client.memories.forget()` | Soft-delete a memory (exact match or semantic fallback) |
| `client.documents.uploadFile()` | Upload PDFs, images, videos |
| `/v4/conversations` | Structured conversation ingestion with smart diffing |
| `/v3/graph/viewport` | Memory graph visualization data |

### MCP Server (`apps/mcp/`)

Runs on Cloudflare Workers with Durable Objects for per-session state. Exposes three core tools to AI clients:

| MCP Tool | Description |
|----------|-------------|
| `memory` | Save or forget information (save/forget action) |
| `recall` | Search memories + user profile in one call |
| `listProjects` | List available container tags for scoping |

Plus resources (`supermemory://profile`, `supermemory://projects`) and a `context` prompt for system prompt injection.

### Framework Integrations (`packages/tools/`)

| Integration | Mechanism | File |
|-------------|-----------|------|
| **Vercel AI SDK** | Middleware: intercepts `doGenerate`/`doStream`, injects memories into system prompt, saves conversation after response | `src/vercel/middleware.ts` |
| **Mastra** | Wrapper + processor for Mastra agent config | `src/mastra/` |
| **OpenAI SDK (Python)** | Middleware for OpenAI Responses API | `src/openai/middleware.ts` |
| **Claude Memory Tool** | File-system metaphor: `view`, `create`, `str_replace`, `insert`, `delete` on `/memories/` paths | `src/claude-memory.ts` |
| **Microsoft Agent Framework** | Python SDK wrapper | `packages/agent-framework-python/` |

Memory retrieval modes: `"profile"` (static+dynamic only), `"query"` (semantic search only), `"full"` (both).

---

## 2. ASMR: Agentic Search and Memory Retrieval (Experimental)

ASMR is an experimental research system, **separate from the production engine**, that replaces vector-based retrieval with multi-agent orchestration. Published March 22, 2026.

### Architecture

```
                    INGESTION (3 Observer Agents)
                    ─────────────────────────────
Raw sessions ──→  Agent 1 (sessions 1,3,5...)  ──→ ┐
                  Agent 2 (sessions 2,4,6...)  ──→ ├→ Structured findings
                  Agent 3 (sessions 7,9...)    ──→ ┘   (6 dimensions)
                  [All: Gemini 2.0 Flash]

                    RETRIEVAL (3 Search Agents)
                    ────────────────────────────
Question ──→  Agent 1: Direct facts & explicit statements  ──→ ┐
              Agent 2: Related context, social cues         ──→ ├→ Compiled
              Agent 3: Temporal timelines, relationship maps ──→ ┘   findings
              [Orchestrator retrieves verbatim session excerpts]

                    ANSWERING (Ensemble Voting)
                    ────────────────────────────
Compiled findings ──→  Strategy 1: 8-variant cluster (98.6% oracle)
                       Strategy 2: 12-variant decision forest (97.2% single output)
```

### Six Knowledge Extraction Dimensions

During ingestion, each observer agent extracts across all six:

1. **Personal Information** -- Names, relationships, biographical facts
2. **Preferences** -- Likes, dislikes, style choices
3. **Events** -- What happened, when, with whom
4. **Temporal Data** -- Timelines, date references, sequences
5. **Updates** -- Changes, corrections, contradictions
6. **Assistant Info** -- What the AI previously said/did

### Answer Strategies

| Strategy | Variants | Accuracy | Output |
|----------|----------|----------|--------|
| **8-Variant Cluster** | Specialized prompts (e.g., "Precise Counter", "Time Specialist") | 98.6% (oracle: success if *any* variant correct) | 8 parallel answers |
| **12-Variant Decision Forest** | GPT-4o-mini agents + Aggregator LLM with majority voting | 97.2% (single consensus output) | 1 aggregated answer |

### Key Innovation: LLM-as-Retriever

ASMR completely eliminates vector database queries. Instead of embedding + cosine similarity, it uses LLM agents that *read and reason* over stored findings. The blog claims this was "the single biggest unlock" -- agentic retrieval overcomes the "semantic similarity trap" where temporal changes and contradictions fool vector search.

### Cost Analysis

Each question requires **11-15 LLM calls**:
- 3 ingestion agents (one-time, amortized)
- 3 search agents per question
- 1 orchestrator for compilation
- 8 or 12 answer variants (depending on strategy)
- 1 aggregator (for decision forest strategy)

This makes ASMR impractical for production at scale but demonstrates the ceiling of what's achievable with agentic reasoning.

### Open-Source Status (as of 2026-03-24)

The blog post promised open-sourcing the ASMR agent flow in "beginning of April" (2026). As of this writing, **no ASMR-specific repository has been published** on the [supermemoryai GitHub organization](https://github.com/supermemoryai). The existing open-source repository contains only the production SDK/client code, not the ASMR agent pipeline. This should be re-checked in April 2026.

---

## 3. Benchmark Performance

### LongMemEval-s (Production Engine)

| Category | Supermemory | Zep | Full Context (115k tokens) |
|----------|-------------|-----|----------------------------|
| **Overall** | **81.6%** | 71.2% | 60.2% |
| Multi-Session | 71.43% | 57.9% | 44.3% |
| Temporal Reasoning | 76.69% | 62.4% | 45.1% |
| Knowledge Update | 88.46% | 83.3% | 78.2% |

### ASMR Experimental Results (LongMemEval-s)

| Configuration | Accuracy |
|---------------|----------|
| 8-Variant Cluster (oracle) | **98.6%** |
| 12-Variant Decision Forest | **97.2%** |
| Previous production engine | ~85% |

### Cross-Benchmark Claims

| Benchmark | What It Tests | Claim |
|-----------|---------------|-------|
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | Long-term memory across sessions with knowledge updates | #1 (81.6%) |
| [LoCoMo](https://github.com/snap-research/locomo) | Fact recall across extended conversations | #1 |
| [ConvoMem](https://github.com/Salesforce/ConvoMem) | Personalization and preference learning | #1 |

Note: Independent benchmarks from third parties sometimes report different numbers. A [DEV.to comparison article](https://dev.to/varun_pratapbhardwaj_b13/5-ai-agent-memory-systems-compared-mem0-zep-letta-supermemory-superlocalmemory-2026-benchmark-59p3) estimated Supermemory at ~70% on LoCoMo, lower than self-reported figures. [Hindsight achieves 91.4% on LongMemEval](https://vectorize.io/articles/hindsight-vs-supermemory), significantly above Supermemory's 81.6%.

---

## 4. Comparison with Other Memory Systems

| Feature | Supermemory | Mem0 | Letta (MemGPT) | Graphiti/Zep | Hindsight |
|---------|-------------|------|-----------------|--------------|-----------|
| **Architecture** | Memory graph + RAG (unified cloud service) | Vector + optional graph memory | OS-inspired tiered memory (agent self-manages) | Temporal knowledge graph (bi-temporal) | Multi-strategy hybrid (4 parallel retrievers) |
| **Open Source** | Client SDKs only; engine is closed | Core open source; graph features Pro-tier | Fully open source | Fully open source (Graphiti) | Open source |
| **Self-Hosting** | Enterprise agreement required | Yes (open-source core) | Yes | Yes | Yes |
| **Storage** | PostgreSQL + pgvector (Cloudflare) | 24+ vector stores + optional Neo4j | PostgreSQL + vector extensions | Neo4j knowledge graph | Embedded PostgreSQL |
| **Memory Extraction** | Automatic (LLM-driven) | LLM-driven fact extraction | Agent-controlled (proactive) | Triplet extraction + entity resolution | Fact extraction at write-time |
| **Contradiction Handling** | Version chain (updates/extends/derives) | LLM semantic deduplication | Agent edits core memory blocks | Temporal edge invalidation | Cross-encoder reranking |
| **Temporal Reasoning** | Dual timestamp (documentDate + eventDate) + forgetAfter TTL | Basic (via metadata) | No built-in temporal logic | Bi-temporal (valid_at + invalid_at) | Temporal filtering |
| **User Profiles** | Built-in (static + dynamic, ~50ms) | Not built-in | Core memory blocks (always in context) | Not built-in | Not built-in |
| **LongMemEval** | 81.6% (production) / ~99% (ASMR) | 58-66% (varies by source) | ~83.2% (estimated) | 71.2% | 91.4% |
| **Retrieval Method** | Hybrid: vector similarity + memory search; ASMR: LLM-as-retriever | Vector similarity | LLM decides when/what to retrieve | Graph traversal + semantic search | 4-channel RRF fusion |
| **Connectors** | Google Drive, Gmail, Notion, OneDrive, GitHub | No built-in | No built-in | No built-in | No built-in |
| **Pricing** | Free tier (1M tokens, 10K searches); paid plans | Open-source free; Pro $249/mo | Open source | Open source | Open source |

### Key Differentiators

**vs Mem0**: Supermemory bundles more features (RAG, profiles, connectors) into one API. Mem0 offers broader open-source flexibility with 24+ vector store backends. Supermemory's memory versioning (updates/extends/derives) is more structured than Mem0's LLM-driven deduplication.

**vs Letta**: Letta's "LLM OS" approach gives agents direct control over memory management (proactive retrieval/editing). Supermemory's memory management is automatic and opaque to the agent -- simpler integration but less agent autonomy.

**vs Graphiti/Zep**: Graphiti's bi-temporal knowledge graph with explicit entity nodes and edges provides richer relationship modeling. Supermemory's memory graph is similarity-based rather than entity-based. Graphiti is fully open source.

**vs Hindsight**: Hindsight outperforms Supermemory's production engine on LongMemEval (91.4% vs 81.6%) with a depth-focused, open-source approach. Supermemory offers breadth (RAG + memory + profiles + connectors) over depth.

**vs Observational Memory** ([Mastra Research](https://mastra.ai/research/observational-memory)): Observational Memory achieves 95% on LongMemEval with a specialized observation extraction approach. Supermemory's ASMR exceeds this experimentally (~99%) but at much higher compute cost.

---

## 5. Unique Features

### Automatic Forgetting

Memories with `forgetAfter` dates are automatically expired. Temporal facts like "I have an exam tomorrow" are recognized and given appropriate TTLs. The `isForgotten` flag allows soft deletion while preserving history.

### Memory Graph Visualization

The MCP server includes a force-directed graph visualization (`memory-graph` tool) that renders documents, extracted memories, and similarity-based edges. Uses WebGL canvas for performance with spatial viewport-based loading (`/v3/graph/viewport`).

### Session-Based Ingestion

Content is processed session-by-session rather than round-by-round. The `/v4/conversations` endpoint supports structured messages with smart diffing -- the backend detects when messages are appended to existing conversations and processes only new content.

### Framework Middleware Pattern

The Vercel AI SDK integration (`packages/tools/src/vercel/`) implements a middleware pattern that intercepts LLM calls to: (1) inject memories into the system prompt before generation, (2) save the full conversation after the response. Per-turn caching avoids redundant API calls during tool-call loops.

---

## 6. Technical Stack

| Component | Technology |
|-----------|------------|
| **Runtime** | Cloudflare Workers |
| **Database** | PostgreSQL (Hyperdrive pooling) + pgvector |
| **Embeddings** | Cloudflare AI |
| **Web Framework** | Hono (API), Next.js (web app) |
| **Auth** | Better Auth + OAuth 2.0 for MCP |
| **MCP** | `agents/mcp` (Cloudflare Durable Objects) |
| **Monorepo** | Turborepo + Bun |
| **Language** | TypeScript (primary), Python (SDK, agent-framework) |
| **Monitoring** | Sentry + PostHog analytics |

---

## 7. Open Questions & Limitations

1. **Closed-source core**: The memory engine, ingestion pipeline, and search infrastructure are proprietary. Evaluating the production system requires trusting published benchmarks or running MemoryBench yourself.

2. **ASMR cost**: 11-15 LLM calls per question makes ASMR impractical for real-time production use. The blog acknowledges this is "not our main production engine (yet)."

3. **Vendor lock-in**: No self-hosting option outside enterprise agreements. Data sovereignty concerns for regulated industries.

4. **Benchmark discrepancies**: Self-reported numbers (#1 on all benchmarks) vs independent testing sometimes diverge. Hindsight's 91.4% on LongMemEval significantly exceeds Supermemory's 81.6%.

5. **ASMR open-source timeline**: Promised for April 2026. Not yet available as of 2026-03-24. Should be re-checked.

6. **Production vs ASMR gap**: The production engine scores 81.6% while ASMR scores ~99%. Bridging this gap for production use would be the key engineering challenge.

---

## Sources

- [Supermemory GitHub Repository](https://github.com/supermemoryai/supermemory) (accessed: 2026-03-24)
- [ASMR Blog Post](https://blog.supermemory.ai/we-broke-the-frontier-in-agent-memory-introducing-99-sota-memory-system/) (accessed: 2026-03-24)
- [Supermemory Research Page](https://supermemory.ai/research/) (accessed: 2026-03-24)
- [Supermemory Documentation](https://supermemory.ai/docs/intro) (accessed: 2026-03-24)
- [Memory vs RAG Concepts](https://supermemory.ai/docs/concepts/memory-vs-rag) (accessed: 2026-03-24)
- [Vectorize: Best AI Agent Memory Systems 2026](https://vectorize.io/articles/best-ai-agent-memory-systems) (accessed: 2026-03-24)
- [Vectorize: Hindsight vs SuperMemory](https://vectorize.io/articles/hindsight-vs-supermemory) (accessed: 2026-03-24)
- [DEV.to: 5 AI Agent Memory Systems Compared](https://dev.to/varun_pratapbhardwaj_b13/5-ai-agent-memory-systems-compared-mem0-zep-letta-supermemory-superlocalmemory-2026-benchmark-59p3) (accessed: 2026-03-24)
