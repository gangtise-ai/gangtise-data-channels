# 基金前十大持有人（Open API · fund/top10-holders）

## 简介

按报告期返回前十大持有人的持有份额及占上市总份额比例。一只基金一个报告期最多十行。试用账号前溯 3 年、正式账号前溯 5 年。脚本：`scripts/top_holders.py`。

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
| `serialNumber` | 排名 | |
| `holderName` | 持有人名称 | |
| `holdingShares` | 持有份额(份) | |
| `holdingPct` | 持有占比(%) | 占上市总份额 |

## 约束与说明

- 单次最多 10000 行。
- 名单里的持有人名称是基金披露原文，可能是机构专户或个人。

## 调用示例

```bash
python3 scripts/top_holders.py --securities 161005.OF -sd 2025-12-31 -ed 2025-12-31
```

## 返回说明

- **成功**：在 `workspace/gangtise/top_holders/` 下生成 `top10_holders_*.csv`。
- **无数据**：提示未找到前十大持有人。
