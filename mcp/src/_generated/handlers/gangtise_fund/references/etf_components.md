# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/references/etf_components.md
# Regenerate: python3 scripts/generate.py
# ETF 申赎成分股（Open API · fund/etf-pcf-components）

## 简介

返回 ETF **最新交易日**的申购赎回成分清单：成分证券、收盘价、权重、申购数量和现金替代。每只基金每个成分一行。试用账号与正式账号均可查全量场内基金。脚本：`scripts/etf_components.py`。

清单头信息（申赎状态、最小申赎单位、现金差额）用 `etf_header.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | ETF 代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

没有日期参数。沪深 300 一类宽基一次就有约 300 行，多只同时查时注意 10000 行上限。

## 字段说明

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `fullName` | 基金全称 | |
| `tradeDate` | 交易日期 | |
| `serialNumber` | 成分序号 | |
| `componentCode` | 成分代码 | 接口若返回该列则保留 |
| `componentName` | 成分名称 | |
| `close` | 收盘价(元) | |
| `pctChange` | 涨跌幅(%) | |
| `pctWeight` | 市值占比(%) | |
| `purchaseQuantity` | 申购数量(股) | |
| `cashSubstituteFlag` | 现金替代标志 | `允许` 或 `必须` |
| `purchasePremiumRatio` | 申购现金替代溢价比例(%) | |
| `redemptionPremiumRatio` | 赎回现金替代溢价比例(%) | |
| `fixedSubstituteAmount` | 固定替代金额(元) | |
| `purchaseSubstituteAmount` | 申购替代金额(元) | |
| `redemptionSubstituteAmount` | 赎回替代金额(元) | |

## 约束与说明

- 单次最多 10000 行。成分很多时一次少查几只 ETF。
- 必须现金替代的成分，申购数量可能为 0。

## 调用示例

```bash
python3 scripts/etf_components.py --securities 510300.SH
python3 scripts/etf_components.py --securities 创业板成长ETF华夏
```

## 返回说明

- **成功**：在 `workspace/gangtise/etf_components/` 下生成 `etf_pcf_components_*.csv`。行数超过 100 时，回复只展示前 3 行和后 3 行。
- **无数据**：提示未找到 ETF申赎成分股。
