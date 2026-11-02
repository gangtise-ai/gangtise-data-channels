# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-data/scripts/search_concept.py
# Regenerate: python3 scripts/generate.py
if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

"""题材 ID 搜索（open-reference concepts/search）。"""
from typing import List, Optional, Tuple

import requests

from .utils import CONCEPT_SEARCH_URL

MATCH_SCORE_THRESHOLD = 0.6
SEARCH_TOP_DEFAULT = 10
SEARCH_TOP_MAX = 10


def _api_error_message(body: dict, fallback: str = "") -> str:
    if isinstance(body, dict):
        return str(body.get("msg") or body.get("message") or fallback)
    return fallback


def _match_score(item: dict) -> float:
    try:
        return float(item.get("matchScore") or 0)
    except (TypeError, ValueError):
        return 0.0


def search_concepts(
    headers: dict,
    keyword: str,
    top: int = SEARCH_TOP_DEFAULT,
) -> Tuple[List[dict], Optional[str]]:
    req_top = max(1, min(int(top), SEARCH_TOP_MAX))
    payload = {"keyword": keyword.strip(), "top": req_top}
    try:
        from gangtise_core.skill_runtime import GangtiseError
        from gangtise_core.skill_runtime import request_json

        data = request_json("POST", CONCEPT_SEARCH_URL, json=payload, timeout=120)
    except GangtiseError:
        raise
    except Exception as e:
        return [], f"题材检索请求失败: {e}"

    items = (data or {}).get("list") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return [], "题材检索返回 list 格式异常"
    return items, None


def _filter_strong_candidates(items: List[dict]) -> List[dict]:
    out = [item for item in items if _match_score(item) > MATCH_SCORE_THRESHOLD]
    out.sort(key=_match_score, reverse=True)
    return out


def _pick_auto_candidate(candidates: List[dict], keyword: str) -> Optional[dict]:
    if len(candidates) == 1:
        return candidates[0]
    kw = (keyword or "").strip()
    if kw:
        exact = [
            c for c in candidates
            if str(c.get("conceptName") or "").strip() == kw
        ]
        if len(exact) == 1:
            return exact[0]
    perfect = [c for c in candidates if _match_score(c) == 1.0]
    if len(perfect) == 1:
        return perfect[0]
    return None


def format_concept_candidates(candidates: List[dict], keyword: str) -> str:
    lines = [
        f"关键词「{keyword}」匹配到 {len(candidates)} 个题材，"
        "请确认后使用 --concepts 指定 conceptId：\n"
    ]
    for c in candidates:
        lines.append(
            f"- conceptId={c.get('conceptId')} | {c.get('conceptName')}"
        )
    return "\n".join(lines)


def resolve_concept_keyword(
    headers: dict,
    keyword: str,
    top: int = SEARCH_TOP_DEFAULT,
) -> Tuple[Optional[str], Optional[str], bool]:
    """
    解析题材关键词。
    返回 (concept_id, message, is_candidates)：
    - 已唯一确定：(id, None, False)
    - 多候选待确认：(None, 候选列表文本, True)
    - 失败：(None, 错误说明, False)
    """
    kw = (keyword or "").strip()
    if not kw:
        return None, "题材关键词为空", False

    items, err = search_concepts(headers, kw, top)
    if err:
        return None, err, False

    candidates = _filter_strong_candidates(items)
    if not candidates:
        return None, f"未找到与「{kw}」匹配的相关题材", False

    picked = _pick_auto_candidate(candidates, kw)
    if picked is None:
        return None, format_concept_candidates(candidates, kw), True

    concept_id = str(picked.get("conceptId") or "").strip()
    if not concept_id:
        return None, "题材检索结果缺少 conceptId", False
    return concept_id, None, False
