# GENERATED FILE. Do not edit. Source: core/src/gangtise_core/endpoints.py
# Regenerate: python3 scripts/generate.py
"""Endpoint registry and compensation log (data, not scattered constants)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .references_loader import _load_yaml_text

_DATA = Path(__file__).resolve().parent / "data"


@dataclass
class Destructive:
    warning: str


@dataclass
class EndpointSpec:
    id: str
    method: str = "POST"
    path: str = ""
    retry: str = "retry"
    timeout_s: int = 120
    expects: str = "any"
    kind: str = "json"
    item_failures: bool = False
    max_limit: Optional[int] = None
    destructive: Optional[Destructive] = None
    tool: str = ""
    mode: str = ""


@dataclass
class Compensation:
    id: str
    title: str
    applies: List[str] = field(default_factory=list)
    reason: str = ""
    server_ticket: str = ""
    sunset: str = ""


_ENDPOINTS: Optional[Dict[str, EndpointSpec]] = None
_COMPENSATIONS: Optional[List[Compensation]] = None


def _load_mapping(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    data = _load_yaml_text(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_endpoints(*, force: bool = False) -> Dict[str, EndpointSpec]:
    global _ENDPOINTS
    if _ENDPOINTS is not None and not force:
        return _ENDPOINTS
    raw = _load_mapping(_DATA / "endpoints.yaml")
    out: Dict[str, EndpointSpec] = {}
    for key, val in raw.items():
        if key.startswith("_") or not isinstance(val, dict):
            continue
        dest = val.get("destructive")
        destructive = None
        if isinstance(dest, dict) and dest.get("warning"):
            destructive = Destructive(warning=str(dest["warning"]))
        elif dest:
            destructive = Destructive(warning=str(dest))
        out[key] = EndpointSpec(
            id=key,
            method=str(val.get("method") or "POST").upper(),
            path=str(val.get("path") or ""),
            retry=str(val.get("retry") or "retry"),
            timeout_s=int(val.get("timeout_s") or 120),
            expects=str(val.get("expects") or "any"),
            kind=str(val.get("kind") or "json"),
            item_failures=bool(val.get("item_failures")),
            max_limit=int(val["max_limit"]) if val.get("max_limit") is not None else None,
            destructive=destructive,
            tool=str(val.get("tool") or ""),
            mode=str(val.get("mode") or ""),
        )
    _ENDPOINTS = out
    return out


def load_compensations(*, force: bool = False) -> List[Compensation]:
    global _COMPENSATIONS
    if _COMPENSATIONS is not None and not force:
        return _COMPENSATIONS
    raw = _load_mapping(_DATA / "compensations.yaml")
    items = raw.get("compensations") if isinstance(raw.get("compensations"), list) else []
    if not items and isinstance(raw, dict):
        # allow a top-level list stored under a dummy key, or numeric keys skipped
        pass
    # file may be a list at root — _load_yaml_text always returns dict; use "items"
    if not items and isinstance(raw.get("items"), list):
        items = raw["items"]
    out: List[Compensation] = []
    for val in items:
        if not isinstance(val, dict):
            continue
        applies = val.get("applies") or []
        if isinstance(applies, str):
            applies = [applies]
        out.append(
            Compensation(
                id=str(val.get("id") or ""),
                title=str(val.get("title") or ""),
                applies=[str(x) for x in applies],
                reason=str(val.get("reason") or ""),
                server_ticket=str(val.get("server_ticket") or ""),
                sunset=str(val.get("sunset") or ""),
            )
        )
    _COMPENSATIONS = out
    return out


def match_endpoint(url: str) -> Optional[EndpointSpec]:
    if not url:
        return None
    u = str(url).split("?", 1)[0].rstrip("/")
    best: Optional[EndpointSpec] = None
    best_len = -1
    for spec in load_endpoints().values():
        path = spec.path.rstrip("/")
        if path and (u.endswith(path) or path in u):
            if len(path) > best_len:
                best = spec
                best_len = len(path)
    return best


def retry_policy_for_url(url: str) -> str:
    spec = match_endpoint(url)
    if spec and spec.retry in {"no-replay", "no-999999"}:
        return spec.retry
    return "retry"


def destructive_for_tool(tool: str, mode: Optional[str] = None) -> Optional[Destructive]:
    """Exact endpoint id, a (tool, mode) pair, or a CLI tool that *only* maps to a destructive endpoint."""
    tool = (tool or "").strip()
    if not tool:
        return None
    specs = load_endpoints()
    if tool in specs and specs[tool].destructive:
        return specs[tool].destructive
    matched = [s for s in specs.values() if s.tool == tool]
    mode = (mode or "").strip()
    if mode:
        for spec in matched:
            if spec.mode == mode and spec.destructive:
                return spec.destructive
        return None
    if len(matched) == 1 and matched[0].destructive:
        return matched[0].destructive
    return None


def compensations_for(endpoint_id: str) -> List[Compensation]:
    return [c for c in load_compensations() if endpoint_id in c.applies or "*" in c.applies]
