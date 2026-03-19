# Dayfold Agent Context Management Research

Last Updated: 2026-03-19

Source: Self-developed agent, closed source. Architecture doc at `dayfold_webapp-new/agent/docs/architecture.md`.

Research focus: How a LangGraph-based multi-node workflow agent manages context, compared to mainstream single-loop agents.

---

## Architecture Overview

Dayfold Agent is a **LangGraph workflow execution engine** — fundamentally different from all other agents studied (Pi, OpenClaw, Gemini CLI, Claude Code, Codex). Where those agents are single-loop conversational agents (user → LLM → tool → LLM → ...), Dayfold uses a **multi-node DAG** with a Planner LLM generating execution plans that a Coordinator dispatches across capability nodes.

```
HTTP Request → RunService → LangGraph CompiledGraph → Capability Nodes → Event Stream
```

Five graph nodes: Planner → Coordinator → capability_worker (×N, parallel via Send) → ResultDigest → WaitForHuman.

## Context Model: Dual Channel

The core design difference from mainstream agents is **separation of structured data and semantic context** into two independent channels:

| Channel | Carries | Mechanism | Consumers |
|---------|---------|-----------|-----------|
| **Port System** | Structured data (story pages, image tasks, style configs) | `port_values: dict[str, PortValue]` in graph state | Coordinator binds inputs via `input_bindings` |
| **ContextMessage System** | Conversation memory (what the user said, what nodes did) | `context_messages: tuple[ContextMessage, ...]` append-only | Planner (full history → LLM), Capability nodes (filtered) |

Mainstream agents (Claude Code, Codex, etc.) have only one channel — everything (tool results, user messages, system reminders) goes into the same conversation history.

## Context Accumulation

Like mainstream agents, `context_messages` is append-only. But what gets appended is different:

**Mainstream agents**: Full tool call arguments + full tool result output + full LLM response, all in one context.

**Dayfold**: Only **summary_exchange** messages enter context. Each capability node's execution is compressed into a user+assistant pair at completion time:

```yaml
# Example from YAML profile
summary_exchange:
  - role: user
    content: "撰写漫画脚本"
  - role: assistant
    content: "完成脚本撰写\n{{ __response__ }}"
```

The full LLM prompt and response (`message_type="full"`) are explicitly disabled:

```python
# llm_service.py:184 — Full exchange disabled: nobody consumes message_type="full"
```

This means every node execution is **compacted immediately** rather than waiting for a threshold trigger. The tradeoff: Planner has less detail when replanning, but context stays small.

## Context Filtering (Per-Node)

Each capability node has a `context_filter` in its YAML profile that controls which context_messages it receives. Three tiers:

| Tier | Nodes | Filter | What they see |
|------|-------|--------|---------------|
| **Full** | story_writer, pages_enhancer, story_editor, universal, planning | `or: [summary, user_input, system]` | All summaries + all user messages + system messages |
| **Cap-restricted** | style_resolver, poster_writer, cover_design | `or: [user_input, system, {and: [summary, cap:self]}]` | User messages + system + only their own historical summaries |
| **None** | image_render, char_ref_render | `"none"` | Nothing (data comes entirely through ports) |

Filtering is based on auto-derived tags from ContextMessage metadata: `type:{message_type}`, `cap:{capability_id}`, `step:{step_id}`, `plan:{plan_id}`, `llm:{llm_id}`.

No mainstream agent has per-node context filtering at this granularity.

## Message Structure

```python
class ContextMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    message_type: Literal["", "summary", "full", "user_input", "system"] = ""
    tags: tuple[str, ...] = ()
    capability_id: str = ""
    step_id: str = ""
    plan_id: str = ""
    llm_id: str = ""
```

`message_type` provides structural distinction between real user messages (`"user_input"`) and system-injected summaries (`"summary"`). This is cleaner than Claude Code's approach (which relies on `<system-reminder>` tags within user messages with no structural field to distinguish them).

## LLM Call Context Assembly

Each LLM call in `LlmServiceImpl` assembles messages as:

```python
all_messages = (
    *context_prompt_msgs,    # 1. Filtered context history (ContextMessage → PromptMessage)
    *messages,               # 2. Additional caller-provided messages
    PromptMessage(           # 3. Current rendered prompt template
        role="user",
        content=rendered.prompt_text
    )
)
```

`context_to_prompt_messages()` is a direct mapping — no normalization or alternation validation:

```python
def context_to_prompt_messages(messages):
    return tuple(PromptMessage(role=m.role, content=m.content) for m in messages)
```

## Potential Issues Identified

**1. No user/assistant alternation guarantee**

Multiple nodes appending to context_messages concurrently (via LangGraph Send) could produce consecutive same-role messages. `context_to_prompt_messages()` does not validate or repair alternation. Some LLM APIs may reject or behave unexpectedly with non-alternating sequences.

**2. No compaction mechanism**

Unlike all mainstream agents studied, there is no compaction/compression triggered when context_messages grows large. The summary_exchange strategy keeps individual entries small, but across many conversation rounds, accumulation could approach context window limits. No fallback exists for this scenario.

**3. context_filter may break message pairing**

If a filter includes one half of a summary_exchange pair (e.g., the assistant response) but not the other (the user request), the resulting message sequence will have broken alternation.

**4. system messages in the middle of history**

`build_context_messages_from_user_text()` injects system messages into context_messages. When mixed with later summary_exchange pairs, system messages may appear in unexpected positions for some LLM APIs.

**5. Summary information loss**

With `message_type="full"` disabled, Planner cannot access the detailed output of previous nodes through context — only through summary text. If a replan requires specific details (exact character names, error messages, etc.), the summary may be insufficient. The Port system compensates for structured data, but unstructured insights from LLM responses may be lost.

## Comparison with Mainstream Agents

| Aspect | Mainstream (Claude Code, Codex, Pi...) | Dayfold Agent |
|--------|---------------------------------------|---------------|
| **Architecture** | Single conversation loop | Multi-node DAG workflow |
| **Data channels** | One (conversation history) | Two (Ports + ContextMessages) |
| **What enters context** | Full tool call + full result | Summary exchange only |
| **When compression happens** | At threshold (reactive) | At node completion (proactive) |
| **Context filtering** | None or coarse (per-session) | Per-node, tag-based filter DSL |
| **Compaction fallback** | Yes (LLM summarization) | None |
| **Sub-agents** | Separate context, return summary | Capability nodes are effectively sub-agents |
| **message_type distinction** | No structural field (Claude Code uses tags) | Explicit `message_type` field |
| **Parallelism** | Sequential tool calls (mostly) | Parallel Send via LangGraph |
