"""MCP 访问 / 调用 / 报错日志：按日写入 ``/opt/data/logs/{date}.log``。

每行一条 JSON，便于按 ``source``（SUBPATHS 渠道）统计与排查。
可通过 ``MCP_LOG_DIR`` / ``WORK_PATH`` 覆盖目录；``MCP_LOG_STDERR=false`` 关闭同步打 stderr。
"""
from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from contextvars import ContextVar, Token
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_CST = timezone(timedelta(hours=8))
_request_id: ContextVar[str] = ContextVar("mcp_request_id", default="")

_lock = threading.Lock()
_current_date: Optional[str] = None
_file_handle: Any = None

_ERROR_MSG_MAX = 800


def log_dir() -> Path:
    raw = (os.getenv("MCP_LOG_DIR") or "").strip()
    if raw:
        return Path(raw)
    work = (os.getenv("WORK_PATH") or "/opt/data").strip() or "/opt/data"
    return Path(work) / "logs"


def set_request_id(request_id: str) -> Token:
    return _request_id.set((request_id or "").strip())


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


def get_request_id() -> str:
    return (_request_id.get() or "").strip()


def _now() -> datetime:
    return datetime.now(_CST)


def _stderr_echo_enabled() -> bool:
    return os.getenv("MCP_LOG_STDERR", "true").lower() in ("1", "true", "yes", "on")


def _open_for_date(day: str):
    global _current_date, _file_handle
    if _file_handle is not None and _current_date == day:
        return _file_handle
    if _file_handle is not None:
        try:
            _file_handle.close()
        except Exception:
            pass
        _file_handle = None
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    _file_handle = open(directory / f"{day}.log", "a", encoding="utf-8")
    _current_date = day
    return _file_handle


def _request_context() -> Dict[str, Any]:
    ctx: Dict[str, Any] = {"source": ""}
    rid = get_request_id()
    if rid:
        ctx["request_id"] = rid
    try:
        from subpath_routing import get_request_mcp_source

        ctx["source"] = get_request_mcp_source() or ""
    except Exception:
        pass
    try:
        from authorization import get_request_client_ip, get_request_headers_extra

        extra = get_request_headers_extra() or {}
        for key in ("uid", "tenantid", "productcode"):
            value = extra.get(key)
            if value:
                ctx[key] = value
        ip = get_request_client_ip()
        if ip:
            ctx["client_ip"] = ip
    except Exception:
        pass
    return ctx


def _truncate(text: str, limit: int = _ERROR_MSG_MAX) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def write_event(event: str, **fields: Any) -> None:
    """追加一条 JSON 日志；写盘失败时仍尽量打到 stderr。"""
    record: Dict[str, Any] = {
        "ts": _now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        **_request_context(),
    }
    for key, value in fields.items():
        if value is None:
            continue
        # source 允许空串（主路径）；其它空串字段省略
        if value == "" and key != "source":
            continue
        record[key] = value
    line = json.dumps(record, ensure_ascii=False)
    day = _now().strftime("%Y-%m-%d")
    with _lock:
        try:
            fh = _open_for_date(day)
            fh.write(line + "\n")
            fh.flush()
        except Exception as exc:
            print(f"[mcp-log] write failed: {exc} | {line}", file=sys.stderr, flush=True)
            return
    if _stderr_echo_enabled():
        print(f"[mcp-log] {line}", file=sys.stderr, flush=True)


def log_access(
    *,
    source: Optional[str] = None,
    path: str,
    method: str,
    request_id: str = "",
    mcp_method: Optional[str] = None,
    tool: Optional[str] = None,
    function: Optional[str] = None,
) -> None:
    fields: Dict[str, Any] = {
        "path": path,
        "method": method,
        "mcp_method": mcp_method,
        "tool": tool,
        "function": function,
        "request_id": (request_id or get_request_id() or None),
    }
    # SubpathMiddleware 早于 HttpMiddleware，须显式带上 source
    if source is not None:
        fields["source"] = (source or "").strip().strip("/")
    write_event("mcp_access", **fields)


def log_tool_call(
    *,
    tool: str,
    status: str,
    function: Optional[str] = None,
    skill: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    fields: Dict[str, Any] = {
        "tool": tool,
        "status": status,
        "function": function,
        "skill": skill,
    }
    if duration_ms is not None:
        fields["duration_ms"] = round(float(duration_ms), 1)
    if error_code:
        fields["error_code"] = error_code
    if error_message:
        fields["error_message"] = _truncate(str(error_message))
    write_event("mcp_call", **fields)


def log_exception(
    *,
    where: str,
    exc: BaseException,
    tool: Optional[str] = None,
    function: Optional[str] = None,
) -> None:
    write_event(
        "mcp_error",
        where=where,
        tool=tool,
        function=function,
        error_type=type(exc).__name__,
        error_message=_truncate(str(exc)),
        traceback=_truncate(traceback.format_exc(), 2000),
    )


def _error_from_texts(texts: list[str]) -> Dict[str, str]:
    if texts:
        try:
            data = json.loads(texts[0])
            if isinstance(data, dict) and (data.get("code") or data.get("message")):
                return {
                    "code": str(data.get("code") or "TOOL_ERROR"),
                    "message": str(data.get("message") or texts[0]),
                }
        except (json.JSONDecodeError, TypeError):
            pass
        return {"code": "TOOL_ERROR", "message": texts[0]}
    return {"code": "TOOL_ERROR", "message": "unknown error"}


def parse_tool_error(result: Any) -> Optional[Dict[str, str]]:
    """仅当 CallToolResult.isError（或 SDK 无该类型时的 tool_error JSON）时判定为失败。"""
    texts: list[str] = []
    try:
        from mcp.types import CallToolResult
    except ImportError:  # pragma: no cover
        CallToolResult = None  # type: ignore[misc, assignment]

    if CallToolResult is not None:
        if not isinstance(result, CallToolResult):
            return None
        if not bool(getattr(result, "isError", False)):
            return None
        for item in getattr(result, "content", None) or []:
            text = getattr(item, "text", None)
            if text:
                texts.append(str(text))
        return _error_from_texts(texts)

    # 旧 SDK：tool_error 退回 TextContent 列表，正文为 {"code","message"}
    if isinstance(result, list):
        for item in result:
            text = getattr(item, "text", None)
            if text:
                texts.append(str(text))
        if not texts:
            return None
        try:
            data = json.loads(texts[0])
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(data, dict) and data.get("code") and data.get("message"):
            return {
                "code": str(data.get("code")),
                "message": str(data.get("message")),
            }
    return None
