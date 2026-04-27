# 人格训练：AI 怎么才能"像个人"

Last Updated: 2026-04-27

前面几篇博客里，我从 **记忆** 写到 **上下文**——从 Mem0 / Letta 到 Claude Code。这两块是目前 AI Agent 领域被研究得最彻底的部分：怎么记、怎么查、怎么压缩、怎么装进有限的窗口里。

写到第三篇 Claude Code 之后我停下来问自己一个问题：**这两块到底能不能让 AI "像个人"？**

答案是——不太能。

记忆系统解决的是"AI 记得住你喜欢什么"，上下文系统解决的是"AI 能在有限 token 里塞进有用的东西"。这些都是**存储与检索问题**，和"AI 的性格是什么"其实是两件事。你换一套记忆系统，AI 的说话风格不会变；你优化了上下文压缩，AI 的价值观也不会变。

如果想做的不是"好用的助手"、而是"有自己人格内核的 AI 角色"——记忆和上下文都只是表层。真正决定 AI 像不像一个人的那一层，得往下走一层：**模型本身的权重**。

这就是这篇的主题。业内英文叫 **Character Training**。中文译法目前并不统一（"人格训练""角色训练""人设训练"都有人用），本文统一采用 **"人格训练"**——严格说它是 Character.AI 对 post-training 中某一层的命名，本文借来做宽泛概念，泛指所有"把角色性格刻进模型权重"的做法。

但这篇最后真正想问的，不只是"怎么训练人格"，而是一个更现实的问题：**如果一个人或一个团队时间有限，怎么部署一个真正有自己人格的 AI？** 现在看可能有两条路。个人开发者短期内更可能走分层路线：小模型负责人格和最终表达，复杂任务交给大模型或 subagent 在后台做；平台厂商长期也许会把人格注入做成基础能力，用 post-training、adapter、activation steering、长期 profile 或其他机制，让大模型天然更擅长进入角色。哪条路会先成熟，现在还没人验证。

查下来发现一件反差很大的事：**记忆**这块开源项目几十个、论文几百篇；**上下文**这块开源 Agent 六七个能读源码、Claude Code 还有源码泄露流出来；**但"把人格训进模型里"这件事，公开材料少得可怜**。本文重点写两个我调研得比较深的案例——一个人做的 **Neuro-sama** 和一家公司做的 **Character.AI**。加起来能查到的公开技术细节，可能还不如 Mem0 一个开源项目多。

（这个领域还有一些其他生产案例我初步扫过但还没深入求证，本文先不展开。）

这篇是我把能找到的资料整理在一起的一份综述。我本身不是训模型的背景，写的是从 Agent 工程师角度对训练侧公开文献的整理。这个领域**信息结构性稀缺**，所以这不是一篇教程，而更像是**一张我能整理到的现状地图**。欢迎熟悉这个方向的朋友补充我漏掉的东西。

---

## 当前 prompt 工程还不够

在讨论"人格训进权重"之前，先说清楚一个前提：**我不是说 prompt engineering 这条路走不通**。未来如果上下文工程、长上下文、工具调用、自动评估和 prompt 优化继续进步，纯 prompt / 外部系统也许能把角色一致性推到很高的水平。

但按目前能看到的公开研究和工程案例，单靠 prompt 做"有稳定人格内核的 AI 角色"，仍然不够稳。绝大多数"AI 角色扮演"类产品（SillyTavern、早期 Character.AI 的 prompt 层、各种 Eliza 式 character cards）都主要靠 prompt 工程撑起来，已经能做出相当像样的角色感；问题不是它没用，而是它现在还很难承担"长期稳定人格"这件事。

**学术层面**不是说 prompt 完全没用，而是说它不稳定、不可预测，而且会把模型带向训练数据里的既有偏差。

[Zheng et al., 2024](https://aclanthology.org/2024.findings-emnlp.888/) 在 EMNLP Findings 做了一个很直接的实验：162 种角色、2,410 个事实问答、4 个主流开源模型家族。结果是，把模型设成"律师""医生""老师"之类的 persona，并不会稳定提升客观任务表现；有些角色还会让表现变差。也就是说，persona prompt 更像一个脆弱的行为偏置器，而不是可靠的能力开关。

更麻烦的是偏移方向经常和我们想象的不一样。[Lutz et al., 2025](https://aclanthology.org/2025.findings-emnlp.1261/) 系统评估了 sociodemographic persona prompting：同样是在模拟某类人，不同的角色扮演格式、人口学描述方式、名字暗示方式，都会显著改变输出；模型尤其难稳定模拟边缘群体，容易滑向刻板化画像。换句话说，prompt 确实能改变"人设"，但改变出来的东西不一定是你写进去的那个人设，而可能是模型从训练语料里激活出来的刻板联想。

还有一类心理测量研究更直接地提醒我们：不要太认真地把 prompt 出来的"人格"当人格。[Dorner et al., 2023](https://openreview.net/forum?id=zKDSfGhCoK) 发现，LLM 在人格测试里的回答会系统性偏离人类受试者：一些反向计分题会被同时肯定；用 prompt 去模拟不同人格类型时，也不遵循人类 Big Five 那种相对清晰的五因子结构。[Bodroža et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11461045/) 进一步测了多个 LLM 在不同时间点的人格问卷，发现时间稳定性有限。

所以我现在的判断是：prompt 的问题不是"完全塑造不了角色"，而是它更像一层**上下文态度**：短期有效、强依赖措辞、容易被任务和对话历史冲掉，也容易把训练数据中的偏见一起激活出来。它适合做场景、语气、临时身份；但在当前阶段，如果目标是长期一致的性格内核，prompt 本身还不够。

**工程层面**更具体。市面上有一批开源项目公开宣称要"复刻一个 Neuro-sama"：kimjammer/Neuro、Open-LLM-VTuber、moeru-ai/airi、AIRIS-VtuberAI 等。它们都把管线做得相当完整：LLM + TTS + STT + Live2D 头像全齐。**但这些公开项目都没有做出 Neuro-sama 那种"感觉"**。

其中 kimjammer 的开发者在 8 篇 dev log 里把原因讲得最清楚。他从 Mistral 7B-v0.2 起步、后来升级到 Llama 3 8B，配 ~1000 token 的角色描述和示例对话，能做到"表面像某个角色"——但在 [Dev Log 4](https://blog.kimjammer.com/neuro-dev-log-4/) 撞到一个硬限制，他的原文是：

> the LLM still stubbornly avoids swearing...the result of using a fairly well aligned base model

大意是：哪怕你在 prompt 里明说，模型还是固执地不骂人——这是 alignment 训练留在权重里的底色。prompt 是写在指令里的字，alignment 是写在权重里的倾向，**后者压得住前者**。

这也是我暂时更相信"动权重"的原因：
- prompt 可以让模型**"像"某个角色**——表面语气、遣词、个别习惯
- 但要让模型更稳定地**"是"某个角色**——一致的性格内核、敢说敢做、不轻易被对齐层和上下文漂移吃掉，目前看还是需要训练侧介入

本文调研的两个案例（Neuro-sama 和 Character.AI）都选择了动权重，下面分别展开。

---

## 两个案例：Neuro-sama 和 Character.AI

下面这两个是我调研得较深的生产级案例。一个代表"个人 × 单角色 × 深度定制"，一个代表"公司 × 任意角色 × 平台化"。把它们放一起看，大致能勾勒出"把人格训进模型里"这件事的两个典型形态。

### 背景

**Neuro-sama** —— VTuber **Vedal**（Vedal987，匿名）在 Twitch 做的 AI 主播，是全球观看人数最多的 AI VTuber 之一。2022 年 12 月首秀时用的是 GPT-3 API + prompt 工程（v2 阶段，人格完全由 prompt 构建）。2023 年中开始迁移到自己微调的小模型——这是 v3+ 阶段，也是本文关心的阶段。从此"人格在权重里，情境在 prompt 里"。

**Character.AI** —— 由 **Noam Shazeer** 和 **Daniel De Freitas** 于 2021 年 11 月创立，两人都是 Google Brain 前员工、LaMDA 团队核心，Shazeer 是 2017 年 "Attention Is All You Need" 论文的八位作者之一。2024 年 8 月，Google 以授权协议签下了 C.AI 的研究成果并雇走了 32 位研究员（基本等于整个 pre-training 团队），Shazeer 回 Google。此后 C.AI 的架构从"自研 foundation model" pivot 到"第三方 pre-training + 自家 post-training"。他们把 post-training 里负责人格学习的那一层叫 **Character Training**，也是本文关键词的英文来源。

和 Neuro-sama 最大的不同是——C.AI 训的不是"成为某一个角色"的模型，而是"能根据描述扮演任何角色"的模型。

### 直接对比

| 维度 | Neuro-sama | Character.AI |
|---|---|---|
| 主体性质 | 个人开发者 | 商业公司 |
| 训练目标 | 成为 Neuro 这一个角色 | 学会根据描述扮演任意角色 |
| 模型规模 | ~2B（疑似，见下文） | 未披露 |
| 训练方法 | 迭代 SFT | "Character Training"（机制未披露） |
| 训练数据 | Twitch 对话人工筛 | 完全不公开 |
| 扩展性 | O(N)：新角色 = 重训一次 | O(1)：新角色 = 用户写一段描述 |
| 行动层 | typed action protocol + 游戏控制器 | 主要是聊天产品交互 |
| 公开程度 | LLM 内部几乎零；游戏接口和部分游戏集成开源 | infra 充分，Layer 2 是黑箱 |

### Neuro-sama 的做法

**阅读提示**：Vedal 对技术细节刻意不公开。下面一些被广泛转述的数字（特别是"2B 参数 + q2_k 量化"）**我没找到可验证的一手出处**——Wikipedia 不提，Fandom Wiki 是主要来源，引用的"某次 Vedal 直播"没有存档链接。这一节的数字请带一层折扣看。

**有一手出处的事实**：

- 基于某个开源 LLM 做 custom fine-tune（具体哪个未公开）—— Vedal 直播
- 训练数据是 Twitch 流对话，**他本人手工筛选**（自己 + 其他人授权的数据）—— Vedal [Threads 帖子](https://www.threads.com/@sinisterpixel/post/DEa_XlXoKjK)
- 推理 self-hosted，跑在他自己的 GPU 上
- v3+ 之后"人格在权重里，prompt 只管情境"（"你在玩 Minecraft"、"你在和 Evil Neuro 对话"）
- 游戏接口是 **typed action protocol**：游戏注册 action、schema、context / force action，Neuro 返回 action name + JSON 参数，游戏侧负责校验和执行（通过 [官方 SDK](https://github.com/VedalAI/neuro-sdk) 可验证）

**二手说法（需打折扣）**：2B + q2_k 参数规模；LoRA 还是 full fine-tune；Evil Neuro 是 LoRA 切换还是 prompt 变体。

**一个反面观察**：市面上不少开源项目（kimjammer/Neuro、Open-LLM-VTuber、moeru-ai/airi、AIRIS-VtuberAI 等）公开声明要"复刻一个 Neuro-sama"，它们管线都搭全了——但没一个做出了 Neuro-sama 那种"感觉"。Vedal 在访谈里提过数据积累很重要，但没详细展开"感觉"差异的具体原因。

### Neuro-sama 更有意思的一层：分层代理系统

如果只盯着"人格在权重里"，其实会错过 Neuro-sama 最有工程味的一面。VedalAI 公开仓库里更值得看的不是模型权重，而是**主模型怎么被限制成一个高层决策器**。

[neuro-sdk](https://github.com/VedalAI/neuro-sdk) 的接口不是让 LLM 直接操作游戏，而是让游戏注册一组 action：每个 action 有名字、自然语言描述、JSON schema。游戏可以发 context 告诉 Neuro 当前发生了什么，也可以发 force action 要求她在几个 action 里做选择。Neuro 返回 action name + JSON 参数后，游戏侧还要自己校验，再返回 action result。

这比"文本进、文本出"更具体：**LLM 只输出低熵、可校验的意图；真正的执行交给下游控制器**。

几个公开集成能看出这个模式：

- **Inscryption**：mod 监听游戏事件，把手牌、道具、地图、战斗状态序列化成 state，强制 Neuro 在合法动作中选择，然后由 `NeuroMouse` 去点击 UI。Neuro 不是直接"点屏幕"，而是在约束选项里做决策。
- **Among Us**：仓库里有记录游戏数据、训练 LSTM 的代码，输出包括移动方向、report、vent、kill 等动作；C# 插件再把这些输出转成移动、按钮点击、路径规划和小游戏 solver。这是一个"自训控制模型 + 确定性求解器"的具身系统，不是纯 LLM。
- **Cyberpunk 2077**：插件把对话选项、短信回复、quickhack、召车、自动驾驶等能力暴露成高层 action。Neuro 选 intent，插件校验 ID，再调用 Redscript、注入按键或启动游戏内自动驾驶。
- **swarm-control**：名字里有 swarm，但公开代码更像 Twitch 观众事件控制平面：Bits 交易、redeem、订单状态、游戏 websocket、PiShock 特殊处理。它不是 LLM subagent 集群的证据，更像"直播观众蜂群"把事件打进游戏和外部设备。

所以我现在更愿意把 Neuro-sama 写成一套四层结构：

1. **人格层**：fine-tuned LLM，决定她说话像谁
2. **情境层**：prompt / context，告诉她现在在干什么
3. **动作层**：typed action protocol，把自然语言意图压成可校验命令
4. **执行层**：游戏插件、路径规划、点击器、自训控制模型、直播事件系统

这也是它比大多数"AI VTuber 复刻"难复刻的地方。别人复刻的是第一眼能看到的 pipeline：LLM、TTS、STT、Live2D；Vedal 真正长期积累的是**角色人格 + 具身控制 + 直播互动**这整套系统。

### Character.AI 的做法

C.AI 讲得比较清楚的部分都集中在 infra 和 prompt 层。**基础设施层面**（来自 [ZenML 整理的 scaling talk](https://www.zenml.io/llmops-database/scaling-a-high-traffic-llm-chat-application-to-30-000-messages-per-second) 和 [research blog](https://research.character.ai/optimizing-inference/)），他们每秒处理 30,000 条消息，95% 的请求能命中 cache。围绕 KV cache 做了一系列优化——Multi-Query Attention 相对基线降低 5× 以上、以 int8 精度做量化感知训练（QAT）、相邻 attention 层共享 KV cache——叠加起来总 KV cache 开销压到了 1/20 以下。

**Prompt 层**有官方的 [Character Book](https://book.character.ai/) 说明角色定义的字段结构：Name，50 字以内的 Short Description，500 字以内的 **Greeting**（通常被认为是对人格塑造影响最大的字段），以及不限长度的 Personality 和 Example Dialogues。官方还开源了 prompt 管理工具 **Prompt Poets**——YAML + Jinja 模板系统，上下文溢出时角色定义的优先级高于对话历史。**用户反馈层**是简单的 1-4 星评分加消息编辑，官方声称不会据此修改 base model 权重。

**Layer 2（Character Training 本身）则从未被系统披露过**。

业内能找到的最接近的参考实现是 Nathan Lambert 在 [interconnects.ai](https://www.interconnects.ai/p/opening-the-black-box-of-character) 发表的复现实验：用 GLM-4.5-Air 作为 base，写 "I am..." 第一人称的人格宪法，让模型在宪法指导下生成回复 vs base model 的原始回复，组成 DPO 偏好对训练。**Lambert 原文是 "We used..."——是他团队在做实验演示，不是 Character.AI 披露的方法**。C.AI 真正怎么做，我们无从验证。

一个相关的侧证：Anthropic 在 [Claude's Character](https://www.anthropic.com/news/claude-character) 里讲他们用 "character 变种的 constitutional AI"——训练数据是 Claude 自己生成的合成数据，但"性状的构建与调整是一个相当手工的过程，依赖人类研究员仔细观察每个特质如何改变模型行为"。这至少说明"合成数据 + 人类 curate 性状"是一类值得严肃对待的方法，但不代表 C.AI 就是这么做的。

---

## 学术方向

生产层面其实还有其他案例值得看（Inflection Pi、Anthropic Claude 都有公开资料），我还在一一求证中，本文先不展开。相比把论文列全，我现在更倾向于把论文部分压短：学术结果提供方法坐标，但这篇真正有价值的地方还是生产系统怎么把人格、协议和执行层接起来。

学术层面倒是有几个论文可以一提。**BIG5-CHAT**（ACL 2025）在 100K 条基于 Big Five 人格的合成对话上做 SFT/DPO；**OpenCharacter**（arxiv 2501.15427）用 LLaMA-3 8B + 20K 合成角色做元角色训练的开源尝试；**FinePE** 则用 per-subtrait 的 MoE-LoRA 做人格细粒度控制。这些工作多数基于 Big Five 这种标准化人格特质维度做受控实验，和生产产品追求的"有灵魂感"不完全是一件事，但提供了方法论层面的实证基础。

---

## 第三条路：activation engineering

回到"Agent 工程师能不能上手"这个问题——前面讲的两条路对个人或小团队都不现实：Neuro-sama 需要几年的数据积累，Character.AI 需要 post-training 基建。是否存在第三条路？

**activation engineering** 可能是一个有希望的方向——学术里近两年很活跃，但还没见产品化。它的核心想法是：**既不改权重，也不依赖 prompt，而是在推理时直接修改模型内部的激活值**。

具体做法是：先用对比样本（有人格 A 的回复 vs 中性回复）在模型内部找出一个"A 人格方向"的向量 `v`；推理时，在某一层的残差流上加 `α·v`，就能让模型表现出对应的人格倾向，**完全不需要训练**。

三条值得关注的研究线：

**① PERSONA（2026 preprint）**
在 PersonalityBench 上，**无训练的 activation steering 拿到 9.60 分，SFT 微调拿到 9.61 分**——几乎打平。用向量代数达到了微调的效果，这对没有 GPU 的人是意义重大的发现。

**② SAS Personality Sliders（2026 preprint）**（Sequential Adaptive Steering）
把"外向性 / 神经质 / 开放性"等 Big Five 维度做成可连续调节的"滑杆"。用户滑到哪一格，就在推理时注入对应强度的人格向量。非常优雅，但目前主要在 Big Five 这种标准化特质上验证过。

**③ Anthropic 的 [persona vectors](https://www.anthropic.com/research/persona-vectors)（2025）**
这是目前最有产品味的一条。Anthropic 不仅用 persona vector 做**监控**（看模型在对话中是否偏离预设人格），还提出了"**接种**"（vaccination）——在训练阶段预先注入少量 persona vector，让模型**学会抵抗**后续训练中被污染成该人格的风险。这给 character training 和安全对齐的结合打开了新方向。

但 activation engineering 也有三个现实限制：

- **需要白盒模型访问**——对 OpenAI / Anthropic 纯 API 用户不可行，只适用于能拿到权重的开源模型
- **所有验证都在 7B–8B 级别**——70B+ 上是否依然 orthogonal、可叠加，没人验证过
- **还没跨越"论文到产品"那条沟**——目前没有任何一个公开产品把 activation engineering 作为主要人格手段

对不想动权重训练的场景，activation engineering 是目前学术界讨论的一条路径。工具链以学术 demo 为主（[repeng](https://github.com/vgel/repeng) 是一个可用的开源实现）。

---

## 我真正好奇但没答案的问题

留几个开放问题，算这篇博客的收尾：

**① Evil Neuro 到底是 LoRA adapter 切换还是同模型 prompt 变体？**
这决定"人格在权重里"这个说法有多硬。如果 Evil Neuro 只是换个 prompt 就能出来，那 Neuro-sama 的 "weight-based personality" 其实比宣传的要浅。Vedal 没讲过。

**② activation engineering 能 scale 到 70B+ 吗？**
学术目前所有验证都在 7B–8B 级别。大模型的激活空间更复杂，persona 向量还能保持 orthogonal 吗？多维度人格（比如同时调"外向 + 攻击性 + 学识"三维）在大模型上还 work 吗？没人验证过。

**③ "灵魂"能不能用开源 20B 模型在小团队手里复刻？**
Neuro-sama 的特殊性被归结为"几年的数据积累"。如果参数量不是关键、数据的"人味"才是——那理论上小团队只要熬够时间，是有机会做出自己版本的"有灵魂的 AI"。这个假设目前没人验证过。

**④ Character Training 和 RLHF / constitutional AI 的边界在哪？**
C.AI 的 Character Training、Anthropic 的 constitutional AI、OpenAI 的 GPT-4o 人格漂移背后的 post-training——这三者在技术实质上是什么关系？是同一大类"合成数据 + 偏好学习"方法的几个变种，还是根本不同的东西？由于 C.AI 和 OpenAI 都几乎零披露，这问题现在没答案。

**⑤ "蜂群"到底是 Agent 集群，还是直播事件系统？**
VedalAI 公开的 `swarm-control` 更像观众事件控制平面，不是 LLM subagent 架构。但它提出了另一个值得看的方向：AI 主播不是只和用户一对一聊天，而是在一个直播场里同时处理观众、游戏、道具、外部设备和角色表演。这个"场"本身也许比单个模型更接近 Neuro-sama 的核心产品形态。

**⑥ 如果一个人时间有限，怎么部署一个真正有自己人格的 AI？**
这是我最关心的终极问题。现在看，一个实际可行的路线可能不是"训练一个无所不能的大模型"，而是反过来分层：用一个自己能负担、能反复微调的小模型负责人格和最终表达；复杂任务交给更强的大模型或 subagent 做，但它们不直接对用户说话。

换句话说，**20B 级别的小模型也许足够承担简单场景里的角色文本和稳定语气**；真正复杂的推理、搜索、代码、游戏控制、工具调用，则交给成熟大模型或专门 agent 在后台完成。前台回复用户的，始终是那个被训练出人格的小模型。这样既保留了"这个 AI 像它自己"的连续性，又不用要求小模型具备所有复杂能力。

这条路很像 Neuro-sama 公开接口里透露出来的分工：人格模型负责意图和表达，下游系统负责执行。区别是，对个人开发者来说，最现实的版本可能是"小人格模型 + 大模型 subagent 群 + 工具层"。

另一条路则要看模型厂商。也许未来的大模型会提供比"用户自己写一大段 character prompt"更灵活、更持久的人格注入方式：不是把角色写在上下文里，而是在 post-training、adapter、activation steering、长期 profile 或其他更底层的机制里，把"角色扮演"变成模型本身擅长的能力。Character.AI 的初衷大概就在这个方向：不是每个角色都靠用户临时 prompt 出来，而是先训练一个天然擅长进入角色的模型。

这也回到了开篇那个更现实的问题：如果想拥有一个真正"像它自己"的 AI，工程上到底应该从哪里下手？

---

## 延伸阅读

**Character.AI / Character Training**

- Nathan Lambert. [*Character Training*](https://www.interconnects.ai/p/character-training) — 概念介绍
- Nathan Lambert. [*Opening the Character Training Pipeline*](https://www.interconnects.ai/p/opening-the-black-box-of-character) — Layer 2 机制推断的原始出处
- Character.AI. [*Optimizing AI Inference at Character.AI*](https://research.character.ai/optimizing-inference/) — infra 细节
- Character.AI. [*Character Book*](https://book.character.ai/) — 官方 prompt 层文档

**Neuro-sama**

- [VedalAI/neuro-sdk](https://github.com/VedalAI/neuro-sdk) (accessed: 2026-04-27) — 官方游戏接口 SDK
- [VedalAI/neuro-inscryption](https://github.com/VedalAI/neuro-inscryption) (accessed: 2026-04-27) — typed action + UI 自动化的典型样本
- [VedalAI/neuro-amongus](https://github.com/VedalAI/neuro-amongus) (accessed: 2026-04-27) — 自训 LSTM 控制模型 + 游戏 solver
- [VedalAI/neuro-cyberpunk](https://github.com/VedalAI/neuro-cyberpunk) (accessed: 2026-04-27) — 高层 action 委托给游戏系统执行
- [VedalAI/swarm-control](https://github.com/VedalAI/swarm-control) (accessed: 2026-04-27) — Twitch 观众事件控制平面
- Vedal 的 [Threads 训练数据说明](https://www.threads.com/@sinisterpixel/post/DEa_XlXoKjK)
- [kimjammer/Neuro](https://github.com/kimjammer/Neuro) + [dev logs](https://blog.kimjammer.com/neuro-dev-log-1/) — 最认真的开源复刻，8 篇开发日志详细记录了 prompt 复刻 Neuro-sama 的阶段性限制
- [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) — 模块化 pipeline 框架
- [moeru-ai/airi](https://github.com/moeru-ai/airi) — 最雄心勃勃的复刻，web-first 架构

**Prompt / Persona Prompting**

- Zheng et al. [*When "A Helpful Assistant" Is Not Really Helpful*](https://aclanthology.org/2024.findings-emnlp.888/) (accessed: 2026-04-27) — prompt persona 效果不稳定的实证研究
- Lutz et al. [*The Prompt Makes the Person(a)*](https://aclanthology.org/2025.findings-emnlp.1261/) (accessed: 2026-04-27) — sociodemographic persona prompting 的刻板化与代表性偏移
- Dorner et al. [*Do Personality Tests Generalize to Large Language Models?*](https://openreview.net/forum?id=zKDSfGhCoK) (accessed: 2026-04-27) — 人格测试迁移到 LLM 的有效性问题
- Bodroža et al. [*Personality testing of large language models*](https://pmc.ncbi.nlm.nih.gov/articles/PMC11461045/) (accessed: 2026-04-27) — LLM 人格问卷的时间稳定性问题

**Activation Engineering**

- Feng et al. [*PERSONA*](https://arxiv.org/abs/2602.15669) (accessed: 2026-04-27) — PersonalityBench 上 activation steering 接近 SFT
- Hoppe et al. [*Controllable and explainable personality sliders for LLMs at inference time*](https://arxiv.org/abs/2603.03326) (accessed: 2026-04-27) — SAS / personality sliders
- Anthropic. [*Persona Vectors*](https://www.anthropic.com/research/persona-vectors) (accessed: 2026-04-27)
- [repeng](https://github.com/vgel/repeng) — 可上手的开源工具

**学术人格训练**

- [OpenCharacter](https://arxiv.org/abs/2501.15427) — arxiv 2501.15427，开源元角色训练尝试
- BIG5-CHAT（ACL 2025）— Big Five 特质控制
