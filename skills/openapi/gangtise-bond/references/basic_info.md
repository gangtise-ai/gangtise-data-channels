# 债券基本资料（Open API · bond/basic-info）

## 简介

返回债券静态档案：发行、期限、利率付息、评级、担保、特殊条款，以及 ABS / 可转债专项字段。单行型接口：每只债券一行，库内无资料的债券仍占一行（除代码外全为空）。脚本：`scripts/basic_info.py`。

数据范围：

- **试用账号**与**正式账号**均支持查询全市场债券基本资料，数据范围覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）、银行间（`.IB`）。
- **数据时效**：本接口返回债券的**最新**静态资料，不区分历史版本，因此**无数据权限长度限制**。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 债券代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` 路径（读 `security_code` / `code` / `代码` / `债券代码` / `security_abbr` / `债券简称` 列）。非标准代码自动经债券检索解析 |
| `--field-list` | 否 | 字段英文名或中文名，逗号分隔；传 `all` 返回全部字段。字段不在下表时直接报错并列出可选字段 |
| `-od` / `--output-dir` | 否 | 结果保存目录，建议绝对路径；文件名自动生成 |

## 字段说明

「默认」列标 ✓ 的为不传 `--field-list` 时返回的常用字段；查询键字段始终返回。

| 字段 | 中文列名 | 默认 | 说明 |
|------|----------|------|------|
| `securityCode` | 债券代码 | 始终 | 债券代码（如 `"019742.SH"`、`"220205.IB"`） |
| `securityName` | 债券简称 | ✓ | 债券简称（如 `"23国债15"`） |
| `securityFullName` | 债券全称 | ✓ | 债券全称（如 `"2023年记账式附息（十五期）国债"`） |
| `bondType` | 债券类型 | ✓ | 债券类型 |
| `exchange` | 交易市场 | ✓ | 交易市场 |
| `currency` | 发行币种 |  | 发行币种 |
| `issuer` | 发行人 | ✓ | 发行人全称 |
| `issueMethod` | 发行方式 |  | 发行方式 |
| `leadUnderwriter` | 主承销商 |  | 主承销商 |
| `issueSize` | 发行总量(亿元) | ✓ | 发行总量（单位：亿元） |
| `outstandingBalance` | 当前余额(亿元) | ✓ | 当前余额（单位：亿元），已考虑回售、赎回、转股等减记 |
| `parValue` | 初始面值/最新面值(元) |  | **初始面值(元)/最新面值(元)**，以 `/` 分隔的复合展示值，如 `"100.00/100.00"`；某一侧无数据时该侧以 `-` 占位，如 `"100.00/-"`、`"-/98.50"`。摊还型债券最新面值小于初始面值 |
| `latestParValue` | 最新面值(元/张) |  | 最新面值（单位：元/张），即 `parValue` 后半部分的数值形式，便于程序化取用 |
| `issuePriceOrReferenceYield` | 发行价格(元)/参考收益率(%) |  | **发行价格(元)/参考收益率(%)**，以 `/` 分隔的复合展示值，如 `"100.00/2.6700"`；某一侧无数据时该侧以 `-` 占位，如 `"100.00/-"`、`"-/2.6700"` |
| `issueFee` | 发行手续费(元) |  | 发行手续费（单位：元） |
| `biddingTarget` | 招标标的 |  | 招标标的，非招标发行返回 `null` |
| `accountingType` | 会计处理类型 |  | 会计处理类型 |
| `issuerRegion` | 发行人所属地区 |  | 发行人所属地区（如 `"广东省深圳市"`） |
| `industry` | 所属行业 |  | 发行人所属行业 |
| `issueAnnouncementDate` | 发行公告日 |  | 发行公告日 |
| `issueDate` | 发行日期 |  | 发行日期 |
| `issueResultAnnouncementDate` | 发行结果公告日 |  | 发行结果公告日 |
| `listDate` | 上市日期 |  | 上市日期 |
| `delistDate` | 摘牌日期 |  | 摘牌日期，未摘牌返回 `null` |
| `valueDate` | 起息日期 | ✓ | 起息日期 |
| `maturityDate` | 到期日期 | ✓ | 到期日期（票面约定的法定到期日） |
| `actualMaturityDate` | 实际到期日 |  | 实际到期日，含提前赎回、回售、全额转股等情形；未提前终止时与 `maturityDate` 一致 |
| `issueTerm` | 发行期限(年) |  | 发行期限（单位：年） |
| `remainingTerm` | 剩余期限(年) | ✓ | 剩余期限（单位：年），基于最新交易日与 `actualMaturityDate` 计算 |
| `remainingDays` | 剩余天数 |  | 剩余天数（单位：天），已到期返回 `0` |
| `couponRate` | 票面利率(%) | ✓ | 当期票面利率（单位：%） |
| `interestRateType` | 利率类型 | ✓ | 利率类型 |
| `interestFrequency` | 付息频率 |  | 付息频率 |
| `interestRateDescription` | 利率说明 |  | 利率说明，浮动利率债券在此说明基准利率与利差规则 |
| `interestAccrualMethod` | 计息方式 |  | 计息方式 |
| `nextInterestPaymentDate` | 下一付息日 |  | 下一付息日，格式 `yyyy-MM-dd`；无后续付息安排返回 `null` |
| `daysToNextInterestPayment` | 距下一付息日(天) |  | 距下一付息日天数（单位：天） |
| `compensationInterest` | 补偿利息(元/张) |  | 补偿利息（单位：元/张），适用于含补偿利息条款的可转债/可交换债 |
| `compensationRate` | 补偿利率(%) |  | 补偿利率（单位：%） |
| `latestBondRating` | 最新债项评级 |  | 最新债项评级，无评级返回 `null` |
| `latestRating` | 最新评级(主体/债项) | ✓ | **最新评级(主体/债项)**，以 `/` 分隔的复合展示值，如 `"AAA/AA+"`；某一侧无评级时该侧以 `-` 占位，如 `"AAA/-"`、`"-/AA"` |
| `issueRating` | 发行时评级(主体/债项) |  | **发行时评级(主体/债项)**，以 `/` 分隔的复合展示值，如 `"AA+/AA"`；某一侧无评级时该侧以 `-` 占位，如 `"AA+/-"`、`"-/AA"` |
| `ratingAgency` | 评级机构 |  | 评级机构 |
| `guarantor` | 担保人 |  | 担保人全称，无担保返回 `null` |
| `guaranteeMethod` | 担保方式 |  | 担保方式 |
| `guaranteePeriod` | 担保时段 |  | 担保时段（如 `"2023-05-10 至 2028-05-10"`） |
| `specialTerms` | 内含特殊条款 | ✓ | 内含特殊条款，无特殊条款返回 `null` |
| `termsDescription` | 条款说明 |  | 条款说明，对 `specialTerms` 中各条款的触发条件与执行规则的文字描述 |
| `nextExerciseDate` | 下一行权日 | ✓ | 下一行权日，格式 `yyyy-MM-dd`；无行权安排返回 `null` |
| `putDate` | 债券回售日 |  | 债券回售日，格式 `yyyy-MM-dd` |
| `conditionalPutStartDate` | 条件回售起始日期 |  | 条件回售起始日期，格式 `yyyy-MM-dd` |
| `conditionalPutEndDate` | 条件回售截止日期 |  | 条件回售截止日期，格式 `yyyy-MM-dd` |
| `specialRevisionStartDate` | 特别修正起始日期 |  | 特别修正起始日期（转股价特别向下修正条款），格式 `yyyy-MM-dd` |
| `specialRevisionEndDate` | 特别修正截止日期 |  | 特别修正截止日期，格式 `yyyy-MM-dd` |
| `pledgeCode` | 质押券代码 |  | 质押券代码，不可质押返回 `null` |
| `standardBondConversion` | 折合标准券(元) |  | 折合标准券（单位：元），即每百元面值可折算的标准券金额 |
| `absProjectName` | ABS项目名称 |  | ABS 项目名称 |
| `absUnderlyingAssetType` | ABS基础资产类型 |  | ABS 基础资产类型 |
| `trusteeOrPlanManager` | 受托机构/计划管理人 |  | 受托机构 / 计划管理人 |
| `originator` | 发起机构/原始权益人 |  | 发起机构 / 原始权益人 |
| `conversionStartDate` | 转换期起始日 |  | 转换期起始日 |
| `conversionEndDate` | 转换期截止日 |  | 转换期截止日 |
| `conversionSecurityCode` | 转股证券代码 |  | 转股证券代码（转换后正股代码，如 `"600519.SH"`） |
| `conversionDeclarationCode` | 转股申报代码 |  | 转股申报代码（交易所转股委托代码） |
| `lastConversionDate` | 最后转股日 |  | 最后转股日 |

## 约束与说明

- 脚本按 10000 只一批请求。
- 枚举字段（债券类型、交易市场、利率类型、付息频率、ABS 基础资产类型、国民经济行业、发行人所属地区）自动换为中文名称。

## 调用示例

**常用字段：**

```bash
python3 scripts/basic_info.py --securities 23国债15,H1万科04
```

**全部字段：**

```bash
python3 scripts/basic_info.py --securities 019708.SH --field-list all
```

**指定字段（中文名亦可）：**

```bash
python3 scripts/basic_info.py --securities 23万科MTN001 --field-list 票面利率,到期日期,最新评级,内含特殊条款
```

## 返回说明

- **成功**：在 `workspace/gangtise/basic_info/` 下生成 `bond_*.csv`（列名为中文），回复中附 Markdown 预览与文件路径。
- **无数据**：全部查询键均无数据时提示未找到。
- **失败**：授权失败、债券无法解析、字段名非法、超出上限等，返回错误说明与处理建议。
