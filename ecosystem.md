# LLM Memory Ecosystem: Products & Open Source Projects

Last Updated: 2025-12-18

> **Research Methodology**: Combined Claude Code analysis + Gemini CLI internet search

---

## 1. Memory Frameworks

| Project | Type | Core Technology | 2025 Updates | Link |
|---------|------|-----------------|--------------|------|
| **Mem0** | Open Source | LLM-driven fact extraction + Vector/Graph dual storage | **Mem0g** - Graph database for relational reasoning | [GitHub](https://github.com/mem0ai/mem0) |
| **Letta** (MemGPT) | Open Source | Three-tier memory + Agent self-editing prompts | Supports "infinite context" chatbots | [GitHub](https://github.com/letta-ai/letta) |
| **Zep** | Open Source | Long-term memory + Auto-summarization + Entity extraction | **Graphiti** temporal knowledge graph engine | [GitHub](https://github.com/getzep/zep) |
| **LangChain Memory** | Open Source | Multiple Memory types (Buffer, Summary, VectorStore) | Most complete ecosystem, but generic | [GitHub](https://github.com/langchain-ai/langchain) |
| **LlamaIndex** | Open Source | Data indexing framework, multiple storage backends | Best for RAG scenarios | [GitHub](https://github.com/run-llama/llama_index) |
| **Motorhead** | Open Source | Memory server with Redis backend | Lightweight option | [GitHub](https://github.com/getmetal/motorhead) |

### Selection Guide

| Use Case | Recommendation |
|----------|----------------|
| Infinite context chat | Letta |
| Smart user profiles | Mem0 or Zep |
| Temporal-aware memory | Zep (Graphiti) |
| Quick prototyping | LangChain Memory |

---

## 2. AI Coding Assistants (Codebase Indexing)

| Project | Type | Core Technology | Highlights | Link |
|---------|------|-----------------|------------|------|
| **Cursor** | Commercial | AST + Symbol graph + Semantic embeddings | 2025 benchmark, custom embedding models | [cursor.com](https://cursor.com) |
| **Augment Code** | Commercial | Context Engine + Real-time personal index | Per-developer index, sub-second updates | [augmentcode.com](https://augmentcode.com) |
| **Void** | Open Source | Cursor-like features | **Privacy-first**, runs locally or with your own API keys | [voideditor.com](https://voideditor.com) |
| **Continue** | Open Source | Customizable Context Providers | Supports local LLMs (Ollama), highly configurable | [GitHub](https://github.com/continuedev/continue) |
| **Tabby** | Open Source | RAG + repo-context indexing | Self-hosted Copilot alternative | [GitHub](https://github.com/TabbyML/tabby) |
| **Aider** | Open Source | Git-aware multi-file editing | Terminal tool, ideal for CLI users | [GitHub](https://github.com/paul-gauthier/aider) |
| **Sourcegraph Cody** | Open Source | Enterprise code search | Cross-repository search support | [GitHub](https://github.com/sourcegraph/cody) |
| **CocoIndex** | Open Source | **Tree-sitter** syntax-aware chunking | Chunks by function/class, live index updates | [GitHub](https://github.com/cocoindex/cocoindex) |

### Selection Guide

| Use Case | Recommendation |
|----------|----------------|
| Privacy-first open source | Void |
| Highly configurable | Continue |
| Self-hosted enterprise | Tabby |
| Syntax-aware indexing | CocoIndex |
| CLI users | Aider |

---

## 3. Vector Databases

| Project | Language | 2025 Features | Best For | Link |
|---------|----------|---------------|----------|------|
| **Qdrant** | Rust | High performance + Payload filtering (user_id, timestamp) | Production, low latency at scale | [GitHub](https://github.com/qdrant/qdrant) |
| **Chroma** | Python | Zero config, in-memory/persistent modes | Prototyping, quick start | [GitHub](https://github.com/chroma-core/chroma) |
| **Weaviate** | Go | **Hybrid search** (BM25 + vector) | Code search (exact variable matching) | [GitHub](https://github.com/weaviate/weaviate) |
| **Milvus** | Go | Distributed, billion-scale vectors | Large-scale production | [GitHub](https://github.com/milvus-io/milvus) |
| **pgvector** | C | PostgreSQL extension, ACID transactions | Teams already using Postgres | [GitHub](https://github.com/pgvector/pgvector) |
| **Pinecone** | Commercial | Fully managed, zero ops | No infrastructure management | [pinecone.io](https://pinecone.io) |

### Selection Guide

| Use Case | Recommendation |
|----------|----------------|
| Production performance | Qdrant |
| Quick prototyping | Chroma |
| Code search | Weaviate (hybrid search) |
| Unified database | pgvector |
| Large-scale distributed | Milvus |

---

## 4. Graph Databases (Knowledge Graphs)

| Project | Type | Highlights | Link |
|---------|------|------------|------|
| **Neo4j** | Commercial/Community | Most mature graph database | [neo4j.com](https://neo4j.com) |
| **Memgraph** | Open Source | In-memory first, high performance | [GitHub](https://github.com/memgraph/memgraph) |
| **Kuzu** | Open Source | Embedded graph database | [GitHub](https://github.com/kuzudb/kuzu) |
| **Graphiti** | Open Source | Zep's temporal knowledge graph engine | [GitHub](https://github.com/getzep/graphiti) |

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

Based on existing research in this project (mem0, letta, augment, cursor):

| Project | Research Value |
|---------|----------------|
| **[Zep + Graphiti](https://github.com/getzep/graphiti)** | Temporal knowledge graph is a new direction |
| **[Continue](https://github.com/continuedev/continue)** | Most active open source coding assistant |
| **[Void](https://voideditor.com)** | Privacy-first Cursor alternative |
| **[CocoIndex](https://github.com/cocoindex/cocoindex)** | Tree-sitter syntax-aware indexing |

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
