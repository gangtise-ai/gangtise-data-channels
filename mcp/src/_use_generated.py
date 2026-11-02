# GENERATED FILE. Do not edit.
# Regenerate: python3 scripts/generate.py
"""Insert sibling `_generated/` onto sys.path. MCP/CLI must not import repo core/src."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_GEN = _HERE / "_generated"
if not (_GEN / "gangtise_core").is_dir():
    sys.stderr.write(
        f"missing {_GEN / 'gangtise_core'}\n"
        "From repo root run: python3 scripts/generate.py\n"
    )
    raise SystemExit(1)
_s = str(_GEN)
if _s not in sys.path:
    sys.path.insert(0, _s)
