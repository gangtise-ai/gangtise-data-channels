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
    BOND_DAILY_QUOTE_URL,
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

METHOD_NAME = "quote"
DEFAULT_KEYS = ["securityCode", "tradeDate"]
DEFAULT_BACK_DAYS = 7
FALLBACK_BACK_DAYS = 30

FIELD_CN = {
    # 基础标识
    "securityCode": "债券代码",
    "tradeDate": "交易日期",
    "securityName": "债券简称",
    "exchange": "交易市场",
    "bondType": "债券类型",
    # 全价行情
    "dirtyPreClose": "全价昨收盘(元)",
    "dirtyOpen": "全价开盘价(元)",
    "dirtyHigh": "全价最高价(元)",
    "dirtyLow": "全价最低价(元)",
    "dirtyClose": "全价收盘价(元)",
    "dirtyChange": "全价涨跌(元)",
    "dirtyChangeRatio": "全价涨跌幅(%)",
    # 净价行情
    "cleanPreClose": "净价昨收盘(元)",
    "cleanOpen": "净价开盘价(元)",
    "cleanHigh": "净价最高价(元)",
    "cleanLow": "净价最低价(元)",
    "cleanClose": "净价收盘价(元)",
    "cleanChange": "净价涨跌(元)",
    "cleanChangeRatio": "净价涨跌幅(%)",
    # 成交与收益率
    "ytmClose": "收盘价到期收益率(%)",
    "volume": "成交量(手)",
    "turnover": "成交金额(万元)",
    "ytc": "赎回收益率(%)",
    "ytp": "回售收益率(%)",
    # 风险指标
    "duration": "久期",
    "modifiedDuration": "修正久期",
    "convexity": "凸性",
    # 票息要素
    "accruedInterest": "应计利息(元)",
    "term": "剩余期限(年)",
    "valueDate": "起息日",
    "couponRate": "票面利率(%)",
}

DEFAULT_FIELDS = [
    "securityName",
    "cleanClose",
    "cleanChangeRatio",
    "dirtyClose",
    "ytmClose",
    "volume",
    "turnover",
    "modifiedDuration",
    "accruedInterest",
]


def bond_daily_quote(
    securities: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> str:
    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    fields, err = resolve_field_list(field_list, FIELD_CN, DEFAULT_KEYS, DEFAULT_FIELDS)
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    codes, abbrs, notes, err_out = resolve_or_error(securities, headers, METHOD_NAME, output_dir)
    if err_out:
        return err_out

    subject = describe_securities(codes, abbrs)
    start, end = default_date_range(start_date, end_date, back_days=DEFAULT_BACK_DAYS)
    base = {"fieldList": fields}
    fallback = None
    if not start_date and not end_date:
        fb_start, _ = default_date_range(None, None, back_days=FALLBACK_BACK_DAYS)
        fallback = (
            daily_payloads(codes, fb_start, end, base),
            f"{subject} {fb_start}~{end} 日收盘行情",
            f"近 {DEFAULT_BACK_DAYS} 日无行情（可能为节假日），已放宽到近 {FALLBACK_BACK_DAYS} 日",
        )
    return run_table_query(
        url=BOND_DAILY_QUOTE_URL,
        method_name=METHOD_NAME,
        module_name="bond_daily_quote",
        title=f"{subject} {start}~{end} 日收盘行情",
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
        description="债券日收盘行情（交易所 + CFETS 银行间；open-quote / bond/daily-quote-exchange-cfets）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        required=True,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径（含 security_code / 债券代码 等列）",
    )
    parser.add_argument("-sd", "--start-date", default=None, help="开始日期 yyyy-MM-dd；不传默认近 7 日，无数据时放宽到近 30 日")
    parser.add_argument("-ed", "--end-date", default=None, help="结束日期 yyyy-MM-dd；不传默认今天")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回常用字段，传 all 返回全部 31 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(
        bond_daily_quote(
            securities,
            start_date=args.start_date,
            end_date=args.end_date,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
