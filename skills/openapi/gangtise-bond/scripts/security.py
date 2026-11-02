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
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .utils import (
    BOND_ISSUER_INFO_URL,
    SECURITIES_SEARCH_URL,
    authorized_request,
    build_headers,
    error_response,
    format_response,
    normalize_securities_arg,
    post_bond_table,
    remove_html_tags,
)

_VALID_API_CATEGORIES = frozenset({"stock", "dr", "index", "fund", "bond"})
BOND_CODE_PATTERN = re.compile(r"^[0-9A-Z]{4,12}\.(SH|SZ|BJ|IB)$")
OTHER_MARKET_CODE_PATTERN = re.compile(r"^[0-9A-Z]{4,12}\.[A-Z]{1,4}$")


def search_securities(
    keyword: str,
    category: Optional[List[str]] = None,
    top: int = 10,
    headers: Optional[dict] = None,
) -> Tuple[List[dict], Optional[str]]:
    """调用 open-reference 证券搜索接口，返回 (按 matchScore 降序的原始结果, 错误信息)。"""
    keyword = (keyword or "").strip()
    if not keyword:
        return [], "keyword 不能为空"
    headers = headers or build_headers()
    if not headers:
        return [], "缺少 Authorization，请配置 GTS 授权"

    payload: dict = {"keyword": keyword, "top": max(1, min(int(top), 10))}
    if category:
        payload["category"] = category
    try:
        r = authorized_request("POST", SECURITIES_SEARCH_URL, headers=headers, json=payload, timeout=60)
        body = r.json()
    except Exception as e:
        return [], f"证券搜索请求失败: {e}"
    if str(body.get("code", "")) != "000000" or body.get("status") is not True:
        return [], f"证券搜索接口错误: {body.get('msg') or body.get('message') or r.text[:300]}"

    items = []
    for it in (body.get("data") or {}).get("list") or []:
        items.append({**it, "gtsName": remove_html_tags(str(it.get("gtsName") or "").strip())})
    items.sort(key=lambda x: -float(x.get("matchScore") or 0))
    return items, None


MATCH_SCORE_THRESHOLD = 0.6
_MATCH_TYPE_CN = {
    "code": "代码",
    "abbr": "简称",
    "pinyin": "拼音",
    "prev": "曾用名",
    "engName": "英文名",
}


def _is_exact(item: dict, keyword: str) -> bool:
    k = keyword.strip().upper()
    return (item.get("gtsCode") or "").strip().upper() == k or (item.get("gtsName") or "").strip().upper() == k


def _match_score(item: dict) -> float:
    try:
        return float(item.get("matchScore") or 0)
    except (TypeError, ValueError):
        return 0.0


def _strong_candidates(items: List[dict]) -> List[dict]:
    out = [item for item in items if _match_score(item) > MATCH_SCORE_THRESHOLD]
    out.sort(key=_match_score, reverse=True)
    return out


def _pick_auto_candidate(candidates: List[dict], keyword: str) -> Optional[dict]:
    """只有一只强候选，或简称/代码与输入完全一致且只有一条时才自动采用。

    匹配度为 1 只说明检索认为它最接近，旁边仍有其他结果时不自动采用。
    """
    if len(candidates) == 1:
        return candidates[0]
    exact = [c for c in candidates if _is_exact(c, keyword)]
    if len(exact) == 1:
        return exact[0]
    return None


def _format_security_candidates(candidates: List[dict], keyword: str, kind: str) -> str:
    lines = [
        f"关键词「{keyword}」匹配到 {len(candidates)} 只{kind}，无法唯一确定，"
        "请确认后使用 --securities 指定代码：",
        "",
    ]
    for c in candidates:
        code = (c.get("gtsCode") or "").strip()
        name = (c.get("gtsName") or "").strip()
        match_type = _MATCH_TYPE_CN.get(str(c.get("matchType") or "").strip(), str(c.get("matchType") or "").strip())
        type_part = f" | {match_type}" if match_type else ""
        lines.append(f"- {code} | {name}{type_part} | matchScore={_match_score(c):.2f}")
    lines.append("")
    lines.append("检索最多返回 10 条。")
    return "\n".join(lines)


def resolve_bonds(tokens: List[str], headers: Optional[dict] = None) -> Dict:
    """
    将用户输入（债券代码 / 简称 / 拼音）解析为标准债券代码。
    已是 .SH/.SZ/.BJ/.IB 标准代码的直通。其余按 category=bond 检索：
    代码或简称完全一致、或匹配度高于 0.6 且只有一只时直接采用；
    多只且无法唯一确定时返回候选列表，不猜测其中一只。
    返回 dict：state, message, codes, abbrs。
    """
    headers = headers or build_headers()
    codes: List[str] = []
    abbrs: List[str] = []
    skipped: List[str] = []
    other_market: List[str] = []
    for raw in tokens:
        token = str(raw).strip()
        if not token:
            continue
        upper = token.upper()
        if BOND_CODE_PATTERN.match(upper):
            if upper not in codes:
                codes.append(upper)
                abbrs.append("")
            continue
        if OTHER_MARKET_CODE_PATTERN.match(upper):
            other_market.append(token)
            continue

        items, err = search_securities(token, category=["bond"], top=10, headers=headers)
        if err or not items:
            skipped.append(f"{token}({err})" if err else token)
            continue
        strong = _strong_candidates(items)
        picked = _pick_auto_candidate(strong, token) if strong else None
        if picked is None:
            return {
                "state": "error",
                "message": _format_security_candidates(strong or items, token, "债券"),
                "codes": [],
                "abbrs": [],
            }
        code = (picked.get("gtsCode") or "").strip().upper()
        if not code:
            return {
                "state": "error",
                "message": _format_security_candidates(strong or items, token, "债券"),
                "codes": [],
                "abbrs": [],
            }
        if code not in codes:
            codes.append(code)
            abbrs.append(picked.get("gtsName") or "")

    def _listed(items: List[str]) -> str:
        return "、".join(items[:10]) + (f" 等 {len(items)} 项" if len(items) > 10 else "")

    if not codes:
        skipped = skipped + [f"{t}(非沪深北/银行间代码)" for t in other_market]
        first = skipped[0].split("(")[0] if skipped else ""
        hint = f"，可先运行 security.py -k {first} 查看候选，或直接传入标准债券代码" if first else ""
        return {"state": "error", "message": f"未找到债券「{'、'.join(skipped)}」{hint}", "codes": [], "abbrs": []}

    pairs = [f"{a}({c})" if a else c for c, a in zip(codes, abbrs)]
    shown = pairs if len(pairs) <= 20 else pairs[:20] + [f"…共 {len(pairs)} 只"]
    comment = f"<!-- 匹配到的债券：{', '.join(shown)} -->\n"
    print(comment, end="")
    message = comment.rstrip("\n")
    if skipped:
        message += f"\n[WARNING]以下输入未能解析为债券，已跳过：{_listed(skipped)}"
    if other_market:
        message += f"\n[WARNING]以下代码不属于沪深北交易所或银行间市场，已跳过：{_listed(other_market)}"
    return {"state": "success", "message": message, "codes": codes, "abbrs": abbrs}


def filter_bond_codes(
    codes: List[str],
    abbrs: List[str],
    headers: Optional[dict] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """保留债券代码。.IB 直接通过；沪深北代码必须在债券检索中命中，避免股票代码进入发债公司报表和指标。"""
    headers = headers or build_headers()
    kept_codes: List[str] = []
    kept_abbrs: List[str] = []
    skipped: List[str] = []
    for code, abbr in zip(codes, list(abbrs) + [""] * max(0, len(codes) - len(abbrs))):
        cu = str(code).strip().upper()
        if not cu:
            continue
        if cu.endswith(".IB"):
            kept_codes.append(cu)
            kept_abbrs.append(str(abbr or "").strip())
            continue
        items, err = search_securities(cu, category=["bond"], top=5, headers=headers)
        matched = None
        if not err:
            for item in items or []:
                if (item.get("gtsCode") or "").strip().upper() != cu:
                    continue
                if (item.get("category") or "").strip().lower() == "bond":
                    matched = item
                    break
        if not matched:
            skipped.append(f"{cu}({err})" if err else f"{cu}(不是债券代码)")
            continue
        kept_codes.append(cu)
        kept_abbrs.append(str(abbr or "").strip() or (matched.get("gtsName") or ""))
    return kept_codes, kept_abbrs, skipped


def resolve_or_error(tokens: List[str], headers: dict, method_name: str, output_dir: Optional[str]):
    """供各数据脚本调用：成功返回 (codes, abbrs, notes, None)，失败返回 (None, None, None, 错误输出)。"""
    try:
        tokens = normalize_securities_arg(tokens)
    except (OSError, ValueError) as e:
        return None, None, None, error_response(method_name, f"解析 securities 失败：{e}", output_dir)
    resolved = resolve_bonds(tokens, headers=headers)
    if resolved.get("state") != "success":
        return None, None, None, error_response(method_name, resolved.get("message") or "债券解析失败", output_dir)
    notes = [line for line in resolved["message"].splitlines() if line.startswith("[WARNING]")]
    return resolved["codes"], resolved["abbrs"], notes, None


def _looks_like_issuer_full_name(token: str) -> bool:
    """已是公司全称时直接交给精确匹配接口，不再做一次主体检索。"""
    return len(token) >= 8 and token.endswith("公司")


def _clean_issuer_name(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text.lower() in {"", "none", "nan", "null"}:
        return ""
    return text


def _issuer_names_from_frame(df: pd.DataFrame) -> List[str]:
    if df is None or df.empty or "issuerName" not in df.columns:
        return []
    names: List[str] = []
    for value in df["issuerName"].tolist():
        name = _clean_issuer_name(value)
        if name and name not in names:
            names.append(name)
    return names


def _format_issuer_candidates(names: List[str], keyword: str) -> str:
    lines = [
        f"关键词「{keyword}」匹配到 {len(names)} 个发债主体，请确认后使用 --issuers 指定全称：",
        "",
    ]
    lines.extend(f"- {name}" for name in names)
    return "\n".join(lines)


def resolve_issuers(tokens: List[str], headers: Optional[dict] = None) -> Dict:
    """
    将发债主体简称或全称解析为发行人全称。
    全称（以「公司」结尾且不少于 8 个字）直接采用。
    简称先查主体信息，再按同名债券反查发行人；名称中包含该关键词的主体全部保留。
    只有一家时直接采用，多家时返回候选列表，不猜测其中一家。
    """
    headers = headers or build_headers()
    resolved: List[str] = []
    skipped: List[str] = []
    for raw in tokens:
        token = str(raw).strip()
        if not token:
            continue
        if _looks_like_issuer_full_name(token):
            if token not in resolved:
                resolved.append(token)
            continue

        df, err = post_bond_table(
            BOND_ISSUER_INFO_URL,
            {"issuerNameList": [token], "fieldList": ["issuerName"]},
            headers,
        )
        if err:
            return {"state": "error", "message": err, "names": []}
        best_names = _issuer_names_from_frame(df)
        best = best_names[0] if best_names else ""
        if best and best.casefold() == token.casefold():
            if best not in resolved:
                resolved.append(best)
            continue

        items, search_err = search_securities(token, category=["bond"], top=10, headers=headers)
        if search_err:
            return {"state": "error", "message": search_err, "names": []}
        codes: List[str] = []
        for item in items:
            code = (item.get("gtsCode") or "").strip().upper()
            if code and code not in codes:
                codes.append(code)
        bond_names: List[str] = []
        if codes:
            bond_df, bond_err = post_bond_table(
                BOND_ISSUER_INFO_URL,
                {"securityList": codes, "fieldList": ["issuerName"]},
                headers,
            )
            if bond_err:
                return {"state": "error", "message": bond_err, "names": []}
            bond_names = _issuer_names_from_frame(bond_df)

        pool: List[str] = []
        for name in [best, *bond_names]:
            if name and token.casefold() in name.casefold() and name not in pool:
                pool.append(name)
        if not pool and best:
            pool = [best]
        if len(pool) == 1:
            if pool[0] not in resolved:
                resolved.append(pool[0])
            continue
        if len(pool) > 1:
            return {"state": "error", "message": _format_issuer_candidates(pool, token), "names": []}
        skipped.append(token)

    if not resolved:
        shown = "、".join(skipped) if skipped else ""
        hint = f"，可传入发行人全称" if shown else ""
        return {"state": "error", "message": f"未找到发债主体「{shown}」{hint}", "names": []}

    comment = f"<!-- 匹配到的发债主体：{', '.join(resolved)} -->\n"
    print(comment, end="")
    message = comment.rstrip("\n")
    if skipped:
        message += f"\n[WARNING]以下输入未能解析为发债主体，已跳过：{'、'.join(skipped[:10])}"
    return {"state": "success", "message": message, "names": resolved}


def resolve_issuers_or_error(tokens: List[str], headers: dict, method_name: str, output_dir: Optional[str]):
    """供各数据脚本调用：成功返回 (全称列表, notes, None)，失败返回 (None, None, 错误输出)。"""
    resolved = resolve_issuers(tokens, headers=headers)
    if resolved.get("state") != "success":
        return None, None, error_response(method_name, resolved.get("message") or "发债主体解析失败", output_dir)
    notes = [line for line in resolved["message"].splitlines() if line.startswith("[WARNING]")]
    return resolved["names"], notes, None


def security_search(
    keyword: str,
    category: Optional[List[str]] = None,
    top: int = 10,
    output_limit: int = 10,
    output_dir: Optional[str] = None,
):
    if category is None:
        category = "bond"
    try:
        category = _parse_categories_arg(",".join(category) if isinstance(category, (list, tuple)) else category)
    except ValueError as e:
        return error_response("security", str(e), output_dir)
    items, err = search_securities(keyword, category=category, top=top)
    if err:
        return error_response("security", err, output_dir)
    if not items:
        return error_response("security", f"未找到与「{keyword}」相关的证券", output_dir)
    rows = [
        {
            "security_code": it.get("gtsCode"),
            "security_abbr": it.get("gtsName"),
            "category": it.get("category"),
            "match_score": it.get("matchScore"),
            "match_type": it.get("matchType"),
        }
        for it in items[: max(1, int(output_limit))]
    ]
    return format_response(
        {
            "state": "success",
            "message": f"已找到{keyword}相关证券",
            "data": [{"data": rows, "module": "security", "type": "data"}],
        },
        "security",
        output_dir=output_dir,
    )


def _parse_categories_arg(category_arg: Optional[str]) -> Optional[List[str]]:
    if not category_arg or not str(category_arg).strip():
        return None
    parts = [p.strip().lower() for p in re.split(r"[,，\s]+", category_arg) if p.strip()]
    if "all" in parts:
        return None
    bad = [p for p in parts if p not in _VALID_API_CATEGORIES]
    if bad:
        raise ValueError(f"不支持的 category: {bad}，允许: {sorted(_VALID_API_CATEGORIES)} 或 all")
    return parts or None


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="债券代码检索（open-reference / securities/search，默认 category=bond）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--keyword", "-k", required=True, help="搜索关键词（债券简称、代码、拼音等）")
    parser.add_argument(
        "--category",
        "-c",
        default="bond",
        help="逗号分隔: bond,stock,dr,index,fund；传 all 查全部类",
    )
    parser.add_argument("--top", type=int, default=10, help="请求接口返回条数上限（1–10）")
    parser.add_argument("--limit", "-l", type=int, default=10, help="输出条数上限")
    parser.add_argument("-od", "--output-dir", default=None, help="结果保存目录路径，建议使用绝对路径")
    args = parser.parse_args()

    try:
        cats = _parse_categories_arg(args.category)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    print(
        security_search(
            keyword=args.keyword,
            category=args.category or "all",
            top=args.top,
            output_limit=args.limit,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
