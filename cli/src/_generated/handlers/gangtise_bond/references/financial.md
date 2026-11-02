# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/references/financial.md
# Regenerate: python3 scripts/generate.py
# 发债公司财务报表（Open API · financial-report）

## 简介

按债券查询发行人的利润表、资产负债表、现金流量表。脚本只接受债券；请求走 A 股 `financial-report` 接口。脚本：`scripts/financial.py`。

资产负债表只有累计值。利润表和现金流量表可以用 `--granularity quarterly` 取单季度。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 债券代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` |
| `-t` / `--table-type` | 否 | `income` / `balance` / `cashflow`，默认 `income` |
| `-g` / `--granularity` | 否 | `accumulated`（默认）/ `quarterly`。`quarterly` 只用于利润表和现金流量表 |
| `--period` | 否 | `Q1` / `Q2` / `Q3` / `Q4` / `Q0`，默认 `Q0` |
| `--fiscal-year` | 否 | 财报年度，逗号分隔 |
| `-sd` / `--start-date` | 否 | 开始日期 |
| `-ed` / `--end-date` | 否 | 结束日期 |
| `--report-type` | 否 | 默认 `consolidated` |
| `--field-list` | 否 | 科目英文名；不传返回全部科目 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 调用示例

```bash
python3 scripts/financial.py --securities 2680022.IB --field-list totalOpRev,netProfit
python3 scripts/financial.py --table-type balance --securities 26京投债01 --fiscal-year 2024 --period Q4
python3 scripts/financial.py --table-type cashflow --granularity quarterly --securities 2680022.IB --fiscal-year 2024 --period Q1
```

股票代码会被拒绝。详见债券检索规则：简称多家匹配时列出候选，不自动取其中一只。
