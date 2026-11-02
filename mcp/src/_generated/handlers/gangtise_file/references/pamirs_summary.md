# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-file/references/pamirs_summary.md
# Regenerate: python3 scripts/generate.py
# 帕米尔专家纪要调用指导

## 简介

检索 **帕米尔（Pamirs）** 牵头机构下的专家纪要列表，返回纪要 ID、标题、摘要、关联证券/研究方向/主题概念等元数据；可选下载原始文件或 HTML。主脚本：`scripts/pamirs_summary.py`。

权限要求：仅限已购买专家纪要数据库的用户调用。本接口不限制历史数据访问范围。

行业/研究方向可通过 `scripts/get_industries.py` 获取枚举；证券、关键词等**无枚举值接口**由后端**智能匹配**。

与通用会议纪要（`summary.py`）的区别：本脚本专用于帕米尔机构；筛选维度不含机构/来源类型/参会人角色；纪要类别仅支持公司分析、行业分析。

## 主脚本：执行检索

| 参数 | 必填 | 说明 |
|------|------|------|
| `-k` / `--keyword` | 否 | 检索关键词；可为空。 |
| `-sd` / `--start-date` | 否 | 开始日期，格式 `YYYY-MM-DD`。 |
| `-ed` / `--end-date` | 否 | 结束日期，格式 `YYYY-MM-DD`。 |
| `-l` / `--limit` | 否 | 返回数量上限；不传时默认见 `FILE_DEFAULT_LIMIT["pamirs_summary"]`，开启 `-d` 时默认 `10`。 |
| `--securities` | 否 | 证券列表，逗号分隔；可为证券名称、代码或拼音首字母。 |
| `--industries` | 否 | 研究方向/行业，逗号分隔；可选值见枚举脚本。 |
| `--category-list` | 否 | 纪要类别，逗号分隔。可选值：`companyAnalysis`、`industryAnalysis`（也支持中文：`公司分析`、`行业分析`）。 |
| `--market-list` | 否 | 市场类别，逗号分隔。可选值：`aShares`、`hkStocks`、`usChinaConcept`、`usStocks`（也支持中文：`A股`、`港股`、`美股中概`、`美股`）。 |
| `--search-type` | 否 | 搜索类型：`1` 标题搜索（默认），`2` 全文搜索。标题无结果时会自动尝试全文。 |
| `--rank-type` | 否 | 排序方式：`1` 综合排序（默认），`2` 时间倒序。 |
| `-d` / `--download` | 否 | 是否下载文件。 |
| `-od` / `--output-dir` | 否 | 结果与下载文件保存目录路径。 |
| `-dt` / `--download-types` | 否 | 下载文件类型，逗号分隔。可选：`original`（原始文件）、`html`。 |

## 枚举值脚本

```bash
python3 scripts/get_industries.py
```

## 调用示例

**按关键词 + 时间倒序：**
```bash
python3 scripts/pamirs_summary.py -k AI智能体 --rank-type 2 -l 20
```

**按证券 + 纪要类别：**
```bash
python3 scripts/pamirs_summary.py --securities 科大讯飞 --category-list companyAnalysis,industryAnalysis
```

**按时间范围 + 市场 + 下载 HTML：**
```bash
python3 scripts/pamirs_summary.py -k 机器人 -sd 2024-01-01 -ed 2024-12-31 --market-list aShares -d -dt html
```

## 返回说明

- **成功**：返回纪要列表（含类型ID、标题、摘要等），可通过 `python3 scripts/get_file.py --file-id <summaryId> --file-type "帕米尔专家纪要"` 下载；`-dt` 可选 `original` / `html`。
- **失败**：返回错误信息（含权限错误）。
