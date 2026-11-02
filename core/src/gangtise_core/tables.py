"""Parse fieldList + list blocks; refuse silent misalignment."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .envelope import unwrap
from .errors import StructuralError
from .ziprow import zip_field_rows


def records_from_block(block: Any, *, trace_id: str = "") -> List[Dict[str, Any]]:
    if block is None:
        return []
    if isinstance(block, list):
        if not block:
            return []
        if isinstance(block[0], dict):
            return [row for row in block if isinstance(row, dict)]
        raise StructuralError("响应包含数组形式的行但没有 fieldList，无法确定各列的含义，已拒绝输出", trace_id=trace_id)
    if not isinstance(block, dict):
        return []
    fail = block.get("failList") or block.get("fail_list")
    fields = block.get("fieldList") or block.get("fields")
    rows = block.get("list")
    if rows is None:
        rows = block.get("rows")
    if fields and rows is not None:
        seq = []
        for row in rows:
            if isinstance(row, (list, tuple)):
                seq.append(row)
            elif isinstance(row, dict):
                seq.append([row.get(f) for f in fields])
        return zip_field_rows(list(fields), seq, trace_id=trace_id)
    return []


def records_from_envelope_body(body: Any, *, http: int = 200) -> List[Dict[str, Any]]:
    """Unwrap envelope then parse a fieldList table. Empty list = vacuum (not an error)."""
    data = unwrap(body, http=http)
    trace_id = ""
    if isinstance(body, dict):
        trace_id = str(body.get("traceId") or body.get("trace_id") or "")
    return records_from_block(data, trace_id=trace_id)


def fail_list_of(data: Any) -> Optional[list]:
    if isinstance(data, dict):
        fail = data.get("failList") or data.get("fail_list")
        if fail:
            return list(fail)
    return None
