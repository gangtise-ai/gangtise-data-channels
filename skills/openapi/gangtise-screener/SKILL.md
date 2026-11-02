---
name: gangtise-screener
description: 条件选股。把口语化的选股需求（板块范围 + 指标条件）翻译成 Gangtise 指标选股 HTTP 请求并给出命中名单。触发词：选股 / 筛股 / 条件选股 / 帮我筛 / 找出…的股票 / 哪些股票…、以及任何「在某板块里按指标筛」的提问。不适用于单只股票的取数（走 gangtise-data 的 financial/quote 等）、排名类需求（screener 只过滤不排序）。
version: 1.7.0
author: Gangtise
metadata:
  category: openapi
  homepage: "https://open-platform.gangtise.com/"
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-screener.zip"
---

# Gangtise 条件选股

本技能**自包含**：板块/证券搜索、交易日查询、指标解析与选股均在本目录 `scripts/` 内完成，**不依赖** `gangtise-data`。

整体长度是可控的，调用时请不要使用 `| head -N`，输出文件地址一般在末尾。

## 推荐调用（自动串联）

参考 `gangtise-data` 的 `company_indicator.py`：传入范围说法 + 指标说法 + 表达式，脚本自动完成剥壳 → 搜板块/证券 → 解析指标 → 补 `tradeDate`/`reportDate`/`scale` → 选股。

```bash
S=<skill目录>/scripts
# 写法一：表达式直接用指标名（推荐，-i 可省略）
python3 $S/screener.py run \
  -u "白酒板块" \
  -e "ROE > 15 && 总市值 > 500 && 业务范围 contains \"白酒\"" \
  -p '{"总市值":{"scale":"8"}}'

# 写法二：F1/F2 + 显式 -i
python3 $S/screener.py run \
  -u "白酒板块" \
  -i "ROE,总市值,地址,上市时间" \
  -e "F1 > 15 && F2 > 500 && F3 contains \"上海市\" && F4 >= \"20260101\"" \
  -p '{"F2":{"scale":"8"}}'
```

| 参数 | 说明 |
| :-- | :-- |
| `-u` / `--universe` | 可选，默认全A；板块名/别名/sectorId/证券代码，**可重复或逗号分隔**；亦可传 `.csv` 路径（读 `code` / `security_code` / `代码` 列） |
| `-e` / `--expression` | **必填**；数值比较如 `"ROE > 15 && 总市值 > 500"`；文本包含须给字符串加引号，如 `"经营范围 contains \"白酒\""`（亦支持 `总市值 > 500亿`） |
| `-i` / `--indicators` | 可选；不传则从 `-e` 左侧自动抽指标说法 |
| `-p` / `--params` | 参数覆盖 JSON；键可用指标说法 / `F2` / 编码，如 `{"总市值":{"scale":"亿"}}` |
| `--trade-date` | 覆盖行情类 `tradeDate`（默认脚本查最近交易日） |
| `--report-date` | 覆盖财报类 `reportDate`（默认最近已披露**年报**） |
| `--dry-run` | 只构造预览，不发起实际选股请求 |
| `--json` | 输出原始 JSON（默认 Markdown） |

指标歧义（`ambiguous` / `weak` / `not_found`）或范围不唯一时，脚本 **blocked** 并返回候选，**不发起实际请求**。确认后改用更精确说法，或直接传 `sectorId` / 指标编码重试。

`run` / `resolve-*` **默认输出 Markdown**。调试需要原始结构时加 `--json`。

### 完整示例

用户：「白酒板块 ROE 大于 15% 且市值超过 500 亿」

```bash
python3 $S/screener.py run \
  -u "白酒板块" \
  -e "ROE > 15 && 总市值 > 500亿"
```

脚本会：解析「白酒」→ 中信白酒板块 ID；从表达式抽出 ROE / 总市值并解析编码；`500亿` → 阈值 500 + scale=8；再调用选股 API。

### 多选证券

多个证券代码取并集，两种写法等价：

```bash
# 重复传 -u
python3 $S/screener.py run \
  -u 600519.SH -u 000858.SZ -u 000568.SZ \
  -e "ROE > 15"

# 逗号分隔（中英文逗号均可）
python3 $S/screener.py run \
  -u "600519.SH,000858.SZ,000568.SZ" \
  -e "ROE > 15"
```

也可混用板块与个股：`-u "白酒板块" -u 600519.SH`。

### 从 CSV 读证券名单

`-u` 传入 `.csv` 路径时，自动读取表头中的 `code` / `security_code` / `代码` 列（优先顺序从前到后，大小写不敏感），作为选股范围：

```bash
# pool.csv 示例表头：code,name  或  security_code,security_name
python3 $S/screener.py run \
  -u ./pool.csv \
  -e "ROE > 15 && 总市值 > 100亿"

# 可与其它 -u 并用（CSV 代码 ∪ 板块）
python3 $S/screener.py run \
  -u ./pool.csv -u "港股通" \
  -e "总市值 > 50亿"
```

本技能选股结果落盘 CSV 的「代码」列也可直接回灌：`-u workspace/gangtise/screener/screener_*.csv`。

## 执行流程（模型侧）

| 步骤 | 执行方 | 内容 |
| :-- | :-- | :-- |
| ① 抽取 | 模型 | 读懂问题 → 范围说法 + 条件表达式（指标名或 F1…）+ 量纲 |
| ② 术语规范化 | 模型 | 口语/同音 → 财务术语（见下方）；口径词与限定词原样保留 |
| ③ 执行 | 脚本 | `screener.py run -e …`（`-u` 可省略，默认全A）。**仅此步在通过校验后发起实际选股请求** |

歧义或失败时再用调试子命令拆开查：

```bash
python3 $S/screener.py resolve-universe "白酒板块"
python3 $S/screener.py resolve-indicator "单季度归母净利润同比" "ROE"
python3 $S/universe_strip.py "白酒板块"   # 仅剥壳
```

## ① 抽取

- **universe 说法**：板块/市场名（如「白酒板块」「港股通」「全A」）；多个证券代码；或 `.csv` 路径（`code` / `security_code` / `代码` 列）
- **条件表达式**：优先写指标名，如 `"ROE > 15 && 总市值 > 500"`；也可用 `F1/F2` + `-i`
- **量纲**：写进阈值后缀（`500亿`）或 `-p` 的 `scale`
- **逻辑 / 运算符**：见下方「表达式运算符」

### 表达式运算符

| 类别 | 运算符 | 说明 |
| :-- | :-- | :-- |
| 比较 | `==`、`>`、`<`、`>=`、`<=`、`!=` | 等于、大于、小于、大于等于、小于等于、不等于 |
| 文本 | `contains`、`notcontains` | 包含、不包含；仅适用于 `string` 类型指标（如经营范围、证券简称、所属概念） |
| 逻辑 | `&&`、`\|\|` | 且、或 |
| 分组 | `()` | 控制优先级 |

**文本匹配必须给字符串加引号**（`"…"` 或 `'…'`），否则 API 报表达式语法错误：

```bash
# 正确
python3 $S/screener.py run -e "经营范围 contains \"白酒\""
python3 $S/screener.py run -e "所属概念 contains '半导体'"

# 错误（缺引号）
python3 $S/screener.py run -e "经营范围 contains 白酒"
```

脚本会把双引号规范成 API 常用的单引号形式（如 `F1 contains '白酒'`），但**调用时仍须写出引号**。

## 术语规范化（写入 `-e` / `-i` 之前）

脚本按关键词检索指标库，**只认财务术语**。三类必须处理：

| 类型 | 用户会说 | 写进 `-i` 的 |
| :-- | :-- | :-- |
| 语音 / 同音误识别 | 市盈利 · 净资产收益绿 · 总市直 | 市盈率 · 净资产收益率 · 总市值 |
| 口语、疑问句式 | 贵不贵 · 赚不赚钱 · 涨了多少 | 市盈率 · 销售净利率 · 涨跌幅 |
| 近义但非术语 | 分红比率 · 净利同比增长 | 股利支付率 · 归母净利润同比 |

**只换词、不换语义**：口径词（单季 / TTM / 同比）与限定词（归母 / 扣非 / 每股）必须原样保留。

### 常见错漏

- **口径叠加不能丢**：「单季度归母净利润同比」= 单季 + 归母 + 同比
- **多条件要拆干净**：「营收超 50 亿且净利率高于 20%」→ `-i "营业收入,销售净利率"` 两条
- **「或者」是 `||`**
- **`contains` 漏引号**：必须写 `contains "白酒"` / `contains '白酒'`，不能写 `contains 白酒`
- **排名类不要硬塞**：「市值最大的 20 只」screener 做不到，见「能力边界」

## 参数自动补全规则

脚本根据指标 `parameterList` 自动填写（可用 `--trade-date` / `--report-date` / `-p` 覆盖）：

| 参数情况 | 行为 |
| :-- | :-- |
| 含 `tradeDate` | 填最近交易日；`mgn_*` 填上一交易日 |
| 含 `reportDate` | 填最近已披露**年报**（非最近一期） |
| `scale` | 仅当 `-p` 提供时写入；`亿`→`8`，`万`→`4` |
| 无日期参数（`pty_*` / `scr_*`） | `parameters` 不含 tradeDate |
| 其他必填且有 defaultValue | 用默认值；无默认则需 `-p` 显式给 |

**传了 scale 后阈值用对应量纲**：scale=8 时「市值超 500 亿」写 `F2 > 500`。比率类不要加 scale。

## 高级：手写 payload

仍支持直接喂 API 体（调试或特殊参数时）：

```bash
echo '<payload json>' | python3 $S/screener.py run -
```

payload 格式见 `references/screener.md`。

## 结果解读

**占位值陷阱**：EDE 取不到数时多数指标返回 `null`（比较运算会跳过），
但个别指标返回 `0`（最常见的是 `is_dnrpnp` 扣非归母净利润），`0` 会照常参与比较。
空集时先排查这一项。

呈现规范：

1. 先复述口径：范围（板块名 + ID）、每个条件的指标全名与口径、日期 / 报告期
2. 正文展示前 3 + 后 3 行样例；完整命中名单落盘 CSV，路径在输出末尾（`workspace/gangtise/screener/screener_*.csv`）
3. 空集 → 按 `references/troubleshooting.md` 的顺序排查后再下结论

## 能力边界

- **排名 / TopN**：screener 只过滤不排序。「市值最大的 20 只」需先条件筛出候选，再本地排序
- **跨指标算术**：表达式只支持「变量 比较 常量」，不支持 `F1/F2`
- **指数成分股范围**（沪深300 / 中证500 / 上证50…）：通过板块搜索解析为指数成份类 sectorId，见 `references/universe.md`
- **单证券取数**：请使用独立的 `gangtise-data` 技能（非本技能依赖）

## 参考

- `references/universe.md` — 范围解析规则、常用板块 ID、指数成分股范围
- `references/indicator.md` — 口径消歧、参数与量纲、平台未提供的指标清单
- `references/troubleshooting.md` — 错误码、空集排查
- `references/screener.md` — 指标选股 API 完整规范
