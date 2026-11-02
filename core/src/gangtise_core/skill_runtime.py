"""CLI / MCP 侧对 skill 里 `from .gts_runtime import ...` 的替换目标。

generate.py 同步 handler 时把 skill 的 gts_runtime 导入改写到这里，使 handler 抛出的错误、
返回的 Result 与 CLI / MCP 适配器用的是同一套类型。名字须与 skill 的 gts_runtime.__all__ 一致。
"""
from __future__ import annotations

from .billing import credit_guard_enabled, guard_row_billed_fetch
from .concurrency import ThreadPoolExecutor
from .envelope import unwrap
from .errors import ApiError, GangtiseError, PartialResultError, StructuralError, ValidationError
from .present import failure_result, success_result
from .result import Result, SavedFile
from .tables import records_from_block, records_from_envelope_body
from .timeutil import maybe_timestamp13, to_timestamp13
from .transport import request_json
from .ziprow import zip_field_row, zip_field_rows

__all__ = [
    "ApiError",
    "GangtiseError",
    "PartialResultError",
    "Result",
    "SavedFile",
    "StructuralError",
    "ThreadPoolExecutor",
    "ValidationError",
    "failure_result",
    "credit_guard_enabled",
    "guard_row_billed_fetch",
    "maybe_timestamp13",
    "records_from_block",
    "records_from_envelope_body",
    "request_json",
    "success_result",
    "to_timestamp13",
    "unwrap",
    "zip_field_row",
    "zip_field_rows",
]
