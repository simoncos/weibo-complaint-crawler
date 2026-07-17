# 研究备忘录：微博社区管理中心「不实信息」判例数据集

*整理：2026-07（本文档是全部研究工作的索引与综述；各专题细节见对应文档）*

## 文档索引

| 文档 | 内容 |
|---|---|
| [literature_review.md](literature_review.md) | 数据集回顾、文献综述、五个候选研究方向（A-E） |
| [full_dump_report.md](full_dump_report.md) | 全量 36,075 案的描述统计（`analysis.stats` 生成） |
| [concentration.md](concentration.md) | 举报集中度（Gini/Lorenz）、类型×年、量刑×年、规章×年（`analysis.concentration` 生成） |
| [reporter_profiles.md](reporter_profiles.md) | Top 10 连环举报者画像（`analysis.reporter_profiles` 生成） |
| [pilot_eval.md](pilot_eval.md) | 方向 A 试点：LLM 盲判 40 案 vs 平台真实裁决 |
| 本文档 | 核心发现综述与研究路线图 |

## 数据集概况

- **36,075 个判例**（2012-06 至 2018-08，约七年跨度，举报量峰值在 2015 年），
  69,769 条举报陈述，38,260 个独立举报者。
- 每案为完整裁决案卷：被举报微博 + 发布者资料、举报人资料 + 举报陈述、
  官方判定文书（结论/引用条款/处罚/生效时限）、围观者列表。
- 判决文书解析覆盖率 99.2%（`analysis.official_parser`，余 0.8% 为早期
  自由文本与平台测试记录）。
- 方向 A 基准：35,187 个可用实例（`benchmark.build_benchmark`，已匿名化）。

## 核心实证发现

**F1 — 公示案卷几乎全部是"举报成立"。** 98.8% upheld，仅 3 例明确驳回。
公示档案存在强选择偏差：看不到未受理与不成立的举报。所有下游分析都要
带着这个前提。

**F2 — "众包举报"实为极不均衡的混合治理。** Gini 0.434；Top 1 账号
「谣场现形记」独占 10.3% 的举报（7,172 案，且 99.9% 集中在 2015 年内，
更像一场工业化批量清理运动）；84.9% 的举报者只出现一次。参与主体混合了
职业辟谣者、普通网友、媒体、平台自身（微博管理员）与国家力量。

**F3 — 国家执法者 2017 年显性进场。** 政务类举报 2016 年 172 条 →
2017 年 1,210 条（与《网络安全法》生效同年）。贵港市三个网警巡查执法
账号合计约 1,000 案，陈述仅"举报违规"四字，举报对象是数月前的旧帖
（中位延迟 450-2,971 小时）——回溯性执法清扫，与民间辟谣的实时响应
（12-38 小时）形成鲜明对照。

**F4 — 平台"立法"三代更替，量刑随年代轻刑化。** 规章：
《新浪微博社区管理规定(试行)》(2012-13) → 《微博社区管理规定(试行)/(正式)》
(2014-16) → 《微博举报投诉操作细则》(2017-18)；主罚条款 第22条 → 第23条 →
第19条。禁言处罚占比从 2012 年约 23% 降至 2015 年后约 5%；扣分档位收敛到
2 分（81%）。

**F5 — 举报陈述的证据质量整体走低。** 附证据链接的陈述占 14.4%，且
2016 年后从约 20% 崩落到 3-7%；#微博辟谣# 话题使用率 16.3%。大部分举报
是无证据的"裸举报"。

**F6 — 存在"认定不实但不处罚"的裁决类别。** 对善意转发灾害求助类谣言的
普通用户，平台常只作辟谣声明、不引条款不处罚（如 2014 鲁甸地震寻人系列）。
平台在区分恶意源头与善意传播者，但案卷材料中没有显式信号。

**F7 — LLM 盲判试点（40 案）：结论易、量刑难。** 裁决结论一致率 97.5%，
但条款精确匹配 60%、处罚类型 Jaccard 53%、扣分 MAE 1.12。分歧主因：
(a) F6 的不处罚类别无从推断；(b) 量刑由年代而非内容驱动（2012 年地沟油
偏方罚 5 分+禁言，官员性丑闻捏造仅扣 2 分，与内容严重性直觉相反）；
(c) 同年代内条款漂移。详见 pilot_eval.md。

## 对两个主攻方向的含义

**方向 B（谁在举报谣言 → JQD:DM / ICWSM 量化描述型论文）**：F2/F3/F5
构成完整的 findings 骨架——集中度、五种举报者原型（工业化辟谣者/模板
搬运工/国家执法者/平台自查/调查型辟谣者）、国家进场时点、证据质量演变。
与 Community Notes 文献的"分布式志愿者"图景对照即是讨论章节。

**方向 A（LLM 复现平台裁决 → FAccT / ICWSM）**：试点表明"结论"接近
天花板（97.5%），基准的真正难点与价值在**条款引用与量刑**。核心实验设计：
零知识 / 年代提示 / policy-as-prompt（当期规章全文）三条件对比；
headline 指标用量刑 MAE 与宽严方向偏差（LLM vs 平台孰严）。F4 的
"同案不同年不同罚"也支持一个独立的公平性审计章节。

## 路线图与状态

- [x] 文献综述与方向论证（literature_review.md）
- [x] 判决文书结构化解析器（覆盖 99.2%）+ 单元测试
- [x] 全量描述统计 / 集中度 / 画像分析
- [x] 匿名化基准构建（35,187 实例）+ 分层抽样 + 评分器
- [x] 40 案盲判试点与错误分析
- [ ] 正式 LLM 评测（需 `ANTHROPIC_API_KEY`）：136 案 × 3 条件，
      命令见 pilot_eval.md「Next steps」
- [ ] 找回三代规章全文（判决中有原始链接，可查 Web Archive）用于
      policy-as-prompt 条件
- [ ] 方向 B 论文初稿（图表：Lorenz 曲线、类型×年堆叠图、量刑×年）
- [ ] 数据发布前的完整匿名化与伦理审查（普通用户假名化；政务/机构等
      公共主体可保留）

## 复现命令

```bash
# 数据：mongo shell 导出 (HK_DEV.WEIBO_COMPLAINT.json)，loader 自动识别格式
python -m tests.test_analysis                                  # 单元测试
python -m analysis.stats dump.json --markdown report.md        # 描述统计
python -m analysis.concentration dump.json --out-dir out/      # 集中度+时间
python -m analysis.reporter_profiles dump.json --top 10        # 举报者画像
python -m benchmark.build_benchmark dump.json instances.jsonl  # 构建基准
python -m benchmark.sample instances.jsonl sample.jsonl --per-stratum 34
python -m benchmark.run_eval sample.jsonl --rules xize.md      # LLM 评测（需 API key）
python -m benchmark.score sample.jsonl predictions.jsonl       # 评分
```
