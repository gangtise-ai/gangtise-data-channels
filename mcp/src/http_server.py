"""Gangtise MCP HTTP/SSE 整合入口。

- --layout unified：单进程 tools/list = 全部 skill 工具（MCP_TOOL_EXPOSURE=leaf 时为叶子工具）
- --layout gateway：拉起各域 api 子进程 + 网关反代

仅 `--transport http|sse|both`（默认 both）。stdio 请用 mcp 包 gangtise-mcp。
"""
from __future__ import annotations

import argparse
import atexit
import os
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple


def _ensure_layer_paths() -> None:
    here = Path(__file__).resolve().parent
    s = str(here)
    if s not in sys.path:
        sys.path.insert(0, s)
    import _use_generated  # noqa: F401


_ensure_layer_paths()
os.environ.setdefault("GTS_CALLER", "mcp")

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from authorization import (
    is_auth_configured,
    reset_request_authorization,
    reset_request_credentials,
    reset_request_headers_extra,
    set_request_authorization,
    set_request_credentials,
    set_request_headers_extra,
)
from http_compat import HttpMiddleware
from http_gateway import main as gateway_main
from subpath_routing import SubpathMiddleware, parse_subpaths
from oauth_server import oauth_routes
from job_result import TOOL_NAME as GET_JOB_RESULT_TOOL, try_call_infra_tool
import skill_tools
from services import (
    backend_mcp_path,
    backends_csv,
    invoke_package_main,
    mcp_root,
    resolve_package,
    run_package_stdio,
    select_services,
    start_backend,
    wait_port,
)
from catalog import load_catalog
from tool_errors import tool_error

SERVER_NAME = "gangtise-mcp"
SERVER_VERSION = "0.1.0"

server = Server(SERVER_NAME)


def _auth_missing_message() -> str:
    return (
        "未配置鉴权。\n"
        "HTTP：Authorization: Bearer <token>，或 X-GTS-Credentials（AK/SK），"
        "或通过 OAuth 同意页（/oauth/authorize）授权后使用客户端持有的 Bearer。\n"
        "stdio：设置 GTS_ACCESS_KEY/GTS_SECRET_KEY 或 GTS_AUTHORIZATION"
    )


def _check_auth_env() -> str | None:
    if is_auth_configured():
        return None
    return _auth_missing_message()


@server.list_tools()
async def list_tools() -> List[Tool]:
    return skill_tools.list_tools()


@server.call_tool()
async def call_tool(
    name: str, arguments: Dict[str, Any]
) -> Any:
    auth_err = _check_auth_env()
    if auth_err:
        return tool_error(auth_err, code="UNAUTHORIZED")

    if name == GET_JOB_RESULT_TOOL:
        return try_call_infra_tool(name, arguments)

    attach = os.getenv("MCP_ATTACH_FILES", "").lower() not in ("0", "false", "no", "off")
    return await skill_tools.call_tool(name, arguments, attach=attach)




def _wrap_http_middleware(app: ASGIApp, *, mcp_paths: set[str]) -> ASGIApp:
    return HttpMiddleware(
        app,
        set_authorization=set_request_authorization,
        reset_authorization=reset_request_authorization,
        set_credentials=set_request_credentials,
        reset_credentials=reset_request_credentials,
        set_headers_extra=set_request_headers_extra,
        reset_headers_extra=reset_request_headers_extra,
        mcp_paths=mcp_paths,
    )


class _StreamableHTTPASGIApp:
    def __init__(self, session_manager: StreamableHTTPSessionManager) -> None:
        self.session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.session_manager.handle_request(scope, receive, send)


def _normalize_path(path: str, *, trailing_slash: bool = False) -> str:
    p = path if str(path).startswith("/") else f"/{path}"
    if trailing_slash and not p.endswith("/"):
        p = f"{p}/"
    if not trailing_slash and len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/")
    return p



def _wrap_sse_endpoint_send(send: Send) -> Send:
    """把 SSE endpoint 的绝对路径 /messages/ 改成相对路径 messages/。

    网关剥离前缀后，MCP 库会下发 ``/messages/?session_id=…``；客户端用 urljoin
    会打到站点根（404）。相对路径可保留 SSE URL 所在前缀（…/mcp/sse → …/mcp/messages/）。
    """
    import re as _re

    done = False

    async def _send(message: dict) -> None:
        nonlocal done
        if (
            not done
            and message.get("type") == "http.response.body"
            and message.get("body")
        ):
            body = message["body"]
            if b"event: endpoint" in body and b"/messages/" in body:
                new_body, n = _re.subn(
                    rb"(data:\s*)/(messages/\?session_id=[0-9a-fA-F]+)",
                    rb"\1\2",
                    body,
                    count=1,
                )
                if n:
                    message = {**message, "body": new_body}
                    done = True
        await send(message)

    return _send

def _build_network_app(
    *,
    enable_http: bool,
    enable_sse: bool,
    path: str,
    sse_path: str,
    message_path: str,
    json_response: bool,
    stateless: bool,
) -> ASGIApp:
    path = _normalize_path(path)
    sse_path = _normalize_path(sse_path)
    message_path = _normalize_path(message_path, trailing_slash=True)

    routes: list[Any] = []
    session_manager: StreamableHTTPSessionManager | None = None

    routes.extend(oauth_routes())

    if enable_http:
        session_manager = StreamableHTTPSessionManager(
            app=server,
            json_response=json_response,
            stateless=stateless,
        )
        routes.append(Route(path, endpoint=_StreamableHTTPASGIApp(session_manager)))

    if enable_sse:
        sse = SseServerTransport(message_path)

        async def handle_sse(request: Request) -> Response:
            send = _wrap_sse_endpoint_send(request._send)  # type: ignore[attr-defined]
            async with sse.connect_sse(request.scope, request.receive, send) as streams:
                await server.run(
                    streams[0],
                    streams[1],
                    server.create_initialization_options(),
                )
            return Response()

        routes.append(Route(sse_path, endpoint=handle_sse, methods=["GET"]))
        routes.append(Mount(message_path, app=sse.handle_post_message))

    @asynccontextmanager
    async def lifespan(_app: Starlette):
        if session_manager is not None:
            async with session_manager.run():
                yield
        else:
            yield

    starlette_app = Starlette(routes=routes, lifespan=lifespan)
    mcp_paths: set[str] = set()
    if enable_http:
        mcp_paths.add(path)
    if enable_sse:
        mcp_paths.add(sse_path)
        mcp_paths.add(message_path.rstrip("/"))
    app = _wrap_http_middleware(starlette_app, mcp_paths=mcp_paths)
    subpaths = parse_subpaths()
    if subpaths:
        app = SubpathMiddleware(app, mcp_base=path, subpaths=subpaths)
    return app


def _run_network(**kwargs) -> None:
    import uvicorn
    keys = ("enable_http", "enable_sse", "path", "sse_path", "message_path", "json_response", "stateless")
    app = _build_network_app(**{k: kwargs[k] for k in keys})
    uvicorn.run(app, host=kwargs["host"], port=kwargs["port"], log_level="info")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="gangtise-mcp-api")
    parser.add_argument("--transport", choices=("http", "sse", "both"), default=os.getenv("MCP_TRANSPORT", "http"))
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8000")))
    parser.add_argument("--path", default=(os.getenv("MCP_PATH") or "/").strip() or "/")
    parser.add_argument("--sse-path", default=os.getenv("MCP_SSE_PATH", "/sse"))
    parser.add_argument("--message-path", default=os.getenv("MCP_MESSAGE_PATH", "/messages/"))
    parser.add_argument("--stateless", action=argparse.BooleanOptionalAction,
                        default=os.getenv("MCP_STATELESS", "true").lower() in ("1", "true", "yes", "on"))
    parser.add_argument("--json-response", action=argparse.BooleanOptionalAction,
                        default=os.getenv("MCP_JSON_RESPONSE", "true").lower() in ("1", "true", "yes", "on"))
    parser.add_argument(
        "--layout",
        choices=("unified", "gateway"),
        default=None,
        help="unified=单进程全量工具；gateway=子进程+反代（Docker 常用）",
    )
    parser.add_argument(
        "--package",
        default=os.getenv("MCP_PACKAGE", "domains"),
        help="gateway 时选择后端：domains|all|agent|data|...",
    )
    return parser.parse_args(argv)


def _resolve_layout(args: argparse.Namespace) -> str:
    if args.layout:
        return args.layout
    env_layout = (os.getenv("MCP_LAYOUT") or "").strip()
    if env_layout in ("gateway", "hub"):
        print("[gangtise-mcp] 已取消多包组合，gateway/hub 均走 unified", file=sys.stderr)
        return "unified"
    if env_layout == "unified":
        return "unified"
    return "unified"


def _delegate_argv(args: argparse.Namespace, transport: str) -> List[str]:
    argv = [
        "--transport", transport,
        "--host", args.host,
        "--port", str(args.port),
        "--path", args.path,
        "--sse-path", args.sse_path,
        "--message-path", args.message_path,
    ]
    argv.append("--stateless" if args.stateless else "--no-stateless")
    argv.append("--json-response" if args.json_response else "--no-json-response")
    return argv


def _preload_or_warn() -> None:
    cat = load_catalog()
    if cat.errors:
        for pkg, err in cat.errors.items():
            print(f"[gangtise-mcp] 警告：未加载 {pkg}: {err}", file=sys.stderr)
    print(
        f"[gangtise-mcp] {skill_tools.mounted_summary(cat)}"
        f"（来自 {', '.join(cat.skills) or 'openapi'}）",
        file=sys.stderr,
    )


def _cleanup_children(children: List[subprocess.Popen]) -> None:
    for proc in children:
        if proc.poll() is None:
            try:
                proc.send_signal(signal.SIGTERM)
            except OSError:
                pass
    for proc in children:
        try:
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except OSError:
                pass


def _run_gateway(args: argparse.Namespace, transport: str) -> None:
    os.environ.setdefault("GTS_MCP_ROOT", str(mcp_root()))
    os.environ.setdefault("GTS_SAVE_FILE", "False")

    try:
        services = select_services(args.package)
    except KeyError:
        print(
            f"未知 --package={args.package}。"
            "可选: domains | all | agent | data | file | kb | private | hub | mcp | gangtise_*",
            file=sys.stderr,
        )
        raise SystemExit(1)

    children: List[subprocess.Popen] = []
    atexit.register(lambda: _cleanup_children(children))

    for spec in services:
        proc = start_backend(spec, transport=transport)
        children.append(proc)
        print(
            f"[gangtise-mcp] started {spec.slug} -> 127.0.0.1:{spec.port} "
            f"({backend_mcp_path(spec.slug)})",
            file=sys.stderr,
        )

    for spec in services:
        try:
            wait_port(spec.port, timeout_s=40.0)
        except TimeoutError as e:
            _cleanup_children(children)
            print(str(e), file=sys.stderr)
            raise SystemExit(1) from e

    gateway_main(
        [
            "--host", args.host,
            "--port", str(args.port),
            "--backends", backends_csv(services),
        ]
    )


def _apply_network_gts_save_file_default() -> None:
    os.environ.setdefault("GTS_SAVE_FILE", "False")
    value = os.environ["GTS_SAVE_FILE"]
    for mod_name in (
        "gangtise_agent.utils",
        "gangtise_data.utils",
        "gangtise_file.utils",
        "gangtise_kb.utils",
        "gangtise_private.utils",
        "gangtise_fund.utils",
        "gangtise_bond.utils",
        "gangtise_web.utils",
    ):
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "GTS_SAVE_FILE"):
            setattr(mod, "GTS_SAVE_FILE", value)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    transport: Literal["http", "sse", "both"] = args.transport  # type: ignore[assignment]
    layout = _resolve_layout(args)

    # 调试：单域委托
    pkg = (args.package or "").strip()
    if pkg and pkg not in ("domains", "five", "core", "all", "*", "mcp", "gangtise_mcp") and layout == "unified":
        try:
            spec = resolve_package(pkg)
            invoke_package_main(spec.package_dir, _delegate_argv(args, transport))
            return
        except KeyError:
            pass

    if layout == "gateway":
        _run_gateway(args, transport)
        return

    _apply_network_gts_save_file_default()
    _preload_or_warn()
    subpaths = parse_subpaths()
    if subpaths:
        print(
            f"[gangtise-mcp] SUBPATHS={','.join(subpaths)} (MCP_PATH={args.path})",
            file=sys.stderr,
        )
    _run_network(
        host=args.host,
        port=args.port,
        enable_http=transport in ("http", "both"),
        enable_sse=transport in ("sse", "both"),
        path=args.path,
        sse_path=args.sse_path,
        message_path=args.message_path,
        json_response=args.json_response,
        stateless=args.stateless,
    )


if __name__ == "__main__":
    main()
