# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-file/references/report.md
# Regenerate: python3 scripts/generate.py
# 研究报告调用指导

## 简介

按关键词、证券、日期、机构、行业、来源类型、荣誉类型等条件检索研究报告，返回文件 ID、标题、摘要等元数据。主脚本：`scripts/report.py`。行业、机构提供枚举值接口（`scripts/get_industries.py`、`scripts/get_institutions.py`）；其余参数**无枚举值接口**，由后端**智能匹配**用户传入的文本。

## 主脚本：执行检索

| 参数 | 必填 | 说明 |
|------|------|------|
| `-k` / `--keyword` | 否 | 检索关键词，可为空。 |
| `-sd` / `--start-date` | 否 | 开始日期，如 `2026-01-01`。 |
| `-ed` / `--end-date` | 否 | 结束日期，如 `2026-12-31`。 |
| `-l` / `--limit` | 否 | 返回数量上限，默认由系统配置。 |
| `--securities` | 否 | 证券列表，逗号分隔；可为证券名称、代码或拼音首字母。 |
| `--institutions` | 否 | 机构名称，逗号分隔；可选值见枚举脚本。 |
| `--industries` | 否 | 行业名称，逗号分隔；可选值见枚举脚本。 |
| `--source-types` | 否 | 来源类型，逗号分隔；可选值：`研报`、`公众号`。 |
| `--category-list` | 否 | 研报类别，逗号分隔。英文 code 或中文均可，如 `industry,company` 或 `行业研究,公司研究`（完整列表见 `report.py --help`）。 |
| `--llm-tag-list` | 否 | 语义标签，逗号分隔。英文：`inDepth`/`earningsReview`/`industryStrategy`；或中文：`深度报告`/`业绩点评`/`行业策略`。 |
| `--search-type` | 否 | 搜索类型：`1` 标题搜索（默认），`2` 全文搜索。标题无结果时会自动尝试全文。 |
| `--rank-type` | 否 | 排序方式：`1` 综合排序（默认），`2` 时间倒序。 |
| `-d` / `--download` | 否 | 是否在检索后自动下载所有对应研究报告文件，默认不下载。 |
| `-od` / `--output-dir` | 否 | 结果与下载文件保存目录路径，建议使用绝对路径。默认保存在 gangtise 工作目录下的 `report` 目录。 |
| `-dt` / `--download-types` | 否 | 下载文件类型，逗号分隔。可选：pdf, markdown。 |

**无枚举值接口的参数**（如 `keyword`、`securities` 等）：直接传入用户意图相关文本，后端会**智能匹配**，无需先查枚举。

## 枚举值脚本：获取参数可选值

- **行业**：执行 `scripts/get_industries.py` 获取行业列表。
- **机构**：执行 `scripts/get_institutions.py` 获取机构列表。

```bash
python3 scripts/get_industries.py
python3 scripts/get_institutions.py
```

## 调用示例

**按关键词 + 时间 + 数量：**
```bash
python3 scripts/report.py -k 比亚迪 -sd 2026-01-01 -ed 2026-12-31 -l 20
```

**全文检索（在正文中匹配关键词）：**
```bash
python3 scripts/report.py -k 固态电池 --search-type 2 -sd 2026-01-01 -ed 2026-12-31 -l 20
```

**按关键词 + 来源 + 行业：**
```bash
python3 scripts/report.py -k 新能源 --source-types 研报 --industries 电力设备
```

**按证券 + 关键词（代码或名称）：**
```bash
python3 scripts/report.py -k 业绩 --securities 宁德时代,比亚迪
```

**按类别 + 语义标签（支持中文）：**
```bash
python3 scripts/report.py -k 锂电 --category-list 行业研究,公司研究 --llm-tag-list 深度报告,业绩点评 -l 20
```

**检索并自动下载研究报告：**
```bash
python3 scripts/report.py -k 新能源 --industries 电力设备 -sd 2026-01-01 -ed 2026-12-31 -d true
```

## 返回说明

- **成功**：返回文件列表（含 file_id、标题、摘要等），可通过`python3 scripts/get_file.py --file-id <file_id> --file-type "研究报告"`下载。
- **失败**：返回错误信息。
