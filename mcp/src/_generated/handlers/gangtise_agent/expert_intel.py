# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-agent/scripts/expert_intel.py
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

import os
import re
import sys
from datetime import datetime
from io import TextIOWrapper
from typing import Any, Dict, List, Optional, Tuple

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from gangtise_core.auth import authorized_request, get_authorization_headers
from gangtise_core.skill_runtime import ValidationError, guard_row_billed_fetch
from .search_concept import resolve_concept_keyword
from .security import security_search_basic
from .utils import (
    EXPERT_INTEL_LIST_URL,
    format_response,
    get_authorization_token)

METHOD_NAME = "expert_intel"
POINTS_PER_ITEM = 20
PAGE_SIZE_MAX = 50
DEFAULT_PAGE_SIZE = 20

_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
_CODE_PATTERN = re.compile(r"^(\d{6}|[A-Z]?\d+)\.[A-Z]{2,4}$")


def _as_list(raw: Any) -> List[str]:
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


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _validate_time(value: Optional[str], field_name: str, *, end_of_day: bool) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if _DATE_ONLY.match(text):
            datetime.strptime(text, "%Y-%m-%d")
            return f"{text} 23:59:59" if end_of_day else f"{text} 00:00:00"
        if _DATETIME.match(text):
            datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            return text
    except ValueError:
        pass
    raise ValueError(f"{field_name} 格式错误，仅支持 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss")


def _resolve_securities(raw: Optional[List[str]]) -> Tuple[Optional[List[str]], Optional[str], List[str]]:
    tokens = _as_list(raw)
    if not tokens:
        return None, None, []
    codes: List[str] = []
    pairs: List[str] = []
    for token in tokens:
        upper = token.upper()
        if _CODE_PATTERN.match(upper):
            codes.append(upper)
            pairs.append(upper)
            continue
        resp = security_search_basic(token, output_limit=1, category=["stock", "dr"])
        if resp.get("state") != "success":
            return None, resp.get("message") or f"证券「{token}」解析失败", []
        rows = resp.get("data") or []
        if not rows:
            return None, f"证券「{token}」不存在", []
        info = rows[0] if isinstance(rows[0], dict) else {}
        code = _text(info.get("security_code"))
        abbr = _text(info.get("security_abbr")) or code
        if not code:
            return None, f"证券「{token}」缺少代码", []
        codes.append(code)
        pairs.append(f"{abbr}({code})")
    return codes or None, None, pairs


def _looks_like_id(token: str) -> bool:
    s = str(token).strip()
    return bool(s) and s.isdigit()


def _resolve_concepts(raw: Optional[List[str]]) -> Tuple[Optional[List[str]], Optional[str], List[str]]:
    tokens = _as_list(raw)
    if not tokens:
        return None, None, []
    headers = get_authorization_headers()
    ids: List[str] = []
    labels: List[str] = []
    for token in tokens:
        if _looks_like_id(token):
            if token not in ids:
                ids.append(token)
                labels.append(token)
            continue
        concept_id, msg, is_candidates = resolve_concept_keyword(headers, token)
        if concept_id:
            if concept_id not in ids:
                ids.append(concept_id)
                labels.append(f"{token}({concept_id})")
            continue
        if is_candidates:
            return None, msg, []
        return None, msg or f"主题概念「{token}」解析失败", []
    return ids or None, None, labels


def markdown_expert_intel_list(data: Dict[str, Any]) -> str:
    total = data.get("total", 0)
    rows = data.get("list") if isinstance(data.get("list"), list) else []
    lines: List[str] = [
        f"## AI专家情报（本页 {len(rows)} 条，接口 total={total}）",
        "",
    ]
    if not rows:
        lines.append("未找到符合条件的 AI 专家情报。")
        return "\n".join(lines).strip()

    for row in rows:
        if not isinstance(row, dict):
            continue
        main = row.get("mainSecurity") if isinstance(row.get("mainSecurity"), dict) else {}
        main_name = _text(main.get("securityName"))
        main_code = _text(main.get("securityCode"))
        title = _text(row.get("title")) or "（无标题）"
        heading = f"{main_name}（{main_code}） · {title}" if main_name or main_code else title
        lines.append(f"### {heading}")
        lines.append(f"- **情报 ID**：{_text(row.get('intelId')) or '-'}")
        lines.append(f"- **发布时间**：{_text(row.get('publishTime')) or '-'}")

        tags = row.get("tagList") if isinstance(row.get("tagList"), list) else []
        tag_text = "、".join(_text(t) for t in tags if _text(t))
        lines.append(f"- **内容标签**：{tag_text or '-'}")

        securities = row.get("securityList") if isinstance(row.get("securityList"), list) else []
        if securities:
            sec_bits = []
            for sec in securities:
                if not isinstance(sec, dict):
                    continue
                sn = _text(sec.get("securityName"))
                sc = _text(sec.get("securityCode"))
                if sn and sc:
                    sec_bits.append(f"{sn}({sc})")
                elif sn or sc:
                    sec_bits.append(sn or sc)
            if sec_bits:
                lines.append(f"- **关联证券**：{'、'.join(sec_bits)}")

        areas = row.get("researchAreaList") if isinstance(row.get("researchAreaList"), list) else []
        if areas:
            area_bits = []
            for area in areas:
                if not isinstance(area, dict):
                    continue
                an = _text(area.get("researchAreaName"))
                aid = _text(area.get("researchAreaId"))
                if an and aid:
                    area_bits.append(f"{an}({aid})")
                elif an or aid:
                    area_bits.append(an or aid)
            if area_bits:
                lines.append(f"- **研究方向**：{'、'.join(area_bits)}")

        concepts = row.get("conceptList") if isinstance(row.get("conceptList"), list) else []
        if concepts:
            concept_bits = []
            for concept in concepts:
                if not isinstance(concept, dict):
                    continue
                cn = _text(concept.get("conceptName"))
                cid = _text(concept.get("conceptId"))
                if cn and cid:
                    concept_bits.append(f"{cn}({cid})")
                elif cn or cid:
                    concept_bits.append(cn or cid)
            if concept_bits:
                lines.append(f"- **主题概念**：{'、'.join(concept_bits)}")

        lines.append("")
        lines.append("**正文**")
        lines.append("")
        lines.append(_text(row.get("content")) or "（无）")
        lines.append("")
        lines.append("---")
        lines.append("")

    while lines and lines[-1].strip() in ("", "---"):
        lines.pop()
    return "\n".join(lines).strip()


def format_expert_intel_payload(
    page_from: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    search_type: int = 2,
    keyword: Optional[str] = None,
    security_list: Optional[List[str]] = None,
    research_area_list: Optional[List[str]] = None,
    concept_list: Optional[List[str]] = None,
    tag_list: Optional[List[str]] = None,
) -> Dict[str, Any]:
    size = int(page_size) if page_size is not None else DEFAULT_PAGE_SIZE
    if size < 1:
        size = 1
    if size > PAGE_SIZE_MAX:
        size = PAGE_SIZE_MAX
    frm = int(page_from) if page_from is not None else 0
    if frm < 0:
        frm = 0

    stype = int(search_type) if search_type is not None else 2
    if stype not in (1, 2):
        raise ValueError("searchType 须为 1（标题）或 2（全文）")

    payload: Dict[str, Any] = {
        "from": frm,
        "size": size,
        "searchType": stype,
    }
    start = _validate_time(start_time, "startTime", end_of_day=False)
    end = _validate_time(end_time, "endTime", end_of_day=True)
    if start:
        payload["startTime"] = start
    if end:
        payload["endTime"] = end
    if keyword and str(keyword).strip():
        payload["keyword"] = str(keyword).strip()
    if security_list:
        payload["securityList"] = security_list
    if research_area_list:
        payload["researchAreaList"] = research_area_list
    if concept_list:
        payload["conceptList"] = concept_list
    if tag_list:
        payload["tagList"] = tag_list
    return payload


def normalize_expert_intel_response(body: Dict[str, Any]) -> Dict[str, Any]:
    ok = str(body.get("code", "")) == "000000" and body.get("status") is True
    if not ok:
        return {
            "state": "error",
            "message": body.get("msg", "请求失败"),
            "data": [],
            "usage": {},
        }

    raw_data = body.get("data")
    if isinstance(raw_data, dict):
        rows = [{"markdown": markdown_expert_intel_list(raw_data), "type": "expert-intel-list"}]
        n = len(raw_data.get("list", [])) if isinstance(raw_data.get("list"), list) else 0
        usage = {"expert-intel": n * POINTS_PER_ITEM} if n else {}
        tip = f"提示：本次成功返回 {n} 条情报，按 {POINTS_PER_ITEM} 积分/条计费。" if n else ""
    else:
        rows = [{"markdown": "（无数据）", "type": "expert-intel-list"}]
        usage = {}
        tip = ""

    return {
        "state": "success",
        "message": (body.get("msg", "请求成功") + ("\n" + tip if tip else "")).strip(),
        "data": [{"data": rows, "module": "agent", "type": "expert-intel-list"}],
        "usage": usage,
    }


def post_expert_intel_list(
    payload: Dict[str, Any],
    confirm: bool = False,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    url = EXPERT_INTEL_LIST_URL
    probe = {k: v for k, v in payload.items() if k not in ("from", "size")}
    guard_row_billed_fetch(
        url,
        probe,
        int(payload.get("size") or 0),
        confirm=confirm,
        start=int(payload.get("from") or 0),
    )
    headers = get_authorization_headers()
    resp = authorized_request("POST", url, headers=headers, json=payload, timeout=300)
    if resp.status_code != 200:
        return None, resp.text
    try:
        return resp.json(), None
    except Exception as e:
        return None, str(e)


def expert_intel(
    page_from: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    search_type: int = 2,
    keyword: Optional[str] = None,
    securities: Optional[List[str]] = None,
    research_area_list: Optional[List[str]] = None,
    concept_list: Optional[List[str]] = None,
    tag_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
    confirm: bool = False,
) -> str:
    if get_authorization_token() is None:
        return format_response(
            {"state": "error", "message": "未配置 gangtise 授权，无法调用 open 接口", "data": [], "usage": {}},
            METHOD_NAME,
            output_dir=output_dir,
        )

    security_codes, sec_err, sec_pairs = _resolve_securities(securities)
    if sec_err:
        return format_response(
            {"state": "error", "message": sec_err, "data": [], "usage": {}},
            METHOD_NAME,
            output_dir=output_dir,
        )

    concept_ids, concept_err, concept_labels = _resolve_concepts(concept_list)
    if concept_err:
        return format_response(
            {"state": "error", "message": concept_err, "data": [], "usage": {}},
            METHOD_NAME,
            output_dir=output_dir,
        )

    research_ids = _as_list(research_area_list) or None
    tags = _as_list(tag_list) or None

    try:
        payload = format_expert_intel_payload(
            page_from=page_from,
            page_size=page_size,
            start_time=start_time,
            end_time=end_time,
            search_type=search_type,
            keyword=keyword,
            security_list=security_codes,
            research_area_list=research_ids,
            concept_list=concept_ids,
            tag_list=tags,
        )
    except ValueError as e:
        return format_response(
            {"state": "error", "message": str(e), "data": [], "usage": {}},
            METHOD_NAME,
            output_dir=output_dir,
        )

    hints: List[str] = []
    if sec_pairs:
        hints.append("匹配证券：" + "、".join(sec_pairs))
    if concept_labels:
        hints.append("主题概念：" + "、".join(concept_labels))
    if hints:
        print("<!-- " + "；".join(hints) + " -->\n")

    body, err = post_expert_intel_list(payload=payload, confirm=confirm)
    if err is not None:
        return format_response(
            {"state": "error", "message": err, "data": [], "usage": {}},
            METHOD_NAME,
            output_dir=output_dir,
        )
    if body is None:
        return format_response(
            {"state": "error", "message": "空响应", "data": [], "usage": {}},
            METHOD_NAME,
            output_dir=output_dir,
        )
    return format_response(normalize_expert_intel_response(body), METHOD_NAME, output_dir=output_dir)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="AI专家情报列表（open-insight expertIntel/getList）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--page-from", type=int, default=0, help="分页起始偏移")
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"分页条数，最大 {PAGE_SIZE_MAX}",
    )
    parser.add_argument("-st", "--start-time", default=None, help="开始时间 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss")
    parser.add_argument("-et", "--end-time", default=None, help="结束时间 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss")
    parser.add_argument(
        "--search-type",
        type=int,
        default=2,
        help="搜索类型：1 标题 / 2 全文",
    )
    parser.add_argument("-k", "--keyword", default=None, help="搜索关键词")
    parser.add_argument("--securities", default=None, help="证券名称或代码，逗号分隔")
    parser.add_argument(
        "--research-areas",
        default=None,
        help="研究方向（行业）ID，逗号分隔；可通过常量接口 citicIndustry/swIndustry/gangtiseIndustry 获取",
    )
    parser.add_argument(
        "--concepts",
        default=None,
        help="主题概念 ID 或名称，逗号分隔；名称会自动解析为 ID",
    )
    parser.add_argument("--tags", default=None, help="内容标签纯文本，逗号分隔，如 景气上行,超预期")
    parser.add_argument("-od", "--output-dir", default=None, help="结果保存目录路径")
    parser.add_argument("--confirm", action="store_true", help="积分估算超防护线时确认继续")
    args = parser.parse_args()

    try:
        out = expert_intel(
            page_from=args.page_from,
            page_size=args.page_size,
            start_time=args.start_time,
            end_time=args.end_time,
            search_type=args.search_type,
            keyword=args.keyword,
            securities=_as_list(args.securities) or None,
            research_area_list=_as_list(args.research_areas) or None,
            concept_list=_as_list(args.concepts) or None,
            tag_list=_as_list(args.tags) or None,
            output_dir=args.output_dir,
            confirm=bool(args.confirm),
        )
    except ValidationError as exc:
        print(str(exc))
        sys.exit(getattr(exc, "exit_code", 1) or 1)
    print(out)


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors="ignore")
    main()
