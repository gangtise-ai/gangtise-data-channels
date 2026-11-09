# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-private/scripts/stockpool.py
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

import os
import sys
from io import TextIOWrapper
from typing import Any, List, Optional, Tuple

import pandas as pd

from gangtise_core.skill_runtime import ApiError, ValidationError
from gangtise_core.skill_runtime import request_json

from .utils import (
    ADD_NOTE_URL,
    ADD_STOCK_URL,
    CREATE_POOL_URL,
    DELETE_NOTE_URL,
    DELETE_POOL_URL,
    DELETE_STOCK_URL,
    GET_NOTE_LIST_URL,
    GET_POOL_LIST_URL,
    GET_STOCK_LIST_URL,
    UPDATE_NOTE_URL,
    UPDATE_POOL_URL,
    check_version,
    format_response,
    get_authorization_token,
    is_code_arg,
)

script_dir = os.path.dirname(os.path.abspath(__file__))

DEFAULT_POOL_LIMIT = 100
IDS_FILE_HINT = (
    "可以删除行或保留需要的池，再通过 --pool-file 读取；"
    "文件中的 space_type 会用于后续明细查询，须与池 ID 同属一个区域"
)
METHOD = "stockpool"
MODES = [
    "search",
    "get",
    "create",
    "rename",
    "delete",
    "add_stock",
    "delete_stock",
    "search_note",
    "add_note",
    "update_note",
    "delete_note",
]
# 删除不可恢复：所有入口（脚本、CLI、MCP）都须显式确认，被拒后不要未经用户同意自行补确认重试。
DELETE_POOL_WARNING = (
    "已拒绝：删除股票池会同时移除池内全部证券的关注关系，且不可恢复（投资笔记不受影响）。"
    "先用 search 模式核对 ID 对应的池名并取得用户明确同意，再加 --yes（MCP 传 confirm=true）重试。"
)
DELETE_NOTE_WARNING = (
    "已拒绝：删除个股笔记不可恢复。"
    "先用 search_note 核对 stockNoteId 对应内容并取得用户明确同意，再加 --yes（MCP 传 confirm=true）重试。"
)
MAX_POOL_NAME_LEN = 10
MAX_STOCKS = 10000
MAX_NOTE_CONTENT_LEN = 10000
MAX_NOTE_SECURITIES = 50
MAX_NOTE_QUERY = 100
NOTE_PAGE_SIZE_DEFAULT = 20
NOTE_PAGE_SIZE_MAX = 50
SPACE_PERSONAL = 1
SPACE_TENANT = 2
# 查询接口的 spaceType：1 个人自选股，2 所属租户。不传按 1。管理接口仍只支持个人池。
SPACE_TYPE_MAP = {
    "1": SPACE_PERSONAL,
    "个人": SPACE_PERSONAL,
    "个人自选股": SPACE_PERSONAL,
    "自选股": SPACE_PERSONAL,
    "个人股票池": SPACE_PERSONAL,
    "2": SPACE_TENANT,
    "租户": SPACE_TENANT,
    "所属租户": SPACE_TENANT,
    "租户股票池": SPACE_TENANT,
}
MANAGE_PERSONAL_ONLY = (
    "创建、重命名、删除股票池以及添加、移除证券仅支持个人自选股（space_type=1）"
)


def _parse_str_list(raw: Any) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, (list, tuple, set)):
        raw = ",".join(str(x) for x in raw)
    if not str(raw).strip():
        return []
    return [x.strip() for x in str(raw).replace("，", ",").split(",") if x.strip()]


def _require_auth() -> None:
    if not get_authorization_token():
        raise ApiError("未配置 gangtise 授权，无法调用 open 接口", code="999011")


def _error(message: str, output_dir: Optional[str] = None):
    return format_response({"state": "error", "message": message, "data": [], "usage": {}}, METHOD, output_dir=output_dir)


def _success_message(message: str, output_dir: Optional[str] = None):
    return format_response({"state": "success", "message": message, "data": [], "usage": {}}, METHOD, output_dir=output_dir)


def _post(url: str, payload: dict) -> Any:
    return request_json("POST", url, json=payload, timeout=120)


def _space_label(space_type: int) -> str:
    return "所属租户" if int(space_type) == SPACE_TENANT else "个人自选股"


def _normalize_space_type(raw: Any) -> int:
    """缺省为个人自选股。接口只接受整数 1/2，中文别名在此转换。"""
    if raw is None:
        return SPACE_PERSONAL
    if isinstance(raw, bool):
        raise ValidationError("space_type 仅支持 1（个人自选股）或 2（所属租户）")
    if isinstance(raw, int):
        if raw in (SPACE_PERSONAL, SPACE_TENANT):
            return raw
        raise ValidationError(f"space_type 仅支持 1（个人自选股）或 2（所属租户），收到 {raw}")
    if isinstance(raw, float):
        if raw.is_integer():
            return _normalize_space_type(int(raw))
        raise ValidationError(f"space_type 仅支持 1（个人自选股）或 2（所属租户），收到 {raw}")
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return SPACE_PERSONAL
    if text.endswith(".0") and text[:-2].lstrip("-").isdigit():
        text = text[:-2]
    if text in SPACE_TYPE_MAP:
        return SPACE_TYPE_MAP[text]
    raise ValidationError(
        f"space_type 仅支持 1（个人自选股）或 2（所属租户），可传「个人」「租户」，收到 {raw}"
    )


def _fetch_pool_list(space_type: int = SPACE_PERSONAL) -> List[dict]:
    data = _post(GET_POOL_LIST_URL, {"spaceType": int(space_type)}) or []
    if not isinstance(data, list):
        raise ApiError("股票池列表返回 data 格式异常")
    return data


def _fetch_stock_list(pool_id_list: List[str], space_type: int = SPACE_PERSONAL) -> List[dict]:
    ids = [str(x).strip() for x in pool_id_list if str(x).strip()]
    if not ids:
        raise ValidationError("股票池 ID 列表不能为空")
    data = _post(GET_STOCK_LIST_URL, {"spaceType": int(space_type), "poolIdList": ids}) or []
    if not isinstance(data, list):
        raise ApiError("证券明细返回 data 格式异常")
    return data


def _pools_to_df(pools: List[dict], space_type: int = SPACE_PERSONAL) -> pd.DataFrame:
    records = []
    for item in pools:
        st = item.get("spaceType")
        records.append(
            {
                "pool_id": item.get("poolId"),
                "pool_name": item.get("poolName"),
                "space_type": space_type if st is None else st,
            }
        )
    return pd.DataFrame(records)


def _stocks_to_df(stocks: List[dict]) -> pd.DataFrame:
    records = []
    for item in stocks:
        records.append(
            {
                "security_code": item.get("securityCode"),
                "security_abbr": item.get("securityName"),
            }
        )
    df = pd.DataFrame(records)
    if not df.empty and "security_code" in df.columns:
        df = df.drop_duplicates(subset=["security_code"], keep="first")
    return df


def _filter_pools_by_keyword(pools: List[dict], keyword: str) -> List[dict]:
    kw = (keyword or "").strip()
    if not kw:
        return pools
    return [
        p
        for p in pools
        if kw in str(p.get("poolName") or "") or kw in str(p.get("poolId") or "")
    ]


def _apply_pool_limit(pools: List[dict], limit: Optional[int]) -> List[dict]:
    if limit is None or limit <= 0:
        return pools
    return pools[: int(limit)]


def _exact_match_pools(keyword: str, pools: List[dict]) -> List[dict]:
    kw = keyword.strip()
    return [
        p
        for p in pools
        if str(p.get("poolName") or "").strip() == kw
        or str(p.get("poolId") or "").strip() == kw
    ]


def _resolve_pools_from_arg(
    raw: str,
    limit: int,
    output_dir: Optional[str] = None,
    space_type: int = SPACE_PERSONAL,
) -> Tuple[Optional[List[str]], Optional[Any]]:
    """池 ID 原样返回；名称唯一完全匹配时解析为 ID，否则返回候选列表。名称只在同一 space_type 内匹配。"""
    if is_code_arg(raw):
        return _parse_str_list(raw), None

    _require_auth()
    pools = _fetch_pool_list(space_type)
    resolved: List[str] = []
    search_outputs: List[str] = []
    label = _space_label(space_type)
    for token in _parse_str_list(raw):
        filtered = _filter_pools_by_keyword(pools, token)
        exact = _exact_match_pools(token, filtered)
        if len(exact) == 1:
            pid = str(exact[0].get("poolId") or "").strip()
            if pid:
                resolved.append(pid)
            continue
        if not filtered:
            return None, _error(f"未找到与「{token}」相关的{label}股票池", output_dir)
        if len(exact) > 1:
            prefix = f"「{token}」在{label}股票池中存在 {len(exact)} 条完全匹配，请指定更精确的名称或 ID：\n\n"
        else:
            prefix = f"未找到与「{token}」完全匹配的{label}股票池，以下为候选结果：\n\n"
        search_outputs.append(
            prefix + str(stockpool_search(keyword=token, limit=limit, space_type=space_type, output_dir=output_dir))
        )

    if search_outputs:
        return None, "\n\n".join(search_outputs)
    return resolved, None


def _space_cell(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    try:
        if pd.isna(raw):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(raw, str) and not raw.strip():
        return None
    return _normalize_space_type(raw)


def _load_pools_from_file(path: str) -> Tuple[List[str], Optional[int]]:
    """读取池 ID；若文件含单一 space_type / spaceType 列，一并返回，供明细查询沿用同一区域。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"股票池文件不存在: {path}")
    df = pd.read_csv(path)
    col = next((c for c in ("pool_id", "poolId", "poolIdList") if c in df.columns), None)
    if col is None:
        raise ValueError("股票池文件须包含 pool_id 或 poolId 列")
    ids = [str(x).strip() for x in df[col].dropna().tolist() if str(x).strip()]
    space_col = next((c for c in ("space_type", "spaceType") if c in df.columns), None)
    if space_col is None:
        return ids, None
    found: List[int] = []
    for raw in df[space_col].tolist():
        value = _space_cell(raw)
        if value is not None and value not in found:
            found.append(value)
    if not found:
        return ids, None
    if len(found) > 1:
        raise ValidationError("股票池文件包含多个 space_type，一次只能查询一个区域，请按区域拆分后再查")
    return ids, found[0]


def _normalize_security_codes(raw: Any) -> List[str]:
    out: List[str] = []
    for x in _parse_str_list(raw):
        code = x.strip().upper()
        if code and code not in out:
            out.append(code)
    return out


def _load_security_codes_from_file(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"证券文件不存在: {path}")
    df = pd.read_csv(path)
    for col in ("security_code", "securityCode"):
        if col in df.columns:
            return [str(x).strip() for x in df[col].dropna().tolist() if str(x).strip()]
    raise ValueError("证券文件须包含 security_code 列")


def _check_pool_name(name: str) -> None:
    if not name:
        raise ValidationError("请指定 --pool-name 股票池名称")
    if len(name) > MAX_POOL_NAME_LEN:
        raise ValidationError(f"股票池名称「{name}」超过 {MAX_POOL_NAME_LEN} 个字符")


def _success_lines(action: str, data: Any) -> str:
    data = data if isinstance(data, dict) else {}
    success_list = data.get("successList") or []
    msg = f"{action}完成：成功 {len(success_list)} 个"
    if success_list:
        msg += "\n成功：" + "，".join(str(x) for x in success_list)
    return msg


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------


def stockpool_search(
    keyword: str = "",
    limit: int = DEFAULT_POOL_LIMIT,
    append_file_hint: bool = False,
    space_type: Any = None,
    output_dir: Optional[str] = None,
    **kwargs,
):
    _require_auth()
    st = _normalize_space_type(space_type)
    label = _space_label(st)
    pools = _fetch_pool_list(st)
    if not pools:
        return _error(f"当前没有可见的{label}股票池", output_dir)

    pools = _filter_pools_by_keyword(pools, keyword)
    pools = _apply_pool_limit(pools, limit)
    if not pools:
        kw_hint = f"与「{keyword.strip()}」匹配的" if (keyword or "").strip() else ""
        return _error(f"未找到{kw_hint}{label}股票池", output_dir)

    df = _pools_to_df(pools, st)
    parts = [
        {
            "data": df.to_dict(orient="records"),
            "module": "stockpool_pools",
            "type": "data",
        }
    ]
    msg = f"已获取 {len(df)} 个{label}股票池"
    if (keyword or "").strip():
        msg += f"（关键词：{keyword.strip()}）"
    if append_file_hint:
        msg += f"；{IDS_FILE_HINT}"
    return format_response(
        {"state": "success", "message": msg, "data": parts, "usage": {}},
        METHOD, output_dir=output_dir)


def stockpool_get(
    pool_ids: List[str],
    all_pools: bool = False,
    space_type: Any = None,
    output_dir: Optional[str] = None,
    **kwargs,
):
    _require_auth()
    st = _normalize_space_type(space_type)
    label = _space_label(st)
    if all_pools:
        pool_id_list = ["all"]
    else:
        pool_id_list = [str(x).strip() for x in pool_ids if str(x).strip()]
        if not pool_id_list:
            raise ValidationError("股票池 ID 列表不能为空（或使用 --all 获取该区域全部池的去重证券）")

    stocks = _fetch_stock_list(pool_id_list, st)
    if not stocks:
        scope = "全部" if all_pools else "所选"
        return _error(f"{scope}{label}股票池中无证券", output_dir)

    df = _stocks_to_df(stocks)
    parts = [
        {
            "data": df.to_dict(orient="records"),
            "module": "stockpool_stocks",
            "type": "data",
        }
    ]
    if all_pools:
        msg = f"已获取全部{label}股票池去重后的 {len(df)} 只证券"
    else:
        msg = f"已获取 {len(pool_id_list)} 个{label}股票池共 {len(df)} 只证券（已按代码去重）"
    if len(df) >= MAX_STOCKS:
        msg += f"；单次最多返回 {MAX_STOCKS} 只，达到上限时无法确认是否已取全，可改为逐池查询"
    return format_response(
        {"state": "success", "message": msg, "data": parts, "usage": {}},
        METHOD, output_dir=output_dir)


# ---------------------------------------------------------------------------
# 管理操作
# ---------------------------------------------------------------------------


def stockpool_create(pool_name: str, output_dir: Optional[str] = None):
    _require_auth()
    name = (pool_name or "").strip()
    _check_pool_name(name)
    data = _post(CREATE_POOL_URL, {"poolName": name})
    data = data if isinstance(data, dict) else {}
    return _success_message(
        f"已创建股票池：poolId={data.get('poolId')}，poolName={data.get('poolName')}；"
        f"可用 mode=add_stock、pool_ids={data.get('poolId')} 添加证券",
        output_dir,
    )


def stockpool_rename(pool_id: str, pool_name: str, output_dir: Optional[str] = None):
    _require_auth()
    if not pool_id:
        raise ValidationError("rename 模式请指定一个股票池（--pool-ids）")
    name = (pool_name or "").strip()
    _check_pool_name(name)
    data = _post(UPDATE_POOL_URL, {"poolId": pool_id, "poolName": name})
    data = data if isinstance(data, dict) else {}
    return _success_message(
        f"股票池重命名成功：poolId={data.get('poolId')}，poolName={data.get('poolName')}", output_dir
    )


def stockpool_delete(pool_ids: List[str], output_dir: Optional[str] = None):
    _require_auth()
    ids = [str(x).strip() for x in pool_ids if str(x).strip()]
    if not ids:
        raise ValidationError("delete 模式请指定股票池（--pool-ids 或 --pool-file）")
    data = _post(DELETE_POOL_URL, {"poolIdList": ids})
    return _success_message(_success_lines("删除股票池", data), output_dir)


def _stock_operation(url: str, action: str, pool_id: str, security_codes: List[str], output_dir: Optional[str] = None):
    _require_auth()
    if not pool_id:
        raise ValidationError(f"{action}请指定一个股票池（--pool-ids）")
    if not security_codes:
        raise ValidationError(f"{action}请指定证券代码（--securities），须带市场后缀，如 600519.SH")
    data = _post(url, {"poolId": pool_id, "securityCodeList": security_codes})
    return _success_message(_success_lines(f"{action}（poolId={pool_id}）", data), output_dir)


def stockpool_add_stock(pool_id: str, security_codes: List[str], output_dir: Optional[str] = None):
    return _stock_operation(ADD_STOCK_URL, "添加证券", pool_id, security_codes, output_dir)


def stockpool_delete_stock(pool_id: str, security_codes: List[str], output_dir: Optional[str] = None):
    return _stock_operation(DELETE_STOCK_URL, "移除证券", pool_id, security_codes, output_dir)


# ---------------------------------------------------------------------------
# 个股笔记
# ---------------------------------------------------------------------------


def _validate_note_id(raw: Any, *, label: str = "stockNoteId") -> str:
    text = str(raw or "").strip()
    if not text or not text.isdigit() or text.startswith("0"):
        raise ValidationError(f"{label} 须为正整数字符串（不含前导零），收到 {raw}")
    return text


def _validate_note_ids(raw: Any) -> List[str]:
    items = _parse_str_list(raw)
    if not items:
        raise ValidationError("请指定笔记 ID（--note-ids）")
    if len(items) > MAX_NOTE_QUERY:
        raise ValidationError(f"笔记 ID 一次最多 {MAX_NOTE_QUERY} 个")
    out: List[str] = []
    for x in items:
        nid = _validate_note_id(x)
        if nid not in out:
            out.append(nid)
    return out


def _validate_note_content(content: Optional[str]) -> str:
    text = "" if content is None else str(content)
    if not text.strip():
        raise ValidationError("笔记正文不能为空或纯空白")
    if len(text) > MAX_NOTE_CONTENT_LEN:
        raise ValidationError(f"笔记正文最长 {MAX_NOTE_CONTENT_LEN} 个字符（Unicode 码点）")
    return text


def _notes_to_df(notes: List[dict]) -> pd.DataFrame:
    records = []
    for item in notes:
        secs = item.get("securityList") or []
        if isinstance(secs, list):
            sec_text = ",".join(str(x).strip() for x in secs if str(x).strip())
        else:
            sec_text = str(secs or "")
        records.append(
            {
                "stock_note_id": item.get("stockNoteId"),
                "security_list": sec_text,
                "content": item.get("content"),
                "create_time": item.get("createTime"),
                "update_time": item.get("updateTime"),
            }
        )
    return pd.DataFrame(records)


def _fetch_note_page(
    *,
    security_list: Optional[List[str]] = None,
    note_ids: Optional[List[str]] = None,
    page_from: int = 0,
    page_size: int = NOTE_PAGE_SIZE_DEFAULT,
) -> dict:
    payload: dict = {
        "from": int(page_from),
        "size": int(page_size),
    }
    if note_ids:
        payload["stockNoteIdList"] = note_ids
    elif security_list:
        payload["securityList"] = security_list
    else:
        raise ValidationError("search_note 请指定 --securities、--all-notes 或 --note-ids")
    data = _post(GET_NOTE_LIST_URL, payload)
    return data if isinstance(data, dict) else {}


def stockpool_search_note(
    securities: Optional[List[str]] = None,
    note_ids: Optional[List[str]] = None,
    all_notes: bool = False,
    page_from: int = 0,
    page_size: int = NOTE_PAGE_SIZE_DEFAULT,
    limit: Optional[int] = None,
    output_dir: Optional[str] = None,
):
    _require_auth()
    ids = _parse_str_list(note_ids)
    codes = _normalize_security_codes(securities)
    if ids and (codes or all_notes):
        raise ValidationError("search_note 的 --note-ids 与 --securities / --all-notes 不能同时使用")
    if ids:
        note_id_list = _validate_note_ids(ids)
        security_list = None
    elif all_notes or (len(codes) == 1 and codes[0] == "ALL"):
        note_id_list = None
        security_list = ["all"]
    elif codes:
        if any(c == "ALL" for c in codes):
            raise ValidationError('securityList 的 "all" 必须单独使用，不能与证券代码混传')
        if len(codes) > MAX_NOTE_QUERY:
            raise ValidationError(f"search_note 证券代码一次最多 {MAX_NOTE_QUERY} 个")
        note_id_list = None
        security_list = codes
    else:
        raise ValidationError("search_note 请指定 --securities、--all-notes 或 --note-ids")

    size = int(page_size or NOTE_PAGE_SIZE_DEFAULT)
    if size < 1 or size > NOTE_PAGE_SIZE_MAX:
        raise ValidationError(f"page_size 须在 1～{NOTE_PAGE_SIZE_MAX} 之间")
    offset = max(0, int(page_from or 0))
    max_rows = int(limit) if limit is not None and int(limit) > 0 else None

    rows: List[dict] = []
    total = 0
    while True:
        page = _fetch_note_page(
            security_list=security_list,
            note_ids=note_id_list,
            page_from=offset,
            page_size=size,
        )
        total = int(page.get("total") or 0)
        chunk = page.get("list") or []
        if not isinstance(chunk, list):
            raise ApiError("笔记列表返回 list 格式异常")
        if not chunk:
            break
        rows.extend(chunk)
        offset += len(chunk)
        if max_rows is not None and len(rows) >= max_rows:
            rows = rows[:max_rows]
            break
        if len(chunk) < size or offset >= total:
            break

    if not rows:
        return _error("未找到符合条件的个股笔记", output_dir)

    df = _notes_to_df(rows)
    parts = [{"data": df.to_dict(orient="records"), "module": "stockpool_notes", "type": "data"}]
    msg = f"已获取 {len(df)} 条个股笔记（合计 {total} 条）"
    return format_response(
        {"state": "success", "message": msg, "data": parts, "usage": {}},
        METHOD, output_dir=output_dir)


def stockpool_add_note(security_codes: List[str], content: str, output_dir: Optional[str] = None):
    _require_auth()
    codes = _normalize_security_codes(security_codes)
    if not codes:
        raise ValidationError("add_note 请指定关联证券（--securities），须带市场后缀")
    if any(c.upper() == "ALL" for c in codes):
        raise ValidationError('add_note 不接受 "all"，请传入具体证券代码')
    if len(codes) > MAX_NOTE_SECURITIES:
        raise ValidationError(f"一条笔记最多关联 {MAX_NOTE_SECURITIES} 只证券")
    body = _validate_note_content(content)
    data = _post(ADD_NOTE_URL, {"securityList": codes, "content": body})
    data = data if isinstance(data, dict) else {}
    secs = data.get("securityList") or codes
    sec_text = "、".join(str(x) for x in secs)
    return _success_message(
        f"已创建个股笔记：stockNoteId={data.get('stockNoteId')}，关联证券：{sec_text}",
        output_dir,
    )


def stockpool_update_note(note_id: str, content: str, output_dir: Optional[str] = None):
    _require_auth()
    nid = _validate_note_id(note_id)
    body = _validate_note_content(content)
    _post(UPDATE_NOTE_URL, {"stockNoteId": nid, "content": body})
    return _success_message(f"个股笔记已更新：stockNoteId={nid}", output_dir)


def stockpool_delete_note(note_ids: List[str], output_dir: Optional[str] = None):
    _require_auth()
    ids = _validate_note_ids(note_ids)
    data = _post(DELETE_NOTE_URL, {"stockNoteIdList": ids})
    data = data if isinstance(data, dict) else {}
    success_list = data.get("successList") or []
    fail_list = data.get("failList") or []
    msg = f"删除个股笔记完成：成功 {len(success_list)} 个"
    if success_list:
        msg += "\n成功：" + "，".join(str(x) for x in success_list)
    if fail_list:
        parts = []
        for item in fail_list:
            if isinstance(item, dict):
                parts.append(f"{item.get('stockNoteId')}:{item.get('failReason') or '失败'}")
            else:
                parts.append(str(item))
        msg += "\n失败：" + "；".join(parts)
    return _success_message(msg, output_dir)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def stockpool_finder(
    mode: str = "search",
    keyword: str = "",
    pool_ids: Optional[str] = None,
    all_pools: bool = False,
    limit: int = DEFAULT_POOL_LIMIT,
    pool_name: Optional[str] = None,
    securities: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
    confirm: bool = False,
    space_type: Any = None,
    note_ids: Optional[str] = None,
    note_content: Optional[str] = None,
    all_notes: bool = False,
    page_from: int = 0,
    page_size: int = NOTE_PAGE_SIZE_DEFAULT,
):
    """按 mode 分发到股票池 / 个股笔记接口。

    space_type 仅用于 search/get：1 个人自选股（默认），2 所属租户。查明细时须与 pool_ids 同区域。
    """
    mode = (mode or "search").strip()
    if mode not in MODES:
        raise ValidationError(f"mode 仅支持 {'/'.join(MODES)}，收到 {mode}")

    if mode == "search_note":
        return stockpool_search_note(
            securities=_parse_str_list(securities),
            note_ids=note_ids,
            all_notes=bool(all_notes),
            page_from=page_from,
            page_size=page_size,
            limit=limit,
            output_dir=output_dir,
        )
    if mode == "add_note":
        return stockpool_add_note(_parse_str_list(securities), note_content or "", output_dir=output_dir)
    if mode == "update_note":
        ids = _validate_note_ids(note_ids)
        if len(ids) != 1:
            raise ValidationError("update_note 一次只能指定一个笔记 ID")
        return stockpool_update_note(ids[0], note_content or "", output_dir=output_dir)
    if mode == "delete_note":
        if not confirm:
            raise ValidationError(DELETE_NOTE_WARNING)
        return stockpool_delete_note(_parse_str_list(note_ids), output_dir=output_dir)

    st = _normalize_space_type(space_type)
    if mode not in ("search", "get") and st != SPACE_PERSONAL:
        raise ValidationError(MANAGE_PERSONAL_ONLY)
    if mode == "delete" and not confirm:
        raise ValidationError(DELETE_POOL_WARNING)

    if mode == "create":
        return stockpool_create(pool_name or "", output_dir=output_dir)

    if mode in ("search", "get") and all_pools:
        return stockpool_get(pool_ids=[], all_pools=True, space_type=st, output_dir=output_dir)

    ids: List[str] = []
    if pool_ids and str(pool_ids).strip():
        resolved, out = _resolve_pools_from_arg(str(pool_ids).strip(), limit, output_dir, space_type=st)
        if out is not None:
            return out
        ids = resolved or []

    if mode in ("search", "get"):
        if ids:
            return stockpool_get(pool_ids=ids, all_pools=False, space_type=st, output_dir=output_dir)
        if mode == "get":
            raise ValidationError("get 模式请指定 --pool、--pool-file 或 --all")
        return stockpool_search(
            keyword=keyword, limit=limit, append_file_hint=True, space_type=st, output_dir=output_dir
        )

    if mode == "delete":
        return stockpool_delete(ids, output_dir=output_dir)

    if len(ids) > 1:
        raise ValidationError(f"{mode} 模式一次只能指定一个股票池")
    pool_id = ids[0] if ids else ""
    if mode == "rename":
        return stockpool_rename(pool_id, pool_name or "", output_dir=output_dir)
    codes = _normalize_security_codes(securities)
    if mode == "add_stock":
        return stockpool_add_stock(pool_id, codes, output_dir=output_dir)
    return stockpool_delete_stock(pool_id, codes, output_dir=output_dir)


def main():
    import argparse

    try:
        if not check_version():
            update_sh = os.path.join(script_dir, "update.sh")
            print(
                f"[WARNING] 存在 Gangtise private 版本更新，可以执行 {update_sh} 更新，请与用户确认是否更新\n"
            )
    except Exception:
        print("[WARNING] 检查 Gangtise private 版本失败\n")

    parser = argparse.ArgumentParser(
        description="股票池与个股笔记：检索股票池、取池内证券、管理股票池，以及查询/新增/修改/删除个股笔记",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=MODES,
        default="search",
        help=(
            "search=列股票池；get=按池取证券；create/rename/delete/add_stock/delete_stock=管理个人池；"
            "search_note/add_note/update_note/delete_note=个股笔记。"
            "search 模式下提供 --pool/--pool-file/--all 时自动为 get。"
            "search/get 可用 --space-type；管理股票池仅支持个人自选股"
        ),
    )
    parser.add_argument("-k", "--keyword", default="", help="股票池名称/ID 关键词过滤（search 模式，可选）")
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_POOL_LIMIT, help="search 模式下列出/过滤的股票池数量上限")
    parser.add_argument(
        "--pool",
        "--pool-ids",
        dest="pool",
        default="",
        help=(
            "股票池 ID 或名称，逗号分隔；纯字母数字视为 ID，否则按名称唯一完全匹配解析。"
            "用于 get/delete（可多个）与 rename/add_stock/delete_stock（仅一个）"
        ),
    )
    parser.add_argument(
        "--pool-file",
        default=None,
        help="从 csv 读取 pool_id / poolId 列，等价于 --pool；若含 space_type 列则明细查询沿用该区域",
    )
    parser.add_argument("--all", "--all-pools", dest="all", action="store_true", help='get 模式传 poolIdList=["all"]，返回所选区域全部池的去重证券')
    parser.add_argument(
        "--space-type",
        default=None,
        help=(
            "股票池区域，仅 search/get：1 个人自选股（默认），2 所属租户；也可传「个人」「租户」。"
            "查询证券明细时须与 --pool 同属一个区域；--pool-file 含 space_type 列且未传本参数时沿用文件中的区域"
        ),
    )
    parser.add_argument("--pool-name", default=None, help="股票池名称，最长 10 字符，不可与已有池重名（create 的新池名；rename 的新名称）")
    parser.add_argument(
        "--securities",
        default=None,
        help=(
            "证券代码，逗号分隔，须带市场后缀。"
            "用于 add_stock/delete_stock；笔记模式用于 search_note/add_note（search_note 也可传 all）"
        ),
    )
    parser.add_argument("--securities-file", default=None, help="从 csv 读取 security_code 列，等价于 --securities")
    parser.add_argument(
        "--note-ids",
        default=None,
        help="个股笔记 ID，逗号分隔（search_note / update_note / delete_note；update_note 仅一个）",
    )
    parser.add_argument("--note-content", default=None, help="个股笔记正文（add_note / update_note），最长 10000 字符")
    parser.add_argument("--all-notes", action="store_true", help='search_note 查询本人全部笔记（securityList=["all"]）')
    parser.add_argument("--page-from", type=int, default=0, help="search_note 起始偏移量（不是页码）")
    parser.add_argument(
        "--page-size",
        type=int,
        default=NOTE_PAGE_SIZE_DEFAULT,
        help=f"search_note 单页条数，1～{NOTE_PAGE_SIZE_MAX}；配合 -l 可自动翻页取更多",
    )
    parser.add_argument("-od", "--output-dir", default=None, help="结果保存目录路径，建议使用绝对路径")
    parser.add_argument(
        "--yes",
        "--confirm",
        dest="confirm",
        action="store_true",
        help="确认删除（delete / delete_note 必填；不可恢复，须先取得用户同意）",
    )

    args = parser.parse_args()
    pool_arg = args.pool
    file_space: Optional[int] = None
    if args.pool_file:
        try:
            file_ids, file_space = _load_pools_from_file(args.pool_file)
            pool_arg = ",".join(file_ids)
        except Exception as e:
            print(f"读取股票池文件失败: {e}")
            sys.exit(1)

    explicit_space = args.space_type is not None and str(args.space_type).strip() != ""
    if explicit_space and file_space is not None:
        try:
            if _normalize_space_type(args.space_type) != file_space:
                print("股票池文件的 space_type 与 --space-type 不一致，查询明细须使用同一区域")
                sys.exit(1)
        except ValidationError as e:
            print(e)
            sys.exit(1)
    space_arg: Any = args.space_type if explicit_space else file_space

    securities_arg = args.securities
    if args.securities_file:
        try:
            securities_arg = ",".join(_load_security_codes_from_file(args.securities_file))
        except Exception as e:
            print(f"读取证券文件失败: {e}")
            sys.exit(1)

    print(
        stockpool_finder(
            mode=args.mode,
            keyword=(args.keyword or "").strip(),
            pool_ids=pool_arg,
            all_pools=bool(args.all),
            limit=int(args.limit),
            pool_name=args.pool_name,
            securities=_parse_str_list(securities_arg),
            output_dir=args.output_dir or None,
            confirm=bool(args.confirm),
            space_type=space_arg,
            note_ids=args.note_ids,
            note_content=args.note_content,
            all_notes=bool(args.all_notes),
            page_from=int(args.page_from),
            page_size=int(args.page_size),
        )
    )


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors="ignore")
    main()
