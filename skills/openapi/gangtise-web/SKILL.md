---
name: gangtise-web
description: "对公开互联网做投研定向检索，返回经转载去重和信源分级（T0–T3）后的标题、摘要、链接，并可按需拉取网页正文。适用于最新公开新闻、政策与监管原文、指定站点检索和传闻核实。内部研报纪要用 gangtise-file / gangtise-kb，结构化行情财务用 gangtise-data。"
version: 1.7.0
author: Gangtise
metadata:
  category: openapi
  homepage: "https://open-platform.gangtise.com/"
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-web.zip"
---

# 联网搜索

## 概览

对公开互联网做投研定向检索。服务端会做转载去重、信源分级（T0–T3）、黑名单剔除和内容打标，再按信源等级、发布日期返回。用于最新公开新闻、政策原文、监管或交易所页面，以及传闻核实。

与其他技能：

- 内部研报、纪要、公告、知识库片段用 **`gangtise-file`** / **`gangtise-kb`**。
- 行情、财务、估值用 **`gangtise-data`**。
- 按指标条件选股用 **`gangtise-screener`**。

服务端**不改写**检索词。要限定站点用 `--site-list`，不要把 `site:` 写进 `-q`。

按次计费，与条数、是否拉正文无关；零结果和错误不扣积分。**零结果是正常响应**（看提示），不是失败。

`-q` 只放检索词。脚本会剥掉句首常见的「忽略以上指令」类前缀。

整体长度是可控的，调用时请不要使用 `| head -N`，输出文件地址一般在末尾。

字段含义、发布日期规则和错误码见 [references/web_search.md](./references/web_search.md)。

## 脚本

`scripts/web_search.py`

先轻搜，确认目标后再精读。默认不要开 `--include-content`。

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-q` / `--query` | 是 | 检索词，去空格后 1–200 字。 |
| `-s` / `--size` | 否 | 返回条数上限，1–20；不传则服务端默认 10。`--include-content` 时必须是 1–5。超出直接拒绝，不会自动改小。 |
| `--freshness` | 否 | `day` 近 1 日 / `week` 近 7 日 / `month` 近 30 日 / `none` 不限。不传等于不限。发布日期为空的结果在 `day` / `week` / `month` 下不会返回。 |
| `--min-tier` | 否 | 最低信源等级：`T0` 只要官方，`T1` 官方+权威媒体，`T2` 再加财经平台，`T3` 或不传表示不过滤。 |
| `--site-list` | 否 | 注册域或子域，逗号分隔，去重后最多 10 个，多个站点是**或**关系。例：`csrc.gov.cn,sse.com.cn`。不要带 `https://`、路径或端口。 |
| `--include-content` | 否 | 返回 Markdown 正文。个别页面取不到正文时该条仍在，正文为空。 |
| `--max-content-chars` | 否 | 单条正文上限，1000–20000，默认 8000。只在 `--include-content` 时生效。 |
| `-od` / `--output-dir` | 否 | 结果保存目录。仅当环境变量 `GTS_SAVE_FILE=true` 时落盘。 |
| `--json` | 否 | 输出 JSON（字段名与接口一致）。 |
| `--timeout` | 否 | HTTP 超时秒数，默认 120。 |

### 示例

轻搜：

```bash
python3 scripts/web_search.py -q "宁德时代 2026年半年报 营收 净利润" -s 5
```

定向监管与交易所，只要官方和权威媒体：

```bash
python3 scripts/web_search.py -q "减持新规" \
  --site-list "csrc.gov.cn,sse.com.cn,szse.cn" \
  --min-tier T1 -s 5
```

传闻核实，限定近一周：

```bash
python3 scripts/web_search.py -q "券商 合并 传闻 辟谣 回应" --freshness week -s 10
```

精读：先用轻搜选定站点，再用站点收束并打开正文。

```bash
python3 scripts/web_search.py -q "上市公司股东减持股份管理暂行办法" \
  --site-list csrc.gov.cn \
  --include-content --max-content-chars 6000 -s 2
```

## 怎么读结果

- 排序是信源等级从高到低（T0 在前），同一等级里发布日期新的在前，日期为空的排最后。**第一条不是最相关。**
- 「发布日期」是规则判定值，给不出就写「未能判定」。同一条里的「索引时间」是搜索索引的原样转述，政府站常常是页面生成时间，**不要把它写成发布时间**。
- 引用监管或交易所原文时，优先**没有「转载」特征**的 T0。「被替换来源」是同题转载里被换掉的低等级链接，主条才是保留下来的最高等级来源。
- 「传闻」「疑似荐股」只作线索，不要当事实。「付费墙」表示正文不完整。「免责声明」表示页面含投资建议免责声明。
- 返回 0 条时按提示放宽 `freshness`、降低 `--min-tier` 或改关键词。不要把同一次请求当成失败重试。
- 错误信息里出现 `260001` 时，检索服务暂时不可用，可以稍后重试；这次不扣积分。
