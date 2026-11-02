# 自选股股票池 API（Open API · stock-pool）

## 简介

通过 Gangtise Open API 读取与管理终端**自选股股票池**。脚本 **`scripts/stockpool.py`**，所有接口通过 `-m` / `--mode` 区分。仅可操作当前用户本人的股票池。

## 模式说明

| 模式 | 接口 | 说明 |
|------|------|------|
| `search` | getPoolList | 列股票池，可 `-k` 过滤（默认）。 |
| `get` | getStockList | 按池 ID/名称或 `--all` 取证券；`search` 模式下提供 `--pool` / `--pool-file` / `--all` 时自动进入。 |
| `create` | createPool | 创建股票池（名称 ≤10 字符、不可重名，每用户最多 30 个）。 |
| `rename` | updatePool | 重命名一个股票池。 |
| `delete` | deletePool | 批量删除股票池（不影响个股投资笔记）。 |
| `add_stock` | addStock | 向一个股票池批量添加证券（单池上限 10000 只）。 |
| `delete_stock` | deleteStock | 从一个股票池批量移除证券。 |

> `create` / `rename` / `delete` / `add_stock` / `delete_stock` 会修改用户股票池，执行前须与用户确认。

## 参数

| 参数 | 适用模式 | 说明 |
|------|----------|------|
| `-k` / `--keyword` | search | 股票池名称或 ID 子串过滤。 |
| `-l` / `--limit` | search | 列出/过滤的股票池数量上限（默认 100）。 |
| `--pool` | get / delete / rename / add_stock / delete_stock | 池 ID 或名称，逗号分隔。仅字母数字与逗号时视为 ID；否则按名称**唯一完全匹配**解析，否则返回候选。rename / add_stock / delete_stock 只能指定一个。 |
| `--pool-file` | 同上 | CSV 含 `pool_id` 或 `poolId`，等价于 `--pool`。 |
| `--all` | get | 使用 `poolIdList=["all"]` 取全部池去重证券。 |
| `--pool-name` | create / rename | 新股票池名称。 |
| `--securities` | add_stock / delete_stock | 证券代码，逗号分隔，**须带市场后缀**：A 股 `600519.SH`、港股 `00700.HK`（5 位）、美股 `AAPL.O`。脚本会自动转大写并去重。 |
| `--securities-file` | add_stock / delete_stock | CSV 含 `security_code` 列，等价于 `--securities`。 |
| `-od` / `--output-dir` | 全部 | 结果保存目录路径；文件名自动生成。 |

## 调用示例

```bash
python3 scripts/stockpool.py -m search -k 自选股 -l 20
python3 scripts/stockpool.py --pool 808477293,808477294
python3 scripts/stockpool.py --all
python3 scripts/stockpool.py -m create --pool-name 核心持仓
python3 scripts/stockpool.py -m rename --pool 808477293 --pool-name 核心持仓
python3 scripts/stockpool.py -m delete --pool 808477293,808477294
python3 scripts/stockpool.py -m add_stock --pool 核心持仓 --securities 688106.SH,600111.SH,00700.HK
python3 scripts/stockpool.py -m delete_stock --pool 808477293 --securities 600111.SH
```

## 返回说明

- **search / get**：CSV 写入 `workspace/gangtise/stockpool/`（`stockpool_pools_*.csv`、`stockpool_stocks_*.csv`）；列 `pool_id`, `pool_name`；`security_code`, `security_abbr`（多池已按代码去重）。`search` 成功时提示可通过 `--pool-file` 读取 CSV 再 `get`。
- **管理操作**：直接返回结果文本。批量接口（delete / add_stock / delete_stock）逐条列出成功项与失败原因（如 `证券代码不存在`、`证券数量已达上限`）；接口外层成功但全部失败时按失败返回。
- **常见错误码**：`230003` 股票池数量超限、`230006` 名称重复、`230007` 名称超长、`130002` 股票池不存在。

## 与 gangtise-data 衔接

将 `stockpool_stocks_*.csv` 路径直接传给 `gangtise-data` 的 `--securities`（自动读 `security_code` 列）拉行情、财务等。
