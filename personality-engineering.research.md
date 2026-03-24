# LLM Personality Engineering: Methods, Boundaries, and Tradeoffs

Last Updated: 2026-03-24

## Overview

How do you make an LLM embody a specific persona? This document surveys three paradigms — prompt engineering, fine-tuning, and activation engineering — and maps the boundary between what each can achieve.

The key finding: **personality is not a single problem, but a spectrum of increasingly deep interventions**, each with distinct tradeoffs in cost, controllability, and persistence.

## Paradigm Map

```
                    Cost / Effort
                         ▲
                         │
        Fine-tuning      │  ● BIG5-CHAT (SFT/DPO)
        (weight change)  │  ● OpenCharacter
                         │  ● FinePE (MoE-LoRA)
                         │  ● Neuro-sama (iterative SFT)
                         │
                         │
  Activation Engineering │  ● PERSONA (vector algebra)
  (inference-time,       │  ● SAS Personality Sliders
   no weight change)     │  ● Anthropic Persona Vectors
                         │
                         │
        Prompting        │  ● SillyTavern character cards
        (no change)      │  ● System prompt + few-shot
                         │  ● Eliza character files
                         │
                         └──────────────────────────────► Personality Depth / Robustness
```

## Paradigm 1: Prompt Engineering

The most accessible approach. Define personality through system prompts, character descriptions, and example dialogues.

### Techniques (from SillyTavern Community)

The SillyTavern roleplay community has developed the most sophisticated prompt-based personality engineering. Key formats:

| Format | Description |
|--------|-------------|
| **PLists** | Comma-separated trait lists: `[brave, sarcastic, loyal]` |
| **Ali:Chat** | Example dialogues with `{{char}}:` and `{{user}}:` prefixes, separated by `<START>` tags |
| **W++** | Structured attribute blocks (deprecated, but historically influential) |
| **Plain prose** | Natural language character description + backstory |

**Best practices** (empirical, from community testing):
- The **first message** is the single most important element — "the model is more likely to pick up style and length constraints from the first message than anything else"
- **MBTI profile** as add-on to character card "significantly improves personality consistency"
- **Backstory + example conversations** more effective than trait lists alone
- Token budget matters: "a 1000-token character definition cuts the AI's memory in half" on small context models

### What Prompting Can Do

- Set broad personality traits (friendly, sarcastic, formal)
- Establish speech patterns and vocabulary
- Define character knowledge and backstory
- Control response length and format

### What Prompting Cannot Do

1. **Override alignment training.** kimjammer's finding: aligned base models "stubbornly avoid swearing" even when the system prompt explicitly demands it. The safety layer built into weights overrides prompt-level instructions.

2. **Maintain consistency over long contexts.** The SAS personality slider paper notes: "prompt engineering remains fragile: models frequently exhibit contextual drift within long context windows." As conversation grows, early personality instructions get diluted.

3. **Achieve statistical validity.** The paper "When 'A Helpful Assistant' Is Not Really Helpful" ([arxiv 2311.10054](https://arxiv.org/html/2311.10054v2)) tested **162 personas across 2,410 questions on 9 models** and found: "most of the personas have no or negative impact on LLM's performance." Persona effects are "largely unpredictable" — even optimized selection barely outperforms random choice.

4. **Produce human-like trait distributions.** BIG5-CHAT showed that prompting produces personality scores that don't match how humans actually express traits. SFT/DPO-trained models produce "intra-trait correlations more closely matching human data."

### Eliza Framework (a16z)

Worth noting as a **production-grade prompt-based system**. Eliza uses JSON character files that define personality, knowledge, and behavior. Architecture separates Runtime, Character, Client, Adapter, and Plugin layers. Character files are purely prompt-based — no fine-tuning, no activation engineering. The sophistication is in the agent framework, not the personality method.

## Paradigm 2: Fine-Tuning

Modify model weights to embed personality. Three sub-approaches:

### 2a. Supervised Fine-Tuning (SFT)

Train on personality-annotated dialogue data.

**BIG5-CHAT** ([ACL 2025](https://aclanthology.org/2025.acl-long.999/)):
- 100K dialogues grounded in Big Five personality model
- Dataset constructed from SODA (social scenarios) + PsychGenerator (846K Facebook posts with Big Five annotations)
- SFT and DPO both **outperform prompting** on BFI and IPIP-NEO personality assessments
- Surprising finding: personality affects reasoning. Models with **higher conscientiousness + agreeableness and lower extraversion + neuroticism** perform better on reasoning tasks — matching psychological research on humans
- Uses LoRA for efficient training

**OpenCharacter** ([arxiv 2501.15427](https://arxiv.org/abs/2501.15427)):
- 20K synthetic characters + 306K role-playing instruction-response pairs
- Two strategies: **response rewriting** (rewrite existing response in character) and **response generation** (generate new response in character)
- LLaMA-3 8B fine-tuned achieves GPT-4o-level role-playing
- Key insight: character info goes into system prompt during fine-tuning, so the model learns to generalize from character descriptions

### 2b. Mixture of LoRA Experts (Per-Trait Modules)

**FinePE** ([ScienceDirect 2026](https://www.sciencedirect.com/science/article/abs/pii/S1568494626003911)):
- Assigns **separate LoRA modules to each Big Five subtrait** (60 subtraits total)
- Gating mechanism learns optimal combination weights
- 120K Q&A pairs across subtrait subsets
- Achieves average induced scores of 4.91 (high) / 1.61 (low), outperforming second-best by **29%**
- Addresses the "granularity gap": standard SFT averages across traits, FinePE achieves fine-grained disentangled control
- Key advantage over prompting: prompting suffers from "conflicting trait expression" when combining multiple traits

**Fusian** ([arxiv 2603.15405](https://arxiv.org/html/2603.15405)):
- Multi-LoRA fusion for fine-grained continuous MBTI personality control
- Similar per-trait LoRA approach applied to MBTI framework instead of Big Five

### 2c. Iterative Batch SFT (Neuro-sama)

See [neuro-sama.research.md](./neuro-sama.research.md) for full analysis.

- 2B parameter model, q2_k quantization
- Training data from curated stream transcripts
- Human-in-the-loop curation (Vedal manually selects data)
- Deploy → collect → curate → retrain → deploy cycle
- The only known production system doing iterative personality fine-tuning

### Fine-Tuning Tradeoffs

| Advantage | Limitation |
|-----------|------------|
| Overrides alignment layer (can produce behaviors prompts can't) | Requires training data and GPU compute |
| Statistically valid personality profiles | Catastrophic forgetting risk on retraining |
| Robust over long contexts | Per-personality model or adapter needed |
| Human-like trait distributions (BIG5-CHAT) | Less flexible than prompting (can't switch on the fly) |

## Paradigm 3: Activation Engineering

The newest approach. Manipulate internal activations at inference time — no prompt changes, no weight changes. This is the most surprising finding in this survey.

### 3a. PERSONA Framework ([arxiv 2602.15669](https://arxiv.org/html/2602.15669))

**Method**: Contrastive activation analysis. Generate responses under trait-expressing and trait-suppressing prompts. The persona vector = difference between mean activations.

**Key discovery**: Personality traits appear as **extractable, approximately orthogonal directions** in the model's representation space that support algebraic operations.

**Operations**:
- **Scalar multiplication**: `α × vector` controls intensity. Pearson correlation > 0.9 between α and personality score
- **Vector addition**: Combine vectors for multi-trait personas (e.g., outgoing + compassionate)
- **Vector subtraction**: Suppress traits while amplifying others

**Performance**:

| Method | PersonalityBench Score |
|--------|----------------------|
| PERSONA (training-free) | **9.60** |
| Supervised Fine-Tuning | 9.61 |
| Neuron-based (NPTI) | 9.43 |
| Simple Prompting | 8.39 |

**PERSONA matches fine-tuning performance without any gradient updates.** This is the headline result.

**Limitations**:
- Safety-aligned traits resist activation (e.g., "self-interested" shows strong resistance)
- Lower improvements on factual accuracy maintenance (43.8-61.4% win rates)
- Requires white-box model access (can't use on API models)

### 3b. SAS Personality Sliders ([arxiv 2603.03326](https://arxiv.org/html/2603.03326))

**Core operation**: `h' = h + α·v` (inject scaled steering vector into residual stream)

**Key innovation**: Naive multi-vector steering causes "representation collapse." **Sequential Adaptive Steering (SAS)** solves this by training subsequent probes on residual streams shifted by prior interventions, effectively orthogonalizing vectors.

**Result**: Users adjust five sliders (Big Five traits) to create complex personas instantly. Zero-parameter, negligible inference overhead.

**Comparison**:

| Approach | Parameter Cost | Multi-trait Support |
|----------|---------------|---------------------|
| Fine-tuning/DPO | Full retraining | Manual composition |
| LoRA merging | Weight updates | Limited |
| Naive steering | None | Fails (interference) |
| SAS | None | Succeeds |

Validated on Llama-3-8B, Mistral-7B, Qwen-7B.

### 3c. Anthropic Persona Vectors ([Anthropic Research](https://www.anthropic.com/research/persona-vectors))

**Scope**: Evil, sycophancy, hallucination, politeness, humor, optimism

**Applications**:
1. **Monitoring**: Detect personality shifts during deployment or training before they manifest in outputs
2. **Steering** (inference-time): Subtract vectors to suppress traits, but degrades general capabilities
3. **Vaccination** (training-time): Add vectors during training to prevent trait acquisition — "little-to-no degradation" in capabilities
4. **Data flagging**: Identify training samples likely to induce unwanted traits

**Tested on**: Qwen 2.5-7B-Instruct, Llama-3.1-8B-Instruct

**Framing**: Anthropic positions this as a **safety/alignment tool**, not a personality customization tool. The emphasis is on monitoring and preventing unwanted traits, not on enabling arbitrary persona creation.

### 3d. PRISM: Routing Between Persona and Base ([arxiv 2603.18507](https://arxiv.org/html/2603.18507))

A hybrid approach. Core finding: **expert personas improve alignment tasks but damage knowledge tasks** (MMLU drops from 71.6% to 68.0%).

PRISM learns a **binary gate** that routes queries to a specialized LoRA adapter only when persona activation helps, routing others to the base model. Result: +1.7 points overall improvement with no MMLU degradation.

## Cross-Paradigm Comparison

| Dimension | Prompting | Fine-Tuning | Activation Engineering |
|-----------|-----------|-------------|----------------------|
| **Cost** | Zero | GPU hours + data | Compute for vector extraction |
| **Flexibility** | Instant persona switch | Need new adapter/model | Instant (adjust α) |
| **Depth** | Surface-level | Deep (in weights) | Deep (in activations) |
| **Robustness** | Drifts over long context | Stable | Stable within operating range |
| **Override alignment** | No | Yes | Partially (safety-aligned traits resist) |
| **Multi-trait composition** | Fragile | Complex (2^N models) | Algebraic (SAS) |
| **Model access needed** | API OK | Weights needed | Weights + activations needed |
| **Production readiness** | Mature | Mature | Research stage |
| **Human-like trait distribution** | No | Yes (BIG5-CHAT) | Untested |

## The Boundary: When to Use What

### Prompting is sufficient when:
- Broad personality traits (helpful, formal, friendly) are enough
- The target behavior doesn't conflict with alignment training
- Context windows are short
- You need instant switching between personas
- You're using API-only models

### Fine-tuning is needed when:
- You need behaviors that conflict with alignment (swearing, aggression, non-standard safety)
- Long-context consistency matters
- Statistical validity of personality is important (psychometric tests)
- You're building a production character system (Neuro-sama, Character.AI)

### Activation engineering is the future for:
- Real-time personality customization (user-facing sliders)
- Multi-trait composition without exponential model count
- Safety monitoring (detecting personality drift)
- Research into personality mechanisms (how models represent traits)

## Connection to Continuous Learning Research

This survey connects to the broader research project in several ways:

1. **Pillar 3 decomposition**: "Learning" isn't just about factual knowledge. Personality is a distinct type of learned behavior. The three paradigms map to three levels of learning depth.

2. **Activation engineering as the missing link**: Between external memory (Pillar 1) and weight updates (Pillar 3), activation engineering offers a middle ground — modify behavior without modifying weights. This could enable "personality memory" that's deeper than prompts but cheaper than fine-tuning.

3. **Anthropic's vaccination concept**: The idea that you can make a model resistant to acquiring certain personality traits during training has implications for continual learning — you could protect against catastrophic forgetting of personality by "vaccinating" before retraining on new data.

4. **BIG5-CHAT's reasoning finding**: Personality isn't just aesthetic — it affects model capability. Higher conscientiousness improves reasoning. This means personality engineering is also capability engineering.

## Open Questions

1. **Does activation engineering scale to larger models?** Current results are on 7B-8B models. Do personality vectors remain orthogonal and manipulable at 70B+?

2. **Can activation engineering be combined with memory systems?** Imagine: Mem0-style facts + persona vectors for personality + prompt for situation. A three-layer personality stack.

3. **What's the long-context durability of activation steering?** Prompts drift. Do steered activations also drift over very long conversations?

4. **Can persona vectors be learned from deployment data?** Instead of Vedal manually curating → fine-tuning, could you extract persona vectors from interaction history automatically?

5. **Is Anthropic using persona vectors in Claude?** They frame it as research, but the monitoring and vaccination capabilities suggest production applicability.

## References

### Prompting
- [SillyTavern Character Design Guide](https://docs.sillytavern.app/usage/core-concepts/characterdesign/)
- [When "A Helpful Assistant" Is Not Really Helpful — arxiv 2311.10054](https://arxiv.org/html/2311.10054v2) — 162 personas, negative/null results
- [ElizaOS Documentation](https://docs.elizaos.ai) — a16z agent framework with JSON character files

### Fine-Tuning
- [BIG5-CHAT — ACL 2025](https://aclanthology.org/2025.acl-long.999/) — 100K dialogues, SFT/DPO outperform prompting
- [OpenCharacter — arxiv 2501.15427](https://arxiv.org/abs/2501.15427) — 20K synthetic characters, LLaMA-3 8B matches GPT-4o
- [FinePE — ScienceDirect 2026](https://www.sciencedirect.com/science/article/abs/pii/S1568494626003911) — MoE-LoRA for per-subtrait control
- [Fusian — arxiv 2603.15405](https://arxiv.org/html/2603.15405) — Multi-LoRA MBTI control
- [Fine-Tuning LLMs for Personality Preservation](https://ijrmeet.org/wp-content/uploads/2025/04/in_ijrmeet_Apr_2025_GC250263-AP04_Fine-Tuning-LLMs-for-Personality-Preservation-in-AI-Assistants-172-191.pdf)

### Activation Engineering
- [PERSONA — arxiv 2602.15669](https://arxiv.org/html/2602.15669) — Vector algebra, matches SFT performance training-free
- [SAS Personality Sliders — arxiv 2603.03326](https://arxiv.org/html/2603.03326) — Sequential Adaptive Steering for multi-trait
- [Anthropic Persona Vectors](https://www.anthropic.com/research/persona-vectors) — Monitoring, steering, vaccination
- [Neuron-Based Personality Manipulation — arxiv 2412.10427](https://arxiv.org/html/2412.10427v2) — Layer 18 intervention

### Hybrid / Routing
- [PRISM — arxiv 2603.18507](https://arxiv.org/html/2603.18507) — Binary gate persona routing, alignment vs accuracy tradeoff

### Psychometrics
- [Psychometric Framework for Personality in LLMs — Nature Machine Intelligence 2025](https://www.nature.com/articles/s42256-025-01115-6)
- [Modeling, Evaluating, and Embodying Personality in LLMs — EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.506.pdf)
