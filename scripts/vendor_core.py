#!/usr/bin/env python3
"""Deprecated alias. Use scripts/generate.py."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

print("scripts/vendor_core.py is deprecated; running scripts/generate.py", file=sys.stderr)
runpy.run_path(str(Path(__file__).with_name("generate.py")), run_name="__main__")
