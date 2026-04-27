# Personality Training — Production Cases Survey

Last Updated: 2026-04-24

Purpose: 记录 Neuro-sama / Character.AI 之外其他"在生产中做过权重级人格训练"的案例，作为未来博客和研究的线索库。本文不做深入研究，只整理基础事实 + 源头链接。

**Scope 说明**：只收录 2018 年之后、基于 transformer + RLHF/DPO/constitutional AI 主流路线的生产案例。XiaoIce（2014）和 Replika（2017）技术栈相对较老（Seq2Seq、GPT-2 时代），与当前权重人格训练的主流方法不在一个世代，已从主研究线索里剥离（见文末"不纳入的历史案例"）。

---

## 值得深入研究的生产级案例

### 1. Inflection Pi — 媒体深度报道已存在

**为什么重要**：非常明确的"商业产品 + 系统性人格训练"案例，有 IEEE Spectrum 级别的深度报道。

**关键事实**
- 由 Reid Hoffman + Mustafa Suleyman + Karén Simonyan 于 2022 年创立
- 自家模型：Inflection-1、Inflection-2、Inflection-2.5（对标 GPT-4）
- 2024 年 3 月 Microsoft 实质上"收购"了核心团队（Suleyman 去做 Microsoft AI CEO），Pi 进入维持模式

**技术方法（已通过 IEEE 原文核实的部分）**
- 专门的 **"personality team"**：工程师 + 语言学家 + Rachel Taylor（前伦敦广告公司 creative director）
- 人格设计方式：列出**要有的特质**（kind, supportive）和**要避免的**（irritable, arrogant, combative）
- RLHF 数据标注团队包含 **"many hundreds of teachers"**（IEEE 原文原话），其中有 behavioral therapists、psychologists、playwrights 等

**之前写过但未在 IEEE 原文证实（需其他源头验证）**
- "600 位兼职老师" —— 来自搜索引擎二手摘要，IEEE 原文只说 "many hundreds"
- "empathetic fine-tuning" 作为官方术语 —— IEEE 原文没用这个说法，只说 RLHF

**主要来源**
- [IEEE Spectrum 深度报道：What Happened to this $4 Billion Chatbot?](https://spectrum.ieee.org/inflection-ai-pi)
- Inflection 官方 blog（还在线但已不活跃）

**深入研究优先级**：高。是 Character.AI 路线的另一个完整样本。

---

### 2. Anthropic Claude — blog.4 已部分覆盖

**当前覆盖**：blog.4 已把它作为 Character.AI 的"侧证"引用过，并在 § 第三条路 activation engineering 讨论过 persona vectors。

**为什么应该单独研究**
- 按"有官方文章公开方法论"的标准，Claude 其实是本领域**最透明的生产案例**
- [Claude's Character](https://www.anthropic.com/news/claude-character)（2024-06-08 官方 blog）直接用 "character training" 这个词，并说这是 **"character variant of our Constitutional AI training"**（原文直引）
- Amanda Askell 作为 lead author 经常在 podcast / 博客里讨论细节

**值得深入的方向**
- constitutional AI 的 "character variant" 具体怎么操作
- Anthropic 的 persona vectors 研究
- 2026 年 1 月最新版 Claude constitution（30K 词）的设计逻辑

**深入研究优先级**：中高。材料已相对多，是性价比最高的补课对象。

---

## 边界情况（要不要算我自己也不确定）

### xAI Grok

- 人格明显（"Hitchhiker's Guide 风格"），但**技术本质不明**
- 有批评文章（如 [Klover.ai: Personality Engineering or Prompt-Tuning Theater?](https://www.klover.ai/groks-rebellious-voice-personality-engineering-or-prompt-tuning-theater/)）质疑 Grok 的"人格"很大部分是 system prompt 而非 weight-level 训练
- 2025 年的"Nazi 事件"也暴露出人格不稳定，暗示训练层面的人格约束并不强
- **不列为确认案例**。但值得单独研究"prompt vs weight 在 Grok 的占比"这件事本身

### Kindroid / Talkie / Chai 等 AI companion 平台

- 主要靠外部 LLM + 用户写的 backstory prompt（Kindroid 允许 2500 字符 backstory）
- 可能有自家 fine-tune 做定制化底色，但没有公开技术资料
- **倾向于不列**——看起来主要是 prompt-level

### Meta Celebrity AI Characters（2024 已下架）

- MrBeast / Paris Hilton / Charli D'Amelio 等虚拟对话版本
- 2024 年因效果不佳 + 离谱 bug（AI 角色 "Liv" 声称创作者缺乏多样性）下架
- 技术细节**几乎零公开**，也没上规模就挂了
- **不列**——更像失败案例，不是方法论参考

---

## 不纳入的历史案例（技术栈过老）

以下两个案例有较完整的技术公开资料，但使用的是 Seq2Seq / GPT-2 级别的旧世代技术栈，和当前 transformer + RLHF/DPO 主流路线不在一个年代，暂不纳入主研究线索：

- **Microsoft XiaoIce（小冰）**：2014 年上线。论文 Zhou et al., ["The Design and Implementation of XiaoIce, an Empathetic Social Chatbot"](https://arxiv.org/abs/1812.08989)（2020 年 MIT *Computational Linguistics*）。核心方法：Seq2Seq + multi-task learning + persona fusion，把对话建模为 MDP 优化 CPS。
- **Replika**：2017 年上线。模型演进：GPT-3 API → fine-tuned GPT-2 → GPT2-XL（1.5B 参数，2022 年起）。训练目标是情感陪伴向的 fine-tuning。

如果未来要写"人格训练的技术演进史"这种综述型内容，这两个案例可以作为历史参照物回过来用。

---

## 下一步 action items

**高优先级**
- [ ] 深度研究 Inflection Pi，特别是 personality team 的实际运作和 RLHF 数据标注流程

**中优先级**
- [ ] 追 Anthropic Claude 2026 新 constitution 的技术细节（30K 词意味着什么）
- [ ] Anthropic persona vectors 的产品化潜力

**低优先级 / 视情况**
- [ ] 研究 Grok 的"人格"到底多少是 weight-level vs system prompt——可能是个有争议的小品文

---

## 参考源头汇总

| 案例 | 主要源头 |
|---|---|
| Inflection Pi | [IEEE Spectrum deep dive](https://spectrum.ieee.org/inflection-ai-pi) |
| Anthropic Claude | [Claude's Character 官方 blog](https://www.anthropic.com/news/claude-character) · [Lawfare Podcast with Amanda Askell](https://www.lawfaremedia.org/article/scaling-laws--claude's-constitution--with-amanda-askell) |
| Grok（disputed） | [Klover.ai 质疑](https://www.klover.ai/groks-rebellious-voice-personality-engineering-or-prompt-tuning-theater/) |
| XiaoIce（历史参照） | [arxiv 1812.08989](https://arxiv.org/abs/1812.08989) · [MIT Computational Linguistics](https://direct.mit.edu/coli/article/46/1/53/93380/) |
| Replika（历史参照） | [LifeArchitect tracker](https://lifearchitect.ai/replika/) |
