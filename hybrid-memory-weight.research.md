# Hybrid Memory → Weight Pipeline: From External Memory to Model Weights

Last Updated: 2026-03-24

## Overview

The hybrid memory-to-weight pipeline is the logical endpoint of combining Pillar 1 (external memory) with Pillar 3 (weight updates): accumulate knowledge in external storage over time, then periodically distill it into model weights.

**Key finding: No production system implements the full pipeline today.** But the concept is well-articulated (Letta), the components exist (Doc-to-LoRA, sparse memory fine-tuning), and adjacent production systems (Cursor, Google Gboard) prove that interaction-data-to-weight pipelines work for specific subsystems.

---

## Current State: Nobody Does This (Yet)

| System | Does memory-to-weight? | What it actually does |
|--------|----------------------|----------------------|
| **Mem0** | No | Fact extraction → vector DB → retrieval. No weight update path |
| **Letta** | Proposed (not shipped) | Token-space memory + skill learning. Explicit roadmap for weight distillation |
| **Graphiti** | No | Bi-temporal knowledge graph. Pure retrieval |
| **Supermemory** | No | LLM-as-retriever. Pure retrieval |
| **MemOS** | Architecturally supports it | Three-layer model (plaintext → activation → parametric). But parametric layer is a blueprint, not production code |
| **Neuro-sama** | Closest analog | Deploy → collect interactions → human curates → SFT → redeploy. But human-curated, personality-only |
| **Cursor** | Yes, for retrieval model | Session traces → train custom embedding model. Not LLM weight updates |
| **Google Gboard** | Yes, federated | User typing → on-device training → server aggregation. But small models, not LLMs |

---

## Five Proposed Architectures

### Architecture A: Token-First Distillation (Letta)

The most articulated proposal, from Letta (formerly MemGPT). Published in "[Continual Learning in Token Space](https://www.letta.com/blog/continual-learning)."

**Core thesis**: An LLM agent = **(θ, C)** where θ = weights, C = context. Token-space memory should be primary; weight updates secondary.

```
Session interactions
    │
    ▼
Token-space memory accumulation
(human-readable, model-agnostic, auditable)
    │
    ▼
"Sleep-time compute": restructure memories between sessions
    │
    ▼
Generate synthetic data from memories
(hypothetical conversations for SFT, or rubrics for RL)
    │
    ▼
Distill into LoRA adapters
    │
    ▼
Deploy updated model
(memory persists across model generations)
```

**Key insight**: "The weights are temporary; the learned context is what persists." Memory should survive model upgrades — if you switch from GPT-4 to Claude, your memories should transfer. Weights can't do this.

**What's shipped today**:
- [learning-sdk](https://github.com/letta-ai/learning-sdk): Drop-in SDK (`pip install agentic-learning`) adding continual learning to any LLM agent
- [Skill Learning](https://www.letta.com/blog/skill-learning): Skills learned from agent trajectories, stored as `.md` files. Boosts Terminal Bench 2.0 by **36.8%**. Skills are model-agnostic — stronger models create skills that weaker models use
- Weight distillation step: **explicitly on roadmap, not yet implemented**

### Architecture B: Instant Injection (Sakana AI Doc-to-LoRA)

Skip the accumulation step entirely. Convert documents to LoRA adapters in <1 second.

```
New document/memory
    │
    ▼
Hypernetwork (~309M params, Perceiver-based)
    │
    ▼
LoRA adapter (rank-8, <1 second generation)
    │
    ▼
Inject into frozen base LLM
```

- No training loop needed at deployment time
- 83.5% of full-context upper bound on SQuAD
- ~50 MB per adapter regardless of document length
- Long documents: chunk → per-chunk LoRA → concatenate along rank dimension
- **Limitation**: Requires expensive pre-training of hypernetwork (~309M params). Currently only on Gemma-2-2b-it

See [multi-lora.research.md](./multi-lora.research.md) for full details.

### Architecture C: Continuous Self-Instruct (AWS)

The most production-ready reference architecture. [Published Feb 2025](https://aws.amazon.com/blogs/machine-learning/llm-continuous-self-instruct-fine-tuning-framework-powered-by-a-compound-ai-system-on-amazon-sagemaker/).

```
Knowledge base / document corpus
    │
    ▼
LLM generates synthetic Q&A training data (self-instruct)
    │
    ▼
SFT on generated data
    │
    ▼
Human-in-the-loop feedback
    │
    ▼
RLHF/RLAIF alignment
    │
    ▼
Evaluate and deploy
```

Built on SageMaker + DSPy + Bedrock. Open-source: [github.com/aws-samples/amlc-2024-tutorial-continuous-fine-tuning-compound-ai](https://github.com/aws-samples/amlc-2024-tutorial-continuous-fine-tuning-compound-ai). Reference architecture, not a running production service.

### Architecture D: Self-Evolving Agent Loop (EvolveR/MemRL)

Agents that improve from their own experience, without external supervision.

```
Agent interacts with environment
    │
    ▼
Collect trajectories (successes + failures)
    │
    ▼
Offline: distill trajectories into strategic principles
    │
    ▼
Online: retrieve principles for guided reasoning
    │
    ▼
Policy Evolution: RL on collected trajectories to update weights
```

- **EvolveR** ([arxiv 2510.16079](https://arxiv.org/abs/2510.16079)): Two-stage lifecycle — offline self-distillation + online principle-guided reasoning
- **MemRL** ([arxiv 2601.03192](https://arxiv.org/abs/2601.03192)): Runtime RL on episodic memory
- **MoE-CL** ([arxiv 2509.18133](https://arxiv.org/abs/2509.18133)): Dedicated LoRA expert per task + GAN-based filtering. **Production validated: 15.3% reduction in manual review costs at Tencent Video**

### Architecture E: Sparse Memory Fine-Tuning

The most forgetting-resistant approach. Requires non-standard model architecture.

```
Accumulate new knowledge items
    │
    ▼
Identify memory slots highly activated by new knowledge
(relative to pretraining usage)
    │
    ▼
Update ONLY those slots (sparse update)
    │
    ▼
Result: 11% forgetting vs 89% full fine-tune
```

From [arxiv 2510.15103](https://arxiv.org/abs/2510.15103) (Jessy Lin et al., Oct 2025). Uses **memory layers** (sparse attention lookup into learned key-value pool) instead of standard FFN layers. Architecturally designed for "accumulate then train."

**Limitation**: Requires memory-layer model architecture, not standard transformers.

---

## Adjacent Production Systems

### Cursor: Memory-to-Weight for Retrieval

The most direct production example of the hybrid pattern, applied to the retrieval model (not LLM):

```
Agent coding sessions (production)
    │
    ▼
Session traces: which files opened, which searches ran, which code was useful
    │
    ▼
LLM acts as ranking oracle: scores content usefulness at each step
    │
    ▼
Train custom embedding model to align with LLM rankings
    │
    ▼
Deploy improved retrieval → better code suggestions
```

**Results**: 12.5% average QA accuracy improvement (range 6.5-23.5%), 2.2% reduction in dissatisfied follow-ups.

This IS memory-to-weight, just for the **retrieval layer** instead of the generation layer. The LLM weights never change.

### Google Gboard: Federated Weight Updates

The gold standard for distributed continuous learning, but on small models:

| Dimension | Value |
|-----------|-------|
| Scale | 30+ models, 7+ languages, 15+ countries |
| Architecture | On-device training → encrypted updates → DP-FTRL server aggregation |
| Privacy | Formal DP guarantees, epsilon ≤ 1 achieved (Brazilian Portuguese) |
| Training cadence | ~2,000 rounds over 14 days, 12,000+ devices per round |
| Model size | Small on-device language models (not LLMs) |

Gboard proves the full loop works: user interactions → on-device learning → aggregate → deploy. But the models are small (next-word prediction), not general-purpose LLMs.

---

## The Catastrophic Forgetting Problem

The central blocker for memory-to-weight pipelines.

### Quantitative Forgetting Rates

| Method | Forgetting (NaturalQuestions F1 drop) |
|--------|--------------------------------------|
| Full fine-tuning on new facts | **89%** |
| LoRA fine-tuning | **71%** |
| Sparse memory fine-tuning | **11%** |

### Key Finding: Spurious Forgetting (ICLR 2025)

[openreview.net/forum?id=ScI7IlKGdI](https://openreview.net/forum?id=ScI7IlKGdI)

Much "forgetting" is actually **alignment degradation**, not true knowledge loss:
- Internal representations remain intact
- The alignment between representations and output layer is disrupted
- Can be reversed with minimal fine-tuning (50-100 samples, 1-3 epochs)
- **Mitigation**: Freezing bottom layers yields substantial improvements

This means the memory-to-weight pipeline may be more viable than forgetting rates suggest — the knowledge is preserved, just misaligned.

### Mitigation Strategies

| Strategy | How | Source |
|----------|-----|--------|
| **Sparse memory fine-tuning** | Update only highly-activated memory slots | [arxiv 2510.15103](https://arxiv.org/abs/2510.15103) |
| **Self-Synthesized Rehearsal** | LLM generates synthetic rehearsal data from its own knowledge | [ACL 2024](https://aclanthology.org/2024.acl-long.77/) |
| **LoRA (inherent property)** | "Learns less and forgets less" — low-rank constraint preserves base | [arxiv 2405.09673](https://arxiv.org/abs/2405.09673) |
| **Freezing bottom layers** | Prevents alignment degradation in early layers | [ICLR 2025](https://openreview.net/forum?id=ScI7IlKGdI) |
| **Anthropic vaccination** | Inject persona vectors during training to protect traits | [Anthropic Research](https://www.anthropic.com/research/persona-vectors) |

---

## RAG-to-Fine-Tune: Academic Approaches

### Fine-Tuning with RAG (ICLR 2026)

[arxiv 2510.01375](https://arxiv.org/abs/2510.01375) — The closest academic analog to the hybrid pipeline:
1. Run base agents, collect failures
2. Extract generalizable "hints" from failures
3. Use hints to generate better teacher trajectories via one-shot retrieval
4. Distill trajectories into student models with hints removed
5. Student internalizes knowledge that was previously external (RAG)

### DRAG: Distilling RAG for SLMs (ACL 2025)

[ACL 2025](https://aclanthology.org/2025.acl-long.358/): Teacher LLM generates N textual evidences per question → knowledge graph + ranked evidence distilled into small models. 94.1% on ARC-C, exceeding Self-RAG by 25-27%.

### Prompt Distillation (TMLR)

[arxiv 2412.14964](https://arxiv.org/abs/2412.14964): Self-distillation to internalize document knowledge without teacher models. Closed-book matches open-book RAG on SquadShifts.

### Knowledge Editing (ROME/MEMIT)

Direct weight editing for factual corrections:
- **ROME**: Rank-one update to specific MLP layers
- **MEMIT**: Scales to thousands of simultaneous edits
- **Limitation**: Degrades after ~10-40 edits. Not suitable for continuous learning — designed for targeted corrections, not accumulative knowledge

---

## Emerging Consensus

Based on all surveyed systems, the field is converging on a **token-first, weight-second** approach:

```
                        Priority
                           ▲
                           │
  Token-space memory       │  ★ Primary
  (facts, skills, .md)     │  - Instant update
                           │  - Auditable, portable
                           │  - Model-agnostic
                           │  - Survives model upgrades
                           │
  Adapter generation       │  ● Secondary
  (Doc-to-LoRA, P2P)      │  - Sub-second generation
                           │  - Bridges retrieval and fine-tuning
                           │  - Per-user scalable
                           │
  Weight distillation      │  ○ Tertiary (future)
  (SFT/DPO from memories) │  - Periodic, batched
                           │  - For efficiency (reduce retrieval cost)
                           │  - Highest forgetting risk
                           │
                           └──────────────────────────────►
                                    Intervention Depth
```

**Letta's position summarizes it**: "The weights are temporary; the learned context is what persists."

This matches what we observe in production:
- All memory systems (Mem0, Letta, Graphiti) store in token space
- Cursor trains retrieval embeddings, not LLM weights
- Gboard does weight updates but only for small specialized models
- Neuro-sama is the only LLM weight-update case, and it's human-curated

---

## Open Questions

1. **When does distillation become worth it?** If retrieval costs X per query and distillation costs Y per training run, at what query volume does distillation pay off? Nobody has published this analysis.

2. **Can Doc-to-LoRA handle personality, not just facts?** Current results are on factual QA. Can a hypernetwork generate a "personality adapter" from a character description as effectively as DPO-based character training?

3. **What's the optimal update cadence?** Google Gboard uses 14-day cycles. DoorDash suggests quarterly. There's no principled framework for deciding when accumulated memories justify a retraining cycle.

4. **Can sparse memory fine-tuning work with standard transformers?** The 11% vs 89% forgetting result is dramatic but requires non-standard architecture. Can the principle be applied to existing models?

5. **Is Letta's learning-sdk the first step?** Their `pip install agentic-learning` SDK adds continual learning to any agent. If they ship the weight-distillation step, it would be the first complete implementation of the full pipeline.

---

## References

### Proposed Architectures
- [Letta: Continual Learning in Token Space](https://www.letta.com/blog/continual-learning)
- [Letta: Skill Learning](https://www.letta.com/blog/skill-learning)
- [Letta learning-sdk (GitHub)](https://github.com/letta-ai/learning-sdk)
- [AWS Continuous Self-Instruct](https://aws.amazon.com/blogs/machine-learning/llm-continuous-self-instruct-fine-tuning-framework-powered-by-a-compound-ai-system-on-amazon-sagemaker/)
- [Sakana AI Doc-to-LoRA — arxiv 2602.15902](https://arxiv.org/abs/2602.15902)

### Self-Evolving Systems
- [EvolveR — arxiv 2510.16079](https://arxiv.org/abs/2510.16079)
- [MemRL — arxiv 2601.03192](https://arxiv.org/abs/2601.03192)
- [MoE-CL (Self-Evolving LLMs) — arxiv 2509.18133](https://arxiv.org/abs/2509.18133)
- [MemSkill — arxiv 2602.02474](https://arxiv.org/abs/2602.02474)

### RAG-to-Fine-Tune
- [Fine-Tuning with RAG — ICLR 2026](https://arxiv.org/abs/2510.01375)
- [DRAG — ACL 2025](https://aclanthology.org/2025.acl-long.358/)
- [Prompt Distillation — arxiv 2412.14964](https://arxiv.org/abs/2412.14964)
- [Self-Tuning — arxiv 2406.06326](https://arxiv.org/abs/2406.06326)

### Catastrophic Forgetting
- [ACM CSUR 2025: Continual Learning of LLMs](https://dl.acm.org/doi/10.1145/3735633)
- [Spurious Forgetting — ICLR 2025](https://openreview.net/forum?id=ScI7IlKGdI)
- [Sparse Memory Fine-tuning — arxiv 2510.15103](https://arxiv.org/abs/2510.15103)
- [Self-Synthesized Rehearsal — ACL 2024](https://aclanthology.org/2024.acl-long.77/)
- [LoRA Learns Less and Forgets Less — arxiv 2405.09673](https://arxiv.org/abs/2405.09673)

### Knowledge Editing
- [ROME](https://rome.baulab.info/)
- [MEMIT](https://memit.baulab.info/)
- [Knowledge Editing Survey — ACM CS](https://dl.acm.org/doi/10.1145/3698590)
- [MemLLM — arxiv 2404.11672](https://arxiv.org/abs/2404.11672)

### Production Adjacent
- [Cursor Custom Embedding Training](https://www.zenml.io/llmops-database/enhancing-ai-coding-agent-performance-with-custom-semantic-search)
- [Google Gboard FL — ACL 2023](https://aclanthology.org/2023.acl-industry.60/)
- [Apple Federated Personalization](https://machinelearning.apple.com/research/federated-personalization)
- [FwdLLM — USENIX ATC 2024](https://www.usenix.org/conference/atc24/presentation/xu-mengwei)
