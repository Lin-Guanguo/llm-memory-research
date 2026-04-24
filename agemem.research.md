# AgeMem Technical Research Report

Last Updated: 2026-04-15

> **Research Methodology**: This document is based on primary analysis of the arXiv paper [AgeMem: Agentic Memory for LLM Agents (arXiv:2601.01885)](https://arxiv.org/abs/2601.01885) via its HTML build and local PDF fallback, cross-referenced with the 2026 Memory Survey (arXiv:2512.13564) taxonomy and contrasted against the heuristic-driven systems already cataloged in this repository (Mem0, Letta, Hindsight, Graphiti, A-MEM, MemOS, Mastra, Supermemory). Implementation details not disclosed in the paper are explicitly flagged. Where paper excerpts were inconclusive, claims are marked as "author-stated" to avoid overclaiming.

## Overview

**AgeMem** (Agentic Memory) is the first published system that trains a **unified long-term/short-term memory controller as a single RL policy**, rather than relying on separate heuristics or prompt-engineered LLM calls for each memory operation. The six memory operations — `Add`, `Update`, `Delete` (LTM side) and `Retrieve`, `Summary`, `Filter` (STM side) — are exposed to the agent as tool actions, and the policy that decides when and how to invoke them is trained end-to-end with a three-stage progressive GRPO curriculum.

This is architecturally significant for the taxonomy maintained in this repository. Every system cataloged so far — Mem0, Letta (MemGPT), Graphiti, Hindsight, Mastra, MemOS, Supermemory — implements memory management as either (a) scripted heuristics (cron-style consolidation, threshold-based eviction), (b) **prompted** LLM calls that use an LLM as a CRUD editor without gradient updates, or (c) tool-call loops at inference where the base LLM is already trained. The 2026 Memory Survey (2512.13564) groups systems in AgeMem's family under "policy-learned management"; AgeMem is the first deep-dive specimen this repo has for that family.

**Key claim from authors**: treating LTM and STM as facets of one learnable policy rather than two independent subsystems enables end-to-end optimization for downstream task reward, yielding consistent gains across five long-horizon benchmarks with Qwen2.5-7B-Instruct and Qwen3-4B-Instruct backbones.

**Authors**: Yi Yu, Liuyi Yao, Yuexiang Xie, Qingquan Tan, Jiaqi Feng, Yaliang Li, Libing Wu.
**Source**: [arXiv:2601.01885](https://arxiv.org/abs/2601.01885) | [HTML v1](https://arxiv.org/html/2601.01885v1)

---

## 1. The Unified-Policy Pitch vs. Separate LTM/STM Heuristics

### What existing systems do

In Mem0, STM is just the raw conversation buffer and LTM is a vector/graph store populated by an "extract-update pipeline" — an LLM is prompted with a fixed template to decide whether to CREATE, UPDATE, DELETE, or NOOP each fact. The LLM is never fine-tuned for this job. Letta (MemGPT) pushes the decision boundary further — it exposes tools like `core_memory_append`, `archival_memory_insert`, `conversation_search` — but the model invoking them is the base LLM at inference, with zero reward signal on the memory operations themselves. Hindsight bolts on a separate consolidation engine that periodically runs LLM-driven summarization heuristics.

In all three, memory management is either **hand-crafted logic** or **prompt-conditioned LLM behavior**. No gradient ever flows from "task succeeded" back into "good memory write."

### What AgeMem does differently

AgeMem reframes the agent's forward pass as:

```
state s_t = (conversation C_t, LTM store M_t, task T)
   |
   v
policy π_θ chooses action a_t ∈ {Add, Update, Delete,
                                  Retrieve, Summary, Filter,
                                  Answer, Think}
   |
   v
environment applies tool effect deterministically → s_{t+1}
```

Memory read/write is no longer an out-of-band plumbing layer — it is part of the action space the policy is trained to use. When the policy calls `Add(content="Alice works at Google")` early in the trajectory and ten turns later issues a correct `Answer`, the terminal reward flows through GRPO advantages all the way back to that `Add` token, nudging the policy toward storing query-relevant content preemptively. This is the "learnable mechanism" claim: the controller **learns** to store, not from a prompt but from reward.

This is the dividing line between "prompted LLM control" and "trained memory policy," which we revisit in §8.

---

## 2. Policy Formulation

### Action space (exact semantics from §3)

| Op | Side | Signature | Effect |
|----|------|-----------|--------|
| `Add` | LTM | `Add(content, metadata)` | Insert new record `m_i` into `M_t` with embedding and metadata |
| `Update` | LTM | `Update(memory_id, new_content)` | Modify existing record referenced by `memory_id` |
| `Delete` | LTM | `Delete(memory_id)` | Remove record (author-stated: "with confirmation") |
| `Retrieve` | STM→LTM | `Retrieve(query, k)` | Return top-k memories by cosine similarity, inject into `C_t` |
| `Summary` | STM | `Summary(span)` | Compress a conversation span into a condensed message |
| `Filter` | STM | `Filter(threshold θ)` | Drop messages below similarity threshold (θ=0.6) w.r.t. active task |

Plus two non-memory actions: `Think` (chain-of-thought) and `Answer` (terminal).

Each tool is a deterministic function on `(C_t, M_t)`. The policy only emits the JSON tool call; the environment executes it. This deterministic separation matters for credit assignment — the policy is not graded on the embedding quality of its writes, only on whether the downstream `Answer` succeeds.

### State representation

State at step `t` is the triple `s_t = (C_t, M_t, T)`:

- `C_t = [u_1, u_2, …, u_{n_t}]` — the running conversation / context window
- `M_t = {m_i}` — the LTM store (rows with id, content, embedding, metadata)
- `T = (q, I_q, A_q)` — task spec: query `q`, contextual info `I_q`, gold answer `A_q`

The policy only sees `C_t` directly in its context window. `M_t` is accessed only through `Retrieve` calls — i.e., the policy has to **learn to query its own memory**.

### Reward signal — **shaped, not pure binary**

This is one of the most important design choices and is where AgeMem diverges from a vanilla "reward = did you answer correctly" setup. The trajectory-level reward is a four-component composite:

1. **Task completion** `R_task` — LLM-judge score `S_judge(A_pred, A_q) ∈ [0,1]`; `-1.0` penalty if no answer produced.
2. **Context management** `R_context` — three normalized terms:
   - Compression efficiency: `max(0, 1 - T_used/T_max)`
   - Preventive action: `1` if a compression tool fired **before** overflow, else `0`
   - Preservation: `1` if query-critical tokens are retained post-filter
3. **Memory management** `R_memory`:
   - Storage quality: `N_high_quality / max(1, N_total)` (an auxiliary LLM judges each stored item)
   - Maintenance: `1` if at least one `Update`/`Delete` occurred
   - Semantic relevance: `S_LLM(R, q) ∈ [0,1]` — auxiliary LLM scores retrieved set against query
4. **Penalties** — `-1.0` for exceeding max rounds, `-0.5` for token overflow.

Component weights are reported as uniform 1.0 ("without manual tuning"), which is a claim worth skepticism (§10).

**Sparseness**: the reward is computed **only at trajectory termination** (it is sparse in time) but is **shaped in magnitude** — it is not binary task success. The paper calls this "sparse and discontinuous rewards induced by memory operations" and explicitly designs step-wise GRPO to handle it. Because multiple tool calls happen per trajectory with no intermediate signal, the only mechanism that ties memory ops to reward is advantage broadcast (§3).

---

## 3. Three-Stage Progressive GRPO

### Stages (curriculum)

The curriculum decomposes the long-horizon task into three phases, each with its own sub-trajectory of length `T_1`, `T_2`, `T_3`:

| Stage | Input | Duration | What the policy learns |
|-------|-------|----------|-----------------------|
| **1. LTM Construction** | Contextual facts `I_q` streamed in | `T_1` turns | When to `Add` / `Update` / `Delete`; how to curate high-quality LTM records |
| **2. STM Control** | `C_t` reset; semantically-related **distractors** injected | `T_2` turns | When to `Filter` and `Summary`; to resist distractor pollution while LTM persists |
| **3. Integrated Reasoning** | Query `q` revealed | `T_3` turns | To orchestrate `Retrieve` + `Think` + `Answer` under the state produced by Stages 1-2 |

The full trajectory `τ_k(q) = (τ_k^(1), τ_k^(2), τ_k^(3))` has total length `T = T_1 + T_2 + T_3`. Crucially, the **same policy** acts in all three stages — the curriculum is a reward-shaping device, not a multi-head split. What makes it "progressive" is that the reward components unlock in sequence: memory-quality reward is only meaningful after Stage 1 writes exist; context-management reward only kicks in once Stage 2 distractors arrive.

### Step-wise GRPO specifics

GRPO (Group Relative Policy Optimization, DeepSeek-R1 style) normalizes advantages within a rollout group rather than using a learned value baseline. The step-wise variant:

- Sample `K` rollouts per task (paper says `K ≈ 4–8`, not more specific).
- Compute terminal reward `r_T(k, q)` for each rollout.
- Group-normalize: `A_T(k, q) = (r_T(k, q) − μ_{G_q}) / (σ_{G_q} + ε)` where `G_q` is the group mean/std across the K rollouts for task q.
- **Broadcast** `A_t(k, q) = A_T(k, q)` uniformly to every timestep in the rollout. This is the "step-wise" twist — every token in every tool call gets the same advantage, solving long-range credit assignment by brute force.
- Policy objective: `J(θ) = E[ρ_t A_t − β · D_KL(π_θ ‖ π_ref)]` with standard importance weight `ρ_t` and KL anchor to the reference policy.

No value network, no GAE. The batch aggregation scales as `ℰ = B × K × T̄` experiences per iteration — with long trajectories this is expensive (§9).

---

## 4. Training Data

### HotpotQA (primary)

Used verbatim as the Stage 1 source: supporting facts become `I_q`, the HotpotQA question becomes `q`, and the human answer is `A_q`. Stage 2 distractors are synthesized by a language model (topical but unrelated claims). This gives a clean gold signal for the terminal judge reward.

### Agentic benchmarks (ALFWorld, SciWorld, PDDL, BabyAI)

These don't natively split into facts/query/answer, so the authors **construct** three-stage trajectories: `T_1` turns of environment observation (Stage 1 extracts state into LTM), `T_2` turns of distractor/noise injection (Stage 2 denoising), then `T_3` turns of actual task interaction. Distractors are programmatically injected during Stage 2.

### How the "correct" action is labeled

It isn't — there is no supervised action label. The policy bootstraps from the base instruction-tuned model (Qwen2.5-7B-Instruct or Qwen3-4B-Instruct) that already knows how to emit tool calls, then discovers good memory-operation patterns through reward. This is pure RL from scratch on the tool-use structure, no SFT warm-up mentioned in the main text. Dataset sizes are deferred to Appendix C.1 and were not extractable from the HTML version.

---

## 5. Empirical Results

### Headline table (success rate / LLM-judge score; higher is better)

**Qwen2.5-7B-Instruct backbone:**

| Method | ALFWorld | SciWorld | PDDL | BabyAI | HotpotQA | Avg |
|--------|---------:|---------:|-----:|-------:|---------:|----:|
| No-Memory | — | — | — | — | — | ~28.1* |
| LangMem | — | — | — | — | — | — |
| A-Mem | — | — | — | — | — | — |
| **Mem0** | 37.49 | 26.99 | 13.96 | 60.58 | 46.66 | 37.14 |
| Mem0^g | — | — | — | — | — | — |
| AgeMem-noRL | — | — | — | — | — | — |
| **AgeMem (full)** | **41.07** | **35.55** | **17.31** | **61.42** | **54.44** | **41.96** |

**Qwen3-4B-Instruct backbone:**

| Method | ALFWorld | SciWorld | PDDL | BabyAI | HotpotQA | Avg |
|--------|---------:|---------:|-----:|-------:|---------:|----:|
| Mem0 | 41.17 | 51.38 | 31.72 | 60.05 | 39.16 | 44.70 |
| **AgeMem** | **48.97** | **59.48** | **35.07** | **72.56** | **55.49** | **54.31** |

The paper reports aggregate gains of **+49.59% relative** over No-Memory on Qwen2.5-7B and **+23.52% relative** on Qwen3-4B. Against the strongest heuristic baseline (Mem0), AgeMem wins on every benchmark × backbone combination extracted, with the largest absolute margins on SciWorld (+8.56 / +8.10), PDDL (+3.35), and HotpotQA (+7.78 / +16.33).

*The No-Memory average is inferred from the stated +49.59% relative gain, not directly quoted.*

### Memory quality and context efficiency

- **Memory quality on HotpotQA** (auxiliary LLM-judged relevance of stored records): AgeMem 0.533 (Qwen2.5) / 0.605 (Qwen3-4B) vs. baselines 0.479-0.513. The policy writes **more relevant** records, not just more records.
- **Context tokens on HotpotQA**: AgeMem uses 2,117 avg tokens vs. 2,186 for a RAG variant — a 3.1% reduction on Qwen2.5 and 5.1% on Qwen3-4B, while scoring higher. The policy learned to compress proactively rather than stuff the window.

### Against heuristic baselines already in this repo

AgeMem beats Mem0 across the board. LangMem and A-Mem are listed in the baseline roster but their specific numbers did not extract cleanly from the HTML — the paper says AgeMem "consistently outperforms strong memory-augmented baselines across multiple LLM backbones." Hindsight and Letta are **not** benchmarked — AgeMem uses agentic RL-style benchmarks (ALFWorld/SciWorld/BabyAI/PDDL) rather than conversational ones (LongMemEval/LoCoMo) where Hindsight dominates. The two systems therefore don't share a head-to-head number.

---

## 6. Ablations

The ablation structure is component-additive on Qwen2.5-7B:

- **+LT** (LTM tools only, no RL): +10.6% / +14.2% / +7.4% across three headline benchmarks vs. no-memory.
- **+LT/RL** (LTM tools + RL but no STM tools): additional +6.3% on HotpotQA.
- **+LT/ST/RL** (full system): +13.9% / +21.7% / +16.1% cumulative gain.

Three takeaways:

1. **Just having the tools exposed (no RL)** already recovers 40-60% of the final gain — the tool vocabulary itself is valuable, echoing Letta's thesis.
2. **RL contributes meaningfully** but not dominantly on top of tools-only; the delta is ~6 points, not the bulk.
3. **STM tools add the largest marginal jump**, especially on tasks with heavy distractor load (Stage 2 is where `Filter`/`Summary` shine).

**Reward ablation** compares two trajectory credit strategies:
- *All-Returns* (the full shaped composite from §2): 0.544 judge score, 0.533 memory quality.
- *Answer-Only* (binary task success): 0.509 judge score, 0.479 memory quality.

All-Returns "converges faster with superior stability." Translation: the shaped reward is doing real work, and a clean binary reward underperforms noticeably — which is informative because it means the system's gains are not purely from "tools + RL" but from "tools + RL + careful reward shaping."

**Tool-usage deltas** post-RL on Qwen2.5: `Add` frequency rises from 0.92 → 1.64 per trajectory, `Update`/`Delete` emerge from near-zero to 0.13/0.08, and `Filter` jumps 0.02 → 0.31. The policy learns to **maintain** memory (not just accumulate), and to **proactively filter**.

No stage-wise ablation (remove Stage 1 / 2 / 3 separately) is reported in the extracted content. No per-operation ablation (remove `Summary` alone) is reported either. This is a real gap — the survey paper (§11 takeaway) would want to know which operations are load-bearing, and the current ablations answer only coarsely.

---

## 7. Comparison with A-MAC (Admission-Only Learned Control)

A-MAC (surveyed in 2512.13564 as the admission-learning exemplar) trains a **classifier**, not a policy, to decide **write vs. no-write** on each incoming message — it is a binary filter at the LTM ingress only. Retrieval, update, deletion, summarization, STM management — all out of scope.

AgeMem is strictly a superset in scope:

| Aspect | A-MAC | AgeMem |
|--------|-------|--------|
| Scope | Admission to LTM only | Full lifecycle (6 ops) + STM |
| Learner | Discriminative classifier | RL policy over tool space |
| Signal | Supervised labels (write-worthy?) | Trajectory-level composite reward |
| Coupling to task | Decoupled — memory trained offline | End-to-end — memory trained against task reward |
| Inference cost | Negligible (one classifier call per write candidate) | Full policy forward pass per tool decision |

The AgeMem pitch vs. A-MAC is: admission is necessary but not sufficient — you also need to know **when** to retrieve, **what** to summarize, **which** stored items to update. Heuristics for those are just as lossy as heuristics for admission. A learned policy covers all of them at once.

Cost: AgeMem pays the price of full RL training where A-MAC only trains a small classifier.

---

## 8. Comparison with Heuristic / Prompted-LLM Systems

This is the critical positioning question for this repository. The distinction is **not**:

> AgeMem uses an LLM; Mem0 uses rules.

Mem0 uses an LLM too — every extract-update decision passes through a prompted LLM call. The real distinction is:

> AgeMem **fine-tunes the weights** of the LLM that makes memory decisions, with gradients flowing from downstream task reward back through every memory operation. Mem0 and Letta do **not** — their LLMs are fixed; only the prompt can be adjusted.

Concretely:

| System | Memory-decision LLM | Trained for memory? | Reward flows to memory ops? |
|--------|---------------------|---------------------|------------------------------|
| Mem0 | Prompted (GPT-4o-class) | No (prompt-only) | No |
| Letta / MemGPT | Prompted base LLM via tools | No | No |
| Hindsight | Prompted for retain/reflect | No (the consolidation logic is scripted) | No |
| Graphiti | Prompted for entity extraction | No | No |
| A-MEM | Prompted for note-taking | No | No |
| **AgeMem** | Fine-tuned via GRPO | **Yes** | **Yes** (group-normalized advantages broadcast to every step) |

The consequence: prompted systems can only get better by **better prompt engineering** or by **swapping in a better base LLM**. AgeMem can get better by **more training data or more RL steps**, specializing the same base model to a particular memory regime. The two scaling axes are different.

Whether this matters in practice depends on whether specialization beats general instruction-following. The ablations suggest it does — a non-trivial +6 points on HotpotQA from RL on top of the same tool vocabulary — but the ceiling of the approach is set by how much task reward you can collect, which is a data problem AgeMem doesn't fully solve.

---

## 9. Production Viability

### Training cost — **not disclosed**

The paper is silent on GPU-hours, total step count, learning rate, and batch size in the main text. What can be inferred:

- Two backbones (Qwen2.5-7B, Qwen3-4B) × group size K ≈ 4-8 × long trajectories of `T_1+T_2+T_3` turns each × five benchmarks is non-trivial. GRPO with group size 8 on 7B models typically costs thousands of GPU-hours for comparable RL-on-reasoning setups (cf. DeepSeek-R1, Tulu 3).
- No value network reduces memory overhead vs. PPO, so per-step cost is lower than classical actor-critic.
- The aggregate `B × K × T̄` experience count scales multiplicatively with trajectory length — STEP 1 facts + STEP 2 distractors + STEP 3 reasoning can easily push `T̄ > 30` tool-call turns.

Realistic floor: this is not something an individual researcher runs on one A100. Expect tens to low-hundreds of H100s for the reported setup.

### Inference cost

At serve time, the policy is a vanilla 4B or 7B model — a tool call per memory op, deterministic tool execution. Per-query latency should be comparable to any tool-using agent of equivalent size. The token-usage wins (3-5% reduction) are modest but free. No inference-time RL overhead.

### Code release

Not mentioned in the extracted HTML. The paper references the **AgentScope** framework for agent orchestration and the **Trinity** framework for fine-tuning — both Alibaba-adjacent projects — which suggests eventual open source is plausible but not confirmed at time of writing. The lack of a public repository is the biggest blocker to reproducibility at present.

### Data requirements

HotpotQA is public. ALFWorld / SciWorld / PDDL / BabyAI are public. Dataset sizes were not extractable. The bigger question is whether a **new domain** (say, a customer-support agent) requires re-running the full three-stage RL. The paper does not address transfer; §10 returns to this.

---

## 10. Limitations

**Author-acknowledged:**
1. Fixed tool set (6 ops) — "clear and effective abstraction but could be extended." No compositional/parameterized tools.
2. Evaluation limited to five representative benchmarks — no LongMemEval, no LoCoMo, no production-style streams.
3. Scalability of the LTM store under long-running deployment is not studied — all trajectories are finite-horizon episodes.

**Not author-acknowledged but salient:**

4. **Reward hacking exposure.** The composite reward includes components like "storage quality = N_high_quality / max(1, N_total)," judged by an auxiliary LLM. An RL policy with enough steps will exploit any weakness in that judge — writing short, generic, high-scoring facts; avoiding legitimately messy writes because they score worse; gaming the "maintenance" bonus by doing a trivial `Update` every trajectory. No analysis of this is presented.

5. **Uniform reward weights (1.0)** without tuning is suspicious. The paper frames this as a strength ("no manual tuning"); more charitably, it means no one systematically studied how much each component contributes, and the ablation only compares All-Returns vs. Answer-Only, not the sub-components.

6. **No cross-task generalization test.** The policy is trained per-benchmark (or at least per-benchmark-family — the setup is unclear). A memory policy that must be re-trained for every new domain is strictly weaker than a prompted Mem0-style system that drops in for any domain without retraining. If AgeMem's gains don't survive transfer, the production calculus flips.

7. **Advantage broadcasting is a coarse credit-assignment hack.** Every token in a long trajectory receiving the same advantage means early memory-writing tokens are credited equally with reasoning tokens at the end. This works when the trajectory has few actions, but breaks down as the horizon grows — arguably the exact regime AgeMem is designed for. The paper does not study how the learning signal degrades at `T = 50` vs. `T = 20`.

8. **No report of training instabilities.** GRPO on long tool-use trajectories is notoriously finicky. The absence of loss curves, KL-blow-up discussion, or reward-collapse mentions is either confidence or omission.

9. **LLM-as-judge dependency.** Task reward `S_judge`, memory-quality reward, and retrieval-relevance reward are all judged by auxiliary LLMs. The entire RL signal is bottlenecked on judge calibration. No analysis of judge agreement with human labels is provided.

---

## 11. Takeaways — When Is a Learned Memory Policy Worth It?

Reconciling AgeMem against the heuristic systems already cataloged in this repo:

### Learned policy is worth it when
- You have a **fixed target task distribution** with ample interaction data (RL data isn't free — it's harder to get than Mem0's zero-shot prompting).
- You can build a **reliable automatic reward** (task completion judge + memory-quality judge). Without it, the policy has nothing to climb.
- Your benchmark is **long-horizon with distractors** — AgeMem's largest wins are on SciWorld / HotpotQA where context compression and selective recall matter. On short-horizon tasks the tool vocabulary alone (the +LT-only ablation) captures most of the gain.
- You already own the **base model weights** and the training budget — this is an in-house-LLM play, not a drop-in API upgrade.

### Prompted control (Mem0/Letta/Hindsight style) is worth it when
- You need **zero-shot domain portability** — a new customer, a new vertical, drop it in.
- You have a **strong general LLM** (Sonnet, GPT-4.x) whose prompted tool use is already above your quality bar.
- You care about **auditability and debuggability** — a prompted pipeline is far easier to inspect than an RL-trained policy whose memory-op distribution is implicit in weights.
- You don't have training infrastructure. Mem0 on top of a frontier API often wins on total-cost-of-ownership even if peak quality is slightly lower.

### Hybrid (likely the endpoint)
The most realistic production architecture is **prompted LLM for the control surface + learned classifier for admission** (A-MAC style) + **learned policy for the subset of operations where reward signal is cleanest** (summarization is a good candidate — reward = downstream retrieval success is measurable). Full AgeMem-style end-to-end RL on all six operations, as the paper presents it, looks like the strongest research result this repo has for "policy-learned management" but is not yet a production-ready drop-in for 2026 stacks.

### For this repo's research program
AgeMem is the **canonical first data point** for the "learned memory controller" family — it answers "can the full lifecycle be RL-trained at all?" with a yes. The next open questions are cross-domain transfer, training cost transparency, reward-hacking resistance, and whether learned control beats prompted control when the prompted controller is a frontier model rather than Qwen-7B. Until an open-source release (or a reproduction) lands, AgeMem's headline numbers should be read as an existence proof, not a production recipe.

---

## Appendix: Key numbers at a glance

- **Benchmarks**: ALFWorld, SciWorld, PDDL, BabyAI, HotpotQA
- **Backbones**: Qwen2.5-7B-Instruct, Qwen3-4B-Instruct
- **Average success**: 41.96% (Qwen2.5) / 54.31% (Qwen3-4B)
- **Relative lift over No-Memory**: +49.59% / +23.52%
- **Beats Mem0 on every benchmark × backbone extracted**
- **Memory quality**: 0.533 / 0.605 vs. 0.479-0.513 baselines
- **Token reduction vs. RAG variants**: 3.1% / 5.1%
- **Action space**: 6 memory ops (Add/Update/Delete/Retrieve/Summary/Filter) + Think + Answer
- **Training**: three-stage progressive GRPO, step-wise terminal-advantage broadcast, group size K≈4-8
- **Reward**: shaped composite (task + context + memory + penalties), sparse-in-time but magnitude-shaped
- **Training cost**: not disclosed
- **Code release**: not mentioned
