# 数据集回顾与文献综述：微博社区管理中心「不实信息」判例数据集的研究机会

*整理时间：2026-07*

> **Status update (2026-07-21):** This is a direction-finding literature note,
> not a validated novelty or ethics statement. Its empirical claims are
> superseded by `research_notes.md`; publication requires the gates in
> `revision_protocol.md`, including a refreshed primary-source literature
> search, data-governance review and full-dump rerun.

## 1. 我们的数据集是什么

本仓库于 2018 年用 Selenium 爬取了[微博社区管理中心](https://service.account.weibo.com/)（Weibo Community Management Center, CMC）「不实信息」类公开判例页。历史报告称共有 **36,075 条**（截至 2018-08-30），但当前工作区没有全量 dump 或内容哈希，因此该数字尚未复现。每条记录是一个公开案卷页的抓取快照，可能包含：

| 字段 | 内容 | 说明 |
|---|---|---|
| `rumor` | 被举报微博原文 + 发布者资料（昵称、性别、地区、简介、主页链接、发布时间） | 谣言本体 |
| `reports` | 页面可见举报人的资料（昵称、性别、地区、简介、头像）+ **举报陈述文本** + 举报时间 | 最多展示 20 人；`actual_reporter_count` 保存页面标注的总数，不能恢复未展示者身份 |
| `official` | **平台官方判定文书**：认定结论、引用《微博举报投诉操作细则》具体条款、处罚决定（如"扣除信用积分 2 分"）、生效时间 | 结构化程度高的"判决书" |
| `looks` | 围观者列表（昵称 + 主页链接） | 案件的旁观受众 |
| `title` / `url` | 案件标题（"@A 举报 @B 不实信息"）与案件页链接 | — |

**关键点：这不只是一个“谣言文本 + 真假标签”数据集；它还可能记录页面可见的“举报 → 陈述 → 裁决 → 处罚 → 围观”多层信息。** 是否罕见、是否完整以及各字段覆盖率，都要在恢复 dump 和更新系统文献检索后验证。

## 2. 文献综述

### 2.1 谣言检测经典数据集：同源，但只取了"谣言文本"这一层

微博社区管理中心是中文谣言检测研究最重要的数据来源，但现有公开数据集几乎都**只保留了谣言文本和标签**，丢弃了案卷的其余部分：

- **Weibo-16**（Ma et al. 2016/2017）：2,313 条谣言 + 2,351 条非谣言，来自同一 CMC 平台，是中文谣言检测最常用 benchmark（见 [Rumor Detection on Social Media: Datasets, Methods and Opportunities](https://arxiv.org/pdf/1911.07199)）。
- **CED: Credible Early Detection**（[Song et al. 2018](https://arxiv.org/pdf/1811.04175)）：同源，聚焦转发/评论序列上的早期检测。
- **Weibo-20**（Rao et al. 2021）：3,034 谣言 + 3,034 非谣言，同源（见 [MCFEND](https://arxiv.org/html/2403.09092v1) 的综述部分）。
- **Weibo-Multi-Domain**（[Zhu et al. 2022](https://arxiv.org/pdf/2205.03068)）：44,728 条假新闻（24,690 来自 CMC），做了多领域划分和用户影响分析——是与我们规模最接近的同源数据集，但同样没有举报人陈述和官方判决文书。
- **MCFEND**（[WWW 2024](https://dl.acm.org/doi/10.1145/3589334.3645385)）：指出单一来源（微博）数据集训练的模型换个数据源性能大幅下降，呼吁多源数据。
- **LTCR**（[2023](https://arxiv.org/pdf/2306.07201)）：长文本中文谣言数据集，说明中文谣言资源仍然稀缺。
- [Examining the Limitations of Computational Rumor Detection Models Trained on Static Datasets](https://arxiv.org/pdf/2309.11576)：证明在静态老数据集上训练的检测模型随时间快速失效——直接提示我们 2018 年的数据做"检测"已过时，但做**时间纵向对比**反而是资产。

**结论：拿这份数据再做一个"谣言分类器"没有增量价值；它未被开发的价值在于举报人、判决文书、围观者这三层。**

### 2.2 众包事实核查（Community Notes）：当前最热的相关方向

2023–2026 年西方平台治理研究的爆点是 X（Twitter）的 Community Notes，以及 2025 年 Meta 宣布跟进（[Poynter](https://www.poynter.org/fact-checking/2025/does-x-community-notes-work-facebook/)、[MIT Tech Review](https://www.technologyreview.com/2025/05/19/1116367/can-crowdsourced-fact-checking-curb-misinformation-on-social-media/)）：

- [Can Crowdchecking Curb Misinformation? Evidence from Community Notes](https://pubsonline.informs.org/doi/10.1287/isre.2024.1609)（ISR 2024）：被公开纠错的帖子被作者删除的概率提升约 32%。
- [Community-based fact-checking reduces the spread of misleading posts](https://arxiv.org/pdf/2409.08781)、[Community notes reduce engagement with false information](https://pmc.ncbi.nlm.nih.gov/articles/PMC12478135/)：有效，但**时效性差**——只有 13.5% 的有效笔记在转发半衰期（5.75 小时）内展示。
- [Community notes increase trust in fact-checking](https://pmc.ncbi.nlm.nih.gov/articles/PMC11212665/)：众包纠错比专业机构核查更被信任。
- [A Survey on the Role of Crowds in Combating Online Misinformation](https://arxiv.org/pdf/2310.02095)：系统综述"群众"在对抗错误信息中作为标注者/评估者/创作者的角色。

**候选空白：先前收集的这批文献主要基于 X/Twitter。微博 CMC 可作为“用户举报 + 平台裁决”机制的历史材料，但本数据不是完整系统快照，中西比较还需要机制可比性、选择过程和制度背景的专门设计。**

### 2.3 微博社区委员会与平台治理：刚起步，且都缺举报人陈述数据

2025 年出现了一小波直接研究微博 CMC 的论文，说明这个题材正在被国际社区"发现"：

- [The Effects and Non-Effects of Social Sanctions from User Jury-Based Content Moderation Decisions on Weibo](https://dl.acm.org/doi/10.1145/3706598.3713154)（CHI 2025）：陪审团制裁对发帖行为的影响短暂（一个月内消退）、集中于男性被举报用户。
- [Unveiling Strategic Governance and User Dynamics in Weibo's Community-driven Content Moderation System](https://journalqd.org/article/view/9113)（JQD:DM / ICS 2025）：发现平台对社会敏感议题案件处罚更重、陪审员动机随时间衰减、**高频举报者呈现"自愿警察"或"滥用举报"两种模式**。
- [The empowerment effect of jury-based content moderation](https://www.sciencedirect.com/science/article/abs/pii/S0736585326000183)（2026）：陪审机制提高用户粘性。

这些研究聚焦**陪审员（投票者）**；而我们的数据聚焦**举报人（发起者）**且带有每个人的陈述文本、资料和精确时间——是上述文献链条中缺失的一环。

### 2.4 举报（flagging）行为研究：西方靠访谈，我们有行为大数据

- [Cleaning Up the Streets: Understanding Motivations, Mental Models, and Concerns of Users Flagging Social Media Content](https://arxiv.org/pdf/2309.06688)（CSCW）：基于 22 人访谈研究举报动机。
- [Incorporating Procedural Fairness in Flag Submissions](https://dl.acm.org/doi/full/10.1145/3797820)（ACM TSC 2025）：举报流程的程序正义设计。
- [Evaluating reporting mechanisms under the Digital Services Act](https://www.researchgate.net/publication/392934822)（2025）：欧盟 DSA 背景下的举报机制评估——监管层面正需要实证数据。
- [Study on factors influencing users' willingness to participate in misinformation purification on Weibo](https://www.emerald.com/ajim/article-abstract/doi/10.1108/AJIM-07-2024-0541/1250456)（2025）：问卷 + SEM 研究微博用户参与"净化"的意愿。

**候选空白：先前整理的这一支文献多用访谈/问卷。若历史记录数与字段覆盖率经 manifest 和重跑确认，本数据可补充公开判例页中可见举报资料与陈述的描述性证据；它不代表全部举报行为。**

### 2.5 LLM 时代的错误信息与内容审核研究

- [CANDY: Benchmarking LLMs' Limitations and Assistive Potential in Chinese Misinformation Fact-Checking](https://arxiv.org/pdf/2509.03957)（2025）：中文错误信息核查 LLM benchmark，发现 LLM 单独核查不可靠、但可辅助人类——中文核查 benchmark 正是热点。
- [Policy-as-Prompt: Rethinking Content Moderation in the Age of LLMs](https://dl.acm.org/doi/10.1145/3715275.3732054)（FAccT 2025）：把平台政策直接写进 prompt 做审核，面临"政策→prompt 转换保真度"难题。
- [Content moderation by LLM: from accuracy to legitimacy](https://link.springer.com/article/10.1007/s10462-025-11328-1)（AI Review 2025）：LLM 审核的评价标准应从准确率转向"正当性"（程序、解释、一致性）。
- [Multi-agent Systems for Misinformation Lifecycle](https://arxiv.org/pdf/2505.17511)、[2nd Workshop on Misinformation Detection in the Era of LLMs (MisD @ ICWSM 2026)](https://workshop-proceedings.icwsm.org/pdf/2026_31.pdf)：多智能体、全生命周期视角是新趋势。

**候选空白：Policy-as-Prompt 和 LLM-as-judge 研究需要带政策引用与处罚结果的历史裁决材料。`official_text` 可能提供这些字段，但“每条都有”、抽取准确率和文献新颖性均未验证，不能把它直接称为完整的“平台司法判例库”。**

## 3. 研究机会（按推荐度排序）

### ⭐ 方向 A：LLM 能否复现平台裁决？——"平台判例"基准（最推荐）

**想法**：从 `official_text` 中抽取结构化标签（认定结论 / 引用条款号 / 处罚类型与力度），构建任务：给定被举报微博 + 举报人陈述，让 LLM 扮演平台裁决者，预测认定与处罚，并与真实裁决对比。

- **潜在增量**：候选资料可能同时具有「案情 + 页面可见举报陈述 + 引用条款 + 处罚」。是否没有可比公开数据集、记录规模是否为 36k，都要通过更新检索与 manifest 确认。
- **可做的问题**：LLM 与平台裁决的一致性有多高？不一致集中在哪类案件？LLM 的处罚是否比平台更严/更松？对造谣者性别、地域是否存在与平台不同的偏差（公平性审计）？给 LLM 提供细则条款（policy-as-prompt）能提升多少？
- **成本**：中等。主要工作是正则/LLM 抽取 `official_text` 结构化标签 + 跑评测。
- **目标会议**：FAccT / CHI / ICWSM / ACL。

### ⭐ 方向 B：谁在举报谣言？——大规模举报者行为的量化描述（最稳）

**想法**：在记录规模复现后，对案件页可见举报人做受限画像与行为描述：粗粒度账号类别、举报陈述形式（URL / #微博辟谣# 话题 / 其他文本）、页面可见的重复举报者分布、举报到裁决的时延。性别、地域和原文是否进入研究，需要单独的必要性与伦理审查。

- **潜在增量**：先前 flagging 文献多用访谈，而候选微博 CMC 文献主要研究陪审员。是否已有可比的举报人陈述数据尚需系统检索。
- **可检验问题**：公示页可见举报活动的集中度如何？启发式识别的机构类账号占比如何？陈述中有多少包含 URL 或其他可编码的可核验来源？这些问题不能直接推出职业身份、国家参与或动机。
- **成本**：低-中。纯数据分析 + 文本编码，可直接出一篇 JQD:DM / ICWSM 量化描述型论文。
- **可与 Community Notes 文献做中西机制对比**，讨论价值高。

### 方向 C：举报陈述作为证据的中文声明验证（claim verification）语料

举报陈述中大量包含辟谣证据（链接、引用官方通报），`official_text` 给出最终裁定。可构建「声明 + 众包证据 + 裁决」三元组，作为中文 evidence-based fact-checking 语料，呼应 [CANDY](https://arxiv.org/pdf/2509.03957) 指出的 LLM 单独核查不可靠、需证据辅助的结论。

### 方向 D：时间纵向研究——重爬 2026 年数据，对比 LLM 前后时代

若未来确认 CMC 仍可合规访问，并重写爬虫采集一批新判例，可研究两件事：

1. **谣言生态八年变迁**：话题、文风、AI 生成痕迹、处罚政策变化（呼应 [静态数据集失效](https://arxiv.org/pdf/2309.11576) 的发现，把"数据老"变成"有历史纵深"）。
2. **数据污染感知评测**：历史案例可能进入模型训练语料；如果未来能合规获取新案例，可把时间作为污染风险变量，但不能把是否污染当成已知事实。

风险：现在的页面结构、登录与反爬与 2018 年完全不同，工程量不小，且需注意合规。

### 方向 E：围观者与举报网络分析

`looks` + 页面可见举报人 + 被举报者可构成三方共现网络，用于描述重复共现与结构模式。仅凭共现不能识别协同举报（brigading）或旁观因果效应；这更适合作为 B 的探索性附录。

## 4. 需要正视的限制

1. **数据年代**：2018 年截止。做"检测"已过时；做行为/治理/基准研究反而合适，或按方向 D 补新数据。
2. **隐私与伦理**：数据含真实昵称、主页 URL、头像、地区与可能敏感的指控。当前数据被分类为 restricted research data；公开可见不等于允许再分发或传给第三方 API。简单昵称哈希不构成匿名化。
3. **采样偏差**：只有被举报且被受理公示的案件，看不到未被举报或未公示的驳回；页面最多展示 20 位举报人。`actual_reporter_count` 只能量化截断下界，不能恢复未知的展示选择机制。
4. **数据可得性**：当前工作区没有全量 dump，也没有内容哈希；在 manifest 和受控访问恢复前，不讨论公开托管。

## 5. 建议的下一步

1. 恢复受控 dump，生成 SHA-256 manifest，并完成数据治理决定。
2. 完成双人标注与仲裁，验证裁决解析和账号类型启发式。
3. 用修订代码重跑方向 B，只陈述公示页可见举报者的描述结果。
4. 验证历史规则版本后，按 `benchmark_protocol.md` 执行方向 A。
5. 是否重写爬虫补新数据需要单独的合规与工程评估，不能由本综述直接授权。
