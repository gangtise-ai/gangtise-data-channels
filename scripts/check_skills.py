#!/usr/bin/env python3
"""校验 openapi skill 可独立运行且共享代码一致。

检查项：
1. 每个 skill 的 scripts/ 下都有 gts_auth.py / gts_runtime.py / _launch.py，且各 skill 间逐字节相同。
2. skill 脚本不导入 gangtise_core，scripts/ 下没有 _generated/。
3. 从 .gts_auth / .gts_runtime 导入的名字都在其 __all__ 里。
4. gts_auth.__all__ 在 gangtise_core.auth 中存在；gts_runtime.__all__ 与 gangtise_core.skill_runtime.__all__ 相同
   （CLI / MCP 同步时按名字改写导入，名字对不上会在那边才报错）。
5. gts_runtime 里的 ERROR_HINTS / PARAM_CODES / ENDPOINT_POLICIES / ROW_BILLING_PRICES 与 core 一致。
6. skill 脚本里没有未定义的名字（用到却没导入、没定义）。

Usage:
  python3 scripts/check_skills.py
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "skills" / "openapi"
CORE_SRC = ROOT / "core" / "src"
SHARED_FILES = ("gts_auth.py", "gts_runtime.py", "_launch.py")
SKIP_DIRS = {"_generated", "__pycache__", ".venv"}
MODULE_DUNDERS = {"__file__", "__name__", "__doc__", "__package__", "__spec__", "__path__", "__builtins__", "__loader__"}


def iter_skills() -> List[Path]:
    if not OPENAPI.is_dir():
        return []
    return sorted(p for p in OPENAPI.iterdir() if (p / "scripts").is_dir())


def iter_skill_sources(skill: Path) -> Iterable[Path]:
    for path in sorted((skill / "scripts").rglob("*.py")):
        if not any(part in SKIP_DIRS for part in path.relative_to(skill / "scripts").parts[:-1]):
            yield path


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def module_all(path: Path) -> List[str]:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return list(ast.literal_eval(node.value))
    return []


def module_constant(path: Path, name: str):
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            target = node.target
        if isinstance(target, ast.Name) and target.id == name and node.value is not None:
            value = node.value
            if isinstance(value, ast.Call) and getattr(value.func, "id", "") == "frozenset":
                return frozenset(ast.literal_eval(value.args[0]))
            return ast.literal_eval(value)
    raise KeyError(f"{name} not found in {path}")


def check_shared(skills: List[Path]) -> List[str]:
    errors: List[str] = []
    for name in SHARED_FILES:
        digests: Dict[str, List[Path]] = {}
        for skill in skills:
            path = skill / "scripts" / name
            if not path.is_file():
                errors.append(f"missing {rel(path)}")
                continue
            digests.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), []).append(path)
        if len(digests) > 1:
            groups = sorted(digests.values(), key=len, reverse=True)
            majority = ", ".join(p.parent.parent.name for p in groups[0])
            for group in groups[1:]:
                for path in group:
                    errors.append(f"{rel(path)} differs from the copy in: {majority}")
    return errors


def check_imports(skills: List[Path], exports: Dict[str, Set[str]]) -> List[str]:
    errors: List[str] = []
    for skill in skills:
        if (skill / "scripts" / "_generated").exists():
            errors.append(f"{rel(skill / 'scripts' / '_generated')} must not exist (skills are standalone)")
        for path in iter_skill_sources(skill):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] == "gangtise_core":
                            errors.append(f"{rel(path)}:{node.lineno} imports gangtise_core")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if node.level == 0 and module.split(".")[0] == "gangtise_core":
                        errors.append(f"{rel(path)}:{node.lineno} imports gangtise_core")
                    if node.level == 1 and module in exports:
                        for alias in node.names:
                            if alias.name not in exports[module]:
                                errors.append(f"{rel(path)}:{node.lineno} imports {alias.name} from .{module}, not in its __all__")
    return errors


def check_core_parity(canonical: Path) -> List[str]:
    sys.path.insert(0, str(CORE_SRC))
    try:
        from gangtise_core import auth, billing, skill_runtime
        from gangtise_core.endpoints import load_endpoints
        from gangtise_core.errors import PARAM_CODES
        from gangtise_core.hints import ERROR_HINTS
    finally:
        sys.path.remove(str(CORE_SRC))
    errors: List[str] = []
    auth_all = module_all(canonical / "gts_auth.py")
    runtime_path = canonical / "gts_runtime.py"
    runtime_all = module_all(runtime_path)
    for name in auth_all:
        if not hasattr(auth, name):
            errors.append(f"gts_auth exports {name}, missing in gangtise_core.auth")
    if sorted(runtime_all) != sorted(skill_runtime.__all__):
        errors.append(
            "gts_runtime.__all__ != gangtise_core.skill_runtime.__all__: "
            f"only in skill {sorted(set(runtime_all) - set(skill_runtime.__all__))}, "
            f"only in core {sorted(set(skill_runtime.__all__) - set(runtime_all))}"
        )
    for name in skill_runtime.__all__:
        if not hasattr(skill_runtime, name):
            errors.append(f"gangtise_core.skill_runtime.__all__ lists {name} but does not define it")
    if module_constant(runtime_path, "ERROR_HINTS") != ERROR_HINTS:
        errors.append("gts_runtime.ERROR_HINTS differs from gangtise_core.hints.ERROR_HINTS")
    if module_constant(runtime_path, "PARAM_CODES") != PARAM_CODES:
        errors.append("gts_runtime.PARAM_CODES differs from gangtise_core.errors.PARAM_CODES")
    for name in ("ROW_BILLING_PRICES", "COSTLY_FETCH_CREDITS"):
        if module_constant(runtime_path, name) != getattr(billing, name):
            errors.append(f"gts_runtime.{name} differs from gangtise_core.billing.{name}")
    expected: Dict[str, Dict[str, object]] = {}
    for spec in load_endpoints().values():
        policy: Dict[str, object] = {}
        if spec.retry != "retry":
            policy["retry"] = spec.retry
        if spec.item_failures:
            policy["item_failures"] = True
        if policy:
            expected[spec.path] = policy
    actual = module_constant(runtime_path, "ENDPOINT_POLICIES")
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])
        errors.append(
            "gts_runtime.ENDPOINT_POLICIES differs from core endpoints.yaml: "
            f"missing {missing}, extra {extra}, changed {changed}"
        )
    return errors


def _bound_names(tree: ast.AST) -> Set[str]:
    bound: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name != "*":
                    bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
        elif isinstance(node, ast.MatchAs) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.MatchStar) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            bound.add(node.rest)
    return bound


def check_undefined(skills: List[Path]) -> List[str]:
    """不分作用域的保守检查：名字在文件任何位置都没有绑定过才报，不会误报，但查不出作用域错用。"""
    errors: List[str] = []
    known = set(dir(builtins)) | MODULE_DUNDERS
    for skill in skills:
        for path in iter_skill_sources(skill):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in ast.walk(tree)):
                errors.append(f"{rel(path)} uses `import *`; undefined-name check needs explicit imports")
                continue
            bound = _bound_names(tree) | known
            seen: Set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in bound and node.id not in seen:
                    seen.add(node.id)
                    errors.append(f"{rel(path)}:{node.lineno} undefined name {node.id}")
    return errors


def run_checks() -> List[str]:
    skills = iter_skills()
    if not skills:
        return [f"no openapi skills under {rel(OPENAPI)}"]
    errors = check_shared(skills)
    canonical = skills[0] / "scripts"
    if all((canonical / name).is_file() for name in SHARED_FILES):
        exports = {
            "gts_auth": set(module_all(canonical / "gts_auth.py")),
            "gts_runtime": set(module_all(canonical / "gts_runtime.py")),
        }
        errors += check_imports(skills, exports)
        errors += check_core_parity(canonical)
    errors += check_undefined(skills)
    return errors


def main() -> int:
    errors = run_checks()
    if errors:
        print("skill checks failed:", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"skill checks passed ({len(iter_skills())} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
