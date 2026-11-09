# 基金公司指标（Open API · EDE）

## 简介

检索或拉取公司指标，标的限定为基金。脚本：`scripts/indicator.py`。场外基金请直接传 `.OF` 代码。

- 只传 `-k`：检索指标编码，不取数。
- `--indicators` 加 `--securities`：拉取时序或截面。纯英文和逗号视为编码，否则先按名称检索。

日频指标不含当天实时。交易所代码会先核对是不是基金，股票代码会被拒绝。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-k` / `--keyword` | 检索时 | 指标关键词 |
| `--indicators` | 取数时 | 指标编码或名称，逗号分隔 |
| `--securities` | 取数时 | 基金代码 / 简称 / 拼音，或 `.csv` |
| `-sd` / `--start-date` | 否 | 默认近一年 |
| `-ed` / `--end-date` | 否 | 默认最近已收盘日 |
| `-p` / `--params` | 否 | JSON。全局参数与按指标覆盖可以写在一起。时序默认不传 `calendarType`；需要固定日期类型时传 `ND` 自然日、`TD` 交易日、`WD` 工作日、`RD` 报告期 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 调用示例

```bash
python3 scripts/indicator.py -k 复权单位净值
python3 scripts/indicator.py --indicators fund_adj_nav --securities 005827.OF -sd 2026-03-01 -ed 2026-03-10
python3 scripts/indicator.py --indicators qte_close --securities 510300.SH -sd 2026-03-01 -ed 2026-03-10
```
