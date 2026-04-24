# Retrieval Layer Research Summary (2026)

Last Updated: 2026-04-15

Synthesis of 4 research docs on the retrieval/embedding layer — the stack that sits below "vector DB" product choices (Qdrant, Chroma) and determines retrieval quality regardless of backend.

Source files:
- `retrieval/chunking.research.md`
- `retrieval/embedding-models.research.md`
- `retrieval/retrieval-architecture.research.md`
- `retrieval/production-stacks.research.md`

---

## 1. Headline findings

| Claim | Verdict | Source |
|-------|---------|--------|
| Semantic chunking beats naive fixed-size | **Mostly hype** — three independent benchmarks show parity or loss | NAACL 2025, Vecta 2026, Chroma 2024 |
| Contextual Retrieval (Anthropic) is worth adding | **Yes, highest-ROI technique** — -35% failures alone, -67% with BM25 + reranker | Anthropic cookbook, Milvus/LlamaIndex reproductions |
| Late chunking (Jina) helps | **Only on long docs with cross-chunk semantics** (legal / narrative) | Jina benchmarks |
| Code needs AST chunking | **Yes, +4.3 Recall@5** vs character split | cAST on RepoEval |
| HyDE query rewriting | **2023 artifact** — modern supervised embedders collapse the gain | retrieval-arch doc |
| 2-stage rerank pipeline | **Highest ROI addition** — +5-6 nDCG@10 / tens-of-ms | Cohere, Jina, BGE benchmarks |
| GraphRAG (Microsoft) | **Rarely worth cost in 2026** — only global sensemaking + multi-hop entity | retrieval-arch doc |
| ColBERT late interaction | **Narrowed use** — direct use rare, but MaxSim powers ColPali for PDFs | embedding-models doc |
| Matryoshka embeddings | **Effectively free** — now standard on all frontier models | OpenAI/Nomic/Jina/Voyage/Gemini all ship MRL |
| Open-weight vs closed-API gap | **1-2 MTEB points** — Qwen3-Embedding-8B open leader at ~77 | MTEB leaderboard |
| Long context replaces RAG? | **Under ~500K tokens, yes** — prompt caching makes long context cheaper | retrieval-arch doc |

---

## 2. The default 2026 stack

**For long-document RAG**:
```
structure-aware recursive chunking (~1K tokens + 10% overlap)
    ↓
Contextual Retrieval (prepend doc context; cache at ~$1.02/M tokens)
    ↓
hybrid BM25 + dense (RRF fusion)
    ↓
cross-encoder reranker (Cohere Rerank v3.5 / Jina v2 / BGE-v2.5)
    ↓
LLM with prompt cache
```

Beats every semantic-chunking configuration in the surveyed benchmarks.

**For conversation memory** (ChatGPT / Claude / Hindsight style):
- Do NOT use document-chunking techniques
- Retrieval unit is the turn or LLM-extracted fact (propositional chunking applied to dialog)
- Token-size chunking is irrelevant — turns are already small
- Use keyword + vector hybrid over extracted facts

**For code repos**:
- AST-based chunking (cAST, tree-sitter)
- Character-splitting is catastrophic
- grep/ripgrep often beats vector retrieval for exact-symbol lookup

---

## 3. When NOT to build a retrieval pipeline

Under these conditions, long-context LLM + prompt caching beats RAG on cost and quality:
- Corpus ≤ 500K tokens
- No strict recency / freshness requirements
- Single-tenant or small multi-tenant
- Model supports prompt caching (Claude, Gemini, GPT)

At 2026 prices, prompt-cached reads are ~1/10 of regular input tokens. A 500K corpus repeatedly queried costs less than an OSS RAG stack's operational overhead.

---

## 4. Stack selection guide

| Scenario | Pick |
|----------|------|
| Small team, RAG product, unknown requirements | **LlamaIndex + Qdrant + Cohere Rerank + Contextual Retrieval** |
| Agent where RAG is one of many tools | **LangGraph for orchestration + retrieval behind a Tool** (do NOT build retrieval inside LangGraph) |
| Search-is-the-product at scale (10M+ docs, 100+ QPS, ML ranking) | **Vespa** |
| Enterprise / regulated | Haystack (deepset) |
| Dayfold-style single-user small corpus, LIKE-sufficient | Keep current design; add reranker only if retriever Phase 4 eval shows precision issue |

**Avoid**:
- LangChain as primary retrieval abstraction (wrapper-of-wrappers issue ~60% still valid after LCEL + LangGraph 1.0)
- Batteries-included OSS RAG apps as platforms (brittle)
- Letta for document RAG (it's a memory agent framework, not RAG)

---

## 5. Open questions

1. **Do rerankers generalize?** Cohere/Jina rerankers are trained on general web QA — does cross-encoder scoring hold up on domain-specific text (legal, medical, code) without fine-tuning?
2. **ColPali for text docs?** ColPali handles PDFs as images. Could this replace text-only embedding + OCR pipelines entirely?
3. **Is Contextual Retrieval's 67% gain stable across domains?** Anthropic's reproduction is on mixed corpora; unclear for narrow domains.
4. **When does "let the LLM retrieve" (Supermemory ASMR, Claude conversation_search) beat pipeline retrieval?** No benchmark directly compares these paradigms.

---

## 6. Tie-back to memory research

Retrieval and memory share mechanisms but differ in scope:

| Aspect | Memory retrieval | Document retrieval |
|--------|------------------|--------------------|
| Unit | Fact / note / turn | Chunk |
| Update | High-write (new facts arrive constantly) | Low-write (corpus mostly static) |
| Noise | Low — curated by extraction | Medium — raw document text |
| Latency budget | Strict (conversation flow) | Flexible (user search) |
| Evaluation | LongMemEval / LoCoMo | BEIR / MTEB |
| Winning stack 2026 | LLM-as-retriever (Supermemory) OR compression-only (Mastra) | Contextual Retrieval + hybrid + rerank |

The retrieval layer's SOTA techniques (hybrid, rerank, Contextual Retrieval) **mostly don't apply to memory systems** because memory retrieval units are already curated. Memory retrieval is closer to keyword lookup over a well-maintained index than to semantic search over raw documents.

This matches our engineering-side finding (Findings §10): text search dominates over RAG in practice within agentic loops — because the content has already been curated upstream.
