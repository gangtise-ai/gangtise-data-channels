"""Load skill `scripts/` as a unique package; relaunch `python3 scripts/foo.py` as a module."""
from __future__ import annotations

import importlib
import importlib.util
import runpy
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional


def ensure_core_on_path(start: Path) -> Path:
    """Insert the nearest `_generated` (containing gangtise_core) onto sys.path.

    Never falls back to the repo `core/src` tree. Skills, MCP, and CLI each
    carry their own generated copy.
    """
    here = start if start.is_dir() else start.parent
    for p in [here, *here.parents]:
        gen = p / "_generated"
        if (gen / "gangtise_core").is_dir():
            s = str(gen)
            if s not in sys.path:
                sys.path.insert(0, s)
            return gen
    raise FileNotFoundError(
        "missing _generated/gangtise_core. From repo root run: python3 scripts/generate.py"
    )


def skill_package_name(scripts_dir: Path) -> str:
    return scripts_dir.parent.name.replace("-", "_")


def register_scripts_package(scripts_dir: Path, pkg_name: Optional[str] = None) -> ModuleType:
    scripts_dir = scripts_dir.resolve()
    name = pkg_name or skill_package_name(scripts_dir)
    existing = sys.modules.get(name)
    if existing is not None and getattr(existing, "__path__", None) == [str(scripts_dir)]:
        return existing
    init_py = scripts_dir / "__init__.py"
    if not init_py.exists():
        init_py.write_text("", encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        name,
        init_py,
        submodule_search_locations=[str(scripts_dir)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load skill package {name} from {scripts_dir}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def relaunch(script_file: str) -> int:
    """Re-exec a skill script as `gangtise_data.quote` so relative imports work."""
    from .errors import GangtiseError

    path = Path(script_file).resolve()
    scripts_dir = path.parent
    ensure_core_on_path(scripts_dir)
    pkg = register_scripts_package(scripts_dir)
    modname = f"{pkg.__name__}.{path.stem}"
    try:
        runpy.run_module(modname, run_name="__main__", alter_sys=True)
    except GangtiseError as err:
        print(str(err), file=sys.stderr)
        return int(getattr(err, "exit_code", 1) or 1)
    return 0
