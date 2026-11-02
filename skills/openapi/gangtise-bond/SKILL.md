---
name: gangtise-bond
description: 通过 Gangtise 金融 Open API 拉取债券结构化数据，覆盖：债券基本资料、日收盘行情（交易所 + 银行间）、上清所估值、付息兑付现金流、发行与增发明细、债项/主体/担保人评级一览、债项评级变动、含权债行权安排、债券公告、利率债发行计划、违约债券列表、发债主体工商档案与主体评级变动、发债公司三大报表、债券公司指标（EDE）；债券检索（security）已嵌入各脚本，可直接用债券简称、拼音或代码指代债券。当用户需要可落盘的债券表格数据时使用。
version: 1.7.0
author: Gangtise
metadata:
  category: openapi
  homepage: "https://open-platform.gangtise.com/"
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-bond.zip"
---

# 债券数据

## 概览

本技能在**本机**调用 `scripts/*.py`，请求 **Gangtise Open API**，得到**结构化、可落盘**的债券数据：结果统一写成 **CSV**（默认在工作区 `workspace/gangtise/<脚本名>/` 下），列名为中文，回复里附预览与文件路径。

与其他技能的分工：股票、指数、行业、题材数据用 `gangtise-data`；研报、公告原文、纪要等文档用 `gangtise-file`；本技能只处理**债券与发债主体**。

## 选哪个脚本

| 用户在问 | 脚本 | 必填输入 | 日期默认 |
|----------|------|----------|----------|
| 票面利率、期限、到期日、付息方式、含权条款、担保等静态信息 | `basic_info.py` | `--securities` | — |
| 收盘价、到期收益率、成交、久期凸性（交易所 + 银行间） | `quote.py` | `--securities` | 近 7 日 |
| 中票、短融等的上清所估值收益率 / 估价 | `valuation.py` | `--securities` | 近 7 日 |
| 未来或历史每次付息兑付的金额与日期 | `cash_flow.py` | `--securities` | 全部 |
| 首发与增发（续发）的规模、价格、边际利率、认购倍数 | `issuance.py` | `--securities` | 全部 |
| 债项、发行人、担保人的**最新**评级 | `rating.py` | `--securities` | — |
| 债项评级的**历次变动** | `rating_change.py` | `--securities` | 全部历史 |
| 赎回 / 回售等行权日期、行权价格与金额 | `exercise_notice.py` | `--securities` | 全部 |
| 债券公告（按债券，或按日期查全市场） | `announcement.py` | 二者任一 | 全市场近 7 日 |
| 违约债券（按日期、债券或发行人全称） | `default_list.py` | 三者任一 | 全市场近 7 日 |
| 国债、地方债、政金债的发行计划 | `issuance_plan.py` | 无 | 今天起 30 天 |
| 发行人档案：企业性质、行业、地区、主体评级、存续债 | `issuer_info.py` | `--securities` 或 `--issuers` | — |
| 发行人主体评级的**历次变动**（含境外机构） | `issuer_rating_change.py` | `--securities` 或 `--issuers` | 全部历史 |
| 发债公司利润表 / 资产负债表 / 现金流量表 | `financial.py` | `--securities` | 最新一期 |
| 发债公司单个指标（资产、营收、估值等 EDE） | `indicator.py` | `--indicators` + `--securities`，或 `-k` | 近一年 |
| 债券简称对应哪个代码、有哪些同名候选 | `security.py` | `-k` | — |

调用某个脚本前，先读对应 [references](./references/) 中的参数与字段说明。

## 通用约定

**指代债券**：所有 `--securities` 都会先解析成标准代码。

- `.SH` / `.SZ` / `.BJ` / `.IB` 代码直接使用（如 `019708.SH`、`102381014.IB`）；
- 简称、拼音（如 `23国债15`、`H1万科04`）自动检索。代码或简称与输入完全一致且只有一条，或匹配度高于 0.6 且只有一只时直接采用。检索到多只时全部列出（代码、简称、匹配度）并停止查询，即使其中一只匹配度为 1 也不自动选用。请改传列表中的标准代码；
- 批量名单可把 `.csv` 路径传给 `--securities`（读 `security_code` / `code` / `代码` / `债券代码` / `security_abbr` / `债券简称` 列），因此本技能输出的 CSV 可以直接作为下一个脚本的输入。

**选择字段**：`--field-list` 可传英文字段名或中文列名（单位可省略，如 `票面利率`），逗号分隔；`all` 返回全部字段。字段名写错时脚本直接报错并列出可选字段。`basic_info`、`quote`、`valuation`、`issuer_info` 字段较多，不传时只返回常用字段；其余脚本不传即返回全部字段。

**日期**：`-sd` / `-ed` 格式为 `yyyy-MM-dd`，使用前请确认**当前真实日期与年份**。只传其中一端时，另一端视为不设限。`quote`、`valuation` 不传日期时取近 7 日，遇长假无数据会自动放宽到近 30 日。`default_list` 不传债券和主体时按违约日期查全市场，默认近 7 日；区间超过 1 个自然年时自动拆分。与债券或主体同时传入的日期在本地过滤。

**枚举字段**（债券类型、利率类型、付息频率、交易市场、行业、地区、评级类型等）由脚本自动换成中文名称；个别查不到名称的代码保留原值。

**分批**：各接口的单次上限（评级一览、债项评级变动每批 10 只；主体评级变动每批 10 个发行人；行情、估值、现金流、发行增发按日期跨度 × 债券只数）都由脚本自动分批，几百只债券的名单也可直接传入，无需手工拆分。违约列表按日期查询时单次不超过 1 个自然年，更长区间自动拆开；按主体查询时每个发行人全称单独请求。名单中个别无法识别或不被接口接受的代码会跳过并以 `[WARNING]` 列出。

**输出**：长度可控，不要加 `| head -N`；CSV 路径在输出末尾。

## 使用说明

### 债券静态信息与评级

```bash
python3 scripts/basic_info.py --securities 23国债15,H1万科04
python3 scripts/basic_info.py --securities 23万科MTN001 --field-list 票面利率,到期日期,最新评级,内含特殊条款
python3 scripts/rating.py --securities H1万科04,23万科MTN001
python3 scripts/rating_change.py --securities H1万科04,23万科MTN001 -sd 2025-01-01
```

`basic_info` 共 65 个字段，涵盖发行、期限、利率付息、评级、担保、特殊条款以及 ABS / 可转债专项；`rating` 给出债项、发行人、担保人三方最新评级；`rating_change` 给出债项评级历次变动。详见 [基本资料](./references/basic_info.md)、[评级一览](./references/rating.md)、[债项评级变动](./references/rating_change.md)。

### 行情与估值

```bash
python3 scripts/quote.py --securities 23国债15 -sd 2026-09-01 -ed 2026-09-30
python3 scripts/quote.py --securities 019708.SH --field-list cleanClose,ytmClose,modifiedDuration,convexity
python3 scripts/valuation.py --securities 23万科MTN001 -sd 2026-09-01 -ed 2026-09-30
```

`quote` 为交易所与银行间的日收盘行情（仅历史，无实时）。`valuation` 为上清所估值，主要覆盖银行间非金融企业债务融资工具（中票、短融等）；`--confidence` 可选 `推荐` / `不推荐`，不传按「推荐」。详见 [日收盘行情](./references/quote.md)、[上清所估值](./references/valuation.md)。

### 现金流、发行与行权

```bash
python3 scripts/cash_flow.py --securities 23国债15
python3 scripts/issuance.py --securities 23国债15
python3 scripts/exercise_notice.py --securities H1万科04
```

`cash_flow` 按兑付日返回每百元应付利息 / 本金与兑付后余额，不传日期即为含未到期部分的完整兑付计划；`issuance` 的日期按发行公告日筛选；`exercise_notice` 的日期按行权日筛选。详见 [付息兑付](./references/cash_flow.md)、[发行与增发](./references/issuance.md)、[行权提示](./references/exercise_notice.md)。

### 公告与发行计划

```bash
python3 scripts/announcement.py --securities H1万科04 --page-size 50
python3 scripts/announcement.py -sd 2026-09-30 -ed 2026-09-30 --page-size 200 --max-pages 5
python3 scripts/issuance_plan.py -sd 2026-10-01 -ed 2026-10-31
```

`announcement` 分页且不返回总数：`--page-size` 为 1~200，`--max-pages` 控制连续拉取页数，遇到空页或不足一页即停；输出提示还有下一页时，用 `--page-no` 续拉。按债券检索时同时给日期，日期只在已拉取的页内过滤。详见 [债券公告](./references/announcement.md)、[利率债发行计划](./references/issuance_plan.md)。

### 违约债券

```bash
python3 scripts/default_list.py -sd 2026-09-01 -ed 2026-10-20
python3 scripts/default_list.py --securities H1万科04
python3 scripts/default_list.py --issuers 万科企业股份有限公司
```

`default_list` 返回违约日期、违约金额(亿元)、发行人与违约原因，成功调用按 **0.4 积分/次**计费。`--issuers` 可写简称：只命中一家时换成发行人全称再查；多家（例如「世茂」）全部列出，请改传全称。详见 [违约债券](./references/default_list.md)。

### 发债主体

```bash
python3 scripts/issuer_info.py --issuers 万科企业股份有限公司
python3 scripts/issuer_info.py --securities H1万科04,23国债15
python3 scripts/issuer_rating_change.py --issuers 万科 -sd 2025-01-01
```

`--securities`（查这些债券的发行人）与 `--issuers` 二选一。`--issuers` 写全称时直接查询；写简称时先检索主体，只命中一家才继续，多家全部列出供确认。按债券查 `issuer_info` 时结果带「查询债券代码」列。详见 [主体基本信息](./references/issuer_info.md)、[主体评级变动](./references/issuer_rating_change.md)。

### 发债公司报表与指标

```bash
python3 scripts/financial.py --securities 2680022.IB --field-list totalOpRev,netProfit
python3 scripts/financial.py --table-type balance --securities 26京投债01 --fiscal-year 2024 --period Q4
python3 scripts/indicator.py -k 资产合计
python3 scripts/indicator.py --indicators bs_aset --securities 2680022.IB -sd 2024-12-31 -ed 2025-12-31
```

`financial.py` 只接受债券，走 A 股三大报表接口，返回发行人报表。利润表和现金流量表可以 `--granularity quarterly`；资产负债表只有累计值。`indicator.py` 是 EDE 公司指标，同样只接受债券。详见 [发债公司财务报表](./references/financial.md)、[债券公司指标](./references/indicator.md)。

### 债券检索

```bash
python3 scripts/security.py -k 万科 -l 10
python3 scripts/security.py -k 23国债15 -c bond,stock
```

`-c` 默认 `bond`，可选 `bond,stock,dr,index,fund` 或 `all`。

## 读结果时注意

- **评级后缀**：评级可能带 `sf`（结构化融资产品）或 `pi`（中债资信主动评级）小写后缀，如 `AA+sf`、`AAApi`，按档位比较前需先去掉。境外机构（惠誉、穆迪、标普）的评级符号体系与境内不同，不能直接按符号比较。
- **复合字段**：`初始面值/最新面值`、`发行价格/参考收益率`、`最新评级(主体/债项)`、`发行时评级(主体/债项)`、国民经济 / 申万行业等以 `/` 拼接，缺失一侧以 `-` 占位。
- **缺失数据**：`basic_info`、`rating` 中库内无资料的债券仍占一行，除代码外全为空；其余脚本中无数据的债券不产生行。全部无数据时提示未找到。
- **行数上限**：`issuance_plan` 单次最多返回 10000 行，超出会被拒绝，请缩短日期区间；其余脚本已自动分批。
- **历史区间**：行情、估值的开始日期早于账号可查询范围时报 `110003`，把开始日期调晚即可。
