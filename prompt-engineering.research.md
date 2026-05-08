# Prompt Engineering as Behavior Control

Last Updated: 2026-04-30

## Overview

This document treats prompt engineering as the shallowest behavior-control interface for LLMs. The question is not "what clever phrase works?", but:

> For the same requirement, which input-side patterns produce more reliable behavior, and where does prompting stop being the right control layer?

The working thesis:

1. Prompt engineering still matters, but its highest-leverage forms are examples, schema, delimiters, decomposition, and eval-driven iteration, not magic wording.
2. Prompt behavior is controlled by the whole prompt distribution: instructions, examples, schema field descriptions, field order, visible context, tool contracts, output parsers, and validators.
3. Hard requirements should move downward into deterministic layers whenever possible: structured outputs, tool schemas, validators, hooks, tests, or review passes.
4. Prompt assets are not fully model-independent. Model switches often require prompt/profile/schema retuning because each model family has different priors, reasoning behavior, structured-output implementation, and instruction-following quirks.
5. Repeated prompt failures with stable eval signals become candidates for deeper learning: activation steering, LoRA/adapters, SFT, DPO, or reinforcement-style optimization.

This document is the long-form research draft for Phase 1 and Phase 2 of [plan/5-prompt-engineering-research.md](./plan/5-prompt-engineering-research.md). It should be treated as a source-of-truth notebook and evidence index. Later blog posts can extract sharper claims from it, but this file should preserve the full reasoning trail: literature, provider guidance, local observations, Dayfold production evidence, caveats, and deferred validation questions.

## Research Questions and Evidence Standard

This track is intentionally more concrete than a general prompt-writing guide. It should answer five research questions:

1. Which prompt patterns still have robust practical value at the current model stage?
2. Which behaviors repeatedly fail under prompt-only control?
3. How do schema, structured outputs, and constrained decoding change prompt engineering?
4. Which Dayfold prompt changes are merely stylistic, and which reveal reusable production patterns?
5. What evidence is strong enough for a public blog claim, and which claims must remain caveated because this round does not run new evals?

Evidence is separated into tiers:

| Tier | Evidence type | What it can support | Main limitation |
|---|---|---|---|
| A | Primary research papers and benchmark papers | Mechanism-level or controlled empirical claims | Often benchmark-specific and not always production-shaped |
| B | Official provider docs and implementation notes | What APIs officially expose, recommend, or claim | Provider-specific; may omit implementation details |
| C | Dayfold production code, prompt files, plans, and commit history | What survived first-line product tuning | Incident history is not a controlled A/B test |
| D | Personal observations and CyberMnema topic notes | Useful synthesis and hypothesis formation | Needs triangulation before becoming a strong claim |
| E | Hypotheses inferred from the above | Future research direction and eval design | Not blog-ready unless clearly labeled as hypothesis |

The standard for the final blog should be: every strong claim must be backed by at least one Tier A or B source, or by multiple Dayfold production signals plus a clear caveat that the evidence is production-observational rather than controlled.

Scope note: this research round does not include running new controlled evals. Eval design is kept as future work and as a caveat framework, not as a prerequisite for the current research summary.

## Evidence Map

The current findings come from four buckets.

### 1. Existing research and provider guidance

The strongest external evidence supports:

- Few-shot examples as pattern induction rather than mere examples. In-context learning papers support the claim that demonstrations transmit format, label space, input distribution, and task pattern.
- CoT-style intermediate reasoning as useful for complex reasoning, with important caveats. CoT, self-consistency, least-to-most, and ReAct all support decomposition, intermediate state, and reasoning/action interleaving.
- Prompt hierarchy and instruction following as imperfect. Instruction hierarchy work supports the view that prompt placement is not a hard security boundary unless models are explicitly trained for it.
- Structured outputs as a stronger layer than plain JSON prompting. OpenAI's structured-output implementation note directly describes constrained decoding, while JSONSchemaBench shows constrained decoding has become a central structured-generation technology.
- Schema wording as an instruction channel. The 2026 schema-key wording paper directly supports the claim that schema text can affect behavior even under constrained decoding.
- Self-review as limited without external signal. Self-Refine supports iterative review as useful in some tasks, while "LLMs Cannot Self-Correct Reasoning Yet" warns that intrinsic self-correction can fail or degrade performance without external feedback.

### 2. Official API and product guidance

Provider docs converge on the same production pattern:

- Prompts should be evaluated, versioned, and tested, not tuned by intuition alone.
- Examples and clear structure are recommended for controlling output format and response pattern.
- Structured outputs are the preferred mechanism when shape matters.
- Schema descriptions and property ordering can be model-visible controls, not passive documentation.
- A separate reasoning or support field can improve final-answer quality, but should be treated as an intermediate product contract, not as a guarantee of truth.

### 3. Dayfold production evidence

Dayfold supplies a different kind of evidence: first-line prompt tuning in a multimodal user product. The evidence is strongest where a commit or plan connects a concrete failure to a concrete prompt/schema/context change.

The strongest Dayfold patterns are:

- `schema_overrides`: LLM-visible Pydantic field descriptions were moved into configurable YAML.
- Schema descriptions were repeatedly realigned after prompt changes, implying prompt and schema drift had real behavior cost.
- `thinking`, `analysis_*`, and `global_reasoning` fields were used as output-contract reasoning fields.
- Planner few-shots encode routing and binding policy, not just examples.
- Reference images and user inputs were routed deliberately; this is context-engineering evidence that should be controlled when evaluating prompt changes.
- Visible control markers such as `"[封面]"` could leak into generated artifacts and were replaced with structured metadata.
- Numeric page indices were replaced with semantic page labels, matching the model-facing interface to model strengths.

### 4. Personal / local synthesis

The local CyberMnema notes add two practical hypotheses:

- Some behavior, such as avoiding verbose comments or generic AI style, is hard to reverse with one negative instruction because it fights pretraining and alignment priors.
- Prompt engineering, memory/context design, and learning are connected by an escalation ladder: prompt first, then context/schema/validator, then eval data, then activation/adapters/fine-tuning when the same failure recurs.

## Findings by Source Type

This table answers the practical question: which findings are from research, which are from Dayfold, and where they overlap?

| Finding | Literature / provider support | Dayfold / local support | Evidence status |
|---|---|---|---|
| Few-shot beats prose for format and local behavior | ICL literature; provider docs recommend examples | Planner few-shots, pattern-chat examples, field add/drop history | Strong |
| Schema is both structure and prompt | OpenAI constrained decoding; Gemini schema descriptions; Schema Key Wording paper | `schema_overrides`, schema realignment commits | Strong |
| `description` text can guide semantics | Gemini docs directly say descriptions guide model; OpenAI examples place descriptions in schema | Dayfold `schema_descriptions.yaml` and `060dc548f` design | Strong production/provider; paper evidence is currently stronger for key names than descriptions |
| Field order can influence output | Gemini says structured output order follows schema key order | Dayfold `style_name` reorder, cover analysis fields before final decision | Medium-to-strong; needs controlled eval for causal size |
| Reasoning fields are a practical prompt pattern | CoT / Least-to-Most / OpenAI structured examples | `thinking`, `analysis_*`, `global_reasoning` fields | Strong as pattern; medium as causal claim |
| Question-driven reasoning is better than generic CoT | Least-to-Most and ReAct support decomposition | Pages enhancer and pattern chat encode domain-specific questions | Strong |
| Context routing constrains prompt effectiveness | Provider prompt-chaining/context docs | `context_filter`, `l:` binding, ref image injection/removal | Strong production evidence, but this is a boundary condition rather than a PE core pattern |
| Self-check alone is not enforcement | Self-Refine and self-correction literature; eval docs | Dayfold bottom-line constraints still need validators/tests | Strong |
| Prompt behavior is model-family-specific | OpenAI reasoning docs; DeepSeek-R1 guidance; provider differences | Dayfold prompt/model-target tuning and product-manager prompt expertise | Strong production observation; needs model-specific eval matrix |
| Visible markers can leak | General prompt/data contamination intuition | `"[封面]"` leakage fix | Strong Dayfold evidence, narrow scope |
| Semantic labels beat brittle indices | Weak direct literature | Pseudo-name page refs replacing numeric indices | Medium; production-specific but plausible |
| Hard rules should migrate to validators | Provider eval/structured-output docs; self-correction limits | Dayfold validator-oriented fixes and runtime error prevention | Strong |

## Findings Record

Current findings worth carrying into later research or blog writing:

| Finding | Main evidence | Why it matters |
|---|---|---|
| Prompt engineering is shifting from wording to interface design | Anthropic/OpenAI/Gemini docs; Dayfold node-level prompts | The production unit is a node contract: prompt, schema, context, model, validator, and eval case |
| Few-shot examples are stronger than prose instructions for format and field behavior | In-context learning literature; Dayfold planner field add/drop history | Examples must be versioned with schema; obsolete examples can keep obsolete behavior alive |
| JSON Schema has two effects: constrained decoding and semantic prompting | OpenAI Structured Outputs; JSONSchemaBench; Schema Key Wording paper; Dayfold `schema_overrides` | Schema can both restrict output shape and bias which valid value the model chooses |
| Schema descriptions are configurable prompt text, not just code comments | Dayfold `060dc548f` and repeated schema realignment commits | Moving Pydantic descriptions into YAML gives prompt owners a safe behavior-tuning surface |
| Field order and intermediate fields are prompt controls | Gemini structured output docs; Dayfold `style_name` reorder and cover `analysis_*` fields | Reordering fields can change model behavior without changing global prompt wording |
| `thinking` / `analysis_*` fields are schema-level CoT | Dayfold pattern-chat, pages enhancer, cover design prompts | A reasoning step becomes part of the output contract, often stronger than "think carefully" |
| Question-driven reasoning is more useful than generic CoT | CoT / Least-to-Most literature; Dayfold highlight-page design | Domain-specific questions give the model inspectable reasoning targets |
| Context routing is a PE boundary condition | Anthropic context engineering; Dayfold `l:` binding, `context_filter`, ref image injection | Model behavior changes when visible context changes, but the control layer belongs mainly to context engineering / orchestration |
| Visible control markers can leak into generated artifacts | Dayfold cover marker leakage fix `e9c467278` | Control metadata should be structured, not placed in natural-language fields meant for generation |
| LLM-facing references should be semantic, not brittle indices | Dayfold pseudo-name page refs `6c6f3fab8` | The interface should match model strengths; avoid arithmetic/index reasoning when labels work better |
| Hard rules should move out of prompt | Generation-verification gap literature; Dayfold validator-oriented fixes | Prompt can raise probability; validators/hooks/review passes provide enforcement |
| Self-review needs an external signal when correctness matters | Self-Refine; LLM self-correction limitation papers; provider eval guidance | Dayfold self-check prompts plus need for validators/regression cases | Review prompts are useful, but not equivalent to deterministic checking |
| Prompt portability is limited across models | OpenAI reasoning docs; DeepSeek-R1 guidance; Dayfold model switches | Switching models often requires prompt adjustment to preserve product behavior |
| Prompt serialization is part of PE | Provider docs emphasize clear structure; ICL format sensitivity | Dayfold tuple-repr cleanup and formatter profiles | Machine-readable to code is not automatically model-readable |
| Prompt changes need eval cases | OpenAI Evals and model optimization docs; APO survey | Dayfold incident-driven prompt history but limited formal evals | Without golden cases, prompt tuning remains anecdotal |

## Positioning

The existing tracks ask adjacent questions:

| Track | Core question | Main control surface |
|---|---|---|
| Memory | What information persists across sessions? | External store, retrieval policy, memory update policy |
| Context | What information enters the current model window? | Context assembly, filtering, compaction, ordering |
| Prompt Engineering | Which input-side patterns steer behavior for the same task? | Instructions, examples, schemas, delimiters, prompt chains |
| Learning | What changes below the prompt? | Activation steering, adapters, fine-tuning, preference optimization |

Prompt engineering sits between Context and Learning:

```text
Prompt patterns
  -> context / memory placement
  -> schema / tool / validator enforcement
  -> eval and feedback data
  -> activation / adapter / weight-level learning
```

The practical boundary is: prompt engineering is cheap and fast, but it only changes the immediate conditional distribution. It does not create durable internal preferences, hard logical guarantees, or deterministic validation.

## Current Provider Guidance

The major provider docs converge on a more engineering-oriented view of prompting.

Anthropic's current Claude prompt engineering docs say to define success criteria and empirical tests before tuning prompts. Their best-practice guide emphasizes examples, XML-style segmentation, role prompting, long-context ordering, output control, and prompt chaining. It also notes that positive examples for the desired concise behavior tend to work better than only telling the model what not to do.

OpenAI's current API docs expose prompt versioning and templating as product primitives, explicitly linking prompt versions with evals. Their Structured Outputs docs frame schema adherence as a stronger alternative to plain JSON mode, and the model optimization guide places evals, prompt engineering, and fine-tuning in a repeated feedback loop. This is used here as provider-side evidence that prompt work is now treated as an evaluated interface, not a one-off text trick.

Google's Gemini docs make the same pattern explicit: clear instructions help, but few-shot examples are recommended for regulating format, phrasing, scope, and general response patterns; too many examples can cause overfitting. Gemini's structured output mode also treats JSON Schema descriptions and property order as part of the model-visible control interface. This supports the Dayfold finding that schema and examples are often stronger tuning knobs than global prose prompts.

Structured outputs also split into two different mechanisms:

1. **Constrained decoding**: the decoder masks tokens that would violate the JSON Schema, so the model can only emit structurally valid continuations.
2. **Schema-as-prompt**: field names, descriptions, enum labels, and property order are model-visible instructions that change the raw token distribution before the mask is applied.

This distinction matters. Constrained decoding explains why JSON is valid. It does not explain why one valid value is preferred over another. The semantic preference comes from the model reading the schema interface.

The implication: current production prompt engineering is closer to interface design plus evaluation than to one-off copywriting.

## Taxonomy of Prompt Control Patterns

| Pattern | Controls best | Why it works | Common failure | Better layer when it fails |
|---|---|---|---|---|
| Direct instruction | Local task intent, simple constraints | Natural language instruction following | Low salience under long context; weak against priors | Move to examples, schema, or validator |
| Message placement | Priority and salience | Earlier/higher-priority text is often weighted more | No absolute hierarchy; examples and recent context can override | Instruction hierarchy training, tool contracts, external checks |
| Few-shot examples | Format, tone, field presence, pattern selection | Pattern induction and distributional conformity | Format lock-in; missing fields if examples omit them; overfitting with too many examples | Golden cases, schema, evals, fine-tuning |
| Positive and negative examples | Boundary definition | Shows both the target and the rejection boundary | Bad negatives can teach the wrong pattern | Review rubric, classifier, DPO-style preference data |
| Constrained structured outputs | JSON validity, required fields, enum membership | Decoder masks schema-invalid continuations | Guarantees structure, not semantic correctness | Business validator, retry, review pass |
| Schema descriptions | Field-level semantic control | Places instruction exactly beside output slot | Ensures shape more than truth | Runtime validation, typed tools, downstream checks |
| Field order / intermediate fields | Reasoning path and decision sequence | The model fills fields in schema order; intermediate slots force decomposition | Can leak unnecessary reasoning or bloat output | Hidden reasoning, separate classifier, tool pipeline |
| `thinking` / analysis fields in schema | Local reasoning before final fields | Forces the model to materialize task-specific interpretation before generating dependent fields | May expose reasoning or become verbose; still self-generated | Private intermediate fields, hidden reasoning, validator |
| Delimiters / XML / Markdown sections | Context separation | Reduces ambiguity between instruction, examples, context, and user input | Tags do not create hard isolation | Data model separation, tool inputs, context filters |
| Question-driven reasoning | Specific analysis dimensions | Converts vague "think step by step" into inspectable subquestions | Still self-generated and self-verified | External reviewer, checklist, eval grader |
| Prompt chaining | Multi-step pipelines | Intermediate outputs can be logged, inspected, branched, or validated | More latency and orchestration cost | Workflow engine, state machine, typed ports |
| Role / persona | Domain prior activation, tone | Activates relevant training distribution | Generic personas are unpredictable; can hurt performance | Domain examples, vertical datasets, adapters |
| Anti-style / anti-refusal constraints | Suppress default aligned style or refusal tendency | Directly counters common model priors | Negative instruction alone is weak | Positive examples, product policy layer, fine-tuning |
| Multimodal reference labeling | Image role disambiguation | Tells model which image is style, action, character, or content | References still entangle when roles are implicit | Structured asset metadata and per-role context assembly |

## Prompt Technique Families

This section is the reusable technique index. The important unit is not "a good prompt", but a control pattern with a mechanism, target behavior, failure mode, and escalation path.

### Direct Instructions

Direct instructions are still the cheapest first step. They work best when the target behavior is local, simple, and aligned with the model's default behavior:

- "Return JSON only."
- "Use concise wording."
- "Do not ask a clarification question."
- "Preserve the user's dialogue exactly."

They are weaker when the rule must hold across a long artifact, when it is phrased negatively, or when it conflicts with a strong model prior. A rule like "do not write verbose comments" has to survive many local generation decisions; each new function or paragraph gives the model another chance to fall back into the training distribution where explanatory comments are common.

Practical guidance:

- Use direct instructions for preferences and low-cost constraints.
- Move repeated local failures into examples or schema descriptions.
- Move high-cost global failures into linters, validators, tests, or review passes.

### Placement, Priority, and Delimiters

System placement, early placement, and visible sectioning increase salience, but they do not create a deterministic hierarchy. This is the main lesson from instruction hierarchy work: models need explicit hierarchy training to reliably distinguish privileged instructions from untrusted content.

Delimiters such as XML tags, Markdown headings, or JSON blocks are useful because they reduce ambiguity:

```text
<instruction>what to do</instruction>
<context>what to use as data</context>
<output_format>what to emit</output_format>
```

The delimiter is not a security boundary. It is a readability and attention boundary. If the content inside `<context>` contains prompt-like text, the model still sees those tokens. For product security or correctness, delimiters should be paired with message roles, tool contracts, validators, and prompt-injection evals.

### Few-Shot and Counterexamples

Few-shot examples are one of the strongest prompt-level controls because they define an immediate local distribution. They communicate:

- expected output fields
- field order
- style and density
- label space
- task boundary
- what counts as a valid transformation

The production risk is lock-in. If a field is removed from the schema but still appears in examples, the model may continue to produce or reason around it. If all examples are story-like, the planner may force non-story requests into the story route. If examples omit an edge case, the model may treat that edge case as out-of-distribution.

Good few-shot practice:

- Version examples with schema.
- Add and remove fields symmetrically.
- Include boundary cases, not just ideal cases.
- Prefer positive examples for desired style, and use negative examples only when the boundary is genuinely ambiguous.
- Keep examples close to the node or field they control.

Dayfold's planner few-shots are a good production example: they encode not only "what output looks like", but also binding policy such as when to use `input.reference_assets`, when to use `l:` literal binding, and how to route `ref_pool` through downstream nodes.

### Schema-Layer Prompt Engineering

Structured output schemas add a field-level prompt channel. The schema is not just a parser contract. For model providers that expose structured outputs, the schema is part of the generation interface, and the model sees names, descriptions, enum labels, required fields, object shape, and often property order.

This creates three layers:

1. **Shape control**: required fields, arrays, enums, type constraints.
2. **Local semantic control**: field names and descriptions tell the model what each slot means.
3. **Reasoning path control**: field order and intermediate fields can force earlier decisions to condition later fields.

Dayfold's `schema_overrides` design makes this explicit. The code-level Pydantic model owns the application contract, while YAML overrides own the model-facing field descriptions. This matters because prompt owners can tune the LLM-visible instruction without changing the Python type definition.

Important nuance:

- Constrained decoding can guarantee that the output conforms to the schema grammar.
- It cannot guarantee that a string is truthful, that a boolean decision is semantically correct, or that a visual description is good.
- The schema text biases which valid output the model chooses.

So schema is both a guardrail and a prompt. It is stronger than a global instruction for local field behavior because the instruction is placed exactly beside the slot being generated.

### Constrained Decoding

The useful mental model is:

```text
raw_logits = model(prompt + visible_schema + generated_prefix)
valid_tokens = grammar_mask(schema, generated_prefix)
next_token = sample(raw_logits restricted to valid_tokens)
```

The constrained decoder filters out schema-invalid continuations. Field names and descriptions influence the raw logits before filtering.

Example:

```json
{
  "need_cover": {
    "type": "boolean",
    "description": "Only true when the story has at least four pages and page one is not already acting as a cover."
  }
}
```

At the boolean value position, the decoder may only allow `true` or `false`. The description still affects which of those two valid tokens is more likely. For open string fields, constrained decoding mostly ensures JSON validity; the description does most of the semantic steering.

This explains why schema edits can sometimes outperform prompt edits. The schema is closer to the decision site.

### Schema-Level Thinking Fields

Fields such as `thinking`, `analysis_story_length`, `analysis_page1_redundancy`, and `global_reasoning` are schema-level reasoning fields. They differ from a generic prose instruction like "think step by step" in three ways:

1. They are required by the output contract.
2. They are placed before dependent fields.
3. They are domain-specific rather than generic.

Dayfold's cover decision schema is a clear example: the model first fills several analysis fields, then fills `need_cover` with a description that references those earlier checks. The output contract encodes a decision procedure:

```text
analysis_story_length
analysis_title_extract
analysis_page1_redundancy
analysis_user_intent
analysis_content_type
need_cover
cover_page
```

This does not make the decision deterministic. The analysis fields are still generated by the model. But it often improves adherence because later fields condition on earlier explicit state. It also makes failures easier to inspect: if `need_cover` is wrong, one can see which analysis field drifted.

The product-design question is whether the reasoning should be exposed. If the field is only for downstream control, it should be hidden from end users and possibly stripped from persisted user-facing artifacts.

### Question-Driven Reasoning

Question-driven reasoning is a more practical variant of CoT. Instead of asking the model to "think carefully", ask it to answer domain questions that directly control the output.

For Dayfold pages enhancement, useful questions are:

- What is the core intent of this story?
- Which elements are necessary and cannot be stylized away?
- Which page is the highlight page?
- What does every other page do to make the highlight page work?
- What is the style singularity: what disappears if we switch to another style?

This is better than generic CoT because each question maps to a production invariant. It also creates reviewable intermediate artifacts. A human or eval grader can inspect whether the model identified the right necessary elements or highlight page.

Least-to-Most prompting supports the same principle from the research side: decompose hard tasks into simpler subproblems, then solve in sequence. ReAct adds another production-relevant extension: alternate reasoning with action/tool observations rather than keeping everything in one hidden chain.

### Prompt Chaining and Workflow Nodes

Prompt chaining is useful when one prompt is trying to do too many things. Splitting a workflow into nodes creates typed intermediate products:

```text
planner -> story_writer -> pages_enhancer -> char_ref_render -> image_render
```

Each node can have:

- a prompt
- a schema
- a context filter
- a model target
- validation rules
- regression cases

This is the strongest production framing: prompt engineering is node-interface design. The prompt is only one component of the node contract.

The cost is latency, orchestration complexity, and intermediate error propagation. The benefit is that each step becomes observable and testable.

### Context Routing as a Boundary Condition

Context selection is not a prompt-writing pattern in the narrow sense. It belongs mainly to context engineering and workflow orchestration. It is included here only because it is a major confounder for prompt evaluation: the same prompt can appear to improve or fail simply because the model saw different inputs.

If irrelevant context is visible, the model may follow the wrong local pattern. If relevant images or summaries are hidden, no prompt wording can recover information the model cannot see.

Dayfold examples:

- `context_filter` limits which messages each capability sees.
- `intent` was bound directly to `input.user_text` to avoid planner rewrite loss.
- `l:` literal binding is used only when the planner has a specific reason to rewrite a task input.
- Reference images were injected into nodes that needed multimodal visibility, then filtered where they polluted the task.

So this should not be framed as "context routing is PE." A cleaner framing is: prompt engineering experiments must control for context routing, and production prompt systems often need context-routing fixes before wording fixes are meaningful.

### Multimodal Reference Role Disambiguation

Multimodal prompts need role labels because images can influence more than intended. A style reference may alter character identity; an action reference may alter style; a character reference may be treated as a scene reference.

Prompt text helps:

- "This is a style reference, not a character identity reference."
- "Use the action pose but keep the current style."
- "This image is the current page to edit."

But product systems should encode roles structurally:

- asset type
- label
- description
- allowed downstream consumers
- per-task reference pool

Dayfold's move toward `ImageRef` labels and reference pools is part of this pattern.

### Self-Check, Review Passes, and Validators

Self-check prompts can catch obvious failures, especially when the checklist is explicit and local. They are weaker when the model has no external signal. A model can often recognize a violation when asked separately, but fail to avoid it during generation.

Use this escalation rule:

| Requirement | Good control layer |
|---|---|
| "Prefer concise style" | Prompt + examples |
| "Return valid JSON" | Structured output |
| "No extra field" | Schema / parser |
| "Dialogue text must be unchanged" | Prompt + validator diff |
| "No title prefix leaks into image text" | Prompt + sanitizer + regression case |
| "Every image task has matching TTS" | Planner validator / runtime check |

The more unacceptable a single violation is, the less it belongs only in prompt text.

### Anti-Style and Anti-Refusal Prompts

Negative constraints such as "do not sound like AI" or "do not refuse" are usually weak by themselves. They name the unwanted basin, but they do not provide a replacement distribution.

Better controls:

- positive examples of the desired style
- forbidden phrase lists for machine-checkable patterns
- post-generation lint/rewrite passes
- route-specific policy text
- preference data or fine-tuning when the behavior is product-wide

Dayfold's "说人话" pattern-chat prompts are stronger than "do not be formal" because they define a replacement voice with examples, length limits, and forbidden structures.

### Model-Specific Prompt Profiles

Prompt engineering is often discussed as if a prompt is a portable artifact. In production, this is only partially true. The more realistic unit is:

```text
prompt behavior = prompt/profile/schema/context/eval x model family
```

When the model changes, the same prompt can fail in subtle ways:

- a reasoning model may ignore generic CoT scaffolding that helped a non-reasoning model
- a model may prefer shorter or longer instructions
- examples may help one model and over-constrain another
- JSON schema support may differ in strictness, latency, and supported keywords
- system-vs-user instruction priority may differ
- default tone, refusal style, verbosity, and "AI-ish" writing style may differ
- multimodal reference binding can differ across vision-capable models

This matches Dayfold production experience: switching model targets often requires retuning prompts to preserve the same product behavior. The knowledge is real but currently fragile because it lives in the heads of prompt-tuning product managers. It is a form of tacit model-specific UX knowledge.

This suggests a missing production artifact: a **model prompt profile**.

Possible fields:

| Field | Purpose |
|---|---|
| `model_family` | OpenAI reasoning, Gemini, Claude, DeepSeek-R1, image model, etc. |
| `instruction_style` | Short objective, XML sections, checklist, examples-first, schema-first |
| `reasoning_guidance` | Avoid explicit CoT, use question fields, use `<think>` prefix only when needed, etc. |
| `few_shot_policy` | When examples help, when they overfit, max example count |
| `schema_policy` | Supported schema subset, description sensitivity, property-order behavior, strictness |
| `tone_compensation` | Known default style and counter-style examples |
| `failure_patterns` | Repeated quirks observed in production |
| `eval_cases` | Golden cases used before adopting or switching to this model |

The long-term goal is to move model-specific prompt taste from individual memory into versioned profiles, regression cases, and migration notes.

### External Experience on Model-Specific Prompt Tuning

The newest external scan supports the user's production observation: prompt tuning knowledge is increasingly model-family-specific. The general techniques still matter, but each provider now publishes model-specific caveats that can contradict older prompt folklore.

#### Relatively general practices

The practices with the broadest support are not magic phrases. They are interface-design habits:

- Define the task, context, constraints, success criteria, and output contract explicitly.
- Use examples when format, tone, label space, routing, or boundary behavior matters.
- Use delimiters or structured sections to separate instructions, context, examples, and user input.
- Prefer structured outputs, tool schemas, and validators when shape or machine consumption matters.
- Keep prompt changes tied to eval cases; do not rely on one successful sample.
- Treat long-context placement as a variable to test, not as a universal law.
- Treat model upgrades as migrations: run the same regression set before assuming prompt parity.

These practices are supported by provider docs, the Prompt Report, ICL literature, DSPy-style prompt optimization, and Dayfold production history.

#### Model-family-specific practices found so far

| Model family / source | Model-specific guidance | Why it matters |
|---|---|---|
| OpenAI reasoning models | Use straightforward prompts; avoid explicit "think step by step" unless needed; try zero-shot first, then few-shot for more complex output requirements; use developer messages and reasoning-context handling in Responses API | Generic CoT and example-heavy prompts can be redundant or harmful on native reasoning models |
| OpenAI o3/o4-mini tool calling | Put workflow order, tool-use boundaries, and argument constraints in developer prompts and function descriptions; few-shot examples can help tool argument construction even if they help pure reasoning less | Tool schema descriptions are model-visible control surfaces, close to Dayfold's schema-as-prompt finding |
| OpenAI GPT-4.1 / GPT-style non-reasoning models | CoT-style planning can still help; long-context prompts may benefit from instructions at both beginning and end; existing prompts for other models may fail because GPT-4.1 follows instructions more literally and infers less | "Reasoning model prompting" and "GPT model prompting" should not be collapsed into one rule |
| OpenAI GPT-5.1 | Migration guidance emphasizes persistence/completeness, verbosity/output-format tuning, and conflict checking; model-specific prompting is framed as iterative production work | Supports treating a model switch as a prompt migration even inside one provider family |
| Anthropic Claude 4.x | Claude docs emphasize clear/direct prompts, examples, XML structure, long-context ordering, effort/thinking controls, and migration tuning; latest Claude guidance also notes that positive examples for concision beat negative "do not be verbose" instructions | Matches Dayfold's observation that replacement distributions beat negative prohibitions |
| Anthropic Claude 4.x migration | Tune verbosity, proactiveness, effort, tool-use triggering, and anti-laziness prompts; prompts that compensated for older model weaknesses may overcorrect newer models | Strong evidence that prompt profiles should have per-model migration notes |
| Google Gemini | Gemini docs recommend few-shot examples for formatting/phrasing/scope, warn too many examples can overfit, expose `thinkingBudget` / `thinkingLevel`, and document structured-output property order and schema descriptions | Strong support for examples, reasoning-budget parameters, property order, and schema descriptions as PE controls |
| Google Gemini 3 | Google recommends keeping temperature at the default 1.0; lowering it may cause unexpected behavior in complex reasoning tasks | Sampling parameters are not universally transferable prompt-adjacent settings |
| DeepSeek-R1 | Official repo recommends temperature 0.5-0.7, 0.6 preferred; avoid system prompts; put all instructions in the user prompt; use multiple tests and averaging; optionally force `<think>` if the model bypasses its thinking pattern | Very strong example that some model families require unusual prompt placement and decoding habits |

The important blog-level claim is not "Claude likes XML" or "R1 dislikes system prompts" as timeless facts. The safer claim is:

> Prompt techniques have a model-family dialect. A production prompt should be versioned against the model, schema, decoding parameters, and eval set it was tuned with.

#### Prompt portability and migration research

PromptBridge directly studies the user's production problem: prompts optimized for one model often degrade when reused on another model. It names this "model drifting" and proposes a training-free cross-model prompt transfer framework based on small calibration sets, reflective prompt evolution, and quantitative evaluation.

This is important because it converts tacit PM prompt-tuning knowledge into a research-shaped problem:

- Source prompt: what currently works for model A.
- Target model: the new model family or snapshot.
- Alignment set: a small set of representative production cases.
- Metric: behavior parity, semantic correctness, tool-call validity, schema-field quality, style compliance.
- Adaptation: a revised prompt/profile/schema tuned for model B.

DSPy points in the same direction from a different angle. It argues that LLM systems should be expressed as declarative modules/signatures and optimized against metrics, rather than maintained as hand-written prompt strings. This does not eliminate product judgment, but it gives a path for moving local prompt taste into an eval-driven compiler/optimizer loop.

#### Relation to Dayfold

Dayfold already has the raw ingredients for this migration discipline:

- prompt profiles in YAML
- schema descriptions and `schema_overrides`
- prompt files per node
- structured generation via schemas
- production commits that encode before/after prompt behavior
- model switching experience held by PMs and prompt owners

The missing artifact is not another global prompt guide. It is a lightweight model-specific prompt profile plus regression cases:

```yaml
model_family: openai_reasoning
model_snapshot: example-model-id
prompt_style:
  instruction_density: low
  reasoning_guidance: avoid_generic_cot
  examples_policy: use_for_tool_arguments_and_format_only
schema_policy:
  description_sensitivity: high
  field_order_policy: analysis_before_decision
known_failures:
  - promises_future_tool_call_without_calling
  - over_literal_instruction_following
eval_cases:
  - cover_short_story_no_cover
  - style_name_two_to_four_chars
```

This profile should be treated as an operational artifact. Each model migration should answer:

1. Which existing prompt assumptions changed?
2. Which failures appeared only on the new model?
3. Which fixes were prompt text, schema description, examples, decoding parameters, or validators?
4. Which fixes should become regression cases?

## Mechanism-Level Explanation

The most useful mechanism model is: LLMs do not merely "read instructions"; they continue a distribution shaped by all visible tokens.

Few-shot examples are strong because in-context learning can exploit pattern-copying circuits. Olsson et al. describe induction heads as attention heads that complete patterns of the form `[A][B] ... [A] -> [B]`, and propose them as a mechanistic source of in-context learning. This explains why stable examples, symbolic mini-DSLs, and repeated output formats often outperform prose instructions.

Min et al. show that demonstrations work partly by supplying label space, input distribution, and sequence format, not just correct labels. This matches production observations: examples can make a field appear, but can also keep obsolete fields alive after the instruction or schema changes.

Wei et al. show that larger models can use in-context exemplars to override semantic priors, while instruction tuning strengthens semantic priors even more than input-label mapping ability. This helps explain the tension between explicit examples and pretrained/alignment defaults.

Wallace et al.'s instruction hierarchy work is important because it states the core weakness directly: current LLMs can treat system prompts and untrusted text as similar-priority instructions unless trained otherwise. From the application side, this means message placement is a salience tool, not a hard permission model.

Kung and Peng's instruction-tuning study suggests another limit: models can gain apparent instruction-following ability from superficial task patterns, output formats, and guessing. That supports a production rule: if a requirement is critical, do not rely on the model's self-reported understanding of a prose rule.

Structured outputs add a second mechanism. A constrained decoder can guarantee that the generated continuation stays inside the JSON Schema grammar, but it still starts from the model's raw next-token probabilities. A useful mental model:

```text
raw_logits = model(prompt + schema names + schema descriptions + generated_prefix)
valid_tokens = grammar_mask(schema_structure, generated_prefix)
next_token = sample(raw_logits restricted to valid_tokens)
```

Schema descriptions affect `raw_logits`; constrained decoding affects `valid_tokens`. For a boolean field such as `need_cover`, the decoder may only allow `true` or `false`, but the schema description can shift which of those valid values is more likely. For an open string field such as `page_description`, the decoder only ensures that the value is a JSON string; the schema description still drives whether the string is generic, cinematic, concise, visual, or business-rule aware.

This is why schema edits can outperform global prompt edits: the instruction is placed exactly at the output slot where the model is deciding what to emit. Recent structured-generation work also supports this direction: JSONSchemaBench treats JSON Schema as the central object for constrained decoding, while "Schema Key Wording as an Instruction Channel" shows that schema key wording can change model behavior even under constrained decoding. The latter paper studies key wording rather than `description` text, so the strict evidence is strongest for schema key names; using field descriptions as a semantic control channel is supported by provider docs plus Dayfold production evidence.

Adding a `thinking`, `analysis_*`, or `global_reasoning` field is the same mechanism taken one step further. The point is not necessarily to expose chain-of-thought to the user. The point is to create an earlier structured field where the model must classify the situation, identify constraints, or choose a strategy before it fills later fields. Later fields then condition on that generated intermediate state. In production, this can be more reliable than writing "think carefully" in prose because the reasoning slot is part of the output contract.

## Prompt Ceiling

Several behaviors are hard to control by prompt alone.

| Failure mode | Symptom | Why prompt is weak | Preferred escalation |
|---|---|---|---|
| Long-context drift | Rule followed once, then forgotten later | Early instruction loses attention against recent local pattern | Dynamic reminders, context pruning, review pass |
| Style prior override | AI-ish copy, verbose comments, generic safety tone | Pretraining/alignment priors are stronger than one soft rule | Positive examples, lints, reviewers, fine-tuning |
| Range-wide negative constraints | "Never do X anywhere" fails in long output | Generation is local; constraint must survive many tokens | Parser/linter/validator over full artifact |
| Few-shot lock-in | Obsolete field keeps appearing | Examples define the distribution more strongly than prose | Update examples symmetrically with schema |
| Schema-semantic gap | JSON shape is valid but meaning is wrong | Schema enforces structure, not full task truth | Domain validator, rubric grader, human review |
| Generation-verification gap | Model can review a failure it did not avoid generating | Generation and checking call different capabilities | Separate review call with checklist or tool feedback |
| Multimodal reference entanglement | Style image affects character/action, or action image affects style | Images are not naturally typed by role | Structured image roles and per-node filtering |
| Over-refusal / under-action | Model refuses or hedges in product workflow | Alignment prior favors caution | Product policy, examples, route-specific model tuning |

The engineering rule is simple: keep preferences in prompts; move red lines into enforcement.

## Dayfold Production Case Bank

Dayfold is useful because it is not a research benchmark. It is a user-facing multimodal product where prompt changes are driven by actual quality failures, cost constraints, node routing, and schema contracts.

| Case | Production pattern | Behavior controlled | Research implication |
|---|---|---|---|
| YAML schema description overrides | `schema_overrides` replace LLM-visible JSON Schema descriptions without changing Pydantic field definitions | Field semantics and nested field behavior | Schema is prompt engineering at field granularity; configurable schema text lets prompt owners tune behavior without changing code-owned Pydantic models |
| Dot-path overrides | Paths such as `pages.page_description` and `characters.description` target nested fields | Local control without global prompt bloat | Prompt scope should match behavior scope |
| Cover decision analysis fields | `analysis_story_length`, `analysis_page1_redundancy`, and related fields precede `need_cover` | Forces a decision path before final boolean | Schema order can encode structured reasoning |
| `thinking` / `global_reasoning` fields | Pattern chat and pages enhancer use explicit thinking/global reasoning before user-facing or downstream fields | Anchors later output in a prior interpretation of intent, constraints, and strategy | Structured thinking fields are a schema-level CoT mechanism, stronger than a free-form "think step by step" instruction |
| `l:` literal binding | Planner passes focused literal text instead of raw `input.user_text` to every node | Reduces context pollution and mixed-intent leakage | Prompt reliability depends on input routing, not only wording |
| Planner few-shots | Planning examples define node choice and binding style | Controls workflow shape | Examples are operational policy, not decoration |
| Prompt bias fix | Replacing story-biased wording with "most relevant few-shot example" | Prevents non-story requests from being forced into story plans | Example selection can bias task routing |
| Bottom-line constraints | Pages enhancer uses explicit invalid-output clauses | Protects semantic invariants like page count and unchanged dialogue | Soft prompt red lines should become validators when product-critical |
| Positive/negative visual examples | Concrete good/bad page description pairs define specificity threshold | Controls descriptive density and visual quality | Boundary examples outperform vague adjectives |
| Reference image role text | "Action reference does not control style" style instructions | Reduces multimodal role contamination | Asset roles should be represented structurally upstream |
| Resource graph and `output_summary` | Planner prompt documents downstream dependencies and insight handoff | Keeps multi-node pipeline coherent | Prompt engineering becomes workflow interface design |

This case bank is expanded below with concrete before/after examples extracted from Dayfold commit history. The central observation is already clear: Dayfold's strongest prompt engineering is not a single prompt. It is a node-level system of prompts, schemas, examples, context filters, model routing, and validators.

### Git History Signals

Reading the Dayfold prompt history adds a stronger production signal than only reading the final prompt files. The history shows which prompt changes were made to fix concrete output failures.

| Signal | Representative commits | What changed | Prompt-engineering lesson |
|---|---|---|---|
| Schema descriptions became configurable prompt assets | `060dc548f` | Added YAML `schema_overrides` with dot-path field descriptions applied before structured generation | Field descriptions are not just code documentation; they are production-tuned prompt text |
| Schema descriptions were repeatedly re-aligned after prompt changes | `1975eb23e`, `e9c467278`, `f74c2a290` | Updated pages enhancer, cover design, and story editor schema descriptions to match new prompt logic | Prompt and schema must be versioned together; schema drift creates behavior drift |
| Field order and instruction placement were treated as tuning knobs | `fdbe8526d` | Moved `style_name` earlier in the JSON schema and moved output notes before the JSON block | Local ordering changes can change output behavior before any model or prompt wording change |
| Character-limit constraints required stronger wording in both prompt and schema | `8428d2b67`, `f4ca91521`, `4ca15fc4a` | Tightened `style_name` from preference language to explicit 2-4 character rules, including examples of invalid length | Soft length rules often need concrete counterexamples and schema-level repetition |
| Pages enhancer moved from uniform enhancement to highlight-page-driven reasoning | `56cb9832d`, `1975eb23e` | Rewrote the prompt around core intent, necessary elements, highlight page, visual strategy, and self-check; then aligned schema fields | Useful CoT is domain-question-driven, not generic "think step by step" |
| Context visibility was tuned as a prompt-control variable | `9e4dd304f`, `75bf13408`, `e5f91a849` | Injected reference images into pages enhancer, later bound raw user input directly, and removed irrelevant conversation context | Prompt quality depends on exactly what the node sees, not just the words in the template |
| Visible markers can leak into generated artifacts | `e9c467278` | Removed string markers like `"[封面]"` that leaked into image text; replaced with structured `StoryPage.is_cover` metadata | If a control marker is not meant for output, keep it out of model-visible natural-language fields |
| LLM-facing references were changed from numeric indices to semantic labels | `6c6f3fab8` | Replaced 0/1-based page indices with labels like `"第N页当前图 - {伪名}"` | Match the model-facing reference format to the model's strengths; avoid brittle arithmetic/index reasoning |
| Prompt serialization format was cleaned up for model readability | `5696e2fbc` | Replaced Python tuple reprs with clean bullet lists and joined character names | Prompt data serialization is part of PE; unreadable machine reprs waste tokens and create confusion |
| Full legacy descriptions were restored when compression hurt routing quality | `5696e2fbc` | Restored detailed `edit_from` criteria with examples because it drives edit-vs-regenerate routing | Compressing schema descriptions can remove decision boundaries the model needs |

Two meta-observations:

1. Prompt work in Dayfold is incident-driven. Commits mention concrete failures: missing cover title, leaked cover marker text, style-name length violations, index out-of-range story edits, reference images invisible to the editor, and degraded edit quality.
2. The repeated fix pattern is not "add more instruction." It is usually one of: move instruction closer to the field, change field order, repair visible context, replace fragile visible markers with structured metadata, or add concrete examples.

### Concrete Before/After Cases

These case cards are production-observational evidence, not controlled experiments. They are useful because each one connects a concrete product failure or fragility to a concrete prompt/schema/context/interface change.

#### Case 1: Schema Descriptions Became Configurable Prompt Assets

Evidence: `060dc548f`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/llm/llm_service.py`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/prompt/profiles/schema_descriptions.yaml`.

Before:

- Pydantic model descriptions were effectively code-owned.
- If prompt owners wanted to tune field semantics, they had to change Python model definitions or rely on more global prompt text.
- Nested fields such as `pages.page_description`, `characters.description`, or `cover_page.title` did not have a clean prompt-owner override surface.

After:

- `schema_overrides` were added to YAML prompt profiles.
- `LlmService.generate_structured` deep-copies the JSON Schema and applies dot-path description overrides before sending the schema to the structured-generation provider.
- Dot paths resolve through arrays, `$defs`, `$ref`, and `allOf`, so nested list-object fields can be tuned locally.
- Unit tests were added for top-level, nested-array, multiple-field, nonexistent-path, and no-mutation behavior.

Prompt-engineering finding:

Schema text became a configurable LLM-facing prompt surface. This is not merely documentation refactoring: the changed descriptions enter the effective schema payload used in structured generation.

Evidence strength:

Direct implementation evidence for "schema-as-prompt" in Dayfold. It does not prove effect size, but it proves the mechanism and explains why colleagues could see schema edits outperform global prompt edits.

#### Case 2: Pages Enhancer Moved From Uniform Enhancement to Highlight-Page Reasoning

Evidence: `56cb9832d`, `1975eb23e`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/prompt/profiles/capability.yaml`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/prompt/profiles/schema_descriptions.yaml`.

Before:

- The prompt framed the node as a general "comic visual director."
- It asked for per-page enhancement across many dimensions: composition, panels, lighting, material, text integration, visual subject, and style self-check.
- The risk was uniform enhancement: every page could become "more stylish" without a stronger story-level hierarchy.

After:

- The prompt identity changed to a "story gold digger" that first finds the story's unique emotional/core element.
- The workflow became question-driven: core intent, necessary elements, causal progression, highlight page, emotional mechanism, style singularity, style-fusion strategy, then per-page design.
- A `global_reasoning.narrative` structure was added before page-level outputs.
- Schema descriptions were then realigned so `enhanced_pages.sub_plan` covers narrative function, element protection, visual density/temperature/rhythm, and director decisions.

Prompt-engineering finding:

Useful reasoning prompting is domain-question-driven, not generic CoT. The prompt and schema jointly encode the questions a good visual director should answer before generating pages.

Evidence strength:

Strong production design evidence. It supports the pattern "structured reasoning questions beat vague think-step-by-step" but does not quantify output improvement without evals.

#### Case 3: Context Visibility Was Tuned as Part of Prompt Control

Evidence: `9e4dd304f`, `75bf13408`, `e5f91a849`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/workflow/nodes/pages_enhancer.py`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/prompt/profiles/capability.yaml`.

Before:

- Pages enhancer prompt quality could be confounded by what the node saw: conversation summaries, user input, system messages, reference images, and stale context.
- Reference images needed by pages enhancer were not consistently visible in the right typed form.
- Intent could be planner-rewritten as a literal, which contaminated downstream interpretation.

After:

- Pages enhancer explicitly received relevant `ref_images`, filtered to keep style/base/inspiration references and avoid character-ref contamination.
- Later, `intent` was bound directly to `input.user_text`, so nodes read the latest user message rather than a planner paraphrase.
- Pages enhancer context filtering was set to `none` because it did not benefit from conversation context; the node gets explicit variables instead.

Prompt-engineering finding:

When model behavior changes, first ask what the model can see. Some "prompt failures" are actually context-routing failures. This is not PE core, but it is a PE evaluation confounder.

Evidence strength:

Strong production evidence for context visibility as a boundary condition. It should not be over-claimed as a prompt-writing technique.

#### Case 4: Cover Design Replaced Visible Markers With Structured Metadata

Evidence: `e9c467278`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/workflow/schemas/cover_schemas.py`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/workflow/schemas/story_schemas.py`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/prompt/profiles/schema_descriptions.yaml`.

Before:

- The migration used string markers such as `sub_plan="1格|封面|..."` and `page_brief="[封面] {title}"` as downstream hints.
- The matching prompt rule was incomplete, so the marker leaked into panel descriptions and could be painted into images.
- The legacy title-rendering wrapper had also been dropped, so cover images could miss title text.

After:

- Cover title rendering was restored through a cover text rules template that wraps `title` and `page_description` for downstream image generation.
- `StoryPage.is_cover` was added as a structured code-side marker.
- `is_cover` is excluded from LLM-facing schema with `SkipJsonSchema`, and callers exclude it when constructing model-visible page data.
- `sub_plan` no longer carries `"封面"`, and `page_brief` no longer contains `"[封面]"`.

Prompt-engineering finding:

Control metadata should not be placed in natural-language channels that later become generation prompts. If a marker is not meant to appear in output, it belongs in structured metadata, not text.

Evidence strength:

Very strong narrow production evidence. It is a concrete leak/fix case and maps cleanly to a broader interface-design rule.

#### Case 5: `style_name` Needed Field Order, Prompt Placement, and Counterexamples

Evidence: `fdbe8526d`, `4ca15fc4a`, `/Users/linguanguo/dev/dayfold_webapp/services/langgraph_agent/nodes/prompts/style_extractor.txt`, `/Users/linguanguo/dev/dayfold_webapp/services/langgraph_agent/nodes/prompts/style_extractor_desc.json`, `/Users/linguanguo/dev/dayfold_webapp/services/langgraph_agent/schemas/custom_style_models.py`.

Before:

- `style_name` appeared after the long `style_overview` and other detailed fields.
- Output notes appeared after the JSON block.
- The length rule allowed 2-5 characters and expressed a preference for four characters.

After:

- `style_name` was moved earlier in the JSON schema, immediately after `thinking` and before the long descriptive fields.
- Output notes were moved before the JSON block so constraints are seen before generation.
- The rule was hardened to 2-4 characters, each Chinese character/digit/letter counted as one character.
- A concrete bad example was added: `"3D国漫潮玩"` has six characters and is explicitly forbidden.
- The same wording was aligned in prompt text and schema description.

Prompt-engineering finding:

Short local constraints may need all three layers: field order, prompt placement, and schema-level wording with counterexamples. The model is more likely to satisfy a compact field if it generates that field before writing a rich long-form explanation.

Evidence strength:

Strong production observation for field order and local constraint reinforcement. Causal size remains a hypothesis without evals.

#### Case 6: Story Editor Replaced Numeric Page Indices With Copyable Semantic Handles

Evidence: `6c6f3fab8`, `/Users/linguanguo/dev/dayfold_webapp/agent/docs/plans/2026-04-19-story-editor-pseudo-naming.md`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/workflow/nodes/story_editor.py`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/workflow/schemas/edit_schemas.py`.

Before:

- The editor LLM output integer `page_index`, `before_index`, and integer `remove_images` values.
- The model had to reason across 0-based and 1-based conventions.
- SLS-visible warning classes included out-of-range delete/edit and clamped add anchors.

After:

- LLM-facing page references became string labels such as `"第N页当前图 - alpha"`.
- The same label appears in prompt text and multimodal image labels, so the text and image channels share an identifier.
- The schema renamed integer fields to `page_ref`, `anchor_ref`, and string `remove_images`.
- Resolver code maps exact or fuzzy labels back to internal integer indices; unknown refs are dropped with a clearer warning.

Prompt-engineering finding:

When an LLM must refer to an existing object, give it a copyable handle instead of asking it to compute an index. Keep numeric indices inside deterministic code.

Evidence strength:

Strong production evidence because the commit names specific warning classes eliminated by the interface change. It is still observational, but the failure class and fix are tightly connected.

#### Case 7: Story Editor Restored Lost Decision Boundaries and Clean Serialization

Evidence: `5696e2fbc`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/prompt/profiles/capability.yaml`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/workflow/schemas/edit_schemas.py`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/workflow/nodes/story_editor.py`.

Before:

- `PageEdit.edit_from` had been compressed to one line: 1 means edit from original image, 0 means regenerate.
- User-uploaded reference images in edit turns were not visible to the story editor LLM.
- `editor_story_info.characters` was rendered as a Python tuple repr, and `characters_present` could appear as a Python list.

After:

- `edit_from` restored a detailed three-dimension decision rubric: character changes, visual/page-structure changes, and text-edit cases, with concrete examples for edit-from-image vs regenerate.
- `StoryEditorInput.ref_images` was added and injected multimodally when users attach images during editing.
- Character data is rendered as a clean bullet list, and `characters_present` is joined into a readable comma-separated list.

Prompt-engineering finding:

Compression can remove decision boundaries the model needs. Data serialization is also prompt engineering: a Python repr is technically complete but model-hostile.

Evidence strength:

Strong production evidence for schema-description richness, multimodal visibility, and serialization quality. It does not isolate which part had the largest effect.

#### Case 8: Planner Few-Shots Became Operational Policy

Evidence: `38fd5ae53`, `7ae513a04`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/prompt/profiles/planning.yaml`, `/Users/linguanguo/dev/dayfold_webapp/agent/src/agent/workflow/planning/planner_node.py`.

Before:

- Planner LLM could hallucinate off-template bindings on long-tail intents, such as binding incompatible fields into `image_render.ref_pool`.
- The result was validation-replan loops.
- Some required pipeline components, such as `bgm_design` on the first story round, could be skipped because the model treated them as optional.

After:

- Planning rules now state that input bindings for repeated fields such as `ref_pool`, `ref_images`, `characters`, and `character_specs` should reuse the exact structures seen in few-shot examples unless the scene clearly does not match.
- Validation failures are logged with run id, attempt, issue count, and error codes, making the prompt failure observable.
- `bgm_design_0` is promoted to an explicit first-round mandatory rule.

Prompt-engineering finding:

Planner examples are not decoration. They are operational policy for a workflow compiler. For DAG construction, "reuse the few-shot binding structure" can be more reliable than asking the model to reason freely about all ports.

Evidence strength:

Strong production observation for few-shot as policy. The logged validation retries also create a path for future monitoring without requiring a controlled eval.

#### Case 9: Pattern Chat Adjusted Prompt Behavior to Entry State

Evidence: `043010bac`, `/Users/linguanguo/dev/dayfold_webapp/services/langgraph_agent/nodes/prompts/pattern_chat_prompt.txt`, `/Users/linguanguo/dev/dayfold_webapp/services/langgraph_agent/nodes/execution/pattern_chat_conversation.py`, `/Users/linguanguo/dev/dayfold_webapp/services/langgraph_agent/schemas/pattern_chat_message.py`.

Before:

- External entry paths could auto-inject the first image message.
- The user had not seen the normal greeting or first question, but the model saw a first user message with an image.
- A normal slot-flow prompt could treat the state as if the user had already participated intentionally.

After:

- `ChatMessage.auto_injected` marks preset client messages.
- Prompt rendering detects an auto-injected image start.
- The prompt adds a special first-reply branch: treat the first image slot as completed, write a natural opening, acknowledge the image without asking for re-upload, and advance to the next slot or complete if there is only one slot.

Prompt-engineering finding:

Prompt behavior depends on interaction state, not only task text. A user-visible conversation contract can break when the same prompt is reused across different entry flows.

Evidence strength:

Strong product-flow evidence. This case is more UI/state prompt engineering than schema prompt engineering, but it supports the broader "prompt as interface" thesis.

## Dayfold Production Evolution

This section turns the commit table into a narrative. The goal is not to claim controlled causality from every commit. The goal is to identify production pressure that repeatedly pushed prompt work toward the same control layers.

### 1. From Prompt Text to Node Contract

Early prompt work can be described as "make the instruction better." The newer Dayfold prompt system is closer to a node contract:

```text
Capability node =
  model target
  system prompt
  prompt template
  context filter
  input bindings
  schema descriptions
  summary exchange
  downstream contract
  runtime validator / retry behavior
```

This is visible in `agent/src/agent/prompt/profiles/capability.yaml`: each `llm_id` defines a model target, a context filter, a system prompt or template, and sometimes a summary exchange. `agent/src/agent/prompt/profiles/schema_descriptions.yaml` separately controls the LLM-visible JSON Schema descriptions.

This architecture creates a useful separation:

- Code owns type shape and runtime behavior.
- Prompt profiles own model-facing text.
- Schemas sit between them as both type contract and prompt surface.
- Context filters and input bindings decide what the model can see.

That separation is the practical meaning of "prompt engineering as interface design."

### 2. Why `schema_overrides` Has Semantic Effect

The Dayfold implementation makes the mechanism concrete:

1. Pydantic models produce a JSON Schema with field descriptions.
2. The prompt profile loads `schema_overrides` from YAML.
3. Before `generate_structured`, `LlmService` deep-copies the schema and applies dot-path overrides.
4. Dot paths such as `pages.page_description` resolve through `properties`, arrays, `$defs`, and `allOf`.
5. The effective schema is sent to the provider's structured-generation API.

So `schema_overrides` are not comments. They replace text inside the schema payload that the model/provider receives.

The effect has two parts:

- **Decoder-side effect**: the provider's structured-output layer may constrain generation to schema-valid continuations.
- **Model-side semantic effect**: the schema names and descriptions are visible conditioning text, so they influence the model's raw probabilities before decoding constraints are applied.

This explains the colleague observation that tuning schema can sometimes outperform tuning the global prompt. A global instruction competes with all other visible context. A schema description is attached to the exact output slot where the model is deciding what to generate.

Important caveat: constrained decoding alone only explains structure. It cannot explain why the model chooses a better `need_cover` value, a more precise `page_description`, or a shorter `style_name`. Those semantic improvements come from the schema-as-prompt channel, model training around structured outputs, or both.

### 3. Cover Decision: Schema-Encoded Decision Procedure

The cover-design case is a strong Dayfold example because it uses a schema to encode a decision path:

- `analysis_story_length`
- `analysis_title_extract`
- `analysis_page1_redundancy`
- `analysis_user_intent`
- `analysis_content_type`
- `need_cover`
- `cover_page`

The schema descriptions define each analysis field and then define `need_cover` as a final decision based on those fields. This is a schema-level CoT pattern. It does not merely say "decide whether a cover is needed." It creates an ordered set of checks and requires the model to materialize them.

The production lesson is subtle:

- The reasoning fields are not valuable because they reveal hidden truth.
- They are valuable because they create state that later fields must condition on.
- They also make errors inspectable. A wrong final boolean can be traced to a wrong or ignored intermediate check.

### 4. Pages Enhancer: From Uniform Enhancement to Highlight-Page Reasoning

The pages enhancer moved from a generic "enhance every page" style prompt toward a story-director prompt:

- identify core intent
- identify necessary elements
- identify highlight page
- define emotional mechanism
- decode style singularity
- make every page serve the highlight page

This is the strongest local evidence for "question-driven reasoning beats generic CoT." The model is not asked to think in a vacuum. It is asked to answer questions that correspond to product quality:

- Did it preserve necessary story elements?
- Did it avoid making every page equally stylized?
- Did it understand why one page should visually explode?
- Did it adapt the style to the story rather than apply a generic filter?

The schema then mirrors the prompt through `global_reasoning`, `director_notes`, and `enhanced_pages.sub_plan`. This prompt/schema alignment is important. If the prompt asks for highlight-page reasoning but the schema has no place for it, the reasoning is more likely to be lost or compressed into a final field.

### 5. Planner: Few-Shot as Operational Policy

The planner prompt shows that few-shot examples are not merely illustrative. They are policy examples for a workflow compiler:

- which capability to call
- which fields to bind
- when to reuse `input.user_text`
- when to use `l:` literal binding
- how to route reference images
- how to preserve downstream dependencies

The planning prompt explicitly says to prefer input binding structures that appeared in few-shot examples. This is an explicit acknowledgment that examples are stronger than free-form reasoning for stable plan structure.

The local production risk is also clear: if few-shots are stale, the planner can keep obsolete binding patterns alive. This matches the ICL literature: examples convey format and distribution, not only task intent.

### 6. Context Visibility as an Evaluation Confounder

Several commits changed not the prompt wording, but what the node could see:

- reference images were injected where needed
- stale context was removed from pages enhancer
- raw user input was bound directly to capability intent

This supports a practical rule: when a model fails, ask "what did it actually see?" before rewriting prompt text.

Prompt tuning without context inspection can solve the wrong problem. If the relevant image is absent, more forceful wording will not help. If irrelevant prior context is visible, the model may follow a stale pattern even with a good instruction.

### 7. Model-Facing References: Labels Beat Indices

The story editor replaced numeric page indices with labels like `"第N页当前图 - {伪名}"`. This is a model-interface improvement rather than a deeper reasoning improvement.

The model is generally better at matching semantic labels copied from context than doing fragile index arithmetic across generated lists. The label also gives the user and logs a more inspectable reference. This is a narrow but useful production heuristic:

> When an LLM must refer to an existing object, give it a copyable semantic handle instead of asking it to compute an index.

### 8. Visible Markers Leak

The `"[封面]"` leakage fix is a concrete example of control metadata contaminating generation. If a control marker is placed inside natural-language content that later becomes an image prompt, the model may render or mention it.

The safer pattern is:

- use structured metadata for control flags
- keep user-facing or generation-facing text clean
- strip or map control metadata before downstream generation
- add regression cases for known leakage patterns

This is an important PE boundary: prompts can tell the model to ignore a marker, but the better design is to remove the marker from the text channel where it can leak.

### 9. Prompt Serialization Quality

Commit history also shows that model-readable serialization matters. Python tuple reprs, noisy objects, or compressed descriptions can harm behavior because the model is reading a messy serialization format, not the original data model.

Production rule:

- data serialization is prompt engineering
- labels should be human-readable
- lists should be explicit
- object fields should be stable
- avoid leaking implementation reprs unless the model is expected to reason about code-like data

This is an under-discussed but high-frequency production issue.

## Control-Layer Decision Table

| Requirement type | Start with | Escalate when | Next layer |
|---|---|---|---|
| Simple one-off instruction | Direct prompt | Same error repeats | Few-shot or targeted reminder |
| Stable output shape | Structured outputs / schema | Shape still invalid | Strict parser, retry, validator |
| Field-level semantic nuance | Schema description + few-shot | Field meaning drifts | Domain validator or rubric grader |
| Tone and style | Positive examples | Long outputs drift or default style returns | Review pass, preference data, fine-tuning |
| "Never do X" artifact rule | Prompt plus explicit checklist | A single violation is unacceptable | Lint, hook, static check |
| Multi-step reasoning | Question-driven intermediate fields | Intermediate answer is not inspectable | Prompt chain or workflow node |
| Tool or node selection | Tool schema + planning examples | Wrong route has high cost | Planner validator or deterministic router |
| Multimodal reference roles | Section headers + explicit role labels | Roles still entangle | Structured asset metadata and per-node filters |
| Product-wide behavior preference | Prompt profile | Repeated across many prompts and users | Eval set, adapter, SFT, DPO |
| Model migration | Model-specific prompt profile + golden cases | Same prompt changes behavior after model switch | Prompt migration notes, model-specific eval matrix, per-model prompt overrides |

## Research Hypotheses

1. Few-shot examples remain the strongest prompt-level control surface for format and local behavior, but they require symmetric maintenance: add and remove fields in examples when the schema changes.
2. Schema-layer prompt engineering is under-discussed academically but central in production, because field descriptions, required fields, enum labels, and field order are all model-visible instructions.
3. Constrained decoding strengthens schema-layer prompt engineering: the schema both limits the output space and supplies local semantic instructions for choosing among valid outputs.
4. Schema-level `thinking` fields are a practical form of question-driven reasoning: they make the reasoning step part of the output contract instead of an optional prose behavior.
5. Prompt placement is not a hard hierarchy. It is a salience mechanism that can be overridden by examples, recent context, tool outputs, or model priors.
6. Mature prompt work eventually needs evals. In this research round, missing evals define the boundary between supported claims and production hypotheses.
7. The real production unit is not "the prompt"; it is a node with a prompt, schema, model, input bindings, context filter, validator, and future regression cases.
8. Repeated prompt patches are a data-discovery process. When the same behavioral failure appears across prompts, it should eventually become eval data and may be considered for deeper learning.
9. Prompt portability is limited. A production prompt should be versioned against the model family it was tuned for, and model switches should be treated as migrations, not drop-in substitutions.

## What Is Proven vs Hypothesized

This distinction matters for blog writing.

### Strongly supported claims

These are safe to use as firm claims with citations:

- Structured outputs can enforce schema shape more reliably than plain JSON prompting, especially when combined with constrained decoding.
- Constrained decoding explains structural validity by masking schema-invalid continuations.
- Schema text can influence model behavior because it is part of the model-visible generation interface.
- Few-shot examples are strong controls for format and local behavior.
- Demonstrations convey more than correct labels; they convey format, distribution, and label space.
- Prompt placement and hierarchy are not hard security guarantees by themselves.
- Decomposition and intermediate reasoning can improve complex reasoning tasks, though the best format depends on the model/task.
- Self-review without external feedback is not a reliable enforcement mechanism.
- Reasoning models have different prompting needs from non-reasoning chat models; provider-specific prompting guidance matters.

### Strong production observations

These are strong Dayfold observations, but should be described as production evidence rather than controlled proof:

- `schema_overrides` are a useful behavior-tuning surface because field descriptions are close to output decisions.
- Schema and prompt must be versioned together; schema drift creates behavior drift.
- Field order and intermediate analysis fields can materially change structured-output behavior.
- Planner few-shots act like operational policy for DAG construction.
- Reference routing and context filtering are important confounders when judging prompt wording changes.
- Model-facing semantic labels are less brittle than numeric page indices.
- Control markers placed in natural-language generation channels can leak.
- Model switches often require prompt/schema/profile retuning even when the product requirement is unchanged.

### Plausible hypotheses that need evals

These should be framed carefully:

- For some Dayfold fields, schema description edits may have larger effect size than global prompt edits.
- Schema-level `thinking` fields may outperform prose "think step by step" because they are required, ordered, and local to dependent fields.
- Field order has a measurable causal effect on decisions when earlier fields are semantically referenced by later fields.
- Positive examples plus schema descriptions may outperform either alone.
- Many repeated prompt failures are better treated as data for fine-tuning or preference optimization than as prompt-writing problems.
- Model-specific prompt profiles can reduce dependence on prompt-tuning expertise that currently lives only in individual product managers' heads.

## Future Validation Plan

The current evidence is enough for a rigorous internal research summary and a careful blog, but not enough for strong causal claims about Dayfold-specific effect sizes. Running evals would be the right next step for a paper-like validation phase, but it is intentionally out of scope for this research round.

This section is kept as a future validation sketch. Its role in the current document is to mark which claims should remain caveated, not to define immediate work.

### Eval principles

1. Keep model, temperature, inputs, and decoding mode fixed while changing one control surface.
2. Test prompt-only, schema-only, examples-only, and combined variants.
3. Use production incidents as regression cases.
4. Separate structure metrics from semantic metrics.
5. Save prompt version, schema version, model target, input context, raw output, parsed output, validator result, and human judgment.

### Minimal experiments

| Experiment | Variable | Fixed | Metrics | Question answered |
|---|---|---|---|---|
| Schema description vs global prompt | Move same instruction between global prompt and field description | model, input, schema shape | field semantic correctness, violation rate | Is local schema text stronger for this field? |
| Field order | Put analysis fields before vs after final field | prompt text, schema descriptions | final decision accuracy, analysis consistency | Does order materially affect decisions? |
| `thinking` field ablation | with/without required reasoning field | prompt, schema final fields | final quality, verbosity, latency | Does schema-level reasoning improve output? |
| Few-shot ablation | no examples / positive examples / positive+negative | prompt and schema | format adherence, route accuracy | Which example pattern controls behavior best? |
| Context-routing control | full context / filtered context / missing ref image | prompt and schema | task relevance, hallucination, image-role confusion | How much apparent prompt behavior actually comes from visible context? |
| Semantic label vs numeric index | page labels vs numeric ids | story and edit request | correct page selection | Do copyable labels reduce reference errors? |
| Self-check vs validator | prompt self-check only / external validator | generation prompt | hard-rule violation rate | Which rules must leave prompt? |
| Model migration | same node prompt across model A/B, then retuned prompt for model B | inputs, schema, validators | behavior parity, violation rate, human preference | What prompt changes are required when switching model families? |

### Dayfold regression set candidates

- Cover generation:
  - story shorter than four pages
  - page one already acts as cover
  - extracted user title must be reused
  - title must not duplicate page one
- Style name:
  - strict 2-4 character limit
  - Chinese/English/digit mixed counting
  - no verbose style names
- Story editor:
  - edit one labeled page
  - insert after semantic page label
  - preserve unchanged dialogue exactly
  - decide edit-from vs regenerate
- Pages enhancer:
  - preserve original page count
  - keep dialogue unchanged
  - identify one highlight page
  - protect necessary elements from style washout
- Pattern chat:
  - auto-injected image opening
  - `thinking` includes story direction, not only slot flow
  - `message` does not ask a question
  - `collected_info` preserves full user words

### Blog-safe claim rule without new evals

Before turning a Dayfold observation into a strong public claim in this round, use one of:

- multiple production incidents fixed by the same pattern
- external paper/provider support plus one production example

If none is available, frame it as "a production hypothesis" or "a pattern worth testing." If a future controlled eval result becomes available, it can upgrade the claim from production-observational to experimentally supported.

## External Blog and Community Scan

This section records non-academic practitioner signals. These sources should not override papers, provider docs, or Dayfold production evidence. Their value is different: they show which ideas are already circulating in engineering communities and which framings may resonate or need clarification in a future blog.

### English web and community discussion

External blogs and discussions broadly support a more mature version of this research thesis:

1. Prompt engineering is not dead, but the public meaning of the term has narrowed to "clever wording." Practitioner writing increasingly uses "context engineering", "prompt management", "skills", "tool ergonomics", or "workflow architecture" for the broader production discipline.
2. Context engineering is usually framed as building dynamic systems that provide the right information, tools, state, memory, and format to the LLM. This confirms the earlier correction: context routing is not PE core; it is a neighboring layer that must be controlled when evaluating prompt changes.
3. Anthropic Skills are a concrete production pattern for progressive disclosure: a small metadata description is loaded first, then detailed instructions, scripts, assets, and references are loaded only when relevant. This is close to "prompt as reusable capability package", not one-off prompt text.
4. Tool design is being discussed as agent-facing interface design. Tool names, descriptions, parameter schemas, and returned context are all part of the model-visible interface.
5. Evals are repeatedly emphasized as the maturity boundary. Blog/community discussions criticize "magic phrases" and favor test cases, traces, A/B variants, production monitoring, and structured graders.
6. Structured outputs are widely treated as essential production infrastructure, but some practitioner discussions warn that constrained decoding can create false confidence: parse failures disappear, while semantic quality failures become less visible.

Representative sources:

| Source | Practitioner signal | Relation to this research |
|---|---|---|
| Simon Willison, "Context engineering" | The term gained traction because "prompt engineering" is often misread as short chatbot wording | Supports using "PE as behavior control" carefully, and separating context routing from PE core |
| LangChain, "The rise of context engineering" | Context engineering is a dynamic system for giving models the right information/tools in the right format | Supports node-level interface design and eval confounder framing |
| Anthropic, "Effective context engineering for AI agents" | Context quality is framed as the decisive input to agent behavior, not merely long prompt text | Supports "what the model sees" as the higher-level control layer |
| Anthropic, "Effective harnesses for long-running agents" | Harnesses include environment, tools, feedback, scoring, and execution control around the model | Supports PE/Context/Harness as adjacent control layers rather than replacements |
| Anthropic, "Harness design for long-running application development" | Harness components encode assumptions about current model capability gaps and should be revisited as models improve | Supports prompt migration and model-specific control-surface framing |
| Phil Schmid, "The New Skill in AI is Not Prompting, It's Context Engineering" | Agent failures are often context failures, and structured output/tool definitions are part of context | Supports the boundary between prompt, context, tools, and schema |
| Coalfire, "Does prompt engineering still matter in late 2025?" | Practitioner framing: prompt engineering still matters, but as part of broader system design, testing, and controls | Supports market-status framing without treating PE as a standalone magic skill |
| Rephrase, "Why Prompt Engineering Isn't Enough" | Practitioner framing: prompt wording alone is insufficient; durable AI systems need context, workflow, and quality controls | Supports the "PE is necessary but insufficient" blog thesis |
| Anthropic, "Agent Skills" | Skills package instructions, scripts, and resources with progressive disclosure | Supports reusable prompt-capability bundles and externalized procedural context |
| Anthropic, "Writing effective tools for agents" | Tools are contracts between deterministic systems and nondeterministic agents; descriptions/specs need prompt-engineering | Supports schema/tool descriptions as model-visible interface design |
| Anthropic, "Demystifying evals for AI agents" | Agent evals need production-like harnesses, transcript inspection, and layered evaluation | Supports eval-first prompt iteration |
| BAML, "Structured Outputs Create False Confidence" | Constrained decoding can make structural errors disappear while hiding semantic quality errors | Supports schema-semantic gap and validation/review layering |
| Reddit prompt-engineering discussions | Recurring practical advice: examples, structured input/output, role/task framing, decomposition, and skepticism toward long magic prompts | Supports "few-shot + structure + eval" rather than phrase hacking |

### Chinese web and Xiaohongshu scan

Chinese public discussion appears more application-facing and less research-taxonomy-oriented. The visible themes are:

1. "提示词工程是否过时" is already being discussed, often through the newer "上下文工程" framing.
2. JSON/structured-output reliability is a prominent practical concern, especially in agent and interview contexts.
3. Chinese practitioner articles often converge on a layered answer: prompt + JSON mode / structured outputs + local validation + retry + logging.
4. 小红书 search results show visible interest in:
   - 提示词工程 vs 上下文工程
   - Harness Engineering
   - JSON 提示词 / JSON schema
   - Claude Code prompt patterns
   - skill context-size management

Useful Chinese sources found:

| Source | Signal | Evidence use |
|---|---|---|
| 知乎: "让大模型稳定地输出 JSON" | Combines prompt, JSON format, few-shot, constrained decoding, function call, extraction/repair, and fallback repair | Strong practitioner support for layered structured-output engineering |
| 知乎: "面试官：如何让AI稳定回复JSON？" | Explicitly frames prompt as soft constraint and structured outputs/constrained decoding/local validation as stronger layers | Good Chinese reference for "soft prompt -> hard constraint -> engineering fallback" |
| 小红书 search: "提示词工程和上下文工程有什么差别？" | High-like search result indicates PE/context-engineering distinction is already a public discussion topic | Discovery signal only; note detail was inaccessible through `opencli` |
| 小红书 search: "Harness Engineering是什么？" | Suggests Chinese AI users are discussing the shift from prompt text to harness/workflow engineering | Discovery signal only |
| 小红书 search: "json提示词还是太好用了" | Suggests JSON-style prompting remains a popular user-facing technique | Weak signal; fetched note content was mostly tags |

### Incremental Takeaways

The external scan adds three useful blog angles:

1. **Avoid the slogan trap.** The public phrase "prompt engineering is dead" is too coarse. A better claim is: "magic wording is shrinking; model-visible interface design is growing."
2. **Schema is a bridge concept.** It is understandable to both engineers and prompt practitioners: it is code-owned structure, model-visible instruction, and decoder-level constraint at the same time.
3. **Chinese blog angle can start from JSON.** For Chinese readers, "如何让 AI 稳定输出 JSON" is a practical entry point into the deeper thesis: prompt is soft control, schema/constrained decoding is harder control, and validators/evals are the production boundary.

### Gemini-Assisted Follow-Up Scan

After loading the local Gemini CLI wrapper from `~/.agent.cli.zsh`, a Gemini web-search pass added one important theme: prompt techniques are becoming more model-family-specific.

The verified subset:

- OpenAI's reasoning-model guidance says reasoning models usually work best with straightforward prompts; explicit "think step by step" prompting is often unnecessary because reasoning happens internally.
- OpenAI's o-series function-calling guide adds a nuance: few-shot prompting may be less useful for pure reasoning, but can still improve tool-calling behavior when the model struggles to construct function arguments correctly.
- DeepSeek-R1's official repository recommends model-specific settings: temperature in the 0.5-0.7 range, 0.6 recommended; avoid system prompts and put instructions in the user prompt; run multiple tests and average results; optionally force a `<think>` prefix when the model bypasses its thinking pattern.

This does not invalidate the few-shot/schema thesis. It refines it:

- Few-shot remains strong for output format, routing, field behavior, and tool arguments.
- Generic CoT prompting is less universally useful on native reasoning models.
- Reasoning-model prompting should prefer clear objectives, constraints, schemas, tools, and evals over heavy reasoning templates.
- Model-specific provider guidance should override generic prompt folklore.

Gemini also returned several community/blog leads that were either too generic or not reliably verifiable. Those are not added as evidence. Only verified sources are cited below.

## Next Work

1. Continue case extraction only if more high-signal Dayfold commits appear; the first before/after pass now covers schema overrides, pages enhancer, context visibility, cover markers, style naming, story editor labels, story editor serialization, planner bindings, and pattern-chat entry state.
2. Defer Dayfold model-specific prompt-profile creation until after current data collection; do not interview prompt owners in this round unless the blog draft exposes a concrete missing detail.
3. Separate blog-ready claims from production hypotheses without adding new eval claims.
4. After data collection stabilizes, outline the blog from the strongest spine: schema-as-prompt, few-shot as pattern control, reasoning fields, and model-specific prompt portability.
5. Keep the eval sketch as a later validation phase, especially if this research is ever upgraded toward a paper-like artifact.
6. Feed stable failures back into the Learning track: prompt -> activation -> adapter -> weight-level intervention.

## Evidence and Source-Gathering Log

This section records the evidence chain for future blog writing. It separates direct literature support from provider guidance and Dayfold production observations.

| Date | Source | Type | Finding extracted | Used for | Evidence strength |
|---|---|---|---|---|---|
| 2026-04-28 | OpenAI Structured Outputs announcement | Provider implementation note | Structured Outputs combines model training with deterministic constrained decoding; constrained decoding masks invalid JSON Schema continuations | Explains why schema can guarantee structure but not semantic correctness | Direct for constrained decoding mechanism |
| 2026-04-28 | JSONSchemaBench | Benchmark paper | JSON Schema is the common target for constrained decoding frameworks; benchmark evaluates efficiency, coverage, and quality across real-world schemas | Supports treating JSON Schema as a first-class control surface | Direct for structured-output constraint layer |
| 2026-04-28 | Schema Key Wording as an Instruction Channel | Research paper | Changing schema key wording alone can alter model behavior under constrained decoding | Supports "schema-as-prompt" and schema wording as an instruction channel | Direct for key wording; adjacent for `description` |
| 2026-04-28 | Gemini structured output docs | Provider docs | Pydantic/Zod schema descriptions and property order are part of the structured output interface | Supports schema descriptions and field order as model-visible controls | Provider guidance; implementation-specific |
| 2026-04-28 | OpenAI prompt / eval / optimization docs | Provider docs | Prompt versions, evals, structured outputs, and fine-tuning belong in the same iteration loop | Supports eval-first prompt engineering | Provider guidance |
| 2026-04-28 | OpenAI reasoning best practices and o-series function-calling guide | Provider docs | Reasoning models prefer simple direct prompts and do not usually need explicit CoT prompting; few-shot can still help tool argument construction | Refines prompt-technique taxonomy by model family | Provider guidance |
| 2026-04-28 | OpenAI GPT-4.1 prompting guide | Provider docs | GPT-4.1 can require different prompting from older models, follows instructions more literally, and may benefit from explicit planning/long-context placement guidance | Supports model-family prompt profile and migration framing | Provider guidance |
| 2026-04-28 | OpenAI GPT-5.1 prompting guide | Provider docs | Model migration can require tuning persistence, verbosity, tool behavior, output format, and instruction conflicts | Supports prompt migration as a first-class engineering task | Provider guidance |
| 2026-04-28 | DeepSeek-R1 official repository | Provider/model docs | R1 recommends 0.5-0.7 temperature, no system prompt, user-prompt instructions, multiple-test averaging, and optional `<think>` prefix enforcement | Adds Chinese/open-model reasoning-specific prompting constraints | Provider/model guidance |
| 2026-04-28 | Anthropic Claude prompting best practices and Claude 4.x guidance | Provider docs | Claude-specific tuning includes XML structure, examples, long-context ordering, effort controls, verbosity/proactiveness tuning, and migration cleanup | Supports model-specific prompt dialect and upgrade retuning | Provider guidance |
| 2026-04-28 | Google Gemini prompting, structured output, and thinking docs | Provider docs | Gemini exposes few-shot policy, schema descriptions/property order, thinking budgets, and model-specific temperature guidance | Supports schema/order/reasoning budget as model-specific PE controls | Provider guidance |
| 2026-04-28 | PromptBridge | Research paper | Cross-model prompt transfer degrades because prompts optimized for one model do not directly preserve behavior on another; calibration/eval-based adaptation can improve transfer | Supports prompt portability limits and prompt migration evals | Direct for cross-model transfer |
| 2026-04-28 | DSPy | Research framework/docs | Declarative signatures/modules plus metrics can compile or optimize prompts for target models | Supports moving prompt taste into eval-driven prompt programs | Research/practitioner framework |
| 2026-04-28 | Anthropic prompt engineering docs | Provider docs | Examples, XML tags, role prompting, long-context ordering, and prompt chaining are recommended prompt controls | Supports taxonomy categories | Provider guidance |
| 2026-04-28 | Simon Willison / LangChain / Phil Schmid context-engineering blogs | Practitioner blogs | Public framing is shifting from short prompt wording to dynamic context, tools, state, memory, and formatting | Supports separating PE core from context-engineering boundary conditions | Practitioner signal |
| 2026-04-28 | Anthropic Agent Skills | Provider engineering blog | Skills package instructions, scripts, and resources with progressive disclosure | Supports reusable capability packages and externalized procedural context | Provider/practitioner guidance |
| 2026-04-28 | Anthropic tool-writing and eval blogs | Provider engineering blogs | Tool specs/descriptions and eval tasks are treated as core agent quality surfaces | Supports tool/schema descriptions and eval-first iteration | Provider/practitioner guidance |
| 2026-04-28 | BAML "Structured Outputs Create False Confidence" | Practitioner blog | Structured outputs may shift visible parse failures into subtler quality failures | Supports schema-semantic gap and the need for validators/evals | Practitioner counterpoint |
| 2026-04-28 | Zhihu JSON-output articles | Chinese practitioner blogs | Chinese applied discussion converges on prompt + JSON mode/schema + validation/retry/logging | Supports Chinese blog entry point around stable JSON as layered control | Practitioner signal |
| 2026-04-28 | Xiaohongshu search via `opencli` | Chinese social scan | Visible discussion exists around prompt engineering vs context engineering, Harness Engineering, JSON prompts, Claude Code prompt patterns | Discovery signal for audience framing | Weak discovery signal; most note details unavailable |
| 2026-04-30 | Anthropic context and harness engineering posts | Provider engineering blogs | Context and harness frame agent quality as selecting and organizing model-visible information, tools, state, feedback, evals, and runtime control; harness components encode assumptions about model capability gaps | Supports the blog framing that Context Engineering and Harness move the control layer up while PE remains the direct model-visible expression layer | Provider/practitioner guidance |
| 2026-04-30 | Coalfire and Rephrase prompt-engineering trend posts | Practitioner blogs | Practitioner writing continues to argue that prompt engineering is not enough by itself, but still matters when integrated with system design, context, schema, testing, and controls | Supports the blog market-status claim: prompt tricks cooled, model-visible interface design did not disappear | Practitioner signal |
| 2026-04-28 | The Prompt Report | Survey paper | Prompt engineering has many distinct technique families, not a single "good prompt" recipe | Supports taxonomy framing | Broad survey evidence |
| 2026-04-28 | Chain-of-Thought Prompting | Research paper | Intermediate reasoning demonstrations improve complex reasoning on arithmetic, commonsense, and symbolic tasks | Supports reasoning fields and CoT-style decomposition | Direct for CoT; task-dependent |
| 2026-04-28 | Self-Consistency | Research paper | Sampling multiple reasoning paths and aggregating answers improves CoT reliability | Supports the idea that reasoning path choice matters | Direct for reasoning aggregation; not directly a schema claim |
| 2026-04-28 | Least-to-Most Prompting | Research paper | Breaking a hard task into simpler subproblems improves easy-to-hard generalization | Supports question-driven reasoning and decomposition | Direct for decomposition |
| 2026-04-28 | ReAct | Research paper | Interleaving reasoning traces with actions lets models use external observations and reduce hallucination/error propagation | Supports prompt chaining and tool/workflow decomposition | Direct for reasoning/action workflows |
| 2026-04-28 | Self-Refine | Research paper | Iterative feedback and refinement can improve outputs at test time without training | Supports review-pass prompts as a useful layer | Direct for self-feedback improvements; task-dependent |
| 2026-04-28 | LLMs Cannot Self-Correct Reasoning Yet | Research paper | Intrinsic self-correction without external feedback can fail or degrade reasoning performance | Supports caution that self-check is not enforcement | Direct for self-correction limits |
| 2026-04-28 | In-context Learning and Induction Heads | Mechanistic paper | In-context pattern completion has identifiable attention-head mechanisms | Supports why few-shot and DSL-like patterns can be strong | Mechanistic evidence |
| 2026-04-28 | Rethinking the Role of Demonstrations | Research paper | Demonstrations supply label space, input distribution, and format, not only correct examples | Supports few-shot format lock-in and add/delete symmetry | Direct for few-shot mechanism |
| 2026-04-28 | Larger language models do in-context learning differently | Research paper | Larger models can use in-context examples to override priors; instruction tuning affects priors and mappings differently | Supports few-shot vs prior tension | Direct for ICL behavior |
| 2026-04-28 | The Instruction Hierarchy | Research paper | Current models need explicit hierarchy training to reliably prioritize privileged instructions | Supports "system prompt is salience, not hard hierarchy" | Direct for hierarchy weakness |
| 2026-04-28 | CyberMnema W17 instruction-following topic | Local research note | Long-context drift, prior override, generation-verification gap, and few-shot lock-in explain why soft rules fail | Provides local synthesis and engineering interpretation | Secondary synthesis |
| 2026-04-28 | Dayfold `060dc548f` schema override implementation | Production code and commit | `schema_overrides` are parsed from YAML, applied to effective JSON Schema before structured generation, and support nested dot paths | Supports exact mechanism for schema-as-prompt in Dayfold | Direct production implementation evidence |
| 2026-04-28 | Dayfold schema override design | Production design doc | LLM-visible Pydantic field descriptions were made configurable through `schema_overrides` | Supports schema override as production PE design | Direct production evidence |
| 2026-04-28 | Dayfold prompt-quality and literal-binding plans | Production design docs | Prompt quality improvements use schema, few-shots, prompt routing, `l:` binding, resource graphs, and self-checks | Supports node-level interface design and the boundary with context engineering | Direct production evidence |
| 2026-04-28 | Dayfold prompt profiles | Production prompt files | `schema_overrides`, analysis fields before final decisions, positive/negative examples, anti-refusal prompts, and multimodal reference disambiguation appear in production prompts | Supplies concrete case bank | Direct production evidence |
| 2026-04-28 | Dayfold prompt Git history | Production commit history | Prompt changes repeatedly target schema text, field order, context visibility, model-readable references, and visible-marker leakage | Supplies before/after production evidence for PE patterns | Direct production evolution evidence |
| 2026-04-28 | Dayfold before/after case extraction | Production commit diffs and plan docs | Nine concrete cases were extracted: schema overrides, highlight-page reasoning, context visibility, cover marker leakage, `style_name`, pseudo page labels, editor serialization, planner bindings, and pattern-chat entry state | Supplies blog-ready production examples with caveats | Strong production-observational evidence; not controlled eval |
| 2026-04-28 | Dayfold pattern-chat and pages-enhancer prompts | Production prompt files | `thinking`, `analysis_*`, and `global_reasoning` fields are used to force task-specific interpretation before final fields | Supports schema-level thinking fields as practical CoT | Direct production evidence |

Blog evidence guidance:

- Use provider docs for "what APIs officially support and recommend."
- Use papers for "why the mechanism should work."
- Use Dayfold docs and prompt files for "what survived first-line production tuning."
- Mark `description` semantics as a strong production/provider-doc finding, but note that the newest direct paper evidence is currently stronger for schema key wording than for description wording specifically.

## References

Provider guidance:

- [Anthropic: Prompt engineering overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) (accessed: 2026-04-28)
- [Anthropic: Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) (accessed: 2026-04-28)
- [Anthropic: Claude 4 best practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices) (accessed: 2026-04-28)
- [OpenAI: Prompting](https://platform.openai.com/docs/guides/prompting) (accessed: 2026-04-28)
- [OpenAI: Reasoning best practices](https://platform.openai.com/docs/guides/reasoning-best-practices) (accessed: 2026-04-28)
- [OpenAI Cookbook: Reasoning function calls](https://cookbook.openai.com/examples/o-series/o3o4-mini_prompting_guide) (accessed: 2026-04-28)
- [OpenAI Cookbook: GPT-4.1 Prompting Guide](https://cookbook.openai.com/examples/gpt4-1_prompting_guide) (accessed: 2026-04-28)
- [OpenAI Cookbook: GPT-5.1 Prompting Guide](https://cookbook.openai.com/examples/gpt-5/gpt-5-1_prompting_guide) (accessed: 2026-04-28)
- [OpenAI: Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) (accessed: 2026-04-28)
- [OpenAI: Introducing Structured Outputs in the API](https://openai.com/index/introducing-structured-outputs-in-the-api/) (accessed: 2026-04-28)
- [OpenAI: Evals](https://platform.openai.com/docs/guides/evals) (accessed: 2026-04-28)
- [OpenAI: Model optimization](https://platform.openai.com/docs/guides/model-optimization) (accessed: 2026-04-28)
- [Google: Gemini prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies) (accessed: 2026-04-28)
- [Google: Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) (accessed: 2026-04-28)
- [Google: Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking) (accessed: 2026-04-28)
- [Google: Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3) (accessed: 2026-04-28)
- [Google: Gemini file prompting strategies](https://ai.google.dev/gemini-api/docs/file-prompting-strategies) (accessed: 2026-04-28)
- [DeepSeek-AI: DeepSeek-R1](https://github.com/deepseek-ai/DeepSeek-R1) (accessed: 2026-04-28)

Academic sources:

- [The Prompt Report: A Systematic Survey of Prompt Engineering Techniques](https://arxiv.org/abs/2406.06608) (accessed: 2026-04-28)
- [A Systematic Survey of Automatic Prompt Optimization Techniques](https://arxiv.org/abs/2502.16923) (accessed: 2026-04-28)
- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) (accessed: 2026-04-28)
- [Self-Consistency Improves Chain of Thought Reasoning in Language Models](https://arxiv.org/abs/2203.11171) (accessed: 2026-04-28)
- [Least-to-Most Prompting Enables Complex Reasoning in Large Language Models](https://arxiv.org/abs/2205.10625) (accessed: 2026-04-28)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) (accessed: 2026-04-28)
- [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651) (accessed: 2026-04-28)
- [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) (accessed: 2026-04-28)
- [In-context Learning and Induction Heads](https://arxiv.org/abs/2209.11895) (accessed: 2026-04-28)
- [Rethinking the Role of Demonstrations: What Makes In-Context Learning Work?](https://arxiv.org/abs/2202.12837) (accessed: 2026-04-28)
- [Larger language models do in-context learning differently](https://arxiv.org/abs/2303.03846) (accessed: 2026-04-28)
- [Do Models Really Learn to Follow Instructions?](https://arxiv.org/abs/2305.11383) (accessed: 2026-04-28)
- [The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions](https://arxiv.org/abs/2404.13208) (accessed: 2026-04-28)
- [JSONSchemaBench: A Benchmark for Evaluating Constrained Decoding for JSON Schema](https://arxiv.org/abs/2501.10868) (accessed: 2026-04-28)
- [Schema Key Wording as an Instruction Channel in Structured Generation under Constrained Decoding](https://arxiv.org/abs/2604.14862) (accessed: 2026-04-28)
- [PromptBridge: Cross-Model Prompt Transfer for Large Language Models](https://arxiv.org/abs/2512.01420) (accessed: 2026-04-28)

Practitioner blogs and community sources:

- [DSPy: Programming, not prompting, LMs](https://dspy.ai/) (accessed: 2026-04-28)
- [Simon Willison: Context engineering](https://simonwillison.net/2025/Jun/27/context-engineering/) (accessed: 2026-04-28)
- [LangChain: The rise of context engineering](https://www.langchain.com/blog/the-rise-of-context-engineering) (accessed: 2026-04-28)
- [LangChain: Context engineering for agents](https://www.langchain.com/blog/context-engineering-for-agents) (accessed: 2026-04-28)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (accessed: 2026-04-30)
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (accessed: 2026-04-30)
- [Anthropic: Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) (accessed: 2026-04-30)
- [Phil Schmid: The New Skill in AI is Not Prompting, It's Context Engineering](https://www.philschmid.de/context-engineering) (accessed: 2026-04-28)
- [Coalfire: Does prompt engineering still matter in late 2025?](https://coalfire.com/the-coalfire-blog/does-prompt-engineering-matter-late-2025) (accessed: 2026-04-30)
- [Rephrase: Why Prompt Engineering Isn't Enough](https://www.rephrasy.ai/blog/why-prompt-engineering-isnt-enough) (accessed: 2026-04-30)
- [Anthropic: Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (accessed: 2026-04-28)
- [Anthropic: Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents) (accessed: 2026-04-28)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (accessed: 2026-04-28)
- [BAML: Structured Outputs Create False Confidence](https://boundaryml.com/blog/structured-outputs-create-false-confidence) (accessed: 2026-04-28)
- [Hacker News discussion: Structured outputs create false confidence](https://news.ycombinator.com/item?id=46345333) (accessed: 2026-04-28)
- [知乎: 让大模型稳定地输出 JSON](https://zhuanlan.zhihu.com/p/1918090301261743958) (accessed: 2026-04-28)
- [知乎: 面试官：如何让AI稳定回复JSON？](https://zhuanlan.zhihu.com/p/2028047982583452125) (accessed: 2026-04-28)

Local research and production sources:

- [plan/5-prompt-engineering-research.md](./plan/5-prompt-engineering-research.md)
- [context.summary.md](./context.summary.md)
- [learning.summary.md](./learning.summary.md)
- [personality-engineering.research.md](./personality-engineering.research.md)
- [anthropic-context-engineering.research.md](./anthropic-context-engineering.research.md)
- `/Users/linguanguo/dev/CyberMnema/timeline/2026/04/W17/LLM指令遵从研究-2026-04-23.md`
- `/Users/linguanguo/dev/CyberMnema/timeline/2026/04/W17/PE生产技巧-2026-04-24.md`
- `/Users/linguanguo/dev/CyberMnema/timeline/2026/04/W18/记忆上下文与PE启发整理-2026-04-28.md`
- `/Users/linguanguo/dev/dayfold_webapp/agent/docs/plans/83-prompt-quality-upgrade-design.md`
- `/Users/linguanguo/dev/dayfold_webapp/agent/docs/plans/111-llm-schema-description-override.md`
- `/Users/linguanguo/dev/dayfold_webapp/agent/docs/plans/105-planner-literal-binding-design.md`
- `/Users/linguanguo/dev/dayfold_webapp/agent/docs/plans/67-planner-literal-binding-and-prompt-bias-fix.md`
