# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-screener/references/screener.md
# Regenerate: python3 scripts/generate.py
# 指标选股

## 一、使用方法

* 通过 `universe` 指定证券筛选范围，支持传入证券代码、市场板块ID，并支持多范围同时传入。
* 通过 `指标清单.md` 获取指标ID及通过 `search_indicator.py` 获取其参数，并配置到 `indicatorList`。
* 在 `expression` 中引用 `indicatorList` 定义的变量，组合筛选条件。表达式语法见【表达式说明】。

## 二、请求参数

| 参数名               | 必选 | 类型                 | 默认值 | 说明                                                                                                                            |
|:------------------|:---|:-------------------|:----|:------------------------------------------------------------------------------------------------------------------------------|
| `universe`        | 是  | **List\<String\>** | -   | 用于指定参与条件选股的范围。支持传入证券代码、市场板块ID，并支持多范围同时传入，调用时自动去重取并集。范围例如：["600519.SH","000858.SZ","1000000125"]。板块ID可以通过`search_sector.py`获取。 |
| `expression`      | 是  | **String**         | -   | 条件表达式，其中使用 `F1`、`F2` 等变量引用 `indicatorList` 中的指标配置；具体规则见下方表达式说明                                                                |
| `indicatorList`   | 是  | **List\<Object\>** | -   | 指标条件列表，不可为空                                                                                                                   |
| ↳ `field`         | 是  | **String**         | -   | 表达式变量，格式为 `F` 加正整数，例如 `F1`。同一次请求中不可重复                                                                                         |
| ↳ `indicatorCode` | 是  | **String**         | -   | 指标ID，通过`指标清单.md`获取                                                                                                            |
| ↳ `parameters`    | 是  | **List\<Object\>** | -   | 指标参数列表；指标无参数时传空数组`[]`                                                                                                         |
| ↳↳ `paramKey`     | 否  | **String**         | -   | 指标参数名，通过`search_indicator.py`获取，必须与 `paramValue` 同时提供。                                                                        |
| ↳↳ `paramValue`   | 否  | **String**         | -   | 指标参数值；当参数定义提供非空 `enumList` 时，应从中选择，否则按照参数定义的数据类型和格式填写。必须与 `paramKey` 同时提供；如需使用 `defaultValue`，应省略整个参数对象。                      |

### 请求示例（JSON）

```json
{
  "universe": [
    "000858.SZ",
    "600519.SH",
    "002594.SZ"
  ],
  "expression": "F1 >= 800 && (F2 >= 20 && F2 <= 30) && F3 contains '酒'",
  "indicatorList": [
    {
      "field": "F1",
      "indicatorCode": "qte_mkt_cptl",
      "parameters": [
        {
          "paramKey": "tradeDate",
          "paramValue": "2026-04-29"
        },
        {
          "paramKey": "currency",
          "paramValue": "DFT"
        },
        {
          "paramKey": "scale",
          "paramValue": "8"
        }
      ]
    },
    {
      "field": "F2",
      "indicatorCode": "finc_pe_ttm",
      "parameters": [
        {
          "paramKey": "tradeDate",
          "paramValue": "2026-04-29"
        }
      ]
    },
    {
      "field": "F3",
      "indicatorCode": "pty_op_scope",
      "parameters": []
    }
  ]
}
```

## 三、返回参数

### 顶层返回结构

| 参数名      | 类型          | 说明                        |
|:---------|:------------|:--------------------------|
| `code`   | **String**  | 响应码，`000000` 表示成功         |
| `msg`    | **String**  | 响应消息                      |
| `status` | **Boolean** | 请求是否成功                    |
| `data`   | **Object**  | 筛选结果对象；未筛选到证券时，各结果数组返回空数组 |

### data 结构

| 参数名                | 类型                                           | 说明                                                                                                                                                               |
|:-------------------|:---------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `securityCodeList` | **List\<String\>**                           | 证券代码（如`"000001.SZ"`）                                                                                                                                             |
| `securityNameList` | **List\<String\>**                           | 证券名称（如`"平安银行"`），数组顺序与 `securityCodeList` 一致                                                                                                                      |
| `indicatorList`    | **List\<Indicator\>**                        | 返回的指标元数据，数组顺序与 `values` 的列顺序一致                                                                                                                                   |
| ↳ `field`          | **String**                                   | 请求中定义的指标条件变量，例如 `F1`                                                                                                                                             |
| ↳ `code`           | **String**                                   | 指标ID                                                                                                                                                             |
| ↳ `name`           | **String**                                   | 指标名称                                                                                                                                                             |
| ↳ `dataType`       | **String**                                   | 指标值的数据类型，例如 `double`、`string`                                                                                                                                    |
| `values`           | **List\<List\<Number \| String \| null\>\>** | 二维指标数据矩阵。每一行对应一只证券，每一列对应一个指标；`values[i]` 对应 `securityCodeList[i]` 和 `securityNameList[i]` 表示的证券，`values[i][j]` 表示该证券的 `indicatorList[j]` 指标值；无符合条件的证券时返回空数组 `[]` |

### 返回示例（JSON）

#### 示例1：存在筛选结果

```json
{
  "code": "000000",
  "msg": "success",
  "status": true,
  "data": {
    "securityCodeList": [
      "000858.SZ",
      "600519.SH"
    ],
    "securityNameList": [
      "五粮液",
      "贵州茅台"
    ],
    "indicatorList": [
      {
        "field": "F1",
        "code": "qte_mkt_cptl",
        "name": "总市值",
        "dataType": "double"
      },
      {
        "field": "F2",
        "code": "finc_pe_ttm",
        "name": "市盈率(TTM)",
        "dataType": "double"
      },
      {
        "field": "F3",
        "code": "pty_op_scope",
        "name": "经营范围",
        "dataType": "string"
      }
    ],
    "values": [
      [
        3817.1733,
        28.4929,
        "公司主要从事白酒生产和销售。"
      ],
      [
        17546.4346,
        21.2131,
        "公司主要业务是茅台酒及系列酒的生产与销售。"
      ]
    ]
  }
}
```

#### 示例2：空筛选结果

```json
{
  "code": "000000",
  "msg": "success",
  "status": true,
  "data": {
    "securityCodeList": [],
    "securityNameList": [],
    "indicatorList": [],
    "values": []
  }
}
```

## 四、表达式说明

`expression` 用于组合指标筛选条件。表达式中的 `F1`、`F2`、`F3` 等变量，分别引用 `indicatorList` 中 `field`
相同的指标配置。系统根据变量对应的指标值计算表达式，并返回满足条件的证券。

### 1. 变量规则

- 每个变量必须在 `indicatorList` 中存在且仅存在一个对应配置；
- 变量格式为 `F` 加正整数，例如 `F1`、`F2`；
- 建议从 `F1` 开始连续编号，便于阅读和排查问题；

### 2. 支持的运算符

| 类别 | 运算符                         | 说明                                   |
|:---|:----------------------------|:-------------------------------------|
| 比较 | `==`、`>`、`<`、`>=`、`<=`、`!=` | 等于、大于、小于、大于等于、小于等于、不等于               |
| 文本 | `contains`、`notcontains`    | 包含、不包含；运算符不区分大小写，仅适用于 `string` 类型的指标 |
| 逻辑 | `&&`、`\|\|`                 | 且、或                                  |
| 分组 | `()`                        | 控制运算优先级                              |

### 3. 表达式示例

指标变量配置：

```json
[
  {
    "field": "F1",
    "indicatorCode": "qte_mkt_cptl"
  },
  {
    "field": "F2",
    "indicatorCode": "finc_pe_ttm"
  },
  {
    "field": "F3",
    "indicatorCode": "pty_op_scope"
  }
]
```

表达式：

```text
F1 >= 800 && (F2 >= 20 && F2 <= 25) && F3 contains '酒'
```

含义：

- 总市值大于等于 800；
- 市盈率（TTM）位于 20～25 区间内；
- 经营范围包含“酒”。
## 输出目录

`run` 子命令支持 `-od` / `--output-dir`：结果 CSV 保存目录路径；未指定时默认写入 gangtise 工作目录下的 `screener` 子目录。
