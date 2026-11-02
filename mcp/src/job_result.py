"""基建工具 get_job_result：按 job_id 轮询异步附件结果。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

from attach_jobs import read_job

TOOL_NAME = "get_job_result"

TOOL_DESCRIPTION = (
    "根据 job_id 查询异步附件处理结果。"
    "当其它工具返回 status: pending 与 job_id 时，调用本工具轮询；"
    "直至 status 为 success（正文/附件就绪）或 failed。"
)

TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_id": {
            "type": "string",
            "description": "异步附件任务 ID（由其它工具返回的 job_id）",
        },
    },
    "required": ["job_id"],
}


def get_job_result_tool() -> Tool:
    return Tool(
        name=TOOL_NAME,
        description=TOOL_DESCRIPTION,
        inputSchema=TOOL_INPUT_SCHEMA,
    )


def list_infra_tools() -> List[Tool]:
    return [get_job_result_tool()]


def handle_get_job_result(arguments: Optional[Dict[str, Any]] = None) -> List[Any]:
    args = dict(arguments or {})
    job_id = str(args.get("job_id") or "").strip()
    if not job_id:
        return [TextContent(type="text", text="缺少参数 job_id")]

    status, err, items = read_job(job_id)
    if status == "not_found":
        return [TextContent(type="text", text=err or f"未找到 job_id: {job_id}")]
    if status == "pending":
        return [
            TextContent(
                type="text",
                text=(
                    f"job_id: `{job_id}`\n"
                    "status: pending\n"
                    "附件仍在处理中，请稍后再调用 get_job_result（建议间隔 2-5 秒）。"
                ),
            )
        ]
    if status == "failed":
        return [
            TextContent(
                type="text",
                text=(
                    f"job_id: `{job_id}`\n"
                    "status: failed\n"
                    f"error: {err or '附件处理失败'}"
                ),
            )
        ]
    # success — 不再二次走 with_path_attachments，避免循环开 job
    return items or [TextContent(type="text", text="(empty)")]


def try_call_infra_tool(
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Optional[List[Any]]:
    """若为基建工具则处理并返回内容；否则返回 None。"""
    if name != TOOL_NAME:
        return None
    return handle_get_job_result(arguments)
