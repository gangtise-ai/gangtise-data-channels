# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-private/references/stockpool.md
# Regenerate: python3 scripts/generate.py
# 股票池与个股笔记 API（Open API · stock-pool）

## 简介

通过 Gangtise Open API 读取与管理终端股票池，以及本人个股投资笔记。脚本 **`scripts/stockpool.py`**，所有接口通过 `-m` / `--mode` 区分。

`search` / `get` 用 `--space-type` 选择区域：

| 值 | 含义 |
|----|------|
| `1`（默认） | 个人自选股股票池，对应终端「自选股」 |
| `2` | 所属租户股票池，对应租户页签下的股票池。租户页签名称不是股票池名称 |

不传 `--space-type` 时按 `1` 处理，原有个人股票池调用不变。一次请求只查一个区域。查询证券明细时，`--space-type` 必须与 `poolId` 所属区域一致：先 `search` 拿到带 `space_type` 的记录，再用同一区域把 `pool_id` 传给 `get`。

`create` / `rename` / `delete` / `add_stock` / `delete_stock` 仍只操作个人自选股（`space_type=1`）。

个股笔记仅属于当前授权用户本人；与是否关注该证券无关，取消关注不会删除笔记。一条笔记可关联多只证券（最多 50），同一证券也可对应多条笔记。

## 模式说明

| 模式 | 接口 | 说明 |
|------|------|------|
| `search` | getPoolList | 列股票池，可 `-k` 过滤（默认）。 |
| `get` | getStockList | 按池 ID/名称或 `--all` 取证券；`search` 模式下提供 `--pool` / `--pool-file` / `--all` 时自动进入。 |
| `create` | createPool | 创建个人股票池（名称 ≤10 字符、不可重名，每用户最多 30 个）。 |
| `rename` | updatePool | 重命名一个个人股票池。 |
| `delete` | deletePool | 批量删除个人股票池（不影响个股投资笔记）。 |
| `add_stock` | addStock | 向一个个人股票池批量添加证券（单池上限 10000 只）。 |
| `delete_stock` | deleteStock | 从一个个人股票池批量移除证券。 |
| `search_note` | getNoteList | 按证券、笔记 ID 或全部笔记查询本人个股笔记。 |
| `add_note` | addNote | 新增一条笔记，关联 1～50 只证券。 |
| `update_note` | updateNote | 按笔记 ID 替换正文（不改关联证券）。 |
| `delete_note` | deleteNote | 按笔记 ID 批量删除（须 `--yes`）。 |

> `create` / `rename` / `delete` / `add_stock` / `delete_stock` / `add_note` / `update_note` / `delete_note` 会修改用户数据，执行前须与用户确认。

## 参数

| 参数 | 适用模式 | 说明 |
|------|----------|------|
| `-k` / `--keyword` | search | 股票池名称或 ID 子串过滤。 |
| `-l` / `--limit` | search / search_note | 股票池列出上限（默认 100）；笔记模式下为自动翻页累计条数上限。 |
| `--space-type` | search / get | `1` 个人自选股（默认），`2` 所属租户。也可传「个人」「租户」。 |
| `--pool` | get / delete / rename / add_stock / delete_stock | 池 ID 或名称，逗号分隔。仅字母数字与逗号时视为 ID；否则在**当前 space_type** 内按名称**唯一完全匹配**解析，否则返回候选。rename / add_stock / delete_stock 只能指定一个。 |
| `--pool-file` | 同上 | CSV 含 `pool_id` 或 `poolId`，等价于 `--pool`。若含 `space_type` 列且未传 `--space-type`，沿用文件中的区域；文件里出现多个区域时报错。显式传入的 `--space-type` 必须与文件一致。 |
| `--all` | get | 使用 `poolIdList=["all"]` 取**所选区域**内全部可见池的去重证券。 |
| `--pool-name` | create / rename | 新股票池名称。 |
| `--securities` | add_stock / delete_stock / search_note / add_note | 证券代码，逗号分隔，**须带市场后缀**：A 股 `600519.SH`、港股 `00700.HK`（5 位）、美股 `AAPL.O`。脚本会自动转大写并去重。`search_note` 也可单独传 `all` 查本人全部笔记。 |
| `--securities-file` | 同上 | CSV 含 `security_code` 列，等价于 `--securities`。 |
| `--note-ids` | search_note / update_note / delete_note | 笔记 ID，逗号分隔；与 `--securities` / `--all-notes` 互斥。`update_note` 仅一个。 |
| `--note-content` | add_note / update_note | 笔记正文，不可空白，最长 10000 字符。 |
| `--all-notes` | search_note | 查询本人全部笔记（`securityList=["all"]`）。 |
| `--page-from` | search_note | 起始偏移量（不是页码），默认 0。 |
| `--page-size` | search_note | 单页条数，1～50，默认 20；配合 `-l` 可自动翻页取更多。 |
| `--yes` / `--confirm` | delete / delete_note | 确认删除；不可恢复，须先取得用户同意。 |
| `-od` / `--output-dir` | 全部 | 结果保存目录路径；文件名自动生成。 |

## 调用示例

```bash
python3 scripts/stockpool.py -m search -k 自选股 -l 20
python3 scripts/stockpool.py --pool 808477293,808477294
python3 scripts/stockpool.py --all
python3 scripts/stockpool.py -m search --space-type 2
python3 scripts/stockpool.py --space-type 2 --pool 908477301,908477302
python3 scripts/stockpool.py --space-type 租户 --all
python3 scripts/stockpool.py -m create --pool-name 核心持仓
python3 scripts/stockpool.py -m rename --pool 808477293 --pool-name 核心持仓
python3 scripts/stockpool.py -m delete --pool 808477293,808477294
python3 scripts/stockpool.py -m add_stock --pool 核心持仓 --securities 688106.SH,600111.SH,00700.HK
python3 scripts/stockpool.py -m delete_stock --pool 808477293 --securities 600111.SH
```

**个股笔记：**

```bash
python3 scripts/stockpool.py -m search_note --all-notes --page-size 50
python3 scripts/stockpool.py -m search_note --securities 688106.SH,600111.SH
python3 scripts/stockpool.py -m search_note --note-ids 1737,1738
python3 scripts/stockpool.py -m add_note --securities 688106.SH,600111.SH --note-content "上游材料涨价叠加国产替代。"
python3 scripts/stockpool.py -m update_note --note-ids 1835 --note-content "最新季报订单加速落地。"
python3 scripts/stockpool.py -m delete_note --note-ids 1835,1836 --yes
```

## 返回说明

- **search / get**：CSV 写入 `workspace/gangtise/stockpool/`（`stockpool_pools_*.csv`、`stockpool_stocks_*.csv`）。股票池列 `pool_id`, `pool_name`, `space_type`；证券列 `security_code`, `security_abbr`（多池已按完整代码去重，不按池分组）。`search` 成功时提示可通过 `--pool-file` 读取 CSV 再 `get`，并沿用其中的 `space_type`。
- **search_note**：CSV 写入同目录 `stockpool_notes_*.csv`，列 `stock_note_id`, `security_list`, `content`, `create_time`, `update_time`。`security_list` 为该笔记完整关联证券（逗号拼接）。
- **空结果**：有查询权限但该区域没有可见股票池，或匹配到的池里没有证券，接口成功且 `data` 为 `[]`（不是 `130001`）。脚本据此提示当前区域没有可见池或池内无证券。`["all"]` 不会退化为无股票池条件的全量证券查询。笔记无命中时提示未找到符合条件的个股笔记。
- **数量上限**：单次最多返回 10000 只证券（合并去重后截取，不是每池各 10000）。没有截断标记；返回恰好 10000 只时不能认定已取全，重复请求也不能翻页。需要降低截断影响时，先取池列表再逐池查询。
- **未匹配的池 ID**：不存在、不属于所选区域或无权访问的 ID 会被忽略。至少匹配到一个可访问池时返回这些池的证券；全部未匹配时接口返回 HTTP 403、`999004`（股票池不存在或不可访问），不区分具体原因。
- **管理操作**：直接返回结果文本。批量接口（delete / add_stock / delete_stock / delete_note）逐条列出成功项与失败原因；接口外层成功但全部失败时按失败返回。`delete_note` 对不存在或不属于本人的 ID 按幂等成功处理。
- **笔记约束**：`securityList` 与 `stockNoteIdList` 互斥；`all` 仅用于查询且须单独使用。关联证券在新增后不可通过 `update_note` 调整，需另建笔记再删旧笔记。不支持申万行业指数（`.SWI`）。
- **常见错误码**：`100005` space_type 不是 1/2；`999004` 无租户股票池查询权限，或指定 ID 在所选区域均不可访问；`999014` 开发账号所属租户失效；`230003` 股票池数量超限、`230006` 名称重复、`230007` 名称超长；`120001` 证券代码无效；`130002` 笔记不存在或无权操作。

## 与 gangtise-data 衔接

将 `stockpool_stocks_*.csv` 路径直接传给 `gangtise-data` 的 `--securities`（自动读 `security_code` 列）拉行情、财务等。
