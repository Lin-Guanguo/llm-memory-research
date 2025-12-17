# LLM Memory Ecosystem: Products & Open Source Projects

Last Updated: 2025-12-18

> **Research Methodology**: Combined Claude Code analysis + Gemini CLI internet search (Dec 2025)

---

## 0. Market Analysis Summary

### Research Status in This Project

| Project | Status | Research File |
|---------|--------|---------------|
| **Mem0** | ✅ Researched | `mem0.research.md` |
| **Letta** | ✅ Researched | `letta.research.md` |
| **Cursor** | ✅ Researched | `cursor.research.md` |
| **Augment Code** | ✅ Researched | `augmentcode.research.md` |
| **Zep + Graphiti** | 🔴 Not yet | High priority |
| **Continue** | 🔴 Not yet | High priority |
| **Qdrant** | 🔴 Not yet | Medium priority |
| **Chroma** | 🔴 Not yet | Medium priority |

### Research Priority Recommendations

| Priority | Project | GitHub Stars | Funding | Reason |
|----------|---------|--------------|---------|--------|
| 🔥 **1** | **Zep + Graphiti** | ~21.2k | $2.3M (YC) | Temporal knowledge graph - new direction in 2025 |
| 🔥 **2** | **Continue** | **30.4k** | **$65M Series A** | Open source coding assistant market leader |
| ⭐ **3** | **Qdrant** | 27.7k | $37.8M | Production-scale vector DB leader |
| ⭐ **4** | **Chroma** | 24k | $36M | Developer experience leader, Rust rewrite v1.0 (Mar 2025) |
| ○ **5** | **Tabby** | 11k | $7.2M | Self-hosted alternative (Continue is leader) |
| ○ **6** | **Void** | - | - | Privacy-first, new project |

### Key 2025 Insight

> **Industry shift**: From pure vector similarity → **Knowledge Graphs + Temporal Awareness**
>
> Graphiti's 21.2k stars (vs Zep core's 3.8k) shows massive developer interest in graph-based memory.

---

## 1. Memory Frameworks

| Project | Type | GitHub Stars | Funding | Core Technology | 2025 Updates | Link |
|---------|------|--------------|---------|-----------------|--------------|------|
| **Mem0** | Open Source | ~23k | $2.2M | LLM-driven fact extraction + Vector/Graph dual storage | **Mem0g** - Graph database for relational reasoning | [GitHub](https://github.com/mem0ai/mem0) |
| **Letta** (MemGPT) | Open Source | ~15k | $10M | Three-tier memory + Agent self-editing prompts | Supports "infinite context" chatbots | [GitHub](https://github.com/letta-ai/letta) |
| **Zep** | Open Source | ~3.8k (core) | $2.3M (YC) | Long-term memory + Auto-summarization + Entity extraction | **Graphiti** temporal knowledge graph engine | [GitHub](https://github.com/getzep/zep) |
| **Graphiti** | Open Source | **~21.2k** | (see Zep) | Temporal knowledge graph engine | **Breakout hit** - massive adoption in 2025 | [GitHub](https://github.com/getzep/graphiti) |
| **LangChain Memory** | Open Source | (part of LangChain) | $35M+ | Multiple Memory types (Buffer, Summary, VectorStore) | Most complete ecosystem, but generic | [GitHub](https://github.com/langchain-ai/langchain) |
| **LlamaIndex** | Open Source | ~38k | $19M | Data indexing framework, multiple storage backends | Best for RAG scenarios | [GitHub](https://github.com/run-llama/llama_index) |
| **Motorhead** | Open Source | ~0.5k | - | Memory server with Redis backend | Lightweight option, less active | [GitHub](https://github.com/getmetal/motorhead) |

### Selection Guide

| Use Case | Recommendation |
|----------|----------------|
| Infinite context chat | Letta |
| Smart user profiles | Mem0 or Zep |
| Temporal-aware memory | Zep (Graphiti) |
| Quick prototyping | LangChain Memory |

---

## 2. AI Coding Assistants (Codebase Indexing)

| Project | Type | GitHub Stars | Funding | Core Technology | Market Position | Link |
|---------|------|--------------|---------|-----------------|-----------------|------|
| **Cursor** | Commercial | - | $400M+ (Series B) | AST + Symbol graph + Semantic embeddings | **Commercial benchmark**, custom embedding models | [cursor.com](https://cursor.com) |
| **Augment Code** | Commercial | - | $252M | Context Engine + Real-time personal index | **Enterprise leader**, per-developer index | [augmentcode.com](https://augmentcode.com) |
| **Continue** | Open Source | **30.4k** | **$65M Series A** | Customizable Context Providers | **Open source leader**, $500M valuation | [GitHub](https://github.com/continuedev/continue) |
| **Tabby** | Open Source | 11k | $7.2M | RAG + repo-context indexing | Self-hosted Copilot alternative | [GitHub](https://github.com/TabbyML/tabby) |
| **Aider** | Open Source | ~25k | - | Git-aware multi-file editing | CLI tool leader | [GitHub](https://github.com/paul-gauthier/aider) |
| **Sourcegraph Cody** | Open Source | ~3k | $225M (company) | Enterprise code search | Cross-repository search | [GitHub](https://github.com/sourcegraph/cody) |
| **Void** | Open Source | ~5k | - | Cursor-like features | **Privacy-first**, new entrant | [voideditor.com](https://voideditor.com) |
| **CocoIndex** | Open Source | ~1k | - | **Tree-sitter** syntax-aware chunking | Niche: syntax-aware indexing | [GitHub](https://github.com/cocoindex/cocoindex) |

### Selection Guide

| Use Case | Recommendation | Notes |
|----------|----------------|-------|
| Open source IDE extension | **Continue** | Market leader, $65M funding |
| Privacy-first | Void | Runs locally with your own API keys |
| Self-hosted enterprise | Tabby | $7.2M funding, enterprise focus |
| CLI workflow | Aider | Git-aware, terminal-native |
| Syntax-aware indexing | CocoIndex | Tree-sitter chunking by function/class |

---

## 3. Vector Databases

| Project | Language | GitHub Stars | Funding | 2025 Features | Market Position | Link |
|---------|----------|--------------|---------|---------------|-----------------|------|
| **Qdrant** | Rust | **27.7k** | **$37.8M** | High performance + Payload filtering | **Production leader**, 2025 AI TechAward, Cloud Inference (Jul 2025) | [GitHub](https://github.com/qdrant/qdrant) |
| **Chroma** | Rust (v1.0) | 24k | $36M | Zero config, in-memory/persistent | **DevEx leader**, Rust rewrite v1.0 (Mar 2025), 90k+ integrations | [GitHub](https://github.com/chroma-core/chroma) |
| **Weaviate** | Go | ~13k | $50M | **Hybrid search** (BM25 + vector) | Best for code search (exact variable matching) | [GitHub](https://github.com/weaviate/weaviate) |
| **Milvus** | Go | ~32k | $113M | Distributed, billion-scale vectors | Large-scale production leader | [GitHub](https://github.com/milvus-io/milvus) |
| **pgvector** | C | ~13k | - | PostgreSQL extension, ACID | Unified database for Postgres users | [GitHub](https://github.com/pgvector/pgvector) |
| **Pinecone** | Commercial | - | $138M | Fully managed, zero ops | Managed service leader | [pinecone.io](https://pinecone.io) |

### Selection Guide

| Use Case | Recommendation | Notes |
|----------|----------------|-------|
| Production performance | **Qdrant** | $37.8M funding, Rust-based, lowest latency |
| Quick prototyping | **Chroma** | DevEx focus, zero config, Rust v1.0 |
| Code search | Weaviate | Hybrid search for exact variable names |
| Unified database | pgvector | No new infrastructure if using Postgres |
| Billion-scale | Milvus | $113M funding, distributed architecture |

---

## 4. Graph Databases (Knowledge Graphs)

| Project | Type | GitHub Stars | Highlights | LLM Memory Use Case | Link |
|---------|------|--------------|------------|---------------------|------|
| **Graphiti** | Open Source | **~21.2k** | Zep's temporal knowledge graph engine | **LLM-native**, designed for agent memory | [GitHub](https://github.com/getzep/graphiti) |
| **Neo4j** | Commercial/Community | ~14k | Most mature graph database | General-purpose, not LLM-specialized | [neo4j.com](https://neo4j.com) |
| **Memgraph** | Open Source | ~1k | In-memory first, high performance | Real-time graph analytics | [GitHub](https://github.com/memgraph/memgraph) |
| **Kuzu** | Open Source | ~1.5k | Embedded graph database | Local/embedded use cases | [GitHub](https://github.com/kuzudb/kuzu) |

> **Note**: Graphiti's 21.2k stars significantly outpace traditional graph DBs for LLM use cases, indicating strong developer preference for LLM-native solutions.

---

## 5. Embedding Models

| Project | Type | Highlights | Link |
|---------|------|------------|------|
| **OpenAI Embeddings** | Commercial | text-embedding-3-small/large | [openai.com](https://openai.com) |
| **Voyage AI** | Commercial | Code-specialized embeddings | [voyageai.com](https://voyageai.com) |
| **BGE** | Open Source | BAAI, multilingual support | [HuggingFace](https://huggingface.co/BAAI/bge-base-en-v1.5) |
| **Nomic Embed** | Open Source | Long context support | [GitHub](https://github.com/nomic-ai/nomic) |
| **Jina Embeddings** | Open Source | 8K context window | [jina.ai](https://jina.ai) |

---

## 6. Key Trends in 2025

| Trend | Description | Representative Project |
|-------|-------------|------------------------|
| **Graph-Enhanced Memory** | From pure vector similarity to relational reasoning | Mem0g |
| **Temporal Knowledge** | Time-aware context management | Zep Graphiti |
| **Privacy-First** | Open source alternatives to proprietary tools | Void |
| **Syntax-Aware Chunking** | Tree-sitter chunking by function/class | CocoIndex |
| **Hybrid Search** | Keyword + vector search combined | Weaviate |
| **Custom Embeddings** | Training from agent session traces | Cursor |
| **Real-Time Personal Index** | Per-developer independent index | Augment Code |

---

## 7. Recommended for Further Research

Based on existing research (mem0, letta, augment, cursor) and market analysis:

### High Priority (New Technical Direction or Market Leader)

| Project | GitHub Stars | Funding | Why Research |
|---------|--------------|---------|--------------|
| **[Zep + Graphiti](https://github.com/getzep/graphiti)** | 21.2k | $2.3M (YC) | **Temporal knowledge graph** - 2025's new direction for agent memory |
| **[Continue](https://github.com/continuedev/continue)** | 30.4k | $65M | **Open source IDE market leader**, $500M valuation |

### Medium Priority (Infrastructure Leaders)

| Project | GitHub Stars | Funding | Why Research |
|---------|--------------|---------|--------------|
| **[Qdrant](https://github.com/qdrant/qdrant)** | 27.7k | $37.8M | Production vector DB leader, Rust performance |
| **[Chroma](https://github.com/chroma-core/chroma)** | 24k | $36M | DevEx leader, Rust v1.0 rewrite |

### Optional (Niche or Less Differentiated)

| Project | GitHub Stars | Notes |
|---------|--------------|-------|
| **[Tabby](https://github.com/TabbyML/tabby)** | 11k | Self-hosted alternative, but Continue is leader |
| **[Void](https://voideditor.com)** | ~5k | Privacy-first, too new to assess |
| **[CocoIndex](https://github.com/cocoindex/cocoindex)** | ~1k | Tree-sitter niche, small community |

---

## 8. Tech Stack Examples

### Scenario A: Personal Project / Prototype

```
Embedding: OpenAI text-embedding-3-small
Vector DB: Chroma (local)
Memory: LangChain ConversationBufferMemory
```

### Scenario B: Production AI Assistant

```
Embedding: Voyage AI (code-specialized)
Vector DB: Qdrant (high performance)
Memory: Mem0 (user profiles) + Letta (long conversations)
Graph: Neo4j (relational reasoning)
```

### Scenario C: Self-Hosted Code Assistant

```
Codebase Index: Tabby / Continue
Embedding: BGE / Nomic (local)
Vector DB: pgvector (unified database)
LLM: Ollama (local)
```

---

## References

- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [Letta GitHub](https://github.com/letta-ai/letta)
- [Zep GitHub](https://github.com/getzep/zep)
- [Continue GitHub](https://github.com/continuedev/continue)
- [Qdrant GitHub](https://github.com/qdrant/qdrant)
- [Cursor Docs](https://cursor.com/docs)
- [Augment Code Docs](https://docs.augmentcode.com)
