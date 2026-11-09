# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-file/references/investment_calendar.md
# Regenerate: python3 scripts/generate.py
# 投研日程调用指导

## 简介

本脚本 `scripts/investment_calendar.py` 整合五类资讯日程列表接口（均为 `POST`，分页 `from`/`size`，单页最大 50 条）：

| `-t` / `--type` | 说明 | 接口路径（相对 open-insight） |
|----------|------|------------------------------|
| `roadshow` | 路演 | `/schedule/roadshow/getList` |
| `site_visit` | 调研 | `/schedule/site-visit/getList` |
| `strategy_meeting` | 线下策略会 | `/schedule/strategy-meeting/getList` |
| `forum` | 论坛 | `/schedule/forum/getList` |
| `performance` | 财报日历 | `/schedule/performance-calendar/getList` |

牵头机构名称通过智能匹配为机构 ID；研究方向支持 `utils.py` 中 `RESEARCH_AREA_MAP` 的中文名（宏观、策略、固收、金工、海外）或**直接传研究方向 ID**。

## 公共参数

| 参数 | 说明 |
|------|------|
| `-t` / `--type` | **必填**，`roadshow` / `site_visit` / `strategy_meeting` / `forum` / `performance` |
| `-k` / `--keyword` | 搜索关键词，可为空（**财报日历不支持**） |
| `-sd` / `--start-date` | 举办开始日期 `YYYY-MM-DD`（路演等转为 13 位时间戳 `startTime`；财报日历为 `startDate`） |
| `-ed` / `--end-date` | 举办结束日期 `YYYY-MM-DD`（路演等结束日含全天；财报日历为 `endDate`） |
| `--publish-start-date` | 收录开始时间 `YYYY-MM-DD` 或 `YYYY-MM-DD HH:mm:ss`（路演/调研/线下策略会/论坛转为 `publishStartTime`）。不传则不按收录时间过滤 |
| `--publish-end-date` | 收录结束时间，格式同上；只传日期时含当天全天（转为 `publishEndTime`） |
| `-l` / `--limit` | 返回条数上限；不传时默认见 `FILE_DEFAULT_LIMIT["calendar"]`，开启 `-d` 下载时默认 `10` |

`--start-date` / `--end-date` 过滤的是**日程举办时间**。`--publish-start-date` / `--publish-end-date` 过滤的是**日程信息首次被收录或发布的时间**。两对区间可以同时使用，关系为「与」。财报日历不支持收录时间参数。

## 按类型的可选参数

### 路演 `roadshow`

| 参数 | 对应请求字段 | 取值说明 |
|------|----------------|----------|
| `--research-areas` | `researchAreaList` | 研究方向 ID 或中文名（见 `RESEARCH_AREA_MAP`） |
| `--institutions` | `institutionList` | 牵头机构，逗号分隔，智能匹配 brokerId |
| `--securities` | `securityList` | 证券列表，逗号分隔；可为证券名称、代码或拼音首字母。 |
| `--category-list` | `categoryList` | `earningsCall` 业绩会、`strategyMeeting` 策略会、`companyAnalysis` 公司分析、`industryAnalysis` 行业分析、`fundRoadshow` 基金路演 |
| `--market-list` | `marketList` | `aShares`、`hkStocks`、`usChinaConcept`、`usStocks` |
| `--participant-role-list` | `participantRoleList` | `management` 高管、`expert` 专家 |
| `--broker-type-list` | `brokerTypeList` | `cnBroker` 中资卖方、`otherBroker` 外资卖方 |
| `--permission` | `permission` | `1` 公开、`2` 私密；可逗号多选，如 `1` 或 `1,2` |

### 调研 `site_visit`

| 参数 | 对应请求字段 | 取值说明 |
|------|----------------|----------|
| `--research-areas` | `researchAreaList` | 同路演 |
| `--institutions` | `institutionList` | 牵头机构 |
| `--securities` | `securityList` | 证券列表；完整代码或名称 / 拼音等（自动解析） |
| `--object-list` | `objectList` | `company` 公司调研、`industry` 行业调研 |
| `--category-list` | `categoryList` | `single` 单场、`series` 系列 |
| `--market-list` | `marketList` | 同路演 |
| `--permission` | `permission` | `1` / `2`，可多选 |

### 线下策略会 `strategy_meeting`

仅支持公共参数与：

| 参数 | 对应请求字段 |
|------|----------------|
| `--institutions` | `institutionList` |

（接口无 `researchAreaList` / `securityList` 等。）

### 论坛 `forum`

| 参数 | 对应请求字段 | 取值说明 |
|------|----------------|----------|
| `--securities` | `securityList` | 完整代码或名称 / 拼音等（自动解析） |
| `--research-areas` | `researchAreaList` | 研究方向 ID 或中文名 |

### 财报日历 `performance`

涵盖业绩预告、业绩快报、业绩公告三类财报事件。按发布日期（`publishDate`）过滤。

| 参数 | 对应请求字段 | 取值说明 |
|------|----------------|----------|
| `--securities` | `securityList` | 证券代码/名称，逗号分隔（如 `000001.SZ`） |
| `--market-list` | `marketList` | `aShares`、`hkStocks`、`usChinaConcept`、`usStocks` |
| `--category-list` | `categoryList` | `performanceForecast` 业绩预告、`performanceExpress` 业绩快报、`performanceAnnouncement` 业绩公告 |
| `-d` / `--download` | — | 是否自动下载已发布报告的原文件 |
| `-od` / `--output-dir` | — | 结果与下载文件保存目录路径（建议绝对路径） |

#### 发布状态说明（重要）

返回字段 `发布状态` 对应接口 `hasAttachment`，语义如下：

| 发布状态 | 含义 | 能否下载 |
|----------|------|----------|
| **已发布（可下载原文件）** | 财报已正式披露并产生原文件 | 可以；用 `类型ID`（`performanceReportId`）经 `get_file.py` 下载 |
| **尚未发布（日程预告，无文件）** | 仅为日程预告，报告尚未发布 | 不可以；此时无附件可下 |

## 枚举与辅助脚本

- **机构**：`python3 scripts/get_institutions.py`
- **研究方向中文名**：见 `scripts/utils.py` 中 `RESEARCH_AREA_MAP`（若平台「研究方向分类」与内置 ID 不一致，请直接传接口要求的 ID）

## 返回说明

每条记录包含 `类型`（路演 / 调研 / 线下策略会 / 论坛 / 财报日历）、`类型ID` 及标题、时间等字段。

- **路演 / 调研 / 线下策略会 / 论坛**：`文件时间` 是举办时间（`startTime`～`endTime`）。`收录时间` 对应接口 `publishTime`，为该日程信息首次被收录的时间（东八区），与举办时间不同，可用于增量同步和去重。日程类结果一般不通过 `get_file.py` 下载文件；如需报名链接等，见返回中的 `报名链接`（线下策略会）等字段。
- **财报日历**：`类型` 为「财报日历」，`类型ID` 为 `performanceReportId`。仅「已发布」条目可下载原文件。

## 调用示例

```bash
# 路演：关键词 + 时间 + 路演类型
python3 scripts/investment_calendar.py -t roadshow -k 策略会 -sd 2026-01-01 -ed 2026-05-31 --category-list strategyMeeting -l 20

# 调研：公司调研 + 公开权限
python3 scripts/investment_calendar.py -t site_visit --object-list company --permission 1 -sd 2026-01-01 -ed 2026-05-31

# 线下策略会：机构
python3 scripts/investment_calendar.py -t strategy_meeting --institutions 开源证券 -l 10

# 论坛：研究方向（宏观 → ID 由 RESEARCH_AREA_MAP 解析）
python3 scripts/investment_calendar.py -t forum --research-areas 宏观 -k 论坛 -l 15

# 论坛：3 月新收录、且举办时间也在 3 月（两对时间为「与」）
python3 scripts/investment_calendar.py -t forum --publish-start-date 2026-03-01 --publish-end-date 2026-03-31 -sd 2026-03-01 -ed 2026-03-31 -l 20

# 路演：按证券名称筛选
python3 scripts/investment_calendar.py -t roadshow --securities 宁德时代 -sd 2026-01-01 -ed 2026-05-31 -l 15

# 财报日历：A 股 + 业绩公告 + 日期区间
python3 scripts/investment_calendar.py -t performance --market-list aShares --category-list performanceAnnouncement -sd 2024-01-01 -ed 2024-06-30 -l 20

# 财报日历：按证券筛选并下载已发布原文件
python3 scripts/investment_calendar.py -t performance --securities 招商银行 -sd 2024-01-01 -ed 2024-06-30 -d true -l 10
```

下载单份已发布业绩报告：

```bash
python3 scripts/get_file.py --file-id <performanceReportId> --file-type "财报日历"
```
