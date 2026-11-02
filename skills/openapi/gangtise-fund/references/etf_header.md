# ETF 申赎基本资料（Open API · fund/etf-pcf-header）

## 简介

返回 ETF **最新交易日**的申赎参数：是否允许申赎、最小申赎单位、现金差额与现金替代比例上限。每只基金一行。试用账号与正式账号均可查全量场内基金。脚本：`scripts/etf_header.py`。

成分股清单用 `etf_components.py`，历史份额变动用 `etf_share.py`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--securities` | 是 | ETF 代码 / 简称 / 拼音，逗号分隔；亦可传 `.csv`。简称不完整时会命中多只同类 ETF，请看 `[WARNING]` 后改传准确代码 |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

没有日期参数，不能查历史某天的申赎清单。

## 字段说明

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `fundCode` | 基金代码 | |
| `fundName` | 基金简称 | |
| `fullName` | 基金全称 | |
| `tradeDate` | 交易日期 | 本次清单对应的交易日 |
| `purchaseRedemptionStatus` | 申赎状态 | 申购与赎回以 `·` 分隔，如「允许申购·允许赎回」「暂停申购·允许赎回」 |
| `minUnitNetAsset` | 最小申赎单位净值(元) | |
| `minUnitShares` | 最小申赎单位(份) | |
| `dailyPurchaseLimit` | 单日申购上限(份) | 无上限时为空 |
| `dailyRedemptionLimit` | 单日赎回上限(份) | 无上限时为空 |
| `cashBalance` | 现金差额(元) | 可为负 |
| `estimatedCash` | 预估现金(元) | 可为负 |
| `maxCashRatio` | 现金替代比例上限(%) | |
| `componentCount` | 成分股记录数 | |

## 约束与说明

- 单次最多 10000 行。
- 只适用于有申赎清单的场内 ETF。普通场外基金会提示未找到。

## 调用示例

```bash
python3 scripts/etf_header.py --securities 510300.SH
python3 scripts/etf_header.py --securities 沪深300ETF华泰柏瑞,创业板成长ETF华夏
```

## 返回说明

- **成功**：在 `workspace/gangtise/etf_header/` 下生成 `etf_pcf_header_*.csv`。
- **无数据**：提示未找到 ETF申赎基本资料。
