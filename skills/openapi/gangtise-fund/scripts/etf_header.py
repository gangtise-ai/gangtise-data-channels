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
    FUND_ETF_PCF_HEADER_URL,
    add_output_arg,
    normalize_securities_arg,
    query_by_codes,
)

METHOD_NAME = "etf_header"
FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "fullName": "基金全称",
    "tradeDate": "交易日期",
    "purchaseRedemptionStatus": "申赎状态",
    "minUnitNetAsset": "最小申赎单位净值(元)",
    "minUnitShares": "最小申赎单位(份)",
    "dailyPurchaseLimit": "单日申购上限(份)",
    "dailyRedemptionLimit": "单日赎回上限(份)",
    "cashBalance": "现金差额(元)",
    "estimatedCash": "预估现金(元)",
    "maxCashRatio": "现金替代比例上限(%)",
    "componentCount": "成分股记录数",
}


def etf_header(securities: List[str], output_dir: Optional[str] = None) -> str:
    return query_by_codes(
        method_name=METHOD_NAME,
        securities=securities,
        jobs=[{
            "url": FUND_ETF_PCF_HEADER_URL,
            "module": "etf_pcf_header",
            "label": "ETF申赎基本资料",
            "field_cn": FIELD_CN,
        }],
        output_dir=output_dir,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="ETF申赎基本资料，返回最新交易日（open-fundamental / fund/etf-pcf-header）",
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

    print(etf_header(securities, output_dir=args.output_dir or None))


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
