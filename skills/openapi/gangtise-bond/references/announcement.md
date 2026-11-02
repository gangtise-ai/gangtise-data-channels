# 债券公告（Open API · bond/announcement）

## 简介

检索债券公告（标题、公告日期、公告类型、原文链接等）。两种检索方式：按债券（`--securities`）或按公告日期区间（全市场）。接口分页且不返回总数。脚本：`scripts/announcement.py`。

数据范围：

- **试用账号**与**正式账号**均支持查询全市场数据，覆盖上交所（`.SH`）、深交所（`.SZ`）、北交所（`.BJ`）、银行间（`.IB`）。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 否 | 同其他脚本；传入时按债券检索 |
| `-sd` / `--start-date` | 否 | 公告日期起始；全市场检索时不传默认近 7 日 |
| `-ed` / `--end-date` | 否 | 公告日期截止；全市场检索时不传默认今天 |
| `--page-no` | 否 | 起始页码，默认 1 |
| `--page-size` | 否 | 每页条数 1~200，默认 50 |
| `--max-pages` | 否 | 从起始页起最多连续拉取的页数，默认 1；遇到空页或不足一页即停 |
| `--field-list` | 否 | 字段英文名或中文名，逗号分隔；传 `all` 返回全部字段。字段不在下表时直接报错并列出可选字段 |
| `-od` / `--output-dir` | 否 | 结果保存目录，建议绝对路径；文件名自动生成 |

## 字段说明

不传 `--field-list` 返回全部字段；查询键字段始终返回。

| 字段 | 中文列名 | 默认 | 说明 |
|------|----------|------|------|
| `announcementDate` | 公告日期 | 始终 | 公告日期，格式 `yyyy-MM-dd` |
| `securityCode` | 债券代码 | 始终 | 公告对应的债券代码 |
| `announcementTitle` | 公告标题 | ✓ | 公告标题 |
| `securityName` | 债券简称 | ✓ | 债券简称 |
| `categoryLevel1` | 一级公告分类 | ✓ | 一级公告分类 |
| `categoryLevel2` | 二级公告分类 | ✓ | 二级公告分类 |
| `categoryLevel3` | 三级公告分类 | ✓ | 三级公告分类 |

## 约束与说明

- 同时传 `--securities` 与日期时，按债券检索，日期**在本地过滤**，只作用于已拉取的页；需要更早的公告请调大 `--max-pages`。
- 可能还有更多页时，输出会提示下一页的 `--page-no`。

## 调用示例

**按债券：**

```bash
python3 scripts/announcement.py --securities H1万科04 --page-size 50
```

**全市场某日：**

```bash
python3 scripts/announcement.py -sd 2026-09-30 -ed 2026-09-30 --page-size 200 --max-pages 5
```

## 返回说明

- **成功**：在 `workspace/gangtise/announcement/` 下生成 `bond_*.csv`（列名为中文），回复中附 Markdown 预览与文件路径。
- **无数据**：全部查询键均无数据时提示未找到。
- **失败**：授权失败、债券无法解析、字段名非法、超出上限等，返回错误说明与处理建议。
