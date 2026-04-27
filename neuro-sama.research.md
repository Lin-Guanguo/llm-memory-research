# Neuro-sama: Weight-Based Personality in Production

Last Updated: 2026-04-27

## Overview

Neuro-sama is an AI VTuber created by pseudonymous developer Vedal (Vedal987), and one of the most-watched VTubers on Twitch. She is notable as arguably the only production system where personality is intentionally embedded in model weights via fine-tuning, rather than relying solely on prompt engineering.

This makes Neuro-sama a unique case study for continuous learning research: it demonstrates an **iterative batch fine-tuning** pipeline where real deployment interactions feed back into training data.

The more recent VedalAI public repositories add a second, equally important lesson: Neuro-sama is not just a chat model with a VTuber shell. The public game integrations point to a **layered embodied-agent architecture**: a personality model produces low-entropy text commands, the Neuro API constrains those commands into typed actions, and game-specific controllers validate and execute the low-level behavior.

## History & Evolution

| Period | Milestone |
|--------|-----------|
| 2018 | Vedal creates Neuro-sama v1: a neural network trained to play the rhythm game osu! (not an LLM) |
| Aug 2021 | Vedal begins the **Airis** project — a concept for an AI VTuber streamer. "Airis" = AI + iris. Written concept document with character description and operation design |
| Mar 2022 | Vedal combines Airis with Neuro-sama (the osu! AI), reviving Neuro as an AI VTuber that plays osu! and talks to chat |
| Dec 2022 | Neuro-sama debuts as an AI VTuber on Twitch using **GPT-3 API** for conversation. Goes viral |
| Jan 2023 | Massive growth (100K+ Twitch followers). Controversial outputs (Holocaust comments, etc.) force moderation improvements |
| Mar 2023 | **Evil Neuro** introduced as a separate personality/"sister". Vedal begins work on moving away from OpenAI API |
| Mid 2023 | Transition to **custom fine-tuned model** based on open-source LLM. Custom TTS voice model trained |
| 2024 | Continuous iteration on custom model. Multiple retraining cycles. Improved game-playing (Minecraft) and multi-modal integration (vision). Neuro × Evil Neuro dual-model interactions become a staple |
| Early 2025 | Community lore starts repeating **2B parameters with q2_k quantization**, but no verifiable primary source has been found. "Airis" remains the internal codename |

### Why "Airis" Was Renamed

A VTuber from hololive named IRyS debuted while Airis was still in development. Vedal felt the name similarity would look like copying, so he reused the Neuro-sama brand from the osu! project instead.

## Technical Architecture

### System Components

Neuro-sama is a multi-component pipeline, not a single model:

```
┌─────────────────────────────────────────────────┐
│                  Twitch Chat                     │
│              (viewer messages)                   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│              STT (Speech-to-Text)                │
│         (for collab voice interactions)          │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│           Custom Fine-Tuned LLM                  │
│     small custom model (2B/q2_k unverified)      │
│     Personality embedded in weights              │
│     + system prompt for situational context      │
└──────┬───────────────────────────┬────────────────┐
       │                           │                │
       ▼                           ▼                ▼
┌──────────────┐          ┌────────────────────────┐
│  TTS Engine  │          │   Neuro API Action Bus  │
│ Azure "Ashley"│          │  (osu!, Minecraft,     │
│ pitched +25% │          │   SDK integrations)     │
└──────┬───────┘          └────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────┐
│          Live2D Avatar (lip-sync)                │
│          (designed by artist Anny)               │
└──────────────────────────────────────────────────┘
```

### LLM Details

| Spec | Value | Source |
|------|-------|--------|
| Parameter count | **~2B (UNVERIFIED)** | Widely repeated in Fandom Wiki and secondary sources, attributed to a Vedal stream in early 2025 but **no verifiable primary source** (no archived stream timestamp / screenshot). NOT mentioned on Wikipedia. |
| Quantization | **q2_k (UNVERIFIED, same source chain as above)** | Same as above — treat as community claim not primary disclosure |
| Base model | Undisclosed. Community speculation: LLaMA family | — |
| Training data | Twitch stream interactions, curated by Vedal. Uses data from his own interactions and others with express permission | [Vedal, Threads](https://www.threads.com/@sinisterpixel/post/DEa_XlXoKjK) |
| Fine-tuning method | Likely LoRA (mentioned on stream), possibly full fine-tune | Vedal (stream) |
| Inference | Self-hosted, Vedal's own GPUs | Vedal (stream) |

**Source warning on 2B + q2_k**: Web search audit (2026-04) found these numbers trace back to Fandom Wikis only. Search result summarizers repeatedly paraphrase "Vedal said 2B + q2_k in early 2025" but direct-fetch of Wikipedia shows no such claim. Fandom wiki returned 403 on direct fetch — could not verify citation. **Until a primary source is located (archived stream link with timestamp, or official screenshot), treat this as unverified community lore.**

**If true, 2B + q2_k is aggressively small.** A model this size at this quantization would struggle to maintain complex character traits via prompt alone. The personality would have to come from fine-tuning quality rather than model scale, and Vedal would be prioritizing inference latency (streaming needs ~1-3s response) over raw capability. But this analysis is only meaningful if the underlying claim is true.

### TTS Pipeline

- Microsoft Azure TTS, voice "Ashley"
- Pitch-shifted upward by 25% for Neuro's signature tone
- Singing uses a **completely separate AI model** (likely voice cloning / neural vocoder)
- Evil Neuro has a distinct voice configuration

### Vision / Multi-Modal

- Computer vision models convert on-screen game data into structured text fed to the LLM
- Game-playing uses **separate game agents** per title (osu! reads beatmaps for optimal movement prediction, Minecraft recognizes block patterns and crafting recipes)
- Gameplay AI processes an 80×60 pixel grayscale input of the game screen (Python-based)

### Memory

- **Within-session context** only — no confirmed persistent cross-session memory
- Some indications of retrieval-based memory (RAG-like) for cross-session facts, but not publicly documented
- Vedal has described memory as an ongoing challenge and area of active work

## Public VedalAI Repositories: Layered Agency

The public VedalAI repositories are more useful for understanding Neuro-sama's **action architecture** than her private LLM internals. They show a recurring pattern: keep the main model's output simple, typed, and easy to validate; move execution into game-specific downstream systems.

### Neuro SDK: Typed Action Protocol

The official [VedalAI/neuro-sdk](https://github.com/VedalAI/neuro-sdk) is a websocket protocol, not a general agent framework. It exposes three core primitives:

- **Context**: the game sends plaintext information about what is happening.
- **Registered actions**: the game declares action names, natural-language descriptions, and JSON schemas.
- **Forced actions**: the game asks Neuro to choose one of a constrained set of actions, optionally with current state and a query.

The API documentation explicitly says action descriptions, schemas, state, queries, and action-result messages are directly received by Neuro. Neuro then sends back an action name plus JSON-stringified data, and the game is responsible for validation and execution.

This is a sharper claim than "text-in/text-out": Neuro is acting as a **high-level action selector**. The game compiles rich state into text or JSON, Neuro selects a typed command, and the downstream integration compiles that command into concrete UI, keyboard, controller, or game-engine operations.

The SDK README also makes the boundary explicit: turn-based games work best, while games with non-low APM generally require Neuro to control only high-level actions and let another system handle low-level actions.

### Inscryption: State Serializer to Mouse Automation

[VedalAI/neuro-inscryption](https://github.com/VedalAI/neuro-inscryption) is the clearest example of the typed-action loop:

- Harmony patches hook into game events such as choosing a card, selecting a map path, or placing a card in a lane.
- The mod builds structured game state such as combat state, hand contents, item options, map options, and card descriptions.
- `Decision` creates an action window, attaches a forced action query, serializes state, and waits for Neuro's response.
- `ActionBase` and schema validation keep Neuro's output inside allowed choices.
- `NeuroMouse` performs the low-level click sequence after a valid high-level choice is returned.

In other words, the LLM does not "play Inscryption" directly. It chooses among constrained game actions. The integration layer executes the embodied behavior.

### Among Us: Trained Controller Plus Deterministic Solvers

[VedalAI/neuro-amongus](https://github.com/VedalAI/neuro-amongus) is the strongest public evidence that "Neuro-sama plays games" can mean more than an LLM loop. The README states the plan: record data from the game, then use it to train a neural network for Neuro.

The AI code implements an LSTM model over recorded game-state frames. Its outputs include movement directions plus action flags such as report, vent, and kill. A local socket server loads the trained model, receives frames from the game plugin, and returns an `NnOutput` protobuf. The C# plugin then maps those outputs into movement and button clicks.

The repository also contains deterministic support systems:

- pathfinding and fallback movement when the learned controller gets stuck
- minigame solvers registered by minigame type
- event-driven movement suggestions, such as moving toward a dead body or an emergency button

This is not just personality training. It is a hybrid embodied stack: supervised sequence model for movement/action policy, deterministic solvers for precise UI tasks, and game-specific perception/recording code.

### Cyberpunk 2077: Delegating to Game Systems

[VedalAI/neuro-cyberpunk](https://github.com/VedalAI/neuro-cyberpunk) shows the same pattern in a more complex real-time game. The plugin registers high-level actions such as querying quests and inventory, selecting dialogue choices, selecting SMS replies, running quickhacks, summoning a car, and driving to a waypoint.

The execution layer is not an LLM. The plugin serializes available choices or quickhack targets, sends context or forced actions to Neuro, validates the selected IDs, and then invokes Redscript methods, injects keypress chains, dispatches quickhacks, or starts an in-game autonomous driving command.

This makes Cyberpunk a useful example of **delegated embodiment**: Neuro supplies intent; the game integration and native game systems supply actuation.

### Swarm Control: Audience Control Plane, Not LLM Subagents

[VedalAI/swarm-control](https://github.com/VedalAI/swarm-control) is easy to overread. It is not public evidence for an LLM subagent cluster. It is a Twitch Extension/backend/game websocket system for Subnautica-style crowd control.

The repo models carts, transactions, orders, Twitch Bits receipts, and redeems. The backend validates prepurchase/transaction flow, sends redeem messages over a game websocket, and tracks order states. The game message source enum includes `Swarm`, and there is a special PiShock redeem handler that bypasses the game and calls PiShock directly.

So "swarm" here is better understood as an **audience/event swarm**: viewer actions flow through a live-event control plane into game effects or external devices. It is adjacent to the agent architecture because it is another downstream execution surface, but it should not be described as an LLM subagent swarm without more evidence.

## The Core Question: Weights vs. Prompts

This is the most research-relevant aspect of Neuro-sama.

### Vedal's Stated Approach

In GPT-3 era (v2), personality was **entirely prompt-based**. In the custom model era (v3+), personality is **baked into weights** through fine-tuning. System prompts are still used, but only for **situational context** ("you are currently playing Minecraft", "you are talking to Evil Neuro"), not for personality definition.

### Evidence For Weight-Based Personality

1. **Model is reportedly small (2B q2_k, UNVERIFIED)** — IF the small-model claim is true, a model this size at this quantization would struggle to maintain complex character traits from prompt alone, so observed personality consistency would have to come from weights. But this argument is contingent on the size claim being accurate, which is itself sourced only from community lore.
2. **Training data from interactions** — Vedal curates training data from stream transcripts, directly encoding conversational style into the model.
3. **Vedal's explicit statements** — he has distinguished his approach from prompt-only AI characters in interviews.

### Evidence Against (or Nuance)

1. **Evil Neuro complicates the picture** — Community-repeated claim is that Evil Neuro uses the "same base AI" with adjusted prompting style and safety settings. This specific phrasing is itself community lore, not confirmed as Vedal's direct quote. If the claim is true: personality purely in weights would require a separate fine-tune, so prompt changes producing a distinct personality would suggest prompts still play a significant role.
2. **System prompts are still used** — even with weight-based personality, situational prompts shape behavior substantially.
3. **Community replication via prompt-only** — open-source projects (kimjammer/Neuro, Open-LLM-VTuber) achieve passable Neuro-sama-like behavior through prompt engineering alone, suggesting the boundary is fuzzy.

### Likely Reality: Hybrid Approach

The most plausible architecture is a **spectrum**:

```
Pure Prompt ◄────────────────────► Pure Weights
     │                                  │
     │   Open-LLM-VTuber               │
     │   kimjammer/Neuro               │
     │         │                        │
     │         │    Neuro-sama ◄────────┤
     │         │    (hybrid)            │
     │         │                        │
     └─────────┴────────────────────────┘
```

- **Core personality** (speech patterns, humor style, quirks): in weights via fine-tuning
- **Situational behavior** (game context, safety rails, Evil vs normal mode): in prompts
- **Personality differentiation** (Neuro vs Evil): likely LoRA adapter swap or prompt-level control

## Continuous Learning Analysis

### What Neuro-sama Actually Does

Neuro-sama implements **iterative batch fine-tuning**, not true continual learning:

```
Stream (inference only)
    │
    ▼
Collect stream transcripts
    │
    ▼
Vedal manually curates training data
    │
    ▼
Fine-tune model (offline)
    │
    ▼
Deploy updated model on next stream
    │
    ▼
(repeat)
```

Key characteristics:
- **No online learning** — no gradient updates during inference/streaming
- **Human-in-the-loop curation** — Vedal manually selects and filters training data
- **Irregular cadence** — retraining happens when Vedal decides, not on a fixed schedule
- **Catastrophic forgetting risk** — not publicly discussed how this is mitigated across retraining cycles

### Comparison with Memory-Based Approaches

| Aspect | Neuro-sama (weight update) | Memory systems (Mem0, Letta, etc.) |
|--------|----------------------------|-------------------------------------|
| Where knowledge lives | Model weights | External storage (vector DB, graph) |
| Update mechanism | Offline fine-tuning | Real-time CRUD operations |
| Latency to learn | Hours/days (retraining) | Instant (write to DB) |
| Forgetting risk | Catastrophic forgetting | Data management complexity |
| Personality depth | Deep (trained into weights) | Shallow (reconstructed from prompts + facts) |
| Scalability | Expensive (GPU hours per update) | Cheap (DB operations) |
| Auditability | Opaque (weight changes) | Transparent (stored facts) |

### Why This Matters for Pillar 3

Neuro-sama is the closest thing to a production **weight-level personalization** system:

1. It suggests small models may carry personality through fine-tuning, if the 2B community claim is accurate
2. The iterative retraining loop is a primitive form of continual learning
3. The human curation step is the critical bottleneck — automating this is where academic continual learning research becomes relevant
4. The hybrid weights+prompts approach matches the "Pillar 3" hypothesis in findings.md: future systems will combine external memory (facts) with weight updates (personality/style)

## Community Recreations: Pipeline Engineering, Not Learning

All open-source recreations focus on **pipeline engineering** — stitching together LLM, TTS, STT, avatar, and game integration. None attempt weight-level personality or iterative learning. Memory implementations are minimal or absent.

### Project Inventory

#### Open-LLM-VTuber ([GitHub](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber))

- Goal: explicitly stated as recreating Neuro-sama with open-source tools
- Architecture: fully modular pipeline (any LLM + any TTS + any STT + Live2D)
- Personality: **100% prompt-based** — "Shape your AI companion's persona by modifying the Prompt"
- Memory: **none**
- No fine-tuning capability built-in. Supports offline operation, cross-platform

#### kimjammer/Neuro ([GitHub](https://github.com/kimjammer/Neuro), [Dev Blog](https://blog.kimjammer.com/neuro-dev-log-1/))

- Created in 7 days as a recreation experiment. 8 dev logs documenting the journey
- Models: started with Mistral 7B, upgraded to LLAMA 3 8B Instruct (ExLlamaV2) for quality
- Personality: **system prompt + priority-based prompt injection** (~1000 tokens of backstory + example conversations)
- Memory: Twitch chat "last 10 messages" temporarily injected into context, then removed. **No persistent cross-session memory**. Dev log says "Coming Soon: Better summary memory management" — never delivered
- TTS: CoquiTTS XTTSv2 (1-3s latency with DeepSpeed). Voice quality limited by low-quality training clips
- Vision: MiniCPM-Llama3-V for screenshot analysis (spotty API support)
- Key finding: "Good characterization is possible with the system prompt" — but **aligned base models stubbornly resist certain behaviors** (e.g., swearing), even when explicitly prompted. This is where fine-tuning would add value

#### moeru-ai/airi ([GitHub](https://github.com/moeru-ai/airi))

- Most ambitious project. Monorepo with TypeScript/Vue.js/Rust. Alpha v0.9.0
- Goal: "self-hosted, you-owned AI companion" — explicitly inspired by Neuro-sama
- LLM: pluggable via `xsAI` abstraction layer (30+ providers including local Ollama/vLLM)
- Personality: prompt-based via `Velin` framework ("stateful prompts" in Vue SFC + Markdown)
- Memory: **most advanced of all recreations**, but still early:
  - Short-term: in-browser session context
  - Long-term: DuckDB WASM (browser-side) + PGVector (semantic search)
  - "Memory Alaya" system — WIP, not yet documented
- Game: Minecraft (Mineflayer), Factorio (RCON API), Kerbal Space Program (planned)
- TTS: ElevenLabs integration. Voice chat via WebSocket + Discord/Telegram
- Key distinction: web-first architecture (runs in browser), vs kimjammer's local-only Python

#### AIRIS-VtuberAI ([GitHub](https://github.com/neurokitti/AIRIS-VtuberAI))

- Fully offline, no API dependencies. **Requires NVIDIA GPU**
- LLM: Microsoft Phi-3-mini-4k-instruct (supports 4-bit/8-bit quantization)
- Personality: system prompt files (`system_message.txt`)
- Memory: **none** — "Coming Soon: Better summary memory management"
- TTS: OpenVoice (voice cloning). STT: faster_whisper
- Performance: GTX 745 → ~7s latency; RTX 4080 → 1-2s
- Smallest/simplest of the projects, good reference for minimal viable AI VTuber

#### VedalAI/neuro-sdk ([GitHub](https://github.com/VedalAI/neuro-sdk)) — Official

- **Not a recreation** — Vedal's official SDK for game integration with Neuro-sama
- WebSocket-based protocol, with SDKs for Unity, Godot, + community ports (Rust, JS, Python, etc.)
- Reveals Neuro's game interface is a **typed high-level action protocol**: games describe state, register action schemas, and execute validated action responses
- Works best for **turn-based games** (Inscryption, Buckshot Roulette). Real-time games need high-level action abstraction
- Tells us nothing about LLM internals, but confirms the system's external API contract

### Comparative Analysis

| Capability | Neuro-sama | Open-LLM-VTuber | kimjammer | airi | AIRIS |
|-----------|------------|------------------|-----------|------|-------|
| Personality source | **Weights** + prompts | Prompts only | Prompts only | Prompts only | Prompts only |
| Fine-tuning | Yes (iterative) | No | No | No | No |
| Cross-session memory | Unclear/limited | None | None | WIP (DuckDB + PGVector) | None |
| Game playing | Yes (per-game agents) | No | No | Yes (Minecraft, Factorio) | No |
| Model | Custom small model (2B unverified) | Any (pluggable) | LLAMA 3 8B | Any (pluggable) | Phi-3-mini |
| Offline capable | Yes | Yes | Yes | Partial (needs API or local) | Yes |
| Maturity | Production | Stable | Archived | Alpha | Active |

### What the Recreations Tell Us

1. **Pipeline is the easy part.** All projects successfully wire together LLM + TTS + STT + avatar. The real differentiation is elsewhere.

2. **Prompt engineering hits a ceiling.** kimjammer's key finding: aligned base models resist behaviors (swearing, aggression) even when explicitly prompted. Fine-tuning removes this ceiling by overriding alignment at the weight level. This is the clearest evidence for why Vedal fine-tunes.

3. **Memory is the missing piece.** None of the recreations have meaningful cross-session memory. airi is attempting it (DuckDB + PGVector), but it's early. This matches the broader pattern in our memory research — memory integration is hard, and most projects punt on it.

4. **Nobody attempts iterative learning.** Zero projects implement the deploy → collect → retrain cycle. The gap between "pipeline that uses an LLM" and "system that learns from interactions" remains wide in the open-source community.

5. **The official SDK confirms a typed high-level action interface.** Neuro-sama's game integration is not low-level raw control by the LLM. Games describe state and register action schemas; Neuro returns action names plus JSON data; downstream integrations validate and execute. This means the LLM is doing **reasoning over constrained game-state descriptions**, while game-specific controllers handle embodiment.

6. **The public VedalAI repos are stronger evidence for layered agency than for "subagent swarm."** `neuro-inscryption`, `neuro-amongus`, and `neuro-cyberpunk` all split high-level intent from low-level actuation. `swarm-control` is a livestream audience/event control plane, not an LLM agent cluster.

## Open Questions

1. **How does Vedal handle catastrophic forgetting?** With iterative retraining on curated data, each fine-tune risks overwriting previously learned behaviors. Does he use rehearsal, LoRA merging, or simply accept some drift?

2. **What's the boundary between prompt-achievable and weight-necessary personality?** The open-source replications suggest most observable personality traits CAN be prompt-engineered. What specifically does fine-tuning add that prompts cannot?

3. **Is 2B the right scale for personality fine-tuning?** The aggressive quantization (q2_k) suggests latency constraints dominate. Would a larger model with better quantization produce qualitatively different personality depth?

4. **Is Evil Neuro a separate fine-tune or a prompt variant?** This is architecturally significant — if it's a LoRA swap, it proves per-character adapter serving in production. If it's prompt-only on the same weights, it suggests personality is less "baked in" than claimed.

5. **Can the human curation step be automated?** This is where Neuro-sama connects to academic continual learning. If you replace "Vedal manually curates" with "automated data selection + anti-forgetting," you get something closer to a true continual learning system.

## Key Takeaway

Neuro-sama is not true continual learning — it's **iterative supervised fine-tuning with human-curated data from deployment**. But it is the closest production analog:

- It demonstrates the full loop: deploy → collect interaction data → curate → retrain → redeploy
- It suggests weight-based personality is viable at small scale, if the community 2B-parameter claim is accurate
- The bottleneck is human curation, which is exactly what continual learning research aims to automate
- The hybrid weights+prompts approach is likely the practical optimum, not pure weight-based personality
- The public integrations show a second moat: personality is only one layer. The rest of the system is an action protocol plus game-specific embodied controllers.

For the research project, Neuro-sama bridges the gap between Pillar 1 (Memory: external storage) and the hypothetical Pillar 3 (Learning: weight updates). It shows what a primitive, human-in-the-loop version of Pillar 3 looks like in production.

It also widens the research frame: a character agent is not only a model-training problem. In production, the convincing "person" emerges from the combination of weight-level personality, situational prompting, typed action protocols, downstream controllers, and livestream event surfaces.

## References

### Neuro-sama Primary Sources
- [Vedal AI official site](https://vedal.ai/)
- [Vedal's Interview: Neuro-sama's New Model (Internet Archive)](https://archive.org/details/vedals-interview-neuro-samas-new-model-and-the-ai-system-behind-her-yy-9-of-46w-4-a)
- [Vedal on training data sourcing (Threads)](https://www.threads.com/@sinisterpixel/post/DEa_XlXoKjK)
- [VedalAI/neuro-sdk (GitHub)](https://github.com/VedalAI/neuro-sdk) (accessed: 2026-04-27) — official game integration SDK
- [VedalAI/neuro-inscryption (GitHub)](https://github.com/VedalAI/neuro-inscryption) (accessed: 2026-04-27) — official Inscryption integration
- [VedalAI/neuro-amongus (GitHub)](https://github.com/VedalAI/neuro-amongus) (accessed: 2026-04-27) — Among Us controller and training code
- [VedalAI/neuro-cyberpunk (GitHub)](https://github.com/VedalAI/neuro-cyberpunk) (accessed: 2026-04-27) — Cyberpunk 2077 integration
- [VedalAI/swarm-control (GitHub)](https://github.com/VedalAI/swarm-control) (accessed: 2026-04-27) — Twitch Extension / audience control plane

### Reference & Wiki
- [Neuro-sama Wikipedia](https://en.wikipedia.org/wiki/Neuro-sama)
- [Neuro-sama Wiki (Fandom)](https://neurosama.fandom.com/wiki/Neuro-sama)
- [Airis — Neuro-sama Wiki](https://neurosama.fandom.com/wiki/Airis)

### Analysis & Academic
- [My Favorite Streamer is an LLM — arxiv 2509.10427](https://arxiv.org/html/2509.10427v1) (academic study of AI VTuber fandom)
- [The Truth About Neuro-sama's AI](https://futureaiblog.com/the-truth-about-neuro-samas-ai/)
- [SynchroVerse: Neuro-sama Case Study](https://synchroverse.gitbook.io/synchroverse-whitepaper/aria-sentient-influencer/neuro-sama-case-study)

### Community Recreations
- [kimjammer/Neuro (GitHub)](https://github.com/kimjammer/Neuro) — 7-day recreation, 8 dev logs
- [kimjammer blog: Dev Logs 1-8](https://blog.kimjammer.com/neuro-dev-log-1/) — detailed development journal
- [Open-LLM-VTuber (GitHub)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) — modular pipeline framework
- [moeru-ai/airi (GitHub)](https://github.com/moeru-ai/airi) — most ambitious recreation, web-first with memory WIP
- [AIRIS-VtuberAI (GitHub)](https://github.com/neurokitti/AIRIS-VtuberAI) — minimal fully-offline recreation
