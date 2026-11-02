# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/references/asset_size.md
# Regenerate: python3 scripts/generate.py
# 基金资产规模（Open API · fund/asset-size）

## 简介

按报告期返回份额申购赎回与期末资产净值。一只基金一个报告期一行。试用账号前溯 3 年、正式账号前溯 5 年。脚本：`scripts/asset_size.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 基金代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv`。场外基金请直接传 `.OF` |
| `-sd` / `--start-date` | 否 | 报告期起。不传不限制 |
| `-ed` / `--end-date` | 否 | 报告期止。不传不限制 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 字段说明

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | `yyyy-MM-dd` |
| `sharesStart` | 期初份额(万份) | |
| `sharesPurchase` | 期间申购份额(万份) | |
| `sharesRedemption` | 期间赎回份额(万份) | |
| `sharesNetPurchase` | 期间净申购份额(万份) | 赎回大于申购时为负 |
| `sharesEnd` | 期末份额(万份) | |
| `netAsset` | 资产净值(万元) | |

## 约束与说明

- 单次最多 10000 行。
- 这是定期报告口径的份额与净值，不是交易日份额。ETF 的日度份额用 `etf_share.py`。

## 调用示例

```bash
python3 scripts/asset_size.py --securities 005827.OF -sd 2026-03-31 -ed 2026-06-30
```

## 返回说明

- **成功**：在 `workspace/gangtise/asset_size/` 下生成 `asset_size_*.csv`。
- **无数据**：提示未找到资产规模。
