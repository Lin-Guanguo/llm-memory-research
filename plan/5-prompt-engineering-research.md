# Prompt Engineering Research Plan

Last Updated: 2026-04-28

## Goal

Study prompt engineering as a lower-level behavior control interface for LLMs.

This direction is deliberately different from the existing Memory and Context tracks:

- **Memory** asks what information is persisted and retrieved across conversations.
- **Context** asks how information is assembled into the model window.
- **Prompt Engineering** asks which input-side patterns change model behavior most reliably for the same task, and where prompting reaches its ceiling.

The core question:

> For the same requirement, which prompt paradigms produce better adherence, reasoning quality, format reliability, and production usability — and which behaviors are difficult to reverse through prompting alone?

## Scope

### In scope

- Prompt paradigms and their comparative effectiveness:
  - direct instruction
  - system vs user placement
  - few-shot and counterexamples
  - schema descriptions and structured output
  - field order and schema-encoded reasoning
  - XML / Markdown / delimiter-based segmentation
  - self-check and review-pass prompts
  - task decomposition and chained prompts
  - persona / role prompts when used for task performance, not just personality
- Prompt limits:
  - behaviors that drift over long context
  - style constraints that lose to pretraining or alignment priors
  - generation-verification gap
  - cases where validator / lint / hook is more reliable than prompt
  - cases where activation steering, LoRA, SFT, DPO, or RL-style learning becomes the right layer
- Production prompt tuning:
  - Dayfold first-line user-facing prompt practices
  - real incident -> prompt change -> evaluation / production signal loops
  - schema override, few-shot, golden tests, A/B switches, and validator migration

### Out of scope

- General "how to write good prompts" tutorials.
- Full context management survey; use `context.summary.md` as prior work.
- Full continual learning survey; use `learning.summary.md` and `personality-engineering.research.md` as prior work.
- Model training implementation. This plan may identify when training is needed, but it does not train models.

## Positioning

This research sits between Context and Learning:

```
Prompt patterns
  -> context / memory placement
  -> schema / tool / validator enforcement
  -> eval and feedback data
  -> activation / adapter / weight-level learning
```

Prompt engineering is treated as the shallowest layer of behavior change. The research should identify:

1. What can be reliably controlled through prompt patterns.
2. What needs structured context, schema, tools, validators, or review passes.
3. What likely requires deeper learning or model intervention.

## Research Questions

### RQ1: Which prompt paradigms still work reliably?

For a fixed requirement, compare:

| Paradigm | Expected strength | Failure mode |
|---|---|---|
| Direct instruction | Cheap, readable | Often ignored under long context or stronger priors |
| System placement | High salience | Not a hard priority in current models |
| Few-shot | Strong pattern induction | Format lock-in; examples can override explicit instructions |
| Positive + negative examples | Defines quality boundary | Needs carefully chosen counterexamples |
| Schema description | Precise field-level control | Cannot guarantee semantic correctness |
| Schema order / intermediate fields | Encodes reasoning path | Can leak unnecessary CoT or bloat output |
| Self-check prompt | Cheap review layer | Weak without checklist or external signal |
| External validator | Deterministic for hard rules | Only works for machine-checkable constraints |

### RQ2: Which behaviors are hard to change by prompt?

Use cases:

- Comment style: model writes long explanatory comments despite project rules.
- Default "AI-ish" expression: generic, over-polished, template-like copy.
- Over-refusal or excessive caution.
- Format fields missing when not present in few-shots.
- Long-output constraints such as "never do X anywhere in this generated artifact."
- Multi-turn drift: instruction obeyed once, then forgotten in later generation.

### RQ3: What is the mechanism-level explanation?

Candidate mechanisms:

- In-context learning and induction heads favor pattern copying over abstract instruction following.
- Few-shot examples create distributional conformity.
- Pretraining / alignment priors override weak prompt-level constraints.
- Generation and verification are asymmetric abilities.
- Reasoning models may respond differently to few-shot vs direct instruction.

### RQ4: What does production prompt tuning actually look like?

Use Dayfold as the primary production case bank:

- planner few-shots and `memory_query` add/drop symmetry
- schema description overrides via YAML
- prompt profiles and per-node model routing
- `l:` literal binding to avoid passing raw mixed user input into every node
- prompt bias removal in planner
- BGM mandatory rule moving from prompt to validator
- pattern chat image-slot contract prompt fix
- story_writer / pages_enhancer / style_resolver / cover_design production prompts
- golden prompt tests, A/B toggles, and production issue-driven edits

## Source Plan

### Official model-provider guidance

Use current official docs as a baseline for recommended practices:

- Anthropic Claude prompt engineering docs
- OpenAI prompt engineering / Structured Outputs / evals docs
- Google Gemini prompting strategies

Focus on areas where official guidance converges or diverges:

- examples / few-shot
- XML or delimiter structure
- chain-of-thought vs hidden reasoning
- structured outputs
- eval-first prompt iteration
- model-specific prompting recommendations

### Academic and survey sources

Initial paper list:

- The Prompt Report: A Systematic Survey of Prompting Techniques
- Automatic Prompt Optimization survey
- Instruction hierarchy and system prompt robustness papers
- In-context learning / induction heads papers
- Generation-verification gap papers
- Long-context instruction following benchmarks

Use papers for mechanisms and taxonomy, not for production claims unless backed by usable evidence.

### Production case sources

Primary repositories / docs:

- `/Users/linguanguo/dev/dayfold_webapp`
- `/Users/linguanguo/dev/dayfold_webapp-new`
- CyberMnema W17 topics:
  - `timeline/2026/04/W17/LLM指令遵从研究-2026-04-23.md`
  - `timeline/2026/04/W17/PE生产技巧-2026-04-24.md`
  - `timeline/2026/04/W18/记忆上下文与PE启发整理-2026-04-28.md`

The production case study should preserve specific before/after examples when possible:

- symptom
- prompt or schema change
- expected mechanism
- verification method
- observed result or remaining risk

## Phasing

### Phase 1: Taxonomy and prior work

- Read official guidance from Anthropic, OpenAI, and Google.
- Read the main prompt technique surveys.
- Extract a compact taxonomy of prompt paradigms.
- Map each paradigm to expected strengths and failure modes.

Output:

- `prompt-engineering.research.md` first draft with taxonomy and research framing.

### Phase 2: Production case extraction

- Extract Dayfold prompt practices from prompt profiles, schema overrides, planning docs, tests, and incident-driven changes.
- Create a case table grouped by behavior-control pattern.
- Separate proven production signals from plausible but unverified hypotheses.

Output:

- `production-prompt-patterns.research.md` or a major section inside `prompt-engineering.research.md`.

### Phase 3: Failure boundary analysis

- Integrate the W17 instruction-following topic.
- Classify prompt failure modes:
  - instruction drift
  - prior override
  - few-shot lock-in
  - generation-verification gap
  - long-output constraint decay
  - multimodal reference entanglement
- For each failure, identify the better control layer:
  - stronger prompt
  - few-shot
  - schema
  - validator
  - review pass
  - learning / training

Output:

- "Prompt ceiling" section in the main research document.

### Phase 4: Evaluation and optimization

- Survey eval-first prompt iteration.
- Compare manual prompt tuning with automatic prompt optimization.
- Define what a minimal production eval harness would look like for Dayfold prompt work:
  - golden cases
  - schema adherence checks
  - task-specific rubric
  - pairwise preference labels
  - production incident regression cases

Output:

- Eval playbook section.

### Phase 5: Cross-layer synthesis

Connect the result back to existing tracks:

- Update `findings.md` with prompt-as-behavior-interface findings.
- Update `learning.summary.md` if prompt limits point to activation / LoRA / SFT boundaries.
- Update `context.summary.md` only if prompt effectiveness depends on context placement.

Output:

- Revised cross-domain synthesis.

## Deliverables

Minimum useful output:

- `prompt-engineering.research.md` — main research document.
- Dayfold production prompt pattern table inside the main doc or as `production-prompt-patterns.research.md`.
- Updates to `findings.md` and `README.md`.

Optional output:

- A small Dayfold prompt eval design note.
- A public-facing Chinese article after the research stabilizes.

## Evaluation Criteria

This research is useful only if it avoids becoming a prompt tips list.

Each finding should answer at least one of:

1. What behavior does this prompt pattern control?
2. Why does it work mechanistically?
3. When does it fail?
4. What evidence supports it?
5. What control layer should replace prompt when it fails?

## Initial Hypotheses

1. **Few-shot is the strongest prompt-level control surface** for structured behavior because it exploits pattern induction.
2. **Schema is prompt engineering in disguise**: field descriptions, enum labels, field order, and required fields often outperform global instructions.
3. **Prompt placement has no absolute hierarchy** in current models; examples and recent context can override system instructions.
4. **Hard rules should migrate out of prompt** into validators, lint, hooks, or tool contracts.
5. **Production PE is node-level, not prompt-level**: a pipeline with per-node prompts, schemas, models, and evals is more reliable than a single universal prompt.
6. **Prompt failures are training data candidates**: repeated prompt fixes with stable eval signals are candidates for activation, adapter, or weight-level learning.

## References

Starting points:

- Anthropic Claude prompt engineering docs: <https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview>
- OpenAI Structured Outputs: <https://platform.openai.com/docs/guides/structured-outputs>
- OpenAI Evals: <https://platform.openai.com/docs/guides/evals>
- Google Gemini prompting strategies: <https://ai.google.dev/gemini-api/docs/prompting-strategies>
- The Prompt Report: <https://arxiv.org/abs/2406.06608>
- Automatic Prompt Optimization survey: <https://arxiv.org/abs/2502.16923>
- In-context Learning and Induction Heads: <https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html>
- The Instruction Hierarchy: <https://arxiv.org/abs/2404.13208>
