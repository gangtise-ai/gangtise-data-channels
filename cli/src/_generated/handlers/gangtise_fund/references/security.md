# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/references/security.md
# Regenerate: python3 scripts/generate.py
# 基金检索（Open API · securities/search）

## 简介

把简称、拼音或代码搜成 gtsCode。各数据脚本已经内置同一套解析；只有结果对不上、或需要看候选列表时，才单独跑本脚本。搜索免费。脚本：`scripts/security.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--keyword` / `-k` | 是 | 基金简称、代码、拼音或英文名 |
| `--category` / `-c` | 否 | 逗号分隔：`fund`、`stock`、`dr`、`index`、`bond`。默认 `fund`。`all` 不限分类 |
| `--top` | 否 | 向接口请求的条数，1–10，默认 10 |
| `--limit` / `-l` | 否 | 实际输出条数，默认 10 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 字段说明

检索结果列名保持英文，便于再传给其他脚本的 `--securities`。

| 字段 | 说明 |
|------|------|
| `security_code` | gtsCode |
| `security_abbr` | 名称 |
| `category` | `fund` / `stock` / `dr` / `index` / `bond` |
| `match_score` | 0–1，越高越接近 |
| `match_type` | `code` 代码、`abbr` 简称、`pinyin` 拼音、`prev` 曾用名、`engName` 英文名 |

## 约束与说明

- 场外 `.OF` 基金的简称和六位数字经常搜不到。数据脚本对 `.OF` 代码会直接采用，不依赖本次检索有命中。
- 场内基金可以用简称。`沪深300ETF` 这类不带公司名的说法会命中多只。数据脚本只在简称或代码完全一致且只有一条、或匹配度高于 0.6 且只有一只时自动采用；多只结果全部列出，不因某一只匹配度为 1 自动采用。需要浏览检索结果时用本脚本。
- 接口最多返回 10 条，不是全市场列表。

## 调用示例

```bash
python3 scripts/security.py -k 沪深300ETF -l 10
python3 scripts/security.py -k 510300 -c fund
python3 scripts/security.py -k 银行 -c fund,index
```

## 返回说明

- **成功**：在 `workspace/gangtise/security/` 下生成 `security_*.csv`。
- **无数据**：提示未找到相关证券。场外基金改传完整 `.OF` 代码给数据脚本。
