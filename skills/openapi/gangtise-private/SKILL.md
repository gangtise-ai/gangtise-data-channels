---
name: gangtise-private
description: 通过 Gangtise Open API 读取终端个人私有数据（个人自选股与所属租户股票池、个股投资笔记、微信群消息、我的会议、录音速记、AI云盘等），结果可落盘 CSV/md，便于衔接 gangtise-data、gangtise-file 等技能。仅可访问当前授权用户有权查看的数据。
version: 1.8.0
author: Gangtise
metadata:
  category: openapi
  homepage: "https://open-platform.gangtise.com/"
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-private.zip"
---

# 个人数据检索

## 概览

| 脚本 | 能力 |
|------|------|
| `scripts/stockpool.py` | 个人自选股与所属租户股票池：列表 + 池内证券（`search` / `get`，`--space-type` 1/2），创建/重命名/删除池、添加/移除证券（仅个人池），以及个股笔记（`search_note` / `add_note` / `update_note` / `delete_note`） |
| `scripts/wechat_message.py` | 微信群消息：`search` / `get` |
| `scripts/private_meeting.py` | 我的会议：列表 + 下载 ASR/速记，`search` / `get` |
| `scripts/private_record.py` | 录音速记：列表 + 下载原始/ASR/速记，`search` / `get` |
| `scripts/private_cloud.py` | AI 云盘：列表 + 下载（`search` / `get`），浏览文件夹、上传、新建文件夹、重命名、移动、复制、删除（`folder_list` / `upload` / `create_folder` / `rename` / `move_file` / `move_folder` / `copy` / `delete_file` / `delete_folder`） |

结果由 `scripts/utils.py` 的 `format_response` 写入 `workspace/gangtise/` 下对应子目录：

- **股票池**：始终保存 **CSV**（`stockpool/`）。
- **群消息**：默认在回复中展示摘要；设置环境变量 **`GTS_SAVE_FILE=True`** 时另存 **md/json**（`wechat_message/`），与 `gangtise-file` 行为一致。

**与其它技能**：股票池导出的 `security_code` → `gangtise-data`；群消息为终端私有线索，与 `gangtise-file`（公开文件库）互补。

调用各脚本前，请阅读 **[references](./references/)** 中的参数说明。

整体长度是可控的，调用时请不要使用 `| head -N`，输出文件地址一般在末尾。

## 模式说明（通用）

各脚本 `-m` 均支持 **`search`**（默认）与 **`get`**；`stockpool.py` 与 `private_cloud.py` 另有管理类模式（见各自 reference）：

| 模式 | 说明 |
|------|------|
| `search` | 检索列表（股票池/群/会议/录音/云盘文件） |
| `get` | 按 ID 取明细或下载内容 |

> 管理类模式（创建、重命名、上传、移动、复制、删除等）会修改用户数据，执行前须与用户确认。

**自动路由**：提供 get 专用参数时自动进入 `get`，无需显式 `-m get`。参数值仅含字母、数字与逗号时视为 ID 直接 `get`；含中文等则先 `search`，**唯一完全匹配**时自动 `get`：

| 脚本 | 自动 get 条件 |
|------|---------------|
| stockpool | `--pool`、`--pool-file`、`--all` |
| wechat_message | `--groups` 或 `-m get` |
| private_meeting | `--conference`、`--conference-file` |
| private_record | `--record`、`--record-file` |
| private_cloud | `--files`、`--files-file` |

`search` 成功时会在消息末尾提示如何通过 ID / ID 文件进入 `get`。

## 使用说明

### 1. 股票池

基于 **getPoolList** / **getStockList** / **getNoteList** 等。`--space-type` 默认 `1`（个人自选股）；`2` 为所属租户股票池。查询证券明细时须与股票池 ID 使用同一区域。创建、重命名、删除、加减证券仍只针对个人池。个股笔记仅本人可见，与是否关注无关。

```bash
python3 scripts/stockpool.py -m search
```

```bash
python3 scripts/stockpool.py -m search -k 自选股 -l 20
```

```bash
python3 scripts/stockpool.py --pool 808477293,808477294
```

```bash
python3 scripts/stockpool.py --all
```

```bash
python3 scripts/stockpool.py -m search --space-type 2
python3 scripts/stockpool.py --space-type 2 --pool 908477301,908477302
python3 scripts/stockpool.py --space-type 2 --all
```

```bash
python3 scripts/stockpool.py -m create --pool-name 核心持仓
python3 scripts/stockpool.py -m add_stock --pool 核心持仓 --securities 688106.SH,00700.HK
```

```bash
python3 scripts/stockpool.py -m search_note --all-notes
python3 scripts/stockpool.py -m add_note --securities 688106.SH --note-content "跟踪订单落地节奏"
python3 scripts/stockpool.py -m update_note --note-ids 1835 --note-content "季报确认加速"
python3 scripts/stockpool.py -m delete_note --note-ids 1835 --yes
```

详见 [股票池调用指导](./references/stockpool.md)。

### 2. 微信群消息

需已绑定并激活**群消息助理**且助理在群内：

```bash
python3 scripts/wechat_message.py -m search -n "AI学习群,投研分享群"
```

```bash
python3 scripts/wechat_message.py -m get -k "半导体" -st 2026-03-01 -et 2026-03-31 -l 100
```

```bash
python3 scripts/wechat_message.py --groups YOUR_GROUP_ID -k "AI应用" -st 2026-03-01 -et 2026-03-31 -l 100
```

落盘（可选）：`export GTS_SAVE_FILE=True` 后，结果写入 `workspace/gangtise/wechat_message/`。

详见 [微信消息调用指导](./references/wechat_message.md)。

### 3. 我的会议

会议助理录制列表与内容下载：

```bash
python3 scripts/private_meeting.py -m search -k "AI" -st 2024-03-01 -et 2024-03-31 -l 30
```

```bash
python3 scripts/private_meeting.py --conference 4444816 --content-type summary
```

```bash
python3 scripts/private_meeting.py -m search -k "业绩" --category-list earningsCall -l 10
```

详见 [我的会议调用指导](./references/private_meeting.md)。

### 4. 录音速记（`private_record.py`）

终端录音速记资产：

```bash
python3 scripts/private_record.py -m search -k "晨会" -st 2024-04-01 -et 2024-04-30 -l 30
```

```bash
python3 scripts/private_record.py --record 49412 --content-type summary
```

详见 [录音速记调用指导](./references/private_record.md)。

### 5. AI 云盘（`private_cloud.py`）

终端 AI 云盘文件（不含对话/速记/翻译目录）：

```bash
python3 scripts/private_cloud.py -m search -k "部门文档" --file-type-list document -l 30
```

```bash
python3 scripts/private_cloud.py --files 49412
```

```bash
python3 scripts/private_cloud.py -m folder_list --space-type 1 --parent-id root
python3 scripts/private_cloud.py -m upload --file-path /abs/path/报告.pdf --folder-id 101
```

详见 [AI云盘调用指导](./references/private_cloud.md)。

## 与 gangtise-data 衔接示例

```bash
python3 scripts/stockpool.py --all
python3 ../gangtise-data/scripts/quote.py \
  --securities workspace/gangtise/stockpool/stockpool_stocks_1.csv \
  -sd 2026-01-01 -ed 2026-05-18
```
