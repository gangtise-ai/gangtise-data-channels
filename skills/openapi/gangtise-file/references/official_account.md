# 公众号资讯调用指导

## 简介

按关键词、证券、公众号（ID 或名称）、文章类型、行业、时间等条件检索**公众号资讯列表**，返回文章 ID、标题、摘要等元数据。主脚本：`scripts/official_account.py`。行业可选值见 `scripts/get_industries.py`；其余参数由后端智能匹配或直接传 API code。

`--accounts` 支持传 **accountId** 或**公众号名称**：名称会通过 `officialAccount/search` 自动解析；须**完全匹配**名称才会继续检索，否则返回候选列表供确认。

下载正文使用 open **`officialAccount/download/file`**，通过 `-d` 或 `scripts/get_file.py` 完成。

## 主脚本：执行检索

| 参数 | 必填 | 说明 |
|------|------|------|
| `-k` / `--keyword` | 否 | 文章检索关键词，需为具体词条（如「泡泡玛特」），勿用白话问句。 |
| `-sd` / `--start-date` | 否 | 开始时间，`YYYY-MM-DD` 或 `yyyy-MM-dd HH:mm:ss`。 |
| `-ed` / `--end-date` | 否 | 结束时间，格式同上。 |
| `-l` / `--limit` | 否 | 返回条数上限，默认 100，单页最大 50（自动分页）。 |
| `--securities` | 否 | 证券列表，逗号分隔；可为名称、代码或拼音。 |
| `--accounts` | 否 | 公众号 **ID 或名称**，逗号分隔；名称自动解析，多匹配时返回候选。 |
| `--account-category-list` | 否 | 解析 `--accounts` 名称时的**公众号分类**筛选，见下表；不传则含未分类公众号。 |
| `--category-list` | 否 | **文章类型**，英文 code 或中文，如 `news,report` 或 `新闻资讯,报告类`。 |
| `--industries` | 否 | 行业名称，逗号分隔。 |
| `--search-type` | 否 | `1` 标题搜索（默认），`2` 全文搜索。 |
| `--rank-type` | 否 | `1` 综合排序（默认），`2` 时间倒序。 |
| `-d` / `--download` | 否 | 检索后自动下载正文。 |
| `-od` / `--output-dir` | 否 | 结果与下载文件保存目录路径，建议绝对路径。 |
| `-dt` / `--download-types` | 否 | 下载格式，逗号分隔：`txt`（默认）、`html`。 |

### 公众号分类（`--account-category-list`）

用于解析 `--accounts` 中的名称时缩小搜索范围，支持多选（英文 code 或中文）：

| code | 中文 |
|------|------|
| `listedCompany` | 上市公司 |
| `broker` | 券商团队 |
| `government` | 政府官方 |
| `media` | 媒体 |

> 部分公众号不属于以上四类，其 `category` 为 null。传入 `--account-category-list` 时，这些**未分类**公众号不会参与名称匹配；若需匹配全部公众号（含未分类），请不要传入该参数。

## 调用示例

按关键词与时间范围检索：

```bash
python3 scripts/official_account.py -k 泡泡玛特 -sd 2026-01-01 -ed 2026-04-30 -l 20
```

按公众号名称筛选（自动解析 ID）：

```bash
python3 scripts/official_account.py --accounts 独角兽 -l 10
```

按名称 + 分类缩小匹配范围（仅券商团队类公众号）：

```bash
python3 scripts/official_account.py --accounts 某券商研究 --account-category-list broker -l 5
```

组合条件并下载：

```bash
python3 scripts/official_account.py -k 新能源 --category-list news,report --securities 比亚迪 -l 10
```

```bash
python3 scripts/official_account.py -k 机器人 -d -dt txt,html -od /tmp/official
```

## 单独下载

```bash
python3 scripts/get_file.py --file-id 276851 --file-type 公众号 -dt html
```

## 返回说明

- **成功**：返回文件列表（含 `类型ID`=articleId、标题、摘要、公众号名称等）。
- **失败**：返回错误信息；`--accounts` 名称存在多个候选时，返回候选列表供用户确认后重试。
