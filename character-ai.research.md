# Character.AI: Character Training at Scale

Last Updated: 2026-03-24

## Overview

Character.AI (C.AI) is the most significant production system for personality-trained LLMs. Founded by Noam Shazeer and Daniel De Freitas — core authors of Google's LaMDA — it processes 30,000 messages/second and was the third most-used generative AI application globally.

Unlike Neuro-sama (one developer, one character, iterative SFT), Character.AI operates a **platform** where millions of users create characters, and the system learns to embody any character definition through a combination of proprietary post-training and prompt-based character definitions.

## Founding & History

| Date | Event |
|------|-------|
| Nov 2021 | Founded by Noam Shazeer and Daniel De Freitas, both ex-Google Brain |
| 2022 | Built proprietary foundation model from scratch (complete pre-training + post-training stack) |
| 2023 | Rapid growth to one of the top 3 generative AI apps globally |
| Aug 2024 | Google licenses C.AI's research, hires 32 researchers including the entire pre-training team. Shazeer returns to Google |
| Post-2024 | C.AI pivots: shifts from self-built foundation models to **third-party pre-trained models + proprietary post-training** |

Key context: Shazeer is one of the 8 authors of "Attention Is All You Need" (2017). The team that built LaMDA at Google is the same team that built Character.AI's foundation model.

## Technical Architecture

### Four-Layer System

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: User Feedback                             │
│  Star ratings (1-4) + message editing               │
│  → Affects per-character response selection          │
│  → Does NOT modify base model weights               │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│  Layer 3: Prompt Layer (User-Facing)                │
│  Character definition: name, description, greeting,  │
│  personality, example dialogues                      │
│  → Managed by Prompt Poets (YAML + Jinja)           │
│  → Smart truncation (character def prioritized)      │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│  Layer 2: Character Training (Post-Training)        │
│  DPO with synthetic constitutional data             │
│  → "I am..." personality constitutions              │
│  → Teaches model to generalize from ANY character   │
│    definition, not just specific characters          │
│  ★ Core competitive moat, fully proprietary         │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│  Layer 1: Foundation Model (Pre-Training)           │
│  Originally: proprietary LaMDA-derived model        │
│  Now: third-party models + proprietary post-training│
│  Multi-Query Attention, native int8 training        │
└─────────────────────────────────────────────────────┘
```

### Layer 1: Foundation Model

- **Custom pre-trained** from day zero, not fine-tuned from an existing model
- Based on team's LaMDA expertise at Google
- **Multi-Query Attention (MQA)**: 5x reduction in GPU KV cache requirements
- **Native int8 training**: eliminates training/serving precision mismatch
- **KV cache sharing**: ties KV cache across neighboring attention layers, further 2-3x reduction
- Parameter count: **never publicly disclosed**
- After Google deal (2024): pivoting to hybrid approach (third-party pre-trained + proprietary post-training)

### Layer 2: Character Training (The Core Innovation)

This is the most research-relevant layer. Character Training is a **specialized form of post-training** that teaches the model how to embody any character description, not how to be a specific character.

**What Character Training is:**
- A subset of post-training focused on "crafting traits within the model in the manner of its response" ([interconnects.ai](https://www.interconnects.ai/p/character-training))
- Uses **Constitutional AI variants adapted for personality**
- Generates synthetic training data through a pipeline:
  1. Define personality as "I am..." constitutional statements (not "Choose the response that..." preference comparisons)
  2. Model generates queries relevant to target traits
  3. Model generates responses under constitutional guidance
  4. Constitution-guided responses vs base model responses form DPO preference pairs
  5. Standard DPO training encodes personality generalization into weights

**What Character Training is NOT:**
- Not per-character fine-tuning (they don't train a separate model for each character)
- Not prompt engineering (it changes weights)
- Not regular RLHF (it's personality-specific, not general helpfulness)

**Key insight from Nathan Lambert**: "crafting a specific personality from scratch is an open question" — Character Training remains "more of an art than a hill to climb up with careful data engineering."

**Evaluation**: They use a **ModernBERT classifier** that predicts which of 11 characters an output most likely came from. This quantifies personality strength across different training interventions.

**Anthropic uses a similar approach for Claude.** Amanda Askell (Anthropic): "It's like constitutional AI, but it's without any human data" — indicating fully synthetic, model-generated training data for personality.

### Layer 3: Prompt Layer

Users define characters through structured prompts:

| Field | Max Length | Purpose |
|-------|-----------|---------|
| Name | — | Character identifier |
| Short Description | 50 chars | Concise system description |
| Greeting | 500 chars | First message, sets tone and style. **Single most influential element** for personality consistency |
| Personality / Description | Unlimited | Detailed traits, backstory, knowledge |
| Example Dialogues | Unlimited | Conversation samples defining speech patterns |

These are managed by **Prompt Poets** (originally internal tool "Hermies", later open-sourced):
- YAML structure + Jinja templating for runtime variables and control flow
- Smart truncation when context overflows: **character definitions are prioritized** over conversation history
- Handles group chat (multiple character definitions in one prompt)

### Layer 4: User Feedback

- **1-4 star ratings** on each response
- Rating "predominantly affects the specific character, but also affects behavioral selection as a whole"
- Official position: feedback does NOT alter base model weights
- Mechanism: likely affects response ranking/selection, not training — a form of **implicit RLHF without gradient updates**
- Users can also edit messages and provide written feedback

## Infrastructure & Scale

| Metric | Value |
|--------|-------|
| Messages per second | 30,000 |
| Bandwidth | 7-8 GB/s on primary generation path |
| Open connections | ~400,000 |
| P50 response time | ~12.5 seconds |
| Cache hit rate | **95%** (only compute the new user message, ~5% of total) |
| Scale timeline | 300 → 30,000 msg/s in 18 months |

The 95% cache hit rate is critical: successive messages in a conversation are nearly identical (same character definition + conversation history, plus one new user message). Without this optimization, the platform would be economically unviable.

## Character.AI vs Neuro-sama

| Dimension | Character.AI | Neuro-sama |
|-----------|-------------|------------|
| Scale | Millions of characters | 2 characters (Neuro + Evil) |
| Personality training | DPO + synthetic constitutional data | Iterative SFT on curated stream data |
| Model | Proprietary (param count unknown) | Custom 2B, q2_k |
| Character definition | User prompt (anyone can create) | Developer-curated training data |
| Learning signal | Star ratings + message edits | Vedal's manual curation |
| Core approach | **Train model to generalize from any character description** | **Train model to BE a specific character** |
| Technical disclosure | Minimal (some blog posts, one scaling talk) | Minimal (stream comments, interviews) |

The key architectural difference: C.AI trains a **meta-character model** (can become any character given a description), while Neuro-sama trains a **specific-character model** (IS Neuro-sama in the weights).

## What This Reveals About Character Training

### The Industry Pattern

Three labs have now confirmed using constitutional/synthetic post-training for personality:

| Lab | Method | Public Detail |
|-----|--------|---------------|
| **Character.AI** | DPO + personality constitutions | Minimal (Nathan Lambert's analysis) |
| **Anthropic** (Claude) | Constitutional AI for character | Amanda Askell confirmed methodology, no paper |
| **OpenAI** (GPT-4o) | Unknown, but dramatic personality shifts observed between versions | Zero disclosure |

Nathan Lambert: "frontier labs lack public documentation of personality changes."

### Character Training vs Academic Personality Methods

| Dimension | Character Training (C.AI/Anthropic) | Academic (BIG5-CHAT, FinePE, PERSONA) |
|-----------|--------------------------------------|---------------------------------------|
| Goal | Generalize to ANY character | Specific Big Five trait control |
| Data | Synthetic, model-generated | Annotated human data (BIG5-CHAT) or contrastive activations (PERSONA) |
| Evaluation | Custom classifier (11 characters) | Psychometric tests (BFI, IPIP-NEO) |
| Human involvement | "Without any human data" (Askell) | Varies (BIG5-CHAT uses Facebook posts) |
| Production | Yes (billions of messages) | No |

### The Meta-Character Insight

Character.AI's most important contribution to the field is the concept of **meta-character training**: instead of training a model to have a personality, train it to adopt any personality given a description. This is:

1. **More scalable** — one model serves millions of characters
2. **More flexible** — new characters don't need retraining
3. **Closer to how humans work** — we can "imagine being" different characters
4. **The reason Layer 2 (training) and Layer 3 (prompts) are both needed** — training gives the model the *ability* to embody characters, prompts specify *which* character

## Open Questions

1. **What happened after the Google deal?** With the pre-training team gone, how much has the architecture changed? Are they now fine-tuning Gemini models with their post-training pipeline?

2. **Does the star rating actually feed back into training?** The official position is "no weight changes," but accumulated ratings across millions of interactions could be valuable DPO signal. It's plausible they batch this data into periodic retraining.

3. **How does Character Training compare to activation engineering?** PERSONA achieves 9.60 vs SFT's 9.61 on PersonalityBench. Would Character Training score higher on the same benchmark? No one has tested this.

4. **Can the meta-character approach be open-sourced?** OpenCharacter (arxiv 2501.15427) attempts this with 20K synthetic characters + SFT, achieving GPT-4o-level role-playing. Is this architecturally equivalent to what C.AI does, or is there a DPO-specific advantage?

5. **Is the "I am..." constitution format important?** C.AI uses first-person constitutional statements instead of third-person preference comparisons. Is this a meaningful design choice, or just a convention?

## Connection to Continuous Learning Research

Character.AI bridges Pillar 1 (Memory) and Pillar 3 (Learning):

- **Layer 2 (Character Training)** is Pillar 3: personality in weights via post-training
- **Layer 3 (Prompts)** is Pillar 1: character definitions as external context
- **Layer 4 (Feedback)** is a potential Pillar 3 signal source: if ratings are ever used for retraining, this closes the continuous learning loop

The meta-character approach also suggests a fourth pillar: **Meta-Learning** — not learning specific facts or personalities, but learning *how to learn* from character descriptions. This is qualitatively different from both memory retrieval and weight updates.

## References

### Character.AI Official
- [Character.AI Character Book](https://book.character.ai/) — official documentation on character creation
- [Building a Better AI Together](https://blog.character.ai/building-a-better-ai-together-your-role-in-character-ai/) — user role in training
- [Our Next Phase of Growth](https://blog.character.ai/our-next-phase-of-growth/) — Google deal, pivot to third-party models
- [Optimizing AI Inference](https://research.character.ai/optimizing-inference/) — MQA, int8 training, KV cache

### Analysis
- [Character Training — interconnects.ai](https://www.interconnects.ai/p/character-training) — Nathan Lambert on character training concept, Anthropic's approach
- [Opening the Character Training Pipeline — interconnects.ai](https://www.interconnects.ai/p/opening-the-black-box-of-character) — DPO + constitutional data, ModernBERT evaluation
- [Character.AI Scaling Talk — ZenML](https://www.zenml.io/llmops-database/scaling-a-high-traffic-llm-chat-application-to-30-000-messages-per-second) — infrastructure, Prompt Poets, 95% cache hit rate

### Related Academic
- [OpenCharacter — arxiv 2501.15427](https://arxiv.org/abs/2501.15427) — open-source attempt at meta-character training
- [Character-LLM — arxiv 2310.10158](https://arxiv.org/abs/2310.10158) — trainable agent for role-playing
