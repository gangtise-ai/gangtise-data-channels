# 含权债行权提示（Open API · bond/exercise-notice）

## 简介

返回含权债（赎回、回售、调整票面利率等）的行权日、申请期、行权公告日、资金到账日、行权价格、行权金额与行权后余额。多行型：每只债券每个行权日一行。脚本：`scripts/exercise_notice.py`。

数据范围：

- **试用账号**与**正式账号**均支持查询全市场数据，覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）、银行间（`.IB`）。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 债券代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` 路径（读 `security_code` / `code` / `代码` / `债券代码` / `security_abbr` / `债券简称` 列）。非标准代码自动经债券检索解析 |
| `-sd` / `--start-date` | 否 | 行权日起始；不传不限 |
| `-ed` / `--end-date` | 否 | 行权日截止；不传不限 |
| `--field-list` | 否 | 字段英文名或中文名，逗号分隔；传 `all` 返回全部字段。字段不在下表时直接报错并列出可选字段 |
| `-od` / `--output-dir` | 否 | 结果保存目录，建议绝对路径；文件名自动生成 |

## 字段说明

不传 `--field-list` 返回全部字段；查询键字段始终返回。

| 字段 | 中文列名 | 默认 | 说明 |
|------|----------|------|------|
| `securityCode` | 债券代码 | 始终 | 债券代码 |
| `exerciseDate` | 行权日 | 始终 | 行权日，格式 `yyyy-MM-dd` |
| `securityName` | 债券简称 | ✓ | 债券简称 |
| `optionType` | 权利类型 | ✓ | 权利类型 |
| `exerciseApplyStartDate` | 行权申请起始日 | ✓ | 行权申请起始日，格式 `yyyy-MM-dd` |
| `exerciseApplyEndDate` | 行权申请截止日 | ✓ | 行权申请截止日，格式 `yyyy-MM-dd` |
| `exerciseAnnouncementDate` | 行权公告日 | ✓ | 行权公告日，格式 `yyyy-MM-dd` |
| `exerciseSettlementDate` | 行权资金到账日 | ✓ | 行权资金到账日，格式 `yyyy-MM-dd` |
| `exercisePrice` | 行权价格(元) | ✓ | 行权价格（单位：元） |
| `exerciseAmount` | 行权金额(亿元) | ✓ | 行权金额（单位：亿元），行权未完成时为 `null` |
| `balanceAfterExercise` | 行权后余额(亿元) | ✓ | 行权后债券余额（单位：亿元），行权未完成时为 `null` |

## 约束与说明

- 只传一端日期时另一端自动补为开放边界。

## 调用示例

**全部行权记录：**

```bash
python3 scripts/exercise_notice.py --securities H1万科04
```

## 返回说明

- **成功**：在 `workspace/gangtise/exercise_notice/` 下生成 `bond_*.csv`（列名为中文），回复中附 Markdown 预览与文件路径。
- **无数据**：全部查询键均无数据时提示未找到。
- **失败**：授权失败、债券无法解析、字段名非法、超出上限等，返回错误说明与处理建议。
