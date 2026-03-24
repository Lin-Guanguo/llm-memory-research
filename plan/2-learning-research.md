# Continuous Learning Research Plan

Last Updated: 2026-03-23

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
| **Neuro-sama** | 2B parameter custom-trained LLM by Vedal. Training data from Twitch interactions. Personality from weights, not prompts. Technical details intentionally private | TODO |
| **Open-LLM-VTuber** | Open source project ([GitHub](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber)). Uses prompt engineering for personality — contrast with Neuro-sama's weight-based approach | TODO |
| **Character.AI** | Commercial platform for custom character chatbots. Likely fine-tuned models. May have published technical details | TODO |
| Community attempts | Reproduce Neuro-sama-like results. Search for blog posts, GitHub repos, forum discussions | TODO |

Key question: **What's the boundary between "prompt-crafted personality" and "weight-embedded personality"?** At what point does fine-tuning produce something that prompt engineering can't replicate?

### Direction 2: Per-User Personalization (Multi-LoRA)

The most production-ready approach to continuous adaptation.

| Target | Details | Status |
|--------|---------|--------|
| **Multi-LoRA serving** | vLLM, Anyscale, NVIDIA NIM support dynamic LoRA adapter swapping per request. One base model, many personalized adapters | TODO |
| **Sakana AI Doc-to-LoRA** | Generates LoRA adapters from documents, not training data. Enables rapid knowledge injection | TODO |
| **Profile-to-PEFT** | Generates per-user LoRA adapters from user history, without storing raw data | TODO |
| **DoorDash personalization** | Production case: personalized menu descriptions via LLM pipeline with continuous evaluation | TODO |

Key question: **Is per-user LoRA a viable middle ground between prompt injection and full fine-tuning?** What are the production tradeoffs (storage, latency, staleness)?

### Direction 3: Academic Survey (Continual Learning for LLMs)

Understand the theoretical landscape and what's possible vs what's practical.

| Target | Details | Status |
|--------|---------|--------|
| **ACM CSUR 2025 survey** | [Continual Learning of LLMs](https://dl.acm.org/doi/10.1145/3735633) — comprehensive survey covering continual pre-training, instruction tuning, and alignment | TODO |
| **Catastrophic forgetting solutions** | Self-distillation, rehearsal, parameter freezing, LoRA-based approaches | TODO |
| **Self-Evolving LLMs** | [arxiv](https://arxiv.org/html/2509.18133v3) — continual instruction tuning without human intervention | TODO |
| **Spurious forgetting** | Recent finding that much "forgetting" is actually alignment degradation, not true knowledge loss | TODO |

Key question: **How close is continual learning to production-ready?** What's the gap between academic SOTA and what's deployable?

### Direction 4: Hybrid Memory → Weight Pipeline

The logical endpoint: external memories accumulated over time, periodically fine-tuned into weights.

| Target | Details | Status |
|--------|---------|--------|
| **Concept exploration** | No known production system does this. But the pattern is: Mem0-style fact extraction → accumulate → batch LoRA fine-tune → deploy | TODO |
| **Federated learning** | Google Gboard model: user devices send model updates, server averages them. A form of distributed continuous learning | TODO |
| **Cursor's approach** | Custom embedding model trained from agent session traces — not weight updates for the LLM itself, but weight updates for the retrieval model | TODO |

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
