# 三代规章全文的找回方案（policy-as-prompt 素材）

## 状态

本会话环境的网络白名单拦截了 web.archive.org 与所有中文镜像站
（curl 与 WebFetch 均 403，仅搜索摘要可用——转述文本不可作为逐字条文来源），
因此规章全文需在环境外抓取。判决文书中引用的原始 URL 已从全量数据提取
（这是精确的抓取靶点）：

| 引用次数 | 原始 URL | 对应规章 | 建议快照时点 |
|---|---|---|---|
| 6,339 | `http://weibo.com/z/guize/guiding.html` | 《新浪微博社区管理规定(试行)》 | 2013 年年中 |
| 23,174 | `http://service.account.weibo.com/roles/guiding` | 《微博社区管理规定(试行)》→《微博社区管理规定》**（同一 URL，内容随版本变化）** | 2015 年初 + 2016 年年中各取一份 |
| 1,439 | `http://service.account.weibo.com/roles/xize` | 《微博举报投诉操作细则》 | 2018 年年中 |
| 4 | `http://service.account.weibo.com/roles/banfa` | （罕见引用的处理办法） | 2018 年 |

## 抓取方式

**方式一（推荐）：在本地跑现成脚本**

```bash
pip install requests beautifulsoup4
python scripts/fetch_rules.py --out data/rules
```

脚本自动通过 Wayback CDX API 选取最接近目标日期的快照，落盘为
`data/rules/<label>.txt` + 溯源信息 `<label>.meta.json`。

**方式二：浏览器手动**，逐个打开：

- `https://web.archive.org/web/2013/http://weibo.com/z/guize/guiding.html`
- `https://web.archive.org/web/20150301/http://service.account.weibo.com/roles/guiding`
- `https://web.archive.org/web/20160601/http://service.account.weibo.com/roles/guiding`
- `https://web.archive.org/web/2018/http://service.account.weibo.com/roles/xize`

保存正文文本；像之前的数据集一样打包上传到会话即可。

**备选来源**（Wayback 缺失时）：百度百科词条
「新浪微博社区管理规定（试行）」「微博社区公约」通常收录全文；
新浪 2012-05-09 公约发布时多家媒体（观察者网、浙江在线、中国互联网协会）
转载过第一代全文。

## 拿到全文后的验证清单

用数据侧解析结果交叉验证条文版本是否正确：

1. **gen1**（新浪规定试行）：第22条应为不实信息的处理条款
   （全量判决中被引用 19,724 次的主罚条款）；
2. **gen2**：试行版主罚条款仍为第22条；正式版（2015 下半年起）应为第23条
   （被引 5,866 次）；若快照里条号对不上，说明取到的版本不对，换相邻时间快照；
3. **gen3**（细则）：第19条应为不实信息处理条款（被引 10,811 次）；
4. 各代还应包含不实信息的**定义**条款与信用积分/禁言/禁被关注的**量刑**条款
   ——这三块正是 policy-as-prompt 评测（`benchmark/run_eval.py --rules`）
   需要喂给模型的内容。

## 接入评测

验证通过后，把对应年代的规章文本传给评测脚本即可，例如按层分别跑：

```bash
python -m benchmark.run_eval gen3_cases.jsonl --rules data/rules/gen3_xize_2018.txt
```

（run_eval 的 system prompt 已支持在 `--rules` 中注入全文并做提示缓存。）
