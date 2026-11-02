<div align="center">

# Gangtise Web

[简体中文](README.cn.md) | **English**

Research-oriented web search over the public internet, with source tiers and optional page content.

</div>

---

## What this is

`gangtise-web` is a local Agent Skill. It searches the public web for research use and returns titles, snippets, links, and source tiers. Page content is fetched only when requested. Use gangtise-file / gangtise-kb for internal research and gangtise-data for structured market data.

**Keywords**: `联网搜索`, `公开网页`, `新闻`, `政策原文`, `监管站点`, `信源分级`, `传闻核实`, `web search`

## Install

1. Download: [gangtise-web.zip](https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-web.zip)
2. Unzip to get `gangtise-web/`, copy it into your `skills/` directory
3. Follow `SKILL.md` for runtime setup (install deps if listed)

Configure `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` from the [open platform](https://open-platform.gangtise.com/), or follow the skill’s auth file instructions.

## Example prompts

- 帮我在公开网上查一下宁德时代 2026 年半年报营收和净利润，优先官方和权威媒体。
- 证监会和交易所站点上，减持新规原文是怎么说的？把正文拉下来。
- 最近一周券商合并传闻有没有官方辟谣或公司回应？

## When not to use

- 查内部研报、纪要、公告或知识库片段时，改用 gangtise-file / gangtise-kb
- 查行情、财务、估值等结构化数据时，改用 gangtise-data
- 按指标条件选股时，改用 gangtise-screener

## Docs index

| File | Contents |
|------|----------|
| [SKILL.md](SKILL.md) | Agent workflow and conventions |
| [references/web_search.md](references/web_search.md) | Parameters, fields, and error codes |
| [scripts/](scripts/) | Executable scripts / CLI |

## Version

Current version: `1.7.0` (see `SKILL.md`).
