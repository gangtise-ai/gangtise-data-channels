# 投资者问答调用指导

## 简介

按**证券**提取 Gangtise 投资者问答（QA）结构化数据，覆盖**电话会议、互动平台、调研纪要**等来源的提问与回答，并支持按问题来源、问题类型、是否涉及重要信息筛选。主脚本：`scripts/qa.py`。

## 主脚本：执行检索

| 参数 | 必填 | 说明 |
|------|------|------|
| `-s` / `--securities` | 是 | 证券列表，逗号分隔；可为名称、代码或拼音，如 `601012.SH`、`隆基绿能`。 |
| `-sd` / `--start-date` | 否 | 开始时间，`YYYY-MM-DD` 或 `yyyy-MM-dd HH:mm:ss`。 |
| `-ed` / `--end-date` | 否 | 结束时间，格式同上。 |
| `-l` / `--limit` | 否 | 返回条数上限，默认 100，单页最大 500（自动分页）。 |
| `--source` | 否 | 问题来源，逗号分隔，见下表。 |
| `--question-category` | 否 | 问题类型，逗号分隔，见下表。 |
| `--answer-important` | 否 | 答案是否涉及重要信息：`1`/`是` 仅重要；`0`/`否` 仅非重要；`0,1` 或 `all` 不过滤。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

### 问题来源（`--source`）

| code | 中文 |
|------|------|
| `conference` | 电话会议 |
| `interactive` | 互动平台 |
| `survey` | 调研纪要 |

### 问题类型（`--question-category`）

| code | 中文 |
|------|------|
| `productAndBusiness` | 产品技术与业务布局 |
| `capacityAndProjects` | 产能与项目进展 |
| `ordersAndCustomers` | 订单与客户 |
| `financialData` | 财务与经营数据 |
| `materialEvents` | 重大事项 |
| `capitalOperations` | 资本运作 |
| `shareholdersAndDividends` | 股东户数与常规分红 |
| `corporateGovernance` | 治理与管理 |
| `marketAndValuation` | 市场与估值 |
| `macroAndIndustry` | 宏观与行业看法 |
| `risksAndOthers` | 风险质疑其他 |

## 调用示例

按证券拉取近期问答：

```bash
python3 scripts/qa.py -s 601012.SH -sd 2026-05-01 -ed 2026-06-16 -l 50
```

限定互动平台与调研纪要，并只看涉及重要信息的问答：

```bash
python3 scripts/qa.py -s 隆基绿能 \
  --source interactive,survey \
  --question-category 产品技术与业务布局,财务与经营数据 \
  --answer-important 1 \
  -sd 2026-05-01 -ed 2026-06-16
```

## 返回说明

- **成功**：返回问答列表，每条包含来源、发布时间、提问、回答、回答方身份、证券代码、问题类型、是否涉及重要信息。
- **失败**：证券解析失败、筛选参数无法识别、无匹配结果或接口异常时会返回具体原因。
- **usage**：成功返回后按实际条数计入 `usage.qa`。
