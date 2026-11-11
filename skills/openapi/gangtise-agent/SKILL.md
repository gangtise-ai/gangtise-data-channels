---
name: gangtise-agent
description: 通过 Gangtise Agent OpenAPI 统一拉取 Markdown 投研文本。 各 Agent 能力概览：one-pager（公司一页通，单票核心要素与结论浓缩）； investment-logic（投资逻辑，主线叙事与关键假设）； peer-comparison（同业对比，竞争格局与可比公司差异）； earnings-review（业绩点评，财报期业绩解读；需 getId 后轮询 getContent，最长约 600s）； viewpoint-debate（观点 PK，对给定观点的正反辨析与论据组织；同样异步轮询）； theme-tracking（主题跟踪，晨报/晚报式产业链与主题脉络）； research-outline（调研提纲，公司调研问题与访谈框架）； stock-one-line-summary（个股一句话总结，A 股/港股个股批量最新一句话投研摘要）； hot-topic-list（热点话题报告列表，按日期与报告类型分页拉取结构化热点，输出为多级 Markdown；核心标的为表格）； security-clue-list（投研线索列表，按证券/行业+时间范围提取研报、电话会议、公告、观点等结构化线索，输出为 Markdown 表格）； management-sentiment（公司管理层情绪，-t 切换指标/结论/问答明细，输出为组装后的 Markdown）； expert-intel（AI专家情报，从专家会议/纪要提炼的个股情报列表，支持证券/行业/主题/标签/关键词/时间筛选）。 返回多为可直接引用的结论文本，适合纪要、速览、投研助理与 Agent 编排中的事实与观点补充。注意不要只调用gangtise-agent，这些投研文本是定期更新的，时效性不足，建议额外调用其他skills进行补充。
version: 1.8.0
author: Gangtise
metadata:
  category: openapi
  homepage: "https://open-platform.gangtise.com/"
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-agent.zip"
---

# Agent 接口调用

## 概览

本技能通过 `scripts/agents.py` 调用通用 Agent 接口；`hot-topic-list`、`security-clue-list`、`management-sentiment` 与 `expert-intel` 为独立脚本调用（参数差异较大）。

支持接口：

- `stock-one-pager`：公司一页通
- `investment-logic`：投资逻辑
- `peer-comparison`：同业对比
- `earnings-review`：业绩点评（自动串联 getId + 轮询 getContent，最长 600s）
- `viewpoint-debate`：观点 PK（自动串联 getId + 轮询 getContent，最长 600s）
- `theme-tracking`：主题跟踪（晨报/晚报）
- `research-outline`：公司调研提纲
- `stock-one-line-summary`：个股一句话总结（A 股/港股；支持批量证券查询）
- `hot-topic-list`：热点话题报告（早报/午报/盘中快报/晚报等，分页与多维筛选，结构化话题与可选标的/精读）
- `security-clue-list`：投研线索列表（按证券/行业查询，支持时间与来源筛选，分页最大 500）
- `management-sentiment`：公司管理层情绪（`-t indicator` 指标、`conclusion` 结论、`detail` 明细；指标与结论按证券/时间分页，明细按来源会议取逐条问答）
- `expert-intel`：AI专家情报（专家会议/纪要提炼情报列表，按证券/研究方向/主题/标签/关键词/时间筛选，分页最大 50，20 积分/条）

整体长度是可控的，调用时请不要使用 `| head -N`，输出文件地址一般在末尾。

## 统一脚本

`scripts/agents.py`

`scripts/hot_topic.py`（仅 `hot-topic-list`）

`scripts/security_clue.py`（仅 `security-clue-list`）

`scripts/management_sentiment.py`（公司管理层情绪：指标 / 结论 / 明细）

`scripts/expert_intel.py`（AI专家情报列表）

## 参数说明

### `scripts/agents.py`

| 参数 | 必填 | 说明 |
|------|------|------|
| `-a` / `--agent-type` | 是 | 接口类型，见上方枚举。`earnings-review` 与 `viewpoint-debate` 会自动串联 getId + 轮询 getContent（最长 600s）。 |
| `--security` | 条件必填 | 单个证券名称或代码（如 `600519.SH`）。用于 `stock-one-pager`、`investment-logic`、`peer-comparison`、`research-outline`、`earnings-review`、`stock-one-line-summary`。 |
| `--securities` | 条件必填 | 多个证券名称或代码，逗号分隔（如 `贵州茅台,比亚迪`）；与 `--security` 可同时使用并去重合并。用于同上需证券的 agent 类型。`stock-one-line-summary` 仅支持 A 股/港股个股，不支持市场标识。 |
| `-p` / `--period` | 条件必填 | 报告期，年份+`q1`/`interim`/`q3`/`annual`（如 `2026interim`、`2025annual`；`2026q2`/`2026h1`/`2025q4` 会自动转换）。仅用于 `earnings-review`。 |
| `-d` / `--data-id` | 否 | 保留参数，当前无对外场景。 |
| `--viewpoint` | 条件必填 | 观点文本（最长 1000 字）。仅用于 `viewpoint-debate`。 |
| `-t` / `--theme-id` | 条件必填 | 主题 ID 或中文主题名。仅用于 `theme-tracking`。 |
| `--date` | 条件必填 | 查询日期（`yyyy-MM-dd`）。仅用于 `theme-tracking`。 |
| `--type` | 条件必填 | 资讯类型（`morning`/`night`，支持逗号分隔多选）。仅用于 `theme-tracking`。 |

### `scripts/hot_topic.py`
| 参数 | 必填 | 说明 |
|------|------|------|
| `--page-from` | 否 | 分页起始偏移，默认 `0`。 |
| `--page-size` | 否 | 分页条数，默认 `500`，最大 `500`。 |
| `-sd` / `--start-date` | 否 | 开始日期，支持 `yyyy-MM-dd`。 |
| `-ed` / `--end-date` | 否 | 结束日期，支持 `yyyy-MM-dd`。 |
| `--hot-category` | 否 | 热点类型，逗号分隔：`morning`、`noon`、`afternoon`、`evening`。 |
| `--with-securities` | 否 | 是否包含相关证券。 |
| `--with-close-reading` | 否 | 是否包含精读。 |

### `scripts/security_clue.py`

| 参数 | 必填 | 说明 |
|------|------|------|
| `--page-from` | 否 | 分页起始偏移，默认 `0`。 |
| `--page-size` | 否 | 分页条数，默认 `500`，最大 `500`。 |
| `-st` / `--start-time` | 否 | 开始时间，支持 `yyyy-MM-dd` 或 `yyyy-MM-dd HH:mm:ss`；与 `-et` 均不传时默认近 **7** 日。 |
| `-et` / `--end-time` | 否 | 结束时间，支持 `yyyy-MM-dd` 或 `yyyy-MM-dd HH:mm:ss`；与 `-st` 均不传时默认近 **7** 日。 |
| `-q` / `--query-mode` | 是 | 查询方式：`bySecurity`（按证券）或 `byIndustry`（按行业）。 |
| `--securities` | 是 | 证券/行业名称或代码列表，逗号分隔；也可传 `all`。例如 `000001.SZ,000063.SH` 或 `888888.CI,999999.CI`。 |
| `--source` | 否 | 来源多选，逗号分隔：`researchReport`、`conference`、`announcement`、`view`。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径；文件名自动生成。 |

### `scripts/management_sentiment.py`

一个脚本覆盖三个接口，用 `-t` / `--type` 切换（与 `gangtise-file` 的投研日程同一做法）。输出已组装成 Markdown，不是原始 JSON。

| 参数 | 必填 | 说明 |
|------|------|------|
| `-t` / `--type` | 是 | `indicator` 指标、`conclusion` 结论、`detail` 明细。也可写 `指标` / `结论` / `明细`。 |
| `--securities` | 否 | 证券名称或代码，逗号分隔。仅指标、结论。不传则不按证券过滤。 |
| `-st` / `--start-time` | 否 | 开始时间，`yyyy-MM-dd` 或 `yyyy-MM-dd HH:mm:ss`。仅指标、结论；只传日期时补 `00:00:00`。 |
| `-et` / `--end-time` | 否 | 结束时间，格式同上。仅指标、结论；只传日期时补 `23:59:59`。 |
| `--page-from` | 否 | 分页起始，默认 `0`。仅指标、结论。 |
| `--page-size` | 否 | 单页条数，`1`~`100`。指标默认 `20`，结论默认 `10`。 |
| `--source-type` | 否 | 明细来源类型，目前仅 `conference`（电话会议）。 |
| `--source-id` | 条件必填 | 明细来源 ID。先查指标或结论，用结果里的 `source.sourceId`。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径；文件名自动生成。 |

指标按 **5 积分/条**，结论按 **5 积分/条**，明细按 **10 积分/次**。明细不分页，一次返回该场全部问答。指标结果含三个维度评分、占比和分问题类型得分；结论结果含情绪结论、三个信号和重点 QA 对比；明细结果含逐条问答原文、三档评分和判断依据。

## 示例

```bash
python3 scripts/agents.py -a stock-one-pager --security 贵州茅台
```

```bash
python3 scripts/agents.py -a stock-one-pager --securities 贵州茅台,比亚迪,宁德时代
```

```bash
python3 scripts/agents.py -a investment-logic --security 比亚迪
```

```bash
python3 scripts/agents.py -a peer-comparison --security ndsd
```

```bash
python3 scripts/agents.py -a earnings-review --security 宁德时代 --period 2026interim
```

```bash
python3 scripts/agents.py -a viewpoint-debate --viewpoint "飞天茅台的批价低点是1500元"
```

```bash
python3 scripts/agents.py -a theme-tracking -t 23600839952306231 --date 2026-01-01 --type morning,night
```

```bash
python3 scripts/agents.py -a theme-tracking -t 核电 --date 2026-04-01 --type morning,night
```

```bash
python3 scripts/agents.py -a research-outline --security 比亚迪
```

```bash
python3 scripts/agents.py -a stock-one-line-summary --securities 600183.SH,00700.HK
```

```bash
python3 scripts/hot_topic.py --page-from 0 --page-size 5 -sd 2026-03-22 -ed 2026-03-27 --hot-category morning,noon,afternoon --with-securities --with-close-reading
```

```bash
python3 scripts/security_clue.py --page-from 0 --page-size 10 -q bySecurity --securities 贵州茅台,比亚迪
```

```bash
python3 scripts/security_clue.py --page-from 0 --page-size 10 -st "2026-01-01 00:00:00" -et "2026-03-23 23:59:59" -q byIndustry --securities 888888.CI,999999.CI --source conference,view
```

```bash
python3 scripts/management_sentiment.py -t indicator --securities 国瓷材料 -st 2026-08-01 -et 2026-08-31
```

```bash
python3 scripts/management_sentiment.py -t conclusion --securities 300285.SZ,688313.SH --page-size 10
```

```bash
python3 scripts/management_sentiment.py -t detail --source-type conference --source-id 554030
```

### `scripts/expert_intel.py`

| 参数 | 必填 | 说明 |
|------|------|------|
| `--page-from` | 否 | 分页起始偏移，默认 `0`。 |
| `--page-size` | 否 | 分页条数，默认 `20`，最大 `50`。 |
| `-st` / `--start-time` | 否 | 开始时间，`yyyy-MM-dd` 或 `yyyy-MM-dd HH:mm:ss`。 |
| `-et` / `--end-time` | 否 | 结束时间，格式同上。 |
| `--search-type` | 否 | `1` 标题搜索 / `2` 全文搜索（默认）。 |
| `-k` / `--keyword` | 否 | 搜索关键词。 |
| `--securities` | 否 | 证券名称或代码，逗号分隔。 |
| `--research-areas` | 否 | 研究方向（行业）ID，逗号分隔。 |
| `--concepts` | 否 | 主题概念 ID 或名称，逗号分隔。 |
| `--tags` | 否 | 内容标签纯文本，逗号分隔（如 `景气上行,超预期`）。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径。 |

```bash
python3 scripts/expert_intel.py --securities 浙江荣泰 -st 2026-10-20 -et 2026-10-23 --concepts 特斯拉机器人 --tags 景气上行,超预期 -k 特斯拉
```

```bash
python3 scripts/expert_intel.py --securities 603119.SH,000700.SZ --page-size 20 --search-type 2
```
