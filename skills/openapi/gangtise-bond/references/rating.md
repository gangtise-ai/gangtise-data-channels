# 债券评级一览（Open API · bond/rating-overview）

## 简介

一次返回债项、发行人、担保人三方的最新评级（评级、评级日期、评级机构、评级类别、评级展望）。单行型：每只债券一行。脚本：`scripts/rating.py`。

数据范围：

- **试用账号**与**正式账号**均支持查询全市场数据，覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）、银行间（`.IB`）。
- **数据时效**：本接口返回最新状态数据，不区分历史版本，**无数据权限长度限制**。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 债券代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` 路径（读 `security_code` / `code` / `代码` / `债券代码` / `security_abbr` / `债券简称` 列）。非标准代码自动经债券检索解析 |
| `--field-list` | 否 | 字段英文名或中文名，逗号分隔；传 `all` 返回全部字段。字段不在下表时直接报错并列出可选字段 |
| `-od` / `--output-dir` | 否 | 结果保存目录，建议绝对路径；文件名自动生成 |

## 字段说明

不传 `--field-list` 返回全部字段；查询键字段始终返回。

| 字段 | 中文列名 | 默认 | 说明 |
|------|----------|------|------|
| `securityCode` | 债券代码 | 始终 | 债券代码 |
| `securityName` | 债券简称 | ✓ | 债券简称 |
| `bondRating` | 债项评级 | ✓ | 最新债项评级，无评级返回 `null` |
| `bondRatingDate` | 债项评级日期 | ✓ | 债项评级日期，格式 `yyyy-MM-dd` |
| `bondRatingAgency` | 债项评级机构 | ✓ | 债项评级机构 |
| `bondRatingType` | 债项评级类别 | ✓ | 债项评级类别 |
| `bondRatingOutlook` | 债项评级展望 | ✓ | 债项评级展望 |
| `issuerName` | 发行人 | ✓ | 发行人全称 |
| `issuerRating` | 主体评级 | ✓ | 最新发行人（主体）评级，无评级返回 `null` |
| `issuerRatingDate` | 主体评级日期 | ✓ | 发行人评级日期，格式 `yyyy-MM-dd` |
| `issuerRatingAgency` | 主体评级机构 | ✓ | 发行人评级机构 |
| `issuerRatingType` | 主体评级类别 | ✓ | 发行人评级类别 |
| `issuerRatingOutlook` | 主体评级展望 | ✓ | 发行人评级展望 |
| `guarantorName` | 担保人 | ✓ | 担保人全称，无担保返回 `null` |
| `guarantorRating` | 担保人评级 | ✓ | 最新担保人评级，无担保或无评级返回 `null` |
| `guarantorRatingDate` | 担保人评级日期 | ✓ | 担保人评级日期，格式 `yyyy-MM-dd` |
| `guarantorRatingAgency` | 担保人评级机构 | ✓ | 担保人评级机构 |
| `guarantorRatingType` | 担保人评级类别 | ✓ | 担保人评级类别 |
| `guarantorRatingOutlook` | 担保人评级展望 | ✓ | 担保人评级展望 |

## 约束与说明

- 接口单次最多 10 只，脚本自动按 10 只分批。

## 调用示例

**多只债券：**

```bash
python3 scripts/rating.py --securities H1万科04,23万科MTN001
```

**只看债项评级：**

```bash
python3 scripts/rating.py --securities 23万科MTN001 --field-list bondRating,bondRatingAgency,bondRatingOutlook
```

## 返回说明

- **成功**：在 `workspace/gangtise/rating/` 下生成 `bond_*.csv`（列名为中文），回复中附 Markdown 预览与文件路径。
- **无数据**：全部查询键均无数据时提示未找到。
- **失败**：授权失败、债券无法解析、字段名非法、超出上限等，返回错误说明与处理建议。
