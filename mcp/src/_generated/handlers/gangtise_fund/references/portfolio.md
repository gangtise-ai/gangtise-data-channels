# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/references/portfolio.md
# Regenerate: python3 scripts/generate.py
# 基金持仓明细（Open API · stock-portfolio、bond-portfolio、fund-portfolio）

## 简介

一个脚本查询三类持仓明细，由 `--type` 选择，各自落盘：

| `--type` | 接口 | 内容 | 模块文件名前缀 |
|----------|------|------|----------------|
| `stock`（默认） | `fund/stock-portfolio` | 持股数量、市值、占净值比及较上期变化 | `stock_portfolio` |
| `bond` | `fund/bond-portfolio` | 持债数量、市值、占净值比 | `bond_portfolio` |
| `fund` | `fund/fund-portfolio` | 持有基金的市值与占净值比 | `fund_portfolio` |

试用账号前溯 3 年、正式账号前溯 5 年。脚本：`scripts/portfolio.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 基金代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv`。场外基金请直接传 `.OF` |
| `--type` / `-t` | 否 | `stock` / `bond` / `fund`，逗号分隔；`all` 三项都查。默认 `stock` |
| `-sd` / `--start-date` | 否 | 报告期起。不传不限制 |
| `-ed` / `--end-date` | 否 | 报告期止。不传不限制 |
| `--position-type` | 否 | 仅 `stock`：`top` 重仓（各季披露，接口默认）、`all` 全部持股（仅半年报、年报） |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 字段说明

### 持股明细

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | `yyyy-MM-dd` |
| `stockName` | 股票简称 | |
| `holdingQuantity` | 持股数量(万股) | |
| `pctToFloatShares` | 占流通股比例(%) | |
| `holdingValue` | 持仓市值(万元) | |
| `pctToNav` | 占资产净值比(%) | |
| `pctToNavChg` | 占资产净值比变化(%) | 较上一报告期 |

### 持债明细

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | |
| `bondName` | 债券简称 | |
| `holdingQuantity` | 持仓量(万张) | |
| `holdingValue` | 持仓市值(万元) | |
| `pctToNav` | 占资产净值比(%) | |

### 持基明细

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | |
| `holdingFundName` | 持仓基金简称 | |
| `holdingValue` | 持仓市值(万元) | |
| `pctToNav` | 占资产净值比(%) | |

## 约束与说明

- 单次最多 10000 行。全部持股在只数或报告期较多时很容易顶满，请先缩到单期。
- 未查持股时传入 `--position-type` 会被忽略，并给出 `[WARNING]`。
- 股票型基金查持债或持基、债券基金查持基，可能该类型没有行。

## 调用示例

```bash
python3 scripts/portfolio.py --securities 005827.OF -sd 2026-06-30 -ed 2026-06-30
python3 scripts/portfolio.py --securities 005827.OF --type stock --position-type all -sd 2026-06-30 -ed 2026-06-30
python3 scripts/portfolio.py --securities 007908.OF --type bond -sd 2026-06-30 -ed 2026-06-30
python3 scripts/portfolio.py --securities 005220.OF --type fund -sd 2026-06-30 -ed 2026-06-30
```

## 返回说明

- **成功**：在 `workspace/gangtise/portfolio/` 下按类型生成 CSV。
- **部分无数据**：查到的明细正常返回，未查到的类型写在说明里。
