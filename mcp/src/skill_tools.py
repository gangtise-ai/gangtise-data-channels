"""MCP 工具暴露层：stdio / http 共用的 list_tools / call_tool 实现。

MCP_TOOL_EXPOSURE（默认 leaf）：
  leaf   每个叶子脚本一个工具（基金/债券带 fund_ / bond_ 前缀）。
  skill  渐进式披露。tools/list 仅含 get_job_result + 每个 skill 一个工具（gangtise-file 等）；
         调用 skill 工具时不传 function（或 function="help"）返回旗下全部 function 的说明与参数，
         传 function + arguments 则执行对应脚本。

无论哪种模式，call_tool 都同时接受 skill 名与叶子工具名。
"""
from __future__ import annotations

import asyncio
import inspect
import io
import json
import os
from contextlib import redirect_stdout
from contextvars import copy_context
from typing import Any, Dict, List, Optional, Set, Tuple

from mcp.types import TextContent, Tool

from catalog import INTERNAL_PARAMS, Catalog, ToolSpec, load_catalog
from gangtise_core.format import invoke_legacy, render_mcp_text
from gangtise_core.result import Result
from job_result import list_infra_tools
from result_attachments import with_path_attachments
from tool_errors import coerce_tool_kwargs, tool_error
from url_whitelist import get_tool_blacklist, get_white_list, tool_denied_reason

EXPOSURE_ENV = "MCP_TOOL_EXPOSURE"
HELP_FUNCTION = "help"

_SKILL_INPUT_DESC = {
    "function": "要调用的 function 名；不传或传 help 时返回本 skill 全部 function 的说明与参数",
    "arguments": "function 的参数对象（键为参数名），也接受 JSON 字符串；先不传 function 查看参数说明",
}


def exposure_mode() -> str:
    mode = (os.getenv(EXPOSURE_ENV) or "leaf").strip().lower()
    return "skill" if mode in ("skill", "skills", "progressive") else "leaf"


# ---------------------------------------------------------------- 权限


def _flat_denied(cat: Catalog, flat: str, wl: Optional[Set[str]]) -> Optional[str]:
    label = cat.source_by_tool.get(flat, "")
    if label and label in get_tool_blacklist():
        return f"skill 已列入部署黑名单: {label}"
    return tool_denied_reason(flat, wl)


def allowed_functions(cat: Catalog, label: str, wl: Optional[Set[str]] = None) -> List[str]:
    info = cat.skills.get(label)
    if info is None:
        return []
    return [fn for fn, flat in info.functions.items() if _flat_denied(cat, flat, wl) is None]


# ---------------------------------------------------------------- 说明文本


def _type_label(prop: Dict[str, Any]) -> str:
    t = str(prop.get("type") or "string")
    if t == "array":
        items = prop.get("items") if isinstance(prop.get("items"), dict) else {}
        return f"array<{items.get('type') or 'string'}>"
    return t


def _param_lines(spec: ToolSpec) -> List[str]:
    params = spec.parameters or (spec.input_schema.get("properties") or {})
    required = set(spec.input_schema.get("required") or [])
    lines: List[str] = []
    for pname, prop in params.items():
        if pname in INTERNAL_PARAMS or not isinstance(prop, dict):
            continue
        flag = "必填" if pname in required or prop.get("required") is True else "可选"
        desc = str(prop.get("description") or "").strip()
        extra: List[str] = []
        if "default" in prop and prop["default"] not in (None, ""):
            extra.append(f"默认 {json.dumps(prop['default'], ensure_ascii=False)}")
        enum = prop.get("enum")
        if not enum and isinstance(prop.get("items"), dict):
            enum = prop["items"].get("enum")
        if enum:
            extra.append("可选值 " + " / ".join(str(v) for v in enum))
        tail = f"（{'；'.join(extra)}）" if extra else ""
        lines.append(f"- `{pname}` ({_type_label(prop)}, {flag}): {desc}{tail}")
    return lines or ["- （无参数）"]


def describe_function(cat: Catalog, label: str, function: str) -> str:
    flat = cat.resolve_function(label, function) or function
    spec = cat.spec_map.get(flat)
    if spec is None:
        return f"### {function}\n（缺少参数说明）"
    head = f"### {function}"
    if spec.title:
        head += f" — {spec.title}"
    return "\n".join([head, spec.description.strip(), "参数:", *_param_lines(spec)])


def describe_skill(cat: Catalog, label: str, functions: List[str]) -> str:
    info = cat.skills[label]
    parts = [
        f"# {label}",
        info.description or info.summary,
        "",
        f'调用方式: {{"function": "<function 名>", "arguments": {{<参数名>: <值>}}}}；'
        "array 参数可传数组或逗号分隔字符串。",
        f"可用 function（{len(functions)} 个）: {', '.join(functions)}",
    ]
    for fn in functions:
        parts.extend(["", describe_function(cat, label, fn)])
    return "\n".join(parts)


# ---------------------------------------------------------------- tools/list


def _skill_tool(cat: Catalog, label: str, functions: List[str]) -> Tool:
    info = cat.skills[label]
    description = (
        f"{info.summary}\n"
        "先不传 function 调用，获取旗下全部 function 的说明与参数；"
        "再传 function + arguments 执行。"
    )
    schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "function": {
                "type": "string",
                "enum": [HELP_FUNCTION, *functions],
                "description": _SKILL_INPUT_DESC["function"],
            },
            "arguments": {
                "type": "object",
                "description": _SKILL_INPUT_DESC["arguments"],
            },
        },
    }
    return Tool(name=label, description=description, inputSchema=schema)


def list_tools() -> List[Tool]:
    cat = load_catalog()
    wl = get_white_list()
    tools: List[Tool] = list(list_infra_tools())
    if exposure_mode() == "leaf":
        for spec in cat.specs:
            if spec.name in cat.handlers and _flat_denied(cat, spec.name, wl) is None:
                tools.append(Tool(name=spec.name, description=spec.description, inputSchema=spec.input_schema))
        return tools
    for label in cat.skills:
        functions = allowed_functions(cat, label, wl)
        if functions:
            tools.append(_skill_tool(cat, label, functions))
    return tools


# ---------------------------------------------------------------- tools/call


def _filter_arguments(handler: Any, arguments: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    sig = inspect.signature(handler)
    allowed = {
        name
        for name, p in sig.parameters.items()
        if name not in INTERNAL_PARAMS and p.kind != p.VAR_KEYWORD
    }
    extra = set(arguments or {}) - allowed
    if extra:
        return {}, f"未知参数: {', '.join(sorted(extra))}。有效参数: {', '.join(sorted(allowed))}"
    return {k: v for k, v in (arguments or {}).items() if k in allowed}, None


def _missing_required(spec: Optional[ToolSpec], arguments: Dict[str, Any]) -> List[str]:
    if spec is None:
        return []
    required = spec.input_schema.get("required") or []
    return [p for p in required if arguments.get(p) in (None, "", [])]


async def invoke_flat(cat: Catalog, flat: str, arguments: Dict[str, Any], *, attach: bool) -> Any:
    handler = cat.handlers[flat]
    filtered, param_err = _filter_arguments(handler, arguments)
    if param_err:
        return tool_error(param_err, code="INVALID_PARAMS")
    filtered = coerce_tool_kwargs(handler, filtered)
    try:
        ctx = copy_context()

        def _invoke():
            buf = io.StringIO()
            with redirect_stdout(buf):
                wrapped = invoke_legacy(handler, filtered, tool=flat)
            return wrapped, buf.getvalue()

        result, stdout_text = await asyncio.to_thread(ctx.run, _invoke)
    except TypeError as e:
        return tool_error(f"参数错误: {e}", code="INVALID_PARAMS")
    except Exception as e:
        return tool_error(f"调用失败: {e}", code="INTERNAL_ERROR")

    if isinstance(result, Result) and not result.ok:
        code = getattr(result.error, "code", None) or "TOOL_ERROR"
        return tool_error(result.text or str(result.error or "调用失败"), code=str(code))
    if isinstance(result, Result):
        text = render_mcp_text(result)
    else:
        text = "" if result is None else str(result)
    if stdout_text:
        text = stdout_text + text
    return with_path_attachments(text, enabled=attach, source_tool=flat)


def _parse_skill_arguments(raw: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Optional[str]]:
    function = str(raw.get("function") or "").strip()
    args = raw.get("arguments")
    if isinstance(args, str):
        text = args.strip()
        if not text:
            args = {}
        else:
            try:
                args = json.loads(text)
            except json.JSONDecodeError as e:
                return function, {}, f"arguments 不是合法 JSON: {e}"
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return function, {}, "arguments 须为 object（键为参数名）"
    loose = {k: v for k, v in raw.items() if k not in ("function", "arguments")}
    return function, {**loose, **args}, None


def _with_usage(message: str, cat: Catalog, label: str, function: str) -> str:
    return f"{message}\n\n{describe_function(cat, label, function)}"


async def call_skill(cat: Catalog, label: str, raw: Dict[str, Any], *, attach: bool) -> Any:
    function, arguments, err = _parse_skill_arguments(raw or {})
    wl = get_white_list()
    functions = allowed_functions(cat, label, wl)
    if not functions:
        return tool_error(f"无权限调用 {label} 下的任何 function", code="FORBIDDEN")
    if err:
        return tool_error(err, code="INVALID_PARAMS")
    if not function or function == HELP_FUNCTION:
        return [TextContent(type="text", text=describe_skill(cat, label, functions))]

    flat = cat.resolve_function(label, function)
    if flat is None:
        return tool_error(
            f"{label} 下没有 function: {function}。可用: {', '.join(functions)}",
            code="UNKNOWN_TOOL",
        )
    denied = _flat_denied(cat, flat, wl)
    if denied:
        return tool_error(f"无权限调用 {label}.{function}: {denied}", code="FORBIDDEN")
    missing = _missing_required(cat.spec_map.get(flat), arguments)
    if missing:
        return tool_error(
            _with_usage(f"缺少必填参数: {', '.join(missing)}", cat, label, function),
            code="INVALID_PARAMS",
        )
    _, param_err = _filter_arguments(cat.handlers[flat], arguments)
    if param_err:
        return tool_error(_with_usage(param_err, cat, label, function), code="INVALID_PARAMS")
    return await invoke_flat(cat, flat, arguments, attach=attach)


async def call_tool(name: str, arguments: Optional[Dict[str, Any]], *, attach: bool) -> Any:
    """分发 skill 工具或叶子工具（get_job_result / 鉴权由调用方先处理）。"""
    cat = load_catalog()
    if name in cat.skills:
        return await call_skill(cat, name, arguments or {}, attach=attach)
    if name not in cat.handlers:
        return tool_error(f"未知工具: {name}", code="UNKNOWN_TOOL")
    denied = _flat_denied(cat, name, None)
    if denied:
        return tool_error(f"无权限调用工具 {name}: {denied}", code="FORBIDDEN")
    return await invoke_flat(cat, name, arguments or {}, attach=attach)


def mounted_summary(cat: Catalog) -> str:
    if exposure_mode() == "leaf":
        return f"已挂载 {len(cat.handlers)} 个叶子工具"
    return f"已挂载 {len(cat.skills)} 个 skill 工具（共 {len(cat.handlers)} 个 function，渐进式披露）"
