# LLM Agent 信息管理：研究总结

Last Updated: 2026-03-24

对 20+ 个项目的综合研究，涵盖 LLM Agent 如何管理信息——从 Memory 框架、Context 管理到 Continuous Learning 的前沿。

---

## 0. 两个分析角度

本研究从两个互补的角度审视 LLM Agent 信息管理。

### 角度一：三种方法——Agent 如何处理信息

| 方法 | 作用 | 成熟度 |
|------|------|--------|
| **Compression** | 压缩信息以适应约束——摘要、事实提取、截断 | 生产就绪，普遍部署 |
| **Retrieval** | 从更大的信息池中选取相关信息——向量搜索、文本搜索、图遍历 | 生产就绪，方案差异大 |
| **Learning** | 将知识写入模型权重，无需外部存储即可持久化 | 研究前沿，无生产部署 |

### 角度二：三个研究方向——Agent 在哪里应用这些方法

| 方向 | 时间尺度 | 研究状态 |
|------|---------|---------|
| **Memory** | 跨会话——在对话之间持久化知识 | 已研究 15 个项目 |
| **Context** | 会话内——在对话过程中管理 context window | 已研究 7 个 Agent + Anthropic 官方指南 |
| **Learning** | 部署后——训练完成后适应模型权重 | 计划已写，尚未开始 |

Part 1-3 按三个研究方向展开。Part 4 讨论只有同时研究 Memory 和 Context 才能发现的跨域洞察。

---

## 1. Memory：跨会话的知识持久化

### 1.1 消费级产品的 Memory：两种哲学

对 ChatGPT 和 Claude 的逆向工程揭示了两种截然相反的方案。（[ChatGPT 详情](./reverse-engineer/chatgpt-memory-reverse-engineering.md) | [Claude 详情](./reverse-engineer/claude-memory-reverse-engineering.md)）

| | ChatGPT | Claude |
|--|---------|--------|
| **策略** | 全量预注入 | 按需检索 |
| **机制** | 33 条预计算事实 + 近期聊天摘要，始终在 context 中 | `conversation_search` 和 `recent_chats` 工具，按需调用 |
| **权衡** | 固定 token 开销，自动连续性 | 可变开销，有遗漏相关信息的风险 |

两者在运行时都不使用向量数据库或 RAG——都依赖比预期更简单的方案。

### 1.2 Memory 框架：两代演进

#### 第一代（2024-2025）：基础方案

| 框架 | 核心思路 | 差异化特点 | 生产采用 |
|------|---------|-----------|---------|
| [**Mem0**](./mem0.research.md) | LLM 驱动的事实 CRUD | LLM 决定对 atomic facts 执行 ADD/UPDATE/DELETE；双存储（vector + graph） | AWS Agent SDK 官方供应商 |
| [**Letta**](./letta.research.md) | 三层自编辑 Memory | Agent 自主写入 prompt（Core/Recall/Archival）；主动而非被动 | 11x 销售 AI、Kognitos |
| [**Graphiti**](./graphiti.research.md) | 双时态知识图谱 | Entity 和 Relationship 带时间有效性；图遍历检索 | Zep AI (YC)，21.2k stars |

与传统 RAG 的关键区别：三者都使用**主动 Memory 管理**——由 LLM 决定存储和删除什么，而非被动地对文档分块。（[生产落地详情](./production-adoption.research.md)）

#### 第二代（2026 Q1）：新浪潮

| 系统 | 核心创新 | LongMemEval |
|------|---------|-------------|
| [**Hindsight**](./hindsight.research.md) | 四个 Memory Network（World/Experience/Observation）+ reflect 操作；多策略检索（graph + BM25 + vector） | 91.4% |
| [**Mastra OM**](./mastra.research.md) | 纯压缩，**无检索**——Observer + Reflector agent 将所有信息压缩进 context | 94.87% |
| [**MemOS**](./memos.research.md) | Memory 作为 OS 资源；MemCube 统一三种类型（plaintext、KV-cache、weights） | N/A |
| [**Supermemory**](./supermemory.research.md) | ASMR：LLM-as-retriever 替代向量数据库；3+3 agent pipeline + ensemble voting | 98.6%（oracle） |

代际转变揭示两个关键趋势：**LLM-as-retriever** 替代向量搜索（Supermemory），以及**纯压缩**作为完全替代 Retrieval 的可行方案（Mastra OM——94.87% 的得分且零检索，挑战了"Retrieval 是必需的"这一假设）。

### 1.3 编程助手的 Memory

一个不同的领域，这里的 Memory 意味着"理解代码库"：

| 助手 | 核心创新 |
|------|---------|
| [**Cursor**](./cursor.research.md) | 从 agent session traces 训练的自定义 embedding 模型 |
| [**Augment**](./augmentcode.research.md) | 按开发者实时构建个人索引；edit event streaming（+2.6% 提升） |
| [**Continue**](./continue.research.md) | BYOM 架构 + content-addressed caching |

完整的市场概览（包括向量数据库 Qdrant/Chroma、图数据库、embedding 模型）见 [memory.ecosystem.md](./memory.ecosystem.md)。

---

## 2. Context：管理对话窗口

### 2.1 通用模式

所有 7 个研究对象共享同一基础模型：（[完整对比](./context.summary.md)）

```
消息累积 → 达到阈值 → 压缩/摘要 → 带着摘要继续
```

差异在于压缩**何时**、**如何**、**在哪里**发生。

### 2.2 架构光谱

| Agent | 核心特征 | 细节 |
|-------|---------|------|
| [**Pi**](./pi.research.md) | 极简 | 接近上限时单次 LLM 摘要；~300 词 system prompt；无预处理 |
| [**Codex**](./codex-context.research.md) | 逐项截断 | 记录时每条 tool output 限 10KB；双重 compaction（server 加密 + client LLM） |
| [**Gemini CLI**](./gemini-cli.research.md) | 验证式压缩 | LLM 摘要 + 第二次 LLM probe 捕捉遗漏；50% 阈值 |
| [**OpenCode**](./opencode.research.md) | 两阶段 | 先裁剪旧 tool outputs，再 LLM 摘要；可恢复的 sub-agents；fork/revert |
| [**Claude Code**](./claude-code-context.research.md) | 服务端 + 模型感知 | API compaction 生成 9 段摘要；模型知道剩余预算（`<budget:token_budget>`） |
| [**OpenClaw**](./openclaw.research.md) | 多阶段流水线 | sanitize → validate → truncate → assemble；可插拔 ContextEngine 含 7 个生命周期钩子 |

### 2.3 关键设计模式

这些模式揭示了一个共同趋势：**压缩的责任正从客户端启发式规则转向服务端 API 和模型自管理**。

**Reactive → Proactive Compression** — 大多数 Agent 等到 context 接近满时才压缩。例外：Codex 在入口逐项截断，Gemini CLI 预摘要 tool outputs。更早、更轻量的压缩降低了单次灾难性信息丢失的风险。

**Client-Side → Server-Side Compaction** — Claude Code（`compact-2026-01-12`）和 Codex（`/responses/compact`）将 compaction 卸载到服务端 API。这使得加密状态保存、流中压缩和更简单的客户端实现成为可能。

**Model Self-Management** — Claude Code 的 `<budget:token_budget>` 让模型感知剩余容量。结合服务端 compaction，模型可以自主管理而无需客户端启发式规则。目前没有其他 Agent 具备此特性——这可能代表了所有 Agent 最终的收敛方向。

**Context Rot** — Anthropic 识别了四种 context 退化类型：poisoning（过时信息）、distraction（无关信息）、confusion（相似信息）、clash（矛盾信息）。大多数 Agent 仅处理 distraction，其余三种基本无缓解措施。（[Anthropic 指南详情](./anthropic-context-engineering.research.md)）

---

## 3. Learning：将知识写入权重（TODO）

第三种方法，也是第三个研究方向。目前**没有生产级 Agent** 使用权重更新做个性化——全部依赖外部 Memory（Compression + Retrieval）。

研究计划涵盖四个方向：（[完整计划](./plan/2-learning-research.md)）

| 方向 | 内容 | 状态 |
|------|------|------|
| 学术综述 | Continual learning、catastrophic forgetting、self-evolving LLMs | TODO |
| 按用户个性化 | Multi-LoRA serving、Sakana Doc-to-LoRA、DoorDash 生产案例 | TODO |
| VTuber / Character AI | Neuro-sama（权重嵌入人格）vs prompt 构造人格 | TODO |
| 混合流水线 | 积累外部 Memory → 批量 LoRA fine-tune → 部署 | TODO（探索性） |

核心问题：**Per-user LoRA 是否是 prompt injection 和 full fine-tuning 之间可行的折中方案？**

---

## 4. 跨域发现

只有同时研究 Memory 和 Context 才能看到的发现。（[完整的 10 项详细分析](./findings.md)）

### Memory 和 Context 是不同时间尺度上的同一个问题

Compaction 就是 Memory 的创建过程。当 Claude Code 在 compaction 中生成 9 段摘要时，它在创建对话的"记忆"。当 Mem0 提取事实时，它在把对话"压缩"进持久存储。方法（Compression、Retrieval）是共通的，只是时间尺度不同。一个领域的技术应当能迁移到另一个领域。

### 两种哲学同时出现在两个领域

"全量给出，信任模型"（ChatGPT 预注入所有事实；Pi 发送完整历史）vs "激进筛选，减少噪声"（Claude 按需检索；OpenClaw 的多阶段流水线）。两者没有绝对优劣。随着 context window 增长（1M+），天平向"信任模型"倾斜——但 context rot（§2.3）又把它推回来。这个张力尚未解决。

### 压缩质量是共有的未解问题

每个做压缩的系统——无论是 Memory 提取（Mem0 丢失细微差别）还是 Context compaction（Pi 的未验证摘要）——都面临无声信息丢失的风险。没有系统能可靠地知道丢失了什么。Gemini CLI 的 two-pass probe（§2.2）是唯一的验证尝试，但它使成本翻倍。

### 图结构在 Context 中尚未被探索

Graphiti 的双时态知识图谱是 Memory 领域的突破（§1.2）。在 Context 管理中，没有 Agent 使用图结构——全部使用线性消息数组。没有人追踪 tool calls 之间的因果关系，或用户意图在对话中如何演变。

### Text Search 在 Agentic Loop 中压倒 RAG

所有研究的编程 Agent 在运行时都使用 `grep`/`glob`（文本搜索），而非向量搜索。原因：零索引成本、精确匹配、始终最新、可解释。RAG 出现在 Memory 层（跨会话检索），但不出现在实时 Agent 操作中。这表明 RAG 的价值在于**知识库检索**，而非**Agentic 执行**。（[完整分析](./findings.md#finding-10-text-search-dominates-over-rag-in-practice)）

### Sub-Agent 是一种压缩策略

Sub-agent 作为 Context 管理技术出现：给一个专注任务分配独立的干净 context window，返回压缩后的摘要。这与 Memory 提取是同一模式——获取原始经验，提炼它，只存储提炼结果。设计 sub-agent 边界本质上是一个压缩设计问题。

---

## 5. 开放问题

### Compression
- **验证**：能否构建比 Gemini CLI 的 two-pass probe 更低成本的替代方案？
- **最优阈值**：Pi 在接近上限时压缩，Gemini CLI 在 50% 时。最优点在哪？
- **加密 vs 可读**：Codex 保存不透明的模型状态；Claude Code 生成可读的 9 段文本。哪个丢失更少？

### Retrieval
- **图结构用于 Context**：基于图的 context 表示（§4）能否产生比线性摘要更好的压缩？
- **LLM-as-retriever**：Supermemory 的 ASMR 用 LLM 推理替代向量数据库。可行方向，还是成本过高？
- **Prompt placement**：没有 Agent 验证过规则放在 system prompt 还是 user message 中是否影响质量。不存在 A/B 测试。

### Learning
- **基于权重的 Memory**：Per-user LoRA 是否可行？更新周期和存储成本如何？
- **混合流水线**：Agent 能否积累外部 Memory，然后定期 fine-tune 到权重中？
- **人格边界**：Fine-tuning 在什么节点能产生 prompt engineering 无法复现的效果？

---

## 研究材料

### 各项目研究文档

| 类别 | 项目 |
|------|------|
| Memory 框架（第一代） | [Mem0](./mem0.research.md)、[Letta](./letta.research.md)、[Graphiti](./graphiti.research.md) |
| Memory 框架（第二代） | [Hindsight](./hindsight.research.md)、[Mastra OM](./mastra.research.md)、[MemOS](./memos.research.md)、[Supermemory](./supermemory.research.md) |
| 向量数据库 | [Qdrant](./qdrant.research.md)、[Chroma](./chroma.research.md) |
| 编程助手 | [Cursor](./cursor.research.md)、[Augment](./augmentcode.research.md)、[Continue](./continue.research.md) |
| Context 管理 | [Pi](./pi.research.md)、[OpenClaw](./openclaw.research.md)、[Gemini CLI](./gemini-cli.research.md)、[Claude Code](./claude-code-context.research.md)、[Codex](./codex-context.research.md)、[OpenCode](./opencode.research.md) |
| 逆向工程 | [ChatGPT Memory](./reverse-engineer/chatgpt-memory-reverse-engineering.md)、[Claude Memory](./reverse-engineer/claude-memory-reverse-engineering.md) |
| 官方指南 | [Anthropic Context Engineering](./anthropic-context-engineering.research.md) |

### 总结文档

| 文档 | 范围 |
|------|------|
| [findings.md](./findings.md) | 跨域发现（10 项发现，详细分析） |
| [context.summary.md](./context.summary.md) | Context 管理对比（6 个 Agent，模式，开放问题） |
| [memory.summary.md](./memory.summary.md) | Memory 研究总结（Phase 1：2025-12） |
| [memory.ecosystem.md](./memory.ecosystem.md) | 市场概览（GitHub stars、融资、选型指南） |

### 计划

| 文档 | 状态 |
|------|------|
| [plan/1-context-research.md](./plan/1-context-research.md) | 已完成 |
| [plan/2-learning-research.md](./plan/2-learning-research.md) | TODO（4 个研究方向已规划） |
| [plan/3-memory-update.md](./plan/3-memory-update.md) | 研究已完成，总结待写 |
