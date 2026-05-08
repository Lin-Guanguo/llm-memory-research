# 为什么 AI 产品不是换最强模型就完了

## 从模型偏好，到 Prompt / Context / Harness

Last Updated: 2026-05-07

前几天我在看一个现象：有些用户并不总是追最新、最强的模型。

GPT-4o 下线后，很多人怀念它。DeepSeek R1 后续明明有新版本，仍然有不少用户继续用旧版本或特定版本。站在工程师视角，这件事一开始有点反直觉：如果新模型能力更强，为什么用户不直接换过去？

后来我发现，这不是“用户不懂模型”，也不是“大多数用户需求太低”。更准确的说法是：**不同用户在优化不同的评价函数。**

工程师更容易把模型当生产力工具，优先看任务完成率：能不能读懂代码、改对文件、跑通测试、处理长上下文、少犯低级错误。但很多聊天、创作、陪伴、角色扮演用户，并不只是在评估能力。他们还在评估语气、节奏、风格、连续性、控制权，以及那个模型是不是“像自己习惯的那个”。

这件事把我带回到另一个问题：**AI 产品的体验到底由什么决定？**

如果答案只是“接入最强模型”，那模型升级应该天然是体验升级。但现实不是这样。模型能力当然重要，可一旦能力跨过某个可用阈值，用户开始在意的东西会变多：风格、稳定性、成本、速度、是否保留选择权、是否能迁移原来的 persona 和写作习惯。

这也是我想写这篇文章的原因。它不是一篇“提示词技巧教程”，也不是一篇模型测评。它想回答的是：

> 当模型越来越强以后，Prompt Engineering 还重要吗？Context Engineering 和 Harness 又到底在解决什么？

我的答案是：**Prompt Engineering 没有死，它被重新归位了。**

它不再是“提示词咒语”，而是模型可见接口设计。Context Engineering 决定模型这一轮看见什么；Harness 决定工具、状态、失败、评估、运行环境怎么组织；Prompt Engineering 则负责把这些模型可见信息表达成模型能稳定理解和执行的形式。

---

## 不是所有体验问题都能靠更强模型解决

工程师很容易有一个默认假设：模型越强，产品越好。

这个假设在 coding agent、复杂工程任务、长链推理、科研分析里大体成立。模型能力还没完全越过阈值时，更强模型往往直接决定任务能不能做成。一个模型能稳定修改大型代码库，另一个模型连文件都读不明白，用户当然选前者。

但不是所有 AI 使用场景都处在这个阶段。

日常写作、总结、翻译、普通问答、轻办公、聊天陪伴、角色扮演、轻量创作，这些场景里，很多模型已经足够可用。模型过了“能用”的线以后，用户不再只问“哪个最聪明”，而会开始问：

- 哪个更顺手？
- 哪个更快、更便宜？
- 哪个更像我原来用惯的风格？
- 哪个更少说教、更少打断沉浸感？
- 哪个能保留我的角色卡、语气和长期偏好？
- 哪个让我觉得自己仍然有控制权？

GPT-4o 的怀念潮，本质上不是 benchmark 争议。很多用户怀念的是一种交互质感：它更会接住情绪，更愿意停留在对话里，更像一个稳定的对话对象，而不是一个急着完成任务的系统。

DeepSeek R1 的持续使用也是类似信号。技术用户在意开放、便宜、可部署、可替换；创作用户未必关心这些。他们更关心它是否“够用且顺手”，是否能写出自己想要的味道。

这对 AI 产品工程师有一个很直接的启发：**模型行为不是后端实现细节，它本身就是产品界面。**

语气、拒绝方式、是否先承接情绪、是否保留风格、是否迁移用户习惯，这些都不是“模型接入完成以后顺手调一下”的小事。它们和按钮位置、页面布局、加载速度一样，都是体验的一部分。

---

## Prompt Engineering 降温了，但问题没有消失

这几年 Prompt Engineering 的热度确实下降了。

2023 年那种“提示词秘籍”“万能咒语”“Act as an expert”“超级 CoT 模板”的时代过去了。模型基础能力变强以后，普通用户直接说需求也能得到不错结果，“提示词技巧”的稀缺性自然下降。

与此同时，大家开始谈 Context Engineering、Memory、Tool Use、Eval、Agent Workflow，最近又开始谈 Harness。这不是概念炒作，而是应用形态变化后的自然结果。

早期很多 LLM 应用就是一次调用：把用户输入、系统 prompt 和少量上下文拼起来，送进模型，拿回结果。那时候 prompt 几乎就是应用能力的主要控制面。

现在越来越多应用不是一次调用了。一个 Agent 系统可能要检索 memory，读取文件，调用工具，维护状态，处理失败，多轮执行，再把中间结果压回上下文。问题自然从“这句话怎么写”扩大成：

- 模型这一轮应该看到什么？
- 工具返回结果怎么压缩？
- 哪些上下文会污染判断？
- 失败后是重试、回滚，还是交给另一个节点？
- 哪些约束应该写进 prompt，哪些应该交给 schema、validator 或测试？

所以 Prompt Engineering 不是被 Context Engineering 和 Harness 取代了，而是被放回了它真正应该在的位置。

它不再是全部控制面，但仍然是模型行为控制里很靠前的一层。

---

## 三个词其实是一条控制链

我现在更愿意把 Prompt、Context、Harness 看成同一条控制链上的三层。

**Prompt Engineering** 关注模型直接看到的信息如何表达。它处理的是指令、示例、字段名、schema description、工具描述、输出格式、分隔符、推理字段、语气约束。

**Context Engineering** 关注模型这一轮到底看到什么。它处理的是上下文选择、排序、压缩、检索、过滤、memory 注入、工具结果摘要。

**Harness** 关注模型运行环境如何组织。它处理的是工具、状态、失败恢复、评估、观测、回滚、多节点协作、模型路由和外部校验。

可以粗略写成这样：

```text
Harness：整个运行环境怎么组织
  Context：这一轮模型应该看到什么
    Prompt：这些信息如何表达给模型
```

对开放式 agent 来说，Context 往往先决定上限。如果相关文件没进上下文，再好的 prompt 也救不了。如果工具返回结果被错误压缩，模型也很难稳定推理。

但对用户直接可见的 C 端流程，Prompt 仍然非常关键。因为很多时候，正确材料已经给了模型，问题变成：它能不能第一次就按正确方式理解和输出。

用户点一下按钮，期望看到的是一次顺滑完成的体验，不是模型调用三次、校验两次、失败重试以后才勉强生成。多一次模型调用就多一份延迟和成本，多一次重试就多一份体验风险。

这就是 Prompt Engineering 在今天的位置：**提高首轮命中率。**

---

## 今天有效的 PE，不是写一句漂亮提示词

如果把 Prompt Engineering 理解成“写一句神奇提示词”，那它确实越来越弱。

但如果把它理解成“模型可见接口设计”，它仍然很重要，而且很多有效手段并不长得像传统 prompt。

### 1. Few-shot 不是例子，是行为范式

Few-shot 的作用不只是“给模型看几个例子”。它会告诉模型输出格式、字段边界、任务分布、标签空间和产品希望的语气。

很多时候，模型不是因为看懂了一句抽象规则而稳定输出，而是因为它看到了“这种情况应该长这样”。

这在结构化输出、路由、字段选择、工具调用里尤其明显。示例越接近真实产品路径，模型越容易按那个局部分布工作。

但 few-shot 也有副作用。旧例子会锁住旧行为。如果 schema 改了，example 还保留旧字段，模型很可能继续沿用旧字段。Few-shot 很强，所以它必须和 schema、prompt、测试一起版本化维护。

### 2. Schema 不只是格式约束，也是 prompt

Structured Outputs 和 constrained decoding 让 JSON 合法性更可靠，但它们只解决“形状合法”，不解决“语义一定对”。

只要 schema 里有多个合法值，模型仍然要在合法空间里做选择。它怎么选，受到字段名、字段描述、枚举值、字段顺序的影响。

这意味着 schema description 不是给工程师看的注释，它也是模型可见信息。很多时候，同一个要求写在全局 prompt 里不稳定，写进字段描述里反而更稳定，因为字段描述离模型即将生成的槽位更近。

所以 schema 有两层作用：

1. constrained decoding 保证输出结构合法；
2. schema text 影响模型在合法结构里怎么选择。

### 3. 推理提示应该变成任务相关字段

我越来越少相信空泛的“请仔细思考”。

更稳的做法不是让模型自由写一段长推理，而是把产品关心的中间判断写成输出结构的一部分。

例如，不是只写“think step by step”，而是让模型先判断：

- 输入属于什么类型？
- 哪些元素必须保留？
- 当前上下文是否足够？
- 哪个对象是核心对象？
- 后续生成必须避免什么？

这类 question-driven reasoning 比泛泛 CoT 更可控。它不是让模型随便想，而是让模型按产品需要回答几个具体问题。错误也更容易定位：最终结果错了，到底是输入理解错、条件判断错，还是最后生成偏了，可以更快看出来。

### 4. 控制信息不要混进生成内容

有些内部 marker、路由标签、控制信息，如果混进自然语言生成通道，模型可能会把它原样输出，甚至让它出现在用户可见内容里。

这不是模型“不听话”，而是接口设计不干净。

如果一个信息只是给系统控制流程用，不应该被用户看到，就不要放进会被生成的文本里。更好的方式是放进结构化 metadata、代码侧字段或下游不可见的控制层。

Prompt 可以告诉模型“不要输出这个 marker”，但更好的设计是：**一开始就不要让它进入用户可见的生成通道。**

### 5. 给模型语义标签，不要让它做脆弱索引计算

LLM 不擅长维护脆弱的 index 算术，尤其是在长上下文、多对象、多轮编辑里。

让模型输出“第 0 页”“第 1 页”“before_index = 3”，很容易遇到 0/1-based 混乱、越界、引用错对象。

更稳的方式是给对象一个可复制的语义标签，让模型直接匹配文本 handle。

原则很简单：**让模型做它擅长的匹配，不要让它做它不擅长的算术。**

---

## 换模型，也是在迁移一套产品接口

很多产品把模型升级当成后端替换：把 model name 改掉，跑通接口，就算完成。

这通常不够。

不同模型对 verbosity、few-shot、schema、reasoning instruction、工具描述、system/user 位置、temperature 的敏感度都不一样。一个 prompt 在 Claude 上刚刚好，换到 Gemini 可能变啰嗦；在 OpenAI reasoning model 上清晰直接，换到另一个模型可能需要更多示例；DeepSeek R1 这类模型甚至有自己的提示和采样习惯。

所以 prompt 不是完全模型无关的资产。它更像和模型、schema、上下文格式、解码参数绑定在一起的一套产品接口。

模型切换不应该被当成简单替换，而应该被当成一次 prompt migration：

- 保留关键 case；
- 观察行为差异；
- 调整 prompt、schema description、few-shot 和参数；
- 看首轮成功率、风格一致性和失败边界有没有变化。

这也解释了为什么用户会怀念旧模型。模型变强了，但原来的交互接口、风格习惯和情绪节奏不一定迁移过去。对用户来说，这不是“后端升级”，而是产品界面被换掉了。

---

## PE 的边界：它提高概率，不提供硬保证

强调 Prompt Engineering 仍然重要，不等于所有问题都交给 prompt。

Prompt 的本质是软控制。它能提高某个行为发生的概率，但不能提供硬保证。

对高风险要求，必须下沉到更确定的层：

- 输出形状交给 structured output / schema；
- 业务红线交给 validator；
- 稳定引用交给结构化 ID 或语义 handle；
- 不该暴露的信息交给代码侧隔离；
- 关键流程交给测试和监控；
- 复杂 agent 行为交给 harness、eval、trace 和 fallback。

这也是成熟 AI 工程和“写提示词”的差别。

真正有经验的工程师不是把所有要求都塞进 prompt，而是判断某个要求应该放在哪一层：

- 偏好、语气、轻量约束，可以先放 prompt；
- 格式、字段、局部语义，应该靠 schema 和 examples；
- 硬规则、不可接受的错误，要靠 validator、代码逻辑和测试兜底；
- 长期稳定风格或模型级偏好，可能最终要进入数据、微调或更深的学习层。

这是一条从浅到深的控制链。

---

## 结论：PE 没死，它成了产品稳定性工程的一部分

Prompt Engineering 没有死。

死掉的是把 prompt 当咒语的想象。

在真实应用里，它正在变成一种更朴素、更工程化的能力：设计模型可见信息的表达方式、结构和约束。

Context Engineering 和 Harness 的上升是必然的。应用越复杂，模型看到什么、工具怎么用、状态怎么维护、失败怎么恢复，就越重要。

但只要模型还需要根据一段可见输入产生行为，Prompt Engineering 就不会消失。

特别是在高稳定性 C 端 AI 应用里，prompt 仍然直接影响用户体验。它不一定是最外显的技术壁垒，也不一定能单独构成护城河。但真正有价值的经验，往往藏在持续调优里：

- 理解用户场景；
- 理解模型脾气；
- 理解输出结构；
- 理解失败边界；
- 知道哪些东西应该写进 prompt；
- 知道哪些应该放进 schema；
- 知道哪些必须交给代码和 validator。

所以我现在对 Prompt Engineering 的看法是：

> 它不再是提示词秘籍，而是模型可见接口设计。  
> 对高稳定性 AI 产品来说，它仍然是产品稳定性工程的一部分。

也因此，AI 产品不是换最强模型就完了。真正的产品能力，是把模型能力、上下文、工具、约束、风格、成本和用户控制权组合成一套用户愿意长期使用的体验。

---

## 参考资料

市场趋势与 Context / Harness：

- [Simon Willison: Context engineering](https://simonwillison.net/2025/Jun/27/context-engineering/) (accessed: 2026-04-30)
- [LangChain: The rise of context engineering](https://www.langchain.com/blog/the-rise-of-context-engineering) (accessed: 2026-04-30)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (accessed: 2026-04-30)
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (accessed: 2026-04-30)
- [Anthropic: Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) (accessed: 2026-04-30)

Prompt Engineering 与结构化输出：

- [The Prompt Report: A Systematic Survey of Prompt Engineering Techniques](https://arxiv.org/abs/2406.06608) (accessed: 2026-04-30)
- [Rethinking the Role of Demonstrations: What Makes In-Context Learning Work?](https://arxiv.org/abs/2202.12837) (accessed: 2026-04-30)
- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) (accessed: 2026-04-30)
- [Least-to-Most Prompting Enables Complex Reasoning in Large Language Models](https://arxiv.org/abs/2205.10625) (accessed: 2026-04-30)
- [OpenAI: Introducing Structured Outputs in the API](https://openai.com/index/introducing-structured-outputs-in-the-api/) (accessed: 2026-04-30)
- [JSONSchemaBench: A Benchmark for Evaluating Constrained Decoding for JSON Schema](https://arxiv.org/abs/2501.10868) (accessed: 2026-04-30)
- [Google Gemini: Structured output](https://ai.google.dev/gemini-api/docs/structured-output) (accessed: 2026-04-30)
