"""MCP 来源子路径：SUBPATHS 与 MCP_PATH 组合多入口，统一落到同一 MCP 服务。

示例：MCP_PATH=/open-mcp，SUBPATHS=doubao,ali,comate
  POST /open-mcp/          → 内部 /open-mcp（source 为空）
  POST /open-mcp/doubao/   → 内部 /open-mcp（source=doubao）

SUBPATHS_MODE 为各子路径指定工具暴露模式，例如 ``A:leaf;B:progressive``。
未写明的子路径默认 leaf。主路径（无 source）仍按 MCP_TOOL_EXPOSURE。

MCP_PROGRESSIVE_SUBPATH（如 progressive）为兼容简写：并入子路径且该来源为 progressive。
"""
from __future__ import annotations

import json
import os
import sys
from contextvars import ContextVar, Token
from typing import Callable, Dict, Iterable, Optional, Set, Tuple

_request_mcp_source: ContextVar[str] = ContextVar("mcp_source", default="")

_SKILL_MODE_ALIASES = frozenset({"skill", "skills", "progressive"})
_LEAF_MODE_ALIASES = frozenset({"leaf", "flat"})


def get_request_mcp_source() -> str:
    """当前 HTTP 请求的来源子路径（无则空串）。"""
    return (_request_mcp_source.get() or "").strip().strip("/")


def set_request_mcp_source(source: Optional[str]) -> Token:
    return _request_mcp_source.set((source or "").strip().strip("/"))


def reset_request_mcp_source(token: Token) -> None:
    _request_mcp_source.reset(token)


def progressive_subpath(raw: Optional[str] = None) -> Optional[str]:
    """渐进式披露专用子路径名（MCP_PROGRESSIVE_SUBPATH）；空=未启用该简写。"""
    text = raw if raw is not None else os.getenv("MCP_PROGRESSIVE_SUBPATH", "")
    name = (text or "").strip().strip("/")
    return name or None


def _normalize_exposure_token(raw: str) -> str:
    mode = (raw or "").strip().lower()
    if mode in _SKILL_MODE_ALIASES:
        return "skill"
    return "leaf"


def parse_subpaths_mode(raw: Optional[str] = None) -> Dict[str, str]:
    """解析 SUBPATHS_MODE → ``{subpath: leaf|skill}``。

    格式：``A:leaf;B:progressive``。另将 MCP_PROGRESSIVE_SUBPATH 标为 skill（若未覆盖）。
    """
    text = raw if raw is not None else os.getenv("SUBPATHS_MODE", "")
    out: Dict[str, str] = {}
    for segment in (text or "").replace("；", ";").split(";"):
        seg = segment.strip()
        if not seg or ":" not in seg:
            continue
        left, right = seg.split(":", 1)
        name = left.strip().strip("/")
        if not name:
            continue
        out[name] = _normalize_exposure_token(right)
    prog = progressive_subpath()
    if prog and prog not in out:
        out[prog] = "skill"
    return out


def exposure_for_source(source: Optional[str] = None) -> Optional[str]:
    """返回子路径暴露模式 ``leaf``/``skill``；主路径（空 source）返回 None。

    子路径未在 SUBPATHS_MODE 中声明时默认 leaf。
    """
    src = (source if source is not None else get_request_mcp_source()).strip().strip("/")
    if not src:
        return None
    return parse_subpaths_mode().get(src, "leaf")


def progressive_subpaths() -> Tuple[str, ...]:
    """所有 progressive/skill 模式的子路径名（稳定顺序）。"""
    return tuple(name for name, mode in parse_subpaths_mode().items() if mode == "skill")


def parse_subpaths(raw: Optional[str] = None) -> Tuple[str, ...]:
    """解析 SUBPATHS，并合并 SUBPATHS_MODE / MCP_PROGRESSIVE_SUBPATH 中的名称。"""
    text = raw if raw is not None else os.getenv("SUBPATHS", "")
    seen: set[str] = set()
    out: list[str] = []
    for part in (text or "").split(","):
        name = part.strip().strip("/")
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    for name in parse_subpaths_mode():
        if name not in seen:
            seen.add(name)
            out.append(name)
    return tuple(out)


def _normalize_base(path: str) -> str:
    p = (path or "/").strip() or "/"
    if not p.startswith("/"):
        p = f"/{p}"
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/")
    return p


def split_subpath(
    path: str,
    *,
    mcp_base: str,
    subpaths: Iterable[str],
) -> Tuple[str, Optional[str]]:
    """从请求路径剥离来源子路径，返回 (改写后的 path, source 或 None)。"""
    p = path or "/"
    base = _normalize_base(mcp_base)
    subs: Set[str] = {s.strip().strip("/") for s in subpaths if s.strip().strip("/")}
    if not subs:
        return p, None

    if base == "/":
        for sp in sorted(subs, key=len, reverse=True):
            prefix = f"/{sp}"
            if p == prefix:
                return "/", sp
            if p.startswith(prefix + "/"):
                rest = p[len(prefix) :]
                return rest if rest.startswith("/") else f"/{rest}", sp
        return p, None

    if p != base and not p.startswith(base + "/"):
        return p, None

    rest = p[len(base) :]
    if not rest or rest == "/":
        return base, None

    tail = rest.lstrip("/")
    head, _, suffix = tail.partition("/")
    if head not in subs:
        return p, None

    if suffix:
        stripped = f"{base}/{suffix}"
    else:
        stripped = base
    return stripped, head


def _parse_mcp_body(body: bytes) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """从 streamable HTTP JSON 体解析 mcp_method、tool 名与 skill 工具的 function。"""
    if not body:
        return None, None, None
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, None, None
    if not isinstance(payload, dict):
        return None, None, None

    mcp_method = payload.get("method")
    tool: Optional[str] = None
    function: Optional[str] = None
    if mcp_method == "tools/call":
        params = payload.get("params")
        if isinstance(params, dict):
            name = params.get("name")
            if name is not None:
                tool = str(name)
            arguments = params.get("arguments")
            if isinstance(arguments, dict) and arguments.get("function"):
                function = str(arguments["function"])
    return (str(mcp_method) if mcp_method is not None else None), tool, function


def log_mcp_access(
    *,
    source: Optional[str],
    path: str,
    method: str,
    request_id: str,
    mcp_method: Optional[str] = None,
    tool: Optional[str] = None,
    function: Optional[str] = None,
) -> None:
    try:
        from access_log import log_access

        log_access(
            source=source,
            path=path,
            method=method,
            request_id=request_id,
            mcp_method=mcp_method,
            tool=tool,
            function=function,
        )
        return
    except Exception as exc:
        # 日志模块异常时仍打 stderr，避免影响主链路
        record = {
            "event": "mcp_access",
            "source": source or "",
            "path": path,
            "method": method,
            "request_id": request_id,
        }
        if mcp_method:
            record["mcp_method"] = mcp_method
        if tool:
            record["tool"] = tool
        if function:
            record["function"] = function
        print(
            f"[mcp-access] fallback={exc} {json.dumps(record, ensure_ascii=False)}",
            file=sys.stderr,
            flush=True,
        )


class _BodyReplayReceive:
    """缓存已读 body，供下游 ASGI 再次读取。"""

    def __init__(self, receive, body: bytes) -> None:
        self._receive = receive
        self._body = body
        self._consumed = False

    async def __call__(self):
        if not self._consumed:
            self._consumed = True
            return {"type": "http.request", "body": self._body, "more_body": False}
        return await self._receive()


class SubpathMiddleware:
    """剥离 MCP_PATH 下的来源子路径，并输出结构化访问日志。"""

    def __init__(
        self,
        app,
        *,
        mcp_base: str,
        subpaths: Optional[Iterable[str]] = None,
        should_log: Optional[Callable[[str, str], bool]] = None,
    ) -> None:
        self.app = app
        self.mcp_base = _normalize_base(mcp_base)
        parsed = parse_subpaths(",".join(subpaths)) if subpaths else parse_subpaths()
        self.subpaths = parsed
        self._should_log = should_log or self._default_should_log

    @staticmethod
    def _default_should_log(method: str, path: str) -> bool:
        if method.upper() not in ("POST", "GET", "PUT", "PATCH", "DELETE"):
            return False
        skip_prefixes = ("/.well-known/", "/oauth/", "/health")
        if path in ("/health", "/authorize", "/token", "/register"):
            return False
        for prefix in skip_prefixes:
            if path.startswith(prefix):
                return False
        return True

    async def __call__(self, scope, receive, send) -> None:
        from http_compat import headers_from_scope, resolve_request_id

        if scope["type"] != "http" or not self.subpaths:
            await self.app(scope, receive, send)
            return

        original_path = scope.get("path") or "/"
        stripped, source = split_subpath(
            original_path,
            mcp_base=self.mcp_base,
            subpaths=self.subpaths,
        )

        headers = headers_from_scope(scope)
        request_id = resolve_request_id(headers)
        method = (scope.get("method") or "GET").upper()

        body = b""
        if method in ("POST", "PUT", "PATCH"):
            chunks: list[bytes] = []
            while True:
                message = await receive()
                chunk = message.get("body") or b""
                if chunk:
                    chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            body = b"".join(chunks)
            receive = _BodyReplayReceive(receive, body)

        if stripped != original_path:
            scope = {**scope, "path": stripped}
            raw = scope.get("raw_path")
            if isinstance(raw, (bytes, bytearray)):
                scope = {**scope, "raw_path": stripped.encode("latin-1")}

        scope = {
            **scope,
            "state": {
                **(scope.get("state") or {}),
                "mcp_source": source or "",
                "mcp_original_path": original_path,
            },
        }

        if self._should_log(method, original_path):
            mcp_method, tool, function = _parse_mcp_body(body)
            log_mcp_access(
                source=source,
                path=original_path,
                method=method,
                request_id=request_id,
                mcp_method=mcp_method,
                tool=tool,
                function=function,
            )

        await self.app(scope, receive, send)
