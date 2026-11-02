# ETF 基金份额变动（Open API · fund/etf-share-change）

## 简介

按交易日返回 ETF 份额、规模及较上一日的变动。一只基金一个交易日一行。试用账号前溯 3 年、正式账号前溯 5 年。脚本：`scripts/etf_share.py`。

定期报告里的份额申赎用 `asset_size.py`，那是季报口径，单位和频率都不同。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | ETF 代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` |
| `-sd` / `--start-date` | 否 | 开始日期。两端都不传时默认近 7 日，近 7 日无数据（如长假）时自动放宽到近 30 日 |
| `-ed` / `--end-date` | 否 | 结束日期。不传默认今天 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 字段说明

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `tradeDate` | 交易日 | `yyyy-MM-dd` |
| `shares` | 份额(万份) | |
| `sharesChange` | 份额变动(万份) | 较上一交易日，净赎回为负 |
| `sharesChangeRate` | 份额变化率(%) | |
| `scale` | 规模(万元) | |
| `scaleChange` | 规模变动(万元) | 较上一交易日 |

## 约束与说明

- 单次最多 10000 行。
- 只覆盖有场内份额披露的 ETF。普通场外基金请用 `asset_size.py`。

## 调用示例

```bash
python3 scripts/etf_share.py --securities 510300.SH -sd 2026-08-25 -ed 2026-08-28
python3 scripts/etf_share.py --securities 沪深300ETF华泰柏瑞
```

## 返回说明

- **成功**：在 `workspace/gangtise/etf_share/` 下生成 `etf_share_change_*.csv`。
- **无数据**：提示未找到 ETF基金份额变动。不传日期时近 7 日为空会自动放宽到近 30 日，并在说明中注明。
