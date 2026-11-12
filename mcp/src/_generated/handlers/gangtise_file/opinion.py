# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-file/scripts/opinion.py
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
import sys
from typing import Any, Dict, List, Optional, Tuple
import requests
from io import TextIOWrapper

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from .utils import (  # noqa: E402
    parse_bool_flag,
    get_authorization_token,
    get_headers_extra,
    OPINION_URL,
    FILE_DEFAULT_LIMIT,
    RESEARCH_AREA_MAP,
    INDUSTRIES_MAP,
    format_response,
    match_best,
    remove_html_tags,
    DOWNLOAD_DEFAULT,
    DOWNLOAD_TYPE_DEFAULT,
    resolve_result_limit)
from .get_file import download_files, guard_opinion_detail_download
from .security import batch_security_search
from .search_chief import SEARCH_TOP_DEFAULT, resolve_chief_token
from .search_institution import (
    CATEGORY_OPINION_INSTITUTION,
    USAGE_API_DOMESTIC_OPINION,
    USAGE_PARAM_BROKER_LIST,
    resolve_institution_tokens,
)
from gangtise_core.auth import authorized_request, get_authorization_headers
from gangtise_core.skill_runtime import ValidationError, guard_row_billed_fetch

# 观点类别 / 投研业务标签 / 机构标签：常量接口暂未挂载，按 OpenAPI 文档硬编码。
OPINION_CATEGORY_LABEL_BY_CODE = {
    "earningsReview": "业绩点评",
    "abnormalReview": "异动点评",
    "researchUpdate": "调研/访谈更新",
    "tradingDesk": "交易台",
    "industryAnalysis": "行业分析",
}
OPINION_CATEGORY_CODE_MAP = {
    "业绩点评": "earningsReview",
    "异动点评": "abnormalReview",
    "调研/访谈更新": "researchUpdate",
    "调研更新": "researchUpdate",
    "访谈更新": "researchUpdate",
    "交易台": "tradingDesk",
    "行业分析": "industryAnalysis",
}

OPINION_LLM_TAG_LABEL_BY_CODE = {
    # 推荐
    "strongRcmd": "强烈推荐",
    "undervalued": "低估值",
    "highElasticity": "高弹性",
    "highDividend": "高股息",
    "reversal": "拐点/反转",
    "bottom": "底部",
    "beatExpect": "超预期",
    "expectGap": "预期差",
    "oversold": "错杀/超跌",
    "targetPrice": "目标股价/市值",
    "certainty": "确定性",
    # 业绩侧
    "highGrowth": "高增（业绩等）",
    "withProfitForecast": "含盈利预测",
    "withGuidance": "含指引",
    "marginalImprovement": "边际改善",
    # 产业链
    "priceHike": "涨价",
    "tightSupplyDemand": "供需趋紧",
    "capacityRelease": "产能释放",
    "newOrder": "新订单",
    "orderSurge": "订单高增/大单",
    "keyCustomer": "大客户",
    "soleSupplier": "独供/一供",
    "coreSupplier": "核心供应商",
    "industryEntry": "产业导入",
    # 壁垒
    "leader": "龙头",
    "moat": "壁垒",
    "scarcity": "稀缺性",
    "breakthrough": "突破",
}
OPINION_LLM_TAG_CODE_MAP = {
    "强烈推荐": "strongRcmd",
    "低估值": "undervalued",
    "高弹性": "highElasticity",
    "高股息": "highDividend",
    "拐点/反转": "reversal",
    "拐点": "reversal",
    "反转": "reversal",
    "底部": "bottom",
    "超预期": "beatExpect",
    "预期差": "expectGap",
    "错杀/超跌": "oversold",
    "错杀": "oversold",
    "超跌": "oversold",
    "目标股价/市值": "targetPrice",
    "目标股价": "targetPrice",
    "目标市值": "targetPrice",
    "确定性": "certainty",
    "高增（业绩等）": "highGrowth",
    "高增": "highGrowth",
    "含盈利预测": "withProfitForecast",
    "含指引": "withGuidance",
    "边际改善": "marginalImprovement",
    "涨价": "priceHike",
    "供需趋紧": "tightSupplyDemand",
    "产能释放": "capacityRelease",
    "新订单": "newOrder",
    "订单高增/大单": "orderSurge",
    "订单高增": "orderSurge",
    "大单": "orderSurge",
    "大客户": "keyCustomer",
    "独供/一供": "soleSupplier",
    "独供": "soleSupplier",
    "一供": "soleSupplier",
    "核心供应商": "coreSupplier",
    "产业导入": "industryEntry",
    "龙头": "leader",
    "壁垒": "moat",
    "稀缺性": "scarcity",
    "突破": "breakthrough",
}

OPINION_BROKER_TAG_LABEL_BY_CODE = {
    "topBroker": "头部券商",
    "newFortune": "新财富团队",
}
OPINION_BROKER_TAG_CODE_MAP = {
    "头部券商": "topBroker",
    "新财富团队": "newFortune",
    "新财富": "newFortune",
}

OPINION_SOURCE_MAP = {
    "实时": "realTime",
    "开放来源": "openSource",
}

OPINION_CATEGORY_CODES = frozenset(OPINION_CATEGORY_LABEL_BY_CODE.keys())
OPINION_LLM_CODES = frozenset(OPINION_LLM_TAG_LABEL_BY_CODE.keys())
OPINION_BROKER_TAG_CODES = frozenset(OPINION_BROKER_TAG_LABEL_BY_CODE.keys())
OPINION_SOURCE_CODES = frozenset(OPINION_SOURCE_MAP.values())


def _display_codes(codes, label_by_code: dict) -> str:
    if not isinstance(codes, list) or not codes:
        return ""
    parts = []
    for x in codes:
        if not x:
            continue
        key = str(x).strip()
        parts.append(label_by_code.get(key, key))
    return ", ".join(parts)


def _resolve_code_list(
    raw_items: Optional[List[str]],
    label_to_code: dict,
    valid_codes: frozenset,
) -> List[str]:
    if not raw_items:
        return []
    out: List[str] = []
    for t in raw_items:
        if not t:
            continue
        s = str(t).strip()
        if not s:
            continue
        if s in valid_codes:
            code = s
        elif s in label_to_code:
            code = label_to_code[s]
        else:
            code = s
        if code not in out:
            out.append(code)
    return out


def _normalize_api_time(s: Optional[str], end_of_day: bool) -> Optional[str]:
    """接口 startTime/endTime：yyyy-MM-dd HH:mm:ss，兼容仅传 yyyy-MM-dd。"""
    if not s or not str(s).strip():
        return None
    t = str(s).strip()
    if len(t) <= 10:
        d = t[:10]
        return f"{d} 23:59:59" if end_of_day else f"{d} 00:00:00"
    return t


def _format_opinion_item(items: List[dict]) -> List[dict]:
    _results = []
    for row in items:
        content_list = row.get("contentList") if isinstance(row.get("contentList"), dict) else {}
        title = remove_html_tags(row.get("title") or content_list.get("title") or "")
        # 列表接口仅返回 brief（正文前 200 字）；兼容旧字段 contentList.content
        brief = remove_html_tags(
            row.get("brief")
            or content_list.get("brief")
            or ""
        )
        if not brief:
            legacy = remove_html_tags(content_list.get("content") or row.get("content") or "")
            brief = legacy[:200] if legacy else ""

        author = row.get("author") or {}
        chief_name = author.get("chiefName") or ""
        chief_id = author.get("chiefId") or ""
        chief_display = f"{chief_name}({chief_id})" if chief_id else chief_name

        research_areas = author.get("researchAreaList") or []
        ra_display = ", ".join([str(x) for x in research_areas if x]) if isinstance(research_areas, list) else ""

        broker_name = author.get("brokerName") or ""
        broker_id = author.get("brokerID") or ""
        broker_display = f"{broker_name}({broker_id})" if broker_id else broker_name

        security_items = row.get("securityList") or []
        stock_parts: List[str] = []
        for s in security_items:
            if not isinstance(s, dict):
                continue
            code = s.get("securityCode") or ""
            name = s.get("securityName") or ""
            if code:
                part = f"{name}({code})" if name else f"({code})"
                if part not in stock_parts:
                    stock_parts.append(part)
        stock_display = ", ".join(stock_parts)

        industry_items = row.get("industryList") or []
        ind_parts: List[str] = []
        for i in industry_items:
            if not isinstance(i, dict):
                continue
            ic = i.get("industryCode") or ""
            iname = i.get("industryName") or ""
            if ic or iname:
                part = f"{iname}({ic})" if ic else iname
                if part not in ind_parts:
                    ind_parts.append(part)
        industry_display = ", ".join(ind_parts)

        concept_items = row.get("conceptList") or []
        con_parts: List[str] = []
        for c in concept_items:
            if not isinstance(c, dict):
                continue
            cid = c.get("conceptId") or ""
            cname = c.get("conceptName") or ""
            if cid or cname:
                part = f"{cname}({cid})" if cid else cname
                if part not in con_parts:
                    con_parts.append(part)
        concept_display = ", ".join(con_parts)

        item = {
            "标题": title,
            "文件时间": (row.get("publishTime") or "") or "",
            "摘要": brief + ("..." if brief else ""),
            "首席": chief_display,
            "券商": broker_display,
            "研究方向": ra_display,
            "关联股票": stock_display,
            "关联行业": industry_display,
            "概念": concept_display,
            "观点类别": _display_codes(row.get("categoryList") or [], OPINION_CATEGORY_LABEL_BY_CODE),
            "投研业务标签": _display_codes(row.get("llmTagList") or [], OPINION_LLM_TAG_LABEL_BY_CODE),
            "机构标签": _display_codes(row.get("brokerTagList") or [], OPINION_BROKER_TAG_LABEL_BY_CODE),
            "类型": "首席观点",
            "类型ID": str(row.get("chiefOpinionId") or ""),
        }
        _results.append(item)
    return _results


def _resolve_research_areas(industries: Optional[List[str]]) -> Tuple[List[str], List[str], List[str]]:
    """CLI 参数 industries → (researchAreaList, industryList, 无法识别的名称)。"""
    if not industries:
        return [], [], []
    area_ids = {str(v) for v in RESEARCH_AREA_MAP.values()}
    industry_map: Dict[str, Any] = {}
    for group in INDUSTRIES_MAP.values():
        industry_map.update(group)
    industry_ids = {str(v) for v in industry_map.values()}
    areas: List[str] = []
    inds: List[str] = []
    unknown: List[str] = []
    for raw in industries:
        s = (raw or "").strip()
        if not s:
            continue
        if s in area_ids or s in RESEARCH_AREA_MAP:
            sid = s if s in area_ids else str(RESEARCH_AREA_MAP[s])
            target = areas
        elif s in industry_ids or s in industry_map:
            sid = s if s in industry_ids else str(industry_map[s])
            target = inds
        else:
            m = match_best(s, list(RESEARCH_AREA_MAP.keys()))
            if m:
                sid, target = str(RESEARCH_AREA_MAP[m]), areas
            else:
                m = match_best(s, list(industry_map.keys()))
                if not m:
                    unknown.append(s)
                    continue
                sid, target = str(industry_map[m]), inds
        if sid not in target:
            target.append(sid)
    return areas, inds, unknown


def _resolve_chiefs(
    chiefs: Optional[List[str]],
    headers: dict,
    top: int = SEARCH_TOP_DEFAULT,
) -> Tuple[List[str], List[str], Optional[str]]:
    """将 --chiefs 中的 chiefId 或关键词解析为 API chiefList。"""
    if not chiefs:
        return [], [], None

    resolved: List[str] = []
    notes: List[str] = []

    for raw in chiefs:
        token = raw.strip()
        if not token:
            continue
        chief_id, msg, is_candidates = resolve_chief_token(token, headers, top)
        if is_candidates:
            return [], [], msg
        if chief_id:
            if chief_id not in resolved:
                resolved.append(chief_id)
        elif msg:
            notes.append(f"首席「{token}」：{msg}")

    return resolved, notes, None


def _resolve_llm_tags(tags: Optional[List[str]]) -> List[str]:
    return _resolve_code_list(tags, OPINION_LLM_TAG_CODE_MAP, OPINION_LLM_CODES)


def _resolve_categories(tags: Optional[List[str]]) -> List[str]:
    return _resolve_code_list(tags, OPINION_CATEGORY_CODE_MAP, OPINION_CATEGORY_CODES)


def _resolve_broker_tags(tags: Optional[List[str]]) -> List[str]:
    return _resolve_code_list(tags, OPINION_BROKER_TAG_CODE_MAP, OPINION_BROKER_TAG_CODES)


def _resolve_opinion_sources(source_types: Optional[List[str]]) -> List[str]:
    return _resolve_code_list(source_types, OPINION_SOURCE_MAP, OPINION_SOURCE_CODES)


def _clean_keyword(
    keyword: str,
    securities=None,
    institutions=None,
    industries=None,
    chiefs=None,
    concepts=None,
    categories=None,
    llm_tags=None,
    broker_tags=None,
    source_types=None,
):
    if not keyword:
        return ""
    keyword = (
        keyword.replace("[", "").replace("]", "")
        .replace("、", " ").replace("，", " ")
        .replace(", ", " ").replace(",", " ")
    )
    for items in [
        securities, institutions, industries, chiefs, concepts,
        categories, llm_tags, broker_tags, source_types,
    ]:
        if items:
            for item in items:
                keyword = keyword.replace(item, "")
    return keyword.strip()


def _fetch_opinions(headers, payload_base, keyword, limit, confirm=False):
    max_page_size = 50
    probe = {**payload_base, "keyword": keyword} if keyword else dict(payload_base)
    guard_row_billed_fetch(OPINION_URL, probe, limit, confirm=confirm)
    all_results = []
    offset = 0
    remaining = limit

    while remaining > 0:
        page_size = min(remaining, max_page_size)
        data = {**payload_base, "from": offset, "size": page_size}
        if keyword:
            data["keyword"] = keyword
        response = authorized_request("POST", OPINION_URL, headers=headers, json=data)
        if response.status_code != 200:
            if all_results:
                return all_results, response.text.replace("\n", " ").replace("\r", " ").strip()
            return None, response.text.replace("\n", " ").replace("\r", " ").strip()
        result = response.json()

        from gangtise_core.skill_runtime import unwrap
        result = {"data": unwrap(result, http=response.status_code) or {}}

        block = result.get("data") or {}
        rows = block.get("list") or []
        if not rows:
            break

        all_results.extend(_format_opinion_item(rows))

        if len(rows) < page_size:
            break

        offset += page_size
        remaining -= len(rows)

    return all_results, None


def opinion_finder(
    keyword: str = "",
    securities: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    institutions: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    chiefs: Optional[List[str]] = None,
    concepts: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    llm_tags: Optional[List[str]] = None,
    broker_tags: Optional[List[str]] = None,
    source_types: Optional[List[str]] = None,
    rank_type: int = 1,
    limit: Optional[int] = None,
    download: bool = False,
    download_types: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
    confirm: bool = False,
):
    try:
        limit = resolve_result_limit(limit, download, "opinion")
        if download:
            guard_opinion_detail_download(limit, confirm)
        headers = get_authorization_headers()

        research_area_ids, industry_ids, unknown_industries = _resolve_research_areas(industries)
        if unknown_industries:
            return format_response(
                {"state": "error", "message": f"无法识别的行业/研究方向：{'、'.join(unknown_industries)}（可选值见 get_industries）"},
                "opinion", output_dir=output_dir)
        broker_ids: List[str] = []
        if institutions:
            broker_ids, inst_notes, inst_candidates = resolve_institution_tokens(
                institutions,
                headers,
                [CATEGORY_OPINION_INSTITUTION],
                USAGE_PARAM_BROKER_LIST,
                USAGE_API_DOMESTIC_OPINION,
            )
            if inst_candidates:
                return format_response(
                    {"state": "error", "message": inst_candidates},
                    "opinion", output_dir=output_dir)
            if not broker_ids:
                msg = "机构解析失败"
                if inst_notes:
                    msg += "：" + "；".join(inst_notes)
                return format_response({"state": "error", "message": msg}, "opinion", output_dir=output_dir)
        category_resolved = _resolve_categories(categories) if categories else []
        llm_resolved = _resolve_llm_tags(llm_tags) if llm_tags else []
        broker_tag_resolved = _resolve_broker_tags(broker_tags) if broker_tags else []
        source_resolved = _resolve_opinion_sources(source_types) if source_types else []

        securities_input = list(securities) if securities else []
        if securities_input:
            tokens = [str(s).strip() for s in securities_input if str(s).strip()]
            resolved = batch_security_search(
                tokens, category=["stock", "dr"], headers=headers, output_limit=1
            )
            if resolved.get("state") != "success":
                return format_response(
                    {"state": "error", "message": resolved.get("message") or "证券解析失败"},
                    "opinion", output_dir=output_dir)
            securities = resolved["codes"]
        else:
            securities = None

        chief_list: List[str] = []
        chief_notes: List[str] = []
        if chiefs:
            chief_list, chief_notes, chief_candidates = _resolve_chiefs(chiefs, headers)
            if chief_candidates:
                return format_response(
                    {"state": "error", "message": chief_candidates},
                    "opinion", output_dir=output_dir)
            if not chief_list:
                msg = "首席解析失败"
                if chief_notes:
                    msg += "：" + "；".join(chief_notes)
                return format_response({"state": "error", "message": msg}, "opinion", output_dir=output_dir)

        concept_list: List[str] = []
        if concepts:
            concept_list = [c.strip() for c in concepts if c and c.strip()]

        start_time = _normalize_api_time(start_date, end_of_day=False)
        end_time = _normalize_api_time(end_date, end_of_day=True)

        keyword_str = _clean_keyword(
            keyword=keyword,
            securities=securities_input if securities_input else None,
            institutions=institutions,
            industries=industries,
            chiefs=chiefs,
            concepts=concepts,
            categories=categories,
            llm_tags=llm_tags,
            broker_tags=broker_tags,
            source_types=source_types,
        )

        payload_base: dict = {
            "rankType": rank_type,
        }
        if start_time:
            payload_base["startTime"] = start_time
        if end_time:
            payload_base["endTime"] = end_time
        if research_area_ids:
            payload_base["researchAreaList"] = research_area_ids
        if industry_ids:
            payload_base["industryList"] = industry_ids
        if broker_ids:
            payload_base["brokerList"] = broker_ids
        if securities:
            payload_base["securityList"] = securities
        if chief_list:
            payload_base["chiefList"] = chief_list
        if concept_list:
            payload_base["conceptList"] = concept_list
        if category_resolved:
            payload_base["categoryList"] = category_resolved
        if llm_resolved:
            payload_base["llmTagList"] = llm_resolved
        if broker_tag_resolved:
            payload_base["brokerTagList"] = broker_tag_resolved
        if source_resolved:
            payload_base["sourceList"] = source_resolved

        all_results, err = _fetch_opinions(headers, payload_base, keyword_str, limit, confirm=confirm)
        if err and not all_results:
            return format_response({"state": "error", "message": err}, "opinion", output_dir=output_dir)
        part_error_message = ""
        if err and all_results:
            part_error_message = f"未完整获取全部结果，错误信息：{err}"
        if chief_notes:
            chief_msg = "；".join(chief_notes)
            part_error_message = (
                f"{part_error_message}；{chief_msg}" if part_error_message else chief_msg
            )

        if not all_results:
            return format_response(
                {"state": "error", "message": "未找到相关观点，建议修改查询条件", "data": []},
                "opinion", output_dir=output_dir)

        all_results = all_results[:limit]

        additional_message = None
        if download:
            dts = download_types or ["txt"]
            additional_message = download_files(
                all_results, "opinion", output_dir, download_types=dts
            ) + ("\n\n" + part_error_message if part_error_message else "")
        elif part_error_message:
            additional_message = part_error_message

        response_data = {
            "state": "success",
            "message": "已找到相关观点",
            "data": [{"data": all_results, "module": "opinion", "type": "files"}],
        }
        return format_response(response_data, "opinion", additional_message=additional_message or "", output_dir=output_dir)
    except ValidationError:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        return format_response(
            {"state": "error", "message": str(e), "data": [], "usage": {}},
            "opinion", output_dir=output_dir)


def _parse_str_list(raw: str) -> Optional[List[str]]:
    if not raw:
        return None
    items = [
        x.strip()
        for x in raw.replace("，", ",").split(",")
        if x.strip()
    ]
    return items or None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="首席观点检索：按关键词、证券、券商、研究方向、首席、概念、标签等查询观点列表；可选 -d 通过 getDetail 下载正文。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-k", "--keyword", default="", help="搜索关键词，可为空")
    parser.add_argument("-sd", "--start-date", default="", help="开始时间：YYYY-MM-DD（自动补 00:00:00）或 yyyy-MM-dd HH:mm:ss")
    parser.add_argument("-ed", "--end-date", default="", help="结束时间：YYYY-MM-DD（自动补 23:59:59）或 yyyy-MM-dd HH:mm:ss")
    parser.add_argument(
        "-l",
        "--limit",
        default=None,
        type=int,
        help="返回条数上限；不传时用检索默认，开启 -d 下载时默认 10",
    )
    parser.add_argument(
        "--rank-type",
        default=1,
        type=int,
        choices=[1, 2],
        help="排序：1 综合排序，2 时间倒序",
    )
    parser.add_argument(
        "--securities",
        default="",
        help="证券代码列表，逗号分隔，如 000001.SZ",
    )
    parser.add_argument(
        "--industries",
        default="",
        help="行业或研究方向，逗号分隔：研究方向（宏观/策略/固收/金工/海外）映射为 researchAreaList，行业（见 get_industries）映射为 industryList",
    )
    parser.add_argument(
        "--institutions",
        default="",
        help="发布机构（券商）列表，逗号分隔",
    )
    parser.add_argument(
        "--chiefs",
        default="",
        help="首席分析师列表，逗号分隔：支持 P 开头 ID 或姓名（模糊匹配，重名时请传 ID）",
    )
    parser.add_argument(
        "--concepts",
        default="",
        help="概念 ID 列表，逗号分隔",
    )
    parser.add_argument(
        "--categories",
        default="",
        help=(
            "观点类别，逗号分隔。英文：earningsReview/abnormalReview/researchUpdate/"
            "tradingDesk/industryAnalysis；或中文：业绩点评/异动点评/调研更新/交易台/行业分析"
        ),
    )
    parser.add_argument(
        "--llm-tags",
        default="",
        help=(
            "投研业务标签，逗号分隔（推荐/业绩侧/产业链/壁垒，共 28 项）。"
            "如 strongRcmd/beatExpect/highGrowth/soleSupplier/moat，或中文强烈推荐/超预期/高增/独供/壁垒"
        ),
    )
    parser.add_argument(
        "--broker-tags",
        default="",
        help="机构标签，逗号分隔：topBroker/newFortune 或 头部券商/新财富团队",
    )
    parser.add_argument(
        "--source-types",
        default="",
        help="来源，逗号分隔：realTime/openSource 或 实时/开放来源",
    )
    parser.add_argument(
        "-d",
        "--download",
        default=DOWNLOAD_DEFAULT,
        type=parse_bool_flag,
        nargs="?",
        const=True,
        help="检索后按观点 ID 调用 getDetail 下载正文原文（按条计费）",
    )
    parser.add_argument(
        "-od",
        "--output-dir",
        default=None,
        help="结果与下载文件保存目录路径，建议使用绝对路径",
    )
    parser.add_argument(
        "-dt",
        "--download-types",
        default=DOWNLOAD_TYPE_DEFAULT.get("opinion", "txt") or "txt",
        help="下载格式，逗号分隔：txt / md（正文相同，仅后缀不同）",
    )
    parser.add_argument("--yes", "--confirm", dest="confirm", action="store_true", help="确认积分消耗较大的拉取（须先征得用户同意）")

    args = parser.parse_args()

    keyword = args.keyword or ""
    securities = _parse_str_list(args.securities)
    institutions = _parse_str_list(args.institutions)
    industries = _parse_str_list(args.industries)
    chiefs = _parse_str_list(args.chiefs)
    concepts = _parse_str_list(args.concepts)
    categories = _parse_str_list(args.categories)
    llm_tags = _parse_str_list(args.llm_tags)
    broker_tags = _parse_str_list(args.broker_tags)
    source_types = _parse_str_list(args.source_types)
    start_date = args.start_date or None
    end_date = args.end_date or None
    limit = resolve_result_limit(args.limit, bool(args.download), "opinion")
    rank_type = int(args.rank_type)
    download_types = [
        x.strip().lower()
        for x in str(args.download_types or "txt").replace("，", ",").split(",")
        if x.strip()
    ] or ["txt"]

    out = opinion_finder(
        keyword=keyword,
        securities=securities,
        start_date=start_date,
        end_date=end_date,
        institutions=institutions,
        industries=industries,
        chiefs=chiefs,
        concepts=concepts,
        categories=categories,
        llm_tags=llm_tags,
        broker_tags=broker_tags,
        source_types=source_types,
        rank_type=rank_type,
        limit=limit,
        download=bool(args.download),
        download_types=download_types,
        output_dir=args.output_dir or None,
        confirm=bool(args.confirm),
    )
    print(out)


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors='ignore')
    main()
