# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/scripts/etf_components.py
# Regenerate: python3 scripts/generate.py
if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

import os
import sys
from io import TextIOWrapper
from typing import List, Optional

from .utils import (
    FUND_ETF_PCF_COMPONENTS_URL,
    add_output_arg,
    normalize_securities_arg,
    query_by_codes,
)

METHOD_NAME = "etf_components"
FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "fullName": "基金全称",
    "tradeDate": "交易日期",
    "serialNumber": "成分序号",
    "componentCode": "成分代码",
    "componentName": "成分名称",
    "close": "收盘价(元)",
    "pctChange": "涨跌幅(%)",
    "pctWeight": "市值占比(%)",
    "purchaseQuantity": "申购数量(股)",
    "cashSubstituteFlag": "现金替代标志",
    "purchasePremiumRatio": "申购现金替代溢价比例(%)",
    "redemptionPremiumRatio": "赎回现金替代溢价比例(%)",
    "fixedSubstituteAmount": "固定替代金额(元)",
    "purchaseSubstituteAmount": "申购替代金额(元)",
    "redemptionSubstituteAmount": "赎回替代金额(元)",
}


def etf_components(securities: List[str], output_dir: Optional[str] = None) -> str:
    return query_by_codes(
        method_name=METHOD_NAME,
        securities=securities,
        jobs=[{
            "url": FUND_ETF_PCF_COMPONENTS_URL,
            "module": "etf_pcf_components",
            "label": "ETF申赎成分股",
            "field_cn": FIELD_CN,
        }],
        output_dir=output_dir,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="ETF申购赎回成分股，返回最新交易日（open-fundamental / fund/etf-pcf-components）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--securities", required=True, help="ETF代码/简称/拼音，逗号分隔；亦可传 .csv 路径")
    add_output_arg(parser)
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(etf_components(securities, output_dir=args.output_dir or None))


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
