# 基金经理信息（Open API · fund/manager-info）

## 简介

按姓名精确查询基金经理档案：学历、从业年限、在管规模与产品数、当前公司与简介。试用账号与正式账号均可查全量在册经理。脚本：`scripts/manager.py`。

本脚本**不**走基金代码解析。查某只基金的历任经理用 `profile.py --type manager`。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--names` | 是 | 基金经理姓名，逗号分隔，精确匹配。如 `张坤,葛兰` |
| `-od` / `--output-dir` | 否 | 结果保存目录 |

## 字段说明

| 字段 | 中文列名 | 说明 |
|------|----------|------|
| `managerName` | 基金经理 | |
| `education` | 学历 | |
| `gender` | 性别 | |
| `nationality` | 国籍 | |
| `birthYear` | 出生年份 | 未披露为空 |
| `careerStartDate` | 证券从业日期 | `yyyy-MM-dd` |
| `workingYears` | 从业年限(年) | |
| `managedFundScale` | 在管规模(亿元) | 在管产品总规模 |
| `managedFundCount` | 在管产品数(只) | |
| `historyFundCount` | 历任管理基金数(只) | |
| `historyCompanyCount` | 历任基金公司数(家) | |
| `currentCompany` | 当前公司 | 同名经理用此列区分 |
| `currentCompanyYears` | 当前公司任职年限(年) | |
| `introduction` | 简介 | 长文本，预览会截断，全文在 CSV |

## 约束与说明

- 单次最多 10000 行。
- 姓名必须与库内姓名一致。简称、拼音不会自动检索。同名时全部返回。

## 调用示例

```bash
python3 scripts/manager.py --names 张坤
python3 scripts/manager.py --names 张坤,葛兰
```

## 返回说明

- **成功**：在 `workspace/gangtise/manager/` 下生成 `manager_info_*.csv`。
- **无数据**：提示未找到基金经理信息。先确认姓名是否完整。
