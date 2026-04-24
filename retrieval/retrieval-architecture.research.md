# Retrieval Architecture Patterns

Last Updated: 2026-04-15

> **Research Methodology**: Synthesis of primary sources (Anthropic engineering blogs, Microsoft GraphRAG repository, LangChain/LlamaIndex retriever code, and arxiv papers for HyDE, Self-RAG, HippoRAG, LightRAG) with benchmark results from BEIR, MTEB, LongMemEval, LoCoMo, and RAGTruth. The focus is on **full pipeline assembly** — how components compose into production systems — not on individual parts (for those, see the sibling docs below).

**Sibling documents** (do not duplicate):
- `retrieval/chunking.research.md` — segmentation strategies (fixed, recursive, semantic, late chunking, propositional)
- `retrieval/embedding-models.research.md` — bi-encoder vs ColBERT vs Matryoshka vs SPLADE

This document covers the **architecture above embeddings**: how retrieval is composed, reranked, rewritten, graph-augmented, and when to skip it entirely.

---

## 0. The 2026 Baseline Pipeline

By early 2026 the "generic production RAG" stack has converged on a roughly stable shape, even though individual components still move every quarter:

```
User Query
    │
    ▼
[ Query Understanding ]   (optional: rewrite, expand, decompose)
    │
    ▼
[ Hybrid First-Stage Retrieve ]   BM25  +  Dense  (+ metadata filter)
    │        (k = 50–200 candidates)
    ▼
[ Fusion ]  RRF / weighted / DBSF
    │
    ▼
[ Cross-Encoder Rerank ]   (top 10–30 output)
    │
    ▼
[ LLM / Generator ]   (optional: self-reflective loop, cite/verify)
```

The interesting question is no longer "should I use RAG"; it is **which layers to include, in what order, with what budget**. The rest of this document walks each layer.

---

## 1. Hybrid Retrieval (BM25 + Dense)

### 1.1 Mechanism

Hybrid retrieval runs a lexical retriever (BM25/tsvector/learned-sparse) and a dense vector retriever in parallel, then fuses the two ranked lists. Three fusion methods dominate:

**Reciprocal Rank Fusion (RRF)**, Cormack et al. 2009:
```
score(d) = Σ_i  1 / (k + rank_i(d))
```
with `k = 60` as the canonical constant. It is **score-free** — only ranks are used — which makes it robust across retrievers with incomparable score distributions. RRF is the default in Elasticsearch, OpenSearch, Qdrant Query API, Weaviate, and LangChain's `EnsembleRetriever`.

**Weighted Sum / Convex Combination**:
```
score(d) = α · norm(bm25_score) + (1-α) · norm(dense_score)
```
Requires min-max or z-score normalization. More expressive than RRF when tuned, but brittle when distributions shift (new corpora, new query types).

**Distribution-Based Score Fusion (DBSF)**, Qdrant 2024:
Normalizes each retriever's scores to its own mean/stddev, then averages. Handles tail-heavy score distributions better than min-max. Available natively in Qdrant ≥1.10.

### 1.2 Empirical gains

On BEIR (18 retrieval tasks), hybrid BM25+dense consistently beats either alone by **2–7 nDCG@10 points**:

| Retriever | BEIR avg nDCG@10 |
|---|---|
| BM25 alone | 42.7 |
| Dense (E5-large) | 50.0 |
| Hybrid RRF | **53.8** |
| Hybrid + cross-encoder rerank | **57.2** |

(Numbers from the BGE/E5 papers and the BEIR leaderboard, 2024.) The gain is largest on **entity-heavy / out-of-domain** corpora (SciFact, FiQA, Touche) where BM25 catches exact terms dense embeddings smooth over.

### 1.3 When each wins

- **BM25 wins**: rare named entities, code identifiers, product SKUs, multi-lingual corpora where dense model wasn't trained on the target language, strict recall requirements on exact wording.
- **Dense wins**: paraphrased queries, abstract/conceptual questions, cross-lingual retrieval with a cross-lingual encoder.
- **Hybrid wins**: anything mixed (i.e. most real systems). The marginal cost is one extra index and one extra query; the tail risk of BM25-only or dense-only failing catastrophically on a query type is eliminated.

### 1.4 Cost overhead

Negligible. Both queries run in parallel; the fusion step is O(k) sort. Index-side, BM25 adds ~20–40% storage over a dense-only index (posting lists). Qdrant, Vespa, and Elasticsearch all run hybrid in a single request.

### 1.5 Production systems using it

Anthropic Contextual Retrieval (Section 5), Hindsight (4-way including BM25 + dense), LlamaIndex `QueryFusionRetriever` default, Vespa's native rank profiles, Perplexity's public stack (BM25+dense+rerank per 2025 blog), GitHub Copilot's code search.

### 1.6 Recommendation

**Always hybrid.** The "should I use hybrid" debate ended in 2024. Default to RRF with `k=60`; only move to weighted/DBSF if you can tune on real query logs.

---

## 2. Query Rewriting and Expansion

Modifying the query before retrieval. Four common patterns:

### 2.1 HyDE — Hypothetical Document Embeddings

Gao et al. 2022 (arxiv 2212.10496). Ask an LLM to hallucinate a plausible answer document, embed that, and retrieve against it.

```
query → LLM("write a passage that answers this") → fake_doc → embed → search
```

**The 2023 hype vs 2026 reality.** HyDE showed nice gains on BEIR zero-shot retrieval with unsupervised Contriever (up to +10 nDCG@10 on some tasks). But:

- With a **good supervised embedder** (E5, BGE, Voyage, Cohere v3/v4), HyDE's lift shrinks to **+0 to +2 nDCG@10**, and often loses on in-domain tasks.
- HyDE is **actively harmful on factual queries about rare entities** — the LLM hallucinates wrong facts, those facts embed close to wrong documents, and retrieval drifts.
- Cost: one extra LLM call per query. At Haiku-4 rates this is ~$0.0001; at GPT-5 rates it is ~$0.002 — still cheap but not free latency-wise (+200–500ms).

**2026 verdict**: HyDE is largely a **2023 artifact of weak unsupervised embedders**. Keep it in the toolbox for (a) unusual domains where you can't fine-tune an embedder, (b) very short queries (<5 tokens) where the embedder lacks signal. LlamaIndex and LangChain still ship it; most production systems don't turn it on.

### 2.2 Multi-Query / Query Variants

Generate N paraphrases of the query, retrieve each, fuse.

```
query → LLM → [q1, q2, q3] → 3× retrieve → RRF → top-k
```

Mechanism popularized by LangChain's `MultiQueryRetriever` (Feb 2023). Gains are real but modest: **+1–3 nDCG@10** on BEIR, mostly from recall on underspecified queries. Cost is N× the retrieval cost plus one LLM call.

**When it helps**: ambiguous natural-language queries ("how do I fix this?"). **When it hurts**: precise queries where variants dilute the signal.

### 2.3 Query Decomposition

Break a complex question into sub-queries, answer each, compose.

```
"Which of the books Alice reviewed in 2024 have movie adaptations?"
  → ["books Alice reviewed in 2024", "movie adaptations of <each book>"]
```

Used by Anthropic's Claude Research, Perplexity Deep Research, OpenAI's ChatGPT Deep Research, and the HotpotQA-style multi-hop benchmarks. This is **essential for multi-hop** — on HotpotQA, decomposition lifts F1 from ~50% to ~75% for systems that do it vs not. Cost is O(hops) LLM calls plus retrievals.

### 2.4 Step-Back Prompting

Zheng et al. 2023 (arxiv 2310.06117). Before retrieving, ask the LLM to generate a more abstract "step-back" question, retrieve context for *that*, then answer the original.

```
"Was Einstein born in Germany?" → step-back: "Where was Einstein born?"
```

Gains reported: +7–11 points on TimeQA, MuSiQue. In practice mostly folded into decomposition pipelines by 2026 — few systems invoke step-back as a distinct mode.

### 2.5 Recommendation

For coding-assistant and memory-recall workloads (this repo's focus): **skip HyDE**, use **decomposition for multi-hop**, and ignore the rest unless you're optimizing a known-weak query class.

---

## 3. Reranking Pipelines

### 3.1 Two-Stage: Retrieve → Cross-Encoder Rerank

The single highest-ROI addition to any retrieval system.

```
Query ──► First-stage retrieve (bi-encoder + BM25, k=100)
          │
          ▼
       Cross-Encoder (query, doc)   k×(Q,D) forward passes
          │
          ▼
       Top 10–20 reranked
```

**Why it works**: bi-encoders embed query and document independently; cross-encoders read them **jointly**, so they model term-interaction and negation properly. Quality ceiling is much higher — at the cost of O(k) forward passes per query instead of O(1).

**Benchmark gains** (BEIR, averaged):

| Stack | nDCG@10 |
|---|---|
| BM25 | 42.7 |
| Dense (E5-large) | 50.0 |
| Hybrid RRF | 53.8 |
| Hybrid + BGE-reranker-large | **57.2** |
| Hybrid + Cohere Rerank v3.5 | **59.1** |
| Hybrid + Voyage Rerank-2 | **59.4** |

**Cost**:
- Open-source (BGE-reranker-v2, Jina Reranker v2, mxbai-rerank-large): ~10–40ms for 100 docs on one A10 GPU.
- Hosted (Cohere Rerank v3.5, Voyage Rerank-2, Jina): ~$0.002 per 1k docs reranked, 80–200ms p50 latency.
- At k=100 this is roughly 50× the cost of a dense-only query, but still <1¢.

**Verdict**: **Always rerank**. A 5–6 nDCG@10 lift for a few tens of milliseconds is the best retrieval bargain in 2026. Every serious production RAG system ships a reranker.

### 3.2 Three-Stage: Retrieve → Cross-Encoder → LLM Rerank

```
Stage 1: hybrid (k=200)
Stage 2: cross-encoder reranker (k=30)
Stage 3: LLM-as-judge rerank (k=5–10)
```

Stage 3 uses a capable LLM (Sonnet/GPT-5-mini class) to score or reorder the top-30, using the full query and optional reasoning. Patterns include RankGPT (Sun et al. 2023), RankZephyr, and listwise LLM rerankers.

**Gains**: +1–3 nDCG@10 over stage-2 alone on hard reasoning benchmarks (TREC DL, BEIR-Hard). On easy benchmarks the gain is often negative (the LLM overthinks).

**Cost**:
- One LLM call per query with 30 docs in context → ~10–30k tokens in, ~500 tokens out.
- ~$0.01–$0.05 per query at GPT-5/Sonnet-4 rates.
- Latency: +500–2000ms.

**When to use**: high-stakes queries (legal, medical, enterprise search), low QPS, and where the downstream generator is already expensive. **When to skip**: anything interactive or high-QPS. Most production systems stop at stage 2.

### 3.3 Cost/quality curve (summary)

| Stack | Rel. cost | BEIR nDCG@10 | Marginal $/point |
|---|---:|---:|---|
| BM25 | 1× | 42.7 | — |
| +Dense (hybrid) | ~2× | 53.8 | cheap |
| +Cross-encoder rerank | ~5× | 59.1 | cheap |
| +LLM rerank | ~500× | 60.5 | expensive |
| +Fine-tune embedder | dev cost | +2–4 | one-time |

The elbow of the curve is clearly at stage 2 (hybrid + cross-encoder).

---

## 4. Agentic Retrieval

Instead of a fixed pipeline, let the LLM drive retrieval as a tool-calling loop.

### 4.1 ReAct-style retrieval loops

The LLM alternates **Thought → Action (search) → Observation** until it decides to answer.

```
while not done:
    thought = LLM.reason(query, history)
    if thought.calls_tool("search"):
        obs = retrieve(thought.query)
        history.append(obs)
    else:
        return thought.answer
```

Canonical in Claude Research, ChatGPT Deep Research, Perplexity's Pro mode, and every coding-agent (Claude Code, Codex, Cursor, Aider) that treats codebase grep/search as a tool. The retrieval pipeline underneath can still be hybrid + rerank; the **agent layer decides when and what to search**.

**Gains**: qualitative on open-ended research tasks; hard to benchmark cleanly. On multi-hop QA (HotpotQA, MuSiQue), ReAct loops lift F1 by **+5–15 points** over single-shot RAG.

**Cost**: unbounded without caps. Typical production systems cap at 5–10 search iterations. Per-query cost ~$0.05–$0.50.

### 4.2 Self-RAG / Self-Reflective

Asai et al. 2023 (arxiv 2310.11511). The model emits special "reflection tokens" (`[Retrieve]`, `[IsRel]`, `[IsSup]`, `[IsUse]`) to decide whether to retrieve, whether retrieved docs are relevant, and whether output is supported. Training requires a specially instruction-tuned model with reflection tokens in its vocab.

**Gains**: +5–10 points on factuality benchmarks (PopQA, FactScore) at the cost of higher latency. By 2026, the pattern has mostly been absorbed into general tool-calling models — frontier models (Claude 4, GPT-5, Gemini 3) do the equivalent reflection via regular reasoning without special tokens. Self-RAG survives as a **technique for open-weight small models** (≤8B) where explicit reflection tokens still help.

### 4.3 LLM-as-Retriever (Supermemory ASMR pattern)

Supermemory's Agent-Style Memory Retrieval (2026) treats retrieval itself as an LLM call: a small model reads candidate chunks and emits which to keep, in what order, with what synthesis. No separate reranker, no separate fusion — one LLM does it all.

**Tradeoff**: simpler pipeline, higher per-query cost. Requires a fast cheap model (Haiku 4.5, GPT-5-mini, Gemini Flash). Wins when the corpus is small enough to fit ~50 candidates in context and the generator model was going to run anyway.

**When to use**: personal memory, agent memory (small N), high-quality requirements. **When not**: web-scale corpora, latency-sensitive, cost-sensitive.

### 4.4 Recommendation

Agentic retrieval is the right answer for **open-ended research** and **coding-agent** workloads. For "answer one question from a knowledge base", a fixed hybrid+rerank pipeline is cheaper and just as good.

---

## 5. Contextual Retrieval (Anthropic)

Anthropic's September 2024 post ([anthropic.com/news/contextual-retrieval](https://www.anthropic.com/news/contextual-retrieval)) introduced a simple but effective indexing-time trick.

### 5.1 Mechanism

For each chunk, ask a cheap LLM (Haiku) to generate a 50–100 token **context blurb** explaining the chunk's place in the document, then **prepend** that context before embedding and before BM25 indexing.

```
Chunk (raw):
    "The company's revenue grew by 3% over the previous quarter."

Chunk (contextualized):
    "This chunk is from an SEC filing on ACME Corp's Q2 2023 performance;
     the previous quarter had revenue of $314M. The company's revenue grew
     by 3% over the previous quarter."
```

Indexing-time cost: one Haiku call per chunk (~$1 per million chunks with prompt caching). Query time: unchanged.

### 5.2 Empirical gains

From Anthropic's own benchmarks (internal corpora, top-20 retrieval failure rate):

| Method | Failure rate | Δ vs baseline |
|---|---:|---:|
| Baseline (embeddings only) | 5.7% | — |
| +BM25 (hybrid) | 3.7% | −35% |
| +Contextual Embeddings | 3.7% | −35% |
| +Contextual Embeddings + Contextual BM25 | 2.9% | −49% |
| +Contextual Retrieval + Rerank | **1.9%** | **−67%** |

The headline "67% reduction in retrieval failure" assumes all layers stacked: contextual embeddings, contextual BM25, and reranking together.

### 5.3 When to use

- **Document corpora with chunks that lose meaning out of context** — financial filings, legal docs, long manuals, codebases with scattered references.
- **Not useful** for corpora of already-self-contained chunks (FAQs, product descriptions, independent news snippets).

Prompt caching makes the indexing cost manageable: if you cache the full document as the prompt prefix, each chunk's contextualization is only ~100 output tokens. Anthropic's own math: ~$1.02 per million tokens of source material.

### 5.4 Production adoption

Anthropic ships it in the [official cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/skills/contextual-embeddings). Hindsight's `context` field per memory unit is a variant (context supplied at retain time). Supermemory documents use it implicitly via their chunking pipeline. LlamaIndex added `DocumentContextExtractor` in late 2024.

Worth noting: contextual retrieval is **an indexing strategy, not a runtime architecture change**, so it composes with every pattern above.

---

## 6. Graph-Augmented Retrieval

Mix a graph structure (entity nodes + relations) into retrieval, either at index time or at query time.

### 6.1 Microsoft GraphRAG

[github.com/microsoft/graphrag](https://github.com/microsoft/graphrag), paper "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (Edge et al. 2024).

**Indexing** (expensive, one-time):
1. Chunk documents.
2. LLM extracts (entity, relation, entity) triples + entity descriptions per chunk.
3. Build a document-scale knowledge graph.
4. Run Leiden community detection → hierarchical community structure.
5. LLM generates **community summaries** at each level.

**Query time** — two modes:
- **Global search**: map-reduce over community summaries; answer produced by aggregating across communities. Designed for "sensemaking" questions: "what are the main themes?"
- **Local search**: start from query-matched entities, walk the graph, pull related chunks.

**Gains**: on Microsoft's own QFS (query-focused summarization) benchmark, GraphRAG beats vanilla RAG on **comprehensiveness and diversity** (LLM-judge metrics) by ~70–80% win rate. On factoid QA, gains are smaller or neutral — GraphRAG is built for global sensemaking, not needle-in-haystack.

**Cost**:
- Indexing: **~$10–$100 per 1M tokens** of source (Feb 2026 prices, using GPT-5-mini or Sonnet-4-cheap for extraction). This is 100–1000× the cost of vanilla embedding.
- Query: comparable to vanilla RAG (+1 LLM call for map-reduce aggregation in global mode).

### 6.2 HippoRAG / HippoRAG 2

Gutiérrez et al. 2024/2025 (arxiv 2405.14831, 2502.xxxxx). Hippocampus-metaphor design: LLM extracts triples into a knowledge graph (the "hippocampal index"); retrieval runs **Personalized PageRank (PPR)** from query-mentioned entities and re-scores passages by PPR mass.

**Gains**: +8–14 F1 over vanilla RAG on MuSiQue/2WikiMultiHopQA multi-hop benchmarks. HippoRAG 2 (2025) improves triple extraction and retrieval, closing the gap to proprietary systems on LongMemEval.

**Cost**: comparable to GraphRAG at index time (LLM triple extraction dominates). Query-time PPR is cheap (sparse matrix-vector product).

### 6.3 LightRAG

Guo et al. 2024 (HKU). Tries to be cheaper than GraphRAG:
- Lightweight extraction with smaller prompts.
- Dual-level retrieval: low-level (entity) + high-level (theme).
- No Leiden community pass.

Reported gains competitive with GraphRAG at ~30% of the cost.

### 6.4 Does GraphRAG justify the cost at 2026 prices?

The honest 2026 answer: **usually no, with sharp exceptions.**

- **Cost gap narrowed**: Haiku-4.5 and GPT-5-mini dropped triple-extraction costs ~5× since the GraphRAG paper; prompt caching cuts another 2–5×. Indexing a 10M-token corpus went from ~$500 to ~$50.
- **But vanilla RAG also got better**: Contextual Retrieval (free-ish) plus a modern reranker closes most of the quality gap on standard QA.
- **Where graph still wins**: (a) **global sensemaking** ("summarize the themes in this 10k-doc corpus") — vanilla RAG fundamentally can't, (b) **multi-hop entity reasoning** ("which customers mentioned by engineers last quarter are also named in the legal filings") — graphs traverse, vectors don't, (c) **agent memory** where the graph doubles as structured knowledge for other operations.
- **Where graph loses**: standard QA, factoid lookup, any corpus under ~100k tokens (just stuff it in context), anything where entity extraction is noisy (informal text, transcripts, code).

**Heuristic**: if your top query types are "summarize across the corpus" or "multi-hop entity questions", build the graph. Otherwise, Contextual Retrieval + hybrid + rerank is 80% of the quality at 5% of the cost.

### 6.5 Hybrid: vector + graph at retrieval time

The production pattern (Graphiti/Zep, Hindsight, Neo4j's GraphRAG integration, LlamaIndex `KnowledgeGraphRAGRetriever`) is **not graph-only** — it's vector retrieval + graph traversal, fused. Hindsight's four-way (dense + BM25 + graph + temporal) → RRF → cross-encoder is the clearest open-source example. See `/Users/linguanguo/dev/llm-memory-research/hindsight.research.md` for pipeline details.

---

## 7. Long-Context vs RAG in 2026

With Gemini 3 Pro at 2M context, Claude 4 at 1M, and GPT-5 at 1M (standard) / 2M (beta), the "just stuff it in" question is real.

### 7.1 When long-context wins

- **Small corpora** (<500k tokens): fits, no retrieval error surface, full cross-document attention.
- **Queries needing full-document reasoning**: summaries, comparative analysis across sections, legal contract review, diff analysis across codebase versions.
- **Low QPS / high-stakes**: the retrieval debugging and ops burden isn't worth it.
- **Prompt caching compatible**: Anthropic/OpenAI/Google all offer 90%+ input-token discounts on cached prompts. If the corpus is stable, second and subsequent queries are nearly free.

### 7.2 When RAG still wins

- **Large corpora** (>2M tokens): doesn't fit, period.
- **High QPS even with caching**: per-query cost of stuffing 1M tokens is still ~$0.15–$0.50 uncached, ~$0.015–$0.05 cached — adds up at scale.
- **Latency-sensitive**: 1M-token attention prefill is 3–15 seconds even on TPU v5/H200. Retrieval keeps p50 under 1s.
- **Needle precision matters**: Ruler/NIAH-Hard benchmarks still show frontier models at ~85–95% recall at 1M, not 100%. Retrieval with a reranker beats it on pure precision.
- **Updates**: long-context requires resending; RAG updates by re-indexing. Differential cost favors RAG for frequently-updated corpora.

### 7.3 Hybrid long-context + retrieval

The 2026 production pattern is frequently **both**:

1. Retrieve top-50 candidates via hybrid + rerank.
2. Stuff all 50 (~100k tokens) into the generator's long context.
3. Let the generator's attention do the final "reading".

This gives up the "smaller prompt" efficiency benefit but retains the **recall** benefit of RAG while letting long-context attention do the precision step. Anthropic Research, Claude Code's codebase understanding, and Perplexity Pro all operate this way.

### 7.4 Decision rule

```
corpus < 500k tokens       → long context + prompt cache, skip RAG
corpus < 10M tokens, low QPS → long context per query, tolerate cost
corpus < 10M tokens, high QPS → RAG (hybrid + rerank)
corpus > 10M tokens          → RAG (mandatory)
need global summaries       → GraphRAG or long-context summarization
need freshness/updates      → RAG
```

The inflection point keeps moving as context windows grow and prices drop. Re-check every 6 months.

---

## 8. Putting It Together: Reference Architectures

### 8.1 "Default production RAG" (80% of use cases)

```
[Indexing]
  docs → chunk (recursive, 500 tok, 50 overlap)
       → contextual blurb via Haiku (prepend)
       → embed (E5-large or Voyage-3) + BM25 tsvector

[Query]
  query → hybrid (BM25 + dense, k=100) → RRF
        → cross-encoder rerank (BGE-v2 or Cohere v3.5, k=10)
        → generator (Sonnet/GPT-5-mini)
```

No HyDE, no multi-query, no graph. Ships in days, solid baseline.

### 8.2 "Agent memory" (LongMemEval-style)

```
[Ingest]
  turn → LLM fact extraction (what/when/who/why)
       → embed + BM25 + entity extraction + temporal links

[Recall]
  query → 4-way parallel (dense + BM25 + graph + temporal)
        → RRF → cross-encoder → recency/temporal boost
        → agentic reflect loop over results
```

Hindsight is the canonical open-source instance.

### 8.3 "Research agent" (open-ended, multi-hop)

```
[Loop]
  while not done:
    plan → decompose into sub-queries
    for each sub-query:
        hybrid retrieve → rerank → read → append evidence
    synthesize → decide (answer | refine | halt)
```

Claude Research, ChatGPT Deep Research, Perplexity Pro.

### 8.4 "Enterprise sensemaking" (global QFS)

```
[Indexing]
  docs → triples → graph → Leiden communities → community summaries

[Query]
  query → map over communities → reduce → global answer
```

Microsoft GraphRAG, LightRAG variants.

---

## 9. Open Questions and What I'd Watch

- **Do cross-encoders survive long-context?** As context grows, the LLM generator is essentially a listwise reranker on its own. Cross-encoder rerankers may collapse into the generator. Already happening in Supermemory ASMR.
- **GraphRAG at frontier prices**: if Haiku-5/GPT-5-nano drops another 5×, graph extraction cost becomes negligible and GraphRAG-like indexing goes default. Worth re-running the cost math each quarter.
- **Learned retrieval end-to-end**: ColBERT-v3/RAGatouille, ReAct-trained retrievers. Still behind hybrid+rerank in 2026, but closing.
- **Retrieval-free memory**: long-context + prompt caching eats RAG from below for small corpora. The question is how fast context windows + caching push that frontier — a 10M-token cached prompt at $0.001/query would obsolete most default RAG stacks.

---

## Sources

- [Anthropic — Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [Anthropic Cookbook — Contextual Embeddings](https://github.com/anthropics/anthropic-cookbook/tree/main/skills/contextual-embeddings)
- [Microsoft GraphRAG repo](https://github.com/microsoft/graphrag)
- [GraphRAG paper — Edge et al. 2024](https://arxiv.org/abs/2404.16130)
- [HippoRAG — Gutiérrez et al. 2024](https://arxiv.org/abs/2405.14831)
- [LightRAG — Guo et al. 2024](https://arxiv.org/abs/2410.05779)
- [Self-RAG — Asai et al. 2023](https://arxiv.org/abs/2310.11511)
- [HyDE — Gao et al. 2022](https://arxiv.org/abs/2212.10496)
- [Step-Back Prompting — Zheng et al. 2023](https://arxiv.org/abs/2310.06117)
- [RankGPT — Sun et al. 2023](https://arxiv.org/abs/2304.09542)
- [Reciprocal Rank Fusion — Cormack et al. 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [BEIR benchmark — Thakur et al. 2021](https://arxiv.org/abs/2104.08663)
- [RAGTruth — Niu et al. 2024](https://arxiv.org/abs/2401.00396)
- [Qdrant DBSF docs](https://qdrant.tech/documentation/concepts/hybrid-queries/)
- [LangChain retrievers catalog](https://python.langchain.com/docs/integrations/retrievers/)
- [LlamaIndex retrievers](https://docs.llamaindex.ai/en/stable/module_guides/querying/retriever/)
- [Vespa hybrid ranking](https://docs.vespa.ai/en/nativerank.html)
- [Cohere Rerank v3.5 release](https://cohere.com/blog/rerank-3pt5)
- [Voyage Rerank-2](https://blog.voyageai.com/2024/09/30/rerank-2/)
- Sibling: `retrieval/chunking.research.md`
- Sibling: `retrieval/embedding-models.research.md`
- Related: `/Users/linguanguo/dev/llm-memory-research/hindsight.research.md` (4-way retrieval in practice)
- Related: `/Users/linguanguo/dev/llm-memory-research/anthropic-context-engineering.research.md`
