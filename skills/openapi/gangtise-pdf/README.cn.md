<div align="center">

# Gangtise PDF

**简体中文** | [English](README.md)

把 PDF 提交到 Gangtise 文件解析接口，并取回 Markdown 结果。

</div>

---

## 这是做什么的

`gangtise-pdf` 是一个本地 Agent Skill。上传 PDF、创建异步解析任务，任务完成后下载含图片的 Markdown。

**关键词**：`PDF 解析`、`PDF 转 Markdown`、`研报 PDF`、`公告 PDF`、`file-parse`

## 安装

1. 下载：[gangtise-pdf.zip](https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-pdf.zip)
2. 解压得到 `gangtise-pdf/`，复制到 `skills/` 目录
3. 运行环境见 `SKILL.md`（Python 3，依赖 `requests`）

在[开放平台](https://open-platform.gangtise.com/)配置 `GTS_ACCESS_KEY` / `GTS_SECRET_KEY`，或按技能内的鉴权文件说明配置。

## 你可以这样用

- 把这份研报 PDF 解析成 Markdown，图片也保留。
- 上次那个解析任务好了吗？用原来的 taskId 把结果拉下来。
- 这篇公告 PDF 转成可检索的 Markdown。

```bash
python3 scripts/pdf_parse.py --help
```

## 文档索引

| 文件 | 内容 |
|------|------|
| [SKILL.md](SKILL.md) | Agent 工作流与约定 |
| [references/pdf_parse.yaml](references/pdf_parse.yaml) | submit / result 参数 |
| [scripts/pdf_parse.py](scripts/pdf_parse.py) | 提交任务并下载结果 |

## 版本

当前版本：`0.1.0`（以 `SKILL.md` 为准）。
