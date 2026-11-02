# AI 云盘 API（Open API · drive）

## 简介

脚本 **`scripts/private_cloud.py`** 对接 Gangtise 终端 **AI 云盘**，所有接口通过 `-m` / `--mode` 区分。`search` 列表结果**不包含**对话、AI 速记、AI 翻译文件夹中的文件。仅可操作当前用户有权访问的**我的云盘**（spaceType=1）与**租户云盘**（spaceType=2）。

## 模式（`-m` / `--mode`）

| 模式 | 接口 | 说明 |
|------|------|------|
| `search` | getList | 检索文件 → `private_cloud_list_*.csv`（默认）。 |
| `get` | download/file | 按 `--files` / `--files-file` 下载文件。 |
| `folder_list` | getFolderList | 浏览 `--parent-id` 下的直接子文件夹与文件。 |
| `upload` | uploadFile | 上传本地文件（单个 ≤100MB）。 |
| `create_folder` | createFolder | 新建文件夹。 |
| `rename` | rename | 重命名文件（`--files`）或文件夹（`--folder-id`）。 |
| `move_file` | moveFile | 批量移动文件，不能跨空间。 |
| `move_folder` | moveFolder | 移动文件夹，不能跨空间、不能移入自身或子孙文件夹。 |
| `copy` | copy | 跨空间复制文件（批量）或文件夹（单个），仅支持 我的云盘 ↔ 租户云盘。 |
| `delete_file` | deleteFile | 批量删除文件。 |
| `delete_folder` | deleteFolder | 删除文件夹，**级联删除其内全部内容且不可恢复**。 |

**自动路由**：`search` 模式下提供 `--files` 或 `--files-file` 时自动进入 `get`。

**文件解析**：`--files` 仅含字母数字与逗号时视为 ID；含中文等则按标题检索，**唯一完全匹配**时解析为 ID，否则返回候选列表（适用于 get / rename / move_file / copy / delete_file）。

> `upload`、`rename`、`move_*`、`copy`、`delete_*` 会修改用户云盘，执行前须与用户确认；删除操作尤其需要确认目标 ID。

## 参数

| 参数 | 适用模式 | 说明 |
|------|----------|------|
| `-k` / `--keyword` | search | 文件标题关键词。 |
| `-st` / `-et` | search | 文件**创建时间**（`yyyy-MM-dd` 可自动补全）。 |
| `--file-type-list` | search | `document` `image` `media` `article` `other`，或中文（文档、图片、音视频等）。 |
| `--space-type-list` | search | `1` 我的云盘、`2` 租户云盘（可传中文），逗号分隔。 |
| `-l` / `--limit` | search | 列表条数上限（默认 100）。 |
| `--files` | get / rename / move_file / copy / delete_file | 文件 ID 或标题，逗号分隔。 |
| `--files-file` | 同上 | CSV 含 `file_id` 列，等价于 `--files`。 |
| `--space-type` | folder_list / upload / create_folder | 单个区域 `1` / `2`（或中文），默认 `1`。 |
| `--parent-id` | folder_list / create_folder | 父文件夹 ID，`root` 或不传为根目录。 |
| `--folder-id` | upload / rename / move_folder / copy / delete_folder | upload 时为目标文件夹；其余为源文件夹。 |
| `--target-folder-id` | move_file / move_folder / copy | 目标（父）文件夹 ID，`root` 为根目录；copy 时须位于源所在空间的**另一空间**。 |
| `--target-type` | rename / copy | `file` \| `folder`；不传时按是否提供 `--files` / `--folder-id` 自动判断。 |
| `--name` | create_folder / rename / upload | 文件夹名 / 新名称 / 上传文件名（仅单文件），≤200 字符。 |
| `--file-path` | upload | 本地文件路径，可空格分隔多个。 |
| `-od` / `--output-dir` | 全部 | 结果保存目录路径；文件名自动生成。 |

## 调用示例

```bash
python3 scripts/private_cloud.py -m search -k "部门文档" --file-type-list document -l 30
python3 scripts/private_cloud.py --files 49412
python3 scripts/private_cloud.py -m folder_list --space-type 1 --parent-id root
python3 scripts/private_cloud.py -m upload --file-path /abs/path/报告.pdf --space-type 1 --folder-id 101
python3 scripts/private_cloud.py -m create_folder --name 2026Q3 --space-type 1 --parent-id 101
python3 scripts/private_cloud.py -m rename --files 49412 --name 核心持仓梳理.pdf
python3 scripts/private_cloud.py -m rename --folder-id 103 --name 2026三季报
python3 scripts/private_cloud.py -m move_file --files 49412,43319 --target-folder-id 101
python3 scripts/private_cloud.py -m move_folder --folder-id 103 --target-folder-id 102
python3 scripts/private_cloud.py -m copy --files 49412,43319 --target-folder-id 201
python3 scripts/private_cloud.py -m copy --folder-id 201 --target-folder-id root
python3 scripts/private_cloud.py -m delete_file --files 49412,43319
python3 scripts/private_cloud.py -m delete_folder --folder-id 103
```

## 返回说明

- **search CSV**：`file_id`, `title`, `create_time`, `space_type`, `file_size`, `url`, `uploader`；消息末尾提示可通过 `--files-file` 读取 CSV 再下载。
- **get**：文件以云盘**原始标题**命名下载到工作目录（或 `-od` 目录），同名不同内容时自动加 `(1)` 后缀；`GTS_SAVE_FILE=True` 时另存 `private_cloud_content_*.md` 汇总。对话/速记/翻译目录下的文件或刚上传几秒内的文件无法查到标题，会退回服务端文件名。
- **folder_list CSV**：子文件夹 `folder_id`, `parent_id`, `folder_name`, `space_type`, `create_time`；文件 `file_id`, `title`, `file_size`, `create_time`。
- **管理操作**：直接返回结果文本；批量接口（move_file / copy 文件 / delete_file）逐条列出成功与失败原因（如 `文件不存在`、`空间不一致`），全部失败时按失败返回。
- 路径：`workspace/gangtise/private_cloud/`
