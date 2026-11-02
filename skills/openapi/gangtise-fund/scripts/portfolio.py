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
    FUND_BOND_PORTFOLIO_URL,
    FUND_FUND_PORTFOLIO_URL,
    FUND_STOCK_PORTFOLIO_URL,
    add_date_args,
    add_output_arg,
    error_response,
    normalize_securities_arg,
    parse_choice,
    parse_types,
    query_by_codes,
)

METHOD_NAME = "portfolio"
TYPE_ORDER = ("stock", "bond", "fund")
TYPE_ALIAS = {
    "stock": "stock",
    "股票": "stock",
    "持股": "stock",
    "持股明细": "stock",
    "bond": "bond",
    "债券": "bond",
    "持债": "bond",
    "持债明细": "bond",
    "fund": "fund",
    "基金": "fund",
    "持基": "fund",
    "持基明细": "fund",
}
POSITION_ALIAS = {
    "top": "top",
    "重仓": "top",
    "重仓股票": "top",
    "all": "all",
    "全部": "all",
    "全部持股": "all",
}

STOCK_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "reportDate": "报告期",
    "stockName": "股票简称",
    "holdingQuantity": "持股数量(万股)",
    "pctToFloatShares": "占流通股比例(%)",
    "holdingValue": "持仓市值(万元)",
    "pctToNav": "占资产净值比(%)",
    "pctToNavChg": "占资产净值比变化(%)",
}
BOND_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "reportDate": "报告期",
    "bondName": "债券简称",
    "holdingQuantity": "持仓量(万张)",
    "holdingValue": "持仓市值(万元)",
    "pctToNav": "占资产净值比(%)",
}
FUND_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "reportDate": "报告期",
    "holdingFundName": "持仓基金简称",
    "holdingValue": "持仓市值(万元)",
    "pctToNav": "占资产净值比(%)",
}


def fund_portfolio(
    securities: List[str],
    query_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    position_type: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    types, err = parse_types(query_type, TYPE_ALIAS, TYPE_ORDER, ("stock",))
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    position_type, err = parse_choice(position_type, POSITION_ALIAS, "持仓类型")
    if err:
        return error_response(METHOD_NAME, err, output_dir)

    notes: List[str] = []
    if position_type and "stock" not in types:
        notes.append("[WARNING] --position-type 仅对持股明细生效，本次未使用")

    jobs = []
    if "stock" in types:
        extra = {"positionType": position_type} if position_type else {}
        jobs.append({
            "url": FUND_STOCK_PORTFOLIO_URL,
            "module": "stock_portfolio",
            "label": "持股明细",
            "field_cn": STOCK_FIELD_CN,
            "extra": extra,
        })
    if "bond" in types:
        jobs.append({
            "url": FUND_BOND_PORTFOLIO_URL,
            "module": "bond_portfolio",
            "label": "持债明细",
            "field_cn": BOND_FIELD_CN,
        })
    if "fund" in types:
        jobs.append({
            "url": FUND_FUND_PORTFOLIO_URL,
            "module": "fund_portfolio",
            "label": "持基明细",
            "field_cn": FUND_FIELD_CN,
        })
    return query_by_codes(
        method_name=METHOD_NAME,
        securities=securities,
        jobs=jobs,
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
        extra_notes=notes,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="基金持仓明细：持股（默认）/ 持债 / 持基",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--securities", required=True, help="基金代码/简称/拼音，逗号分隔；亦可传 .csv 路径")
    parser.add_argument(
        "--type",
        "-t",
        default="stock",
        help="stock(持股明细) / bond(持债明细) / fund(持基明细)，逗号分隔；all 全部",
    )
    add_date_args(parser, daily_default=False)
    parser.add_argument(
        "--position-type",
        default=None,
        help="仅持股明细：top(重仓，接口默认) / all(全部持股，仅半年报与年报)",
    )
    add_output_arg(parser)
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    position, err = parse_choice(args.position_type, POSITION_ALIAS, "持仓类型")
    if err:
        parser.error(err)

    print(
        fund_portfolio(
            securities,
            query_type=args.type,
            start_date=args.start_date,
            end_date=args.end_date,
            position_type=position,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
