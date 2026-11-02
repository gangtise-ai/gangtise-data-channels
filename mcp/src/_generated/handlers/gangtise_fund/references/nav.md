# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/references/nav.md
# Regenerate: python3 scripts/generate.py
# 基金净值表现（Open API · fund/nav）

## 简介

按交易日返回单位净值、累计净值、复权净值和货币基金收益。一只基金一个交易日一行。试用账号前溯 3 年、正式账号前溯 5 年。脚本：`scripts/nav.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 基金代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv`。场外基金请直接传 `.OF` |
| `-sd` / `--start-date` | 否 | 开始日期。两端都不传时默认近 7 日，近 7 日无数据（如长假）时自动放宽到近 30 日 |
| `-ed` / `--end-date` | 否 | 结束日期。不传默认今天 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 字段说明

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `tradeDate` | 交易日 | `yyyy-MM-dd` |
| `navUnit` | 单位净值(元) | |
| `navAccumulated` | 累计单位净值(元) | |
| `adjustFactor` | 复权因子 | 货币基金为空 |
| `navAdjusted` | 复权单位净值(元) | |
| `mmfAnnualizedYield` | 7日年化收益率(%) | 仅货币基金 |
| `mmfUnitYield` | 万份收益(元) | 仅货币基金，每万份基金单位当日收益 |

## 约束与说明

- 单次最多 10000 行。不传日期只取近 7 日，避免一次拉出全部历史。
- 净值日可能晚于自然日。不传日期时近 7 日为空会自动放宽到近 30 日；指定区间仍为空时，把区间放到最近有净值的日期，不要当成这只基金没有净值。
- 非货币基金的万份收益、7 日年化为空；货币基金的复权因子、复权净值可能为空。

## 调用示例

```bash
python3 scripts/nav.py --securities 159967.SZ -sd 2026-08-25 -ed 2026-08-27
python3 scripts/nav.py --securities 005827.OF -sd 2026-08-01 -ed 2026-08-31
```

## 返回说明

- **成功**：在 `workspace/gangtise/nav/` 下生成 `nav_*.csv`。
- **无数据**：提示未找到净值表现。
