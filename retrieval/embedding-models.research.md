# Embedding Model Architectures for Retrieval

Last Updated: 2026-04-15

> **Research Methodology**: Synthesis of the MTEB / MMTEB leaderboard (HuggingFace `mteb/leaderboard`), primary arxiv papers, and vendor model cards (OpenAI, Cohere, Jina, Voyage, Nomic, BAAI, Alibaba, Google). This is an architectural comparison, not a benchmark reproduction.

## 0. TL;DR

| Family | Representative model | Per-chunk bytes (typical) | Query cost | Quality tier (MTEB v2 eng) | When to pick |
|---|---|---|---|---|---|
| Dense bi-encoder | BGE-M3, E5-Mistral-7B, GTE-Qwen2 | 4 KB (d=1024, fp32) → 512 B (int8) | 1 encode + 1 ANN lookup | 65-75 | Default for RAG |
| Late interaction | ColBERTv2 / PLAID | ~30-80 KB/chunk (compressed 128-dim/token) | 1 encode + MaxSim over token vectors | 70-76 on BEIR | Out-of-domain, short-query QA |
| Matryoshka | OpenAI `text-embedding-3`, Nomic v1.5/v2, Jina v3 | Truncatable 64→1536 | 1 encode, dim picked at query | 64-72 | Cost-adjustable single index |
| Sparse learned | SPLADE-v3, BGE-EN-ICL-Sparse | 30-100 non-zero terms / doc | Inverted index lookup | 60-70 | BM25-compatible infra, interpretable |
| Multi-vector (multimodal) | ColPali, ColQwen2, ColSmol | ~100-300 KB / page image | Encode image + MaxSim | 80+ on ViDoRe | Native PDF/slide retrieval |
| Cross-encoder reranker | Cohere Rerank v3.5, BGE-reranker-v2.5, Jina Reranker v2, mxbai-rerank-v2 | 0 (not stored) | 1 forward pass per (q, d) | +3-8 nDCG over stage 1 | Top-20/50 rerank of any stage-1 |
| Frontier general | Qwen3-Embedding-8B, Gemini-Embedding-001, Voyage-3-Large, Jina v4 | 4-16 KB | 1 encode + ANN | **72-78 MTEB v2** | When you need ceiling quality |

Headline numbers as of the snapshot for MTEB v2 (English) and MMTEB (Multilingual) leaderboards captured early April 2026: the top-3 slots are held by Qwen3-Embedding-8B (~76-78), Gemini-Embedding-001 (~74-76), and Voyage-3-Large / NV-Embed-v2 tier (~73-75). Open-weight gap to closed-source is ~1-2 points — the smallest it has ever been.

---

## 1. Dense Bi-encoder: the Baseline

### Architecture

Two independent encoder passes — one for the query, one for each document — each collapsed to a single dense vector, typically 384/768/1024/1536/3072 dimensions. Scoring is cosine or dot product.

```
query ─► Encoder ─► mean/CLS pool ─► L2-norm ─► vec_q (d)
doc   ─► Encoder ─► mean/CLS pool ─► L2-norm ─► vec_d (d)
score = vec_q · vec_d
```

Pooling: mean-pooling (SBERT, BGE, E5) is most common; CLS-pooling is used by some BERT-derived models; last-token pooling has become the standard for LLM-decoder encoders (E5-Mistral, GTE-Qwen2, Qwen3-Embedding).

Training: almost universally **contrastive**, usually **Multiple Negatives Ranking (MNR)** loss (a.k.a. InfoNCE / in-batch negatives) with hard negatives mined from BM25 or a previous-generation retriever. Two-stage training is dominant: (1) weakly-supervised pretraining on billions of (query, positive) pairs from web/CC / title-body pairs; (2) supervised fine-tune on MS MARCO + NLI + retrieval task mixtures with hard negatives and a temperature-scaled softmax.

### Representative models

| Model | Base | Dim | MTEB v2 eng | BEIR avg | License | Notes |
|---|---|---|---|---|---|---|
| SBERT `all-MiniLM-L6-v2` | MiniLM (22M) | 384 | ~45 | ~41 | Apache 2 | 2021 baseline, still ubiquitous |
| BGE-large-en-v1.5 | BERT-large (335M) | 1024 | ~64 | ~54 | MIT | BAAI, 2023 frontier |
| BGE-M3 | XLM-RoBERTa-large | 1024 | ~66 multilingual | ~54 | MIT | Dense + sparse + ColBERT heads in one model |
| E5-large-v2 | BERT-large | 1024 | ~63 | ~50 | MIT | Microsoft, 2023 |
| E5-Mistral-7B-instruct | Mistral-7B | 4096 | ~68 | ~56 | MIT | First LLM-decoder embedding to top MTEB (Jan 2024) |
| GTE-Qwen2-7B-instruct | Qwen2-7B | 3584 | ~70 | ~58 | Apache 2 | Alibaba, 2024 |
| NV-Embed-v2 | Mistral-7B + latent attn | 4096 | ~72 | ~60 | Non-commercial | NVIDIA, 2024, was #1 for ~3 months |
| `text-embedding-3-large` | (proprietary) | 3072 (MRL) | ~65 | ~55 | API only | OpenAI, Matryoshka |
| `stella_en_1.5B_v5` | Qwen-1.5B | 1024-8192 | ~71 | — | MIT | Small open-weight contender |

### Cost structure

- **Index time**: one encoder forward per chunk. A 7B LLM-encoder at 512 tokens ≈ 100-300ms on an A100, ~30-80ms on H100. For 10M chunks, that's ~8-30 A100-hours.
- **Query time**: one encoder forward + one ANN lookup. For a 7B encoder this is often **the dominant cost** (~50-100ms) — larger than HNSW retrieval on 10M vectors (~5-10ms).
- **Storage**: d × 4 bytes (fp32), d × 2 (fp16), d × 1 (int8), d / 8 (binary). int8-quantized PQ or binary-quantized-then-rescore indexes are standard in 2026 — a 3072-dim vector goes from 12 KB to 384 B (int8) or 384 bits (binary) with <1 point MTEB loss.

### When to pick

Default choice for any RAG system. Covers ~90% of workloads at the lowest total cost. Below ~1M chunks the quality ceiling is mostly set by the model, not the index structure.

---

## 2. Late Interaction: ColBERT, ColBERTv2, PLAID

### Architecture

Instead of pooling to a single vector, ColBERT keeps **one vector per token**. Scoring uses **MaxSim**: for each query token, find the maximum cosine similarity against all document tokens, then sum over query tokens.

```
score(q, d) = Σ_{i ∈ q} max_{j ∈ d} cos(q_i, d_j)
```

This "late interaction" approximates the cross-encoder's full token-to-token attention while keeping the query and document encoded independently — so documents can still be indexed offline.

- **ColBERT (Khattab & Zaharia, 2020)** — BERT-base encoder, 128-dim token vectors.
- **ColBERTv2 (2021)** — adds distillation from a cross-encoder teacher and **residual compression**: centroid + 2-bit residual cuts index size 6-10x.
- **PLAID (2022)** — staged retrieval: centroid pruning → filtered token scoring → full rescoring. Makes ColBERTv2 viable at >100M chunks.

### Numbers

| System | BEIR avg nDCG@10 | Index size / 1M 512-token chunks | Query latency |
|---|---|---|---|
| BM25 | ~42 | ~0.5 GB | <10 ms |
| Dense single-vec (BGE-large) | ~54 | ~4 GB fp32 / 1 GB int8 | ~10-50 ms |
| ColBERTv2 (128-dim, 2-bit residual) | ~57 | ~25-40 GB | ~50-200 ms |
| ColBERTv2 (fp32, uncompressed) | ~57 | ~150 GB | 200-500 ms |

### Cost structure

- Encode cost is similar to a bi-encoder of the same base size (you still run one BERT pass).
- **Index size blows up 20-100x** vs. a single-vector index because you store every token.
- **Query time blows up 10-100x** because MaxSim touches many token vectors per candidate document.
- PLAID's staged pruning brings the *wall-clock* gap closer to 3-10x, not 100x.

### When to pick

ColBERT earns its cost specifically when:
1. **Out-of-domain generalization matters.** Late interaction is the single most robust architecture on BEIR's zero-shot splits — ColBERTv2 beats dense bi-encoders by 3-5 points on TREC-COVID, BioASQ, FiQA.
2. **Short queries, long documents.** The MaxSim structure handles the "find the one relevant span" pattern better than mean-pooled single vectors.
3. **No domain fine-tuning budget.** If you cannot fine-tune a bi-encoder on your data, ColBERT's pretrained quality is usually higher.
4. **Low-millions of chunks.** Above ~100M chunks the index cost becomes prohibitive without aggressive sharding.

Do *not* pick ColBERT when you already plan a two-stage pipeline with a strong reranker — in that case, a cheap bi-encoder + cross-encoder dominates on both quality and cost.

### 2026 status

ColBERT as a pure-text retrieval architecture has mostly been eclipsed by (bi-encoder + cross-encoder reranker) pipelines at the top of MTEB/BEIR. But the **architectural pattern** — late interaction over per-token vectors — is very much alive: ColPali and its successors (§5) are currently the dominant approach for document-image retrieval.

---

## 3. Matryoshka Representation Learning (MRL)

### Architecture

Train a single embedding whose **first k dimensions are each themselves a usable embedding**. The MRL loss (Kusupati et al., 2022) is a weighted sum of contrastive losses evaluated at multiple truncation points, e.g. `[64, 128, 256, 512, 768, 1024, 1536]`. At inference, you pick the dimension that matches your latency/storage budget and simply truncate + L2-renormalize.

### Why it matters

Without MRL, cutting a 3072-dim embedding to 768-dim loses 5-15 MTEB points (random subspace). With MRL training, the drop is <1-2 points over a wide range.

### Representative models

| Model | Trained dims | Default | Practical truncation floor | License |
|---|---|---|---|---|
| OpenAI `text-embedding-3-small` | 1536 | 1536 | 512 (≈ -1.2 MTEB) | API |
| OpenAI `text-embedding-3-large` | 3072 | 3072 | 256 (≈ -3 MTEB, still > text-embedding-ada-002 @ 1536) | API |
| Nomic Embed v1.5 | 768 | 768 | 64 (≈ -3-4 MTEB) | Apache 2 |
| Nomic Embed v2 (MoE) | 768 | 768 | 256 | Apache 2 |
| Jina Embeddings v3 | 1024 | 1024 | 128 | CC-BY-NC 4.0 |
| Jina Embeddings v4 | 2048 | 2048 | 128 | CC-BY-NC 4.0 |
| Voyage-3 / Voyage-3-Large | 1024 / 2048 | 1024 | 256 | API |
| Gemini-Embedding-001 | 3072 | 3072 / 1536 / 768 | 768 (documented) | API |

### Is MRL "free quality"?

Close to free in practice, but with caveats:

- At the **full** trained dim, MRL-trained models are typically ~0.5-1 MTEB point *below* a non-MRL model of the same architecture. You pay a small training-time regularization tax.
- At **intermediate** truncations (e.g. 256-d from a 3072-d model), MRL-trained models beat naive truncation or PCA by 5-10 points.
- The **floor** is model-specific: Nomic Embed v1.5 at 64-d still does ~58 MTEB; OpenAI `text-embedding-3-large` at 256-d still beats `text-embedding-ada-002` at 1536-d.
- Combining MRL with **binary / int8 quantization** is multiplicative: 3072 fp32 → 768 int8 → 192 bytes/chunk, a 64x compression with <3 point loss on typical RAG workloads.

Verdict: **effectively free** for the common use case of a single index served at multiple recall qualities (e.g. fast preview + full reranker candidate fetch).

---

## 4. Sparse Learned Embeddings: SPLADE, uniCOIL

### Architecture

Produce a **vocabulary-sized sparse vector** (e.g. 30522 for BERT WordPiece) where each non-zero position corresponds to a vocab term with a learned weight. SPLADE uses the MLM head's logits over the vocabulary, applies `log(1 + ReLU(·))`, and sums across tokens. A FLOPs-regularization loss keeps the vector sparse.

```
for each token t in doc:
    logits_t = MLM_head(BERT(doc))[t]  # [vocab_size]
w_doc = Σ_t log(1 + ReLU(logits_t))   # [vocab_size], ~30-200 non-zero
score(q, d) = w_q · w_d                # dot product on sparse vectors
```

The result is **BM25-shaped**: a weighted bag of terms. Drops straight into a standard inverted index (Lucene, Tantivy, pisa, Vespa), with learned term weights replacing TF-IDF.

### Variants

| Model | Non-zero terms/doc | BEIR avg | When |
|---|---|---|---|
| uniCOIL | ~100 | ~45 | Simpler, per-token weights only |
| SPLADE-v2 (Formal et al., 2021) | ~120 | ~50 | Standard baseline |
| SPLADE-v3 (2024) | ~80-150 (tunable) | ~52-53 | Improved distillation from cross-encoder |
| BGE-M3 sparse head | ~100 | ~48 | Ships alongside dense + ColBERT heads |

### When to pick

- **Existing Lucene/Elasticsearch/OpenSearch infra.** SPLADE rides on the BM25 inverted-index stack — no vector DB required.
- **Interpretability.** Unlike dense vectors, you can read out *why* a document matched: "this doc matched on `kubernetes=0.8`, `pod=0.5`, `restart=0.4`."
- **Hybrid with dense.** Sparse+dense RRF consistently adds 2-4 nDCG points over either alone.
- **Exact-term matching.** Dense embeddings are notoriously bad at product codes, function names, and rare technical terms; sparse learned embeddings keep the exact-match property of BM25 while adding term expansion ("laptop" → "notebook", "macbook").

Do not pick sparse alone for cross-lingual retrieval or very short documents, where the dense models have a clear advantage.

---

## 5. Multi-Vector / ColPali (Multimodal Document Retrieval)

### The shift

Traditional document retrieval requires a document pipeline: PDF parser → OCR → layout detection → table extraction → chunking → embed. This pipeline is lossy (drops layout, ignores figures, garbles tables) and fragile.

**ColPali (Faysse et al., 2024)** dropped the pipeline. It treats each PDF page as a **single image**, encodes it with a Vision-Language Model (PaliGemma-3B), and produces ~1030 patch-level vectors per page. Retrieval uses ColBERT-style MaxSim between the text query's token vectors and the page's patch vectors.

### Evolution (2024-2026)

| Model | Base VLM | Year | ViDoRe v1 nDCG@5 | License |
|---|---|---|---|---|
| ColPali v1 | PaliGemma-3B | 2024 | ~82 | MIT (model); Gemma license |
| ColQwen2 | Qwen2-VL-2B | 2024 Q4 | ~87 | Apache 2 |
| ColQwen2.5 | Qwen2.5-VL-3B | 2025 | ~89 | Apache 2 |
| ColSmol (2B / 500M) | SmolVLM | 2025 | ~85 / ~82 | Apache 2 |
| ColPali v1.3 / ColModernVBERT | ModernVBERT | 2026 | ~90 | MIT |
| DSE (Document Screenshot Embeddings) | various VLMs | 2024-2025 | ~85 (single-vector variant) | Apache 2 |

### Cost structure

- **Index time**: one VLM forward per page. ~200ms-1s per page on an A100 depending on backbone size.
- **Index size**: ~1030 vectors × 128 dim = ~130 KB/page uncompressed; PLAID-style compression brings this to ~30 KB/page.
- **Query time**: text encoding is cheap, but MaxSim is the same cost story as ColBERT — ~50-200ms over a few thousand candidates.

### When to pick

For any retrieval workload where documents are PDFs/slides/scans with non-trivial layout (financial reports, scientific papers, slide decks, forms), ColPali-family is now the 2026 default. Text-pipeline baselines underperform by 10-20 points on ViDoRe. The "OCR + chunk + embed" pipeline survives only when source documents are clean HTML or Markdown.

### Single-vector alternative

**DSE** collapses the page image to one vector. Index is 100x smaller, query is 100x faster, but loses ~3-5 points vs. ColPali. For large corpora (>1M pages) DSE is often the pragmatic choice; below that, ColPali is clearly better.

---

## 6. Cross-Encoder Rerankers

### Architecture

A cross-encoder takes `[CLS] query [SEP] document [SEP]` as a **single concatenated input**, runs the full transformer (so every query token attends to every document token), and outputs a relevance score from a regression head. Not a retriever — too slow to run over a full index — but devastating as a second stage over ~10-100 candidates.

### Representative rerankers (2026 snapshot)

| Model | Params | Max tokens | Latency (H100, 1 pair @512) | License | Notes |
|---|---|---|---|---|---|
| BGE-reranker-v2-m3 | 568M | 8192 | ~15 ms | Apache 2 | Multilingual default |
| BGE-reranker-v2.5-gemma2-lightweight | 2.5B (distilled) | 8192 | ~30 ms | Apache 2 | New SOTA open in 2025 |
| Jina Reranker v2 multilingual | 278M | 1024 | ~8 ms | CC-BY-NC 4.0 | Fast, 100+ languages |
| Cohere Rerank v3.5 | (proprietary) | 4096 | ~30-80 ms API | API | Reference SOTA closed |
| mxbai-rerank-large-v2 | 1.5B | 8192 | ~25 ms | Apache 2 | Mixedbread, strong open-weight |
| Voyage-rerank-2.5 | (proprietary) | 32000 | ~50 ms API | API | Long-context reranker |
| Qwen3-Reranker-8B | 8B | 32000 | ~80 ms | Apache 2 | Top of MTEB rerank subset, 2026 |

### Always worth a second stage?

Empirically yes, with nuance:

- **Quality**: +3-8 nDCG@10 over the stage-1 retriever is the near-universal finding on BEIR. The only exception is when stage-1 is already ColBERT/ColPali (MaxSim is itself a lightweight cross-interaction) — the gain shrinks to +1-2.
- **Latency**: reranking top-50 with a 500M model adds ~400ms on H100, ~1-2s on CPU. Reranking top-10 with the same model adds 80ms. Nearly every production RAG in 2026 reranks top-10 or top-20.
- **Cost at scale**: reranking is pay-per-query, not pay-per-index. Cheap to launch, but for high-QPS workloads the cross-encoder compute can exceed the stage-1 ANN cost by 5-20x.
- **When to skip**: very short documents (titles, tweets, function names) where bi-encoder quality is already near ceiling; any case where the downstream LLM is going to re-rank via its own attention (e.g. top-K straight to a long-context model).

### 2026 frontier: LLM-as-reranker

A quietly important trend: using a 7B-70B decoder LLM with a "score from 1-10" or pairwise prompt often beats purpose-trained rerankers, at 5-20x the latency. Qwen3-Reranker and the rerank-style use of GPT-5-mini / Gemini-2.5-Flash-Lite are the main productized examples. Worth it for long-context (>8K tokens) or reasoning-heavy queries; overkill for FAQ retrieval.

---

## 7. The 2025-2026 Frontier

### Top of MTEB v2 (English) and MMTEB (Multilingual), early April 2026

| Rank | Model | Org | Params | Dim | Avg (v2 eng) | Avg (MMTEB) | License |
|---|---|---|---|---|---|---|---|
| 1 | Qwen3-Embedding-8B | Alibaba | 8B | 4096 | ~77 | ~71 | Apache 2 |
| 2 | Qwen3-Embedding-4B | Alibaba | 4B | 2560 | ~75 | ~69 | Apache 2 |
| 3 | Gemini-Embedding-001 | Google | ~proprietary | 3072 MRL | ~75 | ~72 | API |
| 4 | Voyage-3-Large | Voyage AI | proprietary | 2048 MRL | ~74 | ~70 | API |
| 5 | NV-Embed-v2 | NVIDIA | 7.8B | 4096 | ~73 | n/a | Non-commercial |
| 6 | Jina Embeddings v4 | Jina | 3.8B (VLM) | 2048 MRL | ~72 | ~69 | CC-BY-NC 4.0 |
| 7 | Linq-Embed-Mistral | Linq | 7B | 4096 | ~72 | — | CC-BY-NC 4.0 |
| 8 | SFR-Embedding-v2 | Salesforce | 7B | 4096 | ~71 | — | CC-BY-NC 4.0 |
| 9 | `text-embedding-3-large` | OpenAI | proprietary | 3072 MRL | ~65 (aging) | ~64 | API |
| 10 | BGE-M3 / BGE-multilingual-gemma2 | BAAI | ~9B | 3584 | ~70 | ~68 | Apache 2 / Gemma |

(Exact scores move weekly; these are rounded tiers, not official rankings.)

### Qwen3-Embedding family (Alibaba, 2025-2026)

- **Architecture**: decoder-only Qwen3 (0.6B / 4B / 8B). Instruction-tuned embedding training with bidirectional attention enabled only during embedding forward. MRL at [768, 1024, 2048, 4096]. 100+ languages, 32K context.
- **Training**: multi-stage — (a) weakly supervised contrastive pretrain on ~150B pairs; (b) supervised fine-tune with hard negatives from Qwen3-Reranker; (c) instruction tuning for task-specific prompts.
- **Why it won**: the reranker-mined hard negatives are substantially better than BM25 hard negatives used by older pipelines. It's not the encoder architecture — it's the data curation.

### Gemini-Embedding-001 (Google, 2025)

- 3072-dim default, MRL to 1536/768. Unified across 100+ languages and code. Task-type parameter (`RETRIEVAL_QUERY`, `RETRIEVAL_DOCUMENT`, `CLASSIFICATION`, `CLUSTERING`, `SEMANTIC_SIMILARITY`, `CODE_RETRIEVAL_QUERY`) swaps a lightweight adapter.
- Notable for strong **code retrieval** performance — the only frontier API that's trained with code as a first-class modality.

### Voyage-3 / Voyage-3-Large (Voyage AI)

- Closed-source, API-only. MRL to 256/512/1024/2048. Emphasis on domain-specific variants (`voyage-code-3`, `voyage-law-3`, `voyage-finance-3`) that outperform generalist models by 3-6 points on their respective verticals.

### Jina Embeddings v4 (Jina AI, late 2025)

- 3.8B VLM-based. Single model supports text, image, and document-image retrieval — positioned as "ColPali-quality for docs + GTE-quality for text" in one index.
- Late-interaction mode available (multi-vector) for the same quality tradeoff as ColBERT.

### Nomic Embed v2 (MoE, 2024 Q4)

- 475M total / 305M active MoE encoder. First open-weight MoE embedding. Matryoshka 768 → 64. Strong multilingual, fully reproducible training data + recipe (Apache 2).

### What's actually new

Five architectural shifts between 2024 and 2026:

1. **Decoder-LLM encoders won.** All of the top 10 are decoder-architecture (Mistral, Qwen, Gemma). BERT-style encoders survive only at the <1B small-efficient tier.
2. **Instruction prefixes are standard.** Models are trained with task-specific instructions (`"Represent this sentence for searching relevant passages:"`), and quality drops 2-5 points if you forget them.
3. **Matryoshka is standard.** Every new frontier model ships MRL — it's no longer a differentiator.
4. **Reranker-mined hard negatives** replaced BM25 hard negatives as the dominant data curation recipe.
5. **Multimodal unification.** 2026 embedding models increasingly handle text + image + doc-image in one model (Jina v4, Gemini, Cohere Embed v4).

---

## 8. Cross-cutting Comparison Tables

### Index size (bytes per chunk, ~512-token chunk, typical production settings)

| Architecture | fp32 | fp16 / bf16 | int8 | binary / 1-bit |
|---|---|---|---|---|
| Dense 768-d | 3 KB | 1.5 KB | 768 B | 96 B |
| Dense 1024-d | 4 KB | 2 KB | 1 KB | 128 B |
| Dense 3072-d (MRL → 768 typical) | 12 KB (full) | 1.5 KB | 768 B | 96 B |
| ColBERTv2 (100 tokens × 128-d) | ~50 KB | 25 KB | 13 KB | ~10 KB (2-bit residual) |
| SPLADE-v3 (~100 non-zero) | ~1.2 KB (sparse) | — | — | — |
| ColPali page (~1030 × 128-d) | ~500 KB | 250 KB | 130 KB | ~30 KB |

### Quality ceilings on BEIR (13-task avg nDCG@10, 2026)

| Stack | BEIR avg |
|---|---|
| BM25 | 42 |
| Dense bi-encoder (BGE-large) | 54 |
| Dense bi-encoder (frontier, Qwen3-8B) | 60 |
| SPLADE-v3 | 53 |
| Hybrid (dense + sparse + RRF) | 57 |
| ColBERTv2 | 57 |
| Dense + cross-encoder rerank | 60 |
| Hybrid + cross-encoder rerank | **62** |
| ColBERTv2 + cross-encoder rerank | 61 |

Ceiling improvement from the best 2026 stack over BM25 is ~20 nDCG points — roughly half from stage-1 encoder quality, half from stage-2 rerank.

### Query latency budget (single query, H100, 1M chunks, HNSW)

| Stage | Typical latency |
|---|---|
| Encode query (1B-model encoder) | 5-10 ms |
| Encode query (7B-model encoder) | 30-80 ms |
| HNSW ANN (1M, ef=64) | 3-8 ms |
| ColBERT MaxSim (top-1000 candidates, PLAID) | 30-80 ms |
| Cross-encoder rerank top-10 (500M) | 50-100 ms |
| Cross-encoder rerank top-50 (500M) | 200-400 ms |
| LLM-as-reranker top-10 (Gemini-2.5-Flash) | 500-1500 ms |

### Hardware requirements (index side, 10M chunks)

| Architecture | GPU-hours to index | Disk for index (compressed) |
|---|---|---|
| MiniLM bi-encoder | ~5 A100-hours | ~5 GB |
| BGE-large bi-encoder | ~40 A100-hours | ~10 GB |
| 7B LLM-encoder (Qwen3-8B etc.) | ~200-400 A100-hours | ~10 GB (int8) |
| ColBERTv2 | ~50 A100-hours | ~300-500 GB |
| ColPali (per page) | ~200-500 A100-hours | ~1-3 TB |

---

## 9. Answering the Key Questions

**Q1. When does ColBERT earn its 10-100x cost over bi-encoder?**

Specifically in three cases: (a) zero-shot retrieval on out-of-domain corpora without fine-tuning budget; (b) short queries over long technical documents where the "one relevant span" pattern dominates; (c) multimodal document retrieval where the ColPali variant is effectively the only competitive architecture. In the general RAG case with in-domain fine-tuning available, a (dense bi-encoder + cross-encoder reranker) pipeline matches or beats ColBERT at lower total cost. The 2026 picture: ColBERT's *direct* use has narrowed, but its *architectural idea* (MaxSim late interaction) is the basis of the ColPali family, which now owns document-image retrieval.

**Q2. Is Matryoshka "free quality" or does it trade off?**

Effectively free for the common single-index-multi-budget deployment. Full-dim MRL models score ~0.5-1 MTEB point below an equivalent non-MRL model, but that cost is recouped many times over by the ability to serve the same index at 64/128/256/512/full dimensions. The combination MRL + int8 + binary rescoring is the current cost-quality frontier — 3072-d fp32 (12 KB) → 768-d int8 (768 B) → 192 B binary, at <3 MTEB points lost. Almost every 2026 frontier model ships MRL; avoiding it is the unusual choice now.

**Q3. Are rerankers always worth a 2nd stage?**

Nearly always, for any system with latency budget >200ms. +3-8 nDCG@10 is a large gain in retrieval terms, and the cost scales only with QPS (not index size). Exceptions: (a) when stage-1 is ColBERT/ColPali, the gain shrinks to +1-2 points; (b) ultra-low-latency applications (<100ms total); (c) when a long-context LLM is going to read all top-K anyway and the reranker is just reordering what the LLM will reorder itself. The 2026 trend is toward *LLM-as-reranker* using small frontier models (Qwen3-Reranker-8B, Gemini-Flash-Lite) — slower than classical rerankers but quality-dominant on hard/reasoning queries.

**Q4. What's the 2026 MTEB frontier actually achieving?**

- MTEB v2 English avg tops out around **77** (Qwen3-Embedding-8B), from ~63 two years ago — roughly a 1-point-per-quarter gain.
- BEIR zero-shot avg tops out around **60 nDCG@10**, up from ~54 in early 2024.
- The gap between open-weight and closed-API has closed to ~1-2 points (Qwen3-Embedding and NV-Embed are open-weight). Closed-API models' remaining moat is specialized verticals (Voyage) and true multimodal unification (Gemini, Cohere Embed v4).
- Per-point improvement cost is rising: it now takes a 7-8B decoder LLM to score at 77. Small-model quality is stuck around 65-68 (snowflake-arctic-embed-m, bge-small tier).
- The qualitative shift is **multimodality unification**, not raw text-only quality. The interesting 2026 work is in one-model-handles-text-image-and-pdf architectures, not in pushing MTEB text-only by another point.

---

## Sources

- [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard) (HuggingFace; accessed 2026-04-15)
- [MTEB v2 paper (Muennighoff et al., 2022)](https://arxiv.org/abs/2210.07316)
- [MMTEB / Massive Multilingual Text Embedding Benchmark (2024)](https://arxiv.org/abs/2502.13595)
- [BEIR benchmark (Thakur et al., 2021)](https://arxiv.org/abs/2104.08663)
- [SBERT paper (Reimers & Gurevych, 2019)](https://arxiv.org/abs/1908.10084)
- [BGE-M3 (Chen et al., 2024)](https://arxiv.org/abs/2402.03216)
- [E5-Mistral (Wang et al., 2024)](https://arxiv.org/abs/2401.00368)
- [GTE-Qwen2 model card](https://huggingface.co/Alibaba-NLP/gte-Qwen2-7B-instruct)
- [NV-Embed-v2 paper (NVIDIA, 2024)](https://arxiv.org/abs/2405.17428)
- [Qwen3-Embedding technical report (Alibaba, 2025)](https://github.com/QwenLM/Qwen3-Embedding)
- [Gemini Embedding technical report (Google, 2025)](https://arxiv.org/abs/2503.07891)
- [ColBERT (Khattab & Zaharia, 2020)](https://arxiv.org/abs/2004.12832)
- [ColBERTv2 (Santhanam et al., 2022)](https://arxiv.org/abs/2112.01488)
- [PLAID (Santhanam et al., 2022)](https://arxiv.org/abs/2205.09707)
- [Matryoshka Representation Learning (Kusupati et al., 2022)](https://arxiv.org/abs/2205.13147)
- [OpenAI text-embedding-3 announcement](https://openai.com/blog/new-embedding-models-and-api-updates) (accessed 2026-04-15)
- [Nomic Embed v2 blog](https://www.nomic.ai/blog/posts/nomic-embed-text-v2) (accessed 2026-04-15)
- [Jina Embeddings v3 (Sturua et al., 2024)](https://arxiv.org/abs/2409.10173)
- [Jina Embeddings v4 announcement](https://jina.ai/news/jina-embeddings-v4) (accessed 2026-04-15)
- [SPLADE (Formal et al., 2021)](https://arxiv.org/abs/2107.05720)
- [SPLADE-v2 (Formal et al., 2021)](https://arxiv.org/abs/2109.10086)
- [SPLADE-v3 (Lassance et al., 2024)](https://arxiv.org/abs/2403.06789)
- [ColPali (Faysse et al., 2024)](https://arxiv.org/abs/2407.01449)
- [ColQwen2 / ColPali model cards](https://huggingface.co/vidore) (accessed 2026-04-15)
- [DSE (Ma et al., 2024)](https://arxiv.org/abs/2406.11251)
- [Cohere Rerank v3.5 docs](https://docs.cohere.com/docs/rerank) (accessed 2026-04-15)
- [BGE-reranker-v2 / v2.5 model cards](https://huggingface.co/BAAI) (accessed 2026-04-15)
- [Jina Reranker v2 blog](https://jina.ai/news/jina-reranker-v2-for-agentic-rag) (accessed 2026-04-15)
- [Mixedbread mxbai-rerank-v2 model card](https://huggingface.co/mixedbread-ai) (accessed 2026-04-15)
- [Voyage AI models docs](https://docs.voyageai.com/docs/embeddings) (accessed 2026-04-15)
