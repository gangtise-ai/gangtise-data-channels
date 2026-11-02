# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-data/references/industry_indicator.md
# Regenerate: python3 scripts/generate.py
# 行业指标 API（Open API · EDB）

## 简介

通过 Gangtise Open API 检索数据浏览器平台的**行业/产业指标**（如产量、销量、价格、景气度等），并拉取标准化时序数据。脚本 **`scripts/industry_indicator.py`**。

底层接口：

- **指标检索** `EDB/search`：按关键词模糊匹配，返回指标 ID 及名称、来源、频率、单位等元信息。
- **时序取数** `EDB/getData`：按指标 ID 批量获取时间序列（单次请求最多 **10** 个 ID；脚本在 `get` 模式下会**自动分批**合并）。

覆盖宏观、行业、大宗商品与产品等多类时序数据；**比亚迪分品牌销量等产品类数据仅存在于本接口**（EDE 公司指标不含此类产品销量）。

## 覆盖范围与检索技巧

| 类型 | 说明 |
|------|------|
| **宏观指标** | 各国 GDP、CPI、PPI 等。**中国相关指标在名称中通常不含「中国」**——若宏观指标名未提及国家，一般即为中国宏观指标。 |
| **行业指标** | 各行各业，如原材料价格、航运指数等。 |
| **大宗商品** | 黄金现货价，石油期权、期货等衍生品的结算价、收盘价等。检索时**避免单独使用「价格」**，应使用「现货价」「结算价」「收盘价」等更具体的关键词。 |
| **产品指标** | 某具体产品的销量、产量等，如「新能源汽车销量」「空调销量」。**不支持**按公司拆分到各子品牌/车型的汇总查询（如「比亚迪分品牌销量」）；应先用知识库确认品牌/车型名称，再分别检索，例如「比亚迪 元plus 零售量」「比亚迪 海鸥 零售量」。 |

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-m` / `--mode` | 否 | `search`（默认）或 `get`；提供 `--indicators` 时**自动为 get**。 |
| `-k` / `--keyword` | search* | 检索关键词（如「空调」「新能源汽车销量」）。 |
| `--indicators` | get* | 指标 ID 或名称，逗号分隔。仅含字母数字与逗号时直接取数；否则 search，**唯一完全匹配**则自动拉时序，否则返回候选。 |
| `--indicators-file` | get* | CSV 须含 **`indicator_id`** 或 **`indicatorId`** 列；通常由 search 结果过滤后使用。 |
| `-sd` / `--start-date` | 否 | 时序开始日期 `yyyy-MM-dd`（get），默认约为结束日往前一年。 |
| `-ed` / `--end-date` | 否 | 时序结束日期 `yyyy-MM-dd`（get），默认今天。 |
| `-l` / `--limit` | 否 | search：检索条数上限，默认 **10**，最大 **200**。get：参与取数的指标数量上限（可大于 10，自动分批）。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

\* 各模式须满足对应必填项。

## 模式说明

**search**：`-m search` 或 `-k 关键词`（无 `--indicators` 时）。结果保存为 `industry_indicator_search_*.csv`，并提示可通过 `--indicators-file` 过滤后再取数。

**get**：`-m get` 或 `--indicators` / `--indicators-file`。`--indicators` 为非纯 ID 形式时先 search，**唯一完全匹配**时自动 get。

## 约束与说明

- `search` 模式不使用 `-sd` / `-ed`（仅检索元信息，不拉时序）。
- `get` 模式无检索元信息时，CSV 列名多为**指标 ID**；可先 search 再 `--indicators-file` 取数。
- 时序结果按**频率**拆分为多个 CSV（如 `industry_indicator_weekly_*.csv`）；频率为中文时映射为 `daily` / `weekly` / `monthly` 等模块名。
- 检索关键词宜**具体**（见上文「覆盖范围与检索技巧」）；宏观默认中国、大宗商品避免泛用「价格」、产品销量不支持公司内分品牌汇总。

## 调用示例

```bash
# 检索指标元信息
python3 scripts/industry_indicator.py -k 空调 -l 50
```

```bash
# 非 ID 关键词：search，唯一完全匹配时自动取数
python3 scripts/industry_indicator.py --indicators 新能源汽车销量 -l 20
```

```bash
# 按已知指标 ID 取数
python3 scripts/industry_indicator.py --indicators S14001618,S14001620 -sd 2010-01-01 -ed 2015-01-01
```

```bash
# 从 search 结果 CSV 过滤后取数
python3 scripts/industry_indicator.py --indicators-file ./industry_indicator_search_1.csv -l 30
```

## 返回说明

- **成功（search）**：`workspace/gangtise/industry_indicator/industry_indicator_search_*.csv`。
- **成功（get）**：同目录下按频率生成 **`industry_indicator_{frequency}_*.csv`**，首列为 `date`。
- **失败**：授权失败、无命中、ID 无效、时序无数据等。
