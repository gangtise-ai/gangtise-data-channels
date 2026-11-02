# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/references/issuance.md
# Regenerate: python3 scripts/generate.py
# 发行与增发明细（Open API · bond/issuance-detail）

## 简介

返回首发与历次增发（续发）的发行公告日、招标日、缴款日、上市日、计划与实际发行规模、发行价格、边际利率、认购倍数等。多行型：每只债券每个发行批次一行。脚本：`scripts/issuance.py`。

数据范围：

- **试用账号**与**正式账号**均支持查询全市场数据，覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）、银行间（`.IB`）。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 债券代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` 路径（读 `security_code` / `code` / `代码` / `债券代码` / `security_abbr` / `债券简称` 列）。非标准代码自动经债券检索解析 |
| `-sd` / `--start-date` | 否 | 发行公告日起始；不传返回全部记录 |
| `-ed` / `--end-date` | 否 | 发行公告日截止；不传返回全部记录 |
| `--field-list` | 否 | 字段英文名或中文名，逗号分隔；传 `all` 返回全部字段。字段不在下表时直接报错并列出可选字段 |
| `-od` / `--output-dir` | 否 | 结果保存目录，建议绝对路径；文件名自动生成 |

## 字段说明

不传 `--field-list` 返回全部字段；查询键字段始终返回。

| 字段 | 中文列名 | 默认 | 说明 |
|------|----------|------|------|
| `securityCode` | 债券代码 | 始终 | 债券代码 |
| `issueBatchNo` | 发行批次 | 始终 | 发行 / 增发批次，取值如 `"首发"`、`"第一次增发"`、`"第二次增发"` |
| `securityName` | 债券简称 | ✓ | 债券简称 |
| `issueAnnouncementDate` | 发行公告日 | ✓ | 发行公告日，格式 `yyyy-MM-dd` |
| `biddingDate` | 发行招标日 | ✓ | 发行招标日，格式 `yyyy-MM-dd` |
| `paymentDate` | 发行缴款日 | ✓ | 发行缴款日，格式 `yyyy-MM-dd` |
| `underwritingMethod` | 承销方式 | ✓ | 承销方式 |
| `biddingMethod` | 招标方式 | ✓ | 招标方式 |
| `biddingTarget` | 招标标的 | ✓ | 招标标的，非招标发行返回 `null` |
| `plannedIssueSize` | 计划发行总额(亿元) | ✓ | 本次计划发行总额（单位：亿元） |
| `actualIssueSize` | 实际发行总额(亿元) | ✓ | 本次实际发行总额（单位：亿元） |
| `issuePrice` | 发行价格(元) | ✓ | 本次发行价格（单位：元） |
| `referenceYield` | 参考收益率(%) | ✓ | 参考收益率（单位：%） |
| `marginalRate` | 边际利率(%) | ✓ | 边际利率（单位：%） |
| `bidToCoverRatio` | 全场认购倍数 | ✓ | 全场认购倍数 |
| `marginalBidToCoverRatio` | 边际认购倍数 | ✓ | 边际认购倍数 |

## 约束与说明

- 传了日期时，脚本先取每只债券的存续期，与 `-sd/-ed` 取交集后分批请求，避免区间过长被拒绝；只传一端日期时另一端不设限。

## 调用示例

**全部批次：**

```bash
python3 scripts/issuance.py --securities 23国债15
```

**指定公告日起始：**

```bash
python3 scripts/issuance.py --securities 019708.SH -sd 2023-01-01
```

## 返回说明

- **成功**：在 `workspace/gangtise/issuance/` 下生成 `bond_*.csv`（列名为中文），回复中附 Markdown 预览与文件路径。
- **无数据**：全部查询键均无数据时提示未找到。
- **失败**：授权失败、债券无法解析、字段名非法、超出上限等，返回错误说明与处理建议。
