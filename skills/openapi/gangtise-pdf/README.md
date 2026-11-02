<div align="center">

# Gangtise PDF

[简体中文](README.cn.md) | **English**

Submit a PDF to the Gangtise file-parse API and download the Markdown result.

</div>

---

## What this is

`gangtise-pdf` is a local Agent Skill. It uploads a PDF, creates an async parse task, and downloads the Markdown (including images) when the task is ready.

**Keywords**: `PDF 解析`, `PDF 转 Markdown`, `研报 PDF`, `公告 PDF`, `file-parse`

## Install

1. Download: [gangtise-pdf.zip](https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-pdf.zip)
2. Unzip to get `gangtise-pdf/`, copy it into your `skills/` directory
3. Follow `SKILL.md` for runtime setup (Python 3 with `requests`)

Configure `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` from the [open platform](https://open-platform.gangtise.com/), or follow the skill’s auth file instructions.

## Example prompts

- 把这份研报 PDF 解析成 Markdown，图片也保留。
- 上次那个解析任务好了吗？用原来的 taskId 把结果拉下来。
- 这篇公告 PDF 转成可检索的 Markdown。

```bash
python3 scripts/pdf_parse.py --help
```

## Docs index

| File | Contents |
|------|----------|
| [SKILL.md](SKILL.md) | Agent workflow and conventions |
| [references/pdf_parse.yaml](references/pdf_parse.yaml) | Parameters for submit / result |
| [scripts/pdf_parse.py](scripts/pdf_parse.py) | Submit a task and download the result |

## Version

Current version: `0.1.0` (see `SKILL.md`).
