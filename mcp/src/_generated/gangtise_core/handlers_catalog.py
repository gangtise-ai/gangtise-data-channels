# GENERATED FILE. Do not edit. Source: core/src/gangtise_core/handlers_catalog.py
# Regenerate: python3 scripts/generate.py
"""Load leaf tools from `_generated/handlers/{pkg}` (copied from openapi skill scripts).

Two views of the same handlers:
  - flat:  ``handlers`` / ``spec_map`` keyed by a globally unique tool name (CLI, legacy leaf MCP).
           A skill whose ``tools_registry.CLI_PREFIX`` is set exposes ``<prefix>_<function>``.
  - skill: ``skills[label].functions`` keyed by the function name inside that skill (skill-level MCP).
"""
from __future__ import annotations

import dataclasses
import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .bootstrap import register_scripts_package
from .references_loader import ToolSpec, load_all_tool_specs
from .runtime_path import find_generated

ToolHandler = Callable[..., Any]

INTERNAL_PARAMS = frozenset(
    {
        "headers",
        "authorization",
        "append_file_hint",
        "meta",
        "meta_by_id",
        "indicator_meta",
        "kwargs",
    }
)

DOMAIN_ORDER = (
    "gangtise-agent",
    "gangtise-data",
    "gangtise-file",
    "gangtise-kb",
    "gangtise-private",
    "gangtise-screener",
    "gangtise-pdf",
    "gangtise-fund",
    "gangtise-bond",
    "gangtise-web",
)

SKILL_META_FILE = "skill.json"


@dataclass
class SkillInfo:
    label: str
    summary: str = ""
    description: str = ""
    # function name inside the skill -> flat tool name
    functions: Dict[str, str] = field(default_factory=dict)


@dataclass
class Catalog:
    handlers: Dict[str, ToolHandler] = field(default_factory=dict)
    specs: List[ToolSpec] = field(default_factory=list)
    spec_map: Dict[str, ToolSpec] = field(default_factory=dict)
    source_by_tool: Dict[str, str] = field(default_factory=dict)
    function_by_tool: Dict[str, str] = field(default_factory=dict)
    skills: Dict[str, SkillInfo] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)

    def resolve_function(self, skill: str, function: str) -> Optional[str]:
        info = self.skills.get(skill)
        if info is None:
            return None
        return info.functions.get(function)


_CATALOG: Optional[Catalog] = None


def _pkg_to_label(pkg_name: str) -> str:
    return pkg_name.replace("_", "-")


def _iter_handler_packages(handlers_root: Path) -> List[Tuple[str, Path]]:
    if not handlers_root.is_dir():
        return []
    found: Dict[str, Path] = {}
    for child in sorted(handlers_root.iterdir()):
        if child.is_dir() and (child / "tools_registry.py").is_file():
            found[_pkg_to_label(child.name)] = child
    ordered: List[Tuple[str, Path]] = []
    seen = set()
    for label in DOMAIN_ORDER:
        if label in found:
            ordered.append((label, found[label]))
            seen.add(label)
    for label, path in found.items():
        if label not in seen:
            ordered.append((label, path))
    return ordered


def _load_skill_meta(pkg_dir: Path, label: str) -> SkillInfo:
    info = SkillInfo(label=label)
    path = pkg_dir / SKILL_META_FILE
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        info.summary = str(data.get("summary") or "").strip()
        info.description = str(data.get("description") or "").strip()
    if not info.summary:
        info.summary = info.description or label
    return info


def load_catalog(*, force: bool = False, generated_root: Optional[Path] = None) -> Catalog:
    global _CATALOG
    if _CATALOG is not None and not force and generated_root is None:
        return _CATALOG

    cat = Catalog()
    try:
        gen = Path(generated_root) if generated_root is not None else find_generated()
    except FileNotFoundError as e:
        cat.errors["catalog"] = str(e)
        _CATALOG = cat
        return cat

    handlers_root = gen / "handlers"
    packages = _iter_handler_packages(handlers_root)
    if not packages:
        cat.errors["catalog"] = f"no generated handlers under {handlers_root}"
        _CATALOG = cat
        return cat

    for label, pkg_dir in packages:
        pkg_name = pkg_dir.name
        try:
            register_scripts_package(pkg_dir, pkg_name)
            registry = importlib.import_module(f"{pkg_name}.tools_registry")
        except Exception as e:
            cat.errors[label] = str(e)
            continue
        handlers: Dict[str, ToolHandler] = getattr(registry, "TOOL_HANDLERS", {})
        prefix = str(getattr(registry, "CLI_PREFIX", "") or "").strip()
        refs = pkg_dir / "references"
        specs = {s.name: s for s in load_all_tool_specs(refs)} if refs.is_dir() else {}
        info = _load_skill_meta(pkg_dir, label)
        for function, handler in handlers.items():
            name = f"{prefix}_{function}" if prefix else function
            if name in cat.handlers:
                cat.errors[name] = f"工具名冲突: {name}"
                continue
            cat.handlers[name] = handler
            cat.source_by_tool[name] = label
            cat.function_by_tool[name] = function
            info.functions[function] = name
            spec = specs.get(function)
            if spec is not None:
                if spec.name != name:
                    spec = dataclasses.replace(spec, name=name)
                cat.specs.append(spec)
                cat.spec_map[name] = spec
            else:
                cat.errors[name] = f"缺少 references/{function}.yaml"
        if info.functions:
            cat.skills[label] = info

    order = {d: i for i, d in enumerate(DOMAIN_ORDER)}

    def _sort_key(spec: ToolSpec) -> Tuple[int, str]:
        return (order.get(cat.source_by_tool.get(spec.name, ""), 99), spec.name)

    cat.specs.sort(key=_sort_key)
    _CATALOG = cat
    return cat
