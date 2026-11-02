# 资金流向数据调用指导（Open API · fund-flow/daily）

## 简介

通过 Gangtise Open API 获取 **A 股个股日资金流向**历史数据，覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）。脚本：`scripts/fund_flow.py`。

- 仅提供**历史**资金流向，不提供实时数据；交易日当日数据一般在 **16:30** 左右入库后方可查询。
- 试用账号可查询当前时间前溯 **3 年**历史数据；正式账号权限依购买服务等级调整。
- 默认 `fieldList` 为全部**净流入**相关字段：`smallNetInflow`、`mediumNetInflow`、`largeNetInflow`、`xlargeNetInflow`、`totalNetInflow`、`mainNetInflow`（`securityCode`、`tradeDate` 由接口自动前置返回）。
- 字段英文名按内置映射转中文；金额类数值保留两位小数。
- 输出会把 `证券代码`、`日期` 规范为 `security_code`、`date` 并放在前面（写出 CSV 前会去掉 `证券简称` 列）。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-sd` / `--start-date` | 否 | 开始日期 `yyyy-MM-dd`。非全市场不传时由接口默认（`endDate` 往前一年）。**`--all-market` 且与 `-ed` 均未指定时，默认当天并向前回退取数。** |
| `-ed` / `--end-date` | 否 | 结束日期 `yyyy-MM-dd`。非全市场不传时由接口取最新已入库交易日。 |
| `--securities` | 否* | 逗号分隔的证券名称/代码/拼音；亦可传 `.csv` 路径（须存在且后缀为 `.csv`，读 `security_code` / `code` / `代码` / `security_abbr` 列）。与 `--all-market` **二选一**。 |
| `--all-market` | 否 | 传入 `securityList=["aShares"]` 查询全市场 A 股。未指定 `-sd/-ed` 时默认查**当天**，无数据则逐日向前回退（最多 **15** 天）。 |
| `--limit` | 否 | 单次请求最大返回行数，默认 `5000`，上限 `10000`。 |
| `--field-list` | 否 | 指定字段**英文名或中文名**，逗号分隔；不传则默认返回全部净流入字段。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

\* 指定证券时须提供 `--securities`；全市场时使用 `--all-market` 且不要同时传证券列表。

## 字段说明（fieldList 可选字段一览）

| 分类 | 可选字段 |
|------|----------|
| 基础标识（默认返回） | `securityCode`、`tradeDate` |
| 小单 | `smallInflow`、`smallOutflow`、`smallNetInflow`、`smallInflowRatio`、`smallOutflowRatio` |
| 中单 | `mediumInflow`、`mediumOutflow`、`mediumNetInflow`、`mediumInflowRatio`、`mediumOutflowRatio` |
| 大单 | `largeInflow`、`largeOutflow`、`largeNetInflow`、`largeInflowRatio`、`largeOutflowRatio` |
| 特大单 | `xlargeInflow`、`xlargeOutflow`、`xlargeNetInflow`、`xlargeInflowRatio`、`xlargeOutflowRatio` |
| 汇总与主力 | `totalInflow`、`totalOutflow`、`totalNetInflow`、`mainInflow`、`mainOutflow`、`mainNetInflow`、`mainInflowRatio`、`mainOutflowRatio` |

不传 `--field-list` 时，默认返回全部**净流入**字段：`smallNetInflow`、`mediumNetInflow`、`largeNetInflow`、`xlargeNetInflow`、`totalNetInflow`、`mainNetInflow`（`securityCode`、`tradeDate` 由接口自动前置返回）。主力资金 = 大单 + 特大单：`mainNetInflow = (largeInflow + xlargeInflow) - (largeOutflow + xlargeOutflow)`。

也可通过 `--field-list` 指定上表任意字段，逗号分隔，例如 `mainNetInflow,smallInflow,largeInflowRatio`。

## 约束与说明

- 仅支持 **A 股**；港股、美股、指数等会被跳过并给出 `[WARNING]` 提示。
- 全市场查询务必配合日期或依赖默认「当天 + 向前回退」逻辑；指定日期区间时请控制 `limit`，必要时分批拉取。

## 调用示例

**默认净流入字段（小/中/大/特大/总/主力）：**

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

**批量证券文件：**

```bash
python3 scripts/fund_flow.py --securities ./codes.csv -sd 2024-01-01 -ed 2024-12-31
```

## 返回说明

- **成功**：在 `workspace/gangtise/fund_flow/` 下生成 **`fund_flow_daily_*.csv`**，返回文案含路径与样例。
- **失败**：如授权失败、无数据、参数错误、非 A 股标的全部被跳过等。

## 返回数据示例（CSV 列）

典型列为：`security_code`、`date`、`小单净流入金额（单位：元）`、`中单净流入金额（单位：元）`、`大单净流入金额（单位：元）`、`特大单净流入金额（单位：元）`、`总净流入金额（单位：元）`、`主力净流入（单位：元）` 等（以实际 `--field-list` 为准）。
