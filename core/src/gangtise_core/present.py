"""Turn legacy format_response dicts into Result / ApiError."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .envelope import OK_CODES
from .errors import ApiError, PartialResultError
from .result import Result, SavedFile

_EMPTY_HINTS = (
    "未找到",
    "无数据",
    "无证券",
    "无自选",
    "日期范围内未找到",
    "当前账号下无",
)
_PARAM_HINTS = (
    "仅支持",
    "不能为空",
    "无效:",
    "无效：",
    "请指定",
    "不要使用",
    "须为",
    "必须为",
    "已拒绝",
    "非法",
    "缺少必填参数",
    "超出限制",
    "参数类型错误",
    "必须且只能",
    "只能指定",
)


def failure_result(response: Dict[str, Any]) -> Result:
    """Map a legacy `{state: error}` payload.

    Vacuum (no rows) → success + empty data, CLI exit 0.
    Server code / auth / params → raise ApiError (exit 1 or 2).
    """
    msg = str(response.get("message") or response.get("msg") or "调用失败")
    code = str(response.get("code") or "")
    http = int(response.get("http") or 0)
    trace_id = str(response.get("traceId") or response.get("trace_id") or "")
    if code and code not in OK_CODES:
        raise ApiError(msg, code=code, http=http, trace_id=trace_id, body=response)
    if any(h in msg for h in _PARAM_HINTS):
        raise ApiError(msg, code="100003", http=http or 400, trace_id=trace_id, body=response)
    if "未配置" in msg and "授权" in msg:
        raise ApiError(msg, code="999011", http=http, trace_id=trace_id, body=response)
    if any(h in msg for h in _EMPTY_HINTS):
        return Result.success(text=msg, data=[])
    raise ApiError(msg, code=code, http=http, trace_id=trace_id, body=response)


def success_result(
    markdown: str,
    response: Dict[str, Any],
    *,
    files: Optional[List[SavedFile]] = None,
) -> Result:
    tables: List[Any] = []
    for item in response.get("data") or []:
        if isinstance(item, dict) and item.get("type") == "data":
            tables.append(item.get("data"))
    data: Any = None
    if len(tables) == 1:
        data = tables[0]
    elif tables:
        data = tables
    result = Result.success(
        text=(markdown or "").strip(),
        data=data,
        files=list(files or []),
        usage=dict(response.get("usage") or {}),
    )
    partial = response.get("partial")
    if partial:
        result.exit_code = PartialResultError.exit_code
        result.markers["partial"] = partial if isinstance(partial, str) else "true"
    return result
