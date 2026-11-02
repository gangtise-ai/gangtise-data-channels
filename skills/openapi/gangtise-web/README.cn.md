<div align="center">

# Gangtise Web

**简体中文** | [English](README.md)

对公开互联网做投研定向检索，返回经转载去重和信源分级后的网页结果，并可按需拉取正文。

</div>

---

## 这是做什么的

`gangtise-web` 是一个本地 Agent Skill。对公开互联网做投研定向检索，返回标题、摘要、链接和信源等级；需要原文时再拉取网页正文。内部研报、纪要、公告用 gangtise-file / gangtise-kb，行情财务用 gangtise-data。

**关键词**：`联网搜索`、`公开网页`、`新闻`、`政策原文`、`监管站点`、`信源分级`、`传闻核实`、`web search`

## 安装

1. 下载：[gangtise-web.zip](https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-web.zip)
2. 解压得到 `gangtise-web/`，复制到你的 `skills/` 目录
3. 按 `SKILL.md` 说明配置运行环境（如有依赖再安装）

需配置 `GTS_ACCESS_KEY` / `GTS_SECRET_KEY`（开放平台获取），或按 skill 说明写入鉴权文件。

## 你可以这样用

- 帮我在公开网上查一下宁德时代 2026 年半年报营收和净利润，优先官方和权威媒体。
- 证监会和交易所站点上，减持新规原文是怎么说的？把正文拉下来。
- 最近一周券商合并传闻有没有官方辟谣或公司回应？

## 不适合的场景

- 查内部研报、纪要、公告或知识库片段时，改用 gangtise-file / gangtise-kb
- 查行情、财务、估值等结构化数据时，改用 gangtise-data
- 按指标条件选股时，改用 gangtise-screener

## 文档索引

| 文件 | 内容 |
|------|------|
| [SKILL.md](SKILL.md) | Agent 工作流与约定（给 AI 用） |
| [references/web_search.md](references/web_search.md) | 参数、字段与错误码 |
| [scripts/](scripts/) | 可执行脚本 / CLI |

## 版本

当前版本：`1.7.0`（以 `SKILL.md` 为准）。
