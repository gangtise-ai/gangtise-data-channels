"""让 `python3 scripts/<name>.py` 以包内模块 `<skill_pkg>.<name>` 运行，使相对导入生效。

每个 skill 的 scripts/_launch.py 必须逐字节相同，由 scripts/check_skills.py 校验。只用标准库。
"""
from __future__ import annotations

import importlib
import importlib.util
import runpy
import sys
from pathlib import Path


def _register_package(scripts_dir: Path) -> str:
    name = scripts_dir.parent.name.replace("-", "_")
    existing = sys.modules.get(name)
    if existing is not None and list(getattr(existing, "__path__", []) or []) == [str(scripts_dir)]:
        return name
    init_py = scripts_dir / "__init__.py"
    if not init_py.exists():
        init_py.write_text("", encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, init_py, submodule_search_locations=[str(scripts_dir)])
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load skill package {name} from {scripts_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return name


def relaunch(script_file: str) -> int:
    path = Path(script_file).resolve()
    pkg = _register_package(path.parent)
    error_type = getattr(importlib.import_module(f"{pkg}.gts_runtime"), "GangtiseError")
    try:
        runpy.run_module(f"{pkg}.{path.stem}", run_name="__main__", alter_sys=True)
    except error_type as err:
        print(str(err), file=sys.stderr)
        return int(getattr(err, "exit_code", 1) or 1)
    return 0
