# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/references/issuer_rating_change.md
# Regenerate: python3 scripts/generate.py
# 发债主体评级变动（Open API · bond/issuer-rating-change）

## 简介

返回发行人历次主体评级变动：本次 / 上次评级、变动方向、评级展望、评级机构（含惠誉、穆迪、标普等境外机构）。多行型：每个发行人每次变动一行。脚本：`scripts/issuer_rating_change.py`。

数据范围：

- **试用账号**与**正式账号**均支持查询全市场数据，覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）、银行间（`.IB`）。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 二选一 | 债券代码 / 简称 / 拼音，返回其发行人的评级变动 |
| `--issuers` | 二选一 | 公司全称或简称，逗号分隔。全称直接查询；简称只在唯一命中时换成全称，多家全部列出 |
| `-sd` / `--start-date` | 否 | 公告日期起始；不传返回全部历史 |
| `-ed` / `--end-date` | 否 | 公告日期截止；不传返回全部历史 |
| `--field-list` | 否 | 字段英文名或中文名，逗号分隔；传 `all` 返回全部字段。字段不在下表时直接报错并列出可选字段 |
| `-od` / `--output-dir` | 否 | 结果保存目录，建议绝对路径；文件名自动生成 |

## 字段说明

不传 `--field-list` 返回全部字段；查询键字段始终返回。

| 字段 | 中文列名 | 默认 | 说明 |
|------|----------|------|------|
| `issuerName` | 发行人 | 始终 | 发行人全称 |
| `announcementDate` | 公告日期 | 始终 | 评级变动公告日期，格式 `yyyy-MM-dd` |
| `enterpriseNature` | 企业性质 | ✓ | 企业性质 |
| `region` | 所属地域 | ✓ | 所属地域 |
| `ratingType` | 评级类型 | ✓ | 评级类型 |
| `currentRating` | 本次评级 | ✓ | 本次评级结果 |
| `previousRating` | 上次评级 | ✓ | 上次评级结果，首次评级返回 `null` |
| `changeDirection` | 变动方向 | ✓ | 评级变动方向 |
| `ratingOutlook` | 评级展望 | ✓ | 本次评级展望 |
| `latestRatingDate` | 最新评级日期 | ✓ | 最新评级日期，格式 `yyyy-MM-dd` |
| `previousRatingDate` | 上次评级日期 | ✓ | 上次评级日期，格式 `yyyy-MM-dd`，首次评级返回 `null` |
| `ratingAgency` | 评级机构 | ✓ | 评级机构 |

## 约束与说明

- 接口单次最多命中 10 个发行人，脚本按 10 个一批分批请求。
- 境外机构评级符号体系与境内不同（如 `Caa2`、`RD`），不能直接按符号比较。

## 调用示例

**按名称 + 起始日期：**

```bash
python3 scripts/issuer_rating_change.py --issuers 万科 -sd 2025-01-01
```

**按债券：**

```bash
python3 scripts/issuer_rating_change.py --securities H1万科04 --field-list currentRating,previousRating,changeDirection,ratingAgency
```

## 返回说明

- **成功**：在 `workspace/gangtise/issuer_rating_change/` 下生成 `bond_*.csv`（列名为中文），回复中附 Markdown 预览与文件路径。
- **无数据**：全部查询键均无数据时提示未找到。
- **失败**：授权失败、债券无法解析、字段名非法、超出上限等，返回错误说明与处理建议。
