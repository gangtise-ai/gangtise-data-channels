---
name: gangtise-data
description: 通过 Gangtise 金融 Open API 拉取结构化量化数据，覆盖：行情（日K/分钟K/实时快照，A股/港股/美股及交易所/概念/行业指数）、A股个股与板块日资金流向、估值分位、财务三大报表（含发债公司三表）、主营构成、股东结构、盈利预测（券商一致预期）、行业指标时序（宏观/行业/产品）、公司指标（EDE，A股/港股/美股/债券/基金）、题材指数画像与成分股、板块成分股；证券解析（security）已嵌入各数据脚本，可按证券名称、简称、拼音或代码指代标的，更推荐名称查询。当用户需要可落盘的表格化行情与基本面数据，或题材 Markdown 画像时使用。
version: 1.7.0
author: Gangtise
metadata:
  category: openapi
  homepage: "https://open-platform.gangtise.com/"
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-data.zip"
---

# 数据检索

## 概览

本技能在**本机**调用 `scripts/*.py`，请求 **Gangtise Open API**（`open.gangtise.com`），得到**结构化、可落盘**的结果（由 `scripts/utils.py` 中的 `format_response` 写入工作区 `workspace/gangtise/` 下对应子目录）。多数脚本输出 **CSV**；**题材指数**（`concept.py`）输出 **Markdown 文档**。

**证券指代**：`scripts/security.py` 中的关键词搜索与解析规则**已嵌入**行情、财务、估值、主营、股东、盈利预测等各脚本（共享 `--securities` 等参数时的解析路径）。**均可直接传入证券名称**（亦支持简称、拼音、数字代码等与 open-reference 搜索一致的关键词）；**更建议使用证券名称**，以便解析到预期标的并沿用脚本内的匹配加权与市场偏好。批量名单可将 `.csv` 路径直接传给 `--securities`（须存在；读 `security_code` / `code` / `代码` / `security_abbr` 列）。仅需浏览搜索命中或调试解析时，可单独运行 `security.py`。

当前脚本覆盖：

- **估值分析**（多指标并发、历史分位）：`scripts/valuation.py`
- **行情**（日K / 分钟K / 实时快照，覆盖 A/港/美股与交易所/概念/行业指数；日K 可选全市场、`--adjust` 不复权/前复权/后复权，前复权默认）：`scripts/quote.py`
- **A 股日资金流向**（个股 / 板块 / 全市场；小/中/大/特大单及主力净流入）：`scripts/fund_flow.py`
- **主营构成**（按产品/行业/地区，可并发全维度）：`scripts/main_business.py`
- **股东结构**（前十大股东/前十大流通股东）：`scripts/shareholder.py`
- **财务报表**（利润表/资产负债表/现金流量表）：`scripts/financial.py`
- **盈利预测**（券商一致预期多指标）：`scripts/earning_forecast.py`
- **行业指标**（EDB 检索 + 时序；覆盖宏观、行业以及产品数据；注意比亚迪销量这样的产品数据仅存在于行业指标接口；）：`scripts/industry_indicator.py`
- **公司指标**（EDE 检索 + 时序/截面，A/港/美股、债券与基金；相较于其他脚本，适合取到公司的单个指标或者不同方面的指标，覆盖行情、基本面、信息属性等）：`scripts/company_indicator.py`
- **题材指数**（基本信息 + 成分股，Markdown 输出；`--type info|securities|all`）：`scripts/concept.py`
- **板块成分股**（板块 ID 搜索 + 成分股列表，CSV 输出）：`scripts/block_constituents.py`
- **证券解析 / 代码搜索**（独立脚本 `scripts/security.py`，逻辑已嵌入上文各数据脚本）

使用场景：

- 需要**精确数值、时间序列或宽表**，并保存为 **CSV** 做后续分析或制图。
- 需要查看**题材投资逻辑、行业空间、竞争格局、分组成分股**等叙事性内容，并保存为 **Markdown**。

与其他技能的区别：

| 项目 | `gangtise-data`（本技能） | `gangtise-file` | `gangtise-kb` |
|------|---------------------------|-----------------|---------------|
| 数据形态 | **结构化数值表**（行情、财务、估值等）落盘 CSV；**题材指数**落盘 Markdown | **文件索引**：按类型/证券/日期等筛文档，返回 ID、元数据、摘要，可下载全文 | **语义检索**：返回与查询相关的**内容片段**，偏阅读与推理 |
| 典型问题 | 「这只股票某段区间的收盘价、利润表科目是多少」「机器人题材有哪些成分股、投资逻辑是什么」 | 「最近有哪些研报/公告、ID 是什么」 | 「文档里怎么论述某观点、结论是什么」 |

（中文说明：本技能解决「**是多少、表格化**」；要先**列文件再下载**用 `gangtise-file`；要**读原文片段、问答**用 `gangtise-kb`。）

调用脚本时若使用 `-sd` / `-ed`，请注意**当前真实日期与年份**。

整体长度是可控的，调用时请不要使用 `| head -N`，输出文件地址一般在末尾。

**报告期（财务 / 主营）**：命令行统一使用 **Q1 / Q2 / Q3 / Q4 / Q0**（分别对应一季报、中报、三季报、年报、最新一期）；脚本内再映射为 Open API 所需枚举（详见各 `references`）。

调用各脚本前，请阅读对应 **[references](./references/)** 中的参数与返回说明。

## 使用说明

### 1. 估值数据（估值分析）

基于 open **估值分析**接口，并发拉取 peTtm / psTtm / pbMrq / peg / pcfTtm / em，并组装为与后端类似的宽表列（含「在 N 年中所处分位」）。`-sd/-ed` 均不传时先查当天，无有效数据则向前回退至多 7 日并取最近有效交易日。

```bash
python3 scripts/valuation.py --securities 贵州茅台,五粮液
```

```bash
python3 scripts/valuation.py --securities 600519.SH,000858.SZ
```

```bash
python3 scripts/valuation.py --securities ./codes.csv -sd 2023-01-01 -ed 2026-12-31
```

详见 [估值数据调用指导](./references/valuation.md)。

### 2. 行情数据（日K / 分钟K / 实时快照）

基于 open **日K / 分钟K / 实时快照**接口，统一覆盖 **A 股、港股、美股**个股及**交易所指数（沪深京）、概念指数、行业指数（中信/申万）**；通过 `--type` 切换 `daily`（默认）/`minute`/`snap`。日 K 指定证券时未传 `-sd/-ed` 默认取**近 7 日**；**`--all-market`** 不带值默认 **A 股(cn)**，可指定 `cn`/`hk`/`us`（逗号分隔），未指定 `-sd/-ed` 则默认查**当天**并在无数据时逐日向前回退（最多 15 天）。分钟 K 仅支持 A 股及指数。

```bash
python3 scripts/quote.py --securities 腾讯,英伟达 -sd 2026-04-23 -ed 2026-04-23
```

```bash
python3 scripts/quote.py --securities 000001.SH,121000130.GT,CI005001.CI --adjust none
```

```bash
python3 scripts/quote.py --type minute --securities 600519.SH,000001.SH -sd "2026-04-23 10:00:00" -ed "2026-04-23 15:00:00"
```

```bash
python3 scripts/quote.py --type snap --securities 600519.SH,000001.SH,121000130.GT
```

```bash
python3 scripts/quote.py --securities ./codes.csv --limit 8000
```

详见 [行情数据调用指导](./references/quote.md)。

### 3. 资金流向（个股 / 板块 / 全市场）

基于 open **fund-flow/daily** 与 **fund-flow/sector-daily**；仅历史数据，不含实时。个股仅支持 **A 股**（`.SH` / `.SZ` / `.BJ`）。`--securities`、`--sectors`、`--all-market` 三者互斥。默认返回全部**净流入**字段；板块模式可用个股字段名，脚本自动加 `sector` 前缀。**`--all-market`** 未指定 `-sd/-ed` 时默认查**当天**，无数据逐日向前回退（最多 15 天）。

```bash
python3 scripts/fund_flow.py --securities 贵州茅台 -sd 2024-05-01 -ed 2024-05-20
```

```bash
python3 scripts/fund_flow.py --securities 600519.SH,000001.SZ --field-list mainNetInflow,smallInflow,largeInflow
```

```bash
python3 scripts/fund_flow.py --all-market -l 10
```

```bash
python3 scripts/fund_flow.py --all-market -sd 2024-05-20 -ed 2024-05-20 --limit 8000
```

```bash
python3 scripts/fund_flow.py --sectors 1000001065,1000000125 -sd 2024-05-01 -ed 2024-05-20
python3 scripts/fund_flow.py --sectors 半导体 -sd 2024-05-20 -ed 2024-05-20 --field-list sectorMainNetInflow
```

详见 [资金流向调用指导](./references/fund_flow.md)。

### 4. 主营构成

基于 open **main-business** 接口；不传 `--breakdown` 时并发拉取 **product / industry / region** 三种拆分。`--period` 仅支持 **Q2**（中报）或 **Q4**（年报）。

```bash
python3 scripts/main_business.py --securities 比亚迪
```

```bash
python3 scripts/main_business.py --securities 600519.SH --breakdown product --period Q4
```

详见 [主营构成调用指导](./references/main_business.md)。

### 5. 股东结构（前十大 / 前十大流通）

基于 open **capital-structure/top-holders** 接口；通过 `--holder-type` 切换 `top10`（前十大股东）与 `top10Float`（前十大流通股东）。支持日期区间筛选（`-sd/-ed`）或按财报年度筛选（`--fiscal-year`），并可叠加报告期筛选（`--period`）。

```bash
python3 scripts/shareholder.py --holder-type top10 --securities gzmt
```

```bash
python3 scripts/shareholder.py --holder-type top10Float --securities 600519.SH -sd 2025-01-01 -ed 2025-12-31 --period q3
```

```bash
python3 scripts/shareholder.py --holder-type top10 --securities ./codes.csv --fiscal-year 2024,2025 --period q1,q3
```

详见 [股东结构调用指导](./references/shareholder.md)。

### 6. 财务数据（三大报表）

基于 open **financial-report** 系列接口（支持 A 股、港股、美股，以及债券：债券代码走 A 股三表，返回发债公司报表），支持 `income`/`balance`/`cashflow`；`--period` 使用 `Q1~Q4,Q0`（默认 `Q0`），`--granularity` 支持 `accumulated|quarterly`（默认 `accumulated`，仅利润表/现金流量表生效；资产负债表仅累计值）；默认 `fieldList=[]` 返回全部科目。

```bash
python3 scripts/financial.py --securities 英伟达
```

```bash
python3 scripts/financial.py --table-type balance --securities 腾讯 --period Q4
```

```bash
python3 scripts/financial.py --table-type income --granularity quarterly --securities 贵州茅台 --fiscal-year 2025 --period Q2 --field-list totalOpRev,totalOpCost,netProfit,basicEPS
```

```bash
python3 scripts/financial.py --securities ./codes.csv --field-list netProfit,basicEarningsPerShare
```

详见 [财务数据调用指导](./references/financial.md)。

### 7. 盈利预测（券商一致预期）

基于 open **earning_forecast** 接口，支持通过 `--securities` 并发查询多只证券在指定日期区间的券商一致预期；支持通过 `--consensus-list` 选择指标，不传则默认返回全部可选字段。`-sd/-ed` 默认均为当天。返回会展开为 `security_code | date | 预测年份 | ...` 的扁平表；若单日查询当日无数据，会仅向前回退一天重试一次。

```bash
python3 scripts/earning_forecast.py --securities 贵州茅台,五粮液 -sd 2026-03-20 -ed 2026-03-25
```

```bash
python3 scripts/earning_forecast.py --securities ./codes.csv -sd 2026-03-20 -ed 2026-03-25 --consensus-list netIncome,eps,pe
```

详见 [盈利预测调用指导](./references/earning_forecast.md)。

### 8. 行业指标（EDB）

行业指标覆盖范围：
  - 宏观指标：各国GDP、CPI、PPI等，其中中国相关指标在指标名中不包含"中国"。因此如果一个宏观指标名中没有提及国家，其实是中国的宏观指标。
  - 行业指标：各行各业，比如原材料价格，航运指数等等。
  - 大宗商品：黄金现货价，石油期权、期货等衍生品的结算价、收盘价等。注意查询时，不要使用价格这个关键词，而是使用现货价、结算价、收盘价等关键词。
  - 产品指标：某个具体的产品，比如新能源汽车销量、空调销量等。注意比如比亚迪分品牌销量是查询不到的，需要先去知识库查找比亚迪有哪些品牌，然后发起多个查询比如"比亚迪 元plus 零售量"，"比亚迪 海鸥 零售量"等。

基于 open **EDB** 接口：`-m search` 或 `-k` 检索指标元信息；`--indicators` / `--indicators-file` 触发 get 获取指标具体数据。`--indicators` 仅含字母数字与逗号时直接取数；含中文等则 search，**唯一完全匹配**时自动 get。

```bash
python3 scripts/industry_indicator.py -k 空调 -l 50
```

```bash
python3 scripts/industry_indicator.py --indicators S14001618,S14001620 -sd 2010-01-01 -ed 2015-01-01
```

```bash
python3 scripts/industry_indicator.py --indicators 新能源汽车销量 -l 20
```

```bash
python3 scripts/industry_indicator.py --indicators-file ./industry_indicator_search_1.csv -l 30
```

详见 [行业指标调用指导](./references/industry_indicator.md)。

### 9. 公司指标（EDE）

公司指标覆盖范围：
  - 行情指标：日收盘价、成交量、涨跌幅、换手率、市值、成交额等。
  - 财务报表：利润表、资产负债表、现金流量表各科目及 TTM/单季度/同比环比。
  - 财务比率：估值倍数（PE/PB/PS/PCF/PEG）、盈利能力（ROE/ROA/ROIC）、营运周转与天数、现金流质量等。
  - 分红指标：现金分红、股利支付率、股息率等。
  - 盈利预测：预测营收/归母净利润及同比、预测 PE/PEG 等。
  - 公司/证券属性：主营业务、注册地址、上市板块、上市日期、证券所属概念、总股本/流通股本等。

如果查找不同季度的财务指标一般来说一季度为`yyyy-03-31`，二季度(中报)为`yyyy-06-30`，三季度为`yyyy-09-30`，四季度(年报)为`yyyy-12-31`。日频比如行情等指标，不覆盖当天的实时数据。支持 **A 股、港股、美股、存托凭证、债券与基金**。

基于open **EDE** 接口：`-m search` 或 `-k` 检索指标元信息；`--indicators` / `--indicators-file` 和 `--securities` 触发 get 获取指标具体数据。get模式时`-p '{...}'`可以指定全局参数`{"param": "value"}`应用于可以生效的指标，也可以单独指定指标参数`{"indicator_1":{"param_1": "value_1"}}`。如果`{"indicator_1":{"param_1": "value_1"}}`中`param_1`与全局参数`{"param": "value"}`中的`param`相同，则`value_1`的值会应用到`indicator_1`，`value`的值会应用到其他指标。

```bash
python3 scripts/company_indicator.py -k 收盘价
```

```bash
python3 scripts/company_indicator.py --indicators 营业收入 --securities 贵州茅台 -sd 2026-03-31 -ed 2026-03-31
```

```bash
python3 scripts/company_indicator.py --indicators qte_high,qte_close --securities 贵州茅台 -p '{"adjustType":"3","qte_close":{"adjustType":"2"}}' -sd 2026-07-07 -ed 2026-07-07
```

详见 [公司指标调用指导](./references/company_indicatory.md)。

### 10. 题材指数（基本信息 + 成分股）

通过 `-t/--type` 切换 `info`（定义/投资逻辑/行业空间/竞争格局）、`securities`（分组成分股）或 `all`（两者都查）。支持 `-c/--concepts` 或 `--concepts-file`。**输出 Markdown 文档**（非 CSV），仅返回最新截面。

```bash
python3 scripts/concept.py -c 机器人
```

```bash
python3 scripts/concept.py -c 121000130 --type info
```

```bash
python3 scripts/concept.py -c 机器人,固态电池 --type securities
```

详见 [题材指数调用指导](./references/concept.md)。

### 11. 板块成分股（板块 ID 搜索 + 成分股）

基于 open **`sectors/search`** 与 **`sectors/constituents`** 接口；`-k` 按关键词搜索板块，唯一高置信命中时自动拉取成分股；否则多命中时仅打印候选供确认，请改用 `-s` 指定 sectorId。输出 **CSV**。

```bash
python3 "scripts/block_constituents.py" -k 机器人
```

```bash
python3 "scripts/block_constituents.py" -s 121000130
```

```bash
python3 "scripts/block_constituents.py" -k 半导体 -t 10
```

详见 [板块成分股调用指导](./references/block_constituents.md)。

### 12. 证券解析与单独搜索（`security.py`）

此脚本已嵌入其他各数据脚本的证券参数解析；当且仅当你发现其他脚本中无法解析到预期标的时，可单独运行此脚本进行确认。

```bash
python3 scripts/security.py -k 贵州茅台
```

```bash
python3 scripts/security.py -k 银行 -c index --top 10 -l 5
```