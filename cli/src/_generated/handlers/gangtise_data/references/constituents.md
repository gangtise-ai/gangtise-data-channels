# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-data/references/constituents.md
# Regenerate: python3 scripts/generate.py
# 成分股 API（板块成分股 + 指数成分股权重）

## 简介

脚本 **`scripts/constituents.py`**（旧入口 `block_constituents.py` 仍可用）统一查询成分股：

| 模式 (`-m`) | 接口 | 说明 |
|-------------|------|------|
| `sector`（默认） | `sectors/search` + `sectors/constituents` | 行业/概念/指数等**板块树**成分股名单 |
| `index` | `index/constituent-weight` | 主流宽基**指数**成分股及权重（%），按交易日全量返回 |

输出均为 **CSV**。

## 参数

| 参数 | 模式 | 说明 |
|------|------|------|
| `-m` / `--mode` | 共用 | `sector` \| `index`，默认 `sector`。 |
| `-k` / `--keyword` | sector | 板块搜索关键词（名称/拼音/首字母）。 |
| `-s` / `--sector-id` | sector | 板块 ID，已知时可跳过搜索。 |
| `-t` / `--top` | sector | 关键词搜索条数上限，默认/最大 **10**。 |
| `--indexes` | index | 指数代码或名称，逗号分隔（如 `000300.SH,沪深300`）。 |
| `-td` / `--trade-date` | index | 交易日，严格 `yyyy-MM-dd`（必填）。 |
| `-od` / `--output-dir` | 共用 | 结果保存目录。 |

sector 模式须提供 `-k` 或 `-s` 之一；index 模式须提供 `--indexes` 与 `-td`。

## 板块模式解析逻辑

使用 `-k` 时调用 `sectors/search`：

- **唯一高置信候选**：自动取 sectorId 并拉成分股。
- **多个候选**：终端打印候选列表，改用 `-s` 指定。
- **无候选**：返回错误。

## 指数模式说明

- 覆盖沪深300、中证500/800/1000、中证A500、上证50、科创50、创业板指等主流宽基指数。
- 按 `tradeDate` **单日**精确查询，不分页、不设返回条数上限。
- `weight` 单位为 %，同指数同日权重合计约 100（允许微小舍入偏差）。
- 指数名称会经证券解析转为代码；已是 `000300.SH` 形式则直通。

## 调用示例

```bash
# 板块：按名称搜索并自动取成分股
python3 scripts/constituents.py -k 机器人
```

```bash
# 板块：已知 sectorId
python3 scripts/constituents.py -s 121000130
```

```bash
# 指数：沪深300 成分股权重
python3 scripts/constituents.py -m index --indexes 000300.SH -td 2026-06-30
```

```bash
# 指数：名称解析
python3 scripts/constituents.py -m index --indexes 沪深300,中证500 -td 2026-06-30
```

## 返回说明

- **sector 成功**：`workspace/gangtise/constituents/constituents_sector_*.csv`
- **index 成功**：`constituents_index_*.csv`
- **sector 多候选**：仅打印候选，不落盘

### sector CSV 列

| sector_id | sector_name | hierarchy | security_code | security_name |
|-----------|-------------|-----------|---------------|---------------|

### index CSV 列

| index_code | index_name | trade_date | security_code | security_name | weight |
|------------|------------|------------|---------------|---------------|--------|
