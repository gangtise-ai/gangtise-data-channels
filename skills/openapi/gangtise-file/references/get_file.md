# 文件下载

## 简介

用于根据文件ID和文件类型下载文件。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-id` / `--file-id` | 是 | 文件ID。 |
| `-type` / `--file-type` | 是 | 文件类型（须与检索结果「类型」一致）。可选值：`研究报告`、`外资研报`、`公司公告`、`港股公告`、`美股公告`、`会议纪要`、`帕米尔专家纪要`、`外资独立观点`、`公众号`、`财报日历`。 |
| `-dt` / `--download-type` | 否 | 下载格式。常见：`pdf` / `markdown`（研报、公告）；`original` / `html`（帕米尔）；`txt` / `html`（公众号）；`zh_pdf` / `zh_markdown`（外资研报）；`html` / `html_zh`（外资独立观点）。 |
| `-od` / `--output-dir` | 否 | 输出目录路径；若不指定，则默认保存在 gangtise 工作目录下的 `files`（自动编号）；与环境变量 GTS_SAVE_FILE 无关，单独生效。|

## 调用示例

```bash
python3 scripts/get_file.py --file-id 1234567890 --file-type "研究报告"
```

指定输出路径（可选）：
```bash
python3 scripts/get_file.py --file-id 1234567890 --file-type "研究报告" -od /tmp/out
```

## 返回说明

- **成功**：文件保存到指定目录或默认工作目录下的 `files`，返回说明文字中含保存路径。
- **失败**：返回错误信息（如「获取文件失败：...」）。

`file_type` 须与检索结果中的类型一致，枚举如下：

- 研究报告、外资研报
- 公司公告、港股公告、美股公告
- 会议纪要、帕米尔专家纪要
- 外资独立观点、公众号、财报日历

财报日历下载示例（仅「已发布」条目有原文件；`file-id` 为 `performanceReportId`）：

```bash
python3 scripts/get_file.py --file-id 33366856 --file-type "财报日历"
```

帕米尔专家纪要下载示例（`-dt` 可选 `original` / `html`）：

```bash
python3 scripts/get_file.py --file-id 5551234 --file-type "帕米尔专家纪要" -dt html
```
