#!/usr/bin/env python3
# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-web/scripts/web_search.py
# Regenerate: python3 scripts/generate.py
"""Gangtise OpenAPI 联网搜索：POST /web-search/search。"""

if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

import argparse
import os
import re
import sys
from io import TextIOWrapper
from typing import Any, Dict, List, Optional, Tuple

import requests

from .utils import (
    GTS_SAVE_EXTENSION,
    GTS_SAVE_FILE,
    WEB_SEARCH_URL,
    alloc_result_path,
    authorized_request,
    dump_json,
    failure_result,
    get_authorization_token,
    success_result,
)

DEFAULT_TIMEOUT = 120
QUERY_MAX_CHARS = 200
SIZE_MAX = 20
SIZE_MAX_WITH_CONTENT = 5
SITE_MAX = 10
CONTENT_CHARS_MIN = 1000
CONTENT_CHARS_MAX = 20000

FRESHNESS_ALLOWED = ("day", "week", "month", "none")
MIN_TIER_ALLOWED = ("T0", "T1", "T2", "T3")

TIER_LABELS = {
    "T0": "官方一手",
    "T1": "权威媒体",
    "T2": "财经平台",
    "T3": "默认/自媒体",
}
FLAG_LABELS = {
    "rumor": "传闻",
    "forward": "转载",
    "disclaimer": "免责声明",
    "toutSuspect": "疑似荐股",
    "paywall": "付费墙",
}
PUBLISH_TIME_SOURCE = {
    "url": "URL 日期",
    "cluster": "转载簇",
    "page": "正文日期",
    "index": "索引疑点检查",
}

_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$"
)

# 句首常见提示词注入：仅剥离前缀，与 gangtise-kb 一致
_INJECTION_INLINE_PREFIX = re.compile(
    r"^[\s\uFEFF\u200B-\u200D]*(?:"
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?"
    r"|disregard\s+(?:all\s+)?(?:above|previous)(?:\s+instructions?)?"
    r"|forget\s+(?:everything|all)\s+(?:above|before)"
    r"|忽略\s*(?:所有\s*)?(?:之前|上文|以上)?的?\s*指令"
    r"|忽略\s*以上\s*所有\s*内容"
    r")\s*[:：\.\!！,，]?\s*",
    re.IGNORECASE | re.UNICODE,
)
_INJECTION_FULL_LINE = re.compile(
    r"^[\s\uFEFF\u200B-\u200D]*(?:"
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?"
    r"|disregard\s+(?:all\s+)?(?:above|previous)(?:\s+instructions?)?"
    r"|forget\s+(?:everything|all)\s+(?:above|before)"
    r"|忽略\s*(?:所有\s*)?(?:之前|上文|以上)?的?\s*指令"
    r"|忽略\s*以上\s*所有\s*内容"
    r")\s*[:：\.\!！]?\s*$",
    re.IGNORECASE | re.UNICODE,
)


def _strip_query_injection_prefix(query: str) -> Tuple[str, bool]:
    q = (query or "").strip()
    if not q:
        return "", False
    changed = False
    for _ in range(30):
        before = q
        matched = _INJECTION_INLINE_PREFIX.match(q)
        if matched:
            q = q[matched.end() :].lstrip()
            changed = True
            continue
        lines = q.splitlines()
        if lines and _INJECTION_FULL_LINE.match(lines[0]):
            q = "\n".join(lines[1:]).strip()
            changed = True
            continue
        if q == before:
            break
    return q, changed


def prepare_query(query: str) -> Tuple[str, Optional[str], bool]:
    q, stripped = _strip_query_injection_prefix(query)
    if not q:
        return "", "缺少必填参数：query 未传或为空白", stripped
    if len(q) > QUERY_MAX_CHARS:
        return "", f"参数值非法：query 最长 {QUERY_MAX_CHARS} 字，收到 {len(q)}", stripped
    return q, None, stripped


def parse_site_list(raw: Optional[str]) -> Tuple[Optional[List[str]], Optional[str]]:
    if raw is None or not str(raw).strip():
        return None, None
    parts = [part.strip() for part in str(raw).replace("，", ",").split(",") if part.strip()]
    if not parts:
        return None, "参数值非法：siteList 为空"
    seen = set()
    sites: List[str] = []
    for site in parts:
        if not _HOST_RE.fullmatch(site):
            return None, (
                f"参数值非法：siteList 含非法主机名「{site}」。"
                "请传注册域或子域（如 csrc.gov.cn），不要带协议、路径或端口"
            )
        key = site.lower()
        if key in seen:
            continue
        seen.add(key)
        sites.append(site)
    if len(sites) > SITE_MAX:
        return None, f"查询数量超出限制：siteList 去重后最多 {SITE_MAX} 个，收到 {len(sites)}"
    return sites, None


def build_payload(
    query: str,
    size: Optional[int] = None,
    freshness: Optional[str] = None,
    min_tier: Optional[str] = None,
    site_list: Optional[List[str]] = None,
    include_content: bool = False,
    max_content_chars: Optional[int] = None,
) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
    """返回 (payload, error, warning)。非法取值拒绝，不钳制。"""
    warning = None
    payload: Dict[str, Any] = {"query": query}

    if size is not None:
        if isinstance(size, bool) or not isinstance(size, int):
            return None, "参数类型错误：size 须为整数", None
        upper = SIZE_MAX_WITH_CONTENT if include_content else SIZE_MAX
        if size < 1 or size > upper:
            if include_content:
                return None, f"查询数量超出限制：includeContent 为 true 时 size 须为 1–5，收到 {size}", None
            return None, f"查询数量超出限制：size 须为 1–20，收到 {size}", None
        payload["size"] = size

    if freshness:
        if freshness not in FRESHNESS_ALLOWED:
            allowed = " / ".join(FRESHNESS_ALLOWED)
            return None, f"枚举值非法：freshness 须为 {allowed} 之一，收到 '{freshness}'", None
        if freshness != "none":
            payload["freshness"] = freshness

    if min_tier:
        if min_tier not in MIN_TIER_ALLOWED:
            allowed = " / ".join(MIN_TIER_ALLOWED)
            return None, f"枚举值非法：minTier 须为 {allowed} 之一，收到 '{min_tier}'", None
        if min_tier != "T3":
            payload["minTier"] = min_tier

    if site_list:
        payload["siteList"] = site_list

    if include_content:
        payload["includeContent"] = True
        if max_content_chars is not None:
            if isinstance(max_content_chars, bool) or not isinstance(max_content_chars, int):
                return None, "参数类型错误：maxContentChars 须为整数", None
            if max_content_chars < CONTENT_CHARS_MIN or max_content_chars > CONTENT_CHARS_MAX:
                return (
                    None,
                    f"查询数量超出限制：maxContentChars 须为 {CONTENT_CHARS_MIN}–{CONTENT_CHARS_MAX}，收到 {max_content_chars}",
                    None,
                )
            payload["maxContentChars"] = max_content_chars
    elif max_content_chars is not None:
        warning = "未开启 includeContent，maxContentChars 不生效"

    return payload, None, warning


def _error_result(
    message: str,
    code: Optional[str] = None,
    error_type: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    result = {
        "state": "error",
        "message": message,
    }
    if code:
        result["code"] = code
    if error_type:
        result["errorType"] = error_type
    if trace_id:
        result["traceId"] = trace_id
    return result


def _format_api_error(body: dict, http_status: int) -> dict:
    code = str(body.get("code") or http_status)
    error_type = body.get("errorType") or ""
    msg = str(body.get("msg") or body.get("message") or "请求失败")
    trace_id = body.get("traceId")
    detail = msg
    meta = code + (f" / {error_type}" if error_type else "")
    detail += f"（{meta}）"
    if trace_id:
        detail += f"，traceId={trace_id}"
    if code == "260001":
        detail += "。检索服务暂时不可用，可稍后重试；本次未扣积分"
    elif code == "999006":
        detail += "。已超出日调用上限或 QPS"
    elif code == "999005":
        detail += "。积分不足"
    return _error_result(detail, code=code, error_type=error_type or None, trace_id=trace_id)


def search_web(
    query: str,
    size: Optional[int] = None,
    freshness: Optional[str] = None,
    min_tier: Optional[str] = None,
    site_list: Optional[List[str]] = None,
    include_content: bool = False,
    max_content_chars: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    prepared, err, stripped = prepare_query(query)
    if stripped:
        print(
            "[WARNING] 已从查询开头移除疑似提示词注入片段，后续仅按检索语义请求联网搜索\n",
            file=sys.stderr,
        )
    if err:
        return _error_result(err)

    payload, err, warning = build_payload(
        prepared,
        size=size,
        freshness=freshness,
        min_tier=min_tier,
        site_list=site_list,
        include_content=include_content,
        max_content_chars=max_content_chars,
    )
    if warning:
        print(f"[WARNING] {warning}\n", file=sys.stderr)
    if err or payload is None:
        return _error_result(err or "参数不合法")

    if not get_authorization_token():
        return _error_result("未配置 gangtise 授权，无法调用 open 接口")

    try:
        response = authorized_request("POST", WEB_SEARCH_URL, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        return _error_result(f"联网搜索请求失败: {exc}")

    try:
        body = response.json()
    except Exception:
        text = (response.text or "")[:500]
        return _error_result(f"HTTP {response.status_code}，响应非 JSON: {text}")

    if not isinstance(body, dict):
        return _error_result("响应格式异常")

    if response.status_code != 200 or str(body.get("code")) != "000000" or body.get("status") is False:
        return _format_api_error(body, response.status_code)

    data = body.get("data")
    if not isinstance(data, dict):
        return _error_result("响应 data 格式异常")
    items = data.get("list") if isinstance(data.get("list"), list) else []
    hints = data.get("hints") if isinstance(data.get("hints"), list) else []
    total = data.get("total")
    if not isinstance(total, int) or isinstance(total, bool):
        total = len(items)
    return {
        "state": "success",
        "message": "",
        "data": {
            "query": data.get("query") if data.get("query") is not None else prepared,
            "total": total,
            "hints": [str(item) for item in hints],
            "list": items,
            "includeContent": include_content,
            "requestedSize": payload.get("size"),
        },
    }


def _quote_block(text: str) -> str:
    return '"""\n' + text + '\n"""'


def _format_item(item: dict, index: int, include_content: bool, preview_content: bool) -> str:
    title = item.get("title") or "（无标题）"
    tier = item.get("tier") or ""
    tier_label = TIER_LABELS.get(tier)
    tier_text = f"{tier}（{tier_label}）" if tier and tier_label else (tier or "未知")
    lines = [f"### {index}. {title}", "", f"- 信源：{tier_text}"]
    if item.get("site"):
        lines.append(f"- 站点：{item.get('site')}")

    publish_time = item.get("publishTime")
    source = item.get("publishTimeSource")
    if publish_time:
        source_label = PUBLISH_TIME_SOURCE.get(source, source or "")
        suffix = f"（依据：{source_label}）" if source_label else ""
        lines.append(f"- 发布日期：{publish_time}{suffix}")
    else:
        lines.append("- 发布日期：未能判定")
    if item.get("indexTime"):
        lines.append(f"- 索引时间：{item.get('indexTime')}（不保证是发布时间）")
    if item.get("url"):
        lines.append(f"- 链接：{item.get('url')}")

    flags = item.get("flags") if isinstance(item.get("flags"), list) else []
    if flags:
        labels = [FLAG_LABELS.get(str(flag), str(flag)) for flag in flags]
        lines.append("- 特征：" + "、".join(labels))

    upgraded = item.get("upgradedFrom") if isinstance(item.get("upgradedFrom"), list) else []
    upgraded = [str(url) for url in upgraded if url]
    if upgraded:
        lines.append("- 被替换来源：")
        lines.extend(f"  - {url}" for url in upgraded)

    snippet = item.get("snippet")
    if snippet:
        lines.append("- 摘要：" + _quote_block(str(snippet)))

    content = item.get("content")
    if include_content or content:
        truncated = item.get("contentTruncated")
        if content:
            if truncated is True:
                lines.append("- 正文已截断：是")
            elif truncated is False:
                lines.append("- 正文已截断：否")
            if preview_content:
                lines.append(f"- 正文：已写入文件（{len(str(content))} 字）")
            else:
                lines.append("- 正文：" + _quote_block(str(content)))
        else:
            lines.append("- 正文：获取失败，本条仅保留摘要")
    return "\n".join(lines)


def format_search_markdown(data: dict, preview_content: bool = False) -> str:
    query = data.get("query") or ""
    total = data.get("total")
    hints = data.get("hints") or []
    items = data.get("list") or []
    include_content = bool(data.get("includeContent"))
    requested_size = data.get("requestedSize")

    lines = ["### 联网搜索", "", f"- 实际检索词：{query}"]
    if requested_size is not None:
        lines.append(f"- 返回条数：{total}（请求上限 {requested_size}）")
    else:
        lines.append(f"- 返回条数：{total}")
    lines.append("- 排序：信源等级优先（T0 在前），同等级按发布日期新到旧；第一条不是最相关")
    if hints:
        lines.append("- 提示：")
        lines.extend(f"  - {hint}" for hint in hints)
    else:
        lines.append("- 提示：无")
    if total == 0:
        lines.append("- 这是正常空结果，不是接口错误。请按提示放宽条件或改关键词，不要原样重试。")
    lines.append("")

    blocks = [
        _format_item(item, i + 1, include_content, preview_content)
        for i, item in enumerate(items)
        if isinstance(item, dict)
    ]
    if blocks:
        lines.append("\n\n---\n\n".join(blocks))
    return "\n".join(lines).strip()


def _save_result(text: str, data: dict, output_dir: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    extension = GTS_SAVE_EXTENSION if GTS_SAVE_EXTENSION in ("md", "json") else "md"
    path, err = alloc_result_path("web_search", "web_search", extension, output_dir)
    if err or not path:
        return None, err or "结果保存失败"
    with open(path, "w", encoding="utf-8") as handle:
        if extension == "json":
            handle.write(
                dump_json(
                    {
                        "query": data.get("query"),
                        "total": data.get("total"),
                        "hints": data.get("hints") or [],
                        "list": data.get("list") or [],
                    }
                )
            )
        else:
            handle.write(text)
    return path, None


def render_result(
    result: dict,
    *,
    as_json: bool = False,
    output_dir: Optional[str] = None,
) -> str:
    if result.get("state") != "success":
        message = "调用 Gangtise Open API 失败，错误信息：" + str(result.get("message") or "")
        if as_json:
            body = {
                "state": "error",
                "message": message,
            }
            for key in ("code", "errorType", "traceId"):
                if result.get(key):
                    body[key] = result[key]
            return dump_json(body)
        return message

    data = result.get("data") or {}
    full_markdown = format_search_markdown(data, preview_content=False)
    saved_path = None
    if GTS_SAVE_FILE:
        saved_path, err = _save_result(full_markdown, data, output_dir)
        if err:
            return err

    if as_json:
        body = {
            "state": "success",
            "query": data.get("query"),
            "total": data.get("total"),
            "hints": data.get("hints") or [],
            "list": data.get("list") or [],
        }
        if saved_path:
            body["savedPath"] = os.path.abspath(saved_path)
        return dump_json(body)

    if saved_path:
        preview = format_search_markdown(data, preview_content=True)
        return (
            preview
            + f"\n\n查询结果共计 {data.get('total')} 条\n\n"
            + "<!-- 所有查询结果已保存到 "
            + GTS_SAVE_EXTENSION
            + "：`"
            + os.path.abspath(saved_path)
            + "` -->"
        )
    return full_markdown


def web_search(
    query: str,
    size: Optional[int] = None,
    freshness: Optional[str] = None,
    min_tier: Optional[str] = None,
    site_list: Optional[List[str]] = None,
    include_content: bool = False,
    max_content_chars: Optional[int] = None,
    output_dir: Optional[str] = None,
):
    raw_sites = ",".join(str(s) for s in site_list) if isinstance(site_list, (list, tuple)) else site_list
    sites, site_err = parse_site_list(raw_sites)
    if site_err:
        return failure_result(_error_result(site_err))
    result = search_web(
        query,
        size=size,
        freshness=freshness,
        min_tier=min_tier,
        site_list=sites,
        include_content=include_content,
        max_content_chars=max_content_chars,
    )
    if result.get("state") != "success":
        return failure_result(result)
    items = (result.get("data") or {}).get("list") or []
    return success_result(
        render_result(result, output_dir=output_dir),
        {"data": [{"type": "data", "data": items}]},
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gangtise OpenAPI 联网搜索。服务端不做检索词改写；限定站点请用 --site-list。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-q", "--query", required=True, help="检索词，去空格后 1–200 字")
    parser.add_argument(
        "-s",
        "--size",
        type=int,
        default=None,
        help="返回条数上限，1–20；--include-content 时 1–5。不传则由服务端默认 10",
    )
    parser.add_argument(
        "--freshness",
        choices=FRESHNESS_ALLOWED,
        default=None,
        help="时效窗口：day 近 1 日 / week 近 7 日 / month 近 30 日 / none 不限",
    )
    parser.add_argument(
        "--min-tier",
        choices=MIN_TIER_ALLOWED,
        default=None,
        help="最低信源等级。T3 或不传表示不过滤；T0 只要官方，T1 含权威媒体",
    )
    parser.add_argument(
        "--site-list",
        default=None,
        help="定向站点，逗号分隔的注册域或子域，最多 10 个。不要带协议和路径",
    )
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="返回网页正文。开启后 size 上限为 5",
    )
    parser.add_argument(
        "--max-content-chars",
        type=int,
        default=None,
        help="单条正文最大字符数，1000–20000，仅 --include-content 时生效",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="HTTP 超时（秒）",
    )
    parser.add_argument(
        "-od",
        "--output-dir",
        default=None,
        help="结果保存目录；仅当 GTS_SAVE_FILE=true 时生效",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args()

    sites, site_err = parse_site_list(args.site_list)
    if site_err:
        print("调用 Gangtise Open API 失败，错误信息：" + site_err)
        return

    result = search_web(
        args.query,
        size=args.size,
        freshness=args.freshness,
        min_tier=args.min_tier,
        site_list=sites,
        include_content=args.include_content,
        max_content_chars=args.max_content_chars,
        timeout=args.timeout,
    )
    print(render_result(result, as_json=args.json, output_dir=args.output_dir))


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
