# Text Chunking & Segmentation Strategies for Retrieval

Last Updated: 2026-04-15

> **Research Methodology**: Synthesis of primary papers (Dense X Retrieval, RAPTOR, Late Chunking, "Is Semantic Chunking Worth the Computational Cost?"), vendor engineering posts (Anthropic, Jina, Chroma, LlamaIndex, LangChain), and 2025-2026 empirical benchmarks. Scope is limited to text chunking for dense / hybrid retrieval — embedding model architecture and reranking are covered separately in `embedding-models.research.md` and `retrieval-architecture.research.md`.

## Overview

Chunking is the least glamorous and most consequential knob in a retrieval stack. An embedding model only sees what the splitter hands it, and the top-k that goes to the LLM can never be better than the chunks that were indexed. Despite ~three years of RAG productization, the empirical literature is still contrarian: in two of the three head-to-head benchmarks surveyed here, naive fixed-size chunking matches or beats methods that are 10-100× more expensive.

This document covers seven families of strategies:

1. Fixed-size (token/char + overlap) — the baseline that keeps winning
2. Recursive / structure-aware — LangChain `RecursiveCharacterTextSplitter`, markdown, code (AST)
3. Semantic chunking — embedding-distance boundaries (Kamradt, LlamaIndex `SemanticSplitterNodeParser`)
4. Late chunking (Jina) — embed the whole doc, chunk the token-embedding sequence afterward
5. Agentic / propositional — LLM-driven decomposition (Propositionizer / Dense X, RAPTOR)
6. Parent-child / hierarchical — small-to-big retrieval, sentence-window, auto-merging
7. Contextual Retrieval (Anthropic) — LLM-generated per-chunk context prepended before embedding

---

## Comparison Table

| Strategy | Index-time cost | Query-time cost | Quality claim | Best when | Avoid when |
|---|---|---|---|---|---|
| **Fixed-size + overlap** | Trivial (CPU tokenize) | Standard k-NN | Strong baseline; hard to beat with naive semantic | Anything, as the starting point | Highly structured docs where overlap wastes budget |
| **Recursive / structure-aware** | Trivial | Standard | Best "free lunch" — respects paragraphs, headers, code blocks | Markdown, code, HTML, PDFs with clear structure | Unstructured prose where separators add no signal |
| **Semantic (Kamradt)** | 1 embedding call per sentence | Standard | Mixed: wins on some domains, loses on others; worse on avg vs fixed in NAACL'25 | Prose with clear topic shifts (e.g. long narratives) | Cost-sensitive, or when fixed-size already ≥85% recall |
| **Late chunking (Jina)** | 1 long-context forward pass per doc | Standard | +5-15% similarity on cross-chunk references; preserves pronouns | Long docs with many cross-references (legal, long articles) | Docs fit in <1 chunk; corpus of short independent snippets |
| **Propositional (Dense X)** | Full LLM pass per passage; 250M props for Wikipedia | Standard (but more chunks) | Outperforms passage-level on QA; highest index-time $ | Factoid QA, Wikipedia-like corpora, compliance/legal | Narrative understanding, small corpora, tight budgets |
| **RAPTOR (tree)** | O(n log n) embed + LLM summarize per cluster, recursive | Standard (tree-indexed) | +2-10 F1 points on QASPER/QuALITY over BM25/DPR | Long multi-doc synthesis, thematic questions | Short docs; when you just want span retrieval |
| **Parent-child / small-to-big** | 2× index (child + parent chunks) | Standard; post-expand | Higher precision + higher recall context | Q&A over long docs where LLM needs context window | Storage-constrained; uniform-granularity corpora |
| **Contextual Retrieval** | 1 LLM call per chunk (~$1/M tokens w/ caching) | Standard | -35% retrieval failures; -49% w/ BM25; -67% w/ reranker | Corpora where chunks lose meaning without doc context | Self-contained chunks (FAQs, fact sheets, transcripts) |

---

## 1. Fixed-Size Chunking (Baseline)

**Mechanism.** Split by fixed token or character count, typically with overlap (e.g. 512 tokens, 64 overlap). No structure awareness. Implemented as LangChain `CharacterTextSplitter` / `TokenTextSplitter`, LlamaIndex `SentenceSplitter` (if configured without structure), or a trivial `tokenizer.encode(doc)[i:i+N]` loop.

**Key parameters.**
- **Chunk size**: 64-128 tokens for factoid QA; 256-512 for mixed Q&A; 1024+ for synthesis and long-form. Chroma's 2024 study used 200-token recursive chunks as a strong baseline.
- **Overlap**: 10-20% is the usual prescription. OpenAI's default of 800/400 (50% overlap) was called out by Chroma as producing "particularly poor recall-efficiency tradeoffs" — high recall (85.4%) but precision 1.5%, meaning most retrieved text is redundant.

**When it pays off.** Always start here. It is free, deterministic, and in three of the four rigorous benchmarks surveyed here it is either the winner or within noise of the winner.

**When it doesn't.** Code, tables, anything where arbitrary mid-sentence / mid-function cuts destroy semantics.

**Empirical reference point.** In the Chroma study (472 queries, 5 corpora, `text-embedding-3-large`), `RecursiveCharacterTextSplitter` at 200 tokens achieved **Recall 88.1% / Precision 7.0%** at k=5 — roughly tied with the best semantic approach. [Chroma Research: Evaluating Chunking Strategies](https://research.trychroma.com/evaluating-chunking)

---

## 2. Recursive / Structure-Aware Chunking

**Mechanism.** Define an ordered list of separators (e.g. `["\n\n", "\n", ". ", " ", ""]`). Try the first separator; if any resulting piece is still larger than the target size, recurse into it with the next separator. This preserves paragraph / sentence / word boundaries as long as size permits.

This is LangChain's `RecursiveCharacterTextSplitter` and the default in most production RAG stacks. Language-aware variants ship separator lists for 24 programming languages plus Markdown, HTML, and LaTeX.

**Markdown-aware variants.**
- `MarkdownHeaderTextSplitter`: split by header hierarchy (`#`, `##`, `###`) and attach the header path as metadata. Combines with `RecursiveCharacterTextSplitter` for size control within a section.
- LlamaIndex `MarkdownNodeParser` / `HTMLNodeParser`: similar, keep structural metadata on each chunk.

**Code-aware variants (AST).** Naive splitting on code is catastrophic — a function or class gets split mid-body. Two approaches:
- **Separator-based (LangChain)**: per-language separator lists (`\nclass `, `\ndef `, `\n\n`) approximate structural boundaries without parsing.
- **Tree-sitter / AST-based** (supermemory `code-chunk`, `astchunk`, `cAST`): parse the source, take function / class / method nodes as chunks, merge siblings up to size limit, include scope chain + imports as chunk metadata.

**Empirical.** cAST (arXiv 2506.15655) reports **Recall@5 +4.3 points on RepoEval** and **Pass@1 +2.67 on SWE-bench** vs. naive splitting. A separate comparison cited 70% correct-answer rate for AST-based vs. 59% naive, 61% language-aware separator-based on a code-QA task.

**When it pays off.** Any structured document. The gain is close to free (a few ms of parsing per doc).

**When it doesn't.** Plain prose — the recursive version degenerates to character splitting with extra steps.

---

## 3. Semantic Chunking (Embedding-Distance Boundaries)

**Mechanism (Kamradt / LlamaIndex `SemanticSplitterNodeParser`).**

1. Split text into sentences (typically via `nltk` or regex).
2. For each sentence, embed a window of `buffer_size` sentences (default 1 — itself + neighbors).
3. Compute cosine distance between consecutive window embeddings.
4. Boundary = any position where distance exceeds the `breakpoint_percentile_threshold` (default 95th percentile).
5. Merge adjacent sentences until a boundary is hit.

Variants: Chroma's `ClusterSemanticChunker` does global clustering rather than local thresholding. Milvus's "Max-Min Semantic Chunking" uses min-cut on the sentence-similarity graph.

**Empirical — does it beat fixed-size?** This is the most important empirical question in chunking and the literature is split.

- **Against.** Qu, Tu & Bao (NAACL 2025 Findings, *"Is Semantic Chunking Worth the Computational Cost?"*): across document retrieval, evidence retrieval, and answer generation tasks, fixed-size chunking matched or beat semantic chunking. The conclusion is explicit: *"the computational costs associated with semantic chunking are not justified by consistent performance gains."* [ACL Anthology](https://aclanthology.org/2025.findings-naacl.114/)

- **Against (industrial).** Vecta's 2026 benchmark (50 academic papers, 7 strategies): recursive 512-token split first at **69% accuracy**; semantic chunking **54%**, partly because it produced fragments averaging only 43 tokens.

- **Mixed.** Chroma's study showed the greedy Kamradt chunker underperformed defaults, while their novel `ClusterSemanticChunker` matched recursive at higher precision (Recall 87.3 / Precision 8.0 vs. 88.1 / 7.0).

- **For (domain-specific).** An MDPI Bioengineering 2025 clinical-decision-support study reported 87% vs. 13% for adaptive topic-boundary chunking over fixed-size, p=0.001 — but the fixed-size 13% baseline is anomalous and suggests the fixed baseline was mis-configured.

**Verdict.** Semantic chunking has not survived rigorous evaluation as a general-purpose winner. It can help in specific narrative domains with clear topic shifts, but the default should remain recursive/fixed unless a domain-specific benchmark justifies the 1-embedding-per-sentence cost.

---

## 4. Late Chunking (Jina, 2024)

**Mechanism.** Inverts the order of embedding and chunking. Paper: arXiv 2409.04701, updated through mid-2025.

```
Traditional:          Late chunking:
  text                  text
   │                     │
   ▼                     ▼
 chunk (N pieces)     embed whole doc (token-level outputs, 8K+ ctx)
   │                     │
   ▼                     ▼
 embed each chunk     slice token embeddings by chunk boundaries
                         │
                         ▼
                      mean-pool each slice → chunk embedding
```

Because the transformer's self-attention has already seen the whole document when it produces each token's contextualized embedding, the resulting chunk embedding encodes *its own content conditioned on the rest of the document*. A chunk that says "She then resigned" still carries the identity of "she" in its pooled vector.

**Requirements.** Long-context embedding model (jina-embeddings-v2/v3, up to 8192 tokens). For documents longer than the window, Jina recommends "long late chunking" with overlapping macro-windows.

**Empirical.**
- Jina's own benchmarks on BEIR subsets show late chunking similarity scores of **82-84%** on contextual probe tasks where naive chunking scored **70-75%**.
- Weaviate's head-to-head showed late chunking retrieving contextually-correct chunks where naive chunking retrieved surface-keyword matches, at **identical storage cost** (~4.9 GB for 100K 8K-token docs — same as naive, vs. 2.46 TB for ColBERT-style late interaction).
- Implementation is ~30 lines of Python on top of `jina-embeddings-v2`.

**When it pays off.**
- Long documents with many cross-references (pronouns, "this", "the company") — legal, long-form journalism, research papers.
- When you want the coherence benefits of long-context embeddings without exploding storage (unlike ColBERT multi-vector).

**When it doesn't.**
- Short documents already fit in one chunk → no cross-chunk context to preserve.
- Corpora of independent short snippets (tweets, FAQs, chat turns) — there is no "long-range context" to leak in.
- Without a long-context model, this technique is not available.

**References.** [Jina AI blog](https://jina.ai/news/late-chunking-in-long-context-embedding-models/), [arXiv 2409.04701](https://arxiv.org/abs/2409.04701), [GitHub jina-ai/late-chunking](https://github.com/jina-ai/late-chunking), [Weaviate blog](https://weaviate.io/blog/late-chunking).

---

## 5. Agentic / Propositional Chunking

Two sub-families here, both LLM-driven at index time.

### 5a. Propositionizer (Dense X Retrieval, Chen et al. 2023 → 2024)

**Mechanism.** Fine-tune a text generator (the "Propositionizer") to rewrite a passage into a list of *propositions*: atomic self-contained natural-language factoids. The training data is 42K passages bootstrapped from a teacher model (GPT-4). Indexing is then done at proposition granularity.

Example: *"Marie Curie was born in Warsaw in 1867. She was the first woman to win a Nobel Prize."* → two propositions, each indexable independently and resolving the pronoun "she".

**Empirical.** Paper reports proposition-level indexing consistently outperforms passage-level and sentence-level on EntityQuestions, TriviaQA, NQ, SQuAD, and WebQuestions. Authors released **FactoidWiki**: 6M Wikipedia pages → **250M propositions**. Hugging Face paper page shows QA gains of several F1/EM points across retrievers (BM25, Contriever, GTR) purely from the granularity switch.

**Cost.** One full LLM forward pass per passage at index time. At Wikipedia scale: 250M propositions is a 40-100× increase in index size over passage chunks.

**When it pays off.** Factoid QA over reference corpora; compliance where every claim needs to be independently retrievable.

**When it doesn't.** Narrative or argumentative text where propositions strip away discourse structure; small corpora where the rewrite cost dwarfs the benefit.

### 5b. RAPTOR (Sarthi et al., ICLR 2024)

**Mechanism.** Builds a *tree* of abstractive summaries bottom-up:

```
Level 0: original chunks (fixed-size)
  │  embed → cluster (GMM on UMAP-reduced vectors) → LLM-summarize each cluster
Level 1: summaries of Level 0 clusters
  │  embed → cluster → summarize
Level 2: summaries of Level 1 clusters
  ...until single root or max depth
```

All nodes (leaves + summaries) go into the same index. Retrieval can be tree-traversal or flat ("collapsed tree") — flat performs nearly as well and is simpler.

**Empirical.** On QASPER (full-text NLP papers), RAPTOR F1-Match: **53.1% (GPT-3), 55.7% (GPT-4), 36.6% (UnifiedQA)** — beating DPR by 1.8-4.5 points and BM25 by 5.5-10.2. New SOTA at time of publication on NarrativeQA, QASPER, QuALITY with GPT-4.

**Cost.** O(n log n) LLM summarization calls at index time. Authors report ~$10 for the full QASPER corpus in 2024 OpenAI pricing.

**When it pays off.** Multi-hop or thematic questions over long documents / collections where the answer is a synthesis ("What are the main criticisms of approach X across these 10 papers?"). Leaves alone cannot answer these; summaries at higher levels can.

**When it doesn't.** Span-level factoid QA — the summary layers add noise. Short corpora where the tree is shallow.

**Reference.** [arXiv 2401.18059](https://arxiv.org/abs/2401.18059), [GitHub parthsarthi03/raptor](https://github.com/parthsarthi03/raptor).

---

## 6. Parent-Child / Hierarchical ("Small-to-Big")

**Mechanism.** Index two (or more) granularities of the same document:
- **Child** chunks (e.g. 128-256 tokens): what the vector search runs against. Precise, high-signal.
- **Parent** chunks (e.g. 1024-2048 tokens): what gets fed to the LLM after retrieval.

At query time, retrieve top-k at child granularity, then look up the parent chunks (via stored `parent_id` or graph-based merge) and pass those to the generator.

**Implementations.**
- LlamaIndex `HierarchicalNodeParser` + `AutoMergingRetriever`: if a significant fraction of a parent's children are retrieved, substitute the parent for them.
- LlamaIndex `SentenceWindowNodeParser`: retrieve a single sentence, expand to ±N sentences for the LLM.
- LangChain `ParentDocumentRetriever`: same pattern, two separate vector stores.

**Why it works.** Decouples the two jobs of a chunk. Retrieval wants high-precision queries → small chunks. Generation wants enough context to reason → large chunks. A single chunk size is a compromise; two sizes remove the compromise.

**Empirical.** No single clean benchmark, but it's the de facto standard in production RAG (LlamaIndex "Advanced RAG 01" tutorial, LangChain cookbook). Reports of 10-20% answer quality gains over flat single-size indexing are common but rarely controlled.

**Cost.** Index-time ~2× embedding cost; storage ~2× if parents are embedded too, ~1.2× if parents are only stored as text.

---

## 7. Contextual Retrieval (Anthropic, 2024)

**Mechanism.** Before embedding each chunk, prepend 50-100 tokens of LLM-generated context that situates it in the source document. Also used when building the BM25 index.

**Prompt** (from Anthropic's cookbook):
```
<document> {whole_doc} </document>
Here is the chunk we want to situate:
<chunk> {chunk_text} </chunk>
Please give a short succinct context to situate this chunk within the
overall document for the purposes of improving search retrieval.
```

Prompt caching makes this affordable: the whole document is cached, only the per-chunk query pays full-price tokens. Anthropic reports **~$1.02 per million document tokens** at Claude 3 Haiku pricing (2024).

**Empirical** (Anthropic's own eval, multi-corpus).

| Variant | Top-20 failure rate | vs baseline |
|---|---|---|
| Baseline (plain chunks, embedding only) | 5.7% | — |
| Contextual Embeddings | 3.7% | **-35%** |
| Contextual Embeddings + Contextual BM25 | 2.9% | **-49%** |
| + Reranker | 1.9% | **-67%** |

Independently reproduced in LlamaIndex and Milvus cookbooks at similar magnitudes.

**When it pays off.** Chunks that lose meaning out of context (legal clauses, conversation excerpts, scientific paper fragments that reference "the previous section"). Especially strong when combined with hybrid BM25 and reranking.

**When it doesn't.** Self-contained chunks (encyclopedia entries, FAQ Q&A pairs, reviews) where no extra context exists to inject. Very small corpora where the LLM call cost isn't amortized.

**References.** [Anthropic announcement](https://www.anthropic.com/news/contextual-retrieval), [Claude cookbook](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide), [LlamaIndex cookbook](https://developers.llamaindex.ai/python/examples/cookbooks/contextual_retrieval/).

---

## Tradeoffs and Practical Recommendations

### Which method per scenario

| Scenario | Recommended stack | Rationale |
|---|---|---|
| **Generic prose corpus, prototype** | Recursive 512/64 + hybrid BM25 | Cheap, reproducible, strong baseline. Don't pay for semantic until a benchmark shows the gain. |
| **Long structured docs (legal, research)** | Markdown/header-aware recursive → Contextual Retrieval → reranker | Structure preserved; Anthropic context fills in cross-references; reranker cleans the top-k. |
| **Code repositories** | AST-based (tree-sitter) with scope metadata, then file/module as parent | AST is the only method that doesn't shred functions; parent-child gives the LLM surrounding definitions. |
| **Multi-hop / synthesis over a document set** | RAPTOR tree + flat retrieval | Summary layers answer cross-document thematic questions that leaves can't. |
| **Factoid QA (FAQ, Wikipedia-like)** | Propositional (Dense X) *if* budget allows; otherwise recursive ~200 tokens | Proposition granularity is measurable win on EntityQuestions/NQ/SQuAD style tasks. |
| **Long docs with heavy cross-reference (pronouns, "this")** | Late chunking (Jina v3) over 8K-token windows | The only method that cheaply preserves long-range context in the embedding itself. |
| **Conversation memory (ChatGPT / Claude memory)** | Per-turn or per-session chunking + fact extraction (see below) | Chunking prose techniques are the wrong tool. |
| **Multi-modal (PDFs with tables/figures)** | Out of scope here — use layout-aware parsers (Docling, Unstructured) + recursive chunker per element | Chunking comes after layout segmentation; treat tables/figures as atomic chunks. |

### Conversation memory: which chunking applies?

This is the key question for the broader memory-systems research in this repo. The answer is **none of the document-chunking methods above are a good fit**. Conversation memory (ChatGPT memory, Claude memory, and systems like Mem0 / Hindsight) treats the *conversation turn* or *extracted fact* as the atomic unit:

- **Turn-level chunking**: each user/assistant turn is its own chunk. Natural boundary, zero decision cost. Used by most MemGPT-style systems.
- **Fact extraction** (Hindsight, Mem0, A-Mem): LLM reads recent turns, extracts structured facts ("Alice works at Google", "user prefers TypeScript"), each fact is its own retrieval unit. This is effectively propositional chunking applied to dialog.
- **Session summarization** (MemoryBank, Generative Agents): periodically summarize N turns into a compressed episodic memory. Analogous to RAPTOR Level 1, one level deep.

The retrieval unit in conversation memory is *semantic, not syntactic*. Token-size chunking is irrelevant because turns are already small; the interesting work is in what to extract and at what granularity.

### Cost-quality frontier

Ordered from cheapest to most expensive index-time cost, per 1M document tokens:

1. Fixed-size / recursive: ~$0 (CPU-only)
2. Structure-aware (markdown, AST): ~$0 (CPU parsing)
3. Parent-child: 1-2× embedding cost ≈ $0.02-0.13 depending on model
4. Semantic (Kamradt): 1 embed per sentence ≈ 5-10× embedding cost
5. Late chunking: 1 long-context embed per doc; comparable to or cheaper than semantic
6. Contextual Retrieval: ~$1.02/M tokens with prompt caching (Claude Haiku)
7. Propositional (Dense X): full LLM forward pass per passage; order $10-100/M depending on model
8. RAPTOR: propositional cost × log(n) for summary layers

Contextual Retrieval, at ~$1/M tokens, sits in a sweet spot: order-of-magnitude cheaper than full propositionization, with the largest reproducible win in rigorous benchmarks (-35% to -67% retrieval failure).

### Does semantic chunking actually beat fixed-size? — Verdict

**No, not as a default.** The NAACL 2025 paper, Vecta 2026 benchmark, and Chroma 2024 study collectively show fixed-size + recursive is at or near the top across general corpora. Semantic chunking's one clear win is in specific narrative domains (clinical text with topic shifts), and even there the dominant variant is `ClusterSemanticChunker` (global clustering), not the popularized Kamradt greedy-threshold version.

**What to actually do**: spend the budget on (a) structure-aware parsing for your specific doc type, (b) hybrid BM25+vector, (c) Contextual Retrieval, and (d) a reranker. Those four together dominate semantic chunking in every benchmark surveyed here.

### When does late chunking earn its cost?

Late chunking earns its cost when **two conditions** co-occur: (1) documents are longer than one chunk and (2) semantic dependencies cross chunk boundaries (pronouns, topic continuations, definition-reference patterns). For a corpus of short self-contained snippets, late chunking has nothing to preserve. For a corpus of long narrative or legal text, it delivers the biggest semantic-preservation win per dollar, because a single forward pass per doc replaces per-sentence embedding (semantic) or per-chunk LLM calls (contextual retrieval).

A pragmatic default: **late chunking + recursive boundaries + Contextual Retrieval** for long-document corpora is cheaper than propositional chunking and captures most of the accuracy.

---

## Sources

**Papers:**
- [Dense X Retrieval: What Retrieval Granularity Should We Use? (arXiv 2312.06648)](https://arxiv.org/abs/2312.06648)
- [RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval (arXiv 2401.18059, ICLR 2024)](https://arxiv.org/abs/2401.18059)
- [Late Chunking: Contextual Chunk Embeddings (arXiv 2409.04701)](https://arxiv.org/abs/2409.04701)
- [Is Semantic Chunking Worth the Computational Cost? (NAACL 2025 Findings)](https://aclanthology.org/2025.findings-naacl.114/)
- [cAST: Enhancing Code RAG with Structural Chunking via AST (arXiv 2506.15655)](https://arxiv.org/abs/2506.15655)
- [Beyond Chunking: Discourse-Aware Hierarchical Retrieval (arXiv 2506.06313)](https://arxiv.org/abs/2506.06313)

**Vendor engineering posts:**
- [Anthropic: Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [Anthropic Cookbook: Contextual Embeddings Guide](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide)
- [Jina AI: Late Chunking in Long-Context Embedding Models](https://jina.ai/news/late-chunking-in-long-context-embedding-models/)
- [Jina AI: What Late Chunking Really Is (Part II)](https://jina.ai/news/what-late-chunking-really-is-and-what-its-not-part-ii/)
- [Chroma Research: Evaluating Chunking Strategies for Retrieval](https://research.trychroma.com/evaluating-chunking)
- [Weaviate: Late Chunking — Balancing Precision and Cost](https://weaviate.io/blog/late-chunking)
- [Weaviate: Chunking Strategies for RAG](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Pinecone: Chunking Strategies for LLM Applications](https://www.pinecone.io/learn/chunking-strategies/)
- [Milvus: Contextual Retrieval](https://milvus.io/docs/contextual_retrieval_with_milvus.md)
- [Supermemory: Building code-chunk (AST-aware code chunking)](https://supermemory.ai/blog/building-code-chunk-ast-aware-code-chunking/)

**Framework docs:**
- [LangChain: RecursiveCharacterTextSplitter reference](https://reference.langchain.com/python/langchain-text-splitters/)
- [LangChain: Markdown Header Splitter](https://docs.langchain.com/oss/python/integrations/splitters/markdown_header_metadata_splitter)
- [LlamaIndex: Semantic Chunker](https://developers.llamaindex.ai/python/examples/node_parsers/semantic_chunking/)
- [LlamaIndex: Node Parser Modules](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules/)
- [LlamaIndex: Contextual Retrieval cookbook](https://developers.llamaindex.ai/python/examples/cookbooks/contextual_retrieval/)

**Benchmarks & secondary surveys:**
- [PremAI: RAG Chunking Strategies 2026 Benchmark Guide](https://blog.premai.io/rag-chunking-strategies-the-2026-benchmark-guide/)
- [Firecrawl: Best Chunking Strategies for RAG in 2026](https://www.firecrawl.dev/blog/best-chunking-strategies-rag)
- [Comparative Evaluation of Advanced Chunking in Clinical Decision Support (MDPI, 2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12649634/)
- [Rethinking Chunk Size for Long-Document Retrieval (arXiv 2505.21700)](https://arxiv.org/html/2505.21700v2)
- [Enhancing RAPTOR with Semantic Chunking & Adaptive Graph Clustering (Frontiers, 2025)](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1710121/full)
