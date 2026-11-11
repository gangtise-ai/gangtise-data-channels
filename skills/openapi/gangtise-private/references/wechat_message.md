# 微信消息 API（Open API · wechatgroupmsg）

## 简介

脚本 **`scripts/wechat_message.py`** 调用 Gangtise **open-vault** 接口（需已绑定并激活群消息助理且助理在群内）：

- **chatroomId**：按群名称查 **群 ID**（`search`）。
- **list**：分页拉取**群消息**（`get`）。
- **download/file**：按消息 `msgId` 下载文档/图片/音频/视频附件（`download`）。

域名默认：`https://openapi.gangtise.com/application/open-vault`（可用环境变量 `GANGTISE_VAULT_DOMAIN` 覆盖）。

## 模式（`-m` / `--mode`）

| 模式 | 说明 |
|------|------|
| `search` | 查微信群 ID 列表（默认）。 |
| `get` | 拉群消息；可用 `--groups` 限定群，`-k` 为消息关键词；显式 `-m get` 时即使无群 ID 也在全部可访问群内拉取。 |
| `download` | 按 `--messages` 中的 `msgId` 下载附件。 |

**自动路由**：提供 `--groups` 或 `-m get` 时进入 `get`；提供 `--messages`、`-d` 或 `-m download` 时进入 `download`；否则为 `search`。`--groups` 仅含字母数字与逗号时视为群 ID；含中文等则先 search，**唯一完全匹配**时自动 get。

## 参数

| 参数 | 说明 |
|------|------|
| `-m` / `--mode` | `search` \| `get` \| `download`（默认 `search`）。 |
| `-n` / `--room-name` | 群名称，逗号分隔（`search` → `roomName`）。 |
| `-k` / `--keyword` | `search`：未传 `-n` 时作群名，或与 `-n` 并用作群列表过滤；`get`：**消息内容**关键词。 |
| `-l` / `--limit` | `search`：最多返回群数（默认 50）；`get`：最多消息条数（默认 500）。 |
| `-st` / `-et` | 消息时间范围（仅 `get`）。 |
| `--groups` | 群 ID 或群名，逗号分隔（提供后自动 `get`）。 |
| `--industries` | 行业 ID，逗号分隔（`get` 过滤）。 |
| `--categories` | `text`,`image`,`document`,`url`,`audio`,`video`（`get`；旧值 `documents` 兼容为 `document`）。 |
| `--tags` | 标签代码或中文（如 `路演`→`roadShow`）（`get`）。 |
| `--messages` | 群消息 `msgId`，逗号分隔（`download`；须按字符串保存，勿转 Number）。 |
| `-d` / `--download` | 下载附件开关，配合 `--messages`，等价于 `-m download`（也接受 `-d true`）。 |
| `--page-from` / `--page-size` | 分页；`page-size` 最大 50。 |
| `-od` / `--output-dir` | 结果保存目录路径（需 `GTS_SAVE_FILE=True`）。 |

> 已移除按发言人 ID（`speakerIdList`）筛选；接口不再支持该参数。

## 调用示例

```bash
# 查群 ID（默认 search）
python3 scripts/wechat_message.py -m search -n "AI学习群,投研分享群"
```

```bash
# 已知群 ID，拉消息（自动 get）
python3 scripts/wechat_message.py --groups id1,id2 -k "半导体" -st 2024-03-01 -et 2024-03-31 -l 100
```

```bash
# 筛选文档/图片/音频/视频消息
python3 scripts/wechat_message.py -m get --categories document,image,audio,video -l 50
```

```bash
# 按 msgId 下载附件（两种写法等价）
python3 scripts/wechat_message.py -m download --messages 4784255865508301077
python3 scripts/wechat_message.py -d true --messages 4784255865508301077
```

```bash
# 提供 --messages 即自动进入 download
python3 scripts/wechat_message.py --messages 4784255865508301077,4784255865508301078 -od /tmp/wechat_files
```

## 返回说明

- **成功（search）**：`workspace/gangtise/wechat_message/wechat_chatroom_*.md`（或内联展示）；消息末尾提示复制群 ID 后使用 `--groups`。
- **成功（get）**：`wechat_message_*.md`。消息行含正文、群信息、标签、文件名等；若接口返回 `quoteMsg`，另含引用消息字段。可下载类型消息会提示用 `--messages` 下载。
- **成功（download）**：附件二进制落盘到输出目录，回复中给出本地路径。
- 设置 `GTS_SAVE_FILE=True` 时落盘 md/json；股票池类 CSV 逻辑不适用本脚本。
