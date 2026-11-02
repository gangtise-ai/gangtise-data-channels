"""Locate the generated runtime tree (`_generated/gangtise_core`).

Callers that are not yet able to `import gangtise_core` must insert
`<src>/_generated` onto `sys.path` themselves (see `_use_generated.py` / `_launch.py`).
This module is for code that already imported core.
"""
from __future__ import annotations

import sys
from pathlib import Path

GENERATED_DIRNAME = "_generated"


def find_generated(anchor: Path | None = None) -> Path:
    """Walk from *anchor* (default: this file) until `_generated/gangtise_core` exists."""
    start = Path(anchor) if anchor is not None else Path(__file__).resolve()
    here = start if start.is_dir() else start.parent
    for p in [here, *here.parents]:
        gen = p / GENERATED_DIRNAME
        if (gen / "gangtise_core").is_dir():
            return gen
    raise FileNotFoundError(
        "missing _generated/gangtise_core. From repo root run: python3 scripts/generate.py"
    )


def use_generated(anchor: Path | None = None) -> Path:
    gen = find_generated(anchor)
    s = str(gen)
    if s not in sys.path:
        sys.path.insert(0, s)
    return gen


def handlers_root(anchor: Path | None = None) -> Path:
    return use_generated(anchor) / "handlers"
