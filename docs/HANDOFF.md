# 交接文档（Handoff）

*最后更新：2026-07-17，由远程 Claude Code 会话移交本地会话继续。*

## 一句话现状

文献综述、数据解析工具链、全量实证分析、方向 A 基准与 40 案盲判试点均已完成并
推送到分支 `claude/dataset-literature-review-khplj5`（基于 master，共 7 个 commit，
未开 PR）；下一步是找回三代规章全文（本地网络可直接跑现成脚本）并执行正式
LLM 评测（需 `ANTHROPIC_API_KEY`）。

## 本地环境搭建

```bash
git checkout claude/dataset-literature-review-khplj5
pip install anthropic pydantic requests beautifulsoup4   # 分析模块本身零依赖

# 数据（不在 git 里，97MB）：OneDrive 分享或本地备份
#   HK_DEV.WEIBO_COMPLAINT.json  (mongo shell 导出格式, 36,075 案)
# 放到任意路径，下面统一记为 $DUMP。loader 自动识别三种格式
# (mongo shell / JSONL / JSON array)，无需转换。

python -m tests.test_analysis          # 应全部 PASS（8 个测试）
python -m analysis.stats $DUMP         # 应输出 36,075 案统计
```

## 已完成的工作（读这三份就能接上上下文）

1. **[research_notes.md](research_notes.md)** — 核心发现 F1-F7 + 文档索引 +
   复现命令。**先读这份。**
2. **[literature_review.md](literature_review.md)** — 文献综述与方向论证
   （方向 A：LLM 复现平台裁决；方向 B：谁在举报谣言）。
3. **[pilot_eval.md](pilot_eval.md)** — 40 案盲判试点结果与错误分析
   （结论一致 97.5%，量刑是真正难点）。

代码结构：`analysis/`（解析+统计，零依赖）、`benchmark/`（基准构建/抽样/
评测/评分）、`scripts/fetch_rules.py`（规章抓取）、`tests/`。README 有各命令用法。

## 待办（按优先级）

### 1. 找回三代规章全文（本地网络即可，约 10 分钟）

```bash
python scripts/fetch_rules.py --out data/rules
```

方案、备选来源与**版本验证清单**在 [rules_retrieval.md](rules_retrieval.md)。
关键验证：gen1 第22条 / gen2 正式版第23条 / gen3 细则第19条须是不实信息处理
条款（条号来自全量判决统计，对不上就是快照日期取错）。`.gitignore` 已放行
`data/rules/*.txt`，验证后直接 commit。

### 2. 正式 LLM 评测（需要 API key）

```bash
# 数据侧（确定性，seed 固定可复现）
python -m benchmark.build_benchmark $DUMP instances.jsonl      # 35,187 实例
python -m benchmark.sample instances.jsonl sample.jsonl --per-stratum 34  # 136 案

# 三条件对比
export ANTHROPIC_API_KEY=...
python -m benchmark.run_eval sample.jsonl --out zero_shot.jsonl                 # 条件1 零知识
#   条件2 年代提示：给 run_eval 加 --era-hint 开关（未实现，见下方“待改代码”）
python -m benchmark.run_eval sample.jsonl --rules data/rules/gen3_xize_2018.txt # 条件3 policy-as-prompt
python -m benchmark.score sample.jsonl <predictions>.jsonl                      # 任何预测都可评分
```

**待改代码**（小改动）：
- `run_eval.py` 目前 `--rules` 只接一个文件；按层跑不同年代规章时，要么按层
  切分 sample 分别跑，要么加 per-era rules 映射。
- 条件 2「年代提示」：在 `render_case` 里已含发布时间，只需在 system prompt
  中告知「按案发年代的平台惯例裁决」即可作为轻量条件。
- 试点发现的「认定不实但不处罚」类别已写进 prompt；schema 无需改。

### 3. 方向 B 论文初稿

Findings 骨架已齐（见 research_notes.md F2/F3/F5 + concentration.md +
reporter_profiles.md）。建议图表：Lorenz 曲线（数据在
`analysis.concentration --out-dir` 输出的 `lorenz.csv`）、举报者类型×年
堆叠图、量刑×年。目标：JQD:DM / ICWSM 量化描述型论文。

### 4. 数据发布前的匿名化审查

`benchmark/build_benchmark.py` 已做假名化（昵称→哈希、去 URL/头像），但
`official_text` 字段保留原文用于误差分析——公开发布前删除或同样匿名化；
docs/ 下的分析报告含头部账号真实昵称（公开页面数据，发表时按惯例处理，
普通用户建议假名）。

## 关键决策与坑（避免重新踩）

- **数据格式**：dump 是 mongo shell pretty 导出（`ObjectId(...)`），
  `analysis/load.py` 自动识别，别手动转格式。
- **判决解析覆盖率 99.2%**：剩余 0.8% 是 2012-13 自由文本判决和平台测试
  记录（"test"/"测试"），已决定不过度拟合，基准构建时自动排除。
- **条款抓取限定平台规章**：判决里会引用《刑法》《防震减灾法》甚至国际田联
  规则作证据，`official_parser` 只统计标题含「微博/社区」的规章后跟随的条号。
- **`/roles/guiding` 一个 URL 两代规章**：取快照必须分 2015 初/2016 中两个
  时点。
- **verdict 分类**：`upheld / upheld_informal（辟谣不处罚）/ upheld_harmful
  （有害信息，非不实）/ rejected / undetermined`；基准里 informal 并入
  upheld，harmful 排除。
- **量刑由年代驱动**（试点 F7）：任何裁决评测都要把案发年代作为变量，否则
  一致率会被年代混杂效应污染。
- **公示档案 98.8% upheld**：所有分析都有选择偏差前提（F1），论文里必须交代。
- **举报者年份归属**：约 1/3 陈述无 report_time（被删），crosstab 用
  rumor_time 年份回退（`analysis/concentration.py`）。
- 远程会话的遗留物：`docs/full_dump_report.md` 等由脚本生成后手工拷入
  （远程沙箱限制），本地直接用 `--markdown docs/xxx.md` 覆盖再生成即可。

## 分支与提交习惯

- 工作分支：`claude/dataset-literature-review-khplj5`（未开 PR；是否合回
  master 或开 PR 由你定）。
- 大文件（dump、zip）不入 git（.gitignore 已配）；`data/rules/*.txt` 例外放行。
