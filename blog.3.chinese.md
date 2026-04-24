# Claude Code 为啥好用，他做了什么别人没做的

## 记忆/上下文/检索/工程 代码深入解析，对比其他 Agent

Last Updated: 2026-04-01

> 我扒了 Claude Code v2.1.88 泄漏的完整源码（57MB TypeScript），发现了几个亮点：
>
> - **Markdown + Frontmatter 统一模式**——记忆、技能、Agent、命令用同一套"摘要选择 + 全文注入"范式，简单好用的 AI Native 数据管理
> - **四层渐进压缩**——从每轮静默截断到 9 段结构化摘要，按需逐层升级
> - **三层检索**——索引注入、Sonnet 异步选文件、模型 Grep 精确查找，层层递进互不阻塞
> - **Prompt Cache 作为一等公民**——10x 缓存命中成本差，每个架构决策都优先保护缓存前缀不被破坏
>
> 上一篇以 OpenClaw 为主线，这篇深入 Claude Code，对比 Codex 和 Gemini CLI。

---

## 一、记忆——MD + Frontmatter：一种 AI Native 的存储模式

主流编程 Agent 都有项目指令文件——Claude Code 的 `CLAUDE.md`、Codex 的 `AGENTS.md`、Gemini CLI 的 `GEMINI.md`——启动时加载，提供项目级上下文。这一层大家做法类似。

Claude Code 在此基础上额外构建了**项目维度的长期记忆系统**。

### 存储格式：MD + Frontmatter

每个记忆文件长这样：

```markdown
---
name: user prefers vim keybindings
description: User always requests vim mode in editors, has 10+ years vim experience
type: feedback
---

User explicitly asked to enable vim mode. They mentioned using vim since college.
**Why:** Deep muscle memory, can't work efficiently without vim bindings.
**How to apply:** Always suggest vim-compatible options when configuring editors.
```

YAML frontmatter 是**结构化摘要**（name、description、type），Markdown body 是**完整内容**。检索时只读 frontmatter 做决策，按需加载全文。

这个模式的核心思路是：**先让 AI 看目录和摘要，再决定要不要读全文**。和人类翻书一样——先看目录，再翻到具体章节。简单但有效。

### 不只是记忆——整个扩展体系的统一模式

这个 "frontmatter 选择 + body 注入" 模式**贯穿整个 Claude Code 扩展体系**：

| 内容类型 | Frontmatter 字段 | 用途 |
|---------|-----------------|------|
| 记忆文件 | name, description, type | LLM 选择相关记忆 |
| Skills | name, description, whenToUse | LLM 决定是否触发技能 |
| 自定义 Agent | name, description, tools, model | LLM 决定是否派遣 Agent |
| Commands | name, description | Slash 命令注册 |
| Rules | globs | 按文件路径匹配条件注入 |

记忆、技能、Agent、命令——对 Claude Code 来说，它们本质上是同一种东西：**带结构化元数据的 Markdown 文件**。同一套范式，复用在整个系统中。

### 记忆类型与边界

源码中硬编码了四种记忆类型（`memdir/memoryTypes.ts`）：

```typescript
export const MEMORY_TYPES = [
  'user',       // 用户角色、偏好、知识
  'feedback',   // 做事方式的指导（纠正和确认都记）
  'project',    // 项目进展、截止日期、决策背景
  'reference',  // 外部系统指针（Linear、Grafana 等）
] as const
```

Frontmatter 的 `type` 字段通过 `parseMemoryType()` 校验，不在这四种里的会 graceful degradation。

同样重要的是源码中明确定义了**不存什么**（`WHAT_NOT_TO_SAVE_SECTION`）：不存代码模式和架构、不存 git 历史、不存调试方案、不存 CLAUDE.md 已有的内容。定位很清楚——记忆只存代码和工具推导不出来的信息。

### 实验特性：AutoDream 与 Team Memory Sync

源码中还有两个 feature gate 后的实验特性：

- **AutoDream**：后台 agent 定期（≥24h 且 ≥5 次会话）对记忆文件做合并、去重、裁剪。Prompt 原话："You are performing a dream — a reflective pass over your memory files."
- **Team Memory Sync**：Client-Server 记忆同步，delta 上传 + secret 扫描，面向团队共享记忆

> **对比**：Codex（`AGENTS.md`）和 Gemini CLI（`GEMINI.md`）目前在指令文件阶段，类似 Claude Code 的 `CLAUDE.md`。Claude Code 在此之上多走了一步做长期记忆。

---

## 二、上下文——四层压缩

Claude Code 的上下文管理有**四层压缩系统**，从轻到重按需逐层升级。

### 第一层：Time-Based Microcompaction

最轻量的一层。纯代码逻辑，不调用 LLM，开销几乎为零。

核心思路：如果距离上一条 assistant 消息已经过了较长时间（说明 prompt cache 已过期），就把旧的工具输出内容替换为 `[Old tool result content cleared]`，只保留最近几条。

```typescript
// microCompact.ts:438-441
const gapMinutes =
  (Date.now() - new Date(lastAssistant.timestamp).getTime()) / 60_000
if (!Number.isFinite(gapMinutes) || gapMinutes < config.gapThresholdMinutes) {
  return null  // 间隔不够长，不触发
}
```

只对特定工具的输出动手——`COMPACTABLE_TOOLS` 包含 File Read/Write/Edit、Bash、Grep、Glob、Web 工具。Agent 子代理的返回保留全文，因为那些是经过处理的高质量结果。

### 第二层：Cached Microcompaction

在 prompt cache 仍然有效时（cache 没过期），用 Anthropic 的 cache editing API 删除旧工具结果，**不破坏缓存前缀**。

和第一层的区别：第一层直接改本地消息内容（cache 已经冷了，无所谓）；第二层通过 `cache_edits` 指令让 API 端删除，本地消息不动，保证 cache key 不变。

```typescript
// microCompact.ts:296-301
// Key differences from regular microcompact:
// - Does NOT modify local message content (cache_edits are added at API layer)
// - Uses count-based trigger/keep thresholds
// - Tracks tool results and queues cache edits for the API layer
```

### 第三层：Full Compaction

上下文接近窗口上限时触发。这一层调用 LLM 生成 9 段结构化摘要，是四层中**最昂贵**的。

关键设计：压缩通过一次**独立的 side call** 完成，压缩过程本身不污染主对话历史。

最直觉的做法是在主对话里直接插入压缩 prompt，让模型返回摘要：

```
主对话: [msg1, msg2, ..., msgN, 压缩prompt]
→ API 返回摘要（assistant 消息）
→ 继续: [msg1, ..., msgN, 压缩prompt, 摘要, 新用户消息, ...]
问题：压缩 prompt 和摘要都留在对话历史里，占上下文空间
```

Claude Code 的做法是发一次**独立的 API 调用**（源码中叫 `runForkedAgent`），压缩过程不进入主对话：

```
主对话: [msg1, msg2, ..., msgN]  ← 上下文快满了

独立 API 调用（不在主对话里）:
  发送: [同样的 system prompt + tools + msg1...msgN + 9段结构化压缩prompt]
  返回: 摘要文本
  调用结束，不影响主对话历史

回到主对话:
  [msg1, ..., msgN] 全部替换为 [摘要(user message)]
  继续: [摘要, 新用户消息, ...]
```

压缩 prompt 本身是客户端构造的详细模板（`BASE_COMPACT_PROMPT`），要求模型生成 9 段结构化摘要（请求意图、技术概念、文件和代码、错误与修复、用户消息、待办任务、当前工作等），先在 `<analysis>` 标签里做分析草稿，再输出 `<summary>`。分析草稿在格式化后会被剥离，只有 summary 进入后续上下文。

**为什么不直接发一个全新的 API 调用？** 为了 cache hit。这次独立调用通过 `CacheSafeParams` 传入和主对话**完全相同**的 system prompt、tools、model、messages、thinking config，前缀一致就能命中主对话已缓存的内容，只为新增的压缩请求付费。

```typescript
// compact.ts:431-433 (代码注释原文)
// forked-agent path reuses main conversation's prompt cache.
// Experiment (Jan 2026) confirmed: false path is 98% cache miss
```

摘要 prompt 要求模型先在 `<analysis>` 标签里做详细分析（文件名、代码片段、函数签名、用户反馈），然后生成结构化 `<summary>`。`<analysis>` 在格式化后被剥离，只有 summary 进入后续上下文。

### 第四层：Snip Compaction

Feature gate 后的老上下文直接移除（`HISTORY_SNIP`），通过 lazy-loaded 模块实现。这是最激进的策略——不做摘要，直接丢弃。

### 模型自知预算

通过 `<budget:token_budget>` 标签和 `<system_warning>` 注入，Claude 4.5+ 模型实时感知上下文使用情况，可以自我调节——比如主动精简回复、或者决定是否启动一个可能输出很长的工具调用。

另外，扩展思维（thinking block）的 token 在下一轮自动清除，防止推理痕迹污染后续 turn。

> **对比**：Codex 有写入时截断和中途压缩；Gemini CLI 有二次探针验证压缩质量。各有特色。

---

## 三、检索——三层机制，从被动加载到精确定位

存储只是基础，**检索决定了记忆是否有用**。Claude Code 的检索分三层，从零成本到高成本逐层递进。

### Layer 1：MEMORY.md 索引注入（启动时，零额外成本）

会话启动时，`getMemoryFiles()`（`utils/claudemd.ts:979`）把 MEMORY.md 和 CLAUDE.md 一起加载进上下文：

```typescript
// claudemd.ts:979-992
const { info: memdirEntry } = await safelyReadMemoryFileAsync(
  getAutoMemEntrypoint(),  // → MEMORY.md 路径
  'AutoMem',
)
```

限制硬编码在 `memdir/memdir.ts`：

```typescript
export const MAX_ENTRYPOINT_LINES = 200   // 最多 200 行
export const MAX_ENTRYPOINT_BYTES = 25_000 // 最多 25KB
```

MEMORY.md 只是索引（标题 + 单行描述），不是全文。它的价值在于**让模型"知道"记忆系统里有什么**，为 Layer 3 的主动搜索提供线索。

有意思的发现：源码中有一个 feature flag 开启后会通过 `filterInjectedMemoryFiles()`（`claudemd.ts:1142`）把 MEMORY.md 从系统提示中过滤掉，完全靠 Layer 2 推送。说明 Anthropic 在 A/B 测试 Layer 1 是否可以被 Layer 2 替代。

### Layer 2：Sonnet sideQuery（每个用户 turn 一次，有门控）

这是最精妙的一层。入口在 `query.ts:297`，`while(true)` 工具循环**之前**：

```typescript
// query.ts:297-304
// Fired once per user turn — the prompt is invariant across loop iterations,
// so per-iteration firing would ask sideQuery the same question N times.
using pendingMemoryPrefetch = startRelevantMemoryPrefetch(
  state.messages,
  state.toolUseContext,
)
```

同一 turn 内多轮工具调用只触发一次。`startRelevantMemoryPrefetch()`（`utils/attachments.ts:2361`）有 5 个门控条件：auto-memory 开启、feature flag 为 true、有真实用户消息、用户输入包含空格（单词查询跳过）、会话累计推送字节数低于上限。

通过门控后，`findRelevantMemories()`（`memdir/findRelevantMemories.ts:98`）执行核心流程：

```typescript
// findRelevantMemories.ts:98-108
const result = await sideQuery({
  model: getDefaultSonnetModel(),
  system: SELECT_MEMORIES_SYSTEM_PROMPT,
  messages: [{ role: 'user', content: `Query: ${query}\n\nAvailable memories:\n${manifest}` }],
  max_tokens: 256,
  output_format: { type: 'json_schema', schema: { ... selected_memories: string[] ... } },
})
```

流程：`scanMemoryFiles()` 读所有记忆文件 frontmatter（前 30 行，最多 200 个文件）→ `formatMemoryManifest()` 格式化为清单（每行一个：`- [type] filename (timestamp): description`）→ Sonnet 返回最多 5 个文件名 → 读取选中文件完整内容 → 注入为 `<system-reminder>` 附件。

**不阻塞。** sideQuery 是 prefetch 模式——启动后在后台运行。消费端（`query.ts:1599`）只在已 settle 时消费（`settledAt !== null`），没 settle 就跳过，下次迭代再检查。用户按 Escape 自动 abort。

去重：`alreadySurfaced` set 过滤已推送的文件；`readFileState` 过滤模型已 Read/Write/Edit 的文件。

**为什么不用向量搜索？** 规模有界——单用户、单项目、最多 200 个文件 × ~150 字符描述 ≈ 几千 token。Sonnet 一次调用就能处理。刻意简单，因为场景不需要复杂。

### Layer 3：自主搜索（模型决定，Grep）

当 Layer 1/2 不够时，模型自己决定搜索。`buildSearchingPastContextSection()`（`memdir/memdir.ts:375`）在系统提示词中注入两种 Grep 搜索方式：

```typescript
// memdir.ts:393-403 (注入到系统提示词的内容)
'1. Search topic files in your memory directory:',
memSearch,      // → Grep pattern="<search term>" path="<memoryDir>" glob="*.md"
'2. Session transcript logs (last resort — large files, slow):',
transcriptSearch,  // → Grep pattern="<search term>" path="<projectDir>/" glob="*.jsonl"
'Use narrow search terms (error messages, file paths, function names) rather than broad keywords.',
```

**Layer 3 的关键**：不是盲搜。Layer 1 的索引让模型知道记忆里大概有哪些主题；Layer 2 推送的文件让模型知道某些领域有更多细节。当模型感知到"应该有相关信息但需要更多细节"时，它**知道自己要搜什么**——被前两层引导的精确检索。

### 背景提取：写入端

检索好不好，取决于有没有东西可检索。Claude Code 有持续运行的**背景记忆提取 agent**：

- **触发**：主 agent 产出最终响应时 fire-and-forget
- **机制**：forked agent，共享父进程 prompt cache，最多 5 轮
- **互斥**：主 agent 当轮已写记忆则提取 agent 跳过
- **职责**：Turn 1 并行读取，Turn 2 并行写入记忆目录

用户不需要手动维护，系统在每次对话后自动提取值得记住的信息。

### 三层关系

```
Layer 1（索引）→ 让模型知道记忆系统的存在和大致内容
        ↓
Layer 2（推送）→ 异步补充最相关的具体文件
        ↓
Layer 3（搜索）→ 兜底，模型自己精确查找
        ↑
 背景提取 agent → 持续写入，保证有东西可选
```

> **对比**：Codex 和 Gemini CLI 的指令文件在启动时加载，没有运行时的按需检索层。

---

## 四、65+ Prompt 模块 + 子代理体系

### 模块化系统提示词

Claude Code 的系统提示词不是一个大文件，而是 **65+ 个模块化文件**按需组装，覆盖安全检查、文件修改规范、git 操作流程、输出效率要求、代码风格约束等方方面面。

更关键的是 **20+ 个 `<system-reminder>` 模板**在运行时动态注入——文件被外部修改时提醒过期、Skill 激活时注入指令、token 预算变化时实时告知、记忆文件推送时附带时效性警告等。

`<system-reminder>` 本身是一个值得说的设计。API 消息流里只有三个角色：`system`（系统提示词）、`user`（用户输入）、`assistant`（模型返回）。其中 assistant 的内容**绝对不能修改**（那是模型的输出），system 是缓存前缀**不应该碰**（改了就破缓存）。那运行时动态产生的系统信息放哪里？

Claude Code 的做法是在 `user` 消息中嵌入 `<system-reminder>` 标签，创建了一个**第四通道**——既不是用户输入，也不是模型返回，而是系统注入。系统提示词告诉模型："Tags contain information from the system. They bear no direct relation to the specific tool results or user messages in which they appear." 模型知道这是系统信息，给予相应权重。

实现上极其简单——就是一个 XML 标签包装：

```typescript
export function wrapInSystemReminder(content: string): string {
  return `<system-reminder>\n${content}\n</system-reminder>`
}
```

但这个简单的设计解决了三个问题：保护 prompt cache（不碰 system 前缀）、保持角色语义（不篡改 assistant 输出）、代码可识别（用 `startsWith('<system-reminder>')` 做过滤和合并）。

模型始终在接收最相关的上下文指令——这是编码体感强的直接原因。

### 子代理体系

**6+ 专业化子代理**，每种有针对性的系统提示词和工具集：

| 子代理 | 用途 | 工具限制 |
|-------|------|---------|
| Explore | 只读代码搜索 | 只读工具，快速搜索 |
| Plan | 架构规划 | 只读工具，聚焦设计 |
| Code Reviewer | 代码审查 | 审查标准和输出格式 |
| Code Explorer | 深度分析 | 追踪执行路径 |
| Code Architect | 架构设计 | 蓝图输出格式 |

**Coordinator Mode**：编排多个 Worker，通过 `<task-notification>` XML 块通信。

**Agent Swarm**（详见 [claude-code-swarm.research.md](./claude-code-swarm.research.md)）：
- 文件信箱（JSON + file lock），1 秒轮询
- 8+ 结构化消息类型（权限请求、关机生命周期、模式变更等完整协议）
- 集中权限模型：所有 Worker 的权限请求流向 Leader 终端
- **系统级空闲通知保证**：query loop 退出时系统自动发送空闲通知，不依赖模型记住上报

**Tool 并发分类**：每个工具声明 `isConcurrencySafe()`（默认 false），读操作并行、写操作串行。

> **对比**：Codex 采用单循环 + plan 模式；Gemini CLI 有进程内子代理。思路不同，Claude Code 在专业化分工上投入更多。

---

## 五、工程纪律

Claude Code 好用不只因为某个技术创新，而是系统级的工程纪律。几个代表性例子：

### Prompt Cache 作为一等公民

缓存命中 vs 未命中有 **10x 成本差**，每会话几十到几百轮 tool use，累计差异巨大。三个保护机制：

- **`DANGEROUS_uncachedSystemPromptSection()`** —— 函数名本身是防护栏，强迫开发者意识到自己在破坏缓存
- **动态内容走 user message** —— 所有 `<system-reminder>` 注入用户消息，不碰系统提示词前缀
- **Beta header 单向锁** —— 开了就不关，语义不精确但 cache 友好

### Message Normalization Pipeline

5500+ 行代码，每次 API 调用前处理消息流：重排附件 → 过滤虚拟消息 → 确保 tool-use/tool-result 配对 → 合并连续 thinking/user block。为中断的工具执行创建**合成错误块**，防止 API 拒绝。

### Fail-Closed 默认

- `isConcurrencySafe()` 默认 false —— 没声明安全就不并行
- `isReadOnly()` 默认 false —— 没声明只读就当写操作
- 权限系统默认 ask —— 不确定就问用户

### Forked Agent 共享 Cache

记忆提取、full compaction、AutoDream 都用 forked agent，共享父进程的 prompt cache，避免重复支付系统提示词的 API 成本。这个模式被复用了至少 5 次。

### System-Level Guarantees

Swarm 空闲通知：query loop 退出时**系统级**发送 `sendIdleNotification()`。"模型忘了汇报"在系统层面解决，不靠 prompt。

---

## 结语

Claude Code 为啥好用？

不是某个单点技术碾压，而是**系统完整性**：

- 记忆有存储（MD + Frontmatter）、有检索（三层递进）、有维护（AutoDream）、有提取（后台 agent）
- 上下文有四层渐进压缩，按需逐层升级
- 65+ prompt 模块让模型始终得到最相关的指令
- 6+ 种子代理各司其职
- 工程纪律贯穿每个设计决策

每个维度都做到了**足够好**，而且在同一套工程纪律下协同运作。

---

## 预告

下一篇：**从 Claude Code Buddy/Companion 看 AI 陪伴类产品**。

一个编程工具为什么要做"虚拟宠物"？gacha 无氪设计、sideQuery 模式复用、非侵入原则——以及这对 AI companion 产品设计的启示。

---

## 参考资料

基于源码分析和逆向工程，完整研究材料：

**Claude Code 研究**：
- [Claude Code 源码架构](https://lin-guanguo.github.io/llm-memory-research/claude-code-sourcemap.research/) | [Agent Swarm 架构](https://lin-guanguo.github.io/llm-memory-research/claude-code-swarm.research/) | [上下文管理（逆向工程）](https://lin-guanguo.github.io/llm-memory-research/claude-code-context.research/)

**对比 Agent 研究**：
- [Codex](https://lin-guanguo.github.io/llm-memory-research/codex-context.research/) | [Gemini CLI](https://lin-guanguo.github.io/llm-memory-research/gemini-cli.research/) | [Anthropic Context Engineering 指南分析](https://lin-guanguo.github.io/llm-memory-research/anthropic-context-engineering.research/)

**上一篇**：[我分析了 6 个主流 Agent 的记忆和上下文](https://www.xiaohongshu.com/discovery/item/69ca6277000000001b02229f)

**全部研究**：[lin-guanguo.github.io/llm-memory-research](https://lin-guanguo.github.io/llm-memory-research/)

---

*基于 Claude Code v2.1.88 源码（source map 泄漏）和系统提示词逆向工程。鸣谢：Claude / Codex / Gemini，进行了大部分源码分析工作。*
