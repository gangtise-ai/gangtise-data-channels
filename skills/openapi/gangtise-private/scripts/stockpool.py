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

from .gts_runtime import ApiError, ValidationError
from .gts_runtime import request_json

from .utils import (
    ADD_STOCK_URL,
    CREATE_POOL_URL,
    DELETE_POOL_URL,
    DELETE_STOCK_URL,
    GET_POOL_LIST_URL,
    GET_STOCK_LIST_URL,
    UPDATE_POOL_URL,
    check_version,
    format_response,
    get_authorization_token,
    is_code_arg,
    load_pool_ids_from_file,
)

script_dir = os.path.dirname(os.path.abspath(__file__))

DEFAULT_POOL_LIMIT = 100
IDS_FILE_HINT = "可以删除行或保留需要的池，再通过 --pool-file 参数读取文件获取证券"
METHOD = "stockpool"
MODES = ["search", "get", "create", "rename", "delete", "add_stock", "delete_stock"]
# 删除不可恢复：所有入口（脚本、CLI、MCP）都须显式确认，被拒后不要未经用户同意自行补确认重试。
DELETE_POOL_WARNING = (
    "已拒绝：删除股票池会同时移除池内全部证券的关注关系，且不可恢复（投资笔记不受影响）。"
    "先用 search 模式核对 ID 对应的池名并取得用户明确同意，再加 --yes（MCP 传 confirm=true）重试。"
)
MAX_POOL_NAME_LEN = 10


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


def _fetch_pool_list() -> List[dict]:
    data = _post(GET_POOL_LIST_URL, {}) or []
    if not isinstance(data, list):
        raise ApiError("股票池列表返回 data 格式异常")
    return data


def _fetch_stock_list(pool_id_list: List[str]) -> List[dict]:
    ids = [str(x).strip() for x in pool_id_list if str(x).strip()]
    if not ids:
        raise ValidationError("股票池 ID 列表不能为空")
    data = _post(GET_STOCK_LIST_URL, {"poolIdList": ids}) or []
    if not isinstance(data, list):
        raise ApiError("证券明细返回 data 格式异常")
    return data


def _pools_to_df(pools: List[dict]) -> pd.DataFrame:
    records = []
    for item in pools:
        records.append(
            {
                "pool_id": item.get("poolId"),
                "pool_name": item.get("poolName"),
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


def _resolve_pools_from_arg(raw: str, limit: int, output_dir: Optional[str] = None) -> Tuple[Optional[List[str]], Optional[Any]]:
    """池 ID 原样返回；名称唯一完全匹配时解析为 ID，否则返回候选列表。"""
    if is_code_arg(raw):
        return _parse_str_list(raw), None

    _require_auth()
    pools = _fetch_pool_list()
    resolved: List[str] = []
    search_outputs: List[str] = []
    for token in _parse_str_list(raw):
        filtered = _filter_pools_by_keyword(pools, token)
        exact = _exact_match_pools(token, filtered)
        if len(exact) == 1:
            pid = str(exact[0].get("poolId") or "").strip()
            if pid:
                resolved.append(pid)
            continue
        if not filtered:
            return None, _error(f"未找到与「{token}」相关的股票池", output_dir)
        if len(exact) > 1:
            prefix = f"「{token}」存在 {len(exact)} 条完全匹配，请指定更精确的名称或 ID：\n\n"
        else:
            prefix = f"未找到与「{token}」完全匹配的股票池，以下为候选结果：\n\n"
        search_outputs.append(prefix + str(stockpool_search(keyword=token, limit=limit, output_dir=output_dir)))

    if search_outputs:
        return None, "\n\n".join(search_outputs)
    return resolved, None


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
    output_dir: Optional[str] = None,
    **kwargs,
):
    _require_auth()
    pools = _fetch_pool_list()
    if not pools:
        return _error("当前账号下无自选股股票池", output_dir)

    pools = _filter_pools_by_keyword(pools, keyword)
    pools = _apply_pool_limit(pools, limit)
    if not pools:
        kw_hint = f"与「{keyword.strip()}」匹配的" if (keyword or "").strip() else ""
        return _error(f"未找到{kw_hint}股票池", output_dir)

    df = _pools_to_df(pools)
    parts = [
        {
            "data": df.to_dict(orient="records"),
            "module": "stockpool_pools",
            "type": "data",
        }
    ]
    msg = f"已获取 {len(df)} 个自选股股票池"
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
    output_dir: Optional[str] = None,
    **kwargs,
):
    _require_auth()
    if all_pools:
        pool_id_list = ["all"]
    else:
        pool_id_list = [str(x).strip() for x in pool_ids if str(x).strip()]
        if not pool_id_list:
            raise ValidationError("股票池 ID 列表不能为空（或使用 --all-pools 获取全部池去重证券）")

    stocks = _fetch_stock_list(pool_id_list)
    if not stocks:
        return _error("股票池中无证券或 ID 无效", output_dir)

    df = _stocks_to_df(stocks)
    parts = [
        {
            "data": df.to_dict(orient="records"),
            "module": "stockpool_stocks",
            "type": "data",
        }
    ]
    if all_pools:
        msg = f"已获取全部自选股股票池去重后的 {len(df)} 只证券"
    else:
        msg = f"已获取 {len(pool_id_list)} 个股票池共 {len(df)} 只证券（已按代码去重）"
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
):
    """按 mode 分发到股票池各接口；mode=search 且提供 pool_ids / all_pools 时自动获取池内成分股。"""
    mode = (mode or "search").strip()
    if mode not in MODES:
        raise ValidationError(f"mode 仅支持 {'/'.join(MODES)}，收到 {mode}")
    if mode == "delete" and not confirm:
        raise ValidationError(DELETE_POOL_WARNING)

    if mode == "create":
        return stockpool_create(pool_name or "", output_dir=output_dir)

    if mode in ("search", "get") and all_pools:
        return stockpool_get(pool_ids=[], all_pools=True, output_dir=output_dir)

    ids: List[str] = []
    if pool_ids and str(pool_ids).strip():
        resolved, out = _resolve_pools_from_arg(str(pool_ids).strip(), limit, output_dir)
        if out is not None:
            return out
        ids = resolved or []

    if mode in ("search", "get"):
        if ids:
            return stockpool_get(pool_ids=ids, all_pools=False, output_dir=output_dir)
        if mode == "get":
            raise ValidationError("get 模式请指定 --pool-ids、--pool-file 或 --all-pools")
        return stockpool_search(keyword=keyword, limit=limit, append_file_hint=True, output_dir=output_dir)

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
        description="自选股股票池：检索股票池、取池内证券，以及创建/重命名/删除股票池、添加/移除证券",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=MODES,
        default="search",
        help=(
            "search=列股票池；get=按池取证券；create=创建池；rename=重命名池；delete=删除池；"
            "add_stock=向池添加证券；delete_stock=从池移除证券。"
            "search 模式下提供 --pool/--pool-file/--all 时自动为 get"
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
    parser.add_argument("--pool-file", default=None, help="从 csv 读取 pool_id / poolId 列，等价于 --pool")
    parser.add_argument("--all", "--all-pools", dest="all", action="store_true", help='get 模式传 poolIdList=["all"]，返回全部池去重证券')
    parser.add_argument("--pool-name", default=None, help="股票池名称，最长 10 字符，不可与已有池重名（create 的新池名；rename 的新名称）")
    parser.add_argument(
        "--securities",
        default=None,
        help="证券代码，逗号分隔，须带市场后缀，如 600519.SH,00700.HK,AAPL.O（add_stock/delete_stock）",
    )
    parser.add_argument("--securities-file", default=None, help="从 csv 读取 security_code 列，等价于 --securities")
    parser.add_argument("-od", "--output-dir", default=None, help="结果保存目录路径，建议使用绝对路径")
    parser.add_argument("--yes", "--confirm", dest="confirm", action="store_true", help="确认删除（delete 模式必填；不可恢复，须先取得用户同意）")

    args = parser.parse_args()
    pool_arg = args.pool
    if args.pool_file:
        try:
            pool_arg = ",".join(load_pool_ids_from_file(args.pool_file))
        except Exception as e:
            print(f"读取股票池文件失败: {e}")
            sys.exit(1)

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
        )
    )


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors="ignore")
    main()
