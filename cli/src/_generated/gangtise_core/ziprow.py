# GENERATED FILE. Do not edit. Source: core/src/gangtise_core/ziprow.py
# Regenerate: python3 scripts/generate.py
"""Refuse silently-misaligned fieldList / row zips."""
from __future__ import annotations

from typing import Any, Iterable, List, Mapping, MutableMapping, Sequence

from .errors import StructuralError


def zip_field_row(
    fields: Sequence[str],
    row: Sequence[Any],
    *,
    trace_id: str = "",
) -> dict:
    if len(fields) != len(row):
        raise StructuralError(
            f"fieldList {len(fields)} 列，行 {len(row)} 个值，按位置对齐会错位，已拒绝输出",
            trace_id=trace_id,
        )
    dupes = [f for i, f in enumerate(fields) if f in fields[:i]]
    if dupes:
        raise StructuralError(
            f"响应 fieldList 有重复列名: {', '.join(sorted(set(dupes)))}",
            trace_id=trace_id,
        )
    return {fields[i]: row[i] for i in range(len(fields))}


def zip_field_rows(
    fields: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    trace_id: str = "",
) -> List[dict]:
    return [zip_field_row(fields, row, trace_id=trace_id) for row in rows]
