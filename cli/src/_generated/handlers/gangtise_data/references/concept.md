# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-data/references/concept.md
# Regenerate: python3 scripts/generate.py
# 题材指数 API（Open API · concept/v2/info & concept/v2/securities）

## 简介

通过 Gangtise Open API 查询**题材指数**的最新截面信息，脚本 **`scripts/concept.py`**。

覆盖两个接口：

| 接口 | 说明 |
|------|------|
| `concept/v2/info` | 题材定义、投资逻辑、行业空间、竞争格局 |
| `concept/v2/securities` | 当前成分股列表（按分组展示）；无成分股时 `securityDetail` 为 `null`，不扣积分 |

与其他 data 脚本不同，本脚本将结果**组装为 Markdown 文档**（非 CSV 宽表），便于直接阅读与引用。本接口**仅返回最新截面**，不支持历史交易日回溯。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-t` / `--type` | 否 | 查询类型，默认 **`info`**。可选：`info`（仅基本信息）、`securities`（仅成分股）、`all`（两者都查）。 |
| `-c` / `--concepts` | 否* | 题材 ID 或名称，逗号分隔。纯字母数字视为 ID；否则 search，唯一完全匹配时自动查询。 |
| `--concepts-file` | 否* | CSV 须含列 **`concept_id` / `conceptId` / `concept_name` / `conceptName`** 之一。 |
| `--top` | 否 | 名称搜索返回条数上限，默认 **10**，最大 **10**（非纯 ID 时生效）。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

\* 须至少提供 `-c/--concepts` 或 `--concepts-file` 之一。

## 题材指代

- 可直接传入 **conceptId**（如 `121000130`）。
- 可传入 **题材名称**（如 `机器人`）、拼音/首字母或分组名称。
- 本接口**仅返回最新截面**，不支持历史交易日回溯。

## 约束与说明

- `--type=all` 时，对每个题材并发调用 info 与 securities 两个接口。
- 多题材批量查询时，每个题材独立请求；结果在 Markdown 中以 `---` 分隔。
- 成分股按接口返回顺序展示：分组按 `groupName` 字母序，组内按 `securityCode` 升序。
- 文本字段（定义、投资逻辑、行业空间、竞争格局）若题材未配置，接口返回 `null`，对应 Markdown 章节会省略。
- info 与有成分股的 securities 调用按次计费；无成分股时不扣积分。

## 调用示例

```bash
# 默认：仅基本信息
python3 scripts/concept.py -c 机器人
```

```bash
# 按 conceptId 查询
python3 scripts/concept.py -c 121000130
```

```bash
# 仅查基本信息（定义、投资逻辑、行业空间、竞争格局）
python3 scripts/concept.py -c 机器人 --type info
```

```bash
# 仅查成分股
python3 scripts/concept.py -c 机器人 --type securities
```

```bash
# 批量查询基本信息 + 成分股
python3 scripts/concept.py -c 机器人,固态电池 --type all
```

```bash
python3 scripts/concept.py --concepts-file ./concepts.csv
```

## 返回说明

- **成功**：在 `workspace/gangtise/concept/`（或当前环境解析出的 gangtise 工作目录下）生成 **`concept_*.md`**；终端返回文案中含文件绝对路径及完整 Markdown 正文。
- **失败**：如未配置授权、题材无法解析、接口错误等，返回错误说明字符串。

## 返回数据示例（Markdown 结构）

```markdown
# 机器人（121000130）

## 题材定义
人工替代与具身智能的核心载体，涵盖工业/服务/特种机器人及人形机器人整机与核心零部件

## 投资逻辑
需求刚性：全球老龄化、用工荒、制造业降本增效……

## 行业空间
全球
2025 年：约150-180 亿元人民币……

## 竞争格局
行业0-1阶段，中美主导……

## 成分股（共 68 只）

### 灵巧手
- 雷赛智能（002979.SZ）
- 隆盛科技（300680.SZ）

### 丝杠
- 北特科技（603009.SH）
- 五洲新春（603667.SH）
```
