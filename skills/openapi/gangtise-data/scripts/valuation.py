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
from concurrent.futures import as_completed
from datetime import date, timedelta
from io import TextIOWrapper
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from .gts_runtime import ThreadPoolExecutor
from .utils import (
    get_authorization_token,
    get_headers_extra,
    VALUATION_URL,
    dedupe_resolved,
    format_response,
    parse_str_list,
    normalize_securities_arg)
from .gts_runtime import ApiError, StructuralError, request_json, zip_field_rows

# 查询键全部无数据：按空结果处理，不算失败
NO_DATA_CODE = "130001"

from .security import batch_security_search, resolved_code_abbr_map
from .gts_auth import authorized_request, get_authorization_headers

# 与 open 接口文档一致；并发拉取后按 backend valuation 的列语义组装
VALUATION_INDICATORS: List[str] = ["peTtm", "psTtm", "pbMrq", "peg", "pcfTtm", "em"]

INDICATOR_CN: Dict[str, str] = {
    "peTtm": "市盈率TTM",
    "psTtm": "市销率TTM",
    "pbMrq": "市净率MRQ",
    "peg": "PEG",
    "pcfTtm": "市现率TTM",
    "em": "企业倍数",
}

# 与 backend 中 abs(range_year)=3 时「在N年中所处分位」一致
QUANTILE_YEAR_LABEL = 1

# 未传起止日期时：先查当天；无有效数据则向前回退至多 LOOKBACK_DAYS 天（含当天）
LOOKBACK_DAYS = 7

_FIELD_LIST = ["value", "percentileRank"]


def _is_valid_metric_value(value: object) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return True


def _day_has_valid_metrics(cols: Dict[str, object]) -> bool:
    return any(_is_valid_metric_value(v) for v in cols.values())


def _date_map_has_valid(merged_by_date: Dict[str, Dict[str, object]]) -> bool:
    return any(_day_has_valid_metrics(cols) for cols in merged_by_date.values())


def _keep_latest_valid_day(
    merged_by_date: Dict[str, Dict[str, object]],
) -> Dict[str, Dict[str, object]]:
    for d in sorted(merged_by_date.keys(), reverse=True):
        if _day_has_valid_metrics(merged_by_date[d]):
            return {d: merged_by_date[d]}
    return {}


def _parse_valuation_block(block: object, indicator: str) -> Tuple[Dict[str, Dict[str, object]], int]:
    """将估值分析接口 data 转为 ({日期字符串: {列名: 值}}, 返回行数)；行与表头不等宽时抛 StructuralError。"""
    if not isinstance(block, dict):
        return {}, 0
    field_list = block.get("fieldList") or []
    rows = block.get("list") or []
    if not field_list or not rows:
        return {}, 0
    records = zip_field_rows(field_list, rows)
    for name in ("tradeDate", "value", "percentileRank"):
        if name not in field_list:
            raise StructuralError(f"估值分析返回缺少 {name} 列（fieldList={field_list}）")
    cn = INDICATOR_CN.get(indicator, indicator)
    col_v = cn
    col_q = f"{cn}在时间范围内所处分位"
    out: Dict[str, Dict[str, object]] = {}
    for rec in records:
        raw_d = rec.get("tradeDate")
        ds = str(raw_d).strip()[:10] if raw_d is not None else ""
        if not ds:
            continue
        cols = out.setdefault(ds, {})
        cols[col_v] = rec.get("value")
        cols[col_q] = rec.get("percentileRank")
    return out, len(rows)


def _fetch_one_indicator(
    headers: dict,
    security_code: str,
    indicator: str,
    start_date: str,
    end_date: str,
    limit: int,
) -> Tuple[str, Dict[str, Dict[str, object]], Dict[str, object]]:
    payload = {
        "securityCode": security_code,
        "indicator": indicator,
        "startDate": start_date,
        "endDate": end_date,
        "limit": limit,
        "fieldList": list(_FIELD_LIST),
    }
    meta: Dict[str, object] = {"rows": 0, "earliest": None, "error": None}
    try:
        block = request_json("POST", VALUATION_URL, json=payload, timeout=120)
        merged, n_rows = _parse_valuation_block(block, indicator)
    except ApiError as exc:
        if exc.code != NO_DATA_CODE:
            meta["error"] = str(exc)
        return indicator, {}, meta
    except Exception as exc:
        meta["error"] = str(exc)
        return indicator, {}, meta
    meta["rows"] = n_rows
    meta["earliest"] = min(merged) if merged else None
    return indicator, merged, meta


# 首行晚于开始日期超过该天数才提示（避开周末与短假期）
LATE_START_TOLERANCE_DAYS = 7


def _coverage_notes(
    security_code: str,
    metas: Dict[str, Dict[str, object]],
    start_date: Optional[str],
    limit: int,
) -> Tuple[List[str], List[str]]:
    """返回 (导致部分结果的说明, 仅提示的说明)。"""
    partial: List[str] = []
    warn: List[str] = []
    late: List[str] = []
    for ind in VALUATION_INDICATORS:
        meta = metas.get(ind)
        if not meta:
            continue
        cn = INDICATOR_CN[ind]
        if meta.get("error"):
            partial.append(f"{security_code} {cn} 获取失败：{meta['error']}")
            continue
        earliest = meta.get("earliest")
        if not start_date or not earliest or str(earliest) <= start_date:
            continue
        if int(meta.get("rows") or 0) >= limit:
            partial.append(
                f"{security_code} {cn} 返回 {limit} 行已达 limit，最早只到 {earliest}，"
                f"{start_date} 起的区间开头缺失；请调大 limit 或缩短日期区间"
            )
        else:
            late.append(str(earliest))
    if late:
        first = min(late)
        try:
            gap = (date.fromisoformat(first) - date.fromisoformat(start_date)).days
        except ValueError:
            gap = LATE_START_TOLERANCE_DAYS + 1
        if gap > LATE_START_TOLERANCE_DAYS:
            warn.append(f"{security_code} 最早数据为 {first}，晚于开始日期 {start_date}（可能上市或指标起始较晚）")
    return partial, warn


def _fetch_indicators_merged(
    headers: dict,
    security_code: str,
    start_date: str,
    end_date: str,
    limit: int,
    metas: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict[str, Dict[str, object]]:
    date_maps: List[Dict[str, Dict[str, object]]] = []
    with ThreadPoolExecutor(max_workers=len(VALUATION_INDICATORS)) as ex:
        futs = [
            ex.submit(
                _fetch_one_indicator,
                headers,
                security_code,
                ind,
                start_date,
                end_date,
                limit,
            )
            for ind in VALUATION_INDICATORS
        ]
        for fut in as_completed(futs):
            ind, part, meta = fut.result()
            if metas is not None:
                metas[ind] = meta
            if part:
                date_maps.append(part)

    merged_by_date: Dict[str, Dict[str, object]] = {}
    for part in date_maps:
        for d, cols in part.items():
            if d not in merged_by_date:
                merged_by_date[d] = {}
            merged_by_date[d].update(cols)
    return merged_by_date


def _resolve_explicit_dates(
    start_date: Optional[str],
    end_date: Optional[str],
) -> Tuple[str, str]:
    """显式日期：缺省一侧补齐为另一侧或今天；不触发「当天回退 7 日」逻辑。"""
    today_s = date.today().strftime("%Y-%m-%d")
    end_s = (end_date or "").strip() or today_s
    start_s = (start_date or "").strip() or end_s
    return start_s, end_s


def _resolve_auto_latest_merged(
    headers: dict,
    security_code: str,
    limit: int,
    metas: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict[str, Dict[str, object]]:
    """未传日期：先查当天；无有效值则查 [今天-6, 今天]，并保留最近一个有效交易日。"""
    today = date.today()
    today_s = today.strftime("%Y-%m-%d")
    merged = _fetch_indicators_merged(headers, security_code, today_s, today_s, limit, metas)
    if _date_map_has_valid(merged):
        return _keep_latest_valid_day(merged)

    if metas is not None:
        metas.clear()
    start_s = (today - timedelta(days=LOOKBACK_DAYS - 1)).strftime("%Y-%m-%d")
    merged = _fetch_indicators_merged(headers, security_code, start_s, today_s, limit, metas)
    if not _date_map_has_valid(merged):
        return {}
    return _keep_latest_valid_day(merged)


def _build_valuation_df(
    security_abbr: str,
    security_code: str,
    merged_by_date: Dict[str, Dict[str, object]],
    start_date: Optional[str],
    end_date: Optional[str],
) -> pd.DataFrame:
    if not merged_by_date:
        return pd.DataFrame()

    records = []
    for d in sorted(merged_by_date.keys(), reverse=True):
        row = {
            "证券简称": security_abbr,
            "证券代码": security_code,
            "日期": d,
        }
        row.update(merged_by_date[d])
        records.append(row)

    df = pd.DataFrame(records)
    base_cols = ["证券简称", "证券代码", "日期"]
    ordered_metric_cols: List[str] = []
    for ind in VALUATION_INDICATORS:
        cn = INDICATOR_CN[ind]
        q = f"{cn}在{QUANTILE_YEAR_LABEL}年中所处分位"
        if cn in df.columns:
            ordered_metric_cols.append(cn)
        if q in df.columns:
            ordered_metric_cols.append(q)
    extra = [c for c in df.columns if c not in base_cols + ordered_metric_cols]
    df = df[base_cols + [c for c in ordered_metric_cols if c in df.columns] + extra]

    for c in df.columns:
        if c not in base_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if start_date:
        sd = pd.to_datetime(start_date, errors="coerce")
        df = df[pd.to_datetime(df["日期"], errors="coerce") >= sd]
    if end_date:
        ed = pd.to_datetime(end_date, errors="coerce")
        df = df[pd.to_datetime(df["日期"], errors="coerce") <= ed]
    df = df.reset_index(drop=True)
    if not df.empty:
        df = df.sort_values(by=["日期"], ascending=False).reset_index(drop=True)
    df = df.drop(columns=["证券简称"])
    return df


def _valuation_df_for_security(
    headers: dict,
    security_abbr: str,
    security_code: str,
    start_date: Optional[str],
    end_date: Optional[str],
    limit: int,
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    auto_latest = not (start_date or "").strip() and not (end_date or "").strip()
    metas: Dict[str, Dict[str, object]] = {}
    if auto_latest:
        merged_by_date = _resolve_auto_latest_merged(headers, security_code, limit, metas)
        partial, warn = _coverage_notes(security_code, metas, None, limit)
        return _build_valuation_df(security_abbr, security_code, merged_by_date, None, None), partial, warn

    start_s, end_s = _resolve_explicit_dates(start_date, end_date)
    merged_by_date = _fetch_indicators_merged(headers, security_code, start_s, end_s, limit, metas)
    partial, warn = _coverage_notes(security_code, metas, start_s, limit)
    return _build_valuation_df(security_abbr, security_code, merged_by_date, start_s, end_s), partial, warn


def valuation_data(
    securities: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 2000,
    output_dir: Optional[str] = None,
):
    usage: dict = {}
    if get_authorization_token() is None:
        return format_response(
            {"state": "error", "message": "未配置 gangtise 授权，无法调用 open 接口", "data": [], "usage": usage},
            "valuation", output_dir=output_dir)

    headers = get_authorization_headers()

    # 未传日期保持 None：由 _valuation_df_for_security 按「当天 → 7 日内回退」解析
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None

    resolved = batch_security_search(
        normalize_securities_arg(securities) or [],
        category=["stock", "dr"],
        headers=headers,
        output_limit=1,
    )
    if resolved.get("state") != "success":
        return format_response(
            {
                "state": "error",
                "message": resolved.get("message") or "证券解析失败",
                "data": [],
                "usage": usage,
            },
            "valuation", output_dir=output_dir)
    securities_codes, securities_abbrs = dedupe_resolved(resolved.get("codes"), resolved.get("abbrs"))
    abbr_map = resolved_code_abbr_map(resolved)
    for uk, uv in (resolved.get("usage") or {}).items():
        usage[uk] = usage.get(uk, 0) + (uv if isinstance(uv, (int, float)) else 0)

    frames: List[pd.DataFrame] = []
    partial_notes: List[str] = []
    warn_notes: List[str] = []
    for abbr, code in zip(securities_abbrs, securities_codes):
        df_one, p_notes, w_notes = _valuation_df_for_security(
            headers,
            abbr_map.get(str(code).strip().upper(), abbr),
            code,
            start_date,
            end_date,
            limit,
        )
        partial_notes.extend(p_notes)
        warn_notes.extend(w_notes)
        if not df_one.empty:
            frames.append(df_one)

    if not frames:
        message = "未找到估值数据"
        if partial_notes:
            message += "：" + "；".join(partial_notes)
        return format_response(
            {"state": "error", "message": message, "data": [], "usage": usage},
            "valuation", output_dir=output_dir)

    valuation_data_df = pd.concat(frames, ignore_index=True)
    valuation_data_df = valuation_data_df.sort_values(
        by=["证券代码", "日期"], ascending=[True, False]
    ).reset_index(drop=True)

    col_map = {
        "证券简称": "security_abbr",
        "证券代码": "security_code",
        "日期": "date",
    }
    for col in list(valuation_data_df.columns):
        if col in col_map:
            valuation_data_df.rename(columns={col: col_map[col]}, inplace=True)
    front_columns = ["security_abbr", "security_code", "date"]
    columns = [c for c in front_columns if c in valuation_data_df.columns] + [
        c for c in valuation_data_df.columns if c not in front_columns
    ]
    valuation_data_df = valuation_data_df[columns]

    success_securities_abbr = (
        "、".join(securities_abbrs[:3]) + "等"
        if len(securities_abbrs) > 3
        else "、".join(securities_abbrs)
    )

    parts = [
        {
            "data": valuation_data_df.to_dict(orient="records"),
            "module": "valuation",
            "type": "data",
        }
    ]
    message = f"已找到{success_securities_abbr}估值数据"
    notes = partial_notes + warn_notes
    if notes:
        message += "\n\n" + "\n".join(f"- [WARNING] {n}" for n in notes)
    response = {"state": "success", "message": message, "data": parts, "usage": usage}
    if partial_notes:
        response["partial"] = "；".join(partial_notes)
    return format_response(response, "valuation", output_dir=output_dir)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="查询估值数据（open 估值分析接口）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    today_str = date.today().strftime("%Y-%m-%d")
    parser.add_argument(
        "-sd",
        "--start-date",
        default=None,
        help="开始日期，如 2023-01-01；与 -ed 均不传时先查当天，无数据则向前回退至多 7 日",
    )
    parser.add_argument(
        "-ed",
        "--end-date",
        default=None,
        help=f"结束日期，如 2026-12-31；仅传一侧时另一侧按显式区间补齐（今天={today_str}）",
    )
    parser.add_argument("--securities", default=None, help="证券：完整代码/名称/拼音等，逗号分隔；亦可传 .csv 路径（须含 security_code 等列）")
    parser.add_argument("-l", "--limit", type=int, default=2000, help="单次指标请求最大行数")
    parser.add_argument(
        "-od",
        "--output-dir",
        default=None,
        help="结果保存目录路径，建议使用绝对路径",
    )

    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)

    if not securities:
        parser.error("必须提供 --securities（代码/名称，或 .csv 路径）")

    out = valuation_data(
        securities=securities,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit,
        output_dir=args.output_dir or None,
    )
    print(out)


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors="ignore")
    main()
