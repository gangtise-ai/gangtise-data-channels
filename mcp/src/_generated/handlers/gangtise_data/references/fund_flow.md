# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-data/references/fund_flow.md
# Regenerate: python3 scripts/generate.py
# 资金流向数据调用指导（Open API · fund-flow）

## 简介

通过 Gangtise Open API 获取 **A 股个股日资金流向**与**板块日资金流向**历史数据。脚本：`scripts/fund_flow.py`。

- **个股 / 全市场**：`fund-flow/daily`，覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）。
- **板块**：`fund-flow/sector-daily`，按板块 ID（或可唯一匹配的板块名称）查询；板块资金流向为该历史交易日当日成分股资金流向的加总，仅计入沪深北三市成分。
- 仅提供**历史**资金流向，不提供实时数据；交易日当日数据一般在 **16:30** 左右入库后方可查询。
- 个股默认 `fieldList` 为全部**净流入**相关字段：`smallNetInflow`、`mediumNetInflow`、`largeNetInflow`、`xlargeNetInflow`、`totalNetInflow`、`mainNetInflow`（`securityCode`、`tradeDate` 由接口自动前置返回）。
- 板块默认净流入字段：`sectorSmallNetInflow`、`sectorMediumNetInflow`、`sectorLargeNetInflow`、`sectorXlargeNetInflow`、`sectorMainNetInflow`（`sectorId`、`tradeDate` 自动前置；板块接口无 `totalNetInflow`）。传个股字段名时脚本会自动加 `sector` 前缀。
- 字段英文名按内置映射转中文；金额类数值保留两位小数。
- 个股输出把 `证券代码`、`日期` 规范为 `security_code`、`date`；板块输出把 `板块ID`、`日期` 规范为 `sector_id`、`date`（写出 CSV 前会去掉空的名称列）。

`--securities`、`--sectors`、`--all-market` **三者互斥，须任选其一**。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-sd` / `--start-date` | 否 | 开始日期 `yyyy-MM-dd`。非全市场不传时由接口默认（`endDate` 往前一年）。**`--all-market` 且与 `-ed` 均未指定时，默认当天并向前回退取数。** |
| `-ed` / `--end-date` | 否 | 结束日期 `yyyy-MM-dd`。非全市场不传时由接口取最新已入库交易日。 |
| `--securities` | 否* | 逗号分隔的证券名称/代码/拼音；亦可传 `.csv` 路径（须存在且后缀为 `.csv`，读 `security_code` / `code` / `代码` / `security_abbr` 列）。与 `--sectors` / `--all-market` **互斥**。 |
| `--sectors` | 否* | 板块 ID 或名称，逗号分隔（如 `1000001065` 或 `半导体`）。名称须唯一高分匹配，否则返回候选。与 `--securities` / `--all-market` **互斥**。 |
| `--all-market` | 否 | 传入 `securityList=["aShares"]` 查询全市场 A 股。未指定 `-sd/-ed` 时默认查**当天**，无数据则逐日向前回退（最多 **15** 天）。 |
| `--limit` | 否 | 单次请求最大返回行数，默认 `5000`，上限 `10000`。 |
| `--field-list` | 否 | 指定字段**英文名或中文名**，逗号分隔；不传则默认返回全部净流入字段。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

\* 须在 `--securities`、`--sectors`、`--all-market` 三者中任选其一。

## 字段说明

### 个股（fund-flow/daily）

| 分类 | 可选字段 |
|------|----------|
| 基础标识（默认返回） | `securityCode`、`tradeDate` |
| 小单 | `smallInflow`、`smallOutflow`、`smallNetInflow`、`smallInflowRatio`、`smallOutflowRatio` |
| 中单 | `mediumInflow`、`mediumOutflow`、`mediumNetInflow`、`mediumInflowRatio`、`mediumOutflowRatio` |
| 大单 | `largeInflow`、`largeOutflow`、`largeNetInflow`、`largeInflowRatio`、`largeOutflowRatio` |
| 特大单 | `xlargeInflow`、`xlargeOutflow`、`xlargeNetInflow`、`xlargeInflowRatio`、`xlargeOutflowRatio` |
| 汇总与主力 | `totalInflow`、`totalOutflow`、`totalNetInflow`、`mainInflow`、`mainOutflow`、`mainNetInflow`、`mainInflowRatio`、`mainOutflowRatio` |

不传 `--field-list` 时，默认返回全部**净流入**字段。主力资金 = 大单 + 特大单。

### 板块（fund-flow/sector-daily）

| 分类 | 可选字段 |
|------|----------|
| 基础标识（默认返回） | `sectorId`、`tradeDate` |
| 小单 | `sectorSmallInflow`、`sectorSmallOutflow`、`sectorSmallNetInflow` |
| 中单 | `sectorMediumInflow`、`sectorMediumOutflow`、`sectorMediumNetInflow` |
| 大单 | `sectorLargeInflow`、`sectorLargeOutflow`、`sectorLargeNetInflow` |
| 特大单 | `sectorXlargeInflow`、`sectorXlargeOutflow`、`sectorXlargeNetInflow` |
| 汇总与主力 | `sectorMainInflow`、`sectorMainOutflow`、`sectorMainNetInflow`、`sectorTotalInflow`、`sectorTotalOutflow` |

板块查询按板块数量、成分股数量、日期跨度与所选指标动态计算；计算量超限时请缩短日期区间、减少板块数或缩小 `fieldList`，不要仅调小 `limit`。

## 约束与说明

- 个股仅支持 **A 股**；港股、美股、指数等会被跳过并给出 `[WARNING]` 提示。
- 全市场查询务必配合日期或依赖默认「当天 + 向前回退」逻辑；指定日期区间时请控制 `limit`，必要时分批拉取。
- 板块 ID 可通过 `block_constituents` / 板块检索接口按名称获得；历史日期采用该交易日当日成分股口径。

## 调用示例

**默认净流入字段（个股）：**

```bash
python3 scripts/fund_flow.py --securities 贵州茅台
```

```bash
python3 scripts/fund_flow.py --securities 600519.SH,000001.SZ -sd 2024-05-01 -ed 2024-05-20
```

**指定字段（含流入流出）：**

```bash
python3 scripts/fund_flow.py --securities 比亚迪 --field-list mainNetInflow,smallInflow,smallOutflow,largeInflow,largeOutflow
```

**全市场（默认当天，无数据自动回退）：**

```bash
python3 scripts/fund_flow.py --all-market --limit 10
```

**全市场单日主力净流入：**

```bash
python3 scripts/fund_flow.py --all-market -sd 2024-05-20 -ed 2024-05-20 --field-list mainNetInflow --limit 8000
```

**板块资金流向：**

```bash
python3 scripts/fund_flow.py --sectors 1000001065,1000000125 -sd 2024-05-01 -ed 2024-05-20
```

```bash
python3 scripts/fund_flow.py --sectors 半导体 -sd 2024-05-20 -ed 2024-05-20 --field-list sectorMainNetInflow
```

**批量证券文件：**

```bash
python3 scripts/fund_flow.py --securities ./codes.csv -sd 2024-01-01 -ed 2024-12-31
```

## 返回说明

- **个股成功**：在 `workspace/gangtise/fund_flow/` 下生成 **`fund_flow_daily_*.csv`**。
- **板块成功**：同目录生成 **`fund_flow_sector_*.csv`**，含 `sector_id`、`date` 及所选字段（有名称映射时含 `sector_name`）。
- **失败**：如授权失败、无数据、参数错误、非 A 股标的全部被跳过、板块名称无法唯一匹配等。

## 返回数据示例（CSV 列）

个股典型列：`security_code`、`date`、`小单净流入金额（单位：元）`、…、`主力净流入（单位：元）` 等。

板块典型列：`sector_id`、`date`、`板块小单净流入金额（单位：元）`、…、`板块主力净流入（单位：元）` 等（以实际 `--field-list` 为准）。
