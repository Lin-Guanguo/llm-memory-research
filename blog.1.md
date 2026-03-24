# LLM Memory Systems: 2025 Technology Landscape and Production Reality

Last Updated: 2025-12-28

> While researching LLM memory systems, I found some interesting things: ChatGPT and Claude take completely opposite approaches to memory — one always injects, the other retrieves on demand. Even more surprising, Agent CLI tools like Claude Code, Codex, and Gemini have memory implementations far simpler than expected — no RAG, no knowledge graphs, just plain sliding windows. This article covers open-source frameworks, vector databases, coding assistants, and the real state of production deployment.

Covers: **open-source memory frameworks** (Mem0/Letta/Graphiti), **vector databases** (Qdrant/Chroma), **coding assistants** (Cursor/Augment/Continue), **ChatGPT and Claude memory reverse engineering**, **Agent CLI analysis**, and **production deployment reality**.

---

## 1. Memory Frameworks: Three Technical Approaches

Current mainstream memory frameworks represent three distinct technical philosophies:

### Mem0: LLM-Driven CRUD

Mem0's core idea is using large models to manage memory CRUD operations. It extracts facts from conversations and lets the model judge which version is more trustworthy when conflicts arise.

**Production validation**: Mem0 has become the official memory provider for AWS Agent SDK, with real commercial cases (Sunflower healthcare, RevisionDojo education). This proves the value of "simple but effective" in production environments.

### Letta: Three-Tier Memory + Self-Editing

Letta (formerly MemGPT) designed an OS-like three-tier architecture:
- **Core Memory**: Core facts placed in the system prompt
- **Recall Memory**: Vector retrieval of conversation history
- **Archival Memory**: Long-term knowledge storage

What makes it unique is letting the agent decide when to update its own memory. Already adopted by 11x (sales AI) and Kognitos (enterprise automation).

### Graphiti: Bi-Temporal Knowledge Graph

Graphiti, from the Zep team, introduces a temporal dimension — tracking not just "when we learned it" (transaction_time) but also "when the fact itself occurred" (valid_time).

This solves the state change problem: "user lived in Beijing last year" and "user lives in Shanghai now" are both true, but traditional systems struggle to preserve both simultaneously.

---

## 2. Vector Databases: Two Positions

### Qdrant: Balancing Performance and Features

Qdrant pursues "supporting complex filtering while maintaining recall quality": filtrable HNSW indexing, sparse vector support, RRF/DBSF hybrid ranking.

In production, a common Redis + Qdrant dual-layer architecture emerges: Redis for hot data and fast access, Qdrant for cold data and semantic retrieval.

### Chroma: Developer Experience First

Chroma chose extreme developer experience — its pre-filtering mechanism and clean API make prototyping very smooth. Currently undergoing a Rust v1.0 rewrite, catching up on the "performance" front.

---

## 3. Coding Assistants: Memory in Practice

### Cursor: Learning from User Behavior

Cursor uses agent session trace data to train its own embedding model. Its vector representations are specialized for "code understanding" scenarios, not general text.

### Augment: Real-Time Incremental Indexing

Augment focuses on "real-time" — monitoring edit events and dynamically updating a personal code index. According to public data, this delivers a 2.6% quality improvement.

### Continue: Open Architecture

Continue chose the BYOM (Bring Your Own Model) approach, paired with content-addressed caching. More framework than product, suited for customization needs.

---

## 4. Consumer Product Reverse Engineering: ChatGPT vs Claude Memory

Through reverse engineering analysis of request patterns and system behavior, it was found that ChatGPT and Claude adopt **fundamentally different memory architectures** — representing two opposing design philosophies.

### ChatGPT: Pre-Computed Injection (Passive Memory)

ChatGPT's memory is an "always inject" model:

- **Storage**: ~33 fact summaries + recent conversation summaries
- **Injection timing**: Automatically included at the start of every conversation, invisible to users
- **Update mechanism**: Background async extraction, no impact on conversation latency

**Design philosophy**: Sacrifice context space for simplicity and reliability. Users don't need to wait for retrieval — memory "naturally" exists in the conversation.

**Trade-offs**:
- Pros: Low latency, smooth experience, simple implementation
- Costs: Fixed context window consumption, limited memory capacity

### Claude: On-Demand Retrieval (Active Memory)

Claude implements memory as **explicit tool calls**:

- **Tool interfaces**: `conversation_search` (semantic search of history), `recent_chats` (recent conversation list)
- **Trigger timing**: Invoked only when the model determines it's needed; user sees "searching memory"
- **Retrieval scope**: Can span longer time ranges of conversation history

**Design philosophy**: On-demand retrieval, precise matching. Only consume resources when truly needed.

**Trade-offs**:
- Pros: Saves tokens, theoretically supports larger-scale memory
- Costs: Increased latency, depends on model correctly judging when memory is needed

### The Essential Difference

| Dimension | ChatGPT (Passive) | Claude (Active) |
|-----------|-------------------|-----------------|
| Memory trigger | Auto-injection | Tool call |
| User perception | Invisible | Visible "searching" |
| Context usage | Fixed cost | On-demand cost |
| Latency | Low | Increases during retrieval |
| Capacity limit | Limited by injection volume | Theoretically larger |
| Implementation complexity | Low | High |

This is not just a technical choice — it reflects **product philosophy**: ChatGPT pursues "seamless experience," Claude pursues "transparent control."

---

## 5. Agent CLI Tools: Surprisingly Simple

After studying the implementations of Claude Code, Codex, and Gemini CLI, I found a striking phenomenon: **these tools' "memory" approaches are far simpler than expected**.

| Tool | Storage Format | Compression Method |
|------|---------------|-------------------|
| Claude Code | JSONL | Plaintext summary |
| Codex | JSONL | Encrypted JWT compression |
| Gemini | Server-side | New session file per compression |

**Key finding**: No complex RAG pipelines, no knowledge graphs — just plain sliding windows + summary compression. This stands in stark contrast to the various advanced approaches discussed in academic papers.

---

## 6. Production Deployment Status

### Consumer Products: Memory Features Live

ChatGPT and Claude have both officially launched memory features that users can experience in daily conversations:

| Product | Memory Mode | Core Feature |
|---------|------------|-------------|
| ChatGPT | Passive injection | 33 fact summaries, seamless experience |
| Claude | Active retrieval | Tool calls, transparent control |

This marks: **memory features are transitioning from experimental to standard**.

### B2B Frameworks: Vertical Deployment

| Framework | Deployment Cases | Characteristics |
|-----------|-----------------|----------------|
| Mem0 | AWS Agent SDK, Sunflower, RevisionDojo | Simple approaches deploy first |
| Letta | 11x, Kognitos | Complex stateful agents |
| Graphiti | Zep AI platform core | Temporal knowledge graph |

### Enterprise Common Architecture

Most enterprises (Walmart, JP Morgan, etc.) don't use a single framework but build **dual-layer memory architecture**:

- **Hot layer (Redis)**: Recent 10-20 conversation turns, fast access
- **Cold layer (Vector DB)**: Semantic retrieval of historical conversations

### Dual Purpose of Vector Databases

An easily confused point: vector databases are used not just for RAG (searching documents to answer questions) but also for **conversation memory** (searching past conversations to remember who the user is). Twilio, Aquant, and OpenAI all use this approach.

---

## 7. Summary

### Technical Level

Memory systems are evolving from "vector retrieval" to "structured + lifecycle management." The core problems are clear: **what to extract, how to store, when to retrieve, how to update**. But the optimal solution is far from settled — fact extraction, graph structures, and temporal modeling each have their advocates.

### Business Level

Memory capability has become a core competitive differentiator:

- **Consumer products**: ChatGPT and Claude have made memory a standard feature
- **B2B frameworks**: Mem0's AWS partnership proves the commercial value of memory
- **Developer tools**: Cursor/Augment use memory to improve code understanding and developer retention

**The reality**: Consumer side is live (ChatGPT/Claude), B2B is still in early exploration. True long-term memory and cross-session learning still have a long way to go.

### Observations

The most surprising finding: **production-grade CLI tools universally adopt simple approaches**. This might indicate:

1. Simple approaches are sufficient for current scenarios
2. The marginal benefit of complex approaches doesn't cover their cost
3. Or, better memory systems are the next competitive frontier

Memory is the key capability that transforms LLMs from "tools" into "assistants." The technology stack is still evolving rapidly and is worth continued attention.

---

## Resources

Based on open-source code analysis and product reverse engineering. Full research materials:

- [Mem0 Research](mem0.research.md)
- [Letta Research](letta.research.md)
- [Graphiti Research](graphiti.research.md)
- [ChatGPT Memory Reverse Engineering](reverse-engineer/chatgpt-memory-reverse-engineering.md)
- [Claude Memory Reverse Engineering](reverse-engineer/claude-memory-reverse-engineering.md)
- [Agent CLI Session File Analysis](agent-cli/agent-files-analysis.md)
- [Production Adoption Research](production-adoption.research.md)

---

*Research period: December 2025*
