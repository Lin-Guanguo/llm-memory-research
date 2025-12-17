# Letta (MemGPT) Technical Research Report

Last Updated: 2025-12-17

## Overview

**Letta** (formerly MemGPT) is an open-source framework that transforms stateless LLMs into stateful agents with persistent memory. Based on the MemGPT paper's "LLM Operating System" principles, it implements a hierarchical memory system with virtual context management, enabling unbounded context through intelligent paging.

**Source:** [Letta GitHub Repository](https://github.com/letta-ai/letta)

---

## 1. Core Concept: The "LLM OS" Analogy

Letta treats the LLM agent as an operating system:

| OS Component | LLM Equivalent | Letta Implementation |
|--------------|----------------|----------------------|
| **CPU** | LLM (GPT-4, Claude, etc.) | Processing and reasoning |
| **RAM** | Context Window | Limited "hot" memory for immediate processing |
| **Hard Drive** | External Storage | Unlimited "cold" storage (vector DBs, SQL) |
| **Kernel** | Agent Orchestrator | Manages data paging between RAM and Disk |

**Key Insight:** Unlike standard RAG which passively retrieves before generation, Letta is **proactive** - the LLM decides *if, when, and what* to retrieve using tools.

---

## 2. Three-Tier Memory Architecture

### Memory Tiers

| Tier | Analogy | Description | Always In-Context? |
|------|---------|-------------|--------------------|
| **Core Memory** | RAM/BIOS | Agent identity + working memory | Yes |
| **Recall Memory** | Chat Logs | Conversation history | No (searchable) |
| **Archival Memory** | Hard Drive | Long-term knowledge storage | No (searchable) |

### A. Core Memory (In-Context)

**Location:** `letta/schemas/memory.py` (line 56), `letta/schemas/block.py`

Core memory consists of **editable Blocks** always present in the system prompt:

```python
class Memory(BaseModel):
    blocks: List[Block]           # Editable memory blocks
    file_blocks: List[FileBlock]  # File content blocks
    agent_type: AgentType         # Determines rendering style
```

**Default Blocks:**
- `persona` - Who the agent is (personality, capabilities)
- `human` - Facts about the user

**Block Schema:**
```python
class Block(BaseModel):
    label: str           # Identifier (e.g., "persona", "human")
    value: str           # Actual text content
    limit: int = 2000    # Character limit (CORE_MEMORY_BLOCK_CHAR_LIMIT)
    read_only: bool      # Prevent agent edits
    description: str     # Block purpose documentation
```

**Rendering:** Two modes in `Memory.compile()`:
- Standard XML rendering for most providers
- Line-numbered format for Anthropic models (`_render_memory_blocks_line_numbered()`)

### B. Archival Memory (Long-Term Storage)

**Location:** `letta/services/passage_manager.py`

Vector-embedded passages stored in database:
- **Storage:** Vector DB (Chroma, Qdrant, pgvector) or native PostgreSQL
- **Access:** Via `archival_memory_search()` and `archival_memory_insert()` tools
- **Search:** Hybrid search using RRF (Reciprocal Rank Fusion) combining vector similarity + full-text search

**Schema:** `ArchivalPassage` ORM model with embeddings, timestamps, and tags.

### C. Recall Memory (Conversation History)

**Location:** `letta/services/message_manager.py`

Database-stored message history:
- **Access:** Via `conversation_search()` tool
- **Features:**
  - Date range filtering
  - Role-based filtering (user/assistant/tool)
  - Hybrid search (text + semantic)
- **Integration:** Supports Turbopuffer for fast vector search (line 1051)

---

## 3. Virtual Context Management

### Context Window Structure

The actual prompt sent to the LLM is dynamically assembled:

```
[System Instructions]
[Core Memory Block: Persona]
[Core Memory Block: Human]
[Tool Definitions (Memory Functions)]
[Notification: "70 previous messages hidden..."]
[Recent Message History]
```

### Context Window Tracking

**Location:** `letta/services/context_window_calculator/context_window_calculator.py`

```python
class ContextWindowOverview:
    num_system_message: int      # Tokens in system prompt
    num_core_memory: int         # Tokens in core memory blocks
    num_external_memory_summary: int  # Archival/recall summary tokens
    num_messages: int            # Conversation message tokens
    num_tools: int               # Tool definition tokens
    context_window_limit: int    # Max tokens
    context_window_size_current: int  # Current usage
```

### Paging/Swapping Mechanism

**Location:** `letta/services/summarizer/summarizer.py`

When context exceeds threshold:
1. **Detection:** `context_window_size_current > memory_warning_threshold`
2. **Eviction:** Older messages removed from active window → remain in Recall Memory
3. **Summarization:** `partial_evict_summarization()` compresses old messages
4. **Insertion:** Summary message inserted as index 1 (after system message)

```python
def simple_summary(messages) -> str:
    # Uses separate "ephemeral summary agent" to generate summary
    # Falls back to transcript truncation if context too large
```

---

## 4. Self-Editing Memory (Key Differentiator)

The agent has **write-access** to its own prompts via tools.

### Core Memory Edit Tools

**Location:** `letta/services/tool_executor/core_tool_executor.py`

| Tool | Line | Description |
|------|------|-------------|
| `core_memory_append()` | 320 | Add content to block |
| `core_memory_replace()` | 329 | Replace old_content with new_content |
| `memory_replace()` | 347 | Modern version with old_str/new_str |
| `memory_apply_patch()` | 416 | Apply unified diff-style patches |
| `memory_insert()` | 526 | Insert text at specific line |
| `memory_rethink()` | 599 | Complete block rewrite |
| `memory_finish_edits()` | 643 | Commit pending edits |

### Self-Edit Execution Flow

```
1. User: "My favorite color is actually blue, not red."
2. LLM reasons: "I need to update the 'Human' block"
3. LLM emits: core_memory_replace(label="human", old="fav_color: red", new="fav_color: blue")
4. Letta executes function, updates DB
5. System prompt rebuilt with new memory state for next turn
```

### Safeguards

- **Read-only protection:** Checks `block.read_only` before edits
- **Line number validation:** Regex prevents agents from including line numbers in edits
- **Uniqueness checks:** Ensures `old_str` appears exactly once
- **Persistence:** `update_memory_if_changed_async()` compares and updates only changed blocks

---

## 5. Agent Architecture

### Agent Class Hierarchy

**Location:** `letta/agent.py` (line 96)

```python
class Agent:
    agent_state: AgentState       # Configuration and state
    agent_manager: AgentManager   # Persistence operations
    block_manager: BlockManager   # Block CRUD
    message_manager: MessageManager  # Message history
    llm_client: LLMClient         # LLM API abstraction
```

### Execution Loop

**Main Loop:** `step()` (line 753)

```
step() with chaining support
├── Loop iteration:
│   ├── inner_step() - Single LLM interaction
│   │   ├── Load persisted memory from blocks
│   │   ├── Get in-context messages
│   │   ├── _get_ai_reply() - Call LLM with tools
│   │   ├── _handle_ai_response() - Parse & execute tools
│   │   └── Persist new messages to DB
│   ├── Check heartbeat_request flag
│   └── Handle chaining conditions
└── Return aggregated usage stats
```

### Agent Types

| Type | Description |
|------|-------------|
| `memgpt_agent` | Original MemGPT implementation |
| `memgpt_v2_agent` | Refreshed toolset |
| `letta_v1_agent` | Simplified, no forced tool calls |
| `react_agent` | ReAct-style reasoning |
| `sleeptime_agent` | With background memory agent |
| `workflow_agent` | Auto-clearing message buffer |

---

## 6. Tool System

### Tool Types

**Location:** `letta/schemas/tool.py`

| Type | Description |
|------|-------------|
| `LETTA_CORE` | Core memory and search tools (send_message, conversation_search, archival_memory_*) |
| `CUSTOM` | User-defined Python functions |
| `EXTERNAL_MCP` | Model Context Protocol integrations |
| `COMPOSIO` | Third-party action integrations |

### Tool Execution Pipeline

**Location:** `letta/services/tool_executor/`

```
ToolExecutionManager (orchestrator)
├── ToolExecutorFactory → routes to appropriate executor
├── LettaCoreToolExecutor → handles core Letta tools
├── SandboxToolExecutor → isolated execution for custom tools
└── ToolExecutionSandbox → E2B sandbox support
```

### Tool Rules

**Location:** `letta/schemas/tool_rule.py`

| Rule | Behavior |
|------|----------|
| `TerminalToolRule` | Tool that ends execution chain |
| `RequiresApprovalToolRule` | Requires human approval |
| `ContinueToolRule` | Forces heartbeat after execution |
| `InitToolRule` | Force first message tool |

---

## 7. Persistence Layer

### ORM Architecture

**Location:** `letta/orm/`

SQLAlchemy ORM with PostgreSQL (recommended) or SQLite:

| Model | Purpose |
|-------|---------|
| `AgentModel` | Agent configuration |
| `BlockModel` | Memory blocks |
| `MessageModel` | Conversation history |
| `ArchivalPassageModel` | Archival memory passages |

### Persistence Flow

```python
# Memory update flow (agent_manager.py:1555)
for block in new_memory.blocks:
    old_block = get_block_by_id(block.id)
    if block.value != old_block.value:
        block_manager.update_block(block)

# Refresh memory from DB
agent_state.memory = Memory(
    blocks=[get_block_by_id(b.id) for b in memory.blocks]
)
```

---

## 8. LLM Provider Integration

### Supported Providers

**Location:** `letta/llm_api/`

| Category | Providers |
|----------|-----------|
| **Cloud** | OpenAI, Anthropic, Google (Gemini, Vertex), Azure OpenAI |
| **Enterprise** | AWS Bedrock, Together AI, Groq |
| **Local** | Ollama, LM Studio |
| **Specialized** | XAI, DeepSeek |

### Client Architecture

```python
# Factory pattern
LLMClient.create(provider_type, put_inner_thoughts_first, actor)

# Each client inherits from LLMClientBase:
- build_request_data()  # Convert to provider format
- request_async()       # Send API request
- convert_response_to_chat_completion()  # Normalize response
```

### Provider-Specific Handling

- **Anthropic:** Line-numbered memory rendering (memory.py lines 279-293)
- **OpenAI:** Standard function calling format
- **Reasoning models:** Special handling for o1/o3 models

---

## 9. Letta vs Standard RAG

| Feature | Standard RAG | Letta |
|---------|--------------|-------|
| **Retrieval** | Passive: retrieve before LLM sees query | Active: LLM decides if/when/what to retrieve |
| **Memory** | Read-only: LLM cannot update vector DB | Read/Write: LLM actively saves knowledge |
| **State** | Stateless: reset after every request | Stateful: identity persists across sessions |
| **Context** | Polluted: often stuffed with irrelevant chunks | Curated: agent maintains concise Core Memory |
| **Update Mechanism** | Append-only | Self-editing with CRUD operations |

---

## 10. Recent Developments (2024-2025)

1. **Letta v1 Agent:** New architecture optimized for reasoning models (GPT-4o, Claude 3.5), more flexible than strict MemGPT structure

2. **Split-Thread Architecture:** Separation of "thinking" (internal monologue/tool execution) from "speaking" (user-facing response)

3. **Server/Client Split:** FastAPI backend managing agent states, allowing multiple frontend clients (web, CLI, Discord)

4. **Sleeptime Agents:** Background memory management agent for organizing and compacting memory

---

## 11. Key Takeaways

1. **LLM as Operating System:** Memory management inspired by OS virtual memory principles

2. **Three-Tier Memory:** Core (always in-context) → Recall (searchable history) → Archival (vector storage)

3. **Self-Editing is Key:** Agent writes to its own prompt, unlike passive RAG systems

4. **Virtual Context:** Summarization + paging creates illusion of infinite context

5. **Tool-Based Memory Access:** Memory operations exposed as LLM function calls

6. **Stateful by Design:** Agent identity and knowledge persist across sessions

7. **Provider Agnostic:** Clean abstraction layer supports 15+ LLM providers

---

## References

- [Letta GitHub Repository](https://github.com/letta-ai/letta)
- [Letta Documentation](https://docs.letta.com/)
- [MemGPT Paper](https://arxiv.org/abs/2310.08560) - "MemGPT: Towards LLMs as Operating Systems"
- Core implementation: `letta/agent.py` (2000+ lines)
- Memory schemas: `letta/schemas/memory.py`, `letta/schemas/block.py`
- Tool executor: `letta/services/tool_executor/`
