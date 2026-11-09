# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-file/references/foreign_report.md
# Regenerate: python3 scripts/generate.py
# 外资研报调用指导

## 简介

按关键词、证券、日期、券商、行业、研报类别、区域、语义标签、评级/评级变动、页数范围等条件检索**外资研报列表**，返回研报 ID、标题、摘要等元数据。主脚本：`scripts/foreign_report.py`。行业、券商、区域提供枚举值接口（`scripts/get_industries.py`、`scripts/get_institutions.py`、`scripts/get_regions.py`）；其余参数**无枚举值接口**时由后端**智能匹配**用户传入的文本。境外证券常用代码格式如 `UBER.N`（见平台「境外股票代码格式规范」）。

## 主脚本：执行检索

| 参数 | 必填 | 说明 |
|------|------|------|
| `-k` / `--keyword` | 否 | 检索关键词，可为空。 |
| `-sd` / `--start-date` | 否 | 开始日期，如 `2026-01-01`。 |
| `-ed` / `--end-date` | 否 | 结束日期，如 `2026-12-31`。 |
| `-l` / `--limit` | 否 | 返回数量上限，默认由系统配置（单页最大 50 条，脚本内分页拉取）。 |
| `--securities` | 否 | 证券列表，逗号分隔；可为证券名称、代码或拼音首字母。 |
| `--institutions` | 否 | 券商名称，逗号分隔；可选值见枚举脚本。 |
| `--industries` | 否 | 行业名称，逗号分隔；可选值见枚举脚本。 |
| `--region-list` | 否 | 区域名称，逗号分隔；可选值见枚举脚本。 |
| `--category-list` | 否 | 研报类别，逗号分隔。英文：`macro`/`strategy`/`industry`/`company`/`bond`/`quant`/`morningNotes`/`fund`/`forex`/`futures`/`options`/`warrants`/`market`/`wealthManagement`/`other`；或中文：`宏观研究`/`策略研究`/`行业研究`/`公司研究`/`债券研究`/`金融工程`/`晨会研究`/`基金研究`/`外汇研究`/`期货研究`/`期权研究`/`权证研究`/`市场研究`/`理财研究`/`其他报告`。 |
| `--llm-tag-list` | 否 | 语义标签，逗号分隔。英文：`inDepth`/`earningsReview`/`industryStrategy`；或中文：`深度报告`/`业绩点评`/`行业策略`。 |
| `--rating-list` | 否 | 评级：`buy` / `overweight` / `neutral` / `underweight` / `sell`。 |
| `--rating-change-list` | 否 | 评级变动：`upgrade` / `maintain` / `downgrade` / `initiate`。 |
| `--min-report-pages` | 否 | 研报最小页数。 |
| `--max-report-pages` | 否 | 研报最大页数。 |
| `--search-type` | 否 | `1` 标题搜索（默认），`2` 全文搜索。标题无结果时会自动尝试全文。 |
| `--rank-type` | 否 | `1` 综合排序（默认），`2` 时间倒序。 |
| `-d` / `--download` | 否 | 是否在检索后自动下载对应外资研报文件，默认不下载。 |
| `-od` / `--output-dir` | 否 | 结果与下载文件保存目录路径，建议绝对路径；默认在 gangtise 工作目录下 `foreign_report`。 |
| `-dt` / `--download-types` | 否 | 下载类型，逗号分隔：`pdf`、`markdown`。 |

## 枚举值脚本

- **行业**：`python3 scripts/get_industries.py`
- **券商**：`python3 scripts/get_institutions.py`
- **区域**：`python3 scripts/get_regions.py`

## 调用示例

**关键词 + 时间 + 数量：**

```bash
python3 scripts/foreign_report.py -k 自动驾驶 -sd 2026-01-01 -ed 2026-05-31 -l 20
```

**全文检索：**

```bash
python3 scripts/foreign_report.py -k 自动驾驶 --search-type 2 -sd 2026-01-01 -ed 2026-05-31 -l 20
```

**类别 + 券商 + 语义标签：**

```bash
python3 scripts/foreign_report.py -k 新能源 --category-list industry,company --institutions 摩根大通 --llm-tag-list inDepth -l 15
```

**境外证券代码：**

```bash
python3 scripts/foreign_report.py --securities UBER.N -l 10
```

**检索并下载：**

```bash
python3 scripts/foreign_report.py -k 半导体 -sd 2026-01-01 -ed 2026-05-31 -d true
```

## 返回与下载

- **成功**：返回列表字段含 `类型` 为「外资研报」、`类型ID` 为 `reportId` 等；下载完整文件使用：

```bash
python3 scripts/get_file.py --file-id <reportId> --file-type "外资研报"
```

- **失败**：返回错误信息；试用账号若超出一个月范围可能被接口拒绝。
