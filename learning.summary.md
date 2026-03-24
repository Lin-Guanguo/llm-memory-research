# Continuous Learning & Personality Training: Research Summary

Last Updated: 2026-03-24

---

## Studied Systems

| System | Type | Approach | Source |
|--------|------|----------|--------|
| [Neuro-sama](https://vedal.ai/) | AI VTuber (1 character) | Iterative batch SFT on curated stream data | `neuro-sama.research.md` |
| [Character.AI](https://character.ai/) | Character platform (millions of characters) | DPO + personality constitutions (meta-character training) | `character-ai.research.md` |
| 5 open-source VTuber recreations | Community projects | Prompt engineering only, no weight modification | `neuro-sama.research.md` |
| SillyTavern community | Roleplay platform | Character cards (PLists, Ali:Chat) | `personality-engineering.research.md` |
| BIG5-CHAT (ACL 2025) | Academic | SFT/DPO on 100K Big Five dialogues | `personality-engineering.research.md` |
| FinePE | Academic | MoE-LoRA, per-subtrait modules | `personality-engineering.research.md` |
| PERSONA | Academic | Contrastive activation analysis + vector algebra | `personality-engineering.research.md` |
| SAS Personality Sliders | Academic | Sequential Adaptive Steering | `personality-engineering.research.md` |
| Anthropic Persona Vectors | Industry research | Monitoring + steering + vaccination | `personality-engineering.research.md` |

---

## Core Finding: Three Paradigms for Personality

Personality engineering has three distinct paradigms, each operating at a different depth:

```
           ┌─────────────────────────────────────────────────┐
           │            Depth of Intervention                │
           │                                                 │
 Prompt    │  "Act as a pirate"                              │
 ──────────│  ✓ Zero cost, instant switch                    │
           │  ✗ Can't override alignment                     │
           │  ✗ Drifts over long context                     │
           │  ✗ 162-persona study: effect "largely random"   │
           │                                                 │
 Activation│  Inject α·v into residual stream                │
 ──────────│  ✓ Matches SFT performance (9.60 vs 9.61)      │
           │  ✓ Zero-parameter, instant composition          │
           │  ✗ Requires white-box model access              │
           │  ✗ Safety-aligned traits resist activation      │
           │  ? Long-context durability untested             │
           │                                                 │
 Weight    │  SFT / DPO / LoRA fine-tuning                   │
 ──────────│  ✓ Overrides alignment layer                    │
           │  ✓ Stable over long context                     │
           │  ✓ Human-like trait distributions               │
           │  ✗ Requires training data + GPU                 │
           │  ✗ Catastrophic forgetting on retraining        │
           │  ✗ Inflexible (need new adapter per persona)    │
           └─────────────────────────────────────────────────┘
```

### Quantitative Comparison

| Method | PersonalityBench | Model Access | Cost | Multi-trait |
|--------|-----------------|--------------|------|-------------|
| Prompting | 8.39 | API OK | Zero | Fragile |
| Activation (PERSONA) | **9.60** | White-box | Low | Algebraic |
| SFT (fine-tuning) | **9.61** | Weights | High | 2^N models |
| MoE-LoRA (FinePE) | Outperforms SFT by 29% on BFI | Weights | Medium | Per-trait modules |

**Headline result**: Activation engineering matches fine-tuning on personality benchmarks, without any gradient updates.

---

## Two Production Architectures

Only two systems have confirmed weight-level personality training in production:

### Architecture A: Per-Character Training (Neuro-sama)

```
Stream interactions → Vedal curates data → SFT on 2B model → Deploy
                              ↑                                  │
                              └──────────────────────────────────┘
```

- **Model**: 2B params, q2_k quantization (latency-driven)
- **Personality**: Core traits in weights, situational behavior in prompts
- **Learning**: Iterative batch SFT, human-in-the-loop, irregular cadence
- **Scale**: 1 character (2 with Evil Neuro)

### Architecture B: Meta-Character Training (Character.AI)

```
Layer 4: User feedback (star ratings → response selection, no weight change)
Layer 3: User prompt (character definition via Prompt Poets)
Layer 2: Character Training (DPO + "I am..." constitutions → weights)  ★ moat
Layer 1: Foundation model (custom → now hybrid with third-party)
```

- **Model**: Proprietary, param count unknown, MQA, native int8
- **Personality**: Trained to generalize from ANY character description
- **Learning**: Character Training teaches the mapping「description → behavior」
- **Scale**: Millions of characters, 30K msg/s, 95% KV cache hit

### The Fundamental Difference

| Dimension | Per-Character (Neuro-sama) | Meta-Character (Character.AI) |
|-----------|---------------------------|-------------------------------|
| Training goal | BE a specific character | ADOPT any character from description |
| New character cost | Full retraining | Zero (just write a description) |
| Personality depth | Deepest (in weights) | Deep (in weights, but generalized) |
| Scalability | O(N) models for N characters | O(1) model for N characters |
| Data source | Curated real interactions | Synthetic constitutional data |

Both approaches are confirmed in production. **Anthropic uses a similar method to Character.AI for Claude** (Amanda Askell: "It's like constitutional AI, but without any human data").

---

## What the Open-Source Community Tells Us

5 community projects attempt to recreate Neuro-sama. Key findings:

1. **Pipeline is the easy part.** All projects successfully wire LLM + TTS + STT + avatar.
2. **Prompt engineering hits a ceiling.** Aligned base models resist behaviors (swearing, aggression) even when explicitly prompted. This is the clearest evidence for why fine-tuning adds value.
3. **Nobody attempts iterative learning.** Zero projects implement deploy → collect → retrain.
4. **Memory is the missing piece.** Only moeru-ai/airi attempts cross-session memory (DuckDB + PGVector, WIP). All others have none.

---

## Connection to Pillar 3

In `findings.md`, Pillar 3 (Continuous Learning) was described as "unexplored." This research partially fills that gap:

### What We Now Know

**Pillar 3 is not a single problem.** It decomposes into at least three sub-problems:

| Sub-problem | What changes | Production example |
|-------------|--------------|-------------------|
| **Personality training** | How the model responds (style, tone, traits) | Character.AI, Neuro-sama |
| **Knowledge updating** | What the model knows (facts, skills) | None confirmed in production |
| **Adaptation** | Per-user behavioral preferences | Character.AI feedback (indirect) |

Current production systems only address personality. Knowledge updating and per-user adaptation remain in the domain of external memory (Pillar 1+2).

### The Research-to-Production Gap

Academic methods are mature:
- BIG5-CHAT proves SFT/DPO work for personality (ACL 2025)
- PERSONA proves activation engineering works without training
- FinePE proves per-trait LoRA composition works

But production deployment is rare because:
1. **Prompting is "good enough"** for most commercial use cases
2. **ROI is hard to quantify** — personality quality lacks standard metrics
3. **Evaluation is unsolved** — "is the personality right?" is subjective
4. **Those who do it don't publish** — competitive moat

### Activation Engineering as the Missing Link

Between external memory (Pillar 1) and weight updates (Pillar 3), activation engineering offers a middle ground:

```
Pillar 1: External Memory    ←→  Facts, knowledge (Mem0, Letta)
                                  Cheap, auditable, instant update
                                  Shallow (reconstructed from prompts)

    NEW: Activation Layer    ←→  Personality, style, behavioral traits
                                  No training needed, instant composition
                                  Deep (manipulates internal representations)
                                  Requires white-box model access

Pillar 3: Weight Updates     ←→  Core personality, alignment override
                                  Most persistent, hardest to change
                                  Expensive, risk of catastrophic forgetting
```

### Anthropic's Vaccination Concept

The most forward-looking finding: Anthropic's "preventative steering" — injecting persona vectors during training to make models resistant to acquiring specific traits. This has implications for:
- **Catastrophic forgetting**: "vaccinate" personality traits before retraining on new data
- **Safety alignment**: prevent personality drift during continual learning
- **Production deployment**: monitor personality vectors for drift detection

---

## Updated Pillar 3 Definition

Based on this research, the original Pillar 3 description in `findings.md` should be expanded:

**Original**: "Write knowledge into model weights so it persists without external storage."

**Updated**: Pillar 3 encompasses three intervention depths:
1. **Activation-level** — Modify personality/behavior at inference time without weight changes (PERSONA, SAS, Anthropic persona vectors). Training-free, composable, but requires white-box access.
2. **Adapter-level** — Per-trait or per-user LoRA modules, dynamically loaded (FinePE, Multi-LoRA serving). Moderate cost, good scalability.
3. **Weight-level** — Full SFT/DPO on personality-annotated or constitutional data (Character.AI, Neuro-sama, BIG5-CHAT). Deepest intervention, highest cost.

Production systems combine multiple layers: Character.AI uses weight-level (Layer 2) + prompt-level (Layer 3) + feedback (Layer 4).

---

## Multi-LoRA: Per-User Personalization at Scale

Full details: `multi-lora.research.md`

### Serving Infrastructure (Solved)

Multi-LoRA serving is production-ready. S-LoRA demonstrates 2,000 concurrent adapters on a single A100-80GB. vLLM, NVIDIA NIM, Together AI, Fireworks, and Groq all support dynamic per-request adapter switching with minimal overhead (2ms/token via Punica SGMV kernel).

### Per-User Adapter Generation (Emerging)

The bottleneck has shifted from serving to **adapter creation**. Three approaches bypass traditional fine-tuning:

| Method | Time per User | Storage | Key Innovation |
|--------|--------------|---------|----------------|
| Doc-to-LoRA (Sakana AI) | **<1s** | ~50 MB | Perceiver hypernetwork, 83.5% of full-context quality |
| Profile-to-PEFT | **0.57s** | ~50 MB | MLP hypernetwork from user embedding |
| Personalized Pieces | ~50 steps | **0.45 MB** | Assemble from shared piece pool, no training |

### Adapter Composition

Multiple LoRA adapters can be combined: weight merging (CAT/TIES/DARE), runtime stacking, or learned routing (MoLoRA). MoLoRA enables Qwen3-1.7B + 4 adapters to exceed Qwen3-8B.

### Production Cases

- **Convirza**: 60+ adapters on Llama-3-8b, 10x cost reduction vs OpenAI
- **Phonely**: LoRA hot-swapping on Groq, 99.2% accuracy (surpassing GPT-4o)
- **DoorDash**: LoRA for domain models, but per-user personalization remains RAG-based

---

## Hybrid Memory → Weight Pipeline

Full details: `hybrid-memory-weight.research.md`

### Current State

**No production system implements the full memory-to-weight pipeline.** The closest analogs:
- **Letta**: Explicit roadmap for token-to-weight distillation. Shipped `learning-sdk` and skill learning (36.8% improvement)
- **Cursor**: Memory-to-weight for retrieval layer (12.5% QA accuracy improvement), not LLM
- **Google Gboard**: Full federated loop, but small on-device models, not LLMs

### Five Proposed Architectures

| Architecture | Source | Trigger | Forgetting Mitigation |
|-------------|--------|---------|----------------------|
| **Token-first distillation** | Letta | Accumulated volume | Memory survives model upgrades |
| **Instant injection** | Doc-to-LoRA | Per-document (<1s) | N/A (additive, not destructive) |
| **Continuous self-instruct** | AWS | Scheduled (quarterly) | Human-in-the-loop review |
| **Self-evolving agent** | EvolveR/MemRL | Continuous (online/offline) | RL-based policy updates |
| **Sparse memory fine-tuning** | Jessy Lin et al. | Per-item or batched | **11% forgetting vs 89% full FT** |

### The Catastrophic Forgetting Breakthrough

Sparse memory fine-tuning ([arxiv 2510.15103](https://arxiv.org/abs/2510.15103)) reduces forgetting from 89% to 11% by updating only memory slots highly activated by new knowledge. Combined with the ICLR 2025 finding that much "forgetting" is actually alignment degradation (reversible with 50-100 samples), the memory-to-weight pipeline may be more viable than previously thought.

### Emerging Consensus

The field converges on **token-first, weight-second**: store learning in token/memory space (auditable, portable, model-agnostic), distill into weights only for efficiency. Letta's position: "The weights are temporary; the learned context is what persists."

---

## Open Questions

1. **Does activation engineering scale to larger models?** All results are on 7B-8B. Do persona vectors remain orthogonal at 70B+?

2. **Can the three layers be combined?** Memory (facts) + activation steering (personality) + LoRA (domain knowledge) + prompts (situation). No one has built a four-layer personalization stack.

3. **When does distillation become worth it?** If retrieval costs X per query and distillation costs Y per training run, at what query volume does memory-to-weight pay off?

4. **Can Doc-to-LoRA handle personality, not just facts?** Current results are on factual QA. Can hypernetworks generate personality adapters as effectively as DPO-based character training?

5. **Is Letta's learning-sdk the first step toward the full pipeline?** If they ship weight distillation, it would be the first complete memory-to-weight implementation.

6. **Can sparse memory fine-tuning work with standard transformers?** The 11% vs 89% result requires non-standard architecture with memory layers.
