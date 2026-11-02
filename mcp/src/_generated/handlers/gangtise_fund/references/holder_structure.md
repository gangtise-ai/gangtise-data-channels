# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/references/holder_structure.md
# Regenerate: python3 scripts/generate.py
# 基金持有人结构（Open API · fund/holder-structure）

## 简介

按报告期返回持有人户数、户均份额，以及机构、个人、员工持有份额和占比。一只基金一个报告期一行。试用账号前溯 3 年、正式账号前溯 5 年。脚本：`scripts/holder_structure.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | 基金代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv`。场外基金请直接传 `.OF` |
| `-sd` / `--start-date` | 否 | 报告期起。不传不限制 |
| `-ed` / `--end-date` | 否 | 报告期止。不传不限制 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

持有人结构多在半年报、年报披露，季度末常常没有行。

## 字段说明

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `reportDate` | 报告期 | `yyyy-MM-dd` |
| `holderCount` | 持有人户数(户) | |
| `sharesPerHolder` | 户均份额(份) | |
| `sharesInstitution` | 机构持有份额(份) | |
| `pctInstitution` | 机构持有占比(%) | 占基金总份额 |
| `sharesIndividual` | 个人持有份额(份) | |
| `pctIndividual` | 个人持有占比(%) | |
| `sharesEmployee` | 员工持有份额(份) | |
| `pctEmployee` | 员工持有占比(%) | |

## 约束与说明

- 单次最多 10000 行。
- 份额单位是**份**，不是万份。

## 调用示例

```bash
python3 scripts/holder_structure.py --securities 005827.OF -sd 2025-12-31 -ed 2026-06-30
```

## 返回说明

- **成功**：在 `workspace/gangtise/holder_structure/` 下生成 `holder_structure_*.csv`。
- **无数据**：提示未找到持有人结构。
