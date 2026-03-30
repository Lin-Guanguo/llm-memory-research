# 6 个主流 Agent 的上下文管理与记忆系统深度对比

## 我读了 6 个 Agent 的源码，找到了"养虾"和"记忆"背后的秘密

Last Updated: 2026-03-30

> **OpenClaw** 养虾为什么越来越懂你？**Claude Code** 编码为什么体感最强？我读了 **6 个 Agent 的源码**，发现答案在**上下文管理**和**记忆系统**的实现里。本文以 OpenClaw 为主线，横向对比 Claude Code、Codex、Gemini CLI 等的实现差异。
>
> 我的终极目标是让 AI **不需要我介入就能干活**、像合作已久的伙伴一样**理解我**——但从研究来看，离这个目标还有距离。

---

## 一、OpenClaw 记忆分析

OpenClaw 是我研究过的所有编程 Agent 中，**唯一一个拥有真正记忆系统的**。

先看看其他 Agent 的"记忆"是什么样的：

| Agent | "记忆" | 搜索 | 索引 |
|-------|-------|------|------|
| Claude Code | `CLAUDE.md` + `MEMORY.md` | 无（整个文件直接加载） | 无 |
| Codex | `AGENTS.md` | 无 | 无 |
| Gemini CLI | `GEMINI.md` | 无 | 无 |
| OpenCode | `AGENTS.md` + `CLAUDE.md` + `CONTEXT.md` | 无 | 无 |
| Pi | 无 | 无 | 无 |

它们的"记忆"就是启动时加载一个纯文本文件。没有搜索，没有索引，没有时间感知。你的 `CLAUDE.md` 是 200 行？加载。2000 行？也加载（然后吃掉你的上下文窗口）。

OpenClaw 完全不同。

### 两层存储：每日日志 + 长青知识

OpenClaw 的记忆是**纯 Markdown 文件**——文件本身就是事实来源，SQLite 索引是派生的，可以重建。

```
~/.openclaw/workspace/
├── MEMORY.md              ← 长青知识：经过筛选的持久信息，永不衰减
├── memory/
│   ├── 2026-03-30.md      ← 今天的日志：只追加
│   ├── 2026-03-29.md      ← 昨天的日志
│   ├── projects.md        ← 长青知识：按主题组织
│   └── network.md         ← 长青知识：按主题组织
```

设计很有讲究：
- **每日日志**（`memory/YYYY-MM-DD.md`）是 append-only 的，每天一个文件，记录当天的对话发现和决策
- **长青知识**（`MEMORY.md` 和 `memory/` 下的非日期文件）是经过筛选的持久信息——你的偏好、项目决策、参考资料
- 只有今天和昨天的日志在会话启动时加载，其他的按需通过搜索检索

这模拟了人类记忆的两种模式：短期记忆（今天发生了什么）和长期记忆（我知道的重要事实）。

### 四阶段检索管道

当模型需要回忆时，它调用 `memory_search` 工具，触发一个四阶段检索管道——这是正经的信息检索（IR）工程，不是简单的文件加载：

```
查询
  │
  ├─► 向量搜索 (cosine similarity, 支持 6 种 embedding 提供商)
  │
  ├─► BM25 关键词搜索 (FTS5 全文检索)
  │
  ▼
加权融合 (默认 0.7 × 向量 + 0.3 × 关键词)
  │
  ▼
时间衰减 (指数衰减，30 天半衰期)
  │
  ▼
MMR 重排序 (多样性感知去重)
  │
  ▼
Top-K 结果
```

**向量 + 关键词并行搜索**——向量搜索捕捉语义相似性，BM25 捕捉精确关键词匹配，两者并行执行后加权融合。这比纯向量搜索或纯关键词搜索都更鲁棒。

**时间衰减**——这是其他 Agent 完全没有的维度。衰减公式是 `score × e^(-λ × ageInDays)`，30 天半衰期：

| 时间 | 得分衰减 |
|------|---------|
| 今天 | 100% |
| 7 天前 | ~84% |
| 30 天前 | 50% |
| 90 天前 | 12.5% |
| 180 天前 | ~1.6% |

关键细节：长青知识（`MEMORY.md` 和非日期文件）**永不衰减**。这意味着"你喜欢用 Vim"这样的偏好始终满分，而"上周二的调试记录"会自然淡出——和人类记忆的运作方式一样。

**MMR 重排序**（Maximal Marginal Relevance）——日志里每天可能记录类似的内容，MMR 确保结果多样性，不会返回 5 条差不多的记录。

### 杀手特性：Pre-Compaction Memory Flush

这是我在所有 Agent 中发现的**最有架构意义的设计**。

每个 Agent 都会在上下文快满时做压缩（compaction）——用 LLM 生成摘要，然后丢掉原始对话。问题是：压缩时必然丢失信息。那些对当前任务不重要、但对你这个人很重要的信息——比如你提到的偏好、做出的决策——就这么消失了。

OpenClaw 的做法是：在压缩**之前**，注入一个用户不可见的静默 turn，提醒模型："你即将失去上下文。现在把重要的东西写进 `memory/YYYY-MM-DD.md`。"

```
会话运行中...
  → Token 数量越过阈值
  → 静默系统提示："会话即将压缩。立即保存持久记忆。"
  → 模型将重要上下文写入每日日志（或回复 NO_REPLY 表示无需保存）
  → 压缩继续——上下文被压缩，但记忆已安全落盘
```

触发条件有两个（满足任一即可）：
- **Token 阈值**：总 token 数接近上下文窗口上限
- **转录体积**：会话转录超过 2MB

安全保障也做得细致：
- 只允许写入 `memory/YYYY-MM-DD.md`，MEMORY.md 等文件在 flush 期间是只读的
- 如果文件已存在，只追加不覆盖
- 一次压缩周期最多触发一次 flush

**这就是"养虾"体感的技术根源**——OpenClaw 在你不知道的时候，持续地把对你的了解从易逝的上下文窗口搬运到持久的记忆文件中。用得越久，它存下的关于你的信息越多，检索越精准。其他 Agent 的每次会话都是从零开始；OpenClaw 的每次会话都站在之前所有会话的肩膀上。

---

## 二、OpenClaw 上下文分析

记忆让 OpenClaw 在跨会话层面独特，而它的上下文管理在单次会话层面同样是最复杂的。

### 通用模式

先说结论：所有 Agent 都共享同一个基础模式：

```
消息累积 → 达到阈值 → 压缩/摘要 → 用摘要继续
```

差异在于**何时**、**如何**以及**在哪里**执行压缩。OpenClaw 在这三个维度上都做得最复杂。

### ContextEngine：可插拔的上下文组装

OpenClaw 的上下文管理核心是 ContextEngine——一个可插拔的接口，定义了 7 个生命周期方法：

| 方法 | 用途 |
|------|------|
| `bootstrap()` | 初始化引擎状态，导入历史上下文 |
| `ingest()` | 接收单条消息到引擎存储 |
| `ingestBatch()` | 批量接收一个完整 turn |
| `afterTurn()` | turn 结束后的生命周期（持久化、触发后台压缩） |
| `assemble()` | **核心：在 token 预算下组装模型上下文** |
| `compact()` | 压缩上下文（摘要、裁剪等） |
| `prepareSubagentSpawn()` | 子 Agent 启动前准备引擎状态 |
| `onSubagentEnded()` | 子 Agent 结束后通知引擎 |

默认的 LegacyContextEngine 基本是直通（pass-through），但这个接口的价值在于：第三方插件可以完全替换上下文策略——RAG 管道、向量存储、图结构上下文，都可以接入。

### 每次 LLM 调用前的管道

OpenClaw 不是把消息原样丢给 LLM。每次调用前，消息要经过一条多阶段管道：

```
原始对话历史
    │
    ▼ sanitizeSessionHistory()        ← 清洗：移除无效工具结果，修复配对
    │
    ▼ validateGeminiTurns()           ← 按 provider 校验（Gemini 规则）
    ▼ validateAnthropicTurns()        ← 按 provider 校验（Anthropic 规则）
    │
    ▼ limitHistoryTurns()             ← 按配置截断轮次（DM/频道各有上限）
    │
    ▼ sanitizeToolUseResultPairing()  ← 截断后修复孤立的工具结果
    │
    ▼ contextEngine.assemble()        ← 在 token 预算下组装上下文
    │
    ▼ 发送给 LLM
```

### 三道防线

对比 Pi 只有一道防线（上下文满了才压缩），OpenClaw 在压缩触发前就有三层削减：

| 防线 | 机制 | 成本 |
|------|------|------|
| 第一道 | `limitHistoryTurns()` — 按轮次硬截断 | 极低 |
| 第二道 | `contextEngine.assemble()` — token 预算感知组装 | 取决于引擎 |
| 第三道 | Compaction — LLM 生成摘要 | 高（继承自 Pi） |

这意味着很多情况下，OpenClaw 通过轻量的前两道防线就控制住了上下文体积，避免触发昂贵的 LLM 压缩。

### Provider 感知

一个容易忽略的细节：OpenClaw 针对不同 LLM 提供商做消息格式校验。Gemini 要求严格的交替 turn，Anthropic 有自己的 turn 规则。OpenClaw 在发送前自动适配，而 Pi 对所有 provider 发送完全一样的格式。

### 子 Agent：双向通信

OpenClaw 的子 Agent 通过 gateway RPC 运行，和其他 Agent 的最大区别是**双向通信**：

```
主 Agent
  │
  ├─ sessions_spawn({ task: "...", agentId: "worker" })
  │     ├─ 子 Agent 在独立会话中运行
  │     ├─ 完成后自动推送结果给父 Agent（push，不是轮询）
  │
  └─ 父 Agent 还可以：
     sessions_send()   → 给子 Agent 发消息（中途引导）
     sessions_history() → 读子 Agent 的对话历史
     subagents(action=steer|kill) → 干预或终止
```

其他 Agent 的子 Agent 都是单向的——派出去，等结果回来，没法中途引导。OpenClaw 的父 Agent 可以在子 Agent 运行过程中发送指令、读取进度，甚至直接终止。

### 系统提示词

OpenClaw 的系统提示词由 15+ 个段落组成，包括身份、工具列表、安全规则、记忆检索指令、子 Agent 编排、语音 TTS 提示等。有三种模式：
- `full` — 全部段落（主 Agent）
- `minimal` — 精简版（子 Agent）
- `none` — 仅身份行

---

## 三、其他 Agent 怎么做上下文管理

以下按复杂度从简到繁排列。

### Pi — 基线方案

Pi 是 OpenClaw 的底层引擎，也是所有 Agent 中最简单的。

- 无限累积，每次 LLM 调用发送**全部**上下文
- 系统提示词约 300 字
- 不做预处理，不做 token 预算
- 接近上限时做一次 LLM 摘要（6 段结构）
- 能跑是因为 1M 上下文窗口够宽容

Pi 证明了一件事：如果上下文窗口足够大，"不做上下文管理"也是一种可行的策略。

### Codex — 写入时截断 + 双重压缩

Codex 是唯一用 Rust 写的 Agent，有两个独特设计：

**写入时截断**：每条工具输出在进入上下文**之前**就被截断到 10KB。这是主动压缩——在信息累积的源头就控制了体积，而不是等到快满了再处理。

**双重压缩**：
- 使用 OpenAI 时：服务端加密压缩，返回不透明的 compaction block，保留模型内部状态
- 使用其他 provider 时：客户端 LLM 摘要，4 段结构化模板

Codex 还支持**中途压缩**——模型还在生成时就可以触发压缩。这在其他 Agent 中没有见过。

### Gemini CLI — 唯一验证压缩质量的

Gemini CLI 有一个其他 Agent 都没做的事：**验证压缩结果**。

生成摘要后，它会跑第二次 LLM 调用（"探针"），检查是否丢失了重要信息。如果探针发现遗漏，会补充到摘要中。成本翻倍，但能捕捉无声的信息丢失。

其他特点：
- 在 50% 容量就触发压缩——远比其他 Agent 激进（Claude Code 约 80%，Pi 接近上限）
- 大块工具输出在进入上下文前就预先摘要（类似 Codex 的主动压缩思路，但用 LLM 而非硬截断）

### OpenCode — 两阶段压缩 + fork/revert

OpenCode 的压缩分两步：
1. **规则裁剪**：先用程序规则删除旧的工具输出（便宜）
2. **LLM 摘要**：再用 LLM 摘要剩余内容（昂贵）

先便宜后昂贵，合理。

独特之处在于**文件系统感知的 fork/revert**——你可以给对话分叉，就像 git branch。走错了方向可以 revert 回来。子 Agent 基于独立 SQLite 会话，可以暂停后恢复。

### Claude Code — 为什么编码体感最强

Claude Code 的编码体感公认最好，子 Agent 又快又稳。核心原因不在某个特定的架构创新，而在于**Prompt Engineering 做到了极致**。

**65+ 模块化系统提示词 + 20+ 动态注入**：这是 Claude Code 编码体感强的核心。它的系统提示词不是一个大文件，而是 65+ 个模块化文件按需组装，覆盖了编码工作的方方面面——安全检查、文件修改规范、git 操作流程、输出效率要求、代码风格约束等。更关键的是 20+ 个 system-reminder 模板在运行时动态注入——文件被外部修改了？注入提醒。技能激活了？注入指令。文件内容太长被截断了？注入说明。这让模型始终掌握最新的上下文状态，做出最合适的决策。

**工具最丰富**：Claude Code 提供的工具覆盖面最广——文件读写、搜索、编辑、Bash 执行、Notebook 编辑、LSP 支持等。工具多意味着模型有更多手段完成任务，不需要绕弯路。

**6+ 种子 Agent，每种都有针对性的 prompt**：

| 子 Agent | 用途 | 特调重点 |
|---------|------|---------|
| Explore | 只读代码搜索 | 快速搜索，只读工具 |
| Plan | 架构规划 | 只读工具，聚焦设计 |
| Code Reviewer | 代码审查 | 审查标准和输出格式 |
| Code Explorer | 深度特性分析 | 追踪执行路径 |
| Code Architect | 特性架构设计 | 蓝图输出格式 |

子 Agent 管理好，本质上也是 prompt 特调的功劳——每种子 Agent 都有精心设计的系统提示词和工具集，确保它在自己的职责范围内表现最优。这不是架构优势，而是在 prompt 层面投入了大量工程努力。

**特色功能（非编码核心，但值得了解）**：
- **服务端压缩**：唯一把压缩完全交给服务端 API 的 Agent，客户端代码最简单
- **模型知道自己的剩余预算**：通过 `<budget:token_budget>` 标签，Claude 4.5+ 模型实时知道上下文使用情况，可以自我调节
- **Thinking block 自动清理**：扩展思维 token 在下一轮自动移除，不污染上下文

### 六个 Agent 对比一览

| Agent | 压缩触发 | 压缩位置 | 验证 | 子 Agent | 记忆 |
|-------|---------|---------|------|---------|------|
| Pi | 接近上限 | 客户端 | 无 | 进程隔离（单向） | 无 |
| Codex | 可配置 | 服务端+客户端 | N/A | 无 | `AGENTS.md` |
| Gemini CLI | 50% 容量 | 客户端 | **二次探针** | 进程内（单向） | `GEMINI.md` |
| OpenCode | 可用上限 | 客户端两阶段 | 无 | 会话级（可恢复） | `AGENTS.md` 等 |
| Claude Code | ~80% 容量 | **服务端 API** | 无 | **6+ 种（精细特调 prompt）** | `CLAUDE.md` 等 |
| OpenClaw | 同 Pi | 客户端/自定义引擎 | 取决于引擎 | **Gateway RPC（双向）** | **四阶段检索管道** |

---

## 四、洞察对比

### 记忆和上下文是同一个问题

研究了这么多 Agent 之后，我得出的核心结论是：**记忆和上下文不是两个独立的问题——它们是同一个问题在不同时间尺度上的表现。**

| | 记忆（跨会话） | 上下文（会话内） |
|--|--------------|----------------|
| 保留什么 | 事实提取（Mem0）、实体追踪（Graphiti） | 压缩摘要（所有 Agent） |
| 丢弃什么 | 过期事实、冲突信息 | 旧工具输出、已解决的错误 |
| 如何压缩 | LLM 摘要、知识图谱 | LLM 摘要、结构化模板 |
| 如何检索 | 向量搜索、图遍历 | 全量上下文、token 预算、子 Agent |

当 Claude Code 在压缩时生成 9 段结构化摘要，它其实是在创建对话的*记忆*。当 Mem0 从对话中提取事实，它其实是在把对话*压缩*进持久存储。术语不同，工程本质相同。

OpenClaw 的 Pre-Compaction Memory Flush 是唯一在架构层面承认这一点的设计——上下文即将被销毁时，先变成持久记忆。

### 为什么只有 OpenClaw 打通了？

定位决定了架构。

- **Claude Code / Codex / Gemini CLI** 定位为**任务执行器**——你给它一个编程任务，它执行完，会话结束。不需要记住你是谁。
- **OpenClaw** 定位为**个人助手**，恰好擅长写代码——它需要记住你的偏好、你的项目背景、你的工作习惯。

这不是技术能力的差距，是产品选择。Claude Code 有能力做复杂的记忆系统，但它选择不做，因为它的场景不需要。

### 三个技术趋势

**趋势一：从被动压缩到主动压缩。** 大多数 Agent 等到快满了才压缩。Codex 在写入时就截断（10KB 硬限制），Gemini CLI 预先摘要大块输出。规律：**早压缩、小压缩、频繁压缩** 优于 **晚压缩、一次性全压缩**。

**趋势二：从客户端到服务端。** 2025 年所有压缩在客户端。2026 年 Claude Code 和 Codex 都转向了服务端 API。好处：加密状态保存、中途压缩、客户端代码简化。

**趋势三：从人工规则到模型自管理。** Claude Code 是唯一让模型知道自己剩余预算的 Agent。结合服务端压缩，模型可以自我调节。这可能是所有 Agent 的收敛方向——模型管理自己的上下文，客户端只提供原始输入。

### grep 在实践中胜过 RAG

一个可能反直觉的发现：每个编程 Agent 的实时代码搜索都用 `grep`/`glob`——不是向量搜索，不是 RAG。

| 维度 | 文本搜索 (grep/glob) | RAG (向量搜索) |
|------|---------------------|---------------|
| 索引成本 | 零 | 必须预先计算 embedding |
| 精确度 | 精确匹配 `handleAuth` | 可能返回相似但错误的结果 |
| 时效性 | 始终最新 | 索引可能滞后于编辑 |

RAG 出现在记忆层（跨会话检索），不出现在 Agent 操作层。Anthropic 称之为"Agentic Search"——底层就是 grep。

---

## 五、延伸研究与未解决问题

### Context Rot：上下文腐化的四种类型

Anthropic 在其 Context Engineering 指南中识别出四种上下文退化：

| 类型 | 表现 | 谁在应对 |
|------|-----|---------|
| **Poisoning（投毒）** | 文件被修改后，上下文中的工具结果过期了 | 仅 Claude Code（文件修改检测 + system-reminder 注入） |
| **Distraction（干扰）** | 旧的工具输出占用注意力 | Codex, Gemini CLI, OpenCode（截断/裁剪） |
| **Confusion（混淆）** | 两个相似文件导致模型张冠李戴 | 没有人 |
| **Clash（冲突）** | 同一数据的新旧版本共存 | OpenCode fork/revert（部分） |

大多数 Agent 只处理了 Distraction。Confusion 和 Clash 基本无人触及。这是一个值得关注的改进空间。

### 压缩质量：共同的盲区

每个做压缩的 Agent 都面临一个问题：**没人知道压缩丢了什么**。

- Pi：单次摘要，无验证——你永远不知道丢了什么
- Gemini CLI：二次探针检查——唯一的验证尝试，但成本翻倍
- Claude Code：9 段结构化模板——覆盖面广但未经验证
- Codex：服务端加密状态——保留了模型内部信息，但完全不透明

这是记忆和上下文领域共同的未解难题。如果压缩质量可以衡量，所有 Agent 都能显著改进。

### 还有哪些空白？

**最优压缩阈值**——Pi 接近上限才压缩，Gemini CLI 在 50% 就压缩，Claude Code 约 80%。哪个更好？早压缩单次信息损失小但压缩频率高；晚压缩频率低但每次损失大。目前没有定论。

**谁是下一个？** 目前只有 OpenClaw 同时有复杂上下文管理和全局记忆。但如果编程 Agent 逐渐从任务执行器进化为个人助手——趋势表明它们会——记忆就变成刚需。这个空白格不会空太久。

---

## 关于这个系列

我出于个人兴趣在研究 LLM Agent 的三个核心命题：**记忆、上下文、学习**。[上一篇](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/blog.1.chinese.md)研究了记忆系统，这一篇研究了上下文管理。接下来打算更新的文章包括：记忆系统 2026 年的最新进展，以及持续学习的研究。

做这些研究，我想达到两个目的：

**目的一：让 AI 完全在我不介入的情况下替我干活。** 这需要 AI 记住我的一切——我的偏好、项目背景、工作习惯、历史决策。从本文的分析可以看到，目前的框架离这个目标还有距离：大多数 Agent 连基本的跨会话记忆都没有，OpenClaw 是做得最深的，但也仅限于文件级的记忆存储和检索。我之前搭建了一个[个人知识库](https://www.xiaohongshu.com/discovery/item/694386e1000000001e02eaeb)的实践，就是在探索这个方向。

**目的二：一个真正有独立人格的 AI 伙伴。** 通过学习和长期配合，它能发展出独特的性格和做事方法——就像一个合作已久的伙伴，不只是执行指令，而是理解你的思维方式。这主要是第三部分"持续学习"的研究范围，涉及人格训练、Multi-LoRA 个性化、以及 Memory → Weight 的混合管道。

---

## 参考资料

基于源码分析和逆向工程，完整研究材料：

**OpenClaw 研究**：
- [OpenClaw 上下文管理](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/openclaw.research.md) | [OpenClaw 记忆系统](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/openclaw-memory.research.md)

**其他 Agent 上下文研究**：
- [Pi](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/pi.research.md) | [Gemini CLI](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/gemini-cli.research.md) | [Claude Code](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/claude-code-context.research.md) | [Codex](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/codex-context.research.md) | [OpenCode](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/opencode.research.md)
- [Anthropic Context Engineering 指南分析](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/anthropic-context-engineering.research.md)

**综合研究**：
- [研究总结](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/summary.md) | [上下文管理总结](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/context.summary.md) | [跨域发现](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/findings.md)

**上一篇**：[LLM 记忆：设计很复杂，落地出奇简单](https://github.com/Lin-Guanguo/llm-memory-research/blob/main/blog.1.chinese.md)

---

*研究周期：2025-12 至 2026-03。研究了 6 个 Agent（5 个开源 + 1 个逆向工程）、15+ 个记忆项目，共 20+ 个项目。鸣谢：Claude / Codex / Gemini，进行了大部分研究工作，我只是个指挥。*
