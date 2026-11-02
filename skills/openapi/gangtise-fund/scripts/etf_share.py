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
    FUND_ETF_SHARE_CHANGE_URL,
    add_date_args,
    add_output_arg,
    normalize_securities_arg,
    query_by_codes,
)

METHOD_NAME = "etf_share"
FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "tradeDate": "交易日",
    "shares": "份额(万份)",
    "sharesChange": "份额变动(万份)",
    "sharesChangeRate": "份额变化率(%)",
    "scale": "规模(万元)",
    "scaleChange": "规模变动(万元)",
}


def etf_share(
    securities: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> str:
    return query_by_codes(
        method_name=METHOD_NAME,
        securities=securities,
        jobs=[{
            "url": FUND_ETF_SHARE_CHANGE_URL,
            "module": "etf_share_change",
            "label": "ETF基金份额变动",
            "field_cn": FIELD_CN,
        }],
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
        default_back_days=7,
        fallback_back_days=30,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="ETF基金份额变动（open-fundamental / fund/etf-share-change）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--securities", required=True, help="ETF代码/简称/拼音，逗号分隔；亦可传 .csv 路径")
    add_date_args(parser, daily_default=True)
    add_output_arg(parser)
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(
        etf_share(
            securities,
            start_date=args.start_date,
            end_date=args.end_date,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
