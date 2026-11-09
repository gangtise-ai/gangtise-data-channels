# 公司指标调用指导（Open API · EDE）

## 简介

通过 Gangtise Open API 检索与拉取 **公司指标**（EDE，覆盖 A 股 / 港股 / 美股、存托凭证、债券与基金）。脚本：`scripts/company_indicator.py`。

- **search**：调用 `EDE/search` 检索指标元信息，结果保存为 CSV（含 `indicator_params` 默认值）。
- **get**：按指标与证券拉取数据；日期跨度较长时走 **时序**（`time-series`），否则走 **截面**（`cross-section`）。

相较于其他 data 脚本，适合拉取**单只或多只股票（A/港/美）**的**单个指标或跨类别组合**（行情、财报、财务比率、分红、盈利预测、公司/证券属性等）；**产品销量类数据**（如分品牌零售量）请使用 [行业指标（EDB）](./industry_indicator.md)。**券商一致预期盈利预测**（`earning_forecast`）与本接口内 **预测指标**为不同数据源，勿混淆。

## 覆盖范围与检索技巧

| 类型 | 说明 |
|------|------|
| **行情指标** | 日收盘价、成交量、涨跌幅、换手率、市值、成交额等。日频时序**不含当天实时**；结束日期通常取最近一个已收盘交易日。 |
| **财务报表** | 利润表、资产负债表、现金流量表各科目，含 TTM/单季度/同比环比。取截面时 `-sd` / `-ed` 一般设为对应**报告期季度末**（见下文「日期与数据范围」）。 |
| **财务比率** | 估值倍数（PE/PB/PS/PCF/PEG）、盈利能力（ROE/ROA/ROIC）、营运周转与天数、现金流质量等。 |
| **分红指标** | 现金分红、股利支付率、股息率等。 |
| **盈利预测** | 预测营收/归母净利润及同比、预测 PE/PEG 等。与 `earning_forecast.py` 的券商一致预期为**不同接口**。 |
| **公司/证券属性** | 主营业务、注册地址、上市板块、上市日期、证券所属概念、总股本/流通股本等。 |

- **检索关键词宜具体**：如「收盘价」「营业收入」「所属概念」，避免过于笼统的表述。
- **跨类别组合**：可在一次 get 请求中同时拉取行情、财报与属性类指标（如 `qte_close` + `is_op_rev` + `scr_concept`），注意各指标适用的日期与参数（如行情复权 `adjustType`）。
- **产品销量、宏观/行业时序**：不在 EDE 覆盖内，请用 [行业指标（EDB）](./industry_indicator.md)。

## 日期与数据范围

| 场景 | 说明 |
|------|------|
| **财报类指标（截面）** | 按报告期取数时，日期一般对应各季度末：**一季度** `yyyy-03-31`、**二季度（中报）** `yyyy-06-30`、**三季度** `yyyy-09-30`、**四季度（年报）** `yyyy-12-31`。 |
| **日频指标（时序）** | 如收盘价、成交量等；**不包含当天实时数据**，结束日期通常取最近一个已收盘交易日。 |
| **证券范围** | 支持 **A 股、港股、美股及存托凭证**；指数/基金等会跳过。 |

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-m` / `--mode` | 否 | `search`（默认）或 `get`；提供 `--indicators` 时**自动为 get**。 |
| `-k` / `--keyword` | search* | 检索关键词（须为具体指标词，如「收盘价」「成交量」「所属概念」）。 |
| `--indicators` | get* | 指标编码或名称关键词，逗号分隔。仅含英文字母与逗号时视为编码；否则先检索，**唯一完全匹配**则自动拉取，否则返回候选 Markdown。 |
| `--indicators-file` | get* | CSV 含 `indicator_code`、`indicator_name`、`indicator_params`（JSON）列；通常由 search 结果编辑后使用。 |
| `--securities` | get* | 逗号分隔的证券名称/代码/拼音；亦可传 `.csv` 路径（须存在且后缀为 `.csv`，读 `security_code` / `code` / `代码` / `security_abbr` 列）。 |
| `-sd` / `--start-date` | 否 | get 模式开始日期 `yyyy-MM-dd`，默认近一年。 |
| `-ed` / `--end-date` | 否 | get 模式结束日期，默认今天。 |
| `-p` / `--params` | 否 | JSON 字典，见下文「参数 `-p`」；**币种 `currency` 会规范为大写**。 |

\* 各模式须满足对应必填项。

## 参数 `-p`

`-p` 传入 JSON 对象，分两类：

1. **全局参数**（根级键值）：作用于本次请求中**所有适用该参数的指标**。例如行情复权方式 `adjustType`、请求级 `scale`、`calendarType` 等。
2. **指标参数**（按指标编码嵌套）：仅作用于指定指标。键为指标编码（如 `qte_close`），值为该指标的参数字典。

**覆盖规则**：若某指标在嵌套中显式指定了与全局同名的参数，以嵌套值为准；其余指标仍使用全局值。

```bash
# 全局：全部指标使用后复权（adjustType=3）
-p '{"adjustType":"3"}'

# 全局 + 单指标覆盖：qte_close 不复权（1），其余指标仍用后复权（3）
-p '{"adjustType":"3","qte_close":{"adjustType":"1"}}'
```

**根级请求参数**（写入请求体顶层，非 `indicatorParamList`）：

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `scale` | 量纲 | `0` 个、`3` 千、`4` 万、`6` 百万、`8` 亿、`9` 十亿 |
| `calendarType` | 日期类型（时序）。不传时按请求指标自动返回日期序列：交易日指标为交易日，报告期指标为报告期，多类指标混合时为两者并集。需要固定日期类型时再显式传入 | `ND` 自然日、`TD` 交易日、`WD` 工作日、`RD` 报告期 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

指标专属参数（如 `adjustType`、`basePeriod`）请写在根级（全局）或对应指标编码下；具体以 search 结果中该指标的 **请求参数** 表为准。

> 脚本对中文键名/枚举值有容错映射，仅作冗余兜底，**文档与调用均建议使用英文编码**。

## 模式说明

**search**：`-m search` 或 `-k 关键词`（无 `--indicators` 时）。单独 `-m get` 而未提供 `--indicators` 时会报错提示缺参。

**get**：提供 `--indicators` / `--indicators-file`（可省略 `-m get`，自动进入拉取）；或显式 `-m get` 并同时提供指标与证券。

## search 行为

- 固定检索 **最多 5 条**。
- 若存在指标**名称或编码与关键词完全一致**的命中，仅返回这些完全匹配项；否则返回全部 5 条。
- 结果含 **使用限制**（`usageRestriction`）；参数表展示接口返回的全部参数（含 `sDate` / `tradeDate` / `reportDate` 等日期参数）；币种枚举/默认值为**大写**；不使用 `gtsCode`。
- 结果保存为 **`company_indicator_search_*.csv`**（列：`indicator_code`、`indicator_name`、`indicator_params`），并提示可通过 `--indicators-file` 过滤后再 get。

## --indicators 智能解析（自动 get）

- 提供 `--indicators` 时无需 `-m get`，自动进入拉取模式。
- 参数内容**仅由英文字母、数字与逗号**（`,`、`，`）组成时，直接作为指标编码使用，如 `qte_close,qte_vol`。
- 否则将各逗号分隔片段视为检索关键词：若某片段检索后**名称或编码完全匹配且唯一**，则解析为对应编码并继续；否则按 search 流程返回该片段的候选结果（Markdown），不拉取数据。

## get 行为

- 支持 **A 股、港股、美股、存托凭证、债券与基金**。
- **财报类指标**取截面时，`-sd` / `-ed` 通常设为对应**报告期季度末**（见上文「日期与数据范围」）。
- **日频行情类指标**取时序时，**不含当天实时数据**。
- 成功时仅保存时序/截面数据 CSV。参数模板（含默认 `indicator_params`）由 **search** 产出为 `company_indicator_search_*.csv`，可编辑后经 `--indicators-file` 再 get。
- 使用 `--indicators-file` 时会读取 `indicator_params` 列；若同时传入 `-p`，**以 `-p` 为准**覆盖文件中的同名参数；币种参数统一为大写。
- 请求体证券范围字段为 **`universe`**（原 `securityCodeList`）。
- 时序长度（日历天数）**大于** `min(指标数, universe 宽度)` → 使用 **时序接口**：
  - **单指标**：一次请求可传多证券与多板块 ID。
  - **多指标**：每次请求仅一个证券代码（脚本自动按证券拆分）；不得传板块 ID。
- 否则使用 **截面接口**（`date` 取 `-ed`；`universe` 可同时含证券与板块 ID）。
- 截面返回 `values` 为「行=证券、列=指标」矩阵（脚本兼容旧转置）；时序 `values` 结构不变。指标元数据优先读 `indicatorList`。
- 输出 CSV 列：`date`、`security_code`、`security_name`、`indicator_code`、`indicator_name`、`value`。

## 调用示例

**检索指标（Markdown 输出）：**

```bash
python3 scripts/company_indicator.py -m search -k 成交量
```

**检索证券所属概念等指标：**

```bash
python3 scripts/company_indicator.py -k 所属概念
python3 scripts/company_indicator.py --indicators scr_concept --securities 比亚迪 -sd 2026-07-07 -ed 2026-07-07
```

**按名称拉取（唯一匹配时自动 get，否则返回候选）：**

```bash
python3 scripts/company_indicator.py --indicators 成交量 --securities 600519.SH -sd 2026-05-18 -ed 2026-05-22
```

**财报类指标（截面，报告期取季度末）：**

```bash
python3 scripts/company_indicator.py --indicators 营业收入 --securities 贵州茅台 -sd 2026-03-31 -ed 2026-03-31
```

**多指标 × 单证券时序（全局参数 + 单指标覆盖；日频不含当日实时）：**

```bash
python3 scripts/company_indicator.py --indicators qte_high,qte_close \
  --securities 贵州茅台 \
  -sd 2026-07-07 -ed 2026-07-07 \
  -p '{"adjustType":"3","qte_close":{"adjustType":"2"}}'
```

**单指标 × 多证券时序：**

```bash
python3 scripts/company_indicator.py --indicators qte_close \
  --securities 贵州茅台,平安银行 \
  -sd 2026-05-18 -ed 2026-05-22
```

**截面（短区间）：**

```bash
python3 scripts/company_indicator.py --indicators qte_close,qte_vol \
  --securities 600519.SH,000001.SZ \
  -sd 2026-05-18 -ed 2026-05-18
```

## 返回说明

- **search**：终端输出检索摘要，并保存 `company_indicator_search_*.csv`。
- **get 成功**：`workspace/gangtise/company_indicator/company_indicator_*.csv`。
- **失败**：授权失败、无数据、参数错误、非 A 股全部被跳过等。
