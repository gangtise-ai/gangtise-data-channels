# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-private/references/private_meeting.md
# Regenerate: python3 scripts/generate.py
# 我的会议 API（Open API · my-conference）

## 简介

脚本 **`scripts/private_meeting.py`** 对接 Gangtise **会议助理**录制的个人会议：

- **getList**：分页检索会议列表，返回 `conferenceId` 及元信息。
- **download/file**：按 `conferenceId` 下载 **语音识别（asr）** 或 **AI 速记（summary）**（asr+summary 各计一次下载）。

## 模式（`-m` / `--mode`）

| 模式 | 说明 |
|------|------|
| `search` | 列会议，落盘 `private_meeting_list_*.csv`（默认）。 |
| `get` | 按 `--conference` 下载内容。 |

**自动路由**：提供 `--conference` 或 `--conference-file` 时自动进入 `get`。参数仅含字母数字与逗号时视为 ID；含中文等则 search，**唯一完全匹配**时自动 get。

`search` 的筛选参数均为可选。

## 参数

| 参数 | 说明 |
|------|------|
| `-m` / `--mode` | `search` \| `get`（默认 `search`）。 |
| `-k` / `--keyword` | 会议标题关键词（`search`）。 |
| `-st` / `-et` | 会议**创建时间**范围（日期可只传 `yyyy-MM-dd`）。 |
| `--securities` | 证券代码，逗号分隔，如 `000001.SZ`。 |
| `--institutions` | 牵头机构 ID，逗号分隔。 |
| `--research-areas` | 研究方向 ID，逗号分隔。 |
| `--category-list` | 会议类别：`earningsCall` 等，或中文（业绩会、策略会…）。 |
| `--content-type` | `asr` / `summary` / `both`（`get` 模式，默认 `both`）。 |
| `--conference` | 会议 ID 或标题，逗号分隔（提供后自动 `get`）。 |
| `--conference-file` | CSV 含 `conference_id` 列（提供后自动 `get`）。 |
| `-l` / `--limit` | `search` 列表条数上限（默认 100）。 |
| `--page-from` / `--page-size` | 分页，`page-size` 最大 50。 |
| `-od` / `--output-dir` | 结果保存目录路径；文件名自动生成。 |

## 调用示例

```bash
python3 scripts/private_meeting.py -m search -k "AI" -st 2024-01-01 -et 2024-12-31 -l 30
```

```bash
python3 scripts/private_meeting.py --conference 4444816 --content-type summary
```

```bash
python3 scripts/private_meeting.py --conference 4444816,43319 --content-type both
```

```bash
python3 scripts/private_meeting.py -m search -k "业绩" --category-list earningsCall -l 10
```

## 返回说明

- **列表**：`workspace/gangtise/private_meeting/private_meeting_list_*.csv`
- **下载内容**：`private_meeting_content_*.md`（`GTS_SAVE_FILE=True` 时落盘；否则在回复中展示）
- **search 成功**：消息末尾提示可通过 `--conference-file` 读取 CSV 再下载
- 列：`conference_id`, `title`, `publish_time`, `category`, `institution_*`, `security_*`, `research_area_*`, `guest`

## 权限

试用账号一般仅近 **1 个月** 数据；正式账号以购买服务为准。
