# GENERATED FILE. Do not edit. Source: core/src/gangtise_core/format.py
# Regenerate: python3 scripts/generate.py
"""Render a Result for skill / MCP / CLI. Handlers must not print."""
from __future__ import annotations

import json
import sys
from typing import Any, Literal, Optional, TextIO

from .errors import GangtiseError
from .result import Result

CliFormat = Literal["markdown", "json", "jsonl", "csv", "table"]


def eprint(msg: str, *, file: Optional[TextIO] = None) -> None:
    print(msg, file=file if file is not None else sys.stderr)


def render_skill(result: Result) -> str:
    """Model-facing Markdown (plus saved-file hints already in result.text)."""
    if not result.ok:
        err = result.error
        if isinstance(err, GangtiseError):
            return f"调用失败: {err}"
        return result.text or "调用失败"
    return result.text


def render_mcp_text(result: Result) -> str:
    if not result.ok:
        err = result.error
        payload = {
            "code": getattr(err, "code", None) or "TOOL_ERROR",
            "message": getattr(err, "message", None) or result.text or str(err or "调用失败"),
        }
        if getattr(err, "http", 0):
            payload["http"] = err.http  # type: ignore[union-attr]
        if getattr(err, "hint", None):
            payload["hint"] = err.hint  # type: ignore[union-attr]
        if getattr(err, "trace_id", ""):
            payload["traceId"] = err.trace_id  # type: ignore[union-attr]
        return json.dumps(payload, ensure_ascii=False)
    return result.text


def _rows_from_data(data: Any) -> list:
    if isinstance(data, list):
        return [r for r in data if r is not None]
    if data is None:
        return []
    return [data]


def render_cli(result: Result, fmt: str = "markdown") -> str:
    fmt = (fmt or "markdown").lower()
    if not result.ok:
        return ""
    if fmt == "json":
        if result.data is not None:
            return json.dumps(result.data, ensure_ascii=False, indent=2, default=str)
        return json.dumps({"text": result.text}, ensure_ascii=False, indent=2)
    if fmt == "jsonl":
        rows = _rows_from_data(result.data)
        return "\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rows)
    if fmt in {"csv", "table"}:
        rows = _rows_from_data(result.data)
        if rows and isinstance(rows[0], dict):
            import csv
            import io

            buf = io.StringIO()
            fieldnames: list = []
            for row in rows:
                for k in row.keys():
                    if k not in fieldnames:
                        fieldnames.append(k)
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
            return buf.getvalue()
        return result.text
    return result.text


def emit_cli(
    result: Result,
    *,
    fmt: str = "markdown",
    output: Optional[str] = None,
    verbose: bool = False,
) -> int:
    for key, val in result.markers.items():
        eprint(f"[gangtise] warning: {key}={val}")
    if verbose:
        from .endpoints import load_compensations, load_endpoints

        ids = {
            spec.id
            for spec in load_endpoints().values()
            if result.tool and spec.tool == result.tool
        }
        for comp in load_compensations():
            if "*" in comp.applies or ids.intersection(comp.applies):
                eprint(f"[gangtise] compensated: {comp.id} {comp.title}")
        if result.usage:
            eprint(f"[gangtise] usage: {json.dumps(result.usage, ensure_ascii=False)}")
    if not result.ok:
        err = result.error
        if isinstance(err, GangtiseError):
            eprint(str(err))
        else:
            eprint(result.text or str(err or "调用失败"))
        return result.exit_code or 1
    text = render_cli(result, fmt)
    if output:
        from pathlib import Path

        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    elif text:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return result.exit_code or 0


def invoke_legacy(handler: Any, kwargs: dict, *, tool: str = "") -> Result:
    try:
        out = handler(**kwargs)
    except GangtiseError as e:
        return Result.from_error(e, tool=tool)
    except Exception as e:
        return Result.from_error(e, tool=tool)
    return Result.from_legacy(out, tool=tool)
