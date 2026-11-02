# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-file/references/management-discuss.md
# Regenerate: python3 scripts/generate.py
# 管理层讨论与分析调用指导

## 简介

获取上市公司**半年报/年报**或**业绩会**中管理层讨论与分析（MD&A）的结构化内容，反映公司对行业环境、经营状况、财务表现、发展规划及潜在风险的综合研判。主脚本：`scripts/management_discuss.py`。

两个 OpenAPI 通过 `--type` 区分：

| `--type` | 说明 | 报告期约束 |
|----------|------|------------|
| `announcement` | 半年报/年报中的管理层讨论与分析 | `xxxx-06-30`、`xxxx-12-31` |
| `earningsCall` | 业绩会中的管理层讨论与分析 | `xxxx-03-31`、`xxxx-06-30`、`xxxx-09-30`、`xxxx-12-31` |

## 主脚本：执行查询

| 参数 | 必填 | 说明 |
|------|------|------|
| `-t` / `--type` | 是 | 数据来源：`announcement`（半年报/年报）或 `earningsCall`（业绩会）。 |
| `-rd` / `--report-date` | 是 | 报告期，严格为 `yyyy-MM-dd` 格式。 |
| `--securities` | 是 | 证券列表，逗号分隔；可为证券名称、代码或拼音首字母。 |
| `-dd` / `--discussion-dimension` | 是 | 讨论维度，见下表。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

### 讨论维度（`--discussion-dimension`）

| 值 | 含义 |
|----|------|
| `businessOperation` | 业务经营与行业情况 |
| `financialPerformance` | 财务状况与经营成果 |
| `developmentAndRisk` | 发展规划与风险 |
| `all` | 返回完整管理层讨论内容 |

参数支持中文别名（如「业务经营」「财务状况」「全部」等），脚本会自动映射为接口所需英文 code。

**无枚举值接口的参数**（如 `securities`）：直接传入用户意图相关文本，后端会**智能匹配**证券代码。

## 调用示例

**半年报/年报 — 业务经营与行业情况：**
```bash
python3 scripts/management_discuss.py -t announcement -rd 2025-06-30 --securities 000001.SZ -dd businessOperation
```

**半年报/年报 — 获取完整管理层讨论（`all`）：**
```bash
python3 scripts/management_discuss.py -t announcement -rd 2024-12-31 --securities 平安银行 -dd all
```

**业绩会 — 财务状况与经营成果：**
```bash
python3 scripts/management_discuss.py -t earningsCall -rd 2025-06-30 --securities 比亚迪 -dd financialPerformance
```

**业绩会 — 并发获取全部维度（`all`）：**
```bash
python3 scripts/management_discuss.py -t earningsCall -rd 2025-06-30 --securities 000001.SZ -dd all
```

**多证券批量查询：**
```bash
python3 scripts/management_discuss.py -t earningsCall -rd 2025-03-31 --securities 000001.SZ,600519.SH -dd developmentAndRisk
```

## 返回说明

- **成功**：返回各证券对应报告期、讨论维度下的管理层讨论正文。`announcement` 的 `content` 可能为多段文本；`earningsCall` 的 `all` 会按维度分节合并展示。
- **失败**：返回错误信息（如报告期格式不符、证券未解析、该期无数据等）。
