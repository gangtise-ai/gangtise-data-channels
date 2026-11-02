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

import pandas as pd

from .security import resolve_or_error
from .utils import (
    BOND_ANNOUNCEMENT_URL,
    add_common_args,
    build_headers,
    default_date_range,
    describe_securities,
    error_response,
    format_response,
    normalize_securities_arg,
    post_bond_table,
    resolve_field_list,
    to_display_df,
)

METHOD_NAME = "announcement"
DEFAULT_KEYS = ["announcementDate", "securityCode"]
MAX_PAGE_SIZE = 200

FIELD_CN = {
    "announcementDate": "公告日期",
    "securityCode": "债券代码",
    "announcementTitle": "公告标题",
    "securityName": "债券简称",
    "categoryLevel1": "一级公告分类",
    "categoryLevel2": "二级公告分类",
    "categoryLevel3": "三级公告分类",
}


def _filter_by_date(df: pd.DataFrame, start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
    dates = pd.to_datetime(df["announcementDate"], errors="coerce")
    mask = pd.Series(True, index=df.index)
    if start_date:
        mask &= dates >= pd.to_datetime(start_date, errors="coerce")
    if end_date:
        mask &= dates <= pd.to_datetime(end_date, errors="coerce")
    return df[mask].reset_index(drop=True)


def bond_announcement(
    securities: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_no: int = 1,
    page_size: int = 50,
    max_pages: int = 1,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> str:
    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    if page_no < 1 or not 1 <= page_size <= MAX_PAGE_SIZE or max_pages < 1:
        return error_response(METHOD_NAME, f"分页参数非法：--page-no ≥ 1，--page-size 取 1~{MAX_PAGE_SIZE}，--max-pages ≥ 1", output_dir)
    fields, err = resolve_field_list(field_list, FIELD_CN, DEFAULT_KEYS)
    if err:
        return error_response(METHOD_NAME, err, output_dir)

    notes: List[str] = []
    local_date_filter = False
    if securities:
        codes, abbrs, notes, err_out = resolve_or_error(securities, headers, METHOD_NAME, output_dir)
        if err_out:
            return err_out
        base_payload = {"securityList": codes}
        title = f"{describe_securities(codes, abbrs)}债券公告"
        if start_date or end_date:
            # 接口不允许 securityList 与日期区间同时传入，日期改为本地过滤
            local_date_filter = True
            title += f"（公告日期 {start_date or '最早'}~{end_date or '最晚'}）"
    else:
        start, end = default_date_range(start_date, end_date, back_days=6)
        base_payload = {"startDate": start, "endDate": end}
        title = f"{start}~{end} 债券公告"

    frames: List[pd.DataFrame] = []
    last_page = page_no
    reached_end = False
    page_error = None
    for current in range(page_no, page_no + max_pages):
        payload = {**base_payload, "pageNo": current, "pageSize": page_size, "fieldList": fields}
        df, err = post_bond_table(BOND_ANNOUNCEMENT_URL, payload, headers)
        if err:
            if not frames:
                return error_response(METHOD_NAME, f"{title}查询失败：{err}", output_dir)
            page_error = (current, err)
            break
        last_page = current
        if df.empty:
            reached_end = True
            break
        frames.append(df)
        if len(df) < page_size:
            reached_end = True
            break

    if not frames:
        return error_response(METHOD_NAME, f"未找到{title}", output_dir)
    data = pd.concat(frames, ignore_index=True)
    if local_date_filter:
        data = _filter_by_date(data, start_date, end_date)
        if data.empty:
            hint = "" if reached_end else f"，日期为本地过滤，可能在后续页，可调大 --max-pages 或用 --page-no {last_page + 1} 继续"
            return error_response(METHOD_NAME, f"未找到{title}（已取第 {page_no}~{last_page} 页{hint}）", output_dir)

    if page_error:
        failed, err = page_error
        notes.append(f"[WARNING]第 {failed} 页查询失败（{err}），已返回第 {page_no}~{last_page} 页；可稍后用 --page-no {failed} 续拉")
    elif reached_end:
        notes.append(f"已取第 {page_no}~{last_page} 页，已到末页")
    else:
        notes.append(f"已取第 {page_no}~{last_page} 页，可能还有更多，可用 --page-no {last_page + 1} 继续翻页或调大 --max-pages")

    message = f"已找到{title}"
    for note in notes:
        message += f"\n{note}"
    return format_response(
        {
            "state": "success",
            "message": message,
            "data": [{"data": to_display_df(data, FIELD_CN).to_dict(orient="records"), "module": "bond_announcement", "type": "data"}],
        },
        METHOD_NAME,
        output_dir=output_dir,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="债券公告检索（open-fundamental / bond/announcement）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        default=None,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径。不传则按公告日期区间检索全市场",
    )
    parser.add_argument("-sd", "--start-date", default=None, help="公告日期起始 yyyy-MM-dd；全市场检索时不传默认近 7 日")
    parser.add_argument("-ed", "--end-date", default=None, help="公告日期截止 yyyy-MM-dd；全市场检索时不传默认今天")
    parser.add_argument("--page-no", type=int, default=1, help="起始页码，从 1 开始")
    parser.add_argument("--page-size", type=int, default=50, help=f"每页条数，1~{MAX_PAGE_SIZE}")
    parser.add_argument("--max-pages", type=int, default=1, help="从起始页起最多连续拉取的页数，遇到空页或不足一页即停止")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回全部 7 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)

    print(
        bond_announcement(
            securities=securities or None,
            start_date=args.start_date,
            end_date=args.end_date,
            page_no=args.page_no,
            page_size=args.page_size,
            max_pages=args.max_pages,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
