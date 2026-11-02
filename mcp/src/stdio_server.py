"""Gangtise MCP stdio：默认每个脚本一个工具（MCP_TOOL_EXPOSURE，见 skill_tools）。HTTP 请用 http_server。"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


def _ensure_layer_paths() -> None:
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import _use_generated  # noqa: F401


_ensure_layer_paths()
os.environ.setdefault("GTS_CALLER", "mcp")

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

import skill_tools
from authorization import is_auth_configured
from catalog import load_catalog
from job_result import TOOL_NAME as GET_JOB_RESULT_TOOL, try_call_infra_tool
from tool_errors import tool_error

SERVER_NAME = "gangtise-mcp"
SERVER_VERSION = "0.1.0"
server = Server(SERVER_NAME)


def _auth_missing_message() -> str:
    return (
        "未配置 Authorization。\n"
        "stdio：设置 GTS_ACCESS_KEY / GTS_SECRET_KEY 或 GTS_AUTHORIZATION"
    )


@server.list_tools()
async def list_tools() -> List[Tool]:
    return skill_tools.list_tools()


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    if not is_auth_configured():
        return tool_error(_auth_missing_message(), code="UNAUTHORIZED")
    if name == GET_JOB_RESULT_TOOL:
        return try_call_infra_tool(name, arguments)
    attach = os.getenv("MCP_ATTACH_FILES", "").lower() in ("1", "true", "yes", "on")
    return await skill_tools.call_tool(name, arguments, attach=attach)


async def _run_stdio() -> None:
    cat = load_catalog()
    if cat.errors:
        for pkg, err in cat.errors.items():
            print(f"[gangtise-mcp] 警告：未加载 {pkg}: {err}", file=sys.stderr)
    print(f"[gangtise-mcp] {skill_tools.mounted_summary(cat)}", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main(argv: list[str] | None = None) -> None:
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
