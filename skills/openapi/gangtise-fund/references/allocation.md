# 基金持仓分布（Open API · asset-allocation、industry-allocation、bond-type-allocation、fund-type-allocation）

## 简介

一个脚本查询四类定期报告分布，由 `--type` 选择，各自落盘：

| `--type` | 接口 | 内容 | 模块文件名前缀 |
|----------|------|------|----------------|
| `asset`（默认） | `fund/asset-allocation` | 报告期末大类资产金额及占资产总值比 | `asset_allocation` |
| `industry` | `fund/industry-allocation` | 持股按申万或中信一级行业汇总，占净值比 | `industry_allocation` |
| `bond` | `fund/bond-type-allocation` | 持债按券种汇总，占净值比 | `bond_type_allocation` |
| `fund` | `fund/fund-type-allocation` | 持有基金按一级分类汇总，占净值比 | `fund_type_allocation` |

一只基金一个报告期按类别返回多行。试用账号前溯 3 年、正式账号前溯 5 年。脚本：`scripts/allocation.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 基金代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv`。场外基金请直接传 `.OF` |
| `--type` / `-t` | 否 | `asset` / `industry` / `bond` / `fund`，逗号分隔；`all` 四项都查。默认 `asset` |
| `-sd` / `--start-date` | 否 | 报告期起，`yyyy-MM-dd`。不传不限制 |
| `-ed` / `--end-date` | 否 | 报告期止，`yyyy-MM-dd`。不传不限制 |
| `--asset-level` | 否 | 仅 `asset`：`level1` 一级、`level2` 二级，可同时传。不传返回全部层级 |
| `--industry-standard` | 否 | 仅 `industry`：`swIndustry` 申万一级（接口默认）、`citicIndustry` 中信一级。也可写「申万」「中信」 |
| `--position-type` | 否 | 仅 `industry`：`top` 重仓（各季披露，接口默认）、`all` 全部持股（仅半年报、年报） |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

报告期常用 `03-31`、`06-30`、`09-30`、`12-31`。季报配 `--position-type all` 往往没有行业分布。

## 字段说明

### 资产配置

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | `yyyy-MM-dd` |
| `assetLevel` | 资产层级 | 一级 / 二级 |
| `assetType` | 资产类型代码 | 接口原值，如 `equityInv`、`stock` |
| `assetTypeName` | 资产类型 | 与定期报告口径一致，如「权益投资」「股票」 |
| `holdingValue` | 金额(元) | |
| `pctToTotalAsset` | 占基金资产总值比(%) | |

一级类型包括权益投资、基金投资、固定收益投资、贵金属、金融衍生品、买入返售、货币市场工具、银行存款和结算备付金、其他资产。二级类型挂在对应一级下，如股票、债券、资产支持证券。

### 持股行业分布

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | |
| `industryStandard` | 行业分类标准 | 申万一级行业 / 中信一级行业 |
| `industryCode` | 行业代码 | |
| `industryName` | 行业名称 | 如「食品饮料」 |
| `pctToNav` | 占基金净值比(%) | |
| `positionType` | 持仓类型 | 重仓 / 全部 |

### 持有券种分布

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | |
| `bondTypeCode` | 券种代码 | |
| `bondTypeName` | 券种名称 | 如「企业债券」「中期票据」 |
| `pctToNav` | 占基金净值比(%) | |

### 持有基金类型分布

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | |
| `investTypeCodeLevel1` | 一级分类代码 | 持仓基金的一级分类 |
| `investTypeNameLevel1` | 一级分类 | 如「混合型基金」「股票型基金」 |
| `pctToNav` | 占基金净值比(%) | |
| `positionType` | 持仓类型 | 重仓 / 全部。重仓为季报口径，全部为半年报与年报口径 |

## 约束与说明

- 单次最多 10000 行。不传日期会拉权限范围内全部报告期，基金只数多时请指定一个或少数报告期。
- 与本次 `--type` 无关的筛选参数会被忽略，并在说明里给出 `[WARNING]`。
- 股票型基金通常没有券种或基金类型分布，该类型会提示未找到。

## 调用示例

```bash
python3 scripts/allocation.py --securities 005827.OF -sd 2026-06-30 -ed 2026-06-30
python3 scripts/allocation.py --securities 005827.OF --type asset --asset-level level1 -sd 2026-06-30 -ed 2026-06-30
python3 scripts/allocation.py --securities 005827.OF --type industry --industry-standard citicIndustry --position-type all -sd 2026-06-30 -ed 2026-06-30
python3 scripts/allocation.py --securities 005220.OF --type bond,fund -sd 2026-06-30 -ed 2026-06-30
```

## 返回说明

- **成功**：在 `workspace/gangtise/allocation/` 下按类型生成 CSV。
- **部分无数据**：查到的分布正常返回，未查到的写在说明里。
