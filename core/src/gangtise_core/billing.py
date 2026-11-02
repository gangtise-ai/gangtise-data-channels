"""按行计费列表的积分防护：limit × 单价超过防护线时先取 1 行拿 total，估算超线则拒绝。

与 skill 的 gts_runtime.guard_row_billed_fetch 逐行等价；ROW_BILLING_PRICES / COSTLY_FETCH_CREDITS
由 scripts/check_skills.py 比对。
"""
from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional

from .errors import ValidationError
from .transport import request_json

COSTLY_FETCH_CREDITS = 1000

CREDIT_GUARD_ENV = "GANGTISE_CREDIT_GUARD"


def credit_guard_enabled() -> bool:
    """积分防护开关：默认开启；环境变量 GANGTISE_CREDIT_GUARD 为 0/false/no/off 时关闭。"""
    return (os.getenv(CREDIT_GUARD_ENV) or "").strip().lower() not in {"0", "false", "no", "off"}


# 平台公开价目（积分/条）；客户端无法测量实际扣费，缺省不代表免费。
ROW_BILLING_PRICES: Dict[str, float] = {
    "/chief-opinion/v2/getList": 1,
    "/chief-opinion/getList": 30,
    "/foreign-opinion/v2/getList": 1,
    "/foreign-opinion/getList": 30,
    "/independent-opinion/getList": 5,
    "/schedule/roadshow/getList": 20,
    "/schedule/site-visit/getList": 20,
    "/schedule/strategy-meeting/getList": 20,
    "/schedule/forum/getList": 20,
    "/schedule/performance-calendar/getList": 0.1,
    "/summary/highlight/getList": 5,
    "/security-clue/getList": 5,
    "/hot-topic/getList": 50,
    "/stock-summary/getList": 3,
}


def row_billing_price(url: str) -> Optional[float]:
    u = str(url or "").split("?", 1)[0].rstrip("/")
    best: Optional[float] = None
    best_len = -1
    for path, price in ROW_BILLING_PRICES.items():
        if u.endswith(path) and len(path) > best_len:
            best, best_len = float(price), len(path)
    return best


def guard_row_billed_fetch(
    url: str,
    payload: Mapping[str, Any],
    limit: Optional[int],
    *,
    confirm: bool = False,
    start: int = 0,
    timeout: int = 120,
) -> None:
    """limit × 单价 ≤ 防护线直接放行；否则用 size=1 探测 total，估算超线且未确认时抛 ValidationError。"""
    price = row_billing_price(url)
    if price is None or confirm or limit is None or limit <= 0 or not credit_guard_enabled():
        return
    if limit * price <= COSTLY_FETCH_CREDITS:
        return
    total: Optional[int] = None
    try:
        data = request_json("POST", url, json={**dict(payload), "from": start, "size": 1}, timeout=timeout)
        raw = data.get("total") if isinstance(data, dict) else None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            total = int(raw)
    except ValidationError:
        raise
    except Exception:
        total = None
    rows = limit if total is None else min(max(total - start, 0), limit)
    credits = round(rows * price, 2)
    if credits <= COSTLY_FETCH_CREDITS:
        return
    seen = f"共 {total} 条" if total is not None else "总数未知（按 limit 估算）"
    raise ValidationError(
        f"按当前条件将拉取 {rows} 条（limit={limit}，{seen}），该接口按条计费，预计积分消耗较大，已拒绝；"
        "为获取总数已取 1 条。"
        "请缩小时间范围/筛选条件或调小 limit；确需全部拉取须先征得用户同意，再加 --yes（MCP 传 confirm=true）。"
    )
