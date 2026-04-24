# Production RAG Stacks & Frameworks Research Report

Last Updated: 2026-04-15

> **Research Methodology**: This document synthesizes official documentation, GitHub repositories, vendor case studies (Perplexity/Vespa, Spotify, Notion), and third-party benchmark/teardown blog posts published through Q1 2026. It is the fourth and final installment in the [retrieval layer research series](./) — cross-link to [chunking.research.md](./chunking.research.md), [embedding-models.research.md](./embedding-models.research.md), and [retrieval-architecture.research.md](./retrieval-architecture.research.md) for the sub-components that each stack composes.

## TL;DR

The 2023-2024 framing — "LlamaIndex for RAG, LangChain for agents, Haystack for enterprise" — has collapsed. In 2026 the useful axes are:

1. **Retrieval-engine stacks** (LlamaIndex, Haystack) vs. **orchestration-graph stacks** (LangGraph) vs. **single-system search engines** (Vespa) vs. **DB-plus-app pattern** (Qdrant / pgvector + code).
2. The dominant production recipe is now **hybrid dense+BM25 + cross-encoder rerank + contextual chunking**, and every serious stack implements it — the differentiator has moved to observability, cost control, and whether the stack becomes infrastructure or just scaffolding.
3. LangChain's "wrapper-of-wrappers" criticism has been partially answered by LCEL + LangGraph 1.0 (Sep 2025), but the criticism has migrated rather than disappeared — see [§ LangChain](#2-langchain--langgraph).

---

## Comparison Matrix

| Dimension | LlamaIndex | LangChain + LangGraph | Haystack 2.x | Vespa | Qdrant + app | Anthropic Contextual Retrieval | Letta (memory) | Mastra |
|---|---|---|---|---|---|---|---|---|
| **Primary abstraction** | `Node` / `Index` / `QueryEngine` / `Retriever` | Runnable (LCEL) + LangGraph `StateGraph` | Pipeline (DAG of `Component`s) | `Schema` + `Rank profile` + YQL | Collections, points, named vectors | Notebook recipe (not a framework) | `MemoryBlock` / `ArchivalMemory` | `Agent` + tools with MCP-first design |
| **Default chunker** | `SentenceSplitter` 1024 tok, 200 overlap | `RecursiveCharacterTextSplitter` 1000/200 | `DocumentSplitter` (word/sentence/page) 200 words | User-defined (field-level) | User-defined (pipeline is BYO) | Prepend 50-100 tok LLM context to each chunk | Inherits archival store default | Inherits underlying vector store |
| **Default embedding** | `text-embedding-3-small` (OpenAI) | Provider-agnostic; `text-embedding-3-small` typical | Provider-agnostic; SBERT-family by default in tutorials | User-supplied (ColBERT, BGE, etc. all first-class) | User-supplied | `voyage-3` or OpenAI in cookbook | `text-embedding-3-small` via pgvector | User-supplied |
| **Native hybrid retrieval** | Yes (`QueryFusionRetriever`, RRF) | Yes (`EnsembleRetriever`) | Yes (pipeline with two retrievers + joiner) | **Yes — single engine, single query** | Yes (named-vector hybrid + Score-Boosting as of 2025) | Yes (dense + BM25 + RRF in recipe) | Partial (archival is vector-only) | Via underlying store |
| **Reranker built-in** | Cohere, Jina, bge, ColBERT postprocessors | `ContextualCompressionRetriever` wrapping any reranker | `SentenceTransformersSimilarityRanker`, Cohere, Jina | Yes — ML ranking is the core feature | No (client must call external) | Cohere Rerank or Voyage rerank in recipe | No | Via ContextualCompression wrappers |
| **Observability / eval** | `Traceloop`, `Arize`, native `instrumentation` module; built-in eval harness | LangSmith (paid) — the strongest in class | Native `Tracer`, RAGAS cookbook | Built-in metrics, ranking replay, A/B | BYO (OpenTelemetry hooks exist) | N/A | Built-in trace viewer in ADE | Built-in telemetry |
| **Production maturity (GitHub ★, Q1 2026)** | ~40k | ~85k (LC) + ~10k (LG) | ~17k | ~6k (but Yahoo-backed since 2003) | ~22k | N/A (recipe) | ~16k | ~13k |
| **Marquee production users** | Notion, Uber, ServiceNow | Klarna, Elastic, Replit (LangGraph) | Airbus, NATO, Deutsche Telekom | **Perplexity, Spotify, Yahoo, Okta** | Qdrant Cloud: Disney, Bosch, Glean | Anthropic internal, docs customers | Letta Cloud, open source agents | Y-Combinator batch '25 agents |
| **Opinionated?** | High | Low (LCEL) / Medium (LangGraph) | Medium | High (within its paradigm) | Low | High (just do the recipe) | High (MemGPT paradigm) | Medium |
| **License** | MIT | MIT | Apache 2.0 | Apache 2.0 | Apache 2.0 | — | Apache 2.0 | Elastic License 2.0 |

Star counts approximated from GitHub Q1 2026 snapshots. LangChain total is misleading because the monorepo bundles dozens of integration packages; LangGraph is the more meaningful number for new projects.

---

## 1. LlamaIndex

### What it handles

- **Chunking**: `SentenceSplitter` (default), `TokenTextSplitter`, `SemanticSplitterNodeParser` (embedding-distance breakpoint detection), `HierarchicalNodeParser` for auto-merging, `CodeSplitter` (tree-sitter), `MarkdownNodeParser`, `JSONNodeParser`.
- **Indexing**: `VectorStoreIndex`, `SummaryIndex`, `KeywordTableIndex`, `KnowledgeGraphIndex`, `PropertyGraphIndex` (2024 replacement for KG index, entity-and-relation-typed), `DocumentSummaryIndex`.
- **Retrieval**: `VectorIndexRetriever`, `BM25Retriever`, `QueryFusionRetriever` (multi-query + RRF), `AutoMergingRetriever` (parent-doc), `RecursiveRetriever` (traverses node references), `ColbertRetriever`.
- **Postprocessing/reranking**: 20+ `NodePostprocessor`s — Cohere, Jina, bge, ColBERT, LongLLMLingua, `SentenceEmbeddingOptimizer`, `MetadataReplacementPostProcessor`.
- **Query engines**: `RetrieverQueryEngine`, `SubQuestionQueryEngine`, `RouterQueryEngine`, `MultiStepQueryEngine`, `SQLAutoVectorQueryEngine`.

### Opinionated defaults

`SentenceSplitter(chunk_size=1024, chunk_overlap=200)`, OpenAI `text-embedding-3-small`, cosine similarity, top-k = 2 (surprisingly conservative), no reranker. The defaults produce something functional in ~5 lines, which is why LlamaIndex owns the "prototype fastest" slot.

### Evolution

Originally a pure indexing library; added `Workflows` in 2024 to compete with LangGraph for agent orchestration (event-driven, step-based). In 2025 rebranded repo tagline to "leading document agent and OCR platform" — significant: the company (LlamaCloud, LlamaParse) is monetizing ingestion, not orchestration. That affects what the OSS prioritizes: the ingestion/parsing layer gets most of the R&D investment, orchestration is catch-up work.

### Extensibility

`BaseRetriever`, `BaseNodePostprocessor`, `BaseEmbedding`, `BaseNodeParser`, `LLM` are all small abstract classes you can subclass in ~20 lines. The composability is a real strength — swap a retriever without rewriting upstream or downstream.

### Typical production deployment

- Notion's doc search uses LlamaIndex-derived patterns (hierarchical node parser + auto-merging retrieval) with a self-hosted vector DB.
- Enterprise PDF search: LlamaParse → `SemanticSplitter` → `VectorStoreIndex` on Qdrant/Pinecone → `QueryFusionRetriever` + Cohere rerank → `RetrieverQueryEngine`. This is the "canonical" LlamaIndex prod stack documented across Medium/DEV articles.

### Limitations / anti-patterns

- The abstraction surface is huge and the names aren't always stable across minor versions (`ServiceContext` → `Settings` migration in 0.10 broke every tutorial on the internet).
- `Response` vs `QueryBundle` vs `NodeWithScore` is at least one object too many.
- Agent/workflow story is behind LangGraph; people who start in LlamaIndex often bolt LangGraph on top rather than use `Workflows`.

---

## 2. LangChain + LangGraph

### What it handles

- **Chunking**: `RecursiveCharacterTextSplitter` (default), `TokenTextSplitter`, `MarkdownHeaderTextSplitter`, `HTMLHeaderTextSplitter`, `Language`-aware (Python/JS/etc.) — but no native semantic chunker at top level (must use experimental).
- **Vectorstores**: 70+ integrations. The criticism is that each is a thin wrapper around the underlying client, often lagging upstream features.
- **Retrievers**: `VectorStoreRetriever`, `MultiQueryRetriever` (LLM-generates query variants), `ContextualCompressionRetriever` (rerank wrapper), `ParentDocumentRetriever` (small-to-big), `SelfQueryRetriever` (LLM writes metadata filter), `EnsembleRetriever` (weighted + RRF), `TimeWeightedVectorStoreRetriever`, `MergerRetriever`.
- **Orchestration**: LCEL (the `|` runnable syntax) for simple pipelines; LangGraph for stateful multi-step agents (became the recommended path in 2024-2025).

### Opinionated defaults

Famously opinion-less. `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` is the most consequential default. There is no default embedding or vectorstore — users must pick.

### 2025-2026 refactors

- **LCEL** cleaned up the pre-2024 "chain-of-chains" explosion (`LLMChain`, `RetrievalQA`, `ConversationalRetrievalChain`), replacing them with composable `Runnable`s.
- **LangGraph 1.0** shipped September 2025. Agents are now expressed as explicit state graphs with checkpointing, human-in-the-loop nodes, durable execution (recover mid-run after crash), time-travel debugging via LangSmith. This is the single biggest API-quality improvement in the LangChain family since 2023.
- **LangGraph Platform**: managed deployment target. Not free, but the value proposition (durable state, replayable runs) is real for agents.

### The "wrapper-of-wrappers" criticism in 2026

The criticism had three prongs:
1. **Too-thin integrations**. Still partly true. `Qdrant`'s LangChain wrapper, for example, doesn't surface ACORN filtered HNSW or Score-Boosting reranking — you drop to the native client for those.
2. **Leaky, drifting abstractions**. LCEL addressed this: fewer classes, more functions, clearer type signatures. `Runnable` protocol is coherent.
3. **Agent code is impossible to debug**. LangGraph + LangSmith replay genuinely solves this. Checkpointing is a real engineering advance.

Net: the criticism is 40% addressed (agents) and 60% still valid (integration layer). New projects should think of LangChain-the-library as "the integration catalog" and LangGraph-the-library as "the agent runtime" — use them separately and selectively, not as a monolithic stack.

### Extensibility

`Runnable` protocol is clean — implementing `invoke`, `batch`, `stream`, `astream` gives you a LangGraph-compatible component. Retriever base class is tiny.

### Typical production deployment

- Klarna's customer-support agent is the most-cited LangGraph production case (2024 press).
- Replit's agent system uses LangGraph for orchestration.
- Elastic integrates LangChain retrievers into ES|QL workflows.

### Limitations / anti-patterns

- Still easy to build something that only works with LangChain primitives, creating lock-in for a framework that is not itself a stable contract.
- Debugging without LangSmith (paid) is painful.
- The LCEL `|` syntax is beautiful for two-step pipelines and unreadable for anything nontrivial — which pushes you into LangGraph, which pushes you into LangSmith.

---

## 3. Haystack (deepset)

### What it handles

- **Pipeline model**: DAG of `Component`s connected by explicit input/output sockets. Unlike LangChain's runnable protocol, Haystack pipelines are validated at build time — type mismatches fail before any LLM call.
- **Retrieval components**: `InMemoryEmbeddingRetriever`, `InMemoryBM25Retriever`, `ElasticsearchBM25Retriever`, `QdrantEmbeddingRetriever`, `WeaviateBM25Retriever`, `PineconeDenseRetriever`, and ~20 vectorstore-specific retrievers.
- **Rerankers**: `TransformersSimilarityRanker`, `CohereRanker`, `JinaRanker`, `SentenceTransformersSimilarityRanker`.
- **Generators/chat**: `OpenAIChatGenerator`, `AnthropicChatGenerator`, `HuggingFaceLocalGenerator`, NIM-compatible.
- **Agents**: `Agent` component (added 2024), plus tool-calling via `ToolInvoker`.
- **2025 additions**: `AsyncPipeline` for parallel component execution; `SuperComponent` to wrap sub-pipelines as reusable nodes.

### Opinionated defaults

Medium-opinionated. Tutorials default to SBERT family (`all-MiniLM-L6-v2`) and `DocumentSplitter(split_by="word", split_length=200)`. There is an opinion about pipeline structure (hybrid retrieve → join → rank → prompt → generate is the canonical template) but not about which models.

### Extensibility

Any Python function with type-annotated inputs/outputs becomes a component via `@component`. The connect-time validation is the single most developer-friendly thing in Haystack — it catches entire classes of errors LangChain users debug at runtime.

### Typical production deployment

- deepset Cloud (their managed product) hosts the pipelines for enterprise customers.
- Airbus, NATO, Deutsche Telekom are the publicly cited enterprise users — pattern is document-heavy regulated industries where audit trail and component boundaries matter more than the latest shiny integration.
- `hybrid_rag_pipeline_with_breakpoints` is the reference cookbook: dense retriever || BM25 retriever → `DocumentJoiner` → `SimilarityRanker` → `ChatPromptBuilder` → `OpenAIChatGenerator`.

### Comparison to LangChain

| | Haystack | LangChain |
|---|---|---|
| Pipeline validation | Compile-time | Runtime |
| Integration breadth | Narrower, higher quality per integration | Broadest in industry |
| Agent story | Simpler, less mature than LangGraph | LangGraph is the leader |
| Dev experience | Explicit, verbose | Implicit, terse |
| Learning curve | Higher upfront, flat afterwards | Low upfront, rises with complexity |

Haystack wins where **predictability and observability** matter more than integration breadth. For enterprise RAG with strict uptime requirements, Haystack's DAG model is a better fit; for rapid agent prototyping, LangGraph.

### Limitations / anti-patterns

- Smaller community → fewer third-party components → more custom code than LangChain for exotic integrations.
- The DAG model is clunky for highly dynamic agent loops; you end up embedding an `Agent` component but losing some of the graph-level validation.

---

## 4. Vespa

### What it handles

**Everything in one process.** Vespa is not a RAG framework that uses a vector DB — it **is** the search engine. Single system handles:
- Ingestion (with field-level embedders, including ColBERT native support)
- Hybrid retrieval: vector + BM25 + structured filters + tensor math in one query expression
- ML ranking: first-phase and second-phase rankers can be XGBoost, ONNX neural models, or cross-encoders running in-process
- Real-time indexing with sub-second visibility
- Grouping, aggregation, personalization

The `rank profile` abstraction is what makes Vespa different: you write a ranking function combining `nativeRank(text) + 0.3 * closeness(embedding) + onnx_model(features)`, compile it, and Vespa runs it across shards.

### Opinionated defaults

Opinionated about the paradigm (declarative schema + rank profiles) but unopinionated about models. You pick your embedder, your ranker, your tokenization.

### Why Yahoo/Spotify/Perplexity use it

- **Perplexity** migrated its search backend to Vespa in 2025 — at 22M active users and 780M monthly queries, the DIY-pipeline + vector DB approach becomes operationally untenable. Vespa runs the hybrid-retrieve-and-ML-rank workload in one process, eliminating the network hops between retrieval stage and reranker that dominate tail latency in naive stacks.
- **Spotify** uses Vespa for both search and recommendation, because the same platform serves both workloads (full-text, personalized ranking, real-time signals).
- **Yahoo** originally built Vespa internally; it has been in production since ~2003.

### Extensibility

ONNX models, XGBoost models, custom `searcher` plugins in Java, custom `document processors`. More extensible than most people think, but the entry point is steep.

### Typical production deployment

Self-hosted cluster or Vespa Cloud. Not a "run in a notebook" product. Typical deployment: 3+ content nodes, 2+ stateless container nodes, separate config cluster. Billions of documents, tens of thousands of QPS.

### Limitations / anti-patterns

- Learning curve is by far the steepest in this list. YQL, rank profile DSL, services.xml, deployment packages — it's a full platform.
- Overkill below ~10M documents or <100 QPS. The DIY + Qdrant pattern will be cheaper and easier.
- Java/JVM-centric plugin model in a Python-centric ML ecosystem is friction.

---

## 5. Qdrant + app layer

### The pattern

"Pure vector DB + thin application-layer orchestration." The application code (Python, Go, TS) does chunking, embedding, retrieval calls, and reranking without a framework. Qdrant handles storage, indexing, filtering, and increasingly — server-side hybrid retrieval.

### What Qdrant handles natively (2026)

- Dense + sparse vectors in same collection (named vectors)
- Hybrid search with RRF or DBSF fusion, server-side
- ACORN filtered HNSW (high-quality filtered queries, 2025 release)
- Score-Boosting Reranking (blend vector similarity with business signals)
- MMR (Maximal Marginal Relevance) for diversity
- Full-text filtering with multilingual tokenization, stemming, phrase matching (2025)
- Built-in embedding inference in Qdrant Cloud (send raw text, get search results — blurs the "pure DB" framing)
- Quantization (scalar, binary, product)

Qdrant raised a $50M Series B in 2026 on the "composable vector search" pitch — the positioning is explicitly that the database, not a framework, is the composition point.

### Why pick this pattern

- **You own the pipeline**. No framework abstractions, no upgrade treadmill.
- **Swap embedders freely** without framework approval.
- **Production debugging is just reading your own code + Qdrant logs.**
- **Qdrant Cloud** offers a managed path if you don't want to run Rust + gRPC yourself.

### Typical deployment

```
text → (chunker: custom)
     → (embedder: OpenAI/Voyage/BGE via direct API)
     → Qdrant Collection (dense + sparse named vectors)
     → Query: dense + sparse + filter, fused server-side
     → (reranker: Cohere/Jina via direct API)
     → prompt → LLM
```

Notion-scale and Glean-scale teams tend to land on this pattern after outgrowing LangChain-the-framework while staying below Vespa-scale complexity.

### Limitations / anti-patterns

- No "guided rails" — you must know what a good pipeline looks like. Bad news for teams without a retrieval-savvy engineer.
- No observability framework out of the box — you wire OpenTelemetry yourself.
- You reinvent things every stack has: chunking, dedup, upsert management. Can be a feature (you know exactly what runs) or a bug (you wrote it on a Tuesday and it has edge cases).

---

## 6. Anthropic Contextual Retrieval (reference implementation)

### What it is

Not a framework. A **cookbook recipe** (September 2024, Anthropic blog + `anthropics/claude-cookbooks` GitHub) that specifies a concrete pipeline:

1. Split document into chunks (typical: 800 tokens).
2. For each chunk, prompt Claude with the full document + the chunk, asking for a 50-100 token context snippet that situates the chunk ("This chunk is from the Q2 financial report, section on EMEA revenue…").
3. Prepend that context to the chunk before embedding (`contextual embedding`) and before BM25 indexing (`contextual BM25`).
4. Retrieve with hybrid: top-150 candidates via RRF of dense + BM25.
5. Rerank with Cohere Rerank or Voyage Rerank to top-20.
6. Feed top-20 to the LLM.

### Reported results

49% reduction in top-20 chunk retrieval failure rate versus naive dense-only. With prompt caching, the one-time cost to generate contextualized chunks is ~$1.02 per million document tokens.

### Why it matters for the stacks discussion

Every framework on this page **now has a contextual retrieval cookbook**:
- LlamaIndex: `docs/examples/cookbooks/contextual_retrieval.ipynb`
- Haystack: pipeline pattern in their docs
- LangChain: multiple community notebooks
- Instructor: async-processing blog post with structured output validation
- Together AI: hosted pattern

This is the clearest case of a technique **winning the ecosystem**. If you're picking a stack in 2026, the real question is "how painful is it to implement contextual retrieval here" — by that metric, all the mature stacks are roughly equivalent.

### Limitations

- Doubles ingestion cost (the per-chunk LLM call).
- Without prompt caching, cost is prohibitive — this recipe is implicitly Claude-pilled.
- Quality of the prepended context matters — a bad prompt produces verbose filler that hurts BM25 more than it helps.

---

## 7. Emerging 2025-2026 stacks

### Letta

Not a RAG framework; a **stateful-agent memory framework** (MemGPT lineage). Retrieval is secondary: memory blocks (always-in-context) for hot state, archival memory (vector-indexed) for cold. Notable 2025-2026 move: `Memfs` (context repositories) positioned as successor to both memory blocks and archival memory — but currently supports only exact-match search, no semantic search, which is a regression for retrieval use cases. Pick Letta if you want MemGPT-style agent memory, not if you want a general RAG stack.

### Mastra

TypeScript/Node-native agent framework, MCP-first. Pitches itself as "LangGraph for TS" with lighter ceremony. Retrieval is via underlying vector store integrations (Pinecone, Qdrant, pgvector, Chroma). Y-Combinator batch '25 traction; real but unproven at large scale. Worth watching if your stack is Next.js and you're allergic to Python.

### Instructor + pgvector

Not a framework per se — a **pattern**. Use Instructor (structured output via Pydantic) for all LLM calls including the chunk-context step of contextual retrieval; store in pgvector; write the retrieval pipeline as plain Python. Appeals to teams that already run Postgres, don't want another service, and care more about typed outputs than framework features. The [Instructor async contextual-retrieval blog post](https://python.useinstructor.com/blog/2024/09/26/implementing-anthropics-contextual-retrieval-with-async-processing/) is the canonical reference.

### RAGFlow, Verba, Morphik

OSS "batteries-included" RAG apps, usually fronted by a Web UI. Positioned against enterprise teams that want a product rather than a library. Useful to evaluate as reference implementations; probably not what you build on as a platform.

### DSPy

Not a RAG stack but a **programming model for prompts**. Increasingly used as the outer layer of a RAG pipeline — you declare the retrieve-rerank-answer flow as signatures and let DSPy optimize the prompts/few-shots. Complementary to, not replacement for, the stacks above.

---

## Key Questions

### LlamaIndex vs LangChain in 2026: has the "wrapper-of-wrappers" criticism been addressed?

**Partially.**

- LCEL simplified the inner composition story and killed the worst offenders (`LLMChain`, `ConversationalRetrievalChain`). This genuinely addresses the criticism at the composition layer.
- LangGraph added a coherent agent runtime that replaces the previous agent-as-chain mess. This genuinely addresses the criticism at the agent layer.
- The integration catalog still consists of thin wrappers that lag upstream features, and upgrading LangChain major versions still breaks tutorials. This part of the criticism is not addressed and probably cannot be — it's inherent to being the integration Schelling point.

LlamaIndex doesn't face the same criticism because it wasn't trying to be a universal wrapper — it was a retrieval library that grew. But it has its own equivalent: API surface bloat, naming churn (`ServiceContext` → `Settings`), and the `Node` / `NodeWithScore` / `BaseNode` / `TextNode` hierarchy that nobody can remember.

**Verdict**: LangChain's criticism has moved one layer up (from "their chains are a mess" to "their integrations are leaky"), which is progress. LlamaIndex's equivalent criticism ("too many concepts") has gotten worse, not better, as they added Workflows, Agents, and PropertyGraphs. In 2026, neither framework is embarrassing to pick, but both will make you write adapter code at the edges.

### When should someone pick Vespa over DIY pipeline + Qdrant?

Pick Vespa when you can check **three or more** of:

- \>10M documents, or >100 QPS sustained, or <50ms p99 retrieval latency requirement
- Need real-time indexing (sub-second visibility)
- Need ML ranking with hundreds of signals (personalization, business signals, multi-model ensembles)
- Already have a Java/JVM team, or acceptable to hire for one
- Retrieval is the product (search engine, answer engine, recommender) rather than a component of something bigger

Pick Qdrant + app when:
- Any of the above are "no"
- You want to iterate on the retrieval pipeline weekly
- Your team is Python-first and you want to stay there
- The pipeline is part of a broader agent system, not a standalone search product

Perplexity is the canonical "graduated from DIY to Vespa" case study — but they did so only after hitting scale where the DIY cost was an engineering liability.

### What's the "right default stack" to recommend for a new project in 2026?

Depends on project shape. Three recommendations:

**(a) "I'm a small team, I want to build a RAG product, I don't know what I need yet"**

**LlamaIndex + Qdrant + Cohere Rerank + Anthropic Contextual Retrieval pattern.** Fastest to production with good defaults. You get hierarchical chunking, auto-merging retrieval, RRF, and a reranker out of the box. Qdrant scales with you and you can rip out LlamaIndex later if it becomes a constraint (the data stays in Qdrant).

**(b) "I'm building an agent, RAG is one tool"**

**LangGraph for orchestration + (LlamaIndex retriever OR custom Qdrant pipeline) behind a LangChain `Tool`.** This is the production "power move" pattern — LangGraph for state and control flow, something else for retrieval. Do not build retrieval inside LangGraph itself; treat retrieval as a tool the graph calls.

**(c) "I'm building a search product that is the company"**

**Vespa.** You will pay the upfront learning cost, and that cost is real, but every other option has a scale wall you will hit within 18 months. The Perplexity migration is the cautionary tale: they built the simpler stack first and paid the migration cost later.

**What not to pick**:
- Don't pick LangChain-the-library as your primary retrieval abstraction in 2026. Use it as a tool catalog or don't use it.
- Don't pick a batteries-included OSS RAG app (RAGFlow, Verba) as your platform; use them as reference implementations.
- Don't pick Haystack unless you are in a regulated/enterprise setting that values explicit DAG validation over ecosystem breadth.
- Don't build on Letta if your use case is document RAG — it's an agent-memory framework.

---

## Cross-references

- [chunking.research.md](./chunking.research.md) — semantic vs fixed-size, late chunking, parent-child hierarchies. Every stack in this doc sits on top of a chunking strategy; the comparison matrix's "Default chunker" row is where stack defaults meet that doc's techniques.
- [embedding-models.research.md](./embedding-models.research.md) — bi-encoder vs ColBERT vs Matryoshka. Stacks that natively support ColBERT (Vespa first-class, LlamaIndex via postprocessor) vs those that don't (LangChain retrievers mostly assume single-vector) is a real differentiator.
- [retrieval-architecture.research.md](./retrieval-architecture.research.md) — hybrid retrieval, rerankers, query rewriting. This doc is the "stack" view; that doc is the "algorithm" view of the same space.

## Sources

- [LangChain vs LlamaIndex 2026 production comparison (Prem.ai)](https://blog.premai.io/langchain-vs-llamaindex-2026-complete-production-rag-comparison/)
- [Production RAG in 2026: LangChain vs LlamaIndex (Rahul Kolekar)](https://rahulkolekar.com/production-rag-in-2026-langchain-vs-llamaindex/)
- [LlamaIndex vs LangChain (IBM Think)](https://www.ibm.com/think/topics/llamaindex-vs-langchain)
- [LlamaIndex SentenceSplitter API reference](https://docs.llamaindex.ai/en/stable/api_reference/node_parsers/sentence_splitter/)
- [LlamaIndex Semantic Splitter reference](https://developers.llamaindex.ai/python/examples/node_parsers/semantic_chunking/)
- [LlamaIndex Contextual Retrieval cookbook](https://docs.llamaindex.ai/en/stable/examples/cookbooks/contextual_retrieval/)
- [LangChain LCEL / LangGraph evolution (Binaryverse)](https://binaryverseai.com/langchain-vs-langgraph-decision-guide-framework/)
- [LangChain vs LangGraph practical guide (eesel AI)](https://www.eesel.ai/blog/langchain-vs-langgraph)
- [Haystack docs — Pipelines](https://docs.haystack.deepset.ai/docs/pipelines)
- [Haystack First RAG Pipeline tutorial](https://haystack.deepset.ai/tutorials/27_first_rag_pipeline)
- [Haystack Hybrid RAG Pipeline cookbook](https://haystack.deepset.ai/cookbook/hybrid_rag_pipeline_with_breakpoints)
- [Haystack GitHub repo](https://github.com/deepset-ai/haystack)
- [Vespa — AI Search Platform](https://vespa.ai/)
- [Perplexity on Vespa case study](https://vespa.ai/perplexity/)
- [Perplexity × Vespa partnership announcement (BusinessWire, Apr 2025)](https://www.businesswire.com/news/home/20250415258066/en/Perplexity-Partners-With-Vespa.ai-to-Bring-its-Search-Function-In-House)
- [Vespa benchmarks](https://vespa.ai/benchmarks/)
- [Qdrant 2025 Recap](https://qdrant.tech/blog/2025-recap/)
- [Qdrant $50M Series B announcement](https://www.hpcwire.com/bigdatawire/this-just-in/qdrant-raises-50m-series-b-to-define-composable-vector-search-as-core-infrastructure-for-production-ai/)
- [Building production RAG with LlamaIndex + Qdrant (Arun Brahma)](https://medium.com/@iamarunbrahma/building-a-production-grade-rag-document-ingestion-pipeline-with-llamaindex-and-qdrant-08f4ea1c03c1)
- [Anthropic Contextual Retrieval announcement](https://www.anthropic.com/news/contextual-retrieval)
- [Anthropic Contextual Retrieval cookbook](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide)
- [Implementing Anthropic Contextual Retrieval with Instructor (async)](https://python.useinstructor.com/blog/2024/09/26/implementing-anthropics-contextual-retrieval-with-async-processing/)
- [Together AI contextual RAG how-to](https://docs.together.ai/docs/how-to-implement-contextual-rag-from-anthropic)
- [Letta Memory System (DeepWiki)](https://deepwiki.com/letta-ai/letta/3-memory-system)
- [Letta Archival Memory docs](https://docs.letta.com/guides/agents/archival-memory/)
- [Letta Memory Blocks blog post](https://www.letta.com/blog/memory-blocks)
- [Haystack vs LangChain vs LlamaIndex 2026 (Index.dev)](https://www.index.dev/skill-vs-skill/ai-langchain-vs-llamaindex-vs-haystack)
- [Top LangChain Alternatives 2026 (Scrapfly)](https://scrapfly.io/blog/posts/top-langchain-alternatives)
- [RAG Frameworks comparison (AIMultiple)](https://research.aimultiple.com/rag-frameworks/)
