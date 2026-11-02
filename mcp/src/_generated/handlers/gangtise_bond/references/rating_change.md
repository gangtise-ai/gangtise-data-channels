# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/references/rating_change.md
# Regenerate: python3 scripts/generate.py
# 债项评级变动（Open API · bond/rating-change）

## 简介

返回债券历次债项评级变动：本次 / 上次评级、变动方向、评级展望、最新评级日期、评级机构。多行型：每只债券每次变动一行，无变动记录的债券不产生行。脚本：`scripts/rating_change.py`。

数据范围：

- **试用账号**与**正式账号**均支持查询全市场数据，覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）、银行间（`.IB`）。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 债券代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` 路径（读 `security_code` / `code` / `代码` / `债券代码` / `security_abbr` / `债券简称` 列）。非标准代码自动经债券检索解析 |
| `-sd` / `--start-date` | 否 | 公告日期起始；不传返回全部历史 |
| `-ed` / `--end-date` | 否 | 公告日期截止；不传返回全部历史 |
| `--field-list` | 否 | 字段英文名或中文名，逗号分隔；传 `all` 返回全部字段。字段不在下表时直接报错并列出可选字段 |
| `-od` / `--output-dir` | 否 | 结果保存目录，建议绝对路径；文件名自动生成 |

## 字段说明

不传 `--field-list` 返回全部字段；查询键字段始终返回。

| 字段 | 中文列名 | 默认 | 说明 |
|------|----------|------|------|
| `securityCode` | 债券代码 | 始终 | 债券代码 |
| `announcementDate` | 公告日期 | 始终 | 评级变动公告日期，格式 `yyyy-MM-dd` |
| `securityName` | 债券简称 | ✓ | 债券简称 |
| `bondType` | 债券类型 | ✓ | 债券类型 |
| `ratingType` | 评级类型 | ✓ | 评级类型 |
| `currentRating` | 本次评级 | ✓ | 本次评级结果 |
| `previousRating` | 上次评级 | ✓ | 上次评级结果，首次评级返回 `null` |
| `changeDirection` | 变动方向 | ✓ | 评级变动方向 |
| `ratingOutlook` | 评级展望 | ✓ | 本次评级展望 |
| `latestRatingDate` | 最新评级日期 | ✓ | 最新评级日期，格式 `yyyy-MM-dd` |
| `ratingAgency` | 评级机构 | ✓ | 评级机构 |

## 约束与说明

- 接口单次最多 10 只，脚本自动按 10 只分批。
- 首次评级时 `上次评级` 为空。

## 调用示例

**指定起始日期：**

```bash
python3 scripts/rating_change.py --securities H1万科04,23万科MTN001 -sd 2025-01-01
```

## 返回说明

- **成功**：在 `workspace/gangtise/rating_change/` 下生成 `bond_*.csv`（列名为中文），回复中附 Markdown 预览与文件路径。
- **无数据**：全部查询键均无数据时提示未找到。
- **失败**：授权失败、债券无法解析、字段名非法、超出上限等，返回错误说明与处理建议。
