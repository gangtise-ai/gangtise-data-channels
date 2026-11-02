# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-private/references/private_record.md
# Regenerate: python3 scripts/generate.py
# 录音速记 API（Open API · record）

## 简介

脚本 **`scripts/private_record.py`** 对接 Gangtise 终端**录音速记**数据：

- **getList**：分页检索录音列表，返回 `recordId` 及元信息。
- **download/file**：按 `recordId` + `contentType` 下载 **原始文件 / 语音识别 / AI 速记**。

## 模式（`-m` / `--mode`）

| 模式 | 说明 |
|------|------|
| `search` | 列录音，落盘 `private_record_list_*.csv`（默认）。 |
| `get` | 按 `--record` 下载。 |

**自动路由**：提供 `--record` 或 `--record-file` 时自动进入 `get`。参数仅含字母数字与逗号时视为 ID；含中文等则 search，**唯一完全匹配**时自动 get。

筛选参数均可选。

## 参数

| 参数 | 说明 |
|------|------|
| `-m` / `--mode` | `search` \| `get`（默认 `search`）。 |
| `-k` / `--keyword` | 录音标题关键词（`search`）。 |
| `-st` / `-et` | 文件**创建时间**（`yyyy-MM-dd` 可自动补全时分秒）。 |
| `--category-list` | `upload` `link` `mobile` `gtNote` `pc` `share`，或中文（上传文件、手机录音、与我分享等）。 |
| `--space-type-list` | `1` 我的速记、`2` 租户速记（可传中文）。 |
| `--content-type` | `original` / `asr` / `summary` / `both`（asr+summary）/ `all`（original+asr+summary）（`get` 模式）。 |
| `--record` | 录音 ID 或标题，逗号分隔（提供后自动 `get`）。 |
| `--record-file` | CSV 含 `record_id` 列（提供后自动 `get`）。 |
| `-l` / `--limit` | `search` 列表条数上限（默认 100）。 |
| `-od` / `--output-dir` | 结果保存目录路径；文件名自动生成。 |

**注意**：`category=share`（与我分享）的录音**无法下载 original** 原始文件。

## 调用示例

```bash
python3 scripts/private_record.py -m search -k "晨会" -st 2024-04-01 -et 2024-04-30 -l 30
```

```bash
python3 scripts/private_record.py --record 49412 --content-type summary
```

```bash
python3 scripts/private_record.py --record 49412,49413 --content-type asr,summary
```

```bash
python3 scripts/private_record.py -m search -k "电子" --category-list upload,mobile -l 10
```

## 返回说明

- **列表 CSV 列**：`record_id`, `title`, `create_time`, `category`, `record_duration`, `record_size`, `url`, `space_type`, `uploader`
- **下载内容**：`workspace/gangtise/private_record/private_record_content_*.md`（`GTS_SAVE_FILE=True` 时；否则在回复中展示）
- **search 成功**：消息末尾提示可通过 `--record-file` 读取 CSV 再下载
- **原始文件**为二进制时，文案中提示字节大小，不内嵌全文
