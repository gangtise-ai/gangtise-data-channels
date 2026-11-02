# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-private/references/wechat_message.md
# Regenerate: python3 scripts/generate.py
# 微信消息 API（Open API · wechatgroupmsg）

## 简介

脚本 **`scripts/wechat_message.py`** 调用 Gangtise **open-vault** 接口（需已绑定并激活群消息助理且助理在群内）：

- **chatroomId**：按群名称查 **群 ID**（`search`）。
- **list**：分页拉取**群消息**（`get`）。

域名默认：`https://openapi.gangtise.com/application/open-vault`（可用环境变量 `GANGTISE_VAULT_DOMAIN` 覆盖）。

## 模式（`-m` / `--mode`）

| 模式 | 说明 |
|------|------|
| `search` | 查微信群 ID 列表（`wechat_chatroom_*.md` 落盘，默认）。 |
| `get` | 拉群消息；可用 `--groups` 限定群，`-k` 为消息关键词；显式 `-m get` 时即使无群 ID 也在全部可访问群内拉取。 |

**自动路由**：提供 `--groups` 或 `-m get` 时进入 `get`；否则为 `search`。`--groups` 仅含字母数字与逗号时视为群 ID；含中文等则先 search，**唯一完全匹配**时自动 get。

## 参数

| 参数 | 说明 |
|------|------|
| `-m` / `--mode` | `search` \| `get`（默认 `search`）。 |
| `-n` / `--room-name` | 群名称，逗号分隔（`search` → `roomName`）。 |
| `-k` / `--keyword` | `search`：未传 `-n` 时作群名，或与 `-n` 并用作群列表过滤；`get`：**消息内容**关键词。 |
| `-l` / `--limit` | `search`：最多返回群数（默认 50）；`get`：最多消息条数（默认 500）。 |
| `-st` / `-et` | 消息时间范围（仅 `get`）。 |
| `--groups` | 群 ID 或群名，逗号分隔（提供后自动 `get`）。 |
| `--industries` | 行业 ID，逗号分隔（`get` 过滤）。 |
| `--categories` | `text`,`image`,`documents`,`url`（`get`）。 |
| `--tags` | 标签代码或中文（如 `路演`→`roadShow`）（`get`）。 |
| `--page-from` / `--page-size` | 分页；`page-size` 最大 50。 |
| `-od` / `--output-dir` | 结果保存目录路径（需 `GTS_SAVE_FILE=True`）。 |

## 调用示例

```bash
# 查群 ID（默认 search）
python3 scripts/wechat_message.py -m search -n "AI学习群,投研分享群"
```

```bash
python3 scripts/wechat_message.py -m search -k 投研
```

```bash
# 已知群 ID，拉消息（自动 get）
python3 scripts/wechat_message.py --groups id1,id2 -k "半导体" -st 2024-03-01 -et 2024-03-31 -l 100
```

```bash
# 按群名自动解析（唯一完全匹配时自动 get）
python3 scripts/wechat_message.py --groups AI学习群 -k "业绩" -l 50
```

```bash
# 全部可访问群内按关键词搜消息
python3 scripts/wechat_message.py -m get -k "业绩" -l 50
```

## 返回说明

- **成功（search）**：`workspace/gangtise/wechat_message/wechat_chatroom_*.md`（或内联展示）；消息末尾提示复制群 ID 后使用 `--groups`。
- **成功（get）**：`wechat_message_*.md`。消息行含正文、群信息、标签等；若接口返回 `quoteMsg`，另含 **引用消息ID** / **引用消息内容** / **引用消息链接**（对应 `quoteMsgId`、`quoteContent`、`quoteUrl`，可能为空）。
- 设置 `GTS_SAVE_FILE=True` 时落盘 md/json；股票池类 CSV 逻辑不适用本脚本。
