# 债券公司指标（Open API · EDE）

## 简介

检索或拉取公司指标，标的限定为债券。脚本：`scripts/indicator.py`。

- 只传 `-k`：检索指标编码，不取数。
- `--indicators` 加 `--securities`：拉取时序或截面。纯英文和逗号视为编码，否则先按名称检索。

财报类指标的日期用报告期季度末（`03-31` / `06-30` / `09-30` / `12-31`）。日频指标不含当天实时。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-k` / `--keyword` | 检索时 | 指标关键词 |
| `--indicators` | 取数时 | 指标编码或名称，逗号分隔 |
| `--securities` | 取数时 | 债券代码 / 简称 / 拼音，或 `.csv` |
| `-sd` / `--start-date` | 否 | 默认近一年 |
| `-ed` / `--end-date` | 否 | 默认最近已收盘日 |
| `-p` / `--params` | 否 | JSON。全局参数与按指标覆盖可以写在一起 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 调用示例

```bash
python3 scripts/indicator.py -k 资产合计
python3 scripts/indicator.py --indicators bs_aset --securities 2680022.IB -sd 2024-12-31 -ed 2025-12-31
python3 scripts/indicator.py --indicators is_op_rev_ttm --securities 26京投债01 -sd 2025-01-01 -ed 2025-12-31
```

股票和基金会被拒绝。
