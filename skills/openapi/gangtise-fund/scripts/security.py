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

from .utils import (
    SECURITIES_SEARCH_URL,
    authorized_request,
    build_headers,
    error_response,
    format_response,
    normalize_securities_arg,
    remove_html_tags,
)

_VALID_API_CATEGORIES = frozenset({"stock", "dr", "index", "fund", "bond"})
# .OF 为场外基金，检索未命中时仍采用；.SH/.SZ/.BJ/.HK 须在基金分类中命中，避免把股票代码送进基金接口
FUND_CODE_PATTERN = re.compile(r"^[0-9A-Z]{4,12}\.(OF|SH|SZ|BJ|HK)$")


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


def _match_code(items: List[dict], code: str) -> Optional[dict]:
    for item in items:
        if (item.get("gtsCode") or "").strip().upper() == code:
            return item
    return None


def resolve_funds(tokens: List[str], headers: Optional[dict] = None) -> Dict:
    """
    将用户输入（基金代码 / 简称 / 拼音）解析为基金代码。
    .OF 直接采用；.SH/.SZ/.BJ/.HK 须在 category=fund 的检索结果中命中，避免把股票代码送进基金接口。
    其余按基金分类检索：代码或简称完全一致、或匹配度高于 0.6 且只有一只时直接采用；
    多只且无法唯一确定时返回候选列表，不猜测其中一只。
    查不到或不是基金代码的输入跳过并在 message 中给出 [WARNING]；全部解析失败才返回 error。
    """
    headers = headers or build_headers()
    codes: List[str] = []
    abbrs: List[str] = []
    skipped: List[str] = []
    for raw in tokens:
        token = str(raw).strip()
        if not token:
            continue
        upper = token.upper()
        if FUND_CODE_PATTERN.match(upper):
            items, err = search_securities(upper, category=["fund"], top=5, headers=headers)
            matched = _match_code(items, upper) if not err else None
            if upper.endswith(".OF"):
                if upper not in codes:
                    codes.append(upper)
                    abbrs.append((matched or {}).get("gtsName") or "")
                continue
            if err:
                skipped.append(f"{token}({err})")
                continue
            if not matched:
                skipped.append(f"{token}(不是基金代码)")
                continue
            if upper not in codes:
                codes.append(upper)
                abbrs.append(matched.get("gtsName") or "")
            continue

        items, err = search_securities(token, category=["fund"], top=10, headers=headers)
        if err:
            skipped.append(f"{token}({err})")
            continue
        if not items:
            skipped.append(token)
            continue
        strong = _strong_candidates(items)
        picked = _pick_auto_candidate(strong, token) if strong else None
        if picked is None:
            return {
                "state": "error",
                "message": _format_security_candidates(strong or items, token, "基金"),
                "codes": [],
                "abbrs": [],
            }
        code = (picked.get("gtsCode") or "").strip().upper()
        if not code:
            return {
                "state": "error",
                "message": _format_security_candidates(strong or items, token, "基金"),
                "codes": [],
                "abbrs": [],
            }
        if code not in codes:
            codes.append(code)
            abbrs.append(picked.get("gtsName") or "")

    def _listed(items: List[str]) -> str:
        return "、".join(items[:10]) + (f" 等 {len(items)} 项" if len(items) > 10 else "")

    if not codes:
        first = skipped[0].split("(")[0] if skipped else ""
        hint = f"，可先运行 security.py -k {first} -c fund 查看候选，或直接传入基金代码（场外基金用 .OF 后缀）" if first else ""
        return {"state": "error", "message": f"未找到基金「{'、'.join(skipped)}」{hint}", "codes": [], "abbrs": []}

    pairs = [f"{a}({c})" if a else c for c, a in zip(codes, abbrs)]
    comment = f"<!-- 匹配到的基金：{', '.join(pairs)} -->\n"
    print(comment, end="")
    message = comment.rstrip("\n")
    if skipped:
        message += f"\n[WARNING] 以下输入未能解析为基金，已跳过：{_listed(skipped)}"
    return {"state": "success", "message": message, "codes": codes, "abbrs": abbrs}


def resolve_or_error(tokens: List[str], headers: dict, method_name: str, output_dir: Optional[str]):
    """供各数据脚本调用：成功返回 (codes, abbrs, notes, None)，失败返回 (None, None, None, 错误输出)。"""
    try:
        tokens = normalize_securities_arg(tokens)
    except (OSError, ValueError) as e:
        return None, None, None, error_response(method_name, f"解析 securities 失败：{e}", output_dir)
    resolved = resolve_funds(tokens, headers=headers)
    if resolved.get("state") != "success":
        return None, None, None, error_response(method_name, resolved.get("message") or "基金解析失败", output_dir)
    notes = [line for line in resolved["message"].splitlines() if line.startswith("[WARNING]")]
    return resolved["codes"], resolved["abbrs"], notes, None


def security_search(
    keyword: str,
    category: Optional[List[str]] = None,
    top: int = 10,
    output_limit: int = 10,
    output_dir: Optional[str] = None,
):
    if category is None:
        category = "fund"
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
        description="基金代码检索（open-reference / securities/search，默认 category=fund）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--keyword", "-k", required=True, help="搜索关键词（基金简称、代码、拼音等）")
    parser.add_argument(
        "--category",
        "-c",
        default="fund",
        help="逗号分隔: fund,stock,dr,index,bond；传 all 查全部类",
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
