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
import re
import sys
from io import TextIOWrapper
from typing import List, Optional, Tuple

import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from .gts_auth import get_authorization_headers
from .security import batch_security_search
from .utils import (
    INDEX_CONSTITUENT_WEIGHT_URL,
    SECTOR_CONSTITUENTS_URL,
    SECTOR_SEARCH_URL,
    format_response,
    get_authorization_token)

MATCH_SCORE_THRESHOLD = 0.6
SEARCH_TOP_DEFAULT = 10
SEARCH_TOP_MAX = 10
METHOD_NAME = "constituents"
_CODE_PATTERN = re.compile(r"^(\d{6}|[A-Z]?\d+)\.[A-Z]{2,4}$", re.IGNORECASE)

_TYPE_ALIASES = {
    "sector": "sector",
    "block": "sector",
    "板块": "sector",
    "index": "index",
    "指数": "index",
}


def _normalize_type(raw: Optional[str]) -> str:
    token = str(raw or "sector").strip().lower()
    mapped = _TYPE_ALIASES.get(token) or _TYPE_ALIASES.get(str(raw or "").strip())
    if mapped:
        return mapped
    raise ValueError("type 仅支持 sector（板块成分股）或 index（指数成分股权重）")


def _api_error_message(body: dict, fallback: str = "") -> str:
    if isinstance(body, dict):
        return str(body.get("msg") or body.get("message") or fallback)
    return fallback


def _as_list(raw) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        items = raw
    else:
        items = str(raw).replace("，", ",").split(",")
    out: List[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


def _search_sectors(
    headers: dict,
    keyword: str,
    top: int,
) -> Tuple[List[dict], Optional[str]]:
    from .gts_runtime import GangtiseError
    from .gts_runtime import request_json

    req_top = max(1, min(int(top), SEARCH_TOP_MAX))
    payload = {"keyword": keyword.strip(), "top": req_top}
    try:
        data = request_json("POST", SECTOR_SEARCH_URL, json=payload, timeout=120)
    except GangtiseError:
        raise
    except Exception as e:
        return [], f"板块检索请求失败: {e}"

    items = (data or {}).get("list") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return [], "板块检索返回 list 格式异常"
    return items, None


def _fetch_sector_constituents(
    headers: dict,
    sector_id: str,
) -> Tuple[List[dict], Optional[str]]:
    from .gts_runtime import GangtiseError
    from .gts_runtime import request_json

    payload = {"sectorId": str(sector_id).strip()}
    try:
        data = request_json("POST", SECTOR_CONSTITUENTS_URL, json=payload, timeout=120)
    except GangtiseError:
        raise
    except Exception as e:
        return [], f"成分股请求失败: {e}"

    items = (data or {}).get("list") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return [], "成分股返回 list 格式异常"
    return items, None


def _fetch_index_weights(
    headers: dict,
    index_codes: List[str],
    trade_date: str,
) -> Tuple[List[dict], Optional[str]]:
    from .gts_runtime import GangtiseError
    from .gts_runtime import request_json

    payload = {
        "indexCodeList": index_codes,
        "tradeDate": trade_date,
    }
    try:
        data = request_json("POST", INDEX_CONSTITUENT_WEIGHT_URL, json=payload, timeout=120)
    except GangtiseError:
        raise
    except Exception as e:
        return [], f"指数成分股权重请求失败: {e}"

    items = (data or {}).get("list") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return [], "指数成分股权重返回 list 格式异常"
    return items, None


def _match_score(item: dict) -> float:
    try:
        return float(item.get("matchScore") or 0)
    except (TypeError, ValueError):
        return 0.0


def _filter_strong_candidates(items: List[dict]) -> List[dict]:
    out = []
    for item in items:
        if _match_score(item) > MATCH_SCORE_THRESHOLD:
            out.append(item)
    out.sort(key=_match_score, reverse=True)
    return out


def _pick_auto_candidate(candidates: List[dict]) -> Optional[dict]:
    """唯一候选，或候选中仅一条 matchScore=1 时可直接查询。"""
    if len(candidates) == 1:
        return candidates[0]
    perfect = [c for c in candidates if _match_score(c) == 1.0]
    if len(perfect) == 1:
        return perfect[0]
    return None


def _print_sector_candidates(candidates: List[dict], keyword: str) -> str:
    lines = [
        f"关键词「{keyword}」匹配到 {len(candidates)} 个板块，"
        "请确认后使用 -s/--sector-id 指定 sectorId：\n"
    ]
    for c in candidates:
        lines.append(
            f"- sectorId={c.get('sectorId')} | {c.get('sectorName')} | {c.get('hierarchy')}"
        )
    return "\n".join(lines)


def _sector_to_dataframe(
    rows: List[dict],
    sector_id: str,
    sector_name: str = "",
    hierarchy: str = "",
) -> pd.DataFrame:
    records = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        records.append(
            {
                "sector_id": sector_id,
                "sector_name": sector_name,
                "hierarchy": hierarchy,
                "security_code": row.get("gtsCode"),
                "security_name": row.get("gtsName"),
            }
        )
    if not records:
        return pd.DataFrame(
            columns=["sector_id", "sector_name", "hierarchy", "security_code", "security_name"]
        )
    df = pd.DataFrame(records)
    return df.sort_values(by=["security_code"], ascending=True).reset_index(drop=True)


def _index_to_dataframe(rows: List[dict]) -> pd.DataFrame:
    records = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        records.append(
            {
                "index_code": row.get("indexCode"),
                "index_name": row.get("indexName"),
                "trade_date": row.get("tradeDate"),
                "security_code": row.get("securityCode"),
                "security_name": row.get("securityName"),
                "weight": row.get("weight"),
            }
        )
    if not records:
        return pd.DataFrame(
            columns=[
                "index_code",
                "index_name",
                "trade_date",
                "security_code",
                "security_name",
                "weight",
            ]
        )
    df = pd.DataFrame(records)
    return df.sort_values(
        by=["index_code", "weight", "security_code"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def _sector_constituents(
    keyword: Optional[str] = None,
    sector_id: Optional[str] = None,
    top: int = SEARCH_TOP_DEFAULT,
    output_dir: Optional[str] = None,
):
    usage: dict = {}
    headers = get_authorization_headers()

    resolved_id = (sector_id or "").strip()
    resolved_name = ""
    resolved_hierarchy = ""

    if not resolved_id:
        kw = (keyword or "").strip()
        if not kw:
            return format_response(
                {
                    "state": "error",
                    "message": "板块模式必须提供 keyword 或 sectorId",
                    "data": [],
                    "usage": usage,
                },
                METHOD_NAME,
                output_dir=output_dir,
            )

        items, err = _search_sectors(headers, kw, top)
        if err:
            return format_response(
                {"state": "error", "message": err, "data": [], "usage": usage},
                METHOD_NAME,
                output_dir=output_dir,
            )

        candidates = _filter_strong_candidates(items)
        if not candidates:
            return format_response(
                {
                    "state": "error",
                    "message": f"未找到与「{kw}」匹配的相关板块",
                    "data": [],
                    "usage": usage,
                },
                METHOD_NAME,
                output_dir=output_dir,
            )

        picked = _pick_auto_candidate(candidates)
        if picked is None:
            return _print_sector_candidates(candidates, kw)

        resolved_id = str(picked.get("sectorId") or "").strip()
        resolved_name = str(picked.get("sectorName") or "").strip()
        resolved_hierarchy = str(picked.get("hierarchy") or "").strip()
        if not resolved_id:
            return format_response(
                {
                    "state": "error",
                    "message": "板块检索结果缺少 sectorId",
                    "data": [],
                    "usage": usage,
                },
                METHOD_NAME,
                output_dir=output_dir,
            )

    rows, err = _fetch_sector_constituents(headers, resolved_id)
    if err:
        return format_response(
            {"state": "error", "message": err, "data": [], "usage": usage},
            METHOD_NAME,
            output_dir=output_dir,
        )

    df = _sector_to_dataframe(rows, resolved_id, resolved_name, resolved_hierarchy)
    if df.empty:
        label = resolved_name or resolved_id
        return format_response(
            {
                "state": "error",
                "message": f"板块「{label}」（{resolved_id}）暂无成分股数据",
                "data": [],
                "usage": usage,
            },
            METHOD_NAME,
            output_dir=output_dir,
        )

    label = resolved_name or resolved_id
    parts = [
        {
            "data": df.to_dict(orient="records"),
            "module": "constituents_sector",
            "type": "data",
        }
    ]
    return format_response(
        {
            "state": "success",
            "message": f"已获取板块「{label}」（{resolved_id}）共 {len(df)} 只成分股",
            "data": parts,
            "usage": usage,
        },
        METHOD_NAME,
        output_dir=output_dir,
    )


def _resolve_index_codes(raw_indexes: Optional[List[str]]) -> Tuple[Optional[List[str]], Optional[str], List[str]]:
    tokens = _as_list(raw_indexes)
    if not tokens:
        return None, "指数模式必须提供 indexes（指数代码或名称）", []

    direct: List[str] = []
    names: List[str] = []
    for token in tokens:
        if _CODE_PATTERN.match(token):
            direct.append(token.upper())
        else:
            names.append(token)

    pairs = [c for c in direct]
    codes = list(direct)
    if names:
        resolved = batch_security_search(names, category=["index"], output_limit=1)
        if resolved.get("state") != "success":
            return None, resolved.get("message") or "指数解析失败", []
        for code, abbr in zip(resolved.get("codes") or [], resolved.get("abbrs") or []):
            c = str(code or "").strip().upper()
            if not c:
                continue
            if c not in codes:
                codes.append(c)
            pairs.append(f"{abbr}({c})" if abbr and abbr != c else c)

    if not codes:
        return None, "未能解析到有效指数代码", []
    return codes, None, pairs


def _index_constituents(
    indexes: Optional[List[str]] = None,
    trade_date: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    usage: dict = {}
    td = str(trade_date or "").strip()
    if not td:
        return format_response(
            {
                "state": "error",
                "message": "指数模式必须提供 tradeDate（yyyy-MM-dd）",
                "data": [],
                "usage": usage,
            },
            METHOD_NAME,
            output_dir=output_dir,
        )
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", td):
        return format_response(
            {
                "state": "error",
                "message": "tradeDate 须为 yyyy-MM-dd",
                "data": [],
                "usage": usage,
            },
            METHOD_NAME,
            output_dir=output_dir,
        )

    codes, err, pairs = _resolve_index_codes(indexes)
    if err:
        return format_response(
            {"state": "error", "message": err, "data": [], "usage": usage},
            METHOD_NAME,
            output_dir=output_dir,
        )

    if pairs:
        print(f"<!-- 匹配指数：{'、'.join(pairs)} -->\n")

    headers = get_authorization_headers()
    rows, err = _fetch_index_weights(headers, codes or [], td)
    if err:
        return format_response(
            {"state": "error", "message": err, "data": [], "usage": usage},
            METHOD_NAME,
            output_dir=output_dir,
        )

    df = _index_to_dataframe(rows)
    if df.empty:
        return format_response(
            {
                "state": "error",
                "message": f"指数 {','.join(codes or [])} 在 {td} 暂无成分股权重数据",
                "data": [],
                "usage": usage,
            },
            METHOD_NAME,
            output_dir=output_dir,
        )

    parts = [
        {
            "data": df.to_dict(orient="records"),
            "module": "constituents_index",
            "type": "data",
        }
    ]
    return format_response(
        {
            "state": "success",
            "message": (
                f"已获取 {len(codes or [])} 个指数在 {td} 的成分股权重，共 {len(df)} 条"
            ),
            "data": parts,
            "usage": usage,
        },
        METHOD_NAME,
        output_dir=output_dir,
    )


def constituents_data(
    mode: str = "sector",
    keyword: Optional[str] = None,
    sector_id: Optional[str] = None,
    top: int = SEARCH_TOP_DEFAULT,
    indexes: Optional[List[str]] = None,
    trade_date: Optional[str] = None,
    output_dir: Optional[str] = None,
    query_type: Optional[str] = None,
):
    """统一入口：sector=板块成分股；index=指数成分股权重。"""
    usage: dict = {}
    if get_authorization_token() is None:
        return format_response(
            {
                "state": "error",
                "message": "未配置 gangtise 授权，无法调用 open 接口",
                "data": [],
                "usage": usage,
            },
            METHOD_NAME,
            output_dir=output_dir,
        )

    try:
        kind = _normalize_type(query_type or mode)
    except ValueError as e:
        return format_response(
            {"state": "error", "message": str(e), "data": [], "usage": usage},
            METHOD_NAME,
            output_dir=output_dir,
        )

    if kind == "index":
        return _index_constituents(
            indexes=indexes,
            trade_date=trade_date,
            output_dir=output_dir,
        )
    return _sector_constituents(
        keyword=keyword,
        sector_id=sector_id,
        top=top,
        output_dir=output_dir,
    )


# 兼容旧函数名
def block_constituents_data(
    keyword: Optional[str] = None,
    sector_id: Optional[str] = None,
    top: int = SEARCH_TOP_DEFAULT,
    output_dir: Optional[str] = None,
):
    return constituents_data(
        mode="sector",
        keyword=keyword,
        sector_id=sector_id,
        top=top,
        output_dir=output_dir,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="成分股查询：板块成分股（sector）或指数成分股权重（index）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-m",
        "--mode",
        default="sector",
        help="sector=板块成分股；index=指数成分股权重",
    )
    parser.add_argument("-k", "--keyword", default=None, help="板块搜索关键词（sector）")
    parser.add_argument("-s", "--sector-id", default=None, help="板块 ID（sector）")
    parser.add_argument(
        "-t",
        "--top",
        type=int,
        default=SEARCH_TOP_DEFAULT,
        help=f"关键词搜索返回条数上限（最大 {SEARCH_TOP_MAX}，仅 sector + keyword）",
    )
    parser.add_argument(
        "--indexes",
        default=None,
        help="指数代码或名称，逗号分隔（index），如 000300.SH,沪深300",
    )
    parser.add_argument(
        "-td",
        "--trade-date",
        default=None,
        help="交易日期 yyyy-MM-dd（index 必填）",
    )
    parser.add_argument(
        "-od",
        "--output-dir",
        default=None,
        help="结果保存目录路径，建议使用绝对路径",
    )

    args = parser.parse_args()
    out = constituents_data(
        mode=args.mode,
        keyword=args.keyword,
        sector_id=args.sector_id,
        top=args.top,
        indexes=_as_list(args.indexes) or None,
        trade_date=args.trade_date,
        output_dir=args.output_dir or None,
    )
    print(out)


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors="ignore")
    main()
