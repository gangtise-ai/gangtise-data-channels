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

from .security import resolve_or_error
from .utils import (
    BOND_VALUATION_SHCLEARING_URL,
    add_common_args,
    build_headers,
    daily_payloads,
    default_date_range,
    describe_securities,
    error_response,
    normalize_securities_arg,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "valuation"
DEFAULT_KEYS = ["securityCode", "tradeDate", "confidenceLevel"]
CONFIDENCE_LEVELS = ("推荐", "不推荐")
DEFAULT_BACK_DAYS = 7
FALLBACK_BACK_DAYS = 30

FIELD_CN = {
    # 基础标识
    "securityCode": "债券代码",
    "tradeDate": "估值日期",
    "confidenceLevel": "可信度",
    "securityName": "债券简称",
    "exchange": "交易市场",
    # 估值属性
    "remainingTerm": "代偿期(年)",
    # 估值价格
    "dirtyPrice": "估价全价(元)",
    "accruedInterest": "应计利息(元)",
    "eodDirtyPrice": "日终估价全价(元)",
    "eodAccruedInterest": "日终应计利息(元)",
    "cleanPrice": "估价净价(元)",
    "yield": "估价收益率(%)",
    "remainingPrincipal": "剩余本金",
    # 风险指标
    "modifiedDuration": "估价修正久期",
    "convexity": "估价凸性",
    "pvbp": "估价基点价值",
    "rateDuration": "估价利率久期",
    "rateConvexity": "估价利率凸性",
    "spreadDuration": "估价利差久期",
    "spreadConvexity": "估价利差凸性",
}

DEFAULT_FIELDS = [
    "securityName",
    "remainingTerm",
    "cleanPrice",
    "dirtyPrice",
    "yield",
    "accruedInterest",
    "modifiedDuration",
    "convexity",
    "pvbp",
]


def bond_valuation_shclearing(
    securities: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    confidence_level: Optional[str] = None,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> str:
    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    if confidence_level and confidence_level not in CONFIDENCE_LEVELS:
        return error_response(METHOD_NAME, f"--confidence 仅支持 {'/'.join(CONFIDENCE_LEVELS)}", output_dir)
    fields, err = resolve_field_list(field_list, FIELD_CN, DEFAULT_KEYS, DEFAULT_FIELDS)
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    codes, abbrs, notes, err_out = resolve_or_error(securities, headers, METHOD_NAME, output_dir)
    if err_out:
        return err_out

    subject = describe_securities(codes, abbrs)
    start, end = default_date_range(start_date, end_date, back_days=DEFAULT_BACK_DAYS)
    base = {"fieldList": fields}
    if confidence_level:
        base["confidenceLevel"] = confidence_level
    fallback = None
    if not start_date and not end_date:
        fb_start, _ = default_date_range(None, None, back_days=FALLBACK_BACK_DAYS)
        fallback = (
            daily_payloads(codes, fb_start, end, base),
            f"{subject} {fb_start}~{end} 上清所估值",
            f"近 {DEFAULT_BACK_DAYS} 日无估值（可能为节假日），已放宽到近 {FALLBACK_BACK_DAYS} 日",
        )
    return run_table_query(
        url=BOND_VALUATION_SHCLEARING_URL,
        method_name=METHOD_NAME,
        module_name="bond_valuation_shclearing",
        title=f"{subject} {start}~{end} 上清所估值",
        payloads=daily_payloads(codes, start, end, base),
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
        fallback=fallback,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="上清所估值（open-fundamental / bond/valuation-shclearing）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        required=True,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径（含 security_code / 债券代码 等列）",
    )
    parser.add_argument("-sd", "--start-date", default=None, help="估值日期起始 yyyy-MM-dd；不传默认近 7 日，无数据时放宽到近 30 日")
    parser.add_argument("-ed", "--end-date", default=None, help="估值日期截止 yyyy-MM-dd；不传默认今天")
    parser.add_argument(
        "--confidence",
        default=None,
        choices=CONFIDENCE_LEVELS,
        help="估值可信度筛选；不传由接口按「推荐」处理",
    )
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回常用字段，传 all 返回全部 20 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(
        bond_valuation_shclearing(
            securities,
            start_date=args.start_date,
            end_date=args.end_date,
            confidence_level=args.confidence,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
