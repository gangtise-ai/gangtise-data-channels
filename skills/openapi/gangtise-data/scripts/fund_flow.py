if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

from .gts_runtime import GangtiseError, ValidationError

import os
import sys
from datetime import date, timedelta
from io import TextIOWrapper
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from .security import batch_security_search, resolved_code_abbr_map

from .utils import (
    FUND_FLOW_CN,
    FUND_FLOW_DAILY_URL,
    FUND_FLOW_SECTOR_DAILY_URL,
    SECTOR_FUND_FLOW_CN,
    SECTOR_SEARCH_URL,
    get_authorization_token,
    check_version,
    format_response,
    parse_str_list,
    normalize_securities_arg,
)
from .gts_auth import get_authorization_headers

# 个股默认返回全部净流入相关字段（securityCode、tradeDate 由接口自动前置）
DEFAULT_NET_INFLOW_FIELDS = [
    "smallNetInflow",
    "mediumNetInflow",
    "largeNetInflow",
    "xlargeNetInflow",
    "totalNetInflow",
    "mainNetInflow",
]

# 板块默认净流入字段（sectorId、tradeDate 由接口自动前置；板块接口无 totalNetInflow）
DEFAULT_SECTOR_NET_INFLOW_FIELDS = [
    "sectorSmallNetInflow",
    "sectorMediumNetInflow",
    "sectorLargeNetInflow",
    "sectorXlargeNetInflow",
    "sectorMainNetInflow",
]

_CN_TO_FIELD_EN = {v: k for k, v in FUND_FLOW_CN.items()}
_SECTOR_CN_TO_FIELD_EN = {v: k for k, v in SECTOR_FUND_FLOW_CN.items()}
SECTOR_MATCH_SCORE_THRESHOLD = 0.6
SECTOR_SEARCH_TOP = 10


def _build_fund_flow_cn_lookup(cn_map: Dict[str, str]) -> Dict[str, str]:
    """中文列名查找表：完整名及去掉（单位：元）/（%）/金额 等后缀的简写。"""
    lookup: Dict[str, str] = {}
    for en, cn in cn_map.items():
        if en in {"securityCode", "tradeDate", "sectorId"}:
            continue
        keys: List[str] = [cn]
        if cn.endswith("（单位：元）"):
            base = cn[: -len("（单位：元）")]
            keys.append(base)
            if base.endswith("金额"):
                keys.append(base[: -len("金额")])
        elif cn.endswith("（%）"):
            keys.append(cn[: -len("（%）")])
        for key in keys:
            k = key.strip()
            if k and k not in lookup:
                lookup[k] = en
    return lookup


_FUND_FLOW_CN_LOOKUP = _build_fund_flow_cn_lookup(FUND_FLOW_CN)
_SECTOR_FUND_FLOW_CN_LOOKUP = _build_fund_flow_cn_lookup(SECTOR_FUND_FLOW_CN)

ALL_MARKET_DATE_LOOKBACK_DAYS = 15


def _resolve_security_field_token(token: str) -> Optional[str]:
    t = str(token).strip()
    if not t:
        return None
    if t in FUND_FLOW_CN:
        return t
    if t in _CN_TO_FIELD_EN:
        return _CN_TO_FIELD_EN[t]
    if t in _FUND_FLOW_CN_LOOKUP:
        return _FUND_FLOW_CN_LOOKUP[t]
    return t


def _resolve_sector_field_token(token: str) -> Optional[str]:
    t = str(token).strip()
    if not t:
        return None
    if t in SECTOR_FUND_FLOW_CN:
        return t
    if t in _SECTOR_CN_TO_FIELD_EN:
        return _SECTOR_CN_TO_FIELD_EN[t]
    if t in _SECTOR_FUND_FLOW_CN_LOOKUP:
        return _SECTOR_FUND_FLOW_CN_LOOKUP[t]
    # 兼容个股字段名：smallNetInflow → sectorSmallNetInflow
    if t in FUND_FLOW_CN and t not in {"securityCode", "tradeDate"}:
        mapped = "sector" + t[0].upper() + t[1:]
        if mapped in SECTOR_FUND_FLOW_CN:
            return mapped
    if t.startswith("sector"):
        return t
    return t


def _prepare_field_list(field_list: Optional[List[str]], *, sector: bool = False) -> List[str]:
    defaults = DEFAULT_SECTOR_NET_INFLOW_FIELDS if sector else DEFAULT_NET_INFLOW_FIELDS
    resolve = _resolve_sector_field_token if sector else _resolve_security_field_token
    skip = {"securityCode", "tradeDate", "sectorId"}
    if not field_list:
        return list(defaults)
    out: List[str] = []
    seen: Set[str] = set()
    for raw in field_list:
        en = resolve(raw)
        if not en or en in skip:
            continue
        if en not in seen:
            out.append(en)
            seen.add(en)
    return out or list(defaults)


def _fetch_fund_flow(
    headers: dict,
    security_list: List[str],
    start_date: Optional[str],
    end_date: Optional[str],
    limit: int,
    field_list: List[str],
) -> Tuple[pd.DataFrame, Optional[str]]:
    payload: dict = {
        "securityList": security_list,
        "limit": limit,
        "fieldList": field_list,
    }
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    try:
        from .gts_runtime import request_json, records_from_block

        data = request_json("POST", FUND_FLOW_DAILY_URL, json=payload, timeout=300)
        records = records_from_block(data or {})
        if not records:
            return pd.DataFrame(), "未找到资金流向数据"
        return pd.DataFrame(records), None
    except GangtiseError:
        raise
    except Exception as e:
        return pd.DataFrame(), str(e)


def _fetch_sector_fund_flow(
    headers: dict,
    sector_list: List[str],
    start_date: Optional[str],
    end_date: Optional[str],
    limit: int,
    field_list: List[str],
) -> Tuple[pd.DataFrame, Optional[str]]:
    payload: dict = {
        "sectorList": sector_list,
        "limit": limit,
        "fieldList": field_list,
    }
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    try:
        from .gts_runtime import request_json, records_from_block

        data = request_json("POST", FUND_FLOW_SECTOR_DAILY_URL, json=payload, timeout=300)
        records = records_from_block(data or {})
        if not records:
            return pd.DataFrame(), "未找到板块资金流向数据"
        return pd.DataFrame(records), None
    except GangtiseError:
        raise
    except Exception as e:
        return pd.DataFrame(), str(e)


def _fetch_all_market_with_date_fallback(
    headers: dict,
    security_list: List[str],
    limit: int,
    field_list: List[str],
    max_lookback: int = ALL_MARKET_DATE_LOOKBACK_DAYS,
) -> Tuple[pd.DataFrame, Optional[str], Optional[str]]:
    """全市场且未指定日期时：从当天起逐日向前查询，直到取到数据或达到回退上限。"""
    today = date.today()
    last_err: Optional[str] = None
    for offset in range(max_lookback):
        query_date = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        data, err = _fetch_fund_flow(
            headers=headers,
            security_list=security_list,
            start_date=query_date,
            end_date=query_date,
            limit=limit,
            field_list=field_list,
        )
        if err:
            last_err = err
            continue
        if not data.empty:
            return data, None, query_date
        last_err = "未找到资金流向数据"
    return pd.DataFrame(), last_err, None


def _is_sector_id(token: str) -> bool:
    s = str(token).strip()
    return bool(s) and s.isdigit()


def _search_sectors(headers: dict, keyword: str) -> Tuple[List[dict], Optional[str]]:
    from .gts_runtime import request_json

    payload = {"keyword": keyword.strip(), "top": SECTOR_SEARCH_TOP}
    try:
        data = request_json("POST", SECTOR_SEARCH_URL, json=payload, timeout=120)
    except GangtiseError:
        raise
    except Exception as e:
        return [], f"板块检索失败: {e}"
    items = (data or {}).get("list") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return [], "板块检索返回 list 格式异常"
    return items, None


def _match_score(item: dict) -> float:
    try:
        return float(item.get("matchScore") or 0)
    except (TypeError, ValueError):
        return 0.0


def _pick_sector_candidate(candidates: List[dict]) -> Optional[dict]:
    strong = [c for c in candidates if _match_score(c) > SECTOR_MATCH_SCORE_THRESHOLD]
    strong.sort(key=_match_score, reverse=True)
    if len(strong) == 1:
        return strong[0]
    perfect = [c for c in strong if _match_score(c) == 1.0]
    if len(perfect) == 1:
        return perfect[0]
    return None


def _format_sector_candidates(keyword: str, candidates: List[dict]) -> str:
    lines = [
        f"关键词「{keyword}」匹配到多个板块，请改用明确的板块 ID（可通过 block_constituents 检索）："
    ]
    for c in candidates[:10]:
        lines.append(
            f"- sectorId={c.get('sectorId')} | {c.get('sectorName')} | {c.get('hierarchy')}"
        )
    return "\n".join(lines)


def _resolve_sector_tokens(
    headers: dict, tokens: List[str]
) -> Tuple[Optional[List[str]], Optional[Dict[str, str]], Optional[str]]:
    """返回 (sector_ids, id→name, error_message)。名称须唯一完全/高分匹配。"""
    ids: List[str] = []
    names: Dict[str, str] = {}
    for raw in tokens:
        token = str(raw).strip()
        if not token:
            continue
        if _is_sector_id(token):
            if token not in ids:
                ids.append(token)
            continue
        items, err = _search_sectors(headers, token)
        if err:
            return None, None, err
        strong = [c for c in items if _match_score(c) > SECTOR_MATCH_SCORE_THRESHOLD]
        strong.sort(key=_match_score, reverse=True)
        picked = _pick_sector_candidate(items)
        if picked is None:
            if not strong:
                return None, None, f"未找到与「{token}」匹配的板块"
            return None, None, _format_sector_candidates(token, strong)
        sid = str(picked.get("sectorId") or "").strip()
        if not sid:
            return None, None, f"板块「{token}」检索结果缺少 sectorId"
        if sid not in ids:
            ids.append(sid)
        names[sid] = str(picked.get("sectorName") or "").strip()
    if not ids:
        return None, None, "请指定 --sectors 板块 ID 或名称"
    return ids, names, None


def _apply_cn_columns(df: pd.DataFrame, cn_map: Dict[str, str]) -> pd.DataFrame:
    rename_map = {k: v for k, v in cn_map.items() if k in df.columns}
    out = df.rename(columns=rename_map)
    if "tradeDate" in df.columns and "交易日期" not in out.columns:
        out = out.rename(columns={"tradeDate": "交易日期"})
    if "securityCode" in df.columns and "证券代码" not in out.columns:
        out = out.rename(columns={"securityCode": "证券代码"})
    if "sectorId" in df.columns and "板块ID" not in out.columns:
        out = out.rename(columns={"sectorId": "板块ID"})
    return out


def _format_fund_flow_df(df: pd.DataFrame, abbr_map: Dict[str, str]) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "securityCode" in df.columns:
        codes = df["securityCode"].astype(str).str.strip().str.upper()
        df["证券简称"] = codes.map(lambda c: abbr_map.get(c, ""))
        df["securityCode"] = codes
    if "tradeDate" in df.columns:
        df["tradeDate"] = pd.to_datetime(df["tradeDate"], errors="coerce").dt.strftime("%Y-%m-%d")

    for c in df.columns:
        if c in {"证券简称", "securityCode", "tradeDate"}:
            continue
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = _apply_cn_columns(df, FUND_FLOW_CN)
    if "日期" not in df.columns and "交易日期" in df.columns:
        df = df.rename(columns={"交易日期": "日期"})

    sort_cols = [c for c in ["证券代码", "日期"] if c in df.columns]
    if sort_cols:
        asc = [True, False][: len(sort_cols)]
        df = df.sort_values(by=sort_cols, ascending=asc).reset_index(drop=True)

    metric_cols = [c for c in df.columns if c not in {"证券简称", "证券代码", "日期"}]
    for c in metric_cols:
        df[c] = df[c].round(2)

    col_map = {
        "证券简称": "security_abbr",
        "证券代码": "security_code",
        "日期": "date",
    }
    for col in list(df.columns):
        if col in col_map:
            df = df.rename(columns={col: col_map[col]})
    front = ["security_abbr", "security_code", "date"]
    df = df[[c for c in front if c in df.columns] + [c for c in df.columns if c not in front]]
    if "security_abbr" in df.columns:
        df = df.drop(columns=["security_abbr"])
    return df


def _format_sector_fund_flow_df(df: pd.DataFrame, name_map: Dict[str, str]) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "sectorId" in df.columns:
        df["sectorId"] = df["sectorId"].astype(str).str.strip()
        df["板块名称"] = df["sectorId"].map(lambda x: name_map.get(x, ""))
    if "tradeDate" in df.columns:
        df["tradeDate"] = pd.to_datetime(df["tradeDate"], errors="coerce").dt.strftime("%Y-%m-%d")

    for c in df.columns:
        if c in {"sectorId", "tradeDate", "板块名称"}:
            continue
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = _apply_cn_columns(df, SECTOR_FUND_FLOW_CN)
    if "日期" not in df.columns and "交易日期" in df.columns:
        df = df.rename(columns={"交易日期": "日期"})

    sort_cols = [c for c in ["板块ID", "日期"] if c in df.columns]
    if sort_cols:
        asc = [True, False][: len(sort_cols)]
        df = df.sort_values(by=sort_cols, ascending=asc).reset_index(drop=True)

    metric_cols = [c for c in df.columns if c not in {"板块名称", "板块ID", "日期"}]
    for c in metric_cols:
        rounded = df[c].round(2)
        # 接口 null → 空串，避免 markdown/CSV 里出现 nan（None 经 to_dict 仍会变回 nan）
        df[c] = rounded.map(lambda x: "" if pd.isna(x) else float(x))

    col_map = {
        "板块名称": "sector_name",
        "板块ID": "sector_id",
        "日期": "date",
    }
    for col in list(df.columns):
        if col in col_map:
            df = df.rename(columns={col: col_map[col]})
    front = ["sector_name", "sector_id", "date"]
    df = df[[c for c in front if c in df.columns] + [c for c in df.columns if c not in front]]
    if "sector_name" in df.columns and df["sector_name"].fillna("").astype(str).str.strip().eq("").all():
        df = df.drop(columns=["sector_name"])
    return df


def _title_for_df(df: pd.DataFrame, all_market: bool) -> str:
    if all_market:
        return "全市场A股资金流向数据"
    if "security_code" not in df.columns:
        return "资金流向数据"
    codes = df["security_code"].dropna().astype(str).str.upper().unique().tolist()
    codes.sort()
    if not codes:
        return "资金流向数据"
    if len(codes) == 1:
        return f"{codes[0]}资金流向数据"
    return f"{codes[0]}等{len(codes)}只标的资金流向数据"


def _title_for_sector_df(df: pd.DataFrame) -> str:
    if "sector_id" not in df.columns:
        return "板块资金流向数据"
    ids = df["sector_id"].dropna().astype(str).unique().tolist()
    ids.sort()
    if not ids:
        return "板块资金流向数据"
    if len(ids) == 1:
        name = ""
        if "sector_name" in df.columns:
            names = df.loc[df["sector_id"].astype(str) == ids[0], "sector_name"].dropna().astype(str)
            name = next((x for x in names if x.strip()), "")
        return f"{name or ids[0]}板块资金流向数据"
    return f"{ids[0]}等{len(ids)}个板块资金流向数据"


def fund_flow_data(
    securities: Optional[List[str]] = None,
    sectors: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 5000,
    all_market: bool = False,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    usage: dict = {}
    if get_authorization_token() is None:
        return format_response(
            {"state": "error", "message": "未配置 gangtise 授权，无法调用 open 接口", "data": [], "usage": usage},
            "fund_flow", output_dir=output_dir)

    headers = get_authorization_headers()
    capped_limit = max(1, min(int(limit), 10000))
    sector_tokens = parse_str_list(sectors) or []
    security_tokens = parse_str_list(securities) or []

    if sector_tokens and (all_market or security_tokens):
        raise ValidationError("--sectors 与 --securities / --all-market 不能同时使用")
    if all_market and security_tokens:
        raise ValidationError("--all-market 时不要使用 --securities")

    # ── 板块资金流向 ──────────────────────────────────────────────
    if sector_tokens:
        api_fields = _prepare_field_list(field_list, sector=True)
        sector_ids, name_map, err = _resolve_sector_tokens(headers, sector_tokens)
        if err:
            # 名称多命中 / 未匹配：返回可操作提示，不抬成 API 错误
            soft = ("匹配到多个板块" in err) or err.startswith("未找到与「")
            return format_response(
                {
                    "state": "success" if soft else "error",
                    "message": err,
                    "data": [],
                    "usage": usage,
                },
                "fund_flow",
                output_dir=output_dir,
            )
        data, ferr = _fetch_sector_fund_flow(
            headers=headers,
            sector_list=sector_ids or [],
            start_date=start_date,
            end_date=end_date,
            limit=capped_limit,
            field_list=api_fields,
        )
        if ferr or data.empty:
            return format_response(
                {"state": "error", "message": ferr or "未找到板块资金流向数据", "data": [], "usage": usage},
                "fund_flow", output_dir=output_dir)
        data = _format_sector_fund_flow_df(data, name_map or {})
        title = _title_for_sector_df(data)
        parts = [{"data": data.to_dict(orient="records"), "module": "fund_flow_sector", "type": "data"}]
        return format_response(
            {"state": "success", "message": f"已找到{title}", "data": parts, "usage": usage},
            "fund_flow", output_dir=output_dir)

    # ── 个股 / 全市场资金流向 ──────────────────────────────────────
    api_fields = _prepare_field_list(field_list, sector=False)
    abbr_map: Dict[str, str] = {}
    skip_note: Optional[str] = None
    fallback_note: Optional[str] = None

    if all_market:
        security_list = ["aShares"]
    else:
        tokens = security_tokens
        if not tokens:
            return format_response(
                {
                    "state": "error",
                    "message": "请指定 --securities、--sectors，或使用 --all-market",
                    "data": [],
                    "usage": usage,
                },
                "fund_flow", output_dir=output_dir)
        resolved = batch_security_search(
            tokens,
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
                "fund_flow", output_dir=output_dir)
        codes = resolved.get("codes") or []
        types = list(resolved.get("types") or [])
        abbr_map = resolved_code_abbr_map(resolved)
        for uk, uv in (resolved.get("usage") or {}).items():
            usage[uk] = usage.get(uk, 0) + (uv if isinstance(uv, (int, float)) else 0)
        if not codes:
            return format_response(
                {
                    "state": "error",
                    "message": "未解析到有效证券代码",
                    "data": [],
                    "usage": usage,
                },
                "fund_flow", output_dir=output_dir)

        a_codes: List[str] = []
        skipped: List[str] = []
        for code, st in zip(codes, types + [""] * max(0, len(codes) - len(types))):
            cu = str(code).strip().upper()
            if st == "A股" or cu.endswith((".SH", ".SZ", ".BJ")):
                a_codes.append(cu)
            else:
                skipped.append(f"{cu}（{st or '非A股'}）")
        if skipped:
            tail = "、".join(skipped[:6])
            if len(skipped) > 6:
                tail += "…"
            skip_note = f"[WARNING]个股资金流向仅支持A股，已跳过：{tail}"
        if not a_codes:
            msg = skip_note or "未找到支持的A股证券代码（个股资金流向仅支持上交所/深交所/北交所）"
            return format_response(
                {"state": "error", "message": msg, "data": [], "usage": usage},
                "fund_flow", output_dir=output_dir)
        security_list = list(dict.fromkeys(a_codes))

    if all_market and not start_date and not end_date:
        data, err, used_date = _fetch_all_market_with_date_fallback(
            headers=headers,
            security_list=security_list,
            limit=capped_limit,
            field_list=api_fields,
        )
        if used_date and used_date != date.today().strftime("%Y-%m-%d"):
            fallback_note = f"当日（{date.today().strftime('%Y-%m-%d')}）无数据，已回退至 {used_date}"
    else:
        data, err = _fetch_fund_flow(
            headers=headers,
            security_list=security_list,
            start_date=start_date,
            end_date=end_date,
            limit=capped_limit,
            field_list=api_fields,
        )
    if err or data.empty:
        msg = err or "未找到资金流向数据"
        if skip_note:
            msg = f"{skip_note}；{msg}"
        return format_response(
            {"state": "error", "message": msg, "data": [], "usage": usage},
            "fund_flow", output_dir=output_dir)

    data = _format_fund_flow_df(data, abbr_map)
    title = _title_for_df(data, all_market)
    msg = f"已找到{title}"
    if fallback_note:
        msg += f"\n{fallback_note}"
    if skip_note:
        msg += f"\n{skip_note}"

    parts = [{"data": data.to_dict(orient="records"), "module": "fund_flow_daily", "type": "data"}]
    return format_response(
        {
            "state": "success",
            "message": msg,
            "data": parts,
            "usage": usage,
        },
        "fund_flow", output_dir=output_dir)


def main():
    import argparse

    try:
        if not check_version():
            update_sh = os.path.join(script_dir, "update.sh")
            print(f"[WARNING] 存在 Gangtise data 版本更新，可以执行 {update_sh} 更新，请与用户确认是否更新\n")
    except Exception:
        print("[WARNING] 检查 Gangtise data 版本失败\n")

    parser = argparse.ArgumentParser(
        description="查询 A 股个股或板块日资金流向（open fund-flow/daily、fund-flow/sector-daily）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-sd", "--start-date", default=None, help="开始日期 yyyy-MM-dd；全市场未指定时默认当天并向前回退取数")
    parser.add_argument("-ed", "--end-date", default=None, help="结束日期 yyyy-MM-dd；全市场未指定时默认当天并向前回退取数")
    parser.add_argument(
        "--securities",
        default=None,
        help="证券：完整代码/名称/拼音等，逗号分隔；亦可传 .csv 路径。与 --sectors / --all-market 互斥",
    )
    parser.add_argument(
        "--sectors",
        default=None,
        help="板块 ID 或名称，逗号分隔（如 1000001065 或 半导体）；名称须唯一匹配。与 --securities / --all-market 互斥",
    )
    parser.add_argument(
        "--all-market",
        action="store_true",
        help="查询全市场 A 股（securityList=[aShares]）；未指定 -sd/-ed 时默认查当天，无数据则最多向前回退 15 天",
    )
    parser.add_argument("-l", "--limit", type=int, default=5000, help="单次请求最大行数（上限 10000）")
    parser.add_argument(
        "--field-list",
        default=None,
        help="指定字段英文名或中文名，逗号分隔；不传则默认返回全部净流入字段。板块模式可用个股字段名，脚本会自动加 sector 前缀",
    )
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
    sector_list = parse_str_list(args.sectors)

    selected = sum(bool(x) for x in (securities, sector_list, args.all_market))
    if selected != 1:
        parser.error("请在 --securities、--sectors、--all-market 三者中任选其一")

    fl: Optional[List[str]] = None
    if args.field_list:
        fl = [
            x.strip()
            for x in args.field_list.replace("，", ",").replace("、", ",").split(",")
            if x.strip()
        ]

    try:
        out = fund_flow_data(
            securities=securities,
            sectors=sector_list,
            start_date=args.start_date,
            end_date=args.end_date,
            limit=args.limit,
            all_market=args.all_market,
            field_list=fl,
            output_dir=args.output_dir or None,
        )
    except ValidationError as e:
        print(e)
        sys.exit(1)
    print(out)


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors="ignore")
    main()
