# 板块成分股 API（Open API · sectors/search & sectors/constituents）

## 简介

通过 Gangtise Open API 查询**板块成分股**，脚本 **`scripts/block_constituents.py`**。

串联两个接口：

| 接口 | 说明 |
|------|------|
| `sectors/search` | 按关键词搜索板块 ID（名称/拼音/首字母） |
| `sectors/constituents` | 按 sectorId 查询该板块全量成分股 |

与 `concept.py`（题材指数画像 + 分组成分股 Markdown）不同，本脚本面向**行业/概念/指数等板块树**下的证券代码列表，输出 **CSV** 宽表。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-k` / `--keyword` | 否* | 板块搜索关键词，支持中文名称、拼音/首字母。 |
| `-s` / `--sector-id` | 否* | 板块 ID（如 `121000130`），已知 ID 时可跳过搜索直接查成分股。 |
| `-t` / `--top` | 否 | 关键词搜索返回条数上限，默认 **10**，最大 **10**（仅 `-k` 时生效）。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

\* 须且仅能二选一：`-k` 或 `-s`。

## 关键词解析逻辑

使用 `-k` 时，脚本调用 `sectors/search`，按内部匹配度筛选候选：

- **唯一候选**（筛选后仅 1 条）：自动取该 sectorId 并拉取成分股，结果落盘 CSV。
- **多个候选**：在终端**打印**全部候选（sectorId、名称、hierarchy），**不落盘**；请确认后改用 `-s` 指定 sectorId。
- **无候选**：返回错误说明。

## 约束与说明

- `sectors/search` 返回的是**搜索匹配结果**，非全量板块列表；脚本按匹配度排序后筛选。
- `sectors/constituents` 返回指定板块的**全量**成分股（gtsCode / gtsName）。
- 板块 ID 亦可通过 open **查询板块 ID** 接口单独获取；本脚本在 `-k` 路径下已内置搜索。

## 调用示例

```bash
# 按板块名称搜索并自动取成分股（唯一高置信匹配时）
python3 "scripts/block_constituents.py" -k 机器人
```

```bash
# 按拼音首字母搜索
python3 "scripts/block_constituents.py" -k bdt -t 5
```

```bash
# 已知 sectorId，直接查成分股
python3 "scripts/block_constituents.py" -s 121000130
```

```bash
# 多个候选时终端会列出选项，确认后指定 ID
python3 "scripts/block_constituents.py" -s 100800109
```

## 返回说明

- **成功（单候选或 `-s`）**：在 `workspace/gangtise/block_constituents/` 下生成 **`block_constituents_*.csv`**。
- **多候选（`-k`）**：终端输出候选列表字符串，**不生成文件**。
- **失败**：如未配置授权、无匹配板块、板块无成分股等。

## 返回数据示例（CSV 列）

| sector_id | sector_name | hierarchy | security_code | security_name |
|-----------|-------------|-----------|---------------|---------------|
| 121000130 | 机器人 | 中国内地股票-概念类-机器人 | 300024.SZ | 机器人 |
| 121000130 | 机器人 | 中国内地股票-概念类-机器人 | 002747.SZ | 埃斯顿 |

（使用 `-s` 且未经过搜索时，`sector_name` / `hierarchy` 可能为空。）
