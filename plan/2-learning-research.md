# Continuous Learning Research Plan

Last Updated: 2026-03-24

## Goal

Research how LLMs can learn and adapt after deployment — the "Pillar 3" identified in findings.md. This is the missing piece: Memory (external storage) and Context (window management) are well-studied, but writing knowledge into model weights remains largely unexplored in production.

## Research Approach

Focus on **what's publicly available**: production systems, open-source projects, published case studies, and academic surveys. Not doing original research or model training.

---

## Research Directions

### Direction 1: AI VTuber / Character AI (Custom-Trained Personality)

The clearest real-world example of "personality written into weights."

| Target | Details | Status |
|--------|---------|--------|
| **Neuro-sama** | 2B parameter custom-trained LLM by Vedal. Training data from Twitch interactions. Personality from weights, not prompts. Technical details intentionally private | ✅ Done → `neuro-sama.research.md` |
| **Open-LLM-VTuber** | Open source project ([GitHub](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber)). Uses prompt engineering for personality — contrast with Neuro-sama's weight-based approach | ✅ Covered in `neuro-sama.research.md` |
| **Character.AI** | DPO + personality constitutions for meta-character training. One model generalizes to ANY character given a description. 30K msg/s. Post-Google pivot to third-party pre-trained + proprietary post-training | ✅ Done → `character-ai.research.md` |
| Community attempts | 5 projects surveyed: kimjammer/Neuro, Open-LLM-VTuber, moeru-ai/airi, AIRIS-VtuberAI, VedalAI/neuro-sdk. All focus on pipeline engineering; none attempt weight-level personality or iterative learning. Memory implementations minimal. | ✅ Covered in `neuro-sama.research.md` |

Key question: **What's the boundary between "prompt-crafted personality" and "weight-embedded personality"?** At what point does fine-tuning produce something that prompt engineering can't replicate?

#### Cross-Cutting: Personality Engineering Methods

| Target | Details | Status |
|--------|---------|--------|
| **Prompt-based personality** | SillyTavern character cards, Eliza character files, 162-persona study (null results). Boundary: can't override alignment, drifts over long context | ✅ Done → `personality-engineering.research.md` |
| **Fine-tuning for personality** | BIG5-CHAT (ACL 2025), OpenCharacter, FinePE (MoE-LoRA per Big Five subtrait) | ✅ Done → `personality-engineering.research.md` |
| **Activation engineering** | PERSONA (matches SFT training-free), SAS personality sliders, Anthropic persona vectors (monitoring + vaccination) | ✅ Done → `personality-engineering.research.md` |

### Direction 2: Per-User Personalization (Multi-LoRA)

The most production-ready approach to continuous adaptation.

| Target | Details | Status |
|--------|---------|--------|
| **Multi-LoRA serving** | vLLM, S-LoRA (2000 adapters/GPU), Punica (SGMV kernel), NVIDIA NIM, LoRAX, Together AI, Fireworks, Groq. Serving is solved | ✅ Done → `multi-lora.research.md` |
| **Sakana AI Doc-to-LoRA** | Hypernetwork generates LoRA from document in <1s. 83.5% of full-context quality. ~50MB per adapter | ✅ Done → `multi-lora.research.md` |
| **Profile-to-PEFT** | MLP hypernetwork generates per-user LoRA in 0.57s. Also: Personalized Pieces (0.45MB/user), Apple PLUM, MTA | ✅ Done → `multi-lora.research.md` |
| **DoorDash personalization** | Uses LoRA for domain-specific models, but per-user personalization is RAG-based. Also: Convirza (60+ adapters), Phonely (99.2% accuracy) | ✅ Done → `multi-lora.research.md` |

Key question: **Is per-user LoRA a viable middle ground between prompt injection and full fine-tuning?** What are the production tradeoffs (storage, latency, staleness)?

### Direction 3: Academic Survey (Continual Learning for LLMs)

Understand the theoretical landscape and what's possible vs what's practical.

| Target | Details | Status |
|--------|---------|--------|
| **ACM CSUR 2025 survey** | [Continual Learning of LLMs](https://dl.acm.org/doi/10.1145/3735633) — comprehensive survey covering continual pre-training, instruction tuning, and alignment | ✅ Referenced in `hybrid-memory-weight.research.md` |
| **Catastrophic forgetting solutions** | Sparse memory fine-tuning (11% vs 89% forgetting), self-synthesized rehearsal, LoRA "learns less forgets less" | ✅ Done → `hybrid-memory-weight.research.md` |
| **Self-Evolving LLMs** | MoE-CL (Tencent, production), EvolveR, MemRL, MemSkill | ✅ Done → `hybrid-memory-weight.research.md` |
| **Spurious forgetting** | ICLR 2025: much "forgetting" is alignment degradation, not knowledge loss. Reversible with 50-100 samples | ✅ Done → `hybrid-memory-weight.research.md` |

Key question: **How close is continual learning to production-ready?** What's the gap between academic SOTA and what's deployable?

### Direction 4: Hybrid Memory → Weight Pipeline

The logical endpoint: external memories accumulated over time, periodically fine-tuned into weights.

| Target | Details | Status |
|--------|---------|--------|
| **Concept exploration** | No production system does full pipeline. Letta has explicit roadmap (token-first + weight distillation). 5 architecture proposals surveyed | ✅ Done → `hybrid-memory-weight.research.md` |
| **Federated learning** | Google Gboard (30+ models, DP ε≤1), Apple (keyboard), FwdLLM (LLaMA-7B on mobile). All small models, not LLMs | ✅ Done → `hybrid-memory-weight.research.md` |
| **Cursor's approach** | Session traces → LLM ranking oracle → train custom embedding model. 12.5% QA accuracy improvement. Memory-to-weight for retrieval layer | ✅ Done → `hybrid-memory-weight.research.md` |

Key question: **Is "accumulate memories then fine-tune" a viable architecture?** What would the update cycle look like?

---

## Prioritization

| Priority | Direction | Reason |
|----------|-----------|--------|
| 1 | Direction 3 (Academic survey) | Establishes theoretical foundation before looking at practice |
| 2 | Direction 2 (Multi-LoRA) | Most production-ready, actionable for real systems |
| 3 | Direction 1 (VTuber/Character) | Interesting case study but limited public technical detail |
| 4 | Direction 4 (Hybrid pipeline) | Mostly speculative, explore last |

## Output

Per-direction research documents (`*.research.md`), cross-direction summary, and update to `findings.md` Pillar 3 section.
