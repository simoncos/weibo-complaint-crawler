# 安全请求记录接入交接（2026-10-03，Asia/Hong_Kong）

ready_for_archive: true

本聊天范围内未完成事项：无。协调聊天核验及归档待执行；本聊天不自行归档。
协调聊天：`01a1001c-5653-7e03-816f-b10bbe79f9e7`。

## 基线和修改边界

- 仓库：`/Users/simoncbot/Documents/weibo-complaint-crawler`。
- 分支：`claude/dataset-literature-review-khplj5`。
- 初始及结束 HEAD：`28fcda2226c6fc6f16e97f237ef4762e02c79999`。
- 初始 tracked/untracked WIP 均为空；22 个既有 ignored 文件保留。
- 当前分支相对本地缓存的同名 origin 分支 ahead/behind 为 `0/0`。
- 本地 `master` 和缓存 `origin/master` 均为
  `a1577b1d0e399d7f5af12abbac7556b2f454770c`。未 fetch，缓存不是远端现状证明。
- 仅修改 `benchmark/run_eval.py`、`README.md`、`docs/benchmark_protocol.md`；
  新增 `benchmark/consumer_recording.py`、`tests/test_run_eval_offline.py` 和本交接。
  其余 40 个基线 tracked 非数据文件 SHA-256 不变。没有并发 WIP 被覆盖。
- 未读真实 dump、密钥或凭证；检查只使用合成输入及既有合成 fixture。
  未调用模型、安装包、提交、暂存、推送或部署。

## 实际接入

1. 在每次 `client.messages.create(**arguments)` 之前，对实际 kwargs 调用
   `record_final_request(..., api_flavor='anthropic-messages',
   representation='sdk_arguments')`。记录保存在 `run.request_record` 和
   `run.attempt_records[].request_record`。没有 SDK 网络字节观察的声明。
2. 完整对象按 `sorted-json-utf8-v1` 摘要；只投影允许的配置值，system、工具、
   schema 等内容只进入摘要。attempt 中不保存 prompts、system 文本、schema
   descriptions、headers 或凭证。异常只保存类别与类名，去除可能泄漏请求的
   `str(error)`。既有 `pred.reasoning_summary` 仍是受限研究输出。
3. 应用是唯一 retry 执行者：`Anthropic(max_retries=0)`。
   `--max-attempts` 默认仍为 3，限制每个 case 的 SDK 调用总数；保留原退避。
   `attempts` 保留原语义，新增 `sdk_call_attempts`、`max_attempts`、
   `retry_executor` 和 `sdk_max_retries`。mock 中每次调用对应一个被计数的
   transport 请求；这不等于实测真实 HTTP 流量。
4. `trigger` 为 `initial` / `sdk_error_retry` / `parse_repair`；
   `outcome` 为 `success` / `refusal` / `sdk_error` / `parse_failure`。
   parse repair 继续请求原始 system/messages，不添加反馈或改变实验条件，
   并记录原先失败回复的已报告 usage。它是业务解析后重试，不冒称 HTTP retry。
   refusal 立即结束。耗尽时仍只产出一个 `error` case；评分器不变，所有失败
   保留在原分母，未改条件、采样、gold 或规则选择。
5. 每次响应保留 SDK 的原始 input/output/cache token 数；缺失或无效数为
   `null`，有效的零保留。SDK 失败没有响应用量时保持未知。
   `cost_usd` 为 `null`；未加价格估计或 tokenizer，未做 token 校准。
   Anthropic 的原始 `input_tokens` 未冒称含缓存的完整 prompt 计数。
6. 原 `prompt_sha256 = SHA256(system + '\n---USER---\n' + user_prompt)` 不变。
   新摘要涵盖 kwargs，既不替代历史摘要，也不声称能重建旧请求；未回填旧结果。
7. dry-run 不导入 SDK、不读取 SDK 凭证，不调用模型；请求记录标为
   `planned_sdk_arguments`，attempt/call 为 0，attempt_records 为空。
   resume 只追加未完成 case，保留原输出字节，并核对新增 retry 配置和
   dry-run 模式。旧结果缺少这些字段时拒绝续写；新实验使用独立输出及 run。
8. 数据审批对 exact input SHA / provider / model / purpose / expiration 的验证、
   human-verified 规则及按 policy_date 选择的既有要求保留。安全摘要和 mock
   合成审批都不构成真实数据处理授权。

## 共用模块来源和同步

- 上游原始路径：`/Users/simoncbot/Documents/llm-kit/docs/consumer_recording.py`。
- 本地副本：`benchmark/consumer_recording.py`，逐字节相同，140 行 stdlib-only。
- 原始及副本 SHA-256：
  `e547f545b681475dc514978c4a1a42bc442ce190bb876e03d7467b2d9f4977bd`。
- 观察时 llm-kit HEAD：`a4aac84d23c90a05691776a9d58953bbc4675790`；该上游
  文件当前为 untracked 开发文件，不能将这个 HEAD 冒称模块已发布版本。
- 来源说明：上游 `docs/CONSUMER_VALIDATION.md` 和 `docs/CONSUMER_COVERAGE.md`。
  只接入必要的安全记录模块，未复制其余开发工具，也没有硬编码跨仓库 runtime
  导入或临时工具路径。
- 后续同步：先核对上游内容及 SHA，与本地副本比较；确认变更后整文件同步、
  更新来源 SHA 并运行以下检查。不要自动跟随未经核验的上游修改。
- 原依赖事实：项目无 llm-kit 包依赖/版本 pin，`requirements.txt` 只有既有 legacy
  crawler 的未锁定依赖，不是正式 benchmark lock。未新增 runtime 依赖。
  原 `requirements.txt` SHA-256 保持
  `ee4d152b0f6735a14f6e8bfa7b90e8685e552ea91dc28c66e34a5c450cea1d67`。
  当前 Python 为 3.14.3，Anthropic SDK 未安装；未创建新环境或安装依赖。

## 验证命令和结果

在目标仓库既有环境执行，全部 exit 0：

| 命令 | 结果 |
| --- | --- |
| `python3 -B -m tests.test_run_eval_offline` | 新增 18 项 unittest 通过；无需 SDK、key、网络 |
| `python3 -B -m tests.test_analysis` | 既有 25 项测试通过 |
| `python3 -B -m pytest -q -p no:cacheprovider` | 43 passed, 17 subtests passed |
| `python3 -B scripts/scan_sensitive_artifacts.py` | 敏感产物扫描通过（仅自动检查） |
| `git diff --check` | 通过；新增文件空白检查亦通过 |

离线入口为 `python -B -m tests.test_run_eval_offline`，已写入 README 和协议。
测试在 `main -> run_case -> mock messages.create -> mock transport -> JSONL ->
score_records` 链路观察实际 kwargs、构造参数、调用数及持久化数据，未将 expected
复制为 observations。socket 连接被显式阻断。mock SDK 默认故意模拟 2 次隐式
retry，因此移除生产构造器的 `max_retries=0` 会导致次数上限检查失败。

覆盖 success、terminal refusal、parse repair/耗尽、network error/恢复及混合失败；
1/2/4 次应用上限；kwargs 摘要变更检查和 prompt/schema/异常脱敏；已报告、未知和
无效 usage；resume 追加/全完成/配置不符/旧结果拒绝；dry-run 及不导入 SDK；
审批缺失/无效、历史条件/规则日期和输入禁用字段；已有输出拒绝覆盖。
四 case 合成集实际调用 8 次（1 success + 1 refusal + 3 parse + 3 network），
评分 attempted=4、scored=1、refusal=1、error=2、failure-adjusted agreement=0.25。

## 候选身份和核验材料

| 文件 | 最终 SHA-256 |
| --- | --- |
| `benchmark/run_eval.py` | `2d2d2a5b56eb7d3e737941a3a70fa6c60fec7c7360051a0401a499cbeeb048ca` |
| `benchmark/consumer_recording.py` | `e547f545b681475dc514978c4a1a42bc442ce190bb876e03d7467b2d9f4977bd` |
| `tests/test_run_eval_offline.py` | `c9f9e9c1ae14fc8420229cf78303b96817ea47c051997acb71b7e6d85100b47e` |
| `README.md` | `2fb86e390ef85516117fa92be5ab4e7eab9f8777bf5898b08201385180d949ab` |
| `docs/benchmark_protocol.md` | `2f4e69af54faa951ed395230aa58fd9bd6cdb601e6a81a956b29fd7c74f25530` |

`benchmark/run_eval.py` 原 SHA-256：
`8fa89a6ec0875bd80bc1053737d0ce448265d8628916bb37b76f60b428578b57`。
`docs/data_governance.md` 始终为
`34dc8853b25659f5362cb787ace9daf05e0635901ea004a1ae46110cc8c4297e`。

核验目录：`/private/tmp/weibo-consumer-integration-20261003/`。含 baseline.json、
identity.json、implementation.diff、offline/analysis/scanner/pytest.log，以及
最终 final-verification.json。临时材料仅作本地核验；本交接与项目测试为持久入口。

implementation.diff 覆盖上表五文件，排除本交接以免形成自引用 SHA。
生成顺序：`git diff --binary -- benchmark/run_eval.py README.md docs/benchmark_protocol.md`，
随后分别追加 `git diff --no-index --binary -- /dev/null benchmark/consumer_recording.py`
及相同命令对 `tests/test_run_eval_offline.py` 的输出。
源码/测试/使用说明 diff SHA-256：
`dd37822f65d46fae287e1f678c90787b5384d5116c7763a27ebe2b7c521c8d6a`。

## 未验证边界

只有源码、本地合成 mock 调用链及既有合成 fixture 证据。未验证真实 Anthropic
SDK 序列化、物理 HTTP 重试、provider 行为、真实 usage/费用、token 校准、正式
benchmark lock、CI、部署或研究有效性。真实 dump、gold、人审规则和数据处理审批
原有阻塞不变，详见 data_governance.md 与 benchmark_protocol.md。本次局部接入
已经完成；这些正式研究 gate 不属于本聊天待完成事项。
