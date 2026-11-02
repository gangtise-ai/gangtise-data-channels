# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/scripts/default_list.py
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

import datetime
import sys
from io import TextIOWrapper
from typing import List, Optional, Tuple

import pandas as pd

from .security import resolve_issuers_or_error, resolve_or_error
from .utils import (
    BOND_DEFAULT_LIST_URL,
    add_common_args,
    build_headers,
    default_date_range,
    describe_securities,
    error_response,
    normalize_securities_arg,
    parse_str_list,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "default_list"
DEFAULT_KEYS = ["securityCode", "defaultDate"]

FIELD_CN = {
    "securityCode": "债券代码",
    "securityName": "债券简称",
    "defaultDate": "违约日期",
    "defaultAmount": "违约金额(亿元)",
    "issuerName": "发行人",
    "defaultReason": "违约原因",
}


def _coerce_date(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    tokens = [text[:10]]
    if len(text) >= 8 and text[:8].isdigit():
        tokens.append(text[:8])
    for token in tokens:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
            try:
                return datetime.datetime.strptime(token, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return text


def _parse_iso(value: str) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _plus_years(day: datetime.date, years: int = 1) -> datetime.date:
    """自然年：2 月 29 日的下一年对应日按 2 月 28 日。"""
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, month=2, day=28)


def _year_chunks(start: datetime.date, end: datetime.date) -> List[Tuple[datetime.date, datetime.date]]:
    """拆成若干段，每段满足 end <= start.plusYears(1)，且允许恰好一年。"""
    chunks: List[Tuple[datetime.date, datetime.date]] = []
    cursor = start
    while cursor <= end:
        chunk_end = min(end, _plus_years(cursor, 1))
        chunks.append((cursor, chunk_end))
        if chunk_end >= end:
            break
        cursor = chunk_end + datetime.timedelta(days=1)
    return chunks


def _filter_by_date(df: pd.DataFrame, start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
    if df.empty or "defaultDate" not in df.columns:
        return df
    dates = pd.to_datetime(df["defaultDate"], errors="coerce")
    mask = pd.Series(True, index=df.index)
    if start_date:
        mask &= dates >= pd.to_datetime(start_date, errors="coerce")
    if end_date:
        mask &= dates <= pd.to_datetime(end_date, errors="coerce")
    return df.loc[mask].reset_index(drop=True)


def _sort_defaults(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cols = []
    ascending = []
    if "defaultDate" in df.columns:
        cols.append("defaultDate")
        ascending.append(False)
    if "securityCode" in df.columns:
        cols.append("securityCode")
        ascending.append(True)
    if not cols:
        return df
    return df.sort_values(cols, ascending=ascending, kind="stable").reset_index(drop=True)


def bond_default_list(
    securities: Optional[List[str]] = None,
    issuers: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> str:
    fields, err = resolve_field_list(field_list, FIELD_CN, DEFAULT_KEYS)
    if err:
        return error_response(METHOD_NAME, err, output_dir)

    securities = parse_str_list(securities)
    issuers = list(dict.fromkeys(parse_str_list(issuers)))
    if securities and issuers:
        return error_response(METHOD_NAME, "--securities 与 --issuers 必须且只能传入其中一个；都不传则按违约日期查全市场", output_dir)

    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)

    start_date = _coerce_date(start_date)
    end_date = _coerce_date(end_date)
    local_filter = False
    notes: List[str] = []

    if securities:
        codes, abbrs, resolve_notes, err_out = resolve_or_error(securities, headers, METHOD_NAME, output_dir)
        if err_out:
            return err_out
        notes.extend(resolve_notes or [])
        payloads = [{"securityList": codes, "fieldList": fields}]
        title = f"{describe_securities(codes, abbrs)}违约记录"
        if start_date or end_date:
            local_filter = True
            title += f"（违约日期 {start_date or '最早'}~{end_date or '最晚'}）"
            notes.append("接口不允许债券与日期同时传入，已按债券查询后在本地按违约日期过滤")
    elif issuers:
        issuers, resolve_notes, err_out = resolve_issuers_or_error(issuers, headers, METHOD_NAME, output_dir)
        if err_out:
            return err_out
        notes.extend(resolve_notes or [])
        payloads = [{"issuerNameList": [name], "fieldList": fields} for name in issuers]
        title = f"{issuers[0]}等{len(issuers)}个主体的违约记录" if len(issuers) > 1 else f"{issuers[0]}违约记录"
        notes.append("按发行人全称精确匹配，每个主体单独请求")
        if start_date or end_date:
            local_filter = True
            title += f"（违约日期 {start_date or '最早'}~{end_date or '最晚'}）"
            notes.append("接口不允许主体与日期同时传入，已按主体查询后在本地按违约日期过滤")
    else:
        start, end = default_date_range(start_date, end_date, back_days=6)
        start_d = _parse_iso(start)
        end_d = _parse_iso(end)
        if start_d and end_d and start_d > end_d:
            return error_response(METHOD_NAME, "开始日期不能晚于结束日期", output_dir)
        if start_d and end_d:
            chunks = _year_chunks(start_d, end_d)
            payloads = [
                {"startDate": lo.isoformat(), "endDate": hi.isoformat(), "fieldList": fields}
                for lo, hi in chunks
            ]
            if len(chunks) > 1:
                notes.append(f"日期区间超过 1 个自然年，已拆成 {len(chunks)} 次请求")
        else:
            payloads = [{"startDate": start, "endDate": end, "fieldList": fields}]
        title = f"{start}~{end} 违约债券"

    notes.append(f"本接口按次计费 0.4 积分/次，本次最多 {len(payloads)} 次；全部无数据的请求不计费")

    def post_process(df: pd.DataFrame) -> pd.DataFrame:
        if local_filter:
            df = _filter_by_date(df, start_date, end_date)
        return _sort_defaults(df)

    return run_table_query(
        url=BOND_DEFAULT_LIST_URL,
        method_name=METHOD_NAME,
        module_name="bond_default_list",
        title=title,
        payloads=payloads,
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
        post_process=post_process,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="违约债券列表（open-fundamental / bond/default-list）。日期、债券、发行人三选一。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        default=None,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径。与 --issuers、日期区间互斥（同时给日期时在本地过滤）",
    )
    parser.add_argument(
        "--issuers",
        default=None,
        help="发债主体全称或简称，逗号分隔。简称会先检索主体，多家全部列出；全称精确匹配。与 --securities 互斥",
    )
    parser.add_argument("-sd", "--start-date", default=None, help="违约日期起始 yyyy-MM-dd；全市场检索时不传默认近 7 日")
    parser.add_argument("-ed", "--end-date", default=None, help="违约日期截止 yyyy-MM-dd；全市场检索时不传默认今天。单次超过 1 个自然年会自动拆分")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回全部 6 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)

    print(
        bond_default_list(
            securities=securities or None,
            issuers=parse_str_list(args.issuers) or None,
            start_date=args.start_date,
            end_date=args.end_date,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
