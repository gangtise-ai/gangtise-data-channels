---
name: gangtise-file
description: "在 Gangtise 文件中心按类型/日期/证券等条件检索文档并可选下载全文，覆盖：研报、观点、纪要、公众号资讯、公司公告（A股/港股/美股）、管理层讨论与分析（半年报/年报/业绩会）、投资者问答、投研日程（路演/调研/线下策略会/论坛/财报日历）。返回文件 ID、元数据与摘要，适合“先定位/筛选再下载核验”；深入阅读与引用段落内容请优先用 `gangtise-kb`。"
version: 1.7.0
author: Gangtise
metadata:
  category: openapi
  homepage: "https://open-platform.gangtise.com/"
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-file.zip"
---

# 文件检索

## 概览

该技能会查询 Gangtise 文件中心，检索多种文档类型，例如研究报告、研报图片、投资者问答、外资研报、外资机构/独立观点、公司公告、会议纪要、帕米尔专家纪要、首席观点、公众号资讯与投研日程（路演、调研、线下策略会、论坛、财报日历）等。它会返回文件 ID，并附带关键元数据与简短摘要；这些命中结果基于检索匹配与字段归纳，强调专业性、准确性与覆盖全面，同时提供按“类型 + ID”下载完整文件的方法。注意：由于 API 限制，大多数结果最多限制为 100 条；多数情况下建议将结果数量限制在 10 条以内。

使用场景：
- 你需要按**类型、日期、证券或其他元数据**来定位、筛选或整理文档。
- 你想先构建一个**候选文档列表**（例如某只股票的近期报告、某段时间内的全部公告）。
- 你计划**下载完整文件**并在本技能之外处理（例如后续解析或单独阅读）。
- 给输出的结果配图，可以使用研报图片检索脚本，将查找到的图片插入输出结果，使得输出结果更加生动形象。

与其他技能的区别：
- 当你主要关心的是*文本内容本身*（用于总结、问答、抽取论点等），并且不需要浏览长文件列表时，优先使用 **`gangtise-kb`**。

（中文说明：`gangtise-file` 更像"文件目录/索引"，解决"有哪些文件、ID 是什么、按条件筛一批出来"的问题；真正看内容、抽段落建议用 `gangtise-kb`。）


各文档类型的**主脚本**用于执行检索并返回文件列表；部分参数提供**枚举值脚本**（如行业、机构等），调用前可先执行对应脚本获取可选值。**无枚举值接口的参数**（如关键词、日期等）会由后端**智能匹配**，直接传入用户意图相关文本即可。

多数检索脚本具有 `-d` / `--download`，用于在检索后自动下载对应文件至本地；**首席观点**与**外资机构观点**通过详情接口拉取正文并保存为 txt/md，**外资独立观点**下载 HTML。一般仅在用户明确要求下载时使用 `-d`。

多数脚本都具有 `-dt` / `--download-types` 参数，用于指定下载的文件类型，逗号分隔，可选值：
  - announcement: pdf, markdown
  - foreign_report: pdf, markdown, zh_pdf, zh_markdown
  - foreign_opinion: institution 用 txt / zh；independent 用 html / html_zh
  - opinion: txt, md
  - official_account: txt, html
  - pamirs_summary: original, html
  - report: pdf, markdown

所有脚本都具有`-sd`和`-ed`参数，使用时注意今天的年份和日期！

**搜索类型（`--search-type`）**：内资研报、外资研报、会议纪要、帕米尔专家纪要、公众号资讯、公司公告均支持两种关键词检索方式——`1` 标题搜索（默认）、`2` 全文搜索。用户明确要在正文中找词（如“搜全文”“正文里有…”）时用 `--search-type 2`；默认标题检索即可。标题无结果时多数脚本会自动再试全文。

整体长度是可控的，调用时请不要使用 `| head -N`，输出文件地址一般在末尾。

调用对应脚本前，请先查看对应脚本的调用指导文档，了解更多参数的含义和使用方法。

### 1. 从研究报告检索

按关键词、证券、日期、券商、行业、研报类别、语义标签、评级/评级变动、页数范围、来源类型等条件检索研究报告。支持 `--search-type`：`1` 标题（默认）/ `2` 全文。

示例（证券"比亚迪"，限定时间范围与数量）：

```bash
python3 scripts/report.py --securities 比亚迪 -sd 2026-01-01 -ed 2026-12-31 -l 20
```

示例（关键词全文检索）：

```bash
python3 scripts/report.py -k 固态电池 --search-type 2 -sd 2026-01-01 -ed 2026-12-31 -l 20
```

行业、机构枚举值可通过 `scripts/get_industries.py`、`scripts/get_institutions.py` 获取。详见 [研究报告调用指导](./references/report.md)。

### 1.1 研报图片检索

按关键词搜索研报中的图片，返回图注、页码、页面内容描述及 `chunkId`；支持时间范围、研报 ID （研报 ID 可以通过研报检索脚本获取）过滤，并可 `-d` 下载原图。

```bash
python3 scripts/report_image.py -k AI -sd 2024-01-01 -ed 2024-12-31 -l 10
```

```bash
python3 scripts/report_image.py -k 算力 --source-id 297236012319510528 -d true
```

详见 [研报图片调用指导](./references/report_image.md)。

### 2. 外资研报检索

按关键词、证券、日期、券商、行业、区域、研报类别、语义标签、评级/评级变动、页数范围等条件检索外资研报列表。境外证券代码格式如 `UBER.N`。支持 `--search-type`：`1` 标题（默认）/ `2` 全文。

示例（关键词 + 时间范围）：

```bash
python3 scripts/foreign_report.py -k 自动驾驶 -sd 2026-01-01 -ed 2026-05-31 -l 20
```

示例（全文检索）：

```bash
python3 scripts/foreign_report.py -k 自动驾驶 --search-type 2 -sd 2026-01-01 -ed 2026-05-31 -l 20
```

行业、券商、区域枚举值可通过 `scripts/get_industries.py`、`scripts/get_institutions.py`、`scripts/get_regions.py` 获取。详见 [外资研报调用指导](./references/foreign_report.md)。

### 3. 首席观点列表检索

按关键词、证券、券商、研究方向、首席分析师、概念、观点类别、投研业务标签、机构标签、来源类型等条件检索首席观点列表（仅摘要 brief）。需要全文时使用 `-d` 调用详情接口下载正文（按条计费）。

示例（关键词 + 投研业务标签 + 来源）：

```bash
python3 scripts/opinion.py -k 半导体 --llm-tags strongRcmd --source-types realTime -l 20
```

示例（观点类别 + 机构标签）：

```bash
python3 scripts/opinion.py --categories 业绩点评 --broker-tags 头部券商 -l 20
```

示例（检索并下载正文）：

```bash
python3 scripts/opinion.py -k 安孚科技 -l 5 -d -dt txt
```

券商枚举值可通过 `scripts/get_institutions.py` 获取；首席分析师枚举值可通过 `scripts/get_chiefs.py` 获取。研究方向名称（宏观、策略、固收、金工、海外等）见 `scripts/utils.py` 中 `RESEARCH_AREA_MAP`。详见 [首席观点调用指导](./references/opinion.md)。

### 4. 外资机构观点 / 外资独立观点

`--source institution`（默认）检索外资券商观点列表（摘要 brief），`-d` 通过 `getDetail` 下载正文（`txt` / `zh`）；`--source independent` 检索海外独立分析师观点，`-d` 下载原文或中文翻译 **HTML**。

示例（机构观点 + 下载正文）：

```bash
python3 scripts/foreign_opinion.py --source institution -k 腾讯 -l 3 -d -dt txt,zh
```

示例（独立观点 + 下载）：

```bash
python3 scripts/foreign_opinion.py --source independent -k 肿瘤 -sd 2026-01-01 -ed 2026-05-31 -d -dt html,zh
```

详见 [外资/独立观点调用指导](./references/foreign_opinion.md)。

### 5. 从会议纪要检索

按关键词、证券、机构、行业、来源类型、会议类别/市场/参会人角色等条件检索会议纪要。支持 `--search-type`：`1` 标题（默认）/ `2` 全文。

示例（关键词 + 会议类别）：

```bash
python3 scripts/summary.py -k 锂电 --category-list earningsCall -l 20
```

示例（全文检索）：

```bash
python3 scripts/summary.py -k 锂电 --search-type 2 --category-list earningsCall -l 20
```

行业、机构枚举值可通过 `scripts/get_industries.py`、`scripts/get_institutions.py` 获取。详见 [会议纪要调用指导](./references/summary.md)。

### 5.1 帕米尔专家纪要检索

专用于检索帕米尔牵头机构下的专家纪要；支持关键词、证券、研究方向、纪要类别（公司分析/行业分析）、市场、排序与下载（原始文件或 HTML）。支持 `--search-type`：`1` 标题（默认）/ `2` 全文。需已购买专家纪要数据库权限。

示例（关键词 + 时间倒序）：

```bash
python3 scripts/pamirs_summary.py -k AI智能体 --rank-type 2 -l 20
```

示例（全文检索）：

```bash
python3 scripts/pamirs_summary.py -k AI智能体 --search-type 2 --rank-type 2 -l 20
```

研究方向枚举可通过 `scripts/get_industries.py` 获取。详见 [帕米尔专家纪要调用指导](./references/pamirs_summary.md)。

### 6. 公众号资讯检索

按关键词、证券、公众号（ID 或名称）、文章类型、行业、时间等条件检索资讯订阅平台消息列表；支持 `-d` 下载 txt/HTML 正文。支持 `--search-type`：`1` 标题（默认）/ `2` 全文。`--accounts` 传名称时会自动解析 ID，多匹配时返回候选提醒。

```bash
python3 scripts/official_account.py -k 泡泡玛特 -sd 2026-01-01 -ed 2026-04-30 -l 20
```

```bash
python3 scripts/official_account.py -k 泡泡玛特 --search-type 2 -sd 2026-01-01 -ed 2026-04-30 -l 20
```

```bash
python3 scripts/official_account.py --accounts 独角兽 -l 10
```

```bash
python3 scripts/official_account.py -k 机器人 --category-list news,report -d -dt txt
```

详见 [公众号资讯调用指导](./references/official_account.md)。

### 7. 从公司公告检索

按证券、关键词、日期等条件检索公司公告（支持 A 股、港股、美股）。支持 `--search-type`：`1` 标题（默认）/ `2` 全文。

示例（证券 + 关键词 + 时间；证券可写代码或名称）：

```bash
python3 scripts/announcement.py --securities 五粮液 -k 业绩 -sd 2026-01-01 -ed 2026-12-31
```

示例（全文检索）：

```bash
python3 scripts/announcement.py --securities 五粮液 -k 业绩 --search-type 2 -sd 2026-01-01 -ed 2026-12-31
```

详见 [公司公告调用指导](./references/announcement.md)。

### 7.1 管理层讨论与分析（半年报/年报 / 业绩会）

按报告期、证券与讨论维度，获取半年报/年报或业绩会中的管理层讨论与分析结构化正文。通过 `--type` 区分数据来源：`announcement`（半年报/年报）或 `earningsCall`（业绩会）。

示例（半年报业务经营维度）：

```bash
python3 scripts/management_discuss.py -t announcement -rd 2025-12-31 --securities 000001.SZ -dd all
```

示例（业绩会财务维度）：

```bash
python3 scripts/management_discuss.py -t earningsCall -rd 2025-12-31 --securities 比亚迪 -dd financialPerformance
```

详见 [管理层讨论与分析调用指导](./references/management_discuss.md)。

### 8. 投资者问答检索

按证券拉取互动平台、电话会议、调研纪要中的提问与回答结构化数据；支持按来源、问题类型、是否涉及重要信息筛选（默认 answer-important=1）。

```bash
python3 scripts/qa.py -s 601012.SH -sd 2026-05-01 -ed 2026-06-16 -l 5
```

详见 [投资者问答调用指导](./references/qa.md)。

### 9. 投研日程（路演 / 调研 / 线下策略会 / 论坛 / 财报日历）

示例（路演 + 关键词 + 举办时间）：

```bash
python3 scripts/investment_calendar.py -t roadshow -k 策略会 -sd 2026-01-01 -ed 2026-05-31 -l 20
```

路演、调研、线下策略会、论坛还可按收录时间过滤（`publishStartTime` / `publishEndTime`），与举办时间是「与」关系。返回的 `收录时间` 是该条信息首次被收录的时间（东八区），用于增量同步：

```bash
python3 scripts/investment_calendar.py -t roadshow --publish-start-date 2026-03-01 --publish-end-date 2026-03-31 -l 20
```

财报日历示例（业绩公告 + 日期；结果区分「已发布可下载」与「尚未发布预告」）：

```bash
python3 scripts/investment_calendar.py -t performance --category-list performanceAnnouncement -sd 2024-01-01 -ed 2024-06-30 -l 20
```

机构枚举见 `scripts/get_institutions.py`；研究方向中文名见 `scripts/utils.py` 中 `RESEARCH_AREA_MAP`。详见 [投研日程调用指导](./references/investment_calendar.md)。

### 10. 下载文件

根据文件 ID 与文件类型下载完整文件至本地。

示例（下载研究报告）：

```bash
python3 scripts/get_file.py --file-id 1234567890 --file-type "研究报告"
```

外资独立观点 HTML 示例：

```bash
python3 scripts/get_file.py --file-id <independentOpinionId> --file-type 外资独立观点 -dt zh
```

帕米尔专家纪要示例：

```bash
python3 scripts/get_file.py --file-id <summaryId> --file-type "帕米尔专家纪要" -dt html
```

财报日历原文件示例（仅已发布条目；ID 来自财报日历检索的 `类型ID`）：

```bash
python3 scripts/get_file.py --file-id <performanceReportId> --file-type "财报日历"
```

### 11. 获取枚举值

获取行业、机构的枚举值列表，用于为上述检索脚本提供参数可选值。

```bash
python3 scripts/get_industries.py
python3 scripts/get_institutions.py
python3 scripts/get_regions.py
python3 scripts/get_chiefs.py --name xxx --institution xxx --group xxx
```
