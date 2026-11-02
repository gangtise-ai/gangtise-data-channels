# 基金档案（Open API · fund/basic-info、fee-rate、manager-history）

## 简介

一个脚本查询三类档案，由 `--type` 选择，各自落盘：

| `--type` | 接口 | 内容 | 模块文件名前缀 |
|----------|------|------|----------------|
| `basic`（默认） | `fund/basic-info` | 分类、管理人、成立与存续、申赎规则、业绩基准、跟踪指数 | `basic_info` |
| `fee` | `fund/fee-rate` | 申购费、赎回费、管理费、托管费、销售服务费及条件区间 | `fee_rate` |
| `manager` | `fund/manager-history` | 历任与现任基金经理、任职区间、管理天数与任职回报 | `manager_history` |

`all` 或逗号分隔可同时查多项。基本信息、费率是当前截面；历任经理是全部任职记录。试用账号与正式账号均可查全量，无历史长度限制。脚本：`scripts/profile.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 基金代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv` 路径。场外基金请直接传 `.OF` 代码 |
| `--type` / `-t` | 否 | `basic` / `fee` / `manager`，逗号分隔；`all` 三项都查。默认 `basic` |
| `--fee-type` | 否 | 仅 `fee`：`purchaseFee` 申购费、`redemptionFee` 赎回费、`managementFee` 管理费、`custodianFee` 托管费、`saleFee` 销售服务费，可传中文。不传返回全部类型 |
| `--field-list` | 否 | 仅 `basic`：字段英文名或中文名，逗号分隔；不传或 `all` 返回全部字段 |
| `-od` / `--output-dir` | 否 | 结果保存目录，建议绝对路径 |

## 字段说明

### 基金基本信息

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | 如 `005827.OF`、`159967.SZ` |
| `fundName` | 基金简称 | |
| `fullName` | 基金全称 | |
| `mainFundCode` | 基金主代码 | 同一只基金的 A/C 等份额共用 |
| `investTypeCodeLevel1` | 一级分类代码 | |
| `investTypeNameLevel1` | 一级分类 | 如「股票型基金」「混合型基金」 |
| `investTypeCodeLevel2` | 二级分类代码 | |
| `investTypeNameLevel2` | 二级分类 | 如「被动指数型基金」「偏股混合型基金」 |
| `mgrComp` | 基金管理人 | |
| `custodianBank` | 基金托管人 | |
| `setupDate` | 成立日期 | `yyyy-MM-dd` |
| `maturityDate` | 存续截止日 | 无固定存续期为空 |
| `operationStatus` | 运行状态 | 如「存续中」 |
| `operationMode` | 运作方式 | 如「开放式」「ETF」 |
| `exchange` | 交易场所 | 场外基金为空 |
| `purchaseStatus` | 申购状态 | |
| `minPurchaseAmount` | 单笔申购下限(元) | |
| `largePurchaseLimit` | 大额申购上限(元) | 不限时为空 |
| `minRedemptionShare` | 单笔赎回下限(份) | |
| `redemptionArrivalDays` | 赎回到账天数(天) | |
| `benchmark` | 业绩比较基准 | |
| `riskLevel` | 风险等级 | 低 / 中低 / 中 / 中高 / 高 |
| `investScope` | 投资范围 | 长文本，预览会截断，全文在 CSV |
| `isIndexFund` | 是否指数型基金 | 是 / 否 |
| `trackIndexCode` | 跟踪指数代码 | 非指数型为空 |
| `trackIndexName` | 跟踪指数名称 | 非指数型为空 |

### 基金费率

一只基金按费率条件返回多行。管理费、托管费、销售服务费通常没有条件区间。

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `feeType` | 费率类型 | 已换成中文：申购费、赎回费、管理费、托管费、销售服务费 |
| `feeCondition` | 费率条件 | 如「持有期限＜7日」「100万元≤申购金额＜200万元」；无区间时为空 |
| `feeRate` | 费率 | 如 `1.5%`、`0%`；大额固定收费时为金额描述，如「每笔1000元」 |

### 历任基金经理

每位经理的每段任职一行。现任的任职结束日期为空。

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `managerName` | 基金经理 | |
| `startDate` | 任职开始日期 | `yyyy-MM-dd` |
| `endDate` | 任职结束日期 | 现任为空 |
| `managedDays` | 管理天数(天) | |
| `managedReturn` | 任职回报(%) | 该段任职期间的业绩表现 |

## 约束与说明

- 单次最多 10000 行。费率按条件展开、历任经理按任职段展开，只数很多时请分批。
- `--field-list` 在未查基本信息时会报错；`--fee-type` 在未查费率时会报错。

## 调用示例

```bash
python3 scripts/profile.py --securities 创业板成长ETF华夏
python3 scripts/profile.py --securities 005827.OF --type all
python3 scripts/profile.py --securities 005827.OF --type fee --fee-type 管理费,托管费
python3 scripts/profile.py --securities 005827.OF --field-list 基金简称,成立日期,一级分类,风险等级
```

## 返回说明

- **成功**：在 `workspace/gangtise/profile/` 下按类型生成 CSV，回复中附 Markdown 预览与文件路径。
- **部分无数据**：查到的类型正常返回，未查到的类型写在说明里。
- **失败**：授权失败、基金无法解析、字段名非法时返回错误说明。
