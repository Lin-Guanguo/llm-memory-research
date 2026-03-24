# Per-User Multi-LoRA: Serving, Personalization, and Composition

Last Updated: 2026-03-24

## Overview

Multi-LoRA is the engineering answer to "how do you give N users personalized models without running N copies." One base model serves all users; per-request LoRA adapters provide personalization. The infrastructure is now mature — vLLM, NVIDIA NIM, and multiple commercial platforms support thousands of concurrent adapters on a single GPU.

This document covers: serving infrastructure, per-user adapter generation, production cases, and adapter composition.

---

## Serving Infrastructure

### The Core Idea

```
                   ┌──── LoRA_user_A ────┐
                   │                     │
Request_A ──►  Base Model (frozen)  ──► Response_A
Request_B ──►  + dynamic adapter    ──► Response_B
                   │                     │
                   └──── LoRA_user_B ────┘
```

All requests share the same base model weights. Each request specifies which LoRA adapter to use. The adapter weights are tiny (10-100 MB) compared to the base model (14+ GB for 7B).

### Platform Comparison

| Platform | Max Concurrent Adapters | Latency Overhead | Key Innovation |
|----------|------------------------|-----------------|----------------|
| **vLLM** | Configurable (`--max-loras`) | Minimal (SGMV kernel) | LRU cache (GPU → CPU), runtime load/unload API |
| **S-LoRA** | **2,000** on single A100-80GB | 4x throughput vs vLLM-packed | Unified Paging (KV cache + adapter weights share memory pool) |
| **Punica** | N/A (kernel-level) | **2ms/token** additional | SGMV CUDA kernel: batches operations across different LoRAs |
| **NVIDIA NIM** | N/A | Minimal | CUTLASS batched GEMM with splitK; multi-tier caching (GPU → host) |
| **LoRAX** (Predibase) | 128+ with ~20% latency | 20% at 128 adapters | Tiered weight caching (GPU → CPU → disk), continuous multi-adapter batching |
| **Together AI** | Hundreds (serverless) | ~10% of base throughput loss | Cross-LoRA continuous batching, adapter prefetching |
| **Fireworks AI** | Dynamic | 10-30% TTFT overhead | Cross-Model Continuous Batching via FireAttention |
| **Groq** | Dynamic (enterprise) | Zero (hot-swapping on LPU) | Custom LPU hardware, LoRA hot-swap |
| **Ray Serve** (Anyscale) | Configurable per replica | Minimal | Cloud storage backends (S3, GCS, Azure) for adapter loading |

### Key Academic Systems

**S-LoRA** ([arxiv 2311.03285](https://arxiv.org/abs/2311.03285)) — Three innovations:
1. **Unified Paging**: KV cache and adapter weights share one memory pool (page size = hidden dimension H)
2. **Custom CUDA kernels**: Triton kernels for prefill (variable ranks, non-contiguous memory); modified BGMV for decode
3. **Tensor Parallelism**: LoRA partitioning aligned with Megatron-LM base model

Result: 2,000 adapters on single A100-80GB at 7.6+ req/s. 30x throughput vs HuggingFace PEFT.

**Punica** ([arxiv 2310.18547](https://arxiv.org/abs/2310.18547)) — Introduced SGMV kernel enabling batching across different LoRAs sharing one base model. 12x throughput with only 2ms additional latency. Kernel adopted by LoRAX and vLLM.

**Compressed Multi-LoRA** ([arxiv 2407.00066](https://arxiv.org/abs/2407.00066)) — Joint Diagonalization: factorize each LoRA product B_i·A_i into U·Σ_i·V^T where U, V shared across all adapters. Per-adapter params reduced from r² to r. 1.6x throughput increase, 99%+ preserved quality. Integrated into vLLM.

**ServerlessLoRA** ([arxiv 2505.14468](https://arxiv.org/abs/2505.14468)) — Addresses serverless where 99% of weights are redundantly duplicated. Secure backbone sharing + contention-aware batching. 86% TTFT reduction, 89% cost reduction.

### Real-World Numbers

| Factor | Typical Range |
|--------|--------------|
| Storage per adapter | 10-100 MB (rank 8-32 on 7B model) |
| Latency overhead (dynamic) | 2ms/token (Punica), 10-30% TTFT (Fireworks), ~20% at 128 adapters (LoRAX) |
| Latency overhead (merged) | **Zero** — equivalent to base model |
| Max concurrent (demonstrated) | 2,000 (S-LoRA, A100-80GB) |
| Throughput scaling | Near-linear up to ~100 adapters, then plateaus |

---

## Per-User Adapter Generation

### The Challenge

Creating a LoRA adapter traditionally requires: training data + GPU compute + hours of fine-tuning. This doesn't scale to millions of users. Three approaches bypass this bottleneck:

### Approach 1: Hypernetwork Generation (Sub-Second)

**Sakana AI Doc-to-LoRA** ([arxiv 2602.15902](https://arxiv.org/abs/2602.15902), Feb 2026):

- **Architecture**: Perceiver-based hypernetwork (~309M params, 8 cross-attention blocks)
- **Input**: Document text → frozen base LLM (Gemma-2-2b-it) extracts per-layer activations → hypernetwork maps to rank-8 LoRA matrices targeting MLP layers
- **Speed**: **<1 second** per document (vs 40s oracle context distillation, 100+s traditional CD)
- **Memory**: ~50 MB constant per adapter regardless of document length (vs 12+ GB for full context)
- **Quality**: 83.5% of full-context upper bound on SQuAD. Near-perfect accuracy up to 40K tokens despite training on 2,344-token examples
- **Cross-modal**: Using VLM encoder, transfers image knowledge to text-only model (75% on Imagenette)
- **API**: `model.internalize(doc)` → LoRA adapter
- **Limitation**: Currently only demonstrated on Gemma-2-2b-it. Expensive meta-training upfront

**Profile-to-PEFT (P2P)** ([arxiv 2510.16282](https://arxiv.org/abs/2510.16282), Oct 2025):

- **Architecture**: MLP-based hypernetwork. Input = [user_embedding ‖ module_embedding ‖ depth_embedding] → flattened LoRA A and B matrices
- **User encoding**: Global summary from user history (via LLM) + top-k relevant interactions → sentence embedding (Qwen3-Emb-4B)
- **Speed**: **0.57s per user** (33x faster than OPPU baseline)
- **Quality**: Classification 0.580 vs 0.568 (OPPU), ROUGE-L 0.244 vs 0.221
- **Privacy**: Adapter = compressed user profile. No raw data storage needed
- **Break-even**: Training cost amortized after ~1,450 users

### Approach 2: Piece Assembly (No Training)

**Personalized Pieces (Per-Pcs)** ([EMNLP 2024](https://aclanthology.org/2024.emnlp-main.371/)):

- Decompose per-user PEFT into layer-level "pieces" (each = one LoRA pair B^l, A^l)
- Contributors train pieces → shared pool. New users assemble adapters by scoring pieces with learned gates
- Gate training: ~50 steps on user history
- Assembly: cosine similarity → top-k selection per layer → softmax-weighted combination
- **Storage: ~0.45 MB per user** (only indices + weights) vs 17 MB for OPPU
- 99.28% of OPPU accuracy with 38x smaller storage

### Approach 3: Conversation-to-Adapter

**Apple PLUM** ([arxiv 2411.13405](https://arxiv.org/abs/2411.13405)):

- Augments past conversations into positive/negative QA pairs
- Fine-tunes per-user LoRA with weighted cross-entropy
- 81.5% accuracy across 100 conversations, competitive with RAG
- Focus: inter-conversation knowledge (remembering what was discussed)

**MTA: Merge-then-Adapt** ([arxiv 2511.20072](https://arxiv.org/abs/2511.20072)):

- Stage 1: Build shared Meta-LoRA Bank from anchor users
- Stage 2: Adaptive LoRA Fusion retrieves + merges relevant anchor adapters per target user (no per-user storage)
- Stage 3: LoRA Stacking with ultra-low-rank additional LoRA for few-shot personalization
- +6.67% accuracy, +9.07% F1 vs RAG on LaMP benchmark

### Generation Method Comparison

| Method | Time per User | Storage per User | Training Needed | Quality vs Baseline |
|--------|--------------|-----------------|-----------------|-------------------|
| Traditional SFT | Hours | 10-100 MB | Full fine-tuning | 100% (baseline) |
| Doc-to-LoRA | **<1s** | ~50 MB | Pre-train hypernetwork once | 83.5% of full-context |
| Profile-to-PEFT | **0.57s** | ~50 MB | Pre-train hypernetwork once | ~102% of OPPU |
| Personalized Pieces | ~50 steps | **0.45 MB** | Gate training only | 99.3% of OPPU |
| Apple PLUM | Minutes | ~50 MB | Per-user fine-tuning | Competitive with RAG |
| MTA | Minutes | Near-zero (shared bank) | Anchor bank + stacking | +6.67% vs RAG |

---

## Multi-LoRA Composition

Can you combine multiple LoRA adapters? Yes, through three approaches:

### A. Weight Merging (Pre-Inference)

Combine adapter weights into a single adapter before serving:

| Method | How | When to Use |
|--------|-----|-------------|
| **Linear (Task Arithmetic)** | Weighted sum: A_merged = √w₁·A₁ + √w₂·A₂ | Same-rank, simple combination |
| **Concatenation (CAT)** | Concat along rank dimension. Exact decomposition | **Best baseline**, different ranks OK |
| **SVD** | Compute merged delta, approximate via SVD | Different ranks, configurable output |
| **TIES** | Prune small values → elect majority sign → disjoint merge | Subject + style combos |
| **DARE** | Random pruning with 1/density rescaling → linear/TIES merge | Diverse task combos. Density 0.7-0.8 |

API: `model.add_weighted_adapter(adapters=[...], weights=[...], combination_type="ties", density=0.5)`

LoRA Soups ([arxiv 2410.13025](https://arxiv.org/abs/2410.13025), COLING 2025): CAT (concatenation with optimal weighting) consistently outperforms other merging techniques.

### B. Runtime Stacking (Sequential Application)

Apply multiple adapters in one forward pass via PEFT's `set_adapters()`. Practical limit: 2-3 stacked adapters before quality degrades. Adapters can "fight each other."

### C. Learned Routing (MoLoRA)

**MoLoRA** ([arxiv 2603.15965](https://arxiv.org/abs/2603.15965), Mar 2026):
- Per-token adapter routing via 2-layer MLP router
- Each token classified and routed to the most relevant adapter
- Work = O(N) for N tokens vs O(K·N) for per-sequence routing
- **Qwen3-1.7B + MoLoRA exceeds Qwen3-8B** on four reasoning benchmarks while being 4.7x smaller
- Uses grouped GEMM identical to MoE infrastructure

### LoRA and Catastrophic Forgetting

"LoRA Learns Less and Forgets Less" ([arxiv 2405.09673](https://arxiv.org/abs/2405.09673)):
- LoRA underperforms full fine-tuning on target tasks BUT **preserves source-domain performance much better**
- This makes LoRA inherently suited for continual personalization
- Mitigation strategies for sequential LoRA training: MoE-based (SMoLoRA), semantic routing (SoLA), tree organization (TreeLoRA)

---

## Production Cases

### Convirza (Call Center Analytics, via Predibase/LoRAX)

- Transitioned from Longformer to fine-tuned Llama-3-8b with multi-LoRA
- **60+ specialized adapters** for different performance indicators, one base model
- Results: **10x cost reduction** vs OpenAI, 8% F1 improvement, 80% throughput increase
- Trained and deployed 20+ adapters in first month

### Phonely (AI Phone Support, via Maitai + Groq)

- GroqCloud LoRA hot-swapping with dozens of specialized adapters
- **73.4% TTFT reduction**, 74.6% completion time reduction
- Accuracy: 81.5% → **99.2%** (surpassing GPT-4o's 94.7%)
- One call center replaced 350 human agents

### DoorDash (Personalized Recommendations)

- Uses LoRA/QLoRA fine-tuning with Ray for **domain-specific** models
- Per-user personalization is RAG-based (hierarchical RAG, Semantic IDs), not per-user LoRA
- LLMs assist with query rewriting and recommendation explanation
- Multi-LoRA is per-task, not per-user

### Federated LoRA (Research Stage)

| System | Scale | Key Innovation |
|--------|-------|----------------|
| **Google Gboard** | 30+ models, 7+ languages | DP-FTRL aggregation, epsilon ≤ 1 achieved |
| **FwdLLM** | LLaMA-7B on mobile | Backprop-free, 1.5GB peak memory, 14.6x memory reduction |
| **FlexLoRA** | Thousands of clients | Variable-rank LoRA + SVD aggregation |
| **Tether QVAC** | Smartphone fine-tuning | 125M in ~10min, 1B in ~78min on Samsung S25 |

All federated systems are for small models or research-stage for LLMs. No production federated LLM fine-tuning exists yet.

---

## Connection to Continuous Learning

Multi-LoRA is the **engineering infrastructure layer** that makes per-user continuous learning scalable:

1. **Serving is solved.** 2,000 concurrent adapters on one GPU, 2ms overhead per token. The bottleneck is no longer serving but adapter creation.

2. **Adapter generation is the new frontier.** Doc-to-LoRA (<1s per document) and Profile-to-PEFT (0.57s per user) mean adapters can be generated nearly as fast as retrieval. This blurs the line between RAG and fine-tuning.

3. **Composition enables layered personalization.** Imagine: base model + personality LoRA + domain LoRA + user preference LoRA, composed via TIES or MoLoRA routing. This is the "three-layer personality stack" from personality-engineering.research.md.

4. **LoRA's forgetting profile is a feature, not a bug.** "Learns less, forgets less" means LoRA adapters can be updated incrementally without destroying the base model's capabilities.

## References

### Serving Infrastructure
- [vLLM LoRA Docs](https://docs.vllm.ai/en/latest/features/lora/)
- [S-LoRA — arxiv 2311.03285](https://arxiv.org/abs/2311.03285), [LMSYS Blog](https://lmsys.org/blog/2023-11-15-slora/)
- [Punica — arxiv 2310.18547](https://arxiv.org/abs/2310.18547)
- [LoRAX — Predibase Blog](https://predibase.com/blog/lora-exchange-lorax-serve-100s-of-fine-tuned-llms-for-the-cost-of-one), [GitHub](https://github.com/predibase/lorax)
- [Compressed Multi-LoRA — arxiv 2407.00066](https://arxiv.org/abs/2407.00066)
- [ServerlessLoRA — arxiv 2505.14468](https://arxiv.org/abs/2505.14468)
- [NVIDIA NIM LoRA Blog](https://developer.nvidia.com/blog/seamlessly-deploying-a-swarm-of-lora-adapters-with-nvidia-nim)
- [Together AI Serverless Multi-LoRA](https://www.together.ai/blog/serverless-multi-lora-fine-tune-and-deploy-hundreds-of-adapters-for-model-customization-at-scale)
- [Fireworks Multi-LoRA](https://fireworks.ai/blog/multi-lora)
- [Groq LoRA Docs](https://console.groq.com/docs/lora)
- [Ray/Anyscale Multi-LoRA](https://docs.anyscale.com/llm/serving/multi-lora)

### Per-User Adapter Generation
- [Sakana AI Doc-to-LoRA — arxiv 2602.15902](https://arxiv.org/abs/2602.15902), [Blog](https://pub.sakana.ai/doc-to-lora/), [GitHub](https://github.com/SakanaAI/doc-to-lora)
- [Profile-to-PEFT — arxiv 2510.16282](https://arxiv.org/abs/2510.16282)
- [Personalized Pieces — EMNLP 2024](https://aclanthology.org/2024.emnlp-main.371/)
- [Apple PLUM — arxiv 2411.13405](https://arxiv.org/abs/2411.13405)
- [MTA — arxiv 2511.20072](https://arxiv.org/abs/2511.20072)

### Composition
- [HuggingFace PEFT Merging](https://huggingface.co/blog/peft_merging)
- [MoLoRA — arxiv 2603.15965](https://arxiv.org/abs/2603.15965)
- [LoRA Soups — arxiv 2410.13025](https://arxiv.org/abs/2410.13025)
- [LoRA Learns Less and Forgets Less — arxiv 2405.09673](https://arxiv.org/abs/2405.09673)

### Production Cases
- [Convirza Case Study — Predibase](https://predibase.com/blog/convirza-case-study)
- [Phonely + Groq](https://www.phonely.ai/blogs/phonely-sets-new-benchmark-for-ai-phone-support-with-lightning-fast-model-inference-through-maitai-and-groq)
- [DoorDash KDD Blog](https://careersatdoordash.com/blog/doordash-kdd-llm-assisted-personalization-framework/)

### Federated LoRA
- [Google Gboard FL — ACL 2023](https://aclanthology.org/2023.acl-industry.60/)
- [FwdLLM — USENIX ATC 2024](https://www.usenix.org/conference/atc24/presentation/xu-mengwei)
- [FlexLoRA — NeurIPS 2024](https://arxiv.org/abs/2402.11505)
- [Tether QVAC Fabric](https://tether.io/news/tether-data-introduces-qvac-fabric-llm-the-edge-first-llm-inference-runtime-and-generalized-llm-lora-fine-tuning-framework-for-modern-ai-models-on-heterogeneous-gpus-smartphones-laptops-and-server/)
