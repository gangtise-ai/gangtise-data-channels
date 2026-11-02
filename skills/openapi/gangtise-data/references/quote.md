# 行情数据 API（Open API · 日K / 分钟K / 实时快照）

## 简介

通过 Gangtise Open API 查询 A/港/美股与**交易所/概念/行业指数**的**历史日 K**、**分钟 K** 与**实时快照**，脚本 **`scripts/quote.py`**。

日 K 与分钟 K、实时快照统一走 **`kline/daily`**、**`kline/minute`**、**`quote/realtime`** 接口，均支持 **A 股、港股、美股**个股及 **交易所指数（沪深京）、概念指数（`.GT`）、行业指数（中信 `.CI` / 申万 `.SWI`）**。分钟 K 不含港股/美股。

日 K 默认**前复权**：优先使用日 K 接口内嵌的 `adjustFactor` 字段；缺失时回退调用 **`/adjustFactor`**（`QUOTE_ADJUST_FACTOR_URL`）获取复权因子，在脚本侧计算**开高低收**及**昨收、涨跌额、涨跌幅**的复权序列（列名带 `（前复权）` 或 `（后复权）`）。**不复权**时不请求复权因子，输出原始 OHLC 与涨跌字段。指数无复权因子，保持原价量列。

复权因子接口按自然月拆分请求并合并，以降低单次超过 10000 行的风险；若仍不足以覆盖全部分页场景，请缩短日期区间分批拉取。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-sd` / `--start-date` | 否 | 开始日期 `yyyy-MM-dd`。未指定时：**非全市场**默认近 **7** 日（至 `-ed`）；**`--all-market`** 且与 `-ed` 均未指定时默认当天并向前回退取数。 |
| `-ed` / `--end-date` | 否 | 结束日期 `yyyy-MM-dd`。未指定时默认**今天**。 |
| `--securities` | 否* | 逗号分隔的证券名称/代码/拼音；亦可传 `.csv` 路径（须存在且后缀为 `.csv`，读 `security_code` / `code` / `代码` / `security_abbr` 列）。与 `--all-market` **二选一**。 |
| `--all-market` | 否 | 全市场：不带值默认 **A 股(cn)**；可指定 `cn` / `hk` / `us`，逗号分隔（如 `cn,hk`）。未指定 `-sd/-ed` 时默认查**当天**，无数据则逐日向前回退（最多 **15** 天）。 |
| `--limit` | 否 | 单次 K 线请求最大行数，默认 `5000`，上限 `10000`。复权因子请求同样受上限约束（脚本按月拆分）。 |
| `--type` | 否 | `daily`（默认，日K，A/港/美股及指数）、`minute`（分钟K，A 股及交易所/概念/行业指数，不支持 `--all-market`）或 `snap`（实时快照，A/港/美股及指数）。 |
| `--adjust` | 否 | **仅日 K**。`forward` / `qfq` / `前复权`（默认）、`backward` / `hfq` / `后复权`、`none` / `raw` / `不复权`。分钟 K 忽略复权（勿显式传非 `none`）。 |
| `-od` / `--output-dir` | 否 | 结果保存目录路径，建议使用绝对路径；文件名自动生成。 |

\* 指定证券时须提供 `--securities`；全市场时使用 `--all-market` 且不要同时传证券列表。

## 约束与说明

- **前复权**：\(P'(t) = P(t) \times F(t)/F(t_{\text{latest}})\)，其中 \(t_{\text{latest}}\) 为本次结果中该证券**最后交易日**，\(F\) 优先取日 K 内嵌 `adjustFactor`，缺失时回退独立 **adjustFactor** 接口。
- **后复权**：\(P'(t) = P(t) \times F(t)/F(t_{\text{earliest}})\)，其中 \(t_{\text{earliest}}\) 为本次结果中该证券**首个交易日**。
- 若部分证券缺少有效复权因子，这些标的会**单独按不复权**输出（另表或同次结果中的不复权块），其余证券仍正常复权；不再因个别标的缺因子而整批失败。
- **不复权**：原始行情字段名仍为 `开盘价`、`收盘价` 等（导出列名以脚本为准）。
- `minute` 类型支持 `securities` 并发拉取并聚合（A 股个股及交易所/概念/行业指数）；不支持全市场拉取；不支持复权。
- **指数**：交易所指数（沪深京）、概念指数、行业指数在日 K / 分钟 K / 实时快照中均可查询；指数无复权因子，成交量/成交额通常为 0。
- **实时快照（snap / 日 K 当日补全）**：若返回行情中价格列**全为 0 或 NaN**（如美股未开市、接口侧返回占位零值），脚本视作无效并丢弃；全市场未指定日期时会继续向前回退历史日 K。日 K 一旦用 snap 补全当日，收盘价列名为 **`收盘价/最新价`**（盘中为最新价，已收盘则为当日收盘价），不再单独叫 `收盘价`。snap 来源行会额外输出 **`实时/历史`**（导出列 `realtime_or_hist`）：交易日等于该市场「今天」时为 `实时`（可能为盘中），否则为 `历史`；**美股「今天」按美东时区**，A/港按本地日历。日 K 中非 snap 的历史行同列值为 `历史`。

## 调用示例

```bash
python3 scripts/quote.py --securities 贵州茅台 -sd 2026-04-01 -ed 2026-04-23
```

```bash
python3 scripts/quote.py --securities 600519.SH -sd 2026-04-01 -ed 2026-04-23
```

```bash
python3 scripts/quote.py --securities 600519.SH -sd 2026-04-01 -ed 2026-04-23 --adjust backward
```

```bash
python3 scripts/quote.py --securities ./codes.csv --limit 8000
```

```bash
python3 scripts/quote.py --type minute --securities 600519.SH,000001.SZ -sd "2026-04-23 10:00:00" -ed "2026-04-23 15:00:00"
```

```bash
python3 scripts/quote.py --securities 000001.SH,121000130.GT,CI005001.CI -sd 2026-04-01 -ed 2026-04-23 --adjust none
```

```bash
python3 scripts/quote.py --type snap --securities 600519.SH,000001.SH,121000130.GT
```

```bash
python3 scripts/quote.py --all-market -l 10
```

```bash
python3 scripts/quote.py --all-market hk -l 10 -sd 2026-07-03 -ed 2026-07-03
```

```bash
python3 scripts/quote.py --all-market cn,hk,us --type snap
```

## 返回说明

- **成功**：在 `workspace/gangtise/quote/` 下生成 **`quote_*.csv`**，返回文案含路径与样例。
- **失败**：如授权失败、无数据、参数错误、复权因子缺失等。

## 返回数据示例（CSV 列）

当前实现会在写出前**去掉 `security_abbr` 列**，仅保留 **`security_code`** 等（以实际脚本为准）。

日 K **前复权**时典型列为：`开盘价（前复权）`、`最高价（前复权）`、`最低价（前复权）`、`收盘价（前复权）`、`昨收价（前复权）`、`涨跌额（前复权）`、`涨跌幅（前复权）`、`成交量`、`成交额` 等。
