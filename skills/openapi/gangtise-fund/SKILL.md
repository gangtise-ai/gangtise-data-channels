---
name: gangtise-fund
description: 通过 Gangtise 金融 Open API 拉取公募基金结构化数据，覆盖：基金基本信息、费率、历任基金经理、基金经理档案、资产配置与行业/券种/基金类型分布、持股/持债/持基明细、资产规模、持有人结构与前十大持有人、净值表现、ETF 申赎清单与份额变动、基金公司指标（EDE）；基金检索（security）已嵌入各脚本，场内基金可直接用简称、拼音或代码指代。当用户需要可落盘的公募基金表格数据时使用。
version: 1.7.0
author: Gangtise
metadata:
  category: openapi
  homepage: "https://open-platform.gangtise.com/"
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-fund.zip"
---

# 基金数据

## 概览

本技能在**本机**调用 `scripts/*.py`，请求 **Gangtise Open API**，得到**结构化、可落盘**的公募基金数据：结果统一写成 **CSV**（默认在工作区 `workspace/gangtise/<脚本名>/` 下），列名为中文，回复里附预览与文件路径。一次查询多种内容时，每种内容各写一个 CSV。

与其他技能的分工：股票、指数、行业、题材数据用 `gangtise-data`；债券与发债主体用 `gangtise-bond`；研报、公告原文、纪要等文档用 `gangtise-file`。本技能只处理**公募基金**。

## 选哪个脚本

| 用户在问 | 脚本 | `--type` 默认 | 必填输入 | 日期默认 |
|----------|------|----------------|----------|----------|
| 基金分类、管理人、成立日、申赎规则、业绩基准、跟踪指数 | `profile.py` | `basic` | `--securities` | — |
| 申购/赎回/管理/托管/销售服务费 | `profile.py --type fee` | — | `--securities` | — |
| 这只基金历任和现任基金经理、任职回报 | `profile.py --type manager` | — | `--securities` | — |
| 大类资产配置（权益、债券、现金等金额与占比） | `allocation.py` | `asset` | `--securities` | 全部报告期 |
| 持股的申万/中信行业分布 | `allocation.py --type industry` | — | `--securities` | 全部报告期 |
| 持债的券种分布 | `allocation.py --type bond` | — | `--securities` | 全部报告期 |
| 持有基金的类型分布（FOF） | `allocation.py --type fund` | — | `--securities` | 全部报告期 |
| 重仓股或全部持股明细 | `portfolio.py` | `stock` | `--securities` | 全部报告期 |
| 持债明细 | `portfolio.py --type bond` | — | `--securities` | 全部报告期 |
| 持基明细 | `portfolio.py --type fund` | — | `--securities` | 全部报告期 |
| 份额变动与资产净值 | `asset_size.py` | — | `--securities` | 全部报告期 |
| 机构/个人/员工持有占比、持有人户数 | `holder_structure.py` | — | `--securities` | 全部报告期 |
| 前十大持有人 | `top_holders.py` | — | `--securities` | 全部报告期 |
| 单位净值、累计净值、复权净值、货币基金万份收益 | `nav.py` | — | `--securities` | 近 7 日 |
| 基金经理学历、从业年限、在管规模与简介 | `manager.py` | — | `--names` | — |
| ETF 最新申赎状态、最小申赎单位、现金差额 | `etf_header.py` | — | `--securities` | 最新交易日 |
| ETF 最新申赎成分股 | `etf_components.py` | — | `--securities` | 最新交易日 |
| ETF 份额与规模的日度变动 | `etf_share.py` | — | `--securities` | 近 7 日 |
| 基金单个指标（复权净值、行情等 EDE） | `indicator.py` | — | `--indicators` + `--securities`，或 `-k` | 近一年 |
| 基金简称对应哪个代码、有哪些同名候选 | `security.py` | — | `-k` | — |

调用某个脚本前，先读对应 [references](./references/) 中的参数与字段说明。

## 通用约定

**指代基金**：除 `manager.py` 外，所有 `--securities` 都会先解析成基金代码。

- `.OF` 场外代码直接使用（如 `005827.OF`）。证券检索目前经常匹配不到场外基金的简称和数字代码，查场外基金时**直接传 `.OF` 代码**。
- `.SH` / `.SZ` / `.BJ` / `.HK` 会先在基金分类里核对，确认是基金才继续查；股票代码会被拒绝。
- 场内基金的简称、拼音（如 `创业板成长ETF华夏`、`510300`）自动检索。代码或简称与输入完全一致且只有一条，或匹配度高于 0.6 且只有一只时直接采用。检索到多只时全部列出并停止查询，即使其中一只匹配度为 1 也不自动选用。请改传列表中的代码。
- 查不到、或交易所代码经核对不是基金的输入会跳过并以 `[WARNING]` 列出，其余已确定的基金照常查询；全部无法解析时才报错。无法唯一确定的简称会中止整次查询并列出候选。
- 批量名单可把 `.csv` 路径传给 `--securities`（读 `security_code` / `code` / `代码` / `基金代码` / `fundCode` / `security_abbr` / `基金简称` 列），因此本技能输出的 CSV 可以直接作为下一个脚本的输入。

**一次查多项**：`profile.py`、`allocation.py`、`portfolio.py` 用 `--type` 选择内容，逗号分隔，`all` 表示该脚本里的全部类型。某一类型没有数据时，其余类型仍会返回，并在说明里写「未找到」。

**日期**：`-sd` / `-ed` 格式为 `yyyy-MM-dd`，使用前请确认**当前真实日期与年份**。只传其中一端时，只把该端传给接口。报告期类接口（持仓、分布、规模、持有人）筛的是**报告期**，常用季末 `03-31` / `06-30` / `09-30` / `12-31`；不传日期返回权限范围内的全部报告期。`nav.py`、`etf_share.py` 不传日期时取近 7 日，遇长假无数据会自动放宽到近 30 日。

**输出**：长度可控，不要加 `| head -N`；CSV 路径在输出末尾。单次返回超过 10000 行会被拒绝，请缩短日期或减少基金只数。

## 使用说明

### 基金档案（基本信息 / 费率 / 历任经理）

```bash
python3 scripts/profile.py --securities 创业板成长ETF华夏
python3 scripts/profile.py --securities 005827.OF --type all
python3 scripts/profile.py --securities 005827.OF --type fee --fee-type 管理费,托管费
python3 scripts/profile.py --securities 005827.OF --field-list 基金简称,成立日期,风险等级
```

默认只查基本信息。`--type` 可选 `basic` / `fee` / `manager`。`--field-list` 只作用于基本信息，可传英文名或中文名，`all` 与不传一样返回全部字段。`--fee-type` 只作用于费率，可选申购费、赎回费、管理费、托管费、销售服务费。详见 [基金档案](./references/profile.md)。

### 持仓分布

```bash
python3 scripts/allocation.py --securities 005827.OF -sd 2026-06-30 -ed 2026-06-30
python3 scripts/allocation.py --securities 005827.OF --type industry --industry-standard 中信 --position-type all -sd 2026-06-30 -ed 2026-06-30
python3 scripts/allocation.py --securities 005220.OF --type bond,fund -sd 2026-06-30 -ed 2026-06-30
```

默认只查资产配置。`--type` 可选 `asset` / `industry` / `bond` / `fund`。`--asset-level` 只作用于资产配置（`level1` / `level2`）。`--industry-standard`、`--position-type` 只作用于持股行业：行业标准不传为申万一级，持仓类型不传为重仓。详见 [持仓分布](./references/allocation.md)。

### 持仓明细

```bash
python3 scripts/portfolio.py --securities 005827.OF -sd 2026-06-30 -ed 2026-06-30
python3 scripts/portfolio.py --securities 005827.OF --type stock --position-type all -sd 2026-06-30 -ed 2026-06-30
python3 scripts/portfolio.py --securities 007908.OF,005220.OF --type all -sd 2026-06-30 -ed 2026-06-30
```

默认只查持股明细。`--type` 可选 `stock` / `bond` / `fund`。`--position-type` 只作用于持股：`top` 为重仓（各季披露，接口默认），`all` 为全部持股（仅半年报、年报）。详见 [持仓明细](./references/portfolio.md)。

### 规模、持有人与净值

```bash
python3 scripts/asset_size.py --securities 005827.OF -sd 2026-03-31 -ed 2026-06-30
python3 scripts/holder_structure.py --securities 005827.OF -sd 2025-12-31 -ed 2026-06-30
python3 scripts/top_holders.py --securities 161005.OF -sd 2025-12-31 -ed 2025-12-31
python3 scripts/nav.py --securities 159967.SZ -sd 2026-08-25 -ed 2026-08-27
```

详见 [资产规模](./references/asset_size.md)、[持有人结构](./references/holder_structure.md)、[前十大持有人](./references/top_holders.md)、[净值表现](./references/nav.md)。

### ETF 申赎

```bash
python3 scripts/etf_header.py --securities 510300.SH
python3 scripts/etf_components.py --securities 沪深300ETF华泰柏瑞
python3 scripts/etf_share.py --securities 510300.SH -sd 2026-08-25 -ed 2026-08-28
```

申赎基本资料和成分股只返回**最新交易日**。份额变动是日度序列。详见 [ETF申赎基本资料](./references/etf_header.md)、[ETF申赎成分股](./references/etf_components.md)、[ETF基金份额变动](./references/etf_share.md)。

### 基金指标

```bash
python3 scripts/indicator.py -k 复权单位净值
python3 scripts/indicator.py --indicators fund_adj_nav --securities 005827.OF -sd 2026-03-01 -ed 2026-03-10
python3 scripts/indicator.py --indicators qte_close --securities 510300.SH -sd 2026-03-01 -ed 2026-03-10
```

`indicator.py` 只接受基金。场外基金直接传 `.OF`。详见 [基金公司指标](./references/indicator.md)。

### 基金经理与检索

```bash
python3 scripts/manager.py --names 张坤,葛兰
python3 scripts/security.py -k 沪深300ETF -l 10
python3 scripts/security.py -k 510300 -c fund
```

`manager.py` 按姓名**精确匹配**，同名经理会全部返回，用「当前公司」区分。`security.py` 的 `-c` 默认 `fund`，可选 `fund,stock,dr,index,bond` 或 `all`。详见 [基金经理](./references/manager.md)、[基金检索](./references/security.md)。

## 读结果时注意

- **重仓与全部**：`top` 各季度都披露；`all` 只在半年报和年报披露。季末日期配 `--position-type all` 常常没有行。
- **股票型基金**：查持债、持基、券种或基金类型分布时，可能该类型为空，说明里会写「未找到」，已查到的其他类型仍然有效。
- **净值日期**：净值日常晚于自然日。不传日期时脚本会在近 7 日为空时自动放宽到近 30 日；指定了日期仍为空时，把 `-sd/-ed` 放到最近一个有净值的区间。货币基金看「7日年化收益率」「万份收益」，这两列对非货币基金为空。
- **历史长度**：持仓、分布、规模、持有人、净值、ETF 份额变动，试用账号前溯 3 年、正式账号前溯 5 年。基本信息、费率、历任经理、基金经理档案、ETF 最新申赎清单无此长度限制。
- **行数上限**：单次最多 10000 行，超出会被拒绝。本技能不会自动拆批，请缩短日期或减少基金只数。
- **布尔与枚举**：是否指数型基金写成「是 / 否」。费率类型、资产层级、行业分类标准、持仓类型换成中文；资产类型代码保留接口原值，名称看「资产类型」列。
- **数值格式**：带千分位的数字（如持有人户数）转为普通数值，浮点误差尾数（如 `-6.5600000000000005`）已修正。
